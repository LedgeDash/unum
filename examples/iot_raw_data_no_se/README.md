Given the aggregator and hvac_controller functions written in the style of
`aggregator_raw_data_no_se` and `hvac_controller_raw_data_no_se` respectively,
how do we compose them to form an application where a power consumption
monitor sends data to the aggregator to compute some aggregate statistics and
the hvac_controller uses those statistics to decide whether to turn the HVAC
system down.

![IoT_HVAC](https://github.com/LedgeDash/unum-compiler/blob/main/examples/iot_raw_data_no_se/IoT_HVAC.png)



