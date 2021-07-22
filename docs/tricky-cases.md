# Tricky Cases

## Nested Parallel Fan-in/out

![nested-parallel](D:\Dropbox (Princeton)\Dev\unum-compiler\docs\assets\nested-parallel.jpg)

Blue D has to be able specify that it waits for the blue E in D's unum-config.

Blue D's output has to have a different name from orange D's output.



## Branching in Fan-out

![runtime-io-example-map-branch](D:\Dropbox (Princeton)\Dev\unum-compiler\docs\assets\runtime-io-example-map-branch.jpg)

The difficulty comes from ending an iteration on different functions. Because the fan-in information are distributed, it is difficult for M to figure out that it needs to wait for some H's and some I's. 

If H and I both invoke a same function as next stage, the problem goes away:

![runtime-io-example-map-branch-endOnSame](D:\Dropbox (Princeton)\Dev\unum-compiler\docs\assets\runtime-io-example-map-branch-endOnSame.jpg)

Therefore, if given a Step Functions definition where the last stage of iteration involves a branch, the front-end compiler can add an additional NOP function to all branches before the fan-in.