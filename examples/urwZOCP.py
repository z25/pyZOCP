#!/usr/bin/python3
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

import urwid
import json
import sys
import io
import zmq
import time
import zocp
import errno

# http://stackoverflow.com/questions/38987/how-can-i-merge-union-two-python-dictionaries-in-a-single-expression?rq=1
def mergedicts(a, b, path=None):
    """
    merges b into a, overwites a with b if equal
    """
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                mergedicts(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class ZmqEventLoop(urwid.SelectEventLoop):

    def __init__(self, ctx=zmq.Context(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zctx = ctx
        self._zpoller = zmq.Poller()

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        self._watch_files[fd] = callback
        self._zpoller.register(fd, zmq.POLLIN)
        return fd
    
    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise
        """
        if handle in self._watch_files:
            self._zpoller.unregister(handle)
            del self._watch_files[handle]
            return True
        return False

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        self._did_something = True
        while True:
            try:
                self._loop()
            except urwid.ExitMainLoop:
                break

    def _loop(self):
        """
        A single iteration of the event loop
        """
        if self._alarms or self._did_something:
            if self._alarms:
                tm = self._alarms[0][0]
                timeout = max(0, tm - time.time())
            if self._did_something and (not self._alarms or 
                    (self._alarms and timeout > 0)):
                timeout = 0
                tm = 'idle'
            try:
                items = dict(self._zpoller.poll(timeout))
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    items = {}
                else:
                    raise(e)
        else:
            tm = None
            try:
                items = dict(self._zpoller.poll())
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    items = {}
                    pass
                else:
                    raise(e)

        if not items:
            if tm == 'idle':
                self._entering_idle()
                self._did_something = False
            elif tm is not None:
                # must have been a timeout
                tm, alarm_callback = self._alarms.pop(0)
                alarm_callback()
                self._did_something = True

        for fd, ev in items.items():
            if ev in (zmq.POLLIN, zmq.POLLOUT):
                self._watch_files[fd]()
                self._did_something = True


class PopUpDialog(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button """
    signals = ['close']
    def __init__(self):
        close_button = urwid.Button("that's pretty cool")
        urwid.connect_signal(close_button, 'click',
            lambda button:self._emit("close"))
        pile = urwid.Pile([urwid.Text(
            "^^  I'm attached to the widget that opened me. "
            "Try resizing the window!\n"), close_button])
        fill = urwid.Filler(pile)
        self.__super.__init__(urwid.AttrWrap(fill, 'selected'))

class HeadingWithPopUp(urwid.PopUpLauncher):
    def __init__(self, name):
        super().__init__(urwid.Button(name))
        urwid.connect_signal(self.original_widget, 'click',
            lambda button: self.open_pop_up())

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, 'close',
            lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left':10, 'top':1, 'overlay_width':32, 'overlay_height':7}

class UrwStdWriter(io.TextIOWrapper):
    
    def __init__(self, *args, **kwargs):
        self.wgt = urwid.Text("")
        super().__init__(*args, **kwargs)

    def write(self, data):
        self.wgt.set_text("%s%s" %(self.wgt.get_text()[0], data))

    def get_widget(self):
        return self.wgt

class ZOCPProgressBar(urwid.ProgressBar):

    signals =["change"]

    def selectable(selfs): return True

    def __init__(self, sel_normal, sel_complete, *args, **kwargs):
        self.sel_normal = sel_normal
        self.sel_complete = sel_complete
        super().__init__(*args, **kwargs)

    def set_label(self, label):
        self._label, self._attrib = decompose_tagmarkup(caption)
        self._invalidate()

    def keypress(self, size, key):
        (maxcol,) = size
        cur = int(self.current)
        if key == 'right':
            if cur < self.done:
                self.set_completion(cur + 1)
                self._emit('change', cur + 1)
            return
        elif key == 'left':
            if cur > 0:
                self.set_completion(cur - 1)
                self._emit('change', cur - 1)
            return
        else:
            return key
            
class ZOCPKeyboardWidget(urwid.Edit):
    """Edit widget which emits its value when pressing enter or loosing focus"""

    def __init__(self,caption="",val=None):
        """
        caption -- caption markup
        default -- default edit value
        """
        self.set_val = val
        self.focused = False
        self.__super.__init__(caption,val)

    def keypress(self, size, key):
        """
        Handle editing keystrokes. Emit change message when
        pressing enter or when leaving widget
        """
        (maxcol,) = size
        unhandled = super().keypress((maxcol,),key)

        if key == 'enter':
            self.set_val = self.value()
            self._emit("change", self.value())

        return unhandled
        
    def render(self, size, focus):
        """
        Render the widget.
        
        `render` is overridden so we can generate `on_focus` events 
        when the focus argument changes 

        :param size: see `urwid.Widget.render(size, focus)`
        :type size: widget size
        :param focus: set to ``True`` if this widget or one of its children
                      is in focus
        :type focus: bool        
        """
        if focus != self.focused:
            self.focused = focus
            self.on_focus(focus)

        return self.__super.render(size, focus)

    def on_focus(self, focus):
        """
        Handle changes in focus.
        
        :param focus: set to ``True`` if this widget or one of its children
                      is in focus
        :type focus: bool        
        """
        if focus:
            # Received focus
            self.set_val = self.value()
        else:
            # Lost focus
            val = self.value()
            if val != self.set_val:
                self.set_val = val
                self._emit("change", val)

                
class ZOCPStringWidget(ZOCPKeyboardWidget):
    """Edit widget for string values"""

    def valid_char(self, ch):
        """
        Return true for all characters.
        """
        return len(ch)==1

    def __init__(self,caption="",default=None):
        """
        caption -- caption markup
        default -- default edit value
        """
        if default is not None: val = str(default)
        else: val = ""
        self.__super.__init__(caption,val)

    def value(self):
        """
        Return the string value of self.edit_text.
        """
        if self.edit_text:
            return self.edit_text
        else:
            return ""

    def set_edit_text(self, text):
        """
        Set the text for this widget.

        :param text: text for editing, type (bytes or unicode)
                     must match the text in the caption
        """
        text = self._normalize_to_caption(text)
        self.highlight = None
        self._edit_text = text
        if self.edit_pos > len(text):
            self.edit_pos = len(text)
        self._invalidate()
        
class ZOCPIntWidget(ZOCPKeyboardWidget):
    """Edit widget for integer values"""

    def valid_char(self, ch):
        """
        Return true for decimal digits.
        """
        return len(ch)==1 and ch in "0123456789"

    def __init__(self,caption="",default=None):
        """
        caption -- caption markup
        default -- default edit value

        >>> IntEdit("", 42)
        <IntEdit selectable flow widget '42' edit_pos=2>
        """
        if default is not None: val = str(default)
        else: val = ""
        self.set_val = val
        self.__super.__init__(caption,val)

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.

        >>> e, size = IntEdit("", 5002), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> print(e.edit_text)
        002
        >>> e.keypress(size, 'end')
        >>> print(e.edit_text)
        2
        """
        (maxcol,) = size
        unhandled = super().keypress((maxcol,),key)

        if not unhandled:
        # trim leading zeros
            while self.edit_pos > 0 and self.edit_text[:1] == "0":
                self.set_edit_pos( self.edit_pos - 1)
                self.set_edit_text(self.edit_text[1:])

        return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.

        >>> e, size = IntEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text and self.edit_text != "":
            return int(self.edit_text)
        else:
            return 0

    def set_edit_text(self, text):
        """
        Set the text for this widget.

        :param text: text for editing, type (bytes or unicode)
                     must match the text in the caption
        :type text: bytes or unicode

        >>> e = FloatEdit()
        >>> e.set_edit_text("0.12")
        >>> print(e.edit_text)
        '0.12'
        """
        text = self._normalize_to_caption(text)
        self.highlight = None
        self._edit_text = text
        if self.edit_pos > len(text):
            self.edit_pos = len(text)
        self._invalidate()

class ZOCPFloatWidget(ZOCPKeyboardWidget):

    def valid_char(self, ch):
        """
        Return true for decimal digits.
        """
        return len(ch)==1 and ch in "0123456789."

    def __init__(self, caption="", value=0.0, min=None, max=None, step=0.1):
        """
        caption -- caption markup
        default -- default edit value

        >>> IntEdit("", 42)
        <IntEdit selectable flow widget '42' edit_pos=2>
        """            
        self.min = min
        self.max = max
        self.step = step
        super().__init__(caption, "%f" %value)
        #rwid.connect_signal(self, 'change', self.on_change)

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.

        >>> e, size = IntEdit("", 5002), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> print(e.edit_text)
        002
        >>> e.keypress(size, 'end')
        >>> print(e.edit_text)
        2
        """
        (maxcol,) = size

        if key == 'right':
            val = float(self.get_edit_text()) if self.get_edit_text() != "" else 0.0
            val += self.step
            self.set_edit_text("%f" %val)
            self.set_val = val
            self._emit("change", val)
        elif key == 'left':
            val = float(self.get_edit_text()) if self.get_edit_text() != "" else 0.0
            val -= self.step
            self.set_edit_text("%f" %val)
            self.set_val = val
            self._emit("change", val)
        else:
            unhandled = super().keypress((maxcol,),key)

            if not unhandled:
            # trim leading zeros
                while self.edit_pos > 0 and self.edit_text[:1] == "0":
                    self.set_edit_pos( self.edit_pos - 1)
                    self.set_edit_text(self.edit_text[1:])

            return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.

        >>> e, size = IntEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text and self.edit_text != "":
            return float(self.edit_text)
        else:
            return 0.0

    def set_value(self, val):
        self.set_edit_text("%f" %val)

    def set_edit_text(self, text):
        """
        Set the text for this widget.

        :param text: text for editing, type (bytes or unicode)
                     must match the text in the caption
        :type text: bytes or unicode

        >>> e = FloatEdit()
        >>> e.set_edit_text("0.12")
        >>> print(e.edit_text)
        '0.12'
        """
        text = self._normalize_to_caption(text)
        self.highlight = None
        self._edit_text = text
        if self.edit_pos > len(text):
            self.edit_pos = len(text)
        self._invalidate()

class ZOCPVec2fWidget(ZOCPKeyboardWidget):

    def valid_char(self, ch):
        """
        Return true for decimal digits.
        """
        return len(ch)==1 and ch in "0123456789."

    def __init__(self, caption="", value=[0.0,0.0], min=None, max=None, step=[0.1,0.1]):
        """
        caption -- caption markup
        default -- default edit value
        """            
        self.min = min
        self.max = max
        self.step = step
        super().__init__(caption, "[%.3f, %.3f]" %(value[0], value[1]))

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.
        """
        (maxcol,) = size

        if key == 'd':
            val = self.value()
            val[0] = val[0] + self.step[0]
            self.set_value(val)
            self._emit("change", val)
        elif key == 'a':
            val = self.value()
            val[0] = val[0] - self.step[0]
            self.set_value(val)
            self._emit("change", val)
        elif key == 'w':
            val = self.value()
            val[1] = val[1] + self.step[1]
            self.set_value(val)
            self._emit("change", val)
        elif key == 's':
            val = self.value()
            val[1] = val[1] - self.step[1]
            self.set_value(val)
            self._emit("change", val)
        else:
            unhandled = super().keypress((maxcol,),key)

            if not unhandled:
            # trim leading zeros
                while self.edit_pos > 0 and self.edit_text[:1] == "0":
                    self.set_edit_pos( self.edit_pos - 1)
                    self.set_edit_text(self.edit_text[1:])

            return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.
        """
        if self.edit_text and self.edit_text != "":
            return eval(self.edit_text)
        else:
            return [0.0, 0,0]

    def set_value(self, val):
        self.set_edit_text("[%.3f, %.3f]" %(val[0], val[1]))

    def set_edit_text(self, text):
        """
        Set the text for this widget.

        :param text: text for editing, type (bytes or unicode)
                     must match the text in the caption
        :type text: bytes or unicode
        """
        text = self._normalize_to_caption(text)
        self.highlight = None
        self._edit_text = text
        if self.edit_pos > len(text):
            self.edit_pos = len(text)
        self._invalidate()


class ZOCPNodeWidget(urwid.WidgetWrap):

    #control_ex = '{"control": {"myInt": {"control": "rw", "value": 1, "typeHint": "int"}, "myFloat": {"control": "rw", "value": 1.0, "typeHint": "float"}}}'
    def __init__(self, parent=None, data={}, node_id=None, node_name="NoName", *args, **kwargs):
        #if not isinstance(node, ZOCP)
        #    raise Exception("Node %s is not of ZOCP type" %node)
        self.parent = parent
        self.node_id = node_id
        self.node_name = node_name
        self.node_data = data
        self.focused = False
        self._update_widgets()
        display_widget = urwid.Pile(urwid.SimpleFocusListWalker(self._widgets))
        super().__init__(display_widget)

    def update(self, data=None):
        if isinstance(data, dict):
            self.node_data = mergedicts(self.node_data, data)
        self._update_widgets()
        focus = self._w.focus_position
        self._w = urwid.Pile(urwid.SimpleFocusListWalker(self._widgets))
        self._w.set_focus(self._w.contents[focus][0])

    def _update_widgets(self):
        #self.node_data.update(data)
        name = self.node_name
        #self._widgets = [urwid.AttrMap(urwid.Text([name]), 'heading') ]
        self._widgets = [urwid.AttrMap(HeadingWithPopUp(name), 'heading') ]
        for name, val in self.node_data.items():
            # we only parse keys not starting with '_'
            if not name[0] == '_':
                wgt = None
                # generate widgets based on the typeHint
                #print("%s, %s" %(val, type(val)))
                dtype = val.get('typeHint')
                # get access property, readonly if none
                access = val.get('access', 'r')
                if dtype == 'string' and access.count('w'):
                    wgt = urwid.AttrMap(ZOCPStringWidget(name + " : ", val.get('value')), 'options', 'selected')
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                elif dtype == 'int' and access.count('w'):
                    wgt = urwid.AttrMap(ZOCPIntWidget(name + " : ", val.get('value')), 'options', 'selected')
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                elif dtype == 'float' and access.count('w'):
                    wgt = urwid.AttrMap(ZOCPFloatWidget(caption=name + " :", value=val.get('value')), 'options', 'selected')
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                elif dtype == 'vec2f' and access.count('w'):
                    wgt = urwid.AttrMap(ZOCPVec2fWidget(caption=name + " :", value=val.get('value')), 'options', 'selected')
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                elif dtype == 'bool' and access.count('w'):
                    wgt = urwid.AttrMap(urwid.CheckBox(name, state=val.get('value')), 'options', 'selected')
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                elif dtype == 'percent':
                    wgt = urwid.AttrMap(ZOCPProgressBar(sel_normal='focus pg normal', 
                                                        sel_complete='focus pg complete', 
                                                        normal='pg normal', 
                                                        complete='pg complete', 
                                                        current=val.get('value'), 
                                                        done=100, 
                                                        satt='pg smooth'), 
                                        'options', focus_map_pg)
                                        #'options', {'pg normal': 'focus pg normal', 'pg complete': 'focus pg complete'})
                    urwid.connect_signal(wgt.original_widget, 'change', self.on_changed, (name))
                else:
                    wgt = wgt = urwid.AttrMap(urwid.Text(name + " : %s" %val.get('value')), 'options', 'selected')
                self._widgets.append(wgt)
        self._widgets.append(urwid.AttrMap(urwid.Divider('\N{LOWER ONE QUARTER BLOCK}'), 'line'))
        #self._widgets.append(urwid.Divider())

    def on_changed(self, wgt, value, name):
        self.node_data[name].update({'value': value})
        dat = {name: {'value': value}}
        z.whisper(self.node_id, json.dumps({'SET': dat}).encode('utf-8'))

    def on_focus(self, focus):
        if focus:
            self.parent.foot.original_widget.set_text("%s" %self.node_id)

    def render(self, size, focus):
        """
        Render the widget.
        
        `render` is overridden so we can generate `on_focus` events
        when the focus argument changes

        :param size: see `urwid.Widget.render(size, focus)`
        :type size: widget size
        :param focus: set to ``True`` if this widget or one of its children
                      is in focus
        :type focus: bool
        """
        if focus != self.focused:
            self.focused = focus
            self.on_focus(focus)

        return self.__super.render(size, focus)        
        
palette = [
    (None,  'light gray', 'black'),
    ('selected', 'white', 'dark blue'),
    ('header', 'black', 'dark gray', 'bold'),
    ('heading', 'black', 'light gray', 'bold'),
    ('focus heading', 'white', 'dark red' ),
    ('line', 'black', 'light gray'),
    ('focus line', 'black', 'dark red'),
    ('options', 'white', 'dark gray'),
    ('focus options', 'white', 'dark gray'),
    ('pg normal', 'white', 'dark gray'),
    ('focus pg normal', 'white', 'dark blue'),
    ('pg complete', 'white', 'dark magenta'),
    ('focus pg complete', 'white', 'dark green'),
    ('pg smooth', 'dark magenta','black'),
    ('focus pg smooth', 'dark magenta','dark blue')]
focus_map = {
    'heading': 'focus heading',
    'options': 'focus options',
    'line': 'focus line'
    }
focus_map_pg = {
    'pg normal': 'focus pg normal',
    'pg complete': 'focus pg complete',
    'pg smooth': 'focus pg smooth',
    'options': 'focus options'
}

class urwZOCP(zocp.ZOCP):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oldout = sys.stdout
        self.out = UrwStdWriter(io.BytesIO(), sys.stdout.encoding)
        self.znodes = {}

        # Urwid containers
        self.cells = urwid.GridFlow(self.znodes.values(), 20, 1, 0, 'left')
        self.foot = urwid.AttrMap(urwid.Text("[no node selected]", align='center'), 'header')
        self.frame = urwid.Pile((self.foot, self.cells, self.out.get_widget()), 1)
        self.fill = urwid.Filler(self.frame, 'top')
        self.loop = urwid.MainLoop(self.fill, palette, unhandled_input=self.handle_input, event_loop=ZmqEventLoop(), pop_ups=True)

        # capture std output
        sys.stdout = self.out

    def handle_input(self, key):
        if key == 'esc':
            raise urwid.ExitMainLoop()
        if key in ('q', 'Q'):
            self.out.get_widget().set_text("")

    #########################################
    # ZOCP Event methods.
    #########################################
    def on_peer_enter(self, peer, name, *args, **kwargs):
        print("ZOCP ENTER   : %s" %(name))
        nd = self.znodes.get(peer)
        if not nd:
            #raise Exception("bla", self.peers_capabilities)

            nd = ZOCPNodeWidget(self, self.peers_capabilities[peer], peer, name)
            self.znodes[peer] = (urwid.AttrMap(nd, 'options', focus_map), self.cells.options('given', 20))
            #index = len(cells.contents)
            #cells.contents.insert(index, (nd, ('given', 20)))
            self.cells.contents.append(self.znodes[peer])
            
        self.peer_subscribe(peer)

    def on_peer_exit(self, peer, name, *args, **kwargs):
        print("ZOCP EXIT    : %s" %(name))
        nd = self.znodes.pop(peer)
        if nd:
            # clear self.contents
            del self.cells.contents[:]
            
            # repopulate self.contents with remaining self.znodes
            for val in self.znodes.values():
                self.cells.contents.append(val)
        if len(self.znodes)==0:
            self.cells._invalidate()
            self.foot.original_widget.set_text("[no node selected]")
                
    def on_peer_modified(self, peer, name, data, *args, **kwargs):
        print("ZOCP MODIFIED: %s modified %s" %(name, data))
        nd = self.znodes.get(peer)
        if nd:
            nd[0].original_widget.update(self.peers_capabilities.get(peer, {}))

    def on_peer_signaled(self, peer, data, *args, **kwargs):
        print("ZOCP SIGNALED: %s modified %s" %(peer.hex, data))
        nd = self.znodes.get(peer)
        if nd:
            nd[0].original_widget.update()

    def run(self):
        self.start()
        handle = self.loop.watch_file(self.inbox, self.get_message)
        self._running = True
        self.loop.run()
        self.stop()
        sys.stdout = self.oldout

if __name__ == "__main__":
    ctx = zmq.Context()
    z = urwZOCP(ctx=ctx)
    z.run()
