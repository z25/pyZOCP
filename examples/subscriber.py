#!/usr/bin/python

from zocp import ZOCP
import socket


class SubscriberNode(ZOCP):
    # Constructor
    def __init__(self, nodename=""):
        self.nodename = nodename
        super().__init__()

    def run(self):
        self.set_node_name(self.nodename)
        super().run()
        
    def on_peer_enter(self, peer, *args, **kwargs):
        # TODO: find subscribable node
        #print("found node: %s" % peer.nodename)
        self.peer_subscribe(peer, None, None)
        pass

if __name__ == '__main__':
    z = SubscriberNode("subscriber@%s" % socket.gethostname())
    z.run()
    z.stop()
    print("FINISH")

