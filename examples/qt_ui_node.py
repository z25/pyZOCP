#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
qt_ui_node.py
PyQt5 ZOCP UI Node example
"""

import sys
from PyQt5 import QtCore, QtWidgets, QtGui
from zocp import ZOCP
import zmq

class QTZOCPNode(QtWidgets.QWidget):

    def __init__(self):
        super(QTZOCPNode, self).__init__()
        self.qle = QtWidgets.QTextEdit(self)
        self.qle.move(1, 1)
        self.qle.resize(640,480)
        self.init_zocp()
        self.show()

    def init_zocp(self):
        self.z = ZOCP()
        self.z.set_node_name("QT UI TEST")
        self.z.register_float("myFloat", 2.3, 'rw', 0, 5.0, 0.1)
        self.notifier = QtCore.QSocketNotifier(
                self.z.inbox.getsockopt(zmq.FD), 
                QtCore.QSocketNotifier.Read
                )
        self.notifier.setEnabled(True)
        self.notifier.activated.connect(self.zocp_event)
        self.z.on_modified = self.on_modified

    def zocp_event(self):
        print("ZOCP EVENT START")
        self.z.run_once(0)
        print("ZOCP EVENT END")

    def on_modified(self, data, peer):
        t = self.qle.toPlainText()
        t = "{0}\n{1}".format(data, t)
        self.qle.setPlainText(t)

    def closeEvent(self, *args):
        print(args)
        self.z.stop()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = QTZOCPNode() 
    app.exec_()


if __name__ == '__main__':
    main()
