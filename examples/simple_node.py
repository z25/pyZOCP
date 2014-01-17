#!/usr/bin/python

from zocp import ZOCP

if __name__ == '__main__':
    z = ZOCP()
    z.set_node_name("ZOCP-Test")
    z.register_bool("myBool", True, 'rw')
    z.register_float("myFloat", 2.3, 'rw', 0, 5.0, 0.1)
    z.register_int('myInt', 10, access='rw', min=-10, max=10, step=1)
    z.register_percent('myPercent', 12, access='rw')
    z.run()
    z.stop()
    print("FINISH")
