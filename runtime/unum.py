from ds import UnumIntermediaryDataStore
import json
import uuid
import os, sys
import time, datetime
import random
import string
import re
import functools
from enum import Enum

from faas_invoke_backend import InvocationBackend



class Unum(object):

    def __init__(self, config, datastore_type, datastore_name, platform):
        '''Given a unum configuration, unum intermediary data store info,
        create the runtime context for this function to run.

        The unum configuration for a function is in the unum_config.json file
        and it is function-specific. The unum intermediary data store
        information is in unum-template.yaml and it is shared by all functions
        in the workflow.

        In the case of AWS Lambda, data store info is accessed via environment
        variables.

        All possible continuations for a function are known at compile time.
        The conditional in continuations only controls whether a continuation
        executes or not during runtime. But no continuation is created on the
        fly during runtime.

        Note that once the unum_config and data store info are read and
        related states initialized, they do not change at all during runtime.
        To change them, the function sources needs to be updated and
        redeployed.

        @param config dict the entire JSON from unum_config.json
        @param datastore_type str, supported values: 's3', 'dynamodb'
        @param datastore_name str
        @param platform str, supported values: 'aws'
        '''
        self.name = config['Name']
        self.platform = platform

        try:
            self.checkpoint = config['Checkpoint']
            if self.checkpoint:
                self.run_checkpoint = self._run_checkpoint
            else:
                self.run_checkpoint = noop
        except KeyError:
            self.checkpoint = False
            self.run_checkpoint = noop

        try:
            self.debug = config['Debug']
        except KeyError:
            self.debug = False

        try:
            self.entry_function = config['Start']
            self.get_session = self._generate_session
        except KeyError:
            self.entry_function = False
            self.get_session = self._extract_session

        # TODO: Change Next Payload Modifiers to a per continuation feature
        try:
            self.next_payload_modifiers = config['Next Payload Modifiers']
        except KeyError:
            self.next_payload_modifiers = []

        # print(f'Creating data store type: {datastore_type}, and name: {datastore_name}')
        self.ds = UnumIntermediaryDataStore.create(datastore_type, datastore_name, self.debug)

        self.cont_list = []
        if 'Next' in config:

            self.faas_backend = InvocationBackend.create(platform)

            if isinstance(config['Next'], dict):
                self.cont_list.append(
                    UnumContinuation(
                        config['Next']['Name'],
                        config['Next']['InputType'],
                        config['Next'].get('Conditional'),
                        self.faas_backend, datastore_type,
                        self.ds,
                        debug=self.debug
                        ))
            elif isinstance(config['Next'], list):
                # count the parallel size.
                #
                # Note that the parallel size is not the fan-in size because
                # unum supports partial fan-ins. Fan-in size (or how many
                # functions to 'wait for' before invoking the fan-in function)
                # is determined by the list of names in the
                # config["Next"]["InputType"]["Fan-in"]["Values"] field.
                pc = 0
                for c in config['Next']:
                    # if c['InputType'] == 'Scalar' and 'Parallel' in c and c['Parallel'] == True:
                    if c['InputType'] == 'Scalar':
                        pc = pc +1

                pi = 0
                for c in config['Next']:
                    # if c['InputType'] == 'Scalar' and 'Parallel' in c and c['Parallel'] == True:
                    if c['InputType'] == 'Scalar':
                        # parallel fan-out
                        self.cont_list.append(
                            UnumContinuation(
                                c['Name'],
                                c['InputType'],
                                c.get('Conditional'),
                                self.faas_backend,
                                datastore_type,
                                self.ds,
                                parallel_index=pi,
                                parallel_size=pc,
                                debug=self.debug))
                        pi = pi+1
                    else:
                        self.cont_list.append(
                            UnumContinuation(
                                c['Name'],
                                c['InputType'],
                                c.get('Conditional'),
                                self.faas_backend,
                                datastore_type,
                                self.ds,
                                debug=self.debug))
            else:
                raise ValueError(f'Unknown config["Next"] type: {type(config["Next"])}; {config["Next"]}')

        # Per-invocation states
        self.curr_session = None
        self.curr_instance_name = None
        self.curr_unumIndex_str = None

        # curr_unumIndex_list should be
        #   1. None at the beginning of invocation
        #   2. [] if there's no Fan-out 
        #   3. [x, y, z] if there's Fan-out
        self.curr_unumIndex_list = None

        self.previous_checkpoint = False
        # self.curr_next_payload_fanout = None

        # my_gc_tasks and my_outgoing_edges are for garbage collection

        # A dict whose keys are my parent nodes' instance names and values are
        # that node's outgoing edges (i.e., child nodes' instance names)
        self.my_gc_tasks = None
        # A dict whose key is my instance name and values are my outgoing
        # edges
        self.my_outgoing_edges = None



    def get_checkpoint(self, input_payload):
        '''Return the checkpoint of this instance

        If the checkpoint does not exist, return None. Otherwise, return the
        data of the checkpoint as a python data structure from json.loads().

        unum calls this function before running the user function. If a
        checkpoint exists, a prior instance completed at least up to
        checkpointing and this instance is therefore a duplicate. unum sets
        self.previous_checkpoint = True to indicate a duplicate.

        @param input_payload dict the `event` from the lambda input
        '''
        session = self.get_session(input_payload)
        instance_name = self.get_my_instance_name(input_payload)

        ds_ret = self.ds.get_checkpoint(session, instance_name)

        if ds_ret == None:
            self.previous_checkpoint = False
            return None

        self.previous_checkpoint = True
        return ds_ret


    @staticmethod
    def arn_to_function_name(arn):
        parts = arn.split(':')[-1].split('-')
        return parts[-2].strip("Function")



    def get_my_outgoing_edges(self, input_payload, user_function_output):
        '''Return the instance names of my downstream functions

        The instance names of my downstream functions represent my outgoing
        edges.

        As the potential invoker of my downstream functions, I can compute
        exactly the instance name of my downstream functions because

            1. With my user code output, I can know which of my downstream
               functions will be invoked

            2. I know the function names of my downstream functions

            3. I'll be creating the input payload of my downstream functions,
               including filling in the "Fan-out" field

        An instance name = f'{function_name}-unumIndex-{unum_index_str}'

        @return a list of instance names
        '''

        if self.my_outgoing_edges == None:

            post_modifier_metadata = self.run_next_payload_modifiers(input_payload)

            outgoing_edges = []

            for c in self.cont_list:
                next_payload = c.compute_payload_metadata(input_payload, user_function_output, post_modifier_metadata)

                if isinstance(next_payload, list):
                    for e in next_payload:
                        outgoing_edges.append(Unum.compute_instance_name(c.function_name, e))
                else:
                    outgoing_edges.append(Unum.compute_instance_name(c.function_name, next_payload))

            self.my_outgoing_edges = outgoing_edges

        return self.my_outgoing_edges



    def run_continuation(self, input_payload, user_function_output):
        '''Given the input payload of the invoker (runtime metadata) and the
        user function's output, execute the continuations.

        This function computes the session, and the fan-out field after Next
        Payload Modifiers before passing them to the continuation's run() API.
        '''

        session = self.get_session(input_payload)
        next_payload_metadata = self.run_next_payload_modifiers(input_payload)

        gc_info = {self.get_my_instance_name(input_payload): self.get_my_outgoing_edges(input_payload, user_function_output)}

        for c in self.cont_list:
            c.run(user_function_output,
                session,
                next_payload_metadata,
                input_payload,
                self.get_my_unum_index_list(input_payload),
                gc=gc_info,
                my_name=self.name,
                my_curr_instance_name=self.get_my_instance_name(input_payload))

        # returning session simply for debugging purposes
        return session, next_payload_metadata



    def _run_checkpoint(self, input_payload, user_function_output):
        '''Checkpoint the user function's output

        Checkpoint saves the *user function's output* to the intermediary data
        store.

        Each function invocation is assigned a unique name when writing to the
        intermediary data store. The exact naming scheme varies depending on
        the data store but all schemes comprise of the session ID (of the
        workflow invocation) and the function instance name. _run_checkpoint()
        simply passes the session ID and instance name to the ds library and
        the ds library figures out the exact name depending on which data
        store is used.

        Note that although the checkpoint name is decided by the ds library,
        the instance name is computed here by Unum. It is
        <function-name>[-unumIndex-$n.$(n-1).....$0]. See get_my_instance_name() for details.

        Functions that have continuations whose "InputType" is "Fan-in" always
        has "Checkpoint" set to True. Functions that don't have continuations
        or other types of continuations don't have to checkpoint.

        Users turn workflow-wise checkpoint on and off in the unum template.
        '''
        # print(f'PRINTING _run_checkpoint. {self.get_session(input_payload)}; {self.get_my_instance_name(input_payload)}; {user_function_output}')

        if self.previous_checkpoint:
            # if a previous checkpoint already exists, skip checkpoint again.
            return -2

        ret = self.ds.checkpoint(self.get_session(input_payload),
                self.get_my_instance_name(input_payload), user_function_output)

        if ret == -1:
            # checkpoint already exists
            if self.debug:
                print(f'[DEBUG] checkpoint already exists when trying to create. Session: {self.get_session(input_payload)}, instance name: {self.get_my_instance_name(input_payload)}')

            return -1
        elif ret >= 1:
            # ds successfully writes checkpoint
            return 0

        # unknow error
        return -3



    def run_gc(self):
        '''Delete my parents' checkpoints to garbage collect
        '''

        if self.my_gc_tasks == None:
            return

        if len(self.my_gc_tasks) == 0:
            print(f'No gc tasks')
            return

        # print(f'My gc tasks:{self.my_gc_tasks}')

        for k in self.my_gc_tasks:
            if len(self.my_gc_tasks[k]) == 1:
                if self.my_gc_tasks[k][0] == self.curr_instance_name:
                    # I'm the only child of my parent. Delete my parent's checkpoint now
                    # print(f'[Unum] deleting {self.ds.checkpoint_name(self.curr_session, k)}')
                    self.ds.delete_checkpoint(self.curr_session, k)
                else:
                    print(f'I am not the child of my parent?')

            elif len(self.my_gc_tasks[k]) > 1:
                # I have siblings.
                my_idx = self.my_gc_tasks[k].index(self.curr_instance_name)

                if self.ds.gc_sync_ready(self.curr_session, k, my_idx, len(self.my_gc_tasks[k])):
                    # print(f'[Unum] deleting {self.ds.checkpoint_name(self.curr_session, k)}')
                    self.ds.delete_checkpoint(self.curr_session, k)
            else:
                print(f'self.my_gc_tasks[k] has no element: {self.my_gc_tasks[k]}')




    def run_next_payload_modifiers(self, input_payload):
        '''Given the input payload, return the metadata fields after executing
        Next Payload Modifiers as a dict.

        Next Payload Modifiers are statically specified in the unum
        configuration. They are an ordered array of strings each of which is
        one operation.

        Metadata fields are:
            1. "Fan-out"

        @return a dict with all metadata fields. If a field doesn't exist in
            the input payload or is removed by a Next Payload Modifier, that
            field is included in the return dict and maps to None.
        '''
        metadata = {
            "Fan-out": input_payload.get("Fan-out")
        }
        for m in self.next_payload_modifiers:
            metadata = self._run_next_payload_modifier(m, metadata)

        return metadata



    def _run_next_payload_modifier(self, modifier, metadata):
        '''Run a single modifier on the metadata and return the updated
        metadata
        '''

        # The following modifiers all require the metadata to have an
        # non-empty "Fan-in" field

        if "Fan-out" not in metadata or metadata["Fan-out"] == None:
                return metadata

        if modifier == "Pop":

            if "OuterLoop" not in metadata["Fan-out"]:
                metadata["Fan-out"] = None
                return metadata

            metadata["Fan-out"] = metadata["Fan-out"]["OuterLoop"]
            return metadata

        exec_modifier = modifier
        if "$size" in modifier:
            exec_modifier = exec_modifier.replace("$size", 'metadata["Fan-out"]["Size"]')

        if "$0" in modifier:
            exec_modifier = exec_modifier.replace("$0", 'metadata["Fan-out"]["Index"]')

        if "$1" in modifier:
            exec_modifier = exec_modifier.replace("$1", 'metadata["Fan-out"]["OuterLoop"]["Index"]')

        exec(exec_modifier)

        return metadata



    def get_my_unum_index_list(self, input_payload):
        '''Return my unum index as a list

        This function caches the result into self.curr_unumIndex_list

        See compute_unum_index_list() for how unum index list is computed.

        @param input_payload dict Lambda input event

        '''

        if self.curr_unumIndex_list == None:
            self.curr_unumIndex_list = Unum.compute_unum_index_list(input_payload)

        return self.curr_unumIndex_list



    def get_my_unum_index_str(self, input_payload):
        '''Return my unum index string

        This function caches the result into self.curr_unumIndex_str

        See compute_unum_index_str() for how unum index string is computed.

        @param input_payload dict Lambda input event
        '''

        if self.curr_unumIndex_str == None:
            self.curr_unumIndex_str = Unum.compute_unum_index_str(input_payload)

        return self.curr_unumIndex_str



    def get_my_instance_name(self, input_payload):
        '''Given the input payload, get the instance name

        The function name is set in the unum config, and the unumIndex is
        computed from the input payload which is decided by the invoker of
        this function. This function does NOT have ways to change its
        unumIndex.

        get_my_instance_name() caches the computed instance name into
        self.curr_instance_name. self.curr_instance_name should be set back to
        None after an invocation completes.
        '''
        
        if self.curr_instance_name == None:
            self.curr_instance_name = Unum.compute_instance_name(self.name, input_payload)

        return self.curr_instance_name



    @staticmethod
    def compute_instance_name(function_name, input_payload):
        '''Given a function's name and its input payload, compute its instance
        name

        An instance name = {function name}-unumIndex-{indexString}
        '''

        unum_index = Unum.compute_unum_index_str(input_payload)
        if unum_index == None:
            return f'{function_name}'
        else:
            return f'{function_name}-unumIndex-{unum_index}'



    @staticmethod
    def _compute_unum_index_list(fan_out_field):
        '''Given the "Fan-out" field of the input payload, compute the
        unumIndex list.

        Caller needs to make sure that the fan_out_field is not None.
        '''
        if "OuterLoop" not in fan_out_field:
            return [int(fan_out_field["Index"])]

        return [int(fan_out_field["Index"])] + Unum._compute_unum_index_list(fan_out_field["OuterLoop"])



    @staticmethod
    def compute_unum_index_list(input_payload):
        '''Extract the unum index as a list from the input payload

        If the input payload does NOT have a Fan-out field, return []

        The 0th index of the list is the inner-most/most-recent Fan-out Index. For example,
        if the input payload is 

        ```
        {
            "Data": {
                "Source": "http",
                "Value": "foo"
            },
            "Session": "",
            "Fan-out": {
                "Type": "Map",
                "Index": 1,
                "Size": 3,
                "OuterLoop": {
                    "Type": "Map",
                    "Index": 2,
                    "Size": 5
                }
            }
        }
        ```

        this function should return [1,2].

        '''
        if "Fan-out" not in input_payload:
            return []
        else:
            return Unum._compute_unum_index_list(input_payload["Fan-out"])



    @staticmethod
    def compute_unum_index_str(input_payload):
        '''Given an input payload, return the unum index string

        If there is no "Fan-out" field in the input payload, return None.
        Otherwise, return a .-delimited string of integers. For instance,

        if the input payload is 

        ```
        {
            "Data": {
                "Source": "http",
                "Value": "foo"
            },
            "Session": "",
            "Fan-out": {
                "Type": "Map",
                "Index": 1,
                "Size": 3,
                "OuterLoop": {
                    "Type": "Map",
                    "Index": 2,
                    "Size": 5
                }
            }
        }
        ```

        this function should return 1.2

        if the input pyaload is 

        ```
        {
            "Data": {
                "Source": "http",
                "Value": "foo"
            },
            "Session": "",
            "Fan-out": {
                "Type": "Map",
                "Index": 1,
                "Size": 3
            }
        }
        ```

        this function should return 1

        '''
        unum_index_list = Unum.compute_unum_index_list(input_payload)

        if unum_index_list == []:
            return None
        else:
            return functools.reduce(lambda l, elem: l+ '.'+str(elem), unum_index_list, '')[1:]



    @staticmethod
    def expand_name(name, input_payload):
        '''Expand names in the Fan-in Values field of the *unum config* by
        replacing unum variables with runtime values.

        Note: the names are expanded from the invoker's perspective based on
        the invoker's input payload before any Next Payload Modifier runs.
        '''
        ret = name

        if "$0" in ret:
            ret = ret.replace("$0", str(input_payload["Fan-out"]["Index"]))

        if "$1" in ret:
            ret = ret.replace("$1", str(input_payload["Fan-out"]["OuterLoop"]["Index"]))

        if "$2" in ret:
            ret = ret.replace("$2", str(input_payload["Fan-out"]["OuterLoop"]["OuterLoop"]["Index"]))

        if "$3" in ret:
            ret = ret.replace("$2", str(input_payload["Fan-out"]["OuterLoop"]["OuterLoop"]["OuterLoop"]["Index"]))

        return ret



    def _generate_session(self, input_payload):
        '''Generate an unum invocation session

        Each unum workflow invocation is assigned a unique session ID. The
        session ID is implemented as uuid4 strings. All function instances
        that are part of a workflow invocation share the same session ID.

        Session ID is also used when functions write to intermediary data
        stores. Outputs that are part of the same workflow invocation have
        file names whose prefix is the session ID.

        For instance, with s3, file names are
        {session}/{function-output-name}-output.json. With DynamoDB, item
        names are {session}/{function-outpput-name}-output

        Only the entry function of a unum workflow generates session IDs.
        Entry functions have "Start": True in their unum config. Downstream
        functions get their session ID from their input payload (see
        _extract_session()).

        This function has a input_payload input parameter just to match the
        signature of _extract_session().

        This API is lift from the ds library because session naming is a unum
        design choice. If the session ID implementation depends on the type of
        the data store used, can always add the necessary API in the ds
        library and call it here.
        '''
        if self.curr_session == None:
            if "Session" not in input_payload:
                self.curr_session = str(uuid.uuid4()) # NOTE: used for all data stores
            else:
                self.curr_session = input_payload["Session"]
        
        return self.curr_session



    def _extract_session(self, input_payload):
        if self.curr_session == None:
            self.curr_session = input_payload["Session"]
        
        return self.curr_session



    def cleanup(self):
        self.curr_session = None
        self.curr_instance_name = None
        self.curr_next_payload_fanout = None
        self.curr_unumIndex_str = None
        self.curr_unumIndex_list = None
        self.previous_checkpoint = False
        self.my_gc_tasks = None
        self.my_outgoing_edges = None



    def __str__(self):
        return f'''Name: {self.name},
        Platform: {self.platform},
        Checkpoint: {self.checkpoint},
        Debug: {self.debug},
        Start: {self.entry_function},
        Data store: {self.ds.name} [{self.ds.my_type}],

        Instance name: {self.curr_instance_name}
        Session: {self.curr_session}
        '''

    # def _str_continuations(self):
    #     ret = '[\n'
    #     for c in self.cont_list:
    #         ret = f'{ret}{str(c)}\n'

    #     ret = f'{ret}]'
    #     return ret



