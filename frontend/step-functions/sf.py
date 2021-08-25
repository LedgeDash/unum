#!/usr/bin/env python
import json, os, sys, subprocess, time
import argparse
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from cfn_tools import load_yaml, dump_yaml



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

def _get_map_continuation(state):

    if state["Type"] != "Map":
        raise

    iterator = state["Iterator"]
    entry_state = iterator["States"][iterator["StartAt"]]

    if entry_state["Type"] == "Task":
        return {
                "Next": {
                    "Name": get_state_unum_function_name(entry_state)
                },
                "NextInput": "Map"
            }
    elif entry_state["Type"] == "Parallel":
        pass
    elif entry_state["Type"] == "Map":
        pass
    elif entry_state["Type"] == "Choice":
        pass


def _get_parallel_continuation(state):
    if state["Type"] != "Parallel":
        raise

    cnts = []
    # each branch is a state machine
    for b in state["Branches"]:
        entry_state = b["States"][b["StartAt"]]
        branch_continuation = _get_continuation(entry_state)
        if branch_continuation["NextInput"] == "Scalar":
            # the state is of type "Task"
            cnts.append(branch_continuation)
        elif branch_continuation["NextInput"] == "Map":
            pass
        else:
            pass
    ret = {"Next":[], "NextInput": cnts[0]["NextInput"]}
    for c in cnts:
    	ret["Next"].append(c["Next"])
    print(ret)
    return ret

def _get_continuation(state):
    ''' Given a state, return the continuation into it. State here can be a
    state machine in the case of Map Iterator and Parallel branches
    '''
    if state["Type"] == "Task":
        return {
            "Next": {
                "Name": get_state_unum_function_name(state)
            },
            "NextInput": "Scalar"
        }

    elif state["Type"] == "Map":
        return _get_map_continuation(state)
    elif state["Type"] == "Parallel":
        return _get_parallel_continuation(state)
    elif state["Type"] == "Pass":
        pass
    elif state["Type"] == "Wait":
        pass
    elif state["Type"] == "Choice":
        pass
    elif state["Type"] == "Succeed":
        return None
    elif state["Type"] == "Fail":
        return None



def get_continuation(state, state_machine):
    ''' Given a state, compute its continuation based on its "Next" and "End"
    field. Return the continuation as a dict.
    '''
    if "End" in state and state["End"] == True:
        return None

    try:
        next_state = state_machine["States"][state["Next"]]
        return _get_continuation(next_state)
    except KeyError as e:
        raise e


def translate_task(state_name, state, state_machine):
    ''' Given a Step Function Task state, return its unum config
    '''

    # Get the unum function name from the Resource field
    # This field will be the directory where the new config file lives
    unum_function_name = get_state_unum_function_name(state)
    print(f'{state_name}: {state}\nFunction name: {unum_function_name}')

    config = {
        "Name": unum_function_name,
        "State ID": state_name
    }

    continuation = get_continuation(state, state_machine)
    if continuation == None:
        return config
    else:
        return {**config, **continuation}



def translate_state(state_name, state_machine):
    ''' Given a state in a Step Function state machine definition, generate
    its unum-config in the form of a python dict.

    Note that the state can be container states such as Map and Parallel, in
    which case this function returns a list of dict.

    @param state_name
    @param state_machine

    @return unum_config dict
    '''
    this_state = state_machine["States"][state_name]
    # print(f'{state_name}: {this_state}')

    if this_state["Type"] == "Task":
        return translate_task(state_name, this_state, state_machine)
    elif this_state["Type"] == "Map":
        return translate_map(state_name, this_state, state_machine)
    elif this_state["Type"] == "Parallel":
        return translate_parallel(state_name, this_state, state_machine)
    elif this_state["Type"] == "Choice":
        return translate_choice(state_name, this_state, state_machine)
    elif this_state["Type"] == "Pass" or this_state["Type"] == "Wait" or this_state["Type"] == "Succeed" or this_state["Type"] == "Fail":
        return
    else:
        raise ValueError(f'Unknown State type')

def translate_state_machine(state_machine):
    # entry_state = state_machine["States"][state_machine["StartAt"]]
    ir = []
    for state_name in state_machine["States"]:
        print(f'IR: {ir}')
        print(f'state_name:{state_name}')
        c = translate_state(state_name, state_machine)
        print(f'config: {c}')
        if isinstance(c, list):
            ir = ir + c
        elif isinstance(c, dict):
            ir.append(c)
    return ir



def main():
    parser = argparse.ArgumentParser(description='unmu frontend compiler for AWS Step Functions',
        # usage = "unum-cli [options] <command> <subcommand> [<subcommand> ...] [parameters]",
        #epilog="To see help text for a specific command, use unum-cli <command> -h"
        )
    parser.add_argument('-w', '--workflow',
        help="Step Functions state machine", required=True)
    parser.add_argument('-t', '--template',
        help="unum template", required=True)

    args = parser.parse_args()

    print(args.workflow)

    with open(args.workflow) as f:
        state_machine = json.loads(f.read())

    print(state_machine)
    ir = translate_state_machine(state_machine)

    # Handle the start state
    entry_state = state_machine["States"][state_machine["StartAt"]]
    if entry_state["Type"] == "Map":
        pass
    elif entry_state["Type"] == "Parallel":
        pass
    elif entry_state["Type"] == "Choice":
        pass
    else:
        pass

    # Add global configurations from unum-template.yaml
    with open(args.template) as f:
        template = load_yaml(f.read())

    for c in ir:
        c["Checkpoint"] = template["Globals"]["Checkpoint"]

    print(f'Final IR: {ir}')
if __name__ == '__main__':
    main()