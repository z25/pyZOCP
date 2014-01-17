import bpy
import sys
sys.path.append('/usr/local/lib/python3.3/dist-packages/pyzmq-13.1.0-py3.3-linux-x86_64.egg')
sys.path.append('/home/arnaud/Documents/sphaero/zmq-test/pyZOCP/src')
sys.path.append('/home/arnaud/Documents/sphaero/zmq-test/pyre')
print(sys.path)

import time
import json
from zocp import ZOCP
from mathutils import Vector
from bpy.app.handlers import persistent

alreadyDeletedObjects = set()
camSettings = {}
mistSettings = ()

z = ZOCP()
z.set_node_name("ZOCP-Test")

#    Menu in UI region
#
class UIPanel(bpy.types.Panel):
    bl_label = "Send debug message"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
 
    def draw(self, context):
        self.layout.operator("send.oscdebug", text='Toggle debug')

class OBJECT_OT_HelloButton(bpy.types.Operator):
    bl_idname = "send.zocpdebug"
    bl_label = "Send Debug"
    
    def execute(self, context):
        print("Sending debug!")
        z.shout("ZOCP", {"MOD": {"debug": True}})
        return{'FINISHED'}    
        
def sendObjectData(object):
    z.shout("ZOCP", json.dumps({ 
                        "MOD": 
                        { 
                            object.name+".x": {"value": object.location.x},
                            object.name+".y": {"value": object.location.y},
                            object.name+".z": {"value": object.location.z},
                        }
                    }).encode('utf-8'))

def sendCameraSettings(camera):
    """
    send camera fov and lensshhift
    """
    global camSettings
    angle = camera.angle
    lx = camera.shift_x
    ly = camera.shift_y
    print("sending new camera settings for %s" %camera.name)
    z.shout("ZOCP", json.dumps({ 
                        "MOD": 
                        { 
                            camera.name+".angle": {"value": camera.angle},
                            camera.name+".shift_x": {"value": camera.shift_x},
                            camera.name+".shift_y": {"value": camera.shift_y},
                        }
                    }).encode('utf-8'))
    z.capability[camera.name+".angle"]['value'] = angle
    z.capability[camera.name+".shift_x"]['value'] = lx
    z.capability[camera.name+".shift_y"]['value'] = ly       
    
    camSettings[camera.name] = (angle, lx, ly)
     
@persistent         
def update_data(scene):
    for obj in scene.objects:
        if obj.type == 'MESH': # only send the object if it is a mesh or a Camera
            z.capability[obj.name+".x"]['value'] = obj.location.x
            z.capability[obj.name+".y"]['value'] = obj.location.y
            z.capability[obj.name+".z"]['value'] = obj.location.z        
            sendObjectData(obj)
        elif obj.type == 'CAMERA':
            angle = obj.data.angle
            lx = obj.data.shift_x
            ly = obj.data.shift_y
            if not ( [angle, lx, ly]  == camSettings.get(obj.data.name)):
                print("camera settings changed for %s", obj.name)
                sendCameraSettings(obj.data)
       
def register():
    for obj in  bpy.context.scene.objects:
        if obj.type == 'MESH': # only send the object if it is a mesh or a Camera
            z.register_float(obj.name+".x", obj.location.x, 'r')
            z.register_float(obj.name+".y", obj.location.y, 'r')
            z.register_float(obj.name+".z", obj.location.z, 'r')
        elif obj.type == 'CAMERA':
            z.register_float(obj.name+".angle", obj.data.angle, 'r')
            z.register_float(obj.name+".shift_x", obj.data.shift_x, 'r')
            z.register_float(obj.name+".shift_y", obj.data.shift_y, 'r')

#register cameras
register()
bpy.utils.register_module(__name__)
bpy.app.handlers.frame_change_post.clear()
bpy.app.handlers.frame_change_post.append(update_data)

def run():
    from threading import Thread
    t = Thread(target=z.run)
    t.start()

run()