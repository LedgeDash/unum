There are a few different implementations of mapreduce word count.

# Implementation 1 - workflow.py



Input to the `workflow.py` is a list of file pointers.

To demonstrate

1. the unum map construct
2. runtime handles data passing transparently over different data stores
3. fan-in from mappers to an intermediary sort function

step 3 in actual MapReduce is handled by the runtime (see section 3.1 of the
mapreduce paper). This is not meant to be a full implementation of MapReduce
on Lambda; Rather it's the specific word count application. If we can build
the word count application, then we can abstract out original runtime
functions such as sort to build the actual mapreduce runtime.

# Implementation 2 - workflow_equal_mapper_reducer.py

To demonstrate

1. pipeline with nesting map

# Implementation 3 - workflow_splitter.py

In the original MapReduce, the runtime splits data into chunks (see section
3.1 item 1).

