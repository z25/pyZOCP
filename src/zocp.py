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
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class ZOCP(Pyre):

    def __init__(self, capability={}, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.peers = {} # id : capability data
        self.name = capability.get('_name')
        self.capability = capability
        self._running = False
        # We always join the ZOCP group
        self.join("ZOCP")
        #self.run()

    #########################################
    # Node methods. 
    #########################################
    def set_capability(self, cap):
        """
        Set node's capability, overwites previous
        """
        self.capability = cap
        self.on_modified()

    def get_capability(self):
        """
        Return node's capabilities
        """
        return self.capability

    def set_node_name(self, name):
        """
        Set node's name, overwites previous
        """
        self.capability['_name'] = name
        self.on_modified()

    def get_node_name(self, name):
        """
        Return node's name
        """
        return self.capability.get('_name')

    def set_node_location(self, location=[0,0,0]):
        """
        Set node's location, overwites previous
        """
        self.capability['_location'] = location
        self.on_modified()

    def set_node_orientation(self, orientation=[0,0,0]):
        """
        Set node's name, overwites previous
        """
        self.capability['_orientation'] = location
        self.on_modified()

    def set_node_scale(self, scale=[0,0,0]):
        """
        Set node's name, overwites previous
        """
        self.capability['_scale'] = scale
        self.on_modified()

    def set_node_matrix(self, matrix=[[1,0,0,0],
                                      [0,1,0,0],
                                      [0,0,1,0],
                                      [0,0,0,1]]):
        """
        Set node's matrix, overwites previous
        """
        self.capability['_matrix'] = matrix
        self.on_modified()

    def register_int(self, name, int, access='r', min=None, max=None, step=None):
        """
        Register an integer variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * int: the variable
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': int, 'typeHint': 'int', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

    def register_float(self, name, flt, access='r', min=None, max=None, step=None):
        """
        Register a float variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * int: the variable
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': flt, 'typeHint': 'float', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

    def register_percent(self, name, pct, access='r', min=None, max=None, step=None):
        """
        Register a percentage variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * int: the variable
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': pct, 'typeHint': 'percent', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

    def register_bool(self, name, bl, access='r'):
        """
        Register an integer variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * int: the variable
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        """
        self.capability[name] = {'value': bl, 'typeHint': 'bool', 'access':access }
        self.on_modified()

    def register_string(self, name, s, access='r'):
        """
        Register a string variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * s: the variable
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        """
        self.capability[name] = {'value': s, 'typeHint': 'string', 'access':access }
        self.on_modified()

    def register_vec2f(self, name, vec2f, access='r', min=None, max=None, step=None):
        """
        Register a 2 dimensional vector variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * vec2f: A list containing two floats
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': vec2f, 'typeHint': 'vec3f', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

    def register_vec3f(self, name, vec3f, access='r', min=None, max=None, step=None):
        """
        Register a three dimensional vector variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * vec3f: A list containing three floats
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': vec3f, 'typeHint': 'vec3f', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

    def register_vec4f(self, name, vec4f, access='r', min=None, max=None, step=None):
        """
        Register a four dimensional vector variable

        Arguments are:
        * name: the name of the variable as how nodes can refer to it
        * vec4f: A list containing four floats
        * access: 'r' and/or 'w' as to if it's readable and writeable state
        * min: minimal value
        * max: maximal value
        * step: step value used by increments and decrements
        """
        self.capability[name] = {'value': vec4f, 'typeHint': 'vec4f', 'access':access }
        if min:
            self.capability[name]['min'] = min
        if max:
            self.capability[name]['max'] = max
        if step:
            self.capability[name]['step'] = step
        self.on_modified()

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
        msg = json.dumps({'SET': keys})
        self.whisper(peer, msg.encode('utf-8'))

    def peer_call(self, peer, method, *args):
        """
        Call method on peer
        """
        msg = json.dumps({'CALL': [method, args]})
        self.whisper(peer, msg.encode('utf-8'))

    def peer_subscribe(self, peer, signal, sensor):
        """
        Subscribe a sensor to a signal
        """
        msg = json.dumps({'SUB': [signal, sensor]})
        self.whisper(peer, msg.encode('utf-8'))

    def peer_unsubscribe(self, peer, signal, sensor):
        """
        Unsubscribe a sensor from a signaller
        """
        msg = json.dumps({'SUB': [signal, sensor]})
        self.whisper(peer, msg.encode('utf-8'))

    #########################################
    # Event methods. These can be overwritten
    #########################################
    def on_peer_enter(self, peer, *args, **kwargs):
        print("ZOCP ENTER   : %s" %(peer.hex))

    def on_peer_exit(self, peer, *args, **kwargs):
        print("ZOCP EXIT    : %s" %(peer.hex))

    def on_peer_join(self, peer, grp, *args, **kwargs):
        print("ZOCP JOIN    : %s joined group %s" %(peer.hex, grp))

    def on_peer_leave(self, peer, grp, *args, **kwargs):
        print("ZOCP LEAVE   : %s left group %s" %(peer.hex, grp))

    def on_peer_whisper(self, peer, *args, **kwargs):
        print("ZOCP WHISPER : %s whispered: %s" %(peer.hex, args))

    def on_peer_shout(self, peer, grp, *args, **kwargs):
        print("ZOCP SHOUT   : %s shouted in group %s: %s" %(peer.hex, grp, args))

    def on_peer_modified(self, peer, *args, **kwargs):
        print("ZOCP MODIFIED: %s modified %s" %(peer.hex, args))

    def on_modified(self):
        if self._running:
            self.shout("ZOCP", json.dumps({ 'MOD' :self.capability}).encode('utf-8'))

    #########################################
    # Internal methods
    #########################################
    def get_message(self):
        # A message coming from a zre node contains:
        # * msg type
        # * msg peer id
        # * group (if group type)
        # * the actual message
        msg = self.get_socket().recv_multipart()
        type = msg.pop(0).decode('utf-8')
        peer = uuid.UUID(bytes=msg.pop(0))
        grp=None
        if type == "ENTER":
            if not peer in self.peers.keys():
                self.peers.update({peer: {}})
            self.peer_get_capability(peer)
            self.on_peer_enter(peer, msg)
            return
        if type == "EXIT":
            self.on_peer_exit(peer, msg)
            self.peers.pop(peer)
            return
        if type == "JOIN":
            grp = msg.pop(0)
            self.on_peer_join(peer, grp, msg)
            return
        if type == "LEAVE":
            grp = msg.pop(0)
            self.on_peer_leave(peer, grp, msg)
            return
        if type == "SHOUT":
            grp = msg.pop(0)
            self.on_peer_shout(peer, grp, msg)
        elif type == "WHISPER":
            self.on_peer_whisper(peer, msg)
        else:
            return

        try:
            msg = json.loads(msg.pop(0).decode('utf-8'))
        except Exception as e:
            print("ERROR: %s" %e)
        else:
            for method in msg.keys():
                if method   == 'GET':
                    self._handle_GET(msg[method], peer, grp)
                elif method == 'SET':
                    self._handle_SET(msg[method], peer, grp)
                elif method == 'CALL':
                    self._handle_CALL(msg[method], peer, grp)
                elif method == 'SUB':
                    self._handle_SUB(msg[method], peer, grp)
                elif method == 'UNSUB':
                    self._handle_UNSUB(msg[method], peer, grp)
                elif method == 'REP':
                    self._handle_REP(msg[method], peer, grp)
                elif method == 'MOD':
                    self._handle_MOD(msg[method], peer, grp)
                elif method == 'SIG':
                    self._handle_SIG(msg[method], peer, grp)
                else:
                    try:
                        func = getattr(self, 'handle_'+method)
                        func(msg[method])
                    except:
                        raise Exception('No %s method on resource: %s' %(method,object))

    def _handle_GET(self, data, peer, grp=None):
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

    def _handle_SET(self, data, peer, grp):
        self.capability = dict_merge(self.capability, data)
        self.on_modified()

    def _handle_CALL(self, data, peer, grp):
        return
        self.peers[peer] = dict_merge(self.peers.get(peer), data)

    def _handle_SUB(self, data, peer, grp):
        return
        self.capability = dict_merge(self.capability, data)
        self.on_modified()

    def _handle_UNSUB(self, data, peer, grp):
        return
        self.capability = dict_merge(self.capability, data)
        self.on_modified()

    def _handle_REP(self, data, peer, grp):
        return

    def _handle_MOD(self, data, peer, grp):
        self.peers[peer] = dict_merge(self.peers.get(peer), data)
        self.on_peer_modified(peer, data)

    def _handle_SIG(self, data, peer, grp):
        return

    def run(self):
        poller = zmq.Poller()
        poller.register(self.get_socket(), zmq.POLLIN)
        self._running = True
        while(self._running):
            try:
                items = dict(poller.poll())
                if self.get_socket() in items and items[self.get_socket()] == zmq.POLLIN:
                    self.get_message()
            except (KeyboardInterrupt, SystemExit):
                break
        self.stop()

    #def __del__(self):
    #    self.stop()

if __name__ == '__main__':

    z = ZOCP()
    z.set_node_name("ZOCP-Test")
    z.register_bool("zocpBool", True, 'rw')
    z.register_float("zocpFloat", 2.3, 'rw', 0, 5.0, 0.1)
    z.register_int('zocpInt', 10, access='rw', min=-10, max=10, step=1)
    z.register_percent('zocpPercent', 12, access='rw')
    z.run()
    z.stop()
    print("FINISH")
