#!/usr/bin/python3

from zocp import ZOCP
import socket

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
        super().run()
        
    def on_peer_enter(self, peer, name, *args, **kwargs):
        split_name = name.split("@",1)
        if(split_name[0] == 'subscribable'):
            self.peer_subscribe(peer, 'My String', 'My String')
            self.peer_subscribe(peer, 'Counter', 'Linked counter')
    
        
if __name__ == '__main__':
    z = SubscriberNode("subscriber@%s" % socket.gethostname())
    z.run()
    print("FINISH")

