#!/usr/bin/python3

from zocp import ZOCP
import socket

class SubscriberNode(ZOCP):
    # Constructor
    def __init__(self, nodename=""):
        self.nodename = nodename
        self.newnodes = []
        self.string_value = ''
        self.count_value = 0
        super().__init__()

    def run(self):
        self.set_node_name(self.nodename)
        self.register_string("My String", self.string_value, 'rw')
        self.register_int("Linked counter", self.count_value, 'r')
        super().run()
        
    def on_peer_enter(self, peer, *args, **kwargs):
        self.newnodes.append(peer)
    
    def on_peer_modified(self, peer, *args, **kwargs):
        if peer in self.newnodes:
            self.newnodes.remove(peer)
            
            peer_capabilities = self.peers[peer]
            if '_name' in peer_capabilities: 
                split_name = peer_capabilities['_name'].split("@",1)
                if(split_name[0] == 'subscribable'):
                    self.peer_subscribe(peer)
                    self.peer_subscribe(peer, 'My String', 'My String')
                    self.peer_subscribe(peer, 'Counter', 'Linked counter')
    
        
if __name__ == '__main__':
    z = SubscriberNode("subscriber@%s" % socket.gethostname())
    z.run()
    z.stop()
    print("FINISH")