class UnumContinuationInputType(Enum):
    SCALAR = 1
    MAP = 2
    FAN_IN = 3



class UnumContinuation(object):

    def __init__(self, function_name, input_type, conditional, invoker, datastore_type, datastore, parallel_index=-1, parallel_size=0,debug=False):
        '''Given the "Name", "InputType", "Conditional" from the "Next" field
        of a unum config, create a UnumContinuation object

        This function creates a single UnumContinuation object. If the "Next"
        field is an array of multiple continuations, call this on each item.

        The run() API of an UnumContinuation object only executes that
        particular continuation. It does not set up any context across
        multiple continuations, such as fan-in context.

        In the current version, Next Payload Modifiers is a function-level
        config, not a continuation-granularity config. Therefore, a
        UnumContinuation object cannot execute Next Payload Modifiers. In
        fact, the run() API expects the metadata for the next payload to be
        passed in. See _run_scalar(), _run_map() and _run_fan_in() for
        examples. And see run_continuation() API in the Unum class on how
        continuation run() API is called. See run_next_payload_modifiers() API
        in the unum class on how Next Payload Modifiers are executed.

        When the "Next" field of unum config is a list, UnumContinuation
        objects are created with a `parallel_index` parameter that equal to
        its index in the "Next" list. This is used by _run_scalar() to execute
        parallel fan-out. It can also be potentially used by _run_fan_in()
        when we support multiple fan-in continuations in the "Next" field. But
        right now, not supported. _run_map() ignores `parallel_index` because
        map already adds a "Fan-out" field to the runtime metadata in the
        payload.

        @param function_name str "Name" field
        @param input_type str or dict "InputType" field
        '''
        self.function_name = function_name
        self.invoker = invoker
        self.conditional = conditional
        self.datastore = datastore
        self.debug=debug

        if input_type == 'Scalar':
            self.input_type = UnumContinuationInputType.SCALAR
            self.run = self._run_scalar
            self.parallel_index=parallel_index
            self.parallel_size=parallel_size
        elif input_type == 'Map':
            self.input_type = UnumContinuationInputType.MAP
            self.run = self._run_map
        elif isinstance(input_type, dict) and 'Fan-in' in input_type:
            self.input_type = UnumContinuationInputType.FAN_IN
            self.fan_in_values = input_type['Fan-in']['Values']
            # self.fan_in_wait = input_type['Fan-in']['Wait']
            self.run = self._run_fan_in
            # self.parallel_index=parallel_index
            # self.parallel_size=parallel_size
        else:
            raise ValueError(f'Unknown InputType: {input_type}')



    def __str__(self):
        return f'''Name: {self.function_name},
        Type: {self.input_type},
        Conditional: {self.conditional}'''



    def check_conditional(self, user_function_output, input_payload, unum_index_list):
        '''Check if the conditionals are true or false

        Example conditionals:

            $0 < $size-1

            $0 > 0

            $0 == 1

        All unum variables are from the perspective of this function, not that
        of the continuation that will be invoked. Therefore, the values of the
        unum variables come from the input payload of this function (the
        invoker) *before* any Next Payload Modifiers execute.

        '''
        # Need to replace all references with the actual value, not just the
        # variable name

        if self.conditional == None:
            return True

        cond = self.conditional

        if "$size" in cond:
            cond = cond.replace("$size", str(input_payload["Fan-out"]["Size"]))
        if "$0" in cond:
            cond = cond.replace("$0", str(unum_index_list[0]))
        if "$1" in cond:
            cond = cond.replace("$1", str(unum_index_list[1]))
        if "$2" in cond:
            cond = cond.replace("$1", str(unum_index_list[2]))

        if "$ret" in cond:
            # TODO: Depending on the return value types that we want to support,
            # we might need a more complex conversion than simply calling `str()`.
            # See the Step Functions Choice state for the types and comparison
            # operators that they support.

            if isinstance(user_function_output,str):
                cond = cond.replace("$ret", f"'{user_function_output}'")
            else:
                uerror(f'Unsupported user function return value type for Conditional')
                return False

        # raise IOError(f'{cond}, {type(cond)}; {cont["Conditional"]}')

        # print(f"[check_conditional()] The conditional string to be eval: {cond} and it's {eval(cond)}")
        
        return eval(cond)



    def compute_payload_metadata(self, input_payload, user_function_output, post_modifier_metadata):
        '''Given my input payload and my user code results, compute the input
        payload metadata of this continuation

        "Input payload metadata" refers to the input payload less the actual
        data to user code.

        If this continuation will not be invoked (e.g., due to a false
        conditional), return None.

        Map continuations will return a list of payloads (dictionaries).

        '''
        if self.check_conditional(user_function_output, input_payload, Unum.compute_unum_index_list(input_payload)) == False:
            return None

        if self.input_type == UnumContinuationInputType.SCALAR:
            payload = {}
            if self.parallel_size > 1:
                payload["Fan-out"] = {
                    "Type": "Parallel",
                    "Index": self.parallel_index,
                    "Size": self.parallel_size
                }

            for f in post_modifier_metadata:
                if post_modifier_metadata[f] != None:
                    if f == "Fan-out" and "Fan-out" in payload:
                        payload["Fan-out"]["OuterLoop"] = post_modifier_metadata[f]
                    else:
                        payload[f] = post_modifier_metadata[f]

            return payload

        elif self.input_type == UnumContinuationInputType.FAN_IN:
            payload = {}
            for f in post_modifier_metadata:
                if post_modifier_metadata[f] != None:
                    if f == "Fan-out" and "Fan-out" in payload:
                        payload["Fan-out"]["OuterLoop"] = post_modifier_metadata[f]
                    else:
                        payload[f] = post_modifier_metadata[f]

            return payload

        elif self.input_type == UnumContinuationInputType.MAP:
            ret = []

            for i, d in enumerate(user_function_output):
                payload = {
                    "Fan-out": {
                        "Type": "Map",
                        "Index": i,
                        "Size": len(user_function_output)
                    }
                }

                for f in post_modifier_metadata:
                    if post_modifier_metadata[f] != None:
                        if f == "Fan-out":
                            payload["Fan-out"]["OuterLoop"] = post_modifier_metadata[f]
                        else:
                            payload[f] = post_modifier_metadata[f]

                ret.append(payload)

            return ret

        else:
            print(f'Unknown contintuation type: {self.input_type}')



    def _run_scalar(self, user_function_output, session, next_payload_metadata, input_payload, unum_index_list, **kwargs):
        '''Run scalar continuation

        `user_function_output` is sent as a scalar to the continuation
        function, i.e., payload["Data"]["Value"] =
        json.dumps(user_function_output)

        `user_function_output` can be any json serializable value.

        Scalar continuations do NOT require writing the data to an
        intermediary data store. Therefore, payload["Data"]["Source"] is
        always "http"

        Unless there is Next Payload Modifiers, scalar continuations do not
        require any modifications to the metadata. In other words, the
        constructed payload for continuation can inherit the metadata from the
        input payload of the invoker.

        From an orchestration standpoint, _run_scalar() implements two types
        of orchestrations:

        1. chaining
        2. parallel fan-out

        To specify a parallel fan-out, a function's config needs to have a
        list of continuations whose "InputType" is "Scalar" and its "Parallel"
        field set to true. For each continuation, the function (invoker) will
        add a "Fan-out" field into its input payload. The "Size" will be the
        total number of continuations whose "InputType" is "Scalar" and
        "Parallel" is true. The "Index" will be its order in the list
        counting only those continuations whose "InputType" is "Scalar" and
        "Parallel" is true. 

        Note the "Size" field does not affect the fan-in step that might
        happen downstream in the case of parallel fan-out. This is unlike the
        Map fan-out and fan-in where the fan-in Values could be specified with
        a wildcard * which depends on the Size field in the input payload.

        To specify a chaining continuation, the continuation must have
        "InputType" as "Scalar" and either "Parallel" not specified at all or
        set to False. Note that the "Next" field of a function config can be a
        list of multiple continuations whose "InputType" is "Scalar" and
        "Parallel" is False, in which case, we just have multiple chaining,
        and not parallel fan-out. In practice, this means that the invoker
        will NOT add a Fan-out field into the input payload of the
        continuation.

        Scalar continuations that perform parallel fan-outs are created with
        the `parallel_index` and `parallel_size` parameters (see the
        __init__() API of UnumContinuation class).
        '''
        # print(f'[RunScalar] To execute Scalar continuation {self.function_name}')
        if self.check_conditional(user_function_output, input_payload, unum_index_list) == False:
            return

        # print(f'[RunScalar] Executing Scalar continuation {self.function_name}')

        payload = {
            "Data": {
                "Source": "http",
                "Value": user_function_output # will be serialized once together with the payload by invoker.invoke()
            },
            "Session": session
        }

        if self.parallel_size > 1:
            # if there's only one continuation in the list, it is a chain.
            payload["Fan-out"] = {
                "Type": "Parallel",
                "Index": self.parallel_index,
                "Size": self.parallel_size
            }

        for f in next_payload_metadata:
            if next_payload_metadata[f] != None:
                if f == "Fan-out" and "Fan-out" in payload:
                    payload["Fan-out"]["OuterLoop"] = next_payload_metadata[f]
                else:
                    payload[f] = next_payload_metadata[f]

        payload['GC'] = kwargs['gc']

        if self.debug:
            t1 = time.perf_counter_ns()
            ret = self.invoker.invoke(self.function_name, payload)
            t2 = time.perf_counter_ns()

            print(f'Invoking {self.function_name} with payload {payload}')
            print(f'[INVOKER invoke()]{t2-t1}')

            return ret
        else:
            return self.invoker.invoke(self.function_name, payload)



    def _run_map(self, user_function_output, session, next_payload_metadata, input_payload, unum_index_list, **kwargs):
        '''Run Map continuation

        user_function_output needs to be a list.


        '''
        # print(f'[RunMap] To execute Map continuation {self.function_name}')
        if self.check_conditional(user_function_output, input_payload, unum_index_list) == False:
            return

        # print(f'[RunMap] Executing Map continuation {self.function_name}')

        if isinstance(user_function_output, list) == False:
            # raise ValueError(f'Map continuations expect user function output to be a list')
            print(f'[Error] Map continuations expect user function output to be a list. Returning without executing map continuation.')
            return

        size = len(user_function_output)

        for i,d in enumerate(user_function_output):
            payload = {
                "Data": {
                    "Source": "http",
                    "Value": d # will be serialized once together with the payload by invoker.invoke()
                },
                "Session": session,
                "Fan-out": {
                    "Type": "Map",
                    "Index": i,
                    "Size": size
                }
            }

            for f in next_payload_metadata:
                if next_payload_metadata[f] != None:
                    if f == "Fan-out":
                        payload["Fan-out"]["OuterLoop"] = next_payload_metadata[f]
                    else:
                        payload[f] = next_payload_metadata[f]

            payload['GC'] = kwargs['gc']

            if self.debug:
                print(f'Invoking {self.function_name} with payload {payload}')

            self.invoker.invoke(self.function_name, payload)



    def _run_fan_in(self, user_function_output, session, next_payload_metadata, input_payload, unum_index_list, **kwargs):
        '''Run fan-in

        This function guarantees the following semantics:

            1. Only invoke the aggregation function when all its inputs are
               ready in the intermediary data store

            2. In the absence of faults, only one of the branches will invoke
               the aggregation function

        All branches need to have configurations with

            1. "Checkpoint: True"

            2. the exact same Fan-in continuation where the "Values" are
               listed in the same order

        Functions with a Fan-in continuation might have a "Pop" Next Payload
        Modifier. Therefore, the `next_payload_metadata` parameter may not
        have the "Fan-out" field for this function and we need the
        input_payload for the Fan-out metadata.


        '''
        if self.check_conditional(user_function_output, input_payload, unum_index_list) == False:
            return

        # compute the aggregation function's instance name based on the input payload
        payload = {}
        for f in next_payload_metadata:
            if next_payload_metadata[f] != None:
                if f == "Fan-out" and "Fan-out" in payload:
                    payload["Fan-out"]["OuterLoop"] = next_payload_metadata[f]
                else:
                    payload[f] = next_payload_metadata[f]



        aggregation_function_instance_name = Unum.compute_instance_name(self.function_name, payload)

        my_index = unum_index_list[0]

        branch_instance_names = self.expand_all_fan_in_value_names(unum_index_list, input_payload)

        num_branches = len(branch_instance_names)

        if self.datastore.fanin_sync_ready(session, aggregation_function_instance_name, my_index, num_branches):
            payload['Data'] = {'Source': self.datastore.my_type, 'Value': branch_instance_names}
            payload['Session'] = session

            if self.debug:
                print(f'[DEBUG] Invoking {self.function_name} with {payload}')

            self.invoker.invoke(self.function_name, payload)
        else:
            # fan-in not ready. just return
            pass



    def expand_all_fan_in_value_names(self, unum_index_list, input_payload):
        '''Expand and return the names of self.fan_in_values
        '''
        expanded_names = []

        for n in self.fan_in_values:
            tmp = UnumContinuation.expand_name(n, input_payload, unum_index_list, expand_star=True)

            if isinstance(tmp, list):
                expanded_names = expanded_names+tmp
            else:
                expanded_names.append(tmp)
    
        return expanded_names

    # def _dynamodb_expanded_name_post_processing(self, expanded_names_counter, input_payload):
    #     '''Expand the *
    #     '''
    #     expanded_names = []
    #     for n in expanded_names_counter:

    #         tmp = UnumContinuation.expand_name(n, input_payload, expand_star=True)

    #         if isinstance(tmp, list):
    #             expanded_names = expanded_names+tmp
    #         else:
    #             expanded_names.append(tmp)
    
    #     return expanded_names



    def _dynamodb_fan_in_check_ready(self, session, unum_index_list, input_payload):
        '''Return whether fan-in values are ready

        Expand the names in self.fan_in_values without expanding the * to get
        the counter name. Increment the counter and atomically get the value
        after the update. Then count.

        For Map fan-in (self.fan_in_values with *), the target count is the
        fan-out size.

        For other fan-ins (parallel fan-ins or partial fan-ins where the
        fan-in values do not have *), the target count is the length of the
        list after expanding.

        All functions that are part of a Fan-in need to have the same Fan-in
        continuation in their config. If one of them doesn't correctly have a
        Fan-in continuation in its config, the _run_fan_in() function won't
        execute and that function will never increment the counter, which to
        the other fan-out functions means that the function never completes.

        Counter is uniquely named by

            1. Map fan-out (where the "Fan-in" field of the CONFIG is one name
               with *):
               {session}/{fan_in_value_function_name}(-unumIndex-*)-counter

               For instance, if A maps to B's and fan-in to C, all B's will
               write to {session}/B-unumIndex-*-counter.

               If A maps to B's and each B maps to C's and C fan-in to D and D
               fan-in to E, all C's will write to
               {session}/C-unumIndex-$1.*-counter, where $1 identifies which B
               performed the map fan-out to C. And all D's will write to
               {session}/D-unumIndex-*-counter

            2. Parallel fan-out (where the "Fan-in" field of the CONFIG is a
               list of multiple names) :{session}/{all_expanded_names}-counter

               For instance, if A fan out to B and C and B and C fan in to D,
               B and C will write to
               {session}/{B-unumIndex-0-C-unumIndex-1-counter}

            Note: In nested parallel fan-out, there are scenarios where we can
            use the * pattern. However, we need to be consistent because
            counter name expansion does NOT expand *. See wrapper_test.py
            Nested Parallel Fan-in for an example.

        '''
        expanded_names_no_star = [UnumContinuation.expand_name(v, input_payload, unum_index_list) for v in self.fan_in_values]
        expanded_names = self.expand_all_fan_in_value_names(unum_index_list, input_payload)

        # print(f"[_dynamodb_fan_in_check_ready()] expanded_names_no_star: {expanded_names_no_star}")
        # print(f"[_dynamodb_fan_in_check_ready()] expanded_names: {expanded_names}")

        return self.datastore.check_fan_in_complete(session, expanded_names_no_star, len(expanded_names))
            


    def _s3_fan_in_check_ready_wait(self, session, next_payload_metadata, input_payload):
        '''
        
        If I'm not the last fan-out function (i.e., $0 == $size-1), just
        return False. If I am, wait until all fan-out functions complete and
        return True.

        If timeout, raise exception.
        '''
        last_fan_in = self.fan_in_values[-1]

        pass



    def _s3_expanded_name_post_processing(self, expanded_names, input_payload):
        '''When checking if fan-in values are ready over s3, the names need to
        be fully expanded on the first run. Therefore, postporcessing simply
        returns the expanded names.
        '''
        return expanded_names


    @staticmethod
    def expand_name(name, input_payload, unum_index_list, expand_star=False):
        '''Expand a single name in the Fan-in Values field of the unum config
        by replacing unum variables with runtime values.

        The difference from the Unum.expand_name() is that we're skipping
        expanding the * glob pattern.

        Note: the names are expanded from the invoker's perspective based on
        the invoker's input payload before any Next Payload Modifier runs.
        '''
        ret = name

        # replace the positional variables (e.g., $0, $1, $2) with Fan-out Index values
        # XXX: the use '\$.' has the limitation of up to $9.
        positionals = re.findall('\$.', ret)
        for p in positionals:
            ret = ret.replace(p, str(unum_index_list[int(p[1])]))

        # if "$0" in ret:
        #     ret = ret.replace("$0", str(input_payload["Fan-out"]["Index"]))

        # if "$1" in ret:
        #     ret = ret.replace("$1", str(input_payload["Fan-out"]["OuterLoop"]["Index"]))

        # if "$2" in ret:
        #     ret = ret.replace("$2", str(input_payload["Fan-out"]["OuterLoop"]["OuterLoop"]["Index"]))

        # if "$3" in ret:
        #     ret = ret.replace("$2", str(input_payload["Fan-out"]["OuterLoop"]["OuterLoop"]["OuterLoop"]["Index"]))

        # computations involving positional variables (e.g., ($0-1), ($1+1).$0 )
        exp_np = re.findall('\((.*?)\)', ret)
        exp_wp = re.findall('\(.*?\)', ret)
        for i in range(0,len(exp_np)):
            ret = ret.replace(exp_wp[i], str(eval(exp_np[i])))

        # If * is in the name, expand it based on the innermost Fan-out Size (i.e., input_payload["Fan-out"]["Size"])
        # NOTE: * currently only works on the $0 place
        if expand_star:
            if "*" in ret:
                tmp = ret
                ret = [tmp.replace("*",str(i)) for i in range(input_payload["Fan-out"]["Size"])]

        return ret


def noop(*args, **kws):
    return None


def get_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def http_invoke_async(function, data):
    '''
    @param function string function arn
    @param data dict
    '''
    response = lambda_client.invoke(
        FunctionName=function,
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(data),
    )
    ret = response['Payload'].read()

    return

def uerror(session, name, msg):
    ''' Write error message to datastore/session_context/errors/
    '''
    if "Debug" in config and config["Debug"] == True:
        my_return_value_store.write_error(session, name, msg)

