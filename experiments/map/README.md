This map workflow takes an array as its input. For every element of the array,
it executes one instance of the `F1` function. When all `F1` functions
complete, it invokes one instance of the `Summary` function. The `Summary`
function's input is the `F1` functions' outputs in an array with the same
order as the input array (i.e., the 1st item in `Summary`'s input array is the
output of the `F1` function whose input is the 1st item of the initial
workflow input array).

`F1` function simply reads a local file and returns the file content. We can
increase or decrease `F1`'s runtime and memory footprint by changing the file
size.