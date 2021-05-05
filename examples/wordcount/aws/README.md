This directory contains several different implementations of MapReduce
wordcount. In all implementations, there is a fixed number of reducers decided
ahead of time by users. A word is shuffled to a reducer by computing
`hashlib.sha256(word) % numReducer`.

A primary goal for all implementations *is to separate component function
logic from orchestration logic*. We can use either Step Functions or
hand-tuned triggers to compose the workflow *without modifying the component
functions*.

The main difference among the versions is how they implement partitioning.
**emitSingleS3** explicitly use an s3 bucket as the intermediary datastore.
Mappers in emitSingleS3 creates an object named `reducer{id}/{word}/{uuid}`
for each word occurrence. The individual files have no contents.

**emitBatchS3** also explicitly use an s3 bucket as the intermediary
datastore. But mappers in emitSingleS3 creates an object named
`reducer{id}/{word}/{uuid}` for each word instead of each word occurrence. The
file contains a list of 1's, one for each occurrence.

Both **emitSingleS3** and **emitBatchS3** perform actual partitioning in
mappers when they call the `emit(word)` function in `mapreduce.py` which is
the MapReduce runtime. In other words, the MapReduce runtime in
**emitSingleS3** and **emitBatchS3** implements partitioning as a local
function (not a Lambda function) that mappers execute and dictates to use s3
in a certain way to achieve the desired partitioning results.

**partitionLambda** treats MapReduce as a client application for Lambda.
Instead of component functions explicitly coordinate data movement via S3 (as
in the case of **emitSingleS3** and **emitBatchS3**), all functions simply
return their results as a JSON object. The partition logic is implemented as a
separate Lambda function that takes the outputs of all mappers as its input. I
use this implementation to explore if we could make function oblivious to how
data is passed but the underlying system moves data efficiently. For example,
a desired result is to avoid having the partition function read in the entire
output from all mappers, which is O(corpus).

# A note on Step Functions

Composing with SF when mappers explicitly output to S3 is cumbersome, because
we need to clear the S3 bucket after every invocation. SF doesn't have a way
to create a S3 directory and pass that to each mapper to write to. We could
have a separate frontend Lambda that creates the S3 bucket and then return
that to the Map SF state. Or we could have the client first creating a bucket
and then passing that in the input.

Can we implement with the SF instance as the intermediary datastore? This will
free us from clearing the S3 bucket or having another Lambda to create an
invocation-specific bucket.

Does this force us to have a singleton `partition` function that reads in
O(corpus)?

I use **partitionLambda** to explore this question.