import unittest
import zocp
import zmq
import time
import sys


if sys.version.startswith('3'):
    unicode = str


class ZOCPTest(unittest.TestCase):
    
    def setUp(self, *args, **kwargs):
        ctx = zmq.Context()
        self.node1 = zocp.ZOCP("node1", ctx=ctx)
        self.node1.set_header("X-TEST", "1")
        self.node2 = zocp.ZOCP("node2", ctx=ctx)
        self.node2.set_header("X-TEST", "1")
        self.node1.start()
        self.node2.start()
        # give time for nodes to exchange
        time.sleep(1)
    # end setUp

    def tearDown(self):
        self.node1.stop()
        self.node2.stop()
    # end tearDown

    def test_name(self):
        self.assertEqual("node1", self.node1.name())
        self.assertEqual("node2", self.node2.name())
    # end test_name

    def test_peers(self):
        id1 = self.node1.uuid()
        peers = self.node2.peers()

        self.assertIsInstance(peers, list)
        self.assertIn(id1, peers)
    # end test_peers

    def test_peer_address(self):
        id1 = self.node1.uuid()
        id2 = self.node2.uuid()

        self.assertIsInstance(self.node1.peer_address(id2), unicode)
        self.assertIsInstance(self.node2.peer_address(id1), unicode)
    # end test_peer_address

    def test_peer_header_value(self):
        id1 = self.node1.uuid()
        id2 = self.node2.uuid()

        self.assertEqual("1", self.node1.peer_header_value(id2, "X-TEST"))
        self.assertEqual("1", self.node2.peer_header_value(id1, "X-TEST"))
    # end test_peer_header_value

    def test_own_groups(self):
        self.node1.join("TEST")
        self.node2.join("TEST")

        # pyre works asynchronous so give some time to let changes disperse
        time.sleep(0.5)

        self.assertIn("TEST", self.node1.own_groups())
        self.assertIn("TEST", self.node2.own_groups())
    # end test_own_groups

    def test_peer_groups(self):
        self.node1.join("TEST")
        self.node2.join("TEST")

        # pyre works asynchronous so give some time to let changes disperse
        time.sleep(0.5)

        self.assertIn("TEST", self.node1.peer_groups())
        self.assertIn("TEST", self.node2.peer_groups())
    # end test_peer_groups

    def test_get_value(self):
        self.node1.register_float("TestEmitFloat", 1.0, 'rwe')
        self.node2.register_float("TestRecvFloat", 1.0, 'rws')
        self.assertEqual(self.node1.get_value("TestEmitFloat"), 1.0)
        self.assertEqual(self.node2.get_value("TestRecvFloat"), 1.0)
    # end test_get_value

    def test_signal_subscribe(self):
        self.node1.register_float("TestEmitFloat", 1.0, 'rwe')
        self.node2.register_float("TestRecvFloat", 1.0, 'rws')
        # give time for dispersion
        self.node1.run_once()
        self.node2.run_once()
        self.node2.signal_subscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        # give time for dispersion
        time.sleep(0.5)
        self.node1.run_once()
        # subscriptions structure: {Emitter nodeID: {'EmitterID': ['Local ReceiverID']}}
        self.assertIn("TestRecvFloat", self.node2.subscriptions[self.node1.uuid()]["TestEmitFloat"])
        self.assertIn("TestRecvFloat", self.node1.subscribers[self.node2.uuid()]["TestEmitFloat"])
        # unsubscribe
        self.node2.signal_unsubscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        time.sleep(0.5)
        self.node1.run_once()
        self.assertNotIn("TestRecvFloat", self.node2.subscriptions.get(self.node1.uuid(), {}).get("TestEmitFloat", {}))
        self.assertNotIn("TestRecvFloat", self.node1.subscribers.get(self.node2.uuid(), {}).get("TestEmitFloat", {}))

    def test_self_emitter_subscribe(self):
        self.node1.register_float("TestEmitFloat", 1.0, 'rwe')
        self.node2.register_float("TestRecvFloat", 1.0, 'rws')
        # give time for dispersion
        self.node1.run_once(5)
        self.node2.run_once(5)
        self.node1.run_once(5)
        self.node2.run_once(5)
        self.node1.signal_subscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        # give time for dispersion
        self.node2.run_once(5)
        self.node1.run_once(5)
        self.node2.run_once(5)
        self.node1.run_once(5)
        # subscriptions structure: {Emitter nodeID: {'EmitterID': ['Local ReceiverID']}}
        self.assertIn("TestRecvFloat", self.node1.subscribers[self.node2.uuid()]["TestEmitFloat"])
        self.assertIn("TestRecvFloat", self.node2.subscriptions[self.node1.uuid()]["TestEmitFloat"])
        # unsubscribe
        self.node1.signal_unsubscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        #time.sleep(0.5)
        self.node2.run_once(5)
        self.node1.run_once(5)
        self.assertNotIn("TestRecvFloat", self.node2.subscriptions.get(self.node1.uuid(), {}).get("TestEmitFloat", {}))
        self.assertNotIn("TestRecvFloat", self.node1.subscribers.get(self.node2.uuid(), {}).get("TestEmitFloat", {}))

    def test_emit_signal(self):
        self.node1.register_float("TestEmitFloat", 1.0, 'rwe')
        self.node2.register_float("TestRecvFloat", 1.0, 'rws')
        # give time for dispersion
        time.sleep(0.5)
        self.node1.run_once()
        self.node2.signal_subscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        # give time for dispersion
        time.sleep(0.1)
        self.node1.run_once()
        self.node1.emit_signal("TestEmitFloat", 2.0)
        time.sleep(0.1)
        self.node2.run_once()
        self.assertEqual(2.0, self.node2.capability["TestRecvFloat"]["value"])
        # unsubscribe
        self.node2.signal_unsubscribe(self.node2.uuid(), "TestRecvFloat", self.node1.uuid(), "TestEmitFloat")
        time.sleep(0.1)
        self.node1.run_once()
# end ZOCPTest

if __name__ == '__main__':
    import logging
    logger = logging.getLogger("zocp")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    #logger.propagate = False

    unittest.main()
