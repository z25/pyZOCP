#!/usr/bin/python

from zocp import ZOCP
import logging

if __name__ == '__main__':
    zl = logging.getLogger("zocp")
    zl.setLevel(logging.DEBUG)

    z = ZOCP()
    z.set_name("ZOCP-Test")
    z.register_bool("myBool", True, 'rw')
    z.register_float("myFloat", 2.3, 'rw', 0, 5.0, 0.1)
    z.register_int('myInt', 10, access='rw', min=-10, max=10, step=1)
    z.register_percent('myPercent', 12, access='rw')
    z.start()
    z.run()
    print("FINISH")
