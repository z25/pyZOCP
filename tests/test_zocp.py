import unittest
import zocp
import zmq
import time

class ZOCPTest(unittest.TestCase):
    
    def setUp(self, *args, **kwargs):
        ctx = zmq.Context()
        self.node1 = zocp.ZOCP(ctx=ctx)
        self.node1.set_header("X-TEST", "1")
        self.node1.set_name("node1")
        self.node2 = zocp.ZOCP(ctx=ctx)
        self.node2.set_header("X-TEST", "1")
        self.node2.set_name("node2")
        self.node1.start()
        self.node2.start()
        # give time for nodes to exchange
        time.sleep(1)
    # end setUp

    def tearDown(self):
        self.node1.stop()
        self.node2.stop()
    # end tearDown

    def test_get_name(self):
        self.assertEqual("node1", self.node1.get_name())
        self.assertEqual("node2", self.node2.get_name())
    # end test_get_name

    def test_get_peers(self):
        id1 = self.node1.get_uuid()
        peers = self.node2.get_peers()

        self.assertIsInstance(peers, list)
        self.assertIn(id1, peers)
    # end test_get_peers

    def test_get_peer_address(self):
        id1 = self.node1.get_uuid()
        id2 = self.node2.get_uuid()

        self.assertIsInstance(self.node1.get_peer_address(id2), str)
        self.assertIsInstance(self.node2.get_peer_address(id1), str)
    # end test_get_peer_address

    def test_get_peer_header_value(self):
        id1 = self.node1.get_uuid()
        id2 = self.node2.get_uuid()

        self.assertEqual("1", self.node1.get_peer_header_value(id2, "X-TEST"))
        self.assertEqual("1", self.node2.get_peer_header_value(id1, "X-TEST"))
    # end test_get_peer_header_value

    def test_get_own_groups(self):
        self.node1.join("TEST")
        self.node2.join("TEST")

        # pyre works asynchronous so give some time to let changes disperse
        time.sleep(0.5)

        self.assertIn("TEST", self.node1.get_own_groups())
        self.assertIn("TEST", self.node2.get_own_groups())
    # end test_get_own_groups

    def test_get_peer_groups(self):
        self.node1.join("TEST")
        self.node2.join("TEST")

        # pyre works asynchronous so give some time to let changes disperse
        time.sleep(0.5)

        self.assertIn("TEST", self.node1.get_peer_groups())
        self.assertIn("TEST", self.node2.get_peer_groups())
    # end test_get_peer_groups

    def test_signal_subscribe(self):
        self.node1.register_float("TestEmitFloat", 1.0, 'rwe')
        self.node2.register_float("TestRecvFloat", 1.0, 'rws')
        # give time for dispersion
        time.sleep(0.5)
        self.node2.signal_subscribe(self.node2.get_uuid(), "TestRecvFloat", self.node1.get_uuid(), "TestEmitFloat")
        # give time for dispersion
        time.sleep(0.5)
        #print(self.node2.subscriptions)
        #print(self.node1.subscribers)
        # {UUID('c2d0f94c-1998-4e7a-87d9-f2b3ff287404'): {'TestEmitFloat': ['TestRecvFloat']}}
        self.assertIn("TestRecvFloat", self.node2.subscriptions[self.node1.get_uuid()]["TestEmitFloat"])
        self.assertIn("TestEmitFloat", self.node1.subscribers[self.node2.get_uuid()]["TestRecvFloat"])

    def test_zfinal(self):
        global inst_count
        inst_count = 1
        self.assertTrue(True)
    # end test_zfinal
# end PyreTest

if __name__ == '__main__':
    inst_count = 0

    try:
        unittest.main()
    except Exception as a:
        print(a)

