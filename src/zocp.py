# Z25 Orchestror Control Protocol
# Copyright (c) 2013, Stichting z25.org, All rights reserved.
# Copyright (c) 2013, Arnaud Loonstra, All rights reserved.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3.0 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library.

from pyre import Pyre
import json
import zmq
import uuid
import logging

logger = logging.getLogger(__name__)

def dict_get(d, keys):
    """
    returns a value from a nested dict
    keys argument must be list

    raises a KeyError exception if failed
    """
    for key in keys:
        d = d[key]
    return d

def dict_set(d, keys, value):
    """
    sets a value in a nested dict
    keys argument must be a list
    returns the new updated dict

    raises a KeyError exception if failed
    """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value

def dict_get_keys(d, keylist=""):
    for k, v in d.items():
        if isinstance(v, dict):
            # entering branch add seperator and enter
            keylist=keylist+".%s" %k
            keylist = dict_get_keys(v, keylist)
        else:
            # going back save this branch
            keylist = "%s.%s\n%s" %(keylist, k, keylist)
            #print(keylist)
    return keylist

# http://stackoverflow.com/questions/38987/how-can-i-merge-union-two-python-dictionaries-in-a-single-expression?rq=1
def dict_merge(a, b, path=None):
    """
    merges b into a, overwites a with b if equal
    """
    if not isinstance(a, dict):
        return b
    if path is None: path = []
    for key in b.keys():
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class ZOCP(Pyre):
    """
    The ZOCP class provides all methods for ZOCP nodes
    
    :param str name: Name of the node, if not given a random name will be created
    """
    def __init__(self, *args, **kwargs):
        super(ZOCP, self).__init__(*args, **kwargs)
        self.subscriptions = {}
        self.subscribers = {}
        self.set_header("X-ZOCP", "1")
        self.peers_capabilities = {} # peer id : capability data
        self.capability = kwargs.get('capability', {})
        self._cur_obj = self.capability
        self._cur_obj_keys = ()
        self._running = False
        # We always join the ZOCP group
        self.join("ZOCP")
        self.poller = zmq.Poller()
        self.poller.register(self.inbox, zmq.POLLIN)

    #########################################
    # Node methods. 
    #########################################
    def set_capability(self, cap):
        """
        Set node's capability, overwites previous
        :param dict cap: The dictionary replacing the previous capabilities
        """
        self.capability = cap
        self._on_modified(data=cap)

    def get_capability(self):
        """
        Return node's capabilities
        :return: The capability dictionary
        """
        return self.capability

    def set_node_location(self, location=[0,0,0]):
        """
        Set node's location, overwites previous
        """
        self.capability['_location'] = location
        self._on_modified(data={'_location': location})

    def set_node_orientation(self, orientation=[0,0,0]):
        """
        Set node's name, overwites previous
        """
        self.capability['_orientation'] = orientation
        self._on_modified(data={'_orientation': orientation})

    def set_node_scale(self, scale=[0,0,0]):
        """
        Set node's name, overwites previous
        """
        self.capability['_scale'] = scale
        self._on_modified(data={'scale': scale})

    def set_node_matrix(self, matrix=[[1,0,0,0],
                                      [0,1,0,0],
                                      [0,0,1,0],
                                      [0,0,0,1]]):
        """
        Set node's matrix, overwites previous
        """
        self.capability['_matrix'] = matrix
        self._on_modified(data={'_matrix':matrix})

    def set_object(self, name=None, type="Unknown"):
        """
        Create a new object on this nodes capability
        """
        if name == None:
            self._cur_obj = self.capability
            self._cur_obj_keys = ()
        if not self.capability.get('objects'):
            self.capability['objects'] = {name: {'type': type}}
        elif not self.capability['objects'].get(name):
            self.capability['objects'][name] = {'type': type}
        else:
            self.capability['objects'][name]['type'] = type
        self._cur_obj = self.capability['objects'][name]
        self._cur_obj_keys = ('objects', name)

    def _register_param(self, name, value, type_hint, access='r', min=None, max=None, step=None):
        self._cur_obj[name] = {'value': value, 'typeHint': type_hint, 'access':access, 'subscribers': [] }
        if min:
            self._cur_obj[name]['min'] = min
        if max:
            self._cur_obj[name]['max'] = max
        if step:
            self._cur_obj[name]['step'] = step
        self._on_modified(data={name: self._cur_obj[name]})

    def register_int(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register an integer variable

        :param str name: the name of the variable as how nodes can refer to it
        :param int value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param int min: minimal value
        :param int max: maximal value
        :param int step: step value for increments and decrements
        
        """
        self._register_param(name, value, 'int', access, min, max, step)

    def register_float(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register a float variable

        :param str name: the name of the variable as how nodes can refer to it
        :param float value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param float min: minimal value
        :param float max: maximal value
        :param float step: step value for increments and decrements
        """
        self._register_param(name, value, 'flt', access, min, max, step)

    def register_percent(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register a percentage variable

        :param str name: the name of the variable as how nodes can refer to it
        :param float value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param float min: minimal value
        :param float max: maximal value
        :param float step: step value for increments and decrements
        """
        self._register_param(name, value, 'percent', access, min, max, step)

    def register_bool(self, name, value, access='r'):
        """
        Register an integer variable

        :param str name: the name of the variable as how nodes can refer to it
        :param bool value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        """
        self._register_param(name, value, 'bool', access)

    def register_string(self, name, value, access='r'):
        """
        Register a string variable

        :param str name: the name of the variable as how nodes can refer to it
        :param str value: the variable value
        :param str access: set the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        """
        self._register_param(name, value, 'string', access)

    def register_vec2f(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register a 2 dimensional vector variable

        :param str name: the name of the variable as how nodes can refer to it
        :param tuple value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param tuple min: minimal value
        :param tuple max: maximal value
        :param tuple step: step value for increments and decrements
        """
        self._register_param(name, value, 'vec2f', access, min, max, step)

    def register_vec3f(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register a three dimensional vector variable

        :param str name: the name of the variable as how nodes can refer to it
        :param tuple value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param tuple min: minimal value
        :param tuple max: maximal value
        :param tuple step: step value for increments and decrements
        """
        self._register_param(name, value, 'vec3f', access, min, max, step)

    def register_vec4f(self, name, value, access='r', min=None, max=None, step=None):
        """
        Register a four dimensional vector variable

        :param str name: the name of the variable as how nodes can refer to it
        :param tuple value: the variable value
        :param str access: the access state of the variable. 'r'=readable, 'w'=writeable, 'e'=signal emitter, 's'=signal sensor
        :param tuple min: minimal value
        :param tuple max: maximal value
        :param tuple step: step value for increments and decrements
        """
        self._register_param(name, value, 'vec4f', access, min, max, step)

    def get_value(self, name):
        """
        Retrieve the current value of a named parameter in the capability tree

        :param str name: the name of the variable as how nodes refer to it
        :return: the value of the named variable

        .. note:
            This is a temporary convenience method
        """
        # TODO: could use dict_get(self.capability, keys)
        # for nested values
        return self.capability[name]['value']

    #########################################
    # Node methods to peers
    #########################################
    def peer_get_capability(self, peer):
        """
        Get the capabilities of peer

        Convenience method since it's the same a calling GET on a peer with no 
        data
        """
        self.peer_get(peer, None)

    def peer_get(self, peer, keys):
        """
        Get items from peer
        """
        msg = json.dumps({'GET': keys})
        self.whisper(peer, msg.encode('utf-8'))

    def peer_set(self, peer, data):
        """
        Set items on peer
        """
        msg = json.dumps({'SET': data})
        self.whisper(peer, msg.encode('utf-8'))

    def peer_call(self, peer, method, *args):
        """
        Call method on peer
        """
        msg = json.dumps({'CALL': [method, args]})
        self.whisper(peer, msg.encode('utf-8'))

    def signal_subscribe(self, recv_peer, receiver, emit_peer, emitter):
        """
        Subscribe a receiver to an emitter

        :param uuid recv_peer: the id of the receiving peer
        :param str receiver: the name of the receiving variable.\
                    If None, no capability on the receiving peer is\
                    updated, but a on_peer_signal event is still fired.
        :param uuid emit_peer: the id of the emitting peer
        :param str emitter: the name the emitter. If None, all\
                    capabilities will emit to the receiver

        .. note::
            A third node can instruct two nodes to subscribe to one another
            by specifying the ids of the peers. The subscription request
            is then sent to the emitter node which in turn forwards the
            subscribtion request to the receiver node.
        """
        if recv_peer == self.uuid():
            # we are the receiver so register the emitter
            peer_subscriptions = {}
            if emit_peer in self.subscriptions:
                peer_subscriptions = self.subscriptions[emit_peer]
            if not emitter in peer_subscriptions:
                peer_subscriptions[emitter] = [receiver]
            elif not receiver in peer_subscriptions[emitter]:
                peer_subscriptions[emitter].append(receiver)
            self.subscriptions[emit_peer] = peer_subscriptions

            # check if the peer capability is known
            if receiver is not None:
                if receiver not in self.peers_capabilities:
                    self.peer_get(recv_peer, {receiver: {}})

        if emit_peer == self.uuid():
            # we are the emitter so register the receiver
            # update subscribers in capability tree
            subscriber = (recv_peer.hex, receiver)
            subscribers = self.capability[emitter]["subscribers"]
            if subscriber not in subscribers:
                subscribers.append(subscriber)
                self._on_modified(data={emitter: {"subscribers": subscribers}})

            peer_subscribers = {}
            if recv_peer in self.subscribers:
                peer_subscribers = self.subscribers[recv_peer]
            if not emitter in peer_subscribers:
                peer_subscribers[emitter] = [receiver]
            elif not receiver in peer_subscribers[emitter]:
                peer_subscribers[emitter].append(receiver)
            self.subscribers[recv_peer] = peer_subscribers
            # we don't need to call the peer subscribed event as we initiated it
            # and we don't know the name
            #self.on_peer_subscribed(recv_peer, name, data)

            msg = json.dumps({'SUB': [emit_peer.hex, emitter, recv_peer.hex, receiver]})
            self.whisper(recv_peer, msg.encode('utf-8'))
            return

        msg = json.dumps({'SUB': [emit_peer.hex, emitter, recv_peer.hex, receiver]})
        self.whisper(emit_peer, msg.encode('utf-8'))

    def signal_unsubscribe(self, recv_peer, receiver, emit_peer, emitter):
        """
        Unsubscribe a receiver from an emitter

        :param uuid recv_peer: the id of the receiving peer
        :param str receiver: the name of the receiving variable, or\
                    None if no receiver was specified when subscribing.
        :param uuid emit_peer: the id of the emitting peer
        :param str emitter: the name the emitter, or None if no emitter\
                    was specified during subscription

        .. note::
            A third node can instruct two nodes to unsubscribe from one another
            by specifying the ids of the peers. The subscription request
            is then sent to the emitter node which in turn forwards the
            subscribtion request to the receiver node.
        """
        if recv_peer == self.uuid():
            # we are the receiver so unregister the emitter
            if (emit_peer in self.subscriptions and
                    emitter in self.subscriptions[emit_peer] and
                    receiver in self.subscriptions[emit_peer][emitter]):
                self.subscriptions[emit_peer][emitter].remove(receiver)
                if not any(self.subscriptions[emit_peer][emitter]):
                    self.subscriptions[emit_peer].pop(emitter)
                if not any(self.subscriptions[emit_peer]):
                    self.subscriptions.pop(emit_peer)

        if emit_peer == self.uuid():
            # we are the emitter so unregister the receiver
            # update subscribers in capability tree
            subscriber = (recv_peer.hex, receiver)
            subscribers = self.capability[emitter]["subscribers"]
            if subscriber in subscribers:
                subscribers.remove(subscriber)
                self._on_modified(data={emitter: {"subscribers": subscribers}})

            if (recv_peer in self.subscribers and
                emitter in self.subscribers[recv_peer] and
                receiver in self.subscribers[recv_peer][emitter]):
                self.subscribers[recv_peer][emitter].remove(receiver)
                if not any(self.subscribers[recv_peer]):
                    self.subscribers.pop(recv_peer)
                elif not any(self.subscribers[recv_peer][emitter]):
                    self.subscribers[recv_peer].pop(emitter)

            #self.on_peer_unsubscribed(peer, name, data)

            msg = json.dumps({'UNSUB': [emit_peer.hex, emitter, recv_peer.hex, receiver]})
            self.whisper(recv_peer, msg.encode('utf-8'))
            return

        msg = json.dumps({'UNSUB': [emit_peer.hex, emitter, recv_peer.hex, receiver]})
        self.whisper(emit_peer, msg.encode('utf-8'))

    def emit_signal(self, emitter, value):
        """
        Update the value of the emitter and signal all subscribed receivers

        :param str emitter: name of the emitting variable
        :param value: the new value
        """
        self.capability[emitter]['value'] = value
        msg = json.dumps({'SIG': [emitter, value]}).encode('utf-8')

        for subscriber in self.subscribers:
            if (None in self.subscribers[subscriber] or
                    emitter in self.subscribers[subscriber]):
                self.whisper(subscriber, msg)


    #########################################
    # ZRE event methods. These can be overwritten
    #########################################
    def on_peer_enter(self, peer, name, headers, *args, **kwargs):
        """
        This method is called when a new peer is discovered
        
        :param uuid peer: the id of the new peer
        :param str name: the name of the new peer
        :param hdrs: any headers of the peer
        """
        logger.debug("ZRE ENTER    :%s: %s" %(self.name(), name))

    def on_peer_exit(self, peer, name, *args, **kwargs):
        """
        This method is called when a peer is exiting
        
        :param uuid peer: the id of the exiting peer
        :param str name: the name of the exiting peer
        """
        logger.debug("ZRE EXIT     :%s: %s" %(self.name(), name))

    def on_peer_join(self, peer, name, grp, *args, **kwargs):
        """
        This method is called when a peer is joining a group
        
        :param uuid peer: the id of the joining peer
        :param str name: the name of the joining peer
        :param str grp: the name of the group the peer is joining
        """
        logger.debug("ZRE JOIN     :%s: %s joined group %s" %(self.name(), name, grp))

    def on_peer_leave(self, peer, name, grp, *args, **kwargs):
        """
        This method is called when a peer is leaving a group
        
        :param uuid peer: the id of the leaving peer
        :param str name: the name of the leaving peer
        :param str grp: the name of the group the peer is leaving
        """
        logger.debug("ZRE LEAVE    :%s: %s left group %s" %(self.name(), name, grp))

    def on_peer_whisper(self, peer, name, data, *args, **kwargs):
        """
        This method is called when a peer is whispering
        
        :param uuid peer: the id of the whispering peer
        :param str name: the name of the whispering peer
        :param data: the data the peer is whispering
        """
        logger.debug("ZRE WHISPER  :%s: %s whispered: %s" %(self.name(), name, data))

    def on_peer_shout(self, peer, name, grp, data, *args, **kwargs):
        """
        This method is called when a peer is shouting
        
        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param str grp: the name of the group the peer is shouting in
        :param data: the data the peer is shouting
        """
        logger.debug("ZRE SHOUT    :%s: %s shouted in group %s: %s" %(self.name(), name, grp, data))

    #########################################
    # ZOCP event methods. These can be overwritten
    #########################################
    #def on_get(self, peer, req):
    #def on_set(self, peer, data):
    #def on_call(self, peer, req):
    #def on_subscribe(self, peer, src, dst):
    #def on_unsubscribe(self, peer, src, dst):

    def on_peer_modified(self, peer, name, data, *args, **kwargs):
        """
        Called when a peer signals that its capability tree is modified.

        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param dict data: changed data, formatted as a partial \
                capability dictionary, containing only the changed \
                part(s) of the capability tree of the node
        """
        logger.debug("ZOCP PEER MODIFIED:%s: %s modified %s" %(self.name(), name, data))

    def on_peer_replied(self, peer, name, data, *args, **kwargs):
        logger.debug("ZOCP PEER REPLIED :%s: %s modified %s" %(self.name(), name, data))

    def on_peer_subscribed(self, peer, name, data, *args, **kwargs):
        """
        Called when a peer subscribes to an emitter on this node.

        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param list data: changed data, formatted as [emitter, receiver]\
              emitter: name of the emitter on this node\
              receiver: name of the receiver on the subscriber
        """
        [emit_peer, emitter, recv_peer, receiver] = data
        if emitter is None:
            logger.debug("ZOCP PEER SUBSCRIBED:%s: %s subscribed to all emitters" %(self.name(), name))
        elif receiver is None:
            logger.debug("ZOCP PEER SUBSCRIBED:%s: %s subscribed to %s" %(self.name(), name, emitter))
        else:
            logger.debug("ZOCP PEER SUBSCRIBED:%s: %s subscribed %s to %s" %(self.name(), name, receiver, emitter))

    def on_peer_unsubscribed(self, peer, name, data, *args, **kwargs):
        """
        Called when a peer unsubscribes from an emitter on this node.

        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param list data: changed data, formatted as [emitter, receiver]\
              emitter: name of the emitter on this node\
              receiver: name of the receiver on the subscriber
        """
        [emit_peer, emitter, recv_peer, receiver] = data
        if emitter is None:
            logger.debug("ZOCP PEER UNSUBSCRIBED:%s: %s unsubscribed from all emitters" %(self.name(), name))
        elif receiver is None:
            logger.debug("ZOCP PEER UNSUBSCRIBED:%s: %s unsubscribed from %s" %(self.name(), name, emitter))
        else:
            logger.debug("ZOCP PEER UNSUBSCRIBED:%s: %s unsubscribed %s from %s" %(self.name(), name, receiver, emitter))

    def on_peer_signaled(self, peer, name, data, *args, **kwargs):
        """
        Called when a peer signals that some of its data is modified.

        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param list data: changed data, formatted as [emitter, value, [sensors1, ...]]\
              emitter: name of the emitter on the subscribee\
              value: value of the emitter\
              [sensor1,...]: list of names of sensors on the subscriber\
                             receiving the signal
        """
        logger.debug("ZOCP PEER SIGNALED:%s: %s modified %s" %(self.name(), name, data))

    def on_modified(self, peer, name, data, *args, **kwargs):
        """
        Called when some data is modified on this node.

        :param uuid peer: the id of the shouting peer
        :param str name: the name of the shouting peer
        :param dict data: changed data, formatted as a partial \
                capability dictionary, containing only the changed\
                part(s) of the capability tree of the node
        """
        if peer:
            if not name:
                name = peer.hex
            logger.debug("ZOCP %s modified by %s with %s" %(self.name(), name, data))
        else:
            logger.debug("ZOCP modified by %s with %s" %("self", data))

    #########################################
    # Internal methods
    #########################################
    def get_message(self):
        # A message coming from a zre node contains:
        # * msg type
        # * msg peer id
        # * group (if group type)
        # * the actual message
        msg = self.recv()
        type = msg.pop(0).decode('utf-8')
        peer = uuid.UUID(bytes=msg.pop(0))
        name = msg.pop(0).decode('utf-8')
        grp=None
        if type == "ENTER":
            # This is giving conflicts when using a poller, in discussion
            #if not self.peer_header_value(peer, "X-ZOCP"):
            #    logger.debug("Node is not a ZOCP node")
            #    return

            if not peer in self.peers_capabilities.keys():
                self.peers_capabilities.update({peer: {}})

            self.peer_get_capability(peer)
            self.on_peer_enter(peer, name, msg)
            return

        elif type == "EXIT":
            if peer in self.subscribers:
                self.subscribers.pop(peer)
            if peer in self.subscriptions:
                self.subscriptions.pop(peer)
            self.on_peer_exit(peer, name, msg)
            if peer in self.peers_capabilities:
                self.peers_capabilities.pop(peer)
            return

        elif type == "JOIN":
            grp = msg.pop(0)
            self.on_peer_join(peer, name, grp, msg)
            return

        elif type == "LEAVE":
            #if peer in self.subscribers:
            #    self.subscribers.pop(peer)
            #if peer in self.subscriptions:
            #    self.subscriptions.pop(peer)
            grp = msg.pop(0)
            self.on_peer_leave(peer, name, grp, msg)
            return

        elif type == "SHOUT":
            grp = msg.pop(0)
            self.on_peer_shout(peer, name, grp, msg)

        elif type == "WHISPER":
            self.on_peer_whisper(peer, name, msg)

        else:
            return

        try:
            msg = json.loads(msg.pop(0).decode('utf-8'))
        except Exception as e:
            logger.error("ERROR:%s: %s in %s, type %s" %(e, msg, type))
        else:
            for method in msg.keys():
                if method   == 'GET':
                    self._handle_GET(msg[method], peer, name, grp)
                elif method == 'SET':
                    self._handle_SET(msg[method], peer, name, grp)
                elif method == 'CALL':
                    self._handle_CALL(msg[method], peer, name, grp)
                elif method == 'SUB':
                    self._handle_SUB(msg[method], peer, name, grp)
                elif method == 'UNSUB':
                    self._handle_UNSUB(msg[method], peer, name, grp)
                elif method == 'REP':
                    self._handle_REP(msg[method], peer, name, grp)
                elif method == 'MOD':
                    self._handle_MOD(msg[method], peer, name, grp)
                elif method == 'SIG':
                    self._handle_SIG(msg[method], peer, name, grp)
                else:
                    try:
                        func = getattr(self, 'handle_'+method)
                        func(msg[method])
                    except:
                        raise Exception('No %s method on resource:%s: %s' %(method,object))

    def _handle_GET(self, data, peer, name, grp=None):
        """
        If data is empty just return the complete capabilities object
        else fetch every item requested and return them
        """
        if not data:
            data = {'MOD': self.get_capability()}
            self.whisper(peer, json.dumps(data).encode('utf-8'))
            return
        else:
            # first is the object to retrieve from
            # second is the items list of items to retrieve
            ret = {}
            for get_item in data:
                ret[get_item] = self.capability.get(get_item)
            self.peer_set(peer, data)
            self.whisper(peer, json.dumps({ 'MOD' :ret}).encode('utf-8'))

    def _handle_SET(self, data, peer, name, grp):
        self.capability = dict_merge(self.capability, data)
        self._on_modified(data, peer, name)

    def _handle_CALL(self, data, peer, name, grp):
        return

    def _handle_SUB(self, data, peer, name, grp):
        [emit_peer, emitter, recv_peer, receiver] = data

        node_id = self.uuid()
        recv_peer = uuid.UUID(recv_peer)
        emit_peer = uuid.UUID(emit_peer)
        if emit_peer != node_id and recv_peer != node_id:
            # subscription requests are always initially send to the
            # emitter peer. Recv_peer can only be matched to our id if
            # a subscription to a receiver is done by the emitter.
            logger.warning("ZOCP SUB     :%s: invalid subscription request: %s" %(self.name(), data))
            return

        if recv_peer != peer:
            # check if this should be forwarded (third party subscription request)
            print(recv_peer, peer, type(recv_peer), type(peer))
            logger.debug("ZOCP SUB     :%s: forwarding subscription request: %s" %(self.name(), data))
            self.signal_subscribe(recv_peer, receiver,emit_peer, emitter)
            return

        if emitter is not None:
            # update subscribers in capability tree
            subscriber = (recv_peer.hex, receiver)
            subscribers = self.capability[emitter]["subscribers"]
            if subscriber not in subscribers:
                subscribers.append(subscriber)
                self._on_modified(data={emitter: {"subscribers": subscribers}})

        peer_subscribers = {}
        if recv_peer in self.subscribers:
            peer_subscribers = self.subscribers[recv_peer]
        if not emitter in peer_subscribers:
            peer_subscribers[emitter] = [receiver]
        elif not receiver in peer_subscribers[emitter]:
            peer_subscribers[emitter].append(receiver)
        self.subscribers[recv_peer] = peer_subscribers

        self.on_peer_subscribed(recv_peer, name, data)
        return

    def _handle_UNSUB(self, data, peer, name, grp):
        [emit_peer, emitter, recv_peer, receiver] = data

        node_id = self.uuid()
        recv_peer = uuid.UUID(recv_peer)
        emit_peer = uuid.UUID(emit_peer)
        if emit_peer != node_id and recv_peer != node_id:
            # unsubscription requests are always initially send to the
            # emitter peer. Recv_peer can only be matched to our id if
            # a subscription to a receiver is done by the emitter.
            logger.warning("ZOCP UNSUB   :%s: invalid unsubscription request: %s" %(self.name(), data))
            return

        if recv_peer != peer:
            # check if this should be forwarded (third party unsubscription request)
            logger.debug("ZOCP UNSUB   :%s: forwarding unsubscription request: %s" %(self.name(), data))
            self.signal_unsubscribe(recv_peer, receiver, emit_peer, emitter)
            return

        if emitter is not None:
            # update subscribers in capability tree
            subscriber = (recv_peer.hex, receiver)
            subscribers = self.capability[emitter]["subscribers"]
            if subscriber in subscribers:
                subscribers.remove(subscriber)
                self._on_modified(data={emitter: {"subscribers": subscribers}})

        if (recv_peer in self.subscribers and
                emitter in self.subscribers[recv_peer] and
                receiver in self.subscribers[recv_peer][emitter]):
            self.subscribers[recv_peer][emitter].remove(receiver)
            if not any(self.subscribers[recv_peer][emitter]):
                self.subscribers[recv_peer].pop(emitter)
            if not any(self.subscribers[recv_peer]):
                self.subscribers.pop(recv_peer)

            self.on_peer_unsubscribed(peer, name, data)
        return

    def _handle_REP(self, data, peer, name, grp):
        return

    def _handle_MOD(self, data, peer, name, grp):
        self.peers_capabilities[peer] = dict_merge(self.peers_capabilities.get(peer), data)
        self.on_peer_modified(peer, name, data)

    def _handle_SIG(self, data, peer, name, grp):
        [emitter, value] = data
        if emitter in self.peers_capabilities[peer]:
            self.peers_capabilities[peer][emitter].update({'value': value})

        if peer in self.subscriptions:
            subscription = self.subscriptions[peer]
            if emitter in subscription:
                receivers = subscription[emitter]

                # add a list of sensors on this node receiving the signal
                data.append(receivers)

                for receiver in receivers:
                    # propagate the signal if it changes the value of this node
                    if receiver is not None and self.capability[receiver]['value'] != value:
                        self.emit_signal(receiver, value)

            if None in subscription or emitter in subscription:
                self.on_peer_signaled(peer, name, data)

    def _on_modified(self, data, peer=None, name=None):
        if self._cur_obj_keys:
            # the last key in the _cur_obj_keys list equals 
            # the first in data so skip the last key
            for key in self._cur_obj_keys[::-1]:
                new_data = {}
                new_data[key] = data
                data = new_data
        self.on_modified(peer, name, data)

        if len(data) == 1:
            # if the only modification is a value change,
            # emit a SIG instead of a MOD
            name = list(data.keys())[0]
            if len(data[name]) == 1 and 'value' in data[name]:
                msg = json.dumps({'SIG': [name, data[name]['value']]})
                for subscriber in self.subscribers:
                    # no need to send the signal to the node that
                    # modified the value
                    if subscriber != peer and (
                            None in self.subscribers[subscriber] or
                            name in self.subscribers[subscriber]):
                        self.whisper(subscriber, msg.encode('utf-8'))
                data = {}

        if any(data):
            msg = json.dumps({ 'MOD' :data}).encode('utf-8')
            for subscriber in self.subscribers:
                # inform node that are subscribed to one or more
                # updated capabilities that they have changed
                if subscriber != peer and (
                        None in self.subscribers[subscriber] or
                        len(set(self.subscribers[subscriber]) & set(data)) > 0):
                    self.whisper(subscriber, msg)

    def run_once(self, timeout=None):
        """
        Run one iteration of getting ZOCP events

        If timeout is None it will block until an
        event has been received. If 0 it will return instantly

        The timeout is in milliseconds
        """
        self._running = True
        items = dict(self.poller.poll(timeout))
        while(len(items) > 0):
            for fd, ev in items.items():
                if self.inbox == fd and ev == zmq.POLLIN:
                    self.get_message()
            # just q quick query
            items = dict(self.poller.poll(0))

    def run(self, timeout=None):
        """
        Run the ZOCP loop indefinitely
        """
        self._running = True
        while(self._running):
            try:
                items = dict(self.poller.poll(timeout))
                while(len(items) > 0):
                    for fd, ev in items.items():
                        if self.inbox == fd and ev == zmq.POLLIN:
                            self.get_message()
            except (KeyboardInterrupt, SystemExit):
                break
        self.stop()

    #def __del__(self):
    #    self.stop()

if __name__ == '__main__':

    z = ZOCP("ZOCP-Test")
    z.register_bool("zocpBool", True, 'rw')
    z.register_float("zocpFloat", 2.3, 'rw', 0, 5.0, 0.1)
    z.register_int('zocpInt', 10, access='rw', min=-10, max=10, step=1)
    z.register_percent('zocpPercent', 12, access='rw')
    z.run()
    z.stop()
    print("FINISH")
