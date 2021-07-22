# Execution Guarantee

A->B.

1. what if A crashes before user function code executes
2. what if A crashes while user function code executes
3. what if A crashes after user function code executes but before invoking B
4. what if B fails to start
5. what if B crashes before user function code executes
6. what if B crashes while user function code executes
7. what if B crashes after user function code execute but before completing



A->[ Bs ]

What if A crashes half way through invoking the Bs.



A->[ Bs ]->C

If only one of the B instances waits for all other B instances and invokes C,

1. what if the invoker B crashes before invoking C
2. Can I make sure C is invoked at least once?

If any of the B instances can invoke C,

1. what if multiple B instances invoke C? 
   1. Can I make sure C is invoked at most once? exactly once?
   2. Or am I doomed to ask C to be idempotent
2. Does writing the runtime in such a way that any of the B instances can invoke C provide at least once guarantee?



What if C starts and cannot see all of B's outputs in the data store?