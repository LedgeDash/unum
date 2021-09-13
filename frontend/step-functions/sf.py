#!/usr/bin/env python
import json, os, sys, subprocess, time
import argparse
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from cfn_tools import load_yaml, dump_yaml

unum_map_counter = 0
unum_parallel_counter = 0

PASS_FUNCTION = "def lambda_handler(event, context):\n    return event"

def lambda_state(state):
    if ':' not in state["Resource"]:
        return True

    # AWS arn
    if state["Resource"].split(':')[2] == 'lambda':
        return True

    return False

def get_state_unum_function_name(state):
    ''' Given a Step Functions Task state, return the Lambda function's unum
    name

    @param state dict

    @return str
    '''
    if 'arn:aws:lambda' in state["Resource"]:
        try:
            with open('function-arn.yaml') as f:
                arn_to_name_mapping = load_yaml(f.read())
        except Exception as e:
            raise e

        try:
            function_name = list(arn_to_name_mapping.keys())[list(arn_to_name_mapping.values()).index(state["Resource"])]
        except Exception as e:
            raise e
        return function_name

    else:
        return state["Resource"]


def _translate_state_machine(state_name, state_machine):
    ''' Given a state, compute the IR, Entry function's config and exit
    function's config for the downstream state machine
    '''

    state = state_machine["States"][state_name]
    ir = []

    if state["Type"] == "Task":
        unum_function_name = get_state_unum_function_name(state)
        # print(f'{state_name}: {state}\nFunction name: {unum_function_name}')
        if "End" in state and state["End"] == True:

            config = {"Name": unum_function_name}
            ir.append(config)
            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": config,
                "Exit unum function": config
            }

        elif "Next" in state:

            next_state = _translate_state_machine(state["Next"], state_machine)

            config = {
                "Name": unum_function_name,
                "Next": {"Name": next_state["Entry unum function"]["Name"]},
                "NextInput":"Scalar"
            }

            ir.append(config)
            ir = ir + next_state["unum IR"]

            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": config,
                "Exit unum function": next_state["Exit unum function"]
            }
        else:
            raise

    elif state["Type"] == "Map":

        iterator = translate_state_machine(state["Iterator"])
        global unum_map_counter
        unum_map = {
            "Name": f'UnumMap{unum_map_counter}',
            "Next": {"Name": iterator["Entry unum function"]["Name"]},
            "NextInput": "Map"
        }

        unum_map_sink = {
            "Name": f'UnumSinkMap{unum_map_counter}'
        }
        unum_map_counter = unum_map_counter + 1

        iterator["Exit unum function"]["Next"] = {"Name": unum_map_sink["Name"]}
        iterator["Exit unum function"]["NextInput"] = {
            "Fan-in": {
                "Values": [
                    f'{iterator["Exit unum function"]["Name"]}-unumIndex-*'
                ]
            }
        }

        ir.append(unum_map)
        ir = ir + iterator["unum IR"]
        ir.append(unum_map_sink)

        if "Next" in state:
            next_state = _translate_state_machine(state["Next"], state_machine)
            unum_map_sink["Next"] = {"Name": next_state["Entry unum function"]["Name"]}
            unum_map_sink["NextInput"] = "Scalar"
            ir = ir + next_state["unum IR"]
            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": unum_map,
                "Exit unum function": next_state["Exit unum function"]
            }
        else:
            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": unum_map,
                "Exit unum function": unum_map_sink
            }


    elif state["Type"] == "Parallel":
        branches = [translate_state_machine(b) for b in state["Branches"]]
        global unum_parallel_counter
        unum_parallel = {
            "Name": f'UnumParallel{unum_parallel_counter}',
            "Next": [{"Name": b["Entry unum function"]["Name"]} for b in branches],
            "NextInput":"Scalar"
        }
        ir.append(unum_parallel)

        unum_parallel_sink = {
            "Name": f'UnumSinkParallel{unum_parallel_counter}'
        }
        unum_parallel_counter = unum_parallel_counter +1
        parallel_fan_in_vals = [f'{branches[i]["Exit unum function"]["Name"]}-unumIndex-{i}' for i in range(len(branches))]
        for b in branches:
            ir = ir + b["unum IR"]
            b["Exit unum function"]["NextInput"] = {
                "Fan-in": {
                    "Values": parallel_fan_in_vals
                }
            }
            b["Exit unum function"]["Next"] = {"Name": unum_parallel_sink["Name"]}

        ir.append(unum_parallel_sink)

        if "Next" in state:
            next_state = _translate_state_machine(state["Next"], state_machine)
            unum_parallel_sink["Next"] = {"Name": next_state["Entry unum function"]["Name"]}
            unum_parallel_sink["NextInput"] = "Scalar"
            ir = ir + next_state["unum IR"]
            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": unum_parallel,
                "Exit unum function": next_state["Exit unum function"]
            }
        else:
            return {
                "State Name": state_name,
                "unum IR": ir,
                "Entry unum function": unum_parallel,
                "Exit unum function": unum_parallel_sink
            }


def translate_state_machine(state_machine):
    ''' Given a state machine, return its IR, entry state and end state

    A state machine = A Step Function state machine, a Map State, a Parallel
    State
    '''

    states = state_machine["States"]
    entry_state_name = state_machine["StartAt"]
    entry_state = states[entry_state_name]

    ret = _translate_state_machine(entry_state_name, state_machine)

    return ret

def get_config_by_name(function_name, ir):
    for c in ir['unum IR']:
        # print(f'{c}   {function_name}')
        if c["Name"] == function_name:
            return c

    return None

def _trim(fc, ir):

    if "Next" not in fc:
        return

    # If the workflow starts with a Map or Parallel state, then the generated
    # UnumMap or UnumParallel function needs to stay. In fact, if _trim() ever
    # encounters a UnumMap or UnumParallel function, it should stay.
    if fc["Name"].startswith("UnumMap") or fc["Name"].startswith("UnumParallel"):
        # if ir["Entry unum function"] == fc:
        #     fc["Remove"] = False
        fc["Remove"] = False
    else:
        # if next is a UnumSinkMap or UnumSinkParallel that has a next
        # function, skip the sink
        if fc["Next"]["Name"].startswith("UnumSinkMap") or fc["Next"]["Name"].startswith("UnumSinkParallel"):
            next_sink_config = get_config_by_name(fc["Next"]["Name"], ir)
            if "Next" in next_sink_config and next_sink_config["NextInput"] == "Scalar":
                fc["Next"]["Name"] = next_sink_config["Next"]["Name"]
                next_sink_config["Remove"] = True

        # when a NON-SINK function has UnumMap or UnumParallel as its next
        # function with Scalar input, we can have the function perform the
        # fan-out and skip the UnumMap or UnumParallel
        elif fc["Next"]["Name"].startswith("UnumMap"):
            next_map_config = get_config_by_name(fc["Next"]["Name"], ir)
            if fc["NextInput"] == "Scalar":
                fc["Next"]["Name"] = next_map_config["Next"]["Name"]
                fc["NextInput"] = "Map"
                next_map_config["Remove"] = True

        elif fc["Next"]["Name"].startswith("UnumParallel"):
            next_parallel_config = get_config_by_name(fc["Next"]["Name"], ir)
            fc["Next"] = next_parallel_config["Next"]
            next_parallel_config["Remove"] = True


    if isinstance(fc["Next"], list):
        for n in fc["Next"]:
            _trim(get_config_by_name(n["Name"], ir), ir)
    else:
        _trim(get_config_by_name(fc["Next"]["Name"], ir), ir)

def trim(ir):
    entry_function = ir["Entry unum function"]
    _trim(entry_function, ir)

    for c in ir["unum IR"]:
        if "Remove" in c and c["Remove"] == True:
            ir["unum IR"].remove(c)
    return

def main():
    parser = argparse.ArgumentParser(description='unmu frontend compiler for AWS Step Functions',
        # usage = "unum-cli [options] <command> <subcommand> [<subcommand> ...] [parameters]",
        #epilog="To see help text for a specific command, use unum-cli <command> -h"
        )
    parser.add_argument('-w', '--workflow',
        help="Step Functions state machine", required=True)
    parser.add_argument('-t', '--template',
        help="unum template", required=True)
    parser.add_argument('-p', '--print',
        help="print the generate IR to stdout", action="store_true", required=False)
    parser.add_argument('-u', '--update',
        help="update the function's unum_config", action="store_true", required=False)
    parser.add_argument('-o', '--optimize',
        help="optimizations", choices=['trim', 'foo'], required=False)

    args = parser.parse_args()

    with open(args.workflow) as f:
        state_machine = json.loads(f.read())

    ir = translate_state_machine(state_machine)


    # Add global configurations from unum-template.yaml
    with open(args.template) as f:
        template = load_yaml(f.read())

    for c in ir["unum IR"]:
        if "NextInput" in c and "Fan-in" in c["NextInput"]:
            c["Checkpoint"] = True
        else:
            c["Checkpoint"] = template["Globals"]["Checkpoint"]

    # mark the start function
    ir["Entry unum function"]["Start"] = True

    if args.optimize == "trim":
        print(f'Trimming IR...')
        trim(ir)


    if args.print:
        print("**************** IR ***************")
        print(f'{ir}')

    if args.update:
        workflow_dir = os.path.dirname(args.template)
        for config in ir["unum IR"]:
            if config["Name"] in template["Functions"]:
                function_dir = os.path.join(workflow_dir, template["Functions"][config["Name"]]["Properties"]["CodeUri"])
                with open(os.path.join(function_dir, 'unum_config.json'), 'w') as f:
                    f.write(json.dumps(config))

            elif config["Name"].startswith("UnumMap") or config["Name"].startswith("UnumParallel"):
                # update the template
                template["Functions"][config["Name"]] = {
                    'Properties': {
                        "CodeUri": f'{config["Name"]}/',
                        "Runtime": "python3.8"
                        }
                    }

                # create the directory and inside the directory, create
                # unum_config.json, __init__.py, requirements.txt and app.py
                function_dir = os.path.join(workflow_dir, f'{config["Name"]}/')
                try:
                    os.mkdir(function_dir)
                except FileExistsError as e:
                    pass

                with open(os.path.join(function_dir, '__init__.py'), 'w') as f:
                    pass
                with open(os.path.join(function_dir, 'requirements.txt'), 'w') as f:
                    pass
                with open(os.path.join(function_dir, 'app.py'), 'w') as f:
                    f.write(PASS_FUNCTION)
                with open(os.path.join(function_dir, 'unum_config.json'), 'w') as f:
                    f.write(json.dumps(config))

        # move the old unum-template.yaml file to .unum-template.yaml.old
        # Save the new template as unum-template.yaml
        os.rename(args.template, f'.{args.template}.old')
        with open(os.path.join(workflow_dir, args.template), 'w') as f:
            f.write(dump_yaml(template))


if __name__ == '__main__':
    main()