#!/usr/bin/python3

from zocp import ZOCP
import socket
import logging
import time

class SubscribableNode(ZOCP):
    # Constructor
    def __init__(self, nodename=""):
        self.nodename = nodename
        self.float_value = 1.0
        self.count_value = 0
        self.counter_active = False
        self.string_value = ''
        self.interval = 1.0
        self.loop_time = 0
        super(SubscribableNode, self).__init__()


    def run(self):
        self.set_name(self.nodename)
        self.register_float("My Float", self.float_value, 'rwe')
        self.register_bool("Counter active", self.counter_active, 'rw')
        self.register_float("Counter", self.count_value, 're')
        self.register_float("Interval", self.count_value, 'rw', .01, 10, 0.1)
        self.register_string("My String", self.string_value, 'rwe')
        self.start()

        while True:
            try:
                self.run_once(0)
                if self.counter_active and time.time() > self.loop_time:
                    self.loop_time = time.time() + self.interval
                    self.on_timer()
            except (KeyboardInterrupt, SystemExit):
                break

        z.stop()


    def on_modified(self, peer, name, data, *args, **kwargs):
        if self._running and peer:
            for key in data:
                if 'value' in data[key]:
                    self.receive_value(key)

                
    def on_peer_signaled(self, peer, name, data, *args, **kwargs):
        if self._running and peer:
            self.receive_value(data[0])


    def receive_value(self, key):
        new_value = self.capability[key]['value']

        if key == "My Float":
            if new_value != self.float_value:
                self.float_value = new_value
        if key == "My String":
            if new_value != self.string_value:
                self.string_value = new_value
        if key == "My Float":
            if new_value != self.interval:
                self.interval = new_value
                new_loop = time.time() + self.interval
                if new_loop < self.loop_time:
                    self.loop_time = new_loop
        if key == "Counter active":
            if new_value != self.counter_active:
                self.counter_active = new_value
                if new_value:
                    self.loop_time = time.time() + self.interval


    def on_timer(self):
        if self.counter_active:
            self.count_value += 1
            self.emit_signal('Counter', self.count_value)
    
        
if __name__ == '__main__':
    zl = logging.getLogger("zocp")
    zl.setLevel(logging.DEBUG)

    z = SubscribableNode("subscribable@%s" % socket.gethostname())
    z.run()
    z = None
    print("FINISH")
