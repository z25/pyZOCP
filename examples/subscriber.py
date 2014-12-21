#!/usr/bin/python3

from zocp import ZOCP
import socket
import logging

class SubscriberNode(ZOCP):
    # Constructor
    def __init__(self, nodename=""):
        self.nodename = nodename
        self.string_value = ''
        self.count_value = 0
        super().__init__()

    def run(self):
        self.set_name(self.nodename)
        self.register_string("My String", self.string_value, 'rws')
        self.register_int("Linked counter", self.count_value, 'rs')
        self.start()
        super().run()
        
    def on_peer_enter(self, peer, name, *args, **kwargs):
        split_name = name.split("@",1)
        if(split_name[0] == 'subscribable'):
            self.signal_subscribe(self.get_uuid(), 'My String', peer, 'My String')
            self.signal_subscribe(self.get_uuid(), 'Linked counter', peer, 'Counter')
    
        
if __name__ == '__main__':
    zl = logging.getLogger("zocp")
    zl.setLevel(logging.DEBUG)

    z = SubscriberNode("subscriber@%s" % socket.gethostname())
    z.run()
    print("FINISH")

