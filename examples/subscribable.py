#!/usr/bin/python

from zocp import ZOCP
import socket
import re
from uuid import UUID
import json

class SubscribableNode(ZOCP):
    # Constructor
    def __init__(self, nodename=""):
        self.nodename = nodename
        super().__init__()

    def run(self):
        self.set_node_name(self.nodename)
        value=1
        self.register_float("Value", value, 'rw')
        super().run()
    
    def on_modified(self, data, peer=None):
        if self._running and peer:            
            modifiedkey = (list(data.keys())[0])
            if modifiedkey == "Value":
                newValue = data['Value']['value']

            if newValue != value:
                value = newValue
                self._on_modified(data=self.capability)
                
    def on_peer_modified(self, peer, data, *args, **kwargs):
        pass
    
    def on_peer_enter(self, peer, *args, **kwargs):
        pass
    
    def on_peer_exit(self, peer, *args, **kwargs):
        pass
    
        
if __name__ == '__main__':
    z = SubscribableNode("subscribable@%s" % socket.gethostname())
    z.run()
    z.stop()
    print("FINISH")
