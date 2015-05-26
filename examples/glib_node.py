import gi
from gi.repository import GObject

from zocp import ZOCP
import zmq

GObject.threads_init()
loop = GObject.MainLoop()

z = ZOCP("GLibTest")
z.register_percent('myPercent', 12, access='rw')

def zocp_handle(*args, **kwargs):
    z.run_once()
    return True

GObject.io_add_watch(
        z.inbox.getsockopt(zmq.FD), 
        GObject.PRIORITY_DEFAULT, 
        GObject.IO_IN, zocp_handle
    )
z.start()
try:
    loop.run()
except Exception as e:
    print(e)
finally:
    z.stop()
