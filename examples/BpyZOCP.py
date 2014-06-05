import bpy
import sys
import time
import json
import socket
import zmq

from zocp import ZOCP
from mathutils import Vector
from bpy.app.handlers import persistent

alreadyDeletedObjects = set()
camSettings = {}
mistSettings = ()

def toggleDebug(s, ctx):
    pass

# PROPERTIES
bpy.types.Scene.zdebug_prop = bpy.props.BoolProperty( name="Toggle Debug", description = "This is a boolean", default=False, update=toggleDebug )
bpy.types.Scene.zmute_prop = bpy.props.BoolProperty( name="Mute", description = "This is a boolean", default=False )
bpy.types.Scene.zname_prop = bpy.props.StringProperty(name="Node Name", default=socket.gethostname(),description = "This can be used to identify your node")

#    Menu in UI region
#
class UIPanel(bpy.types.Panel):
    bl_label = "ZOCP Control"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        scn = bpy.context.scene
        self.layout.operator("send.all", text='Send all object data')
        self.layout.prop( scn, "zdebug_prop" ) 
        self.layout.prop( scn, "zmute_prop" )
        self.layout.prop( scn, "zname_prop" )

class OBJECT_OT_SendMesh(bpy.types.Operator):
    bl_idname = "send.all"
    bl_label = "Send Object Data"

    def execute(self, context):
        z.register_objects();
        return{'FINISHED'}   
        
class OBJECT_OT_HelloButton(bpy.types.Operator):
    bl_idname = "send.zocpdebug"
    bl_label = "Send Debug"

    def execute(self, context):
        print("Sending debug!")
        z.shout("ZOCP", {"MOD": {"debug": True}})
        return{'FINISHED'}    


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
     
# @persistent         
# def update_data(scene):
#     for obj in scene.objects:
#         if obj.type == 'MESH': # only send the object if it is a mesh or a Camera
#             z.capability[obj.name+".x"]['value'] = obj.location.x
#             z.capability[obj.name+".y"]['value'] = obj.location.y
#             z.capability[obj.name+".z"]['value'] = obj.location.z        
#             sendObjectData(obj)
#         elif obj.type == 'CAMERA':
#             angle = obj.data.angle
#             lx = obj.data.shift_x
#             ly = obj.data.shift_y
#             if not ( [angle, lx, ly]  == camSettings.get(obj.data.name)):
#                 print("camera settings changed for %s", obj.name)
#                 sendCameraSettings(obj.data)

# def register():
#     for obj in  bpy.context.scene.objects:
#         if obj.type == 'MESH': # only send the object if it is a mesh or a Camera
#             z.register_float(obj.name+".x", obj.location.x, 'r')
#             z.register_float(obj.name+".y", obj.location.y, 'r')
#             z.register_float(obj.name+".z", obj.location.z, 'r')
#         elif obj.type == 'CAMERA':
#             z.register_float(obj.name+".angle", obj.data.angle, 'r')
#             z.register_float(obj.name+".shift_x", obj.data.shift_x, 'r')
#             z.register_float(obj.name+".shift_y", obj.data.shift_y, 'r')

class BpyZOCP(ZOCP):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_node_name("Blender@" + socket.gethostname() + ":" + bpy.app.version_string)

    @persistent
    def clear_objects(self):
        print("CLEAR OBJECTS")
        if not self.capability.get('objects'):
            return
        self.set_object()
        self.capability['objects'].clear()
        self._on_modified(self.capability)

    @persistent
    def register_objects(self):
        print("REGISTER OBJECTS")
        self._running = False
        for obj in bpy.context.scene.objects:
            print(obj.name)
            if obj.type in ['MESH', 'CAMERA', 'LAMP']:
                if obj.type == "LAMP":
                    self._register_lamp(obj)
                elif obj.type == "CAMERA":
                    self._register_camera(obj)
                else:
                    self._register_mesh(obj)
        self._running = True

    def _register_lamp(self, obj):
        self.set_object(obj.name, "BPY_Lamp")
        self.register_vec3f("location",           obj.location[:])
        #self.register_mat3f("worldOrientation",   obj.worldOrientation[:])
        self.register_vec3f("orientation",        obj.rotation_euler[:])
        self.register_vec3f("scale",              obj.scale[:])
        self.register_vec3f("color",              obj.data.color[:])
        self.register_float("energy",             obj.data.energy)
        self.register_float("distance",           obj.data.distance)
        #self.register_int  ("state",              obj.state)
        #self.register_float("mass",               obj.mass)

    def _register_camera(self, obj):
        self.set_object(obj.name, "BPY_Camera")
        self.register_vec3f("location",           obj.location[:])
        #self.register_mat3f("worldOrientation",   obj.worldOrientation[:])
        self.register_vec3f("orientation",        obj.rotation_euler[:])
        self.register_float("angle",              obj.data.angle, 'r')
        self.register_float("shift_x",            obj.data.shift_x, 'r')
        self.register_float("shift_y",            obj.data.shift_y, 'r')

    def _register_mesh(self, obj):
        self.set_object(obj.name, "BPY_Mesh")
        self.register_vec3f("location",           obj.location[:])
        #self.register_mat3f("worldOrientation",   obj.worldOrientation[:])
        self.register_vec3f("orientation",        obj.rotation_euler[:])
        self.register_vec3f("scale",              obj.scale[:])
        self.register_vec4f("color",              obj.color[:])
        #self.register_int  ("state",              obj.state)
        #self.register_float("mass",               obj.mass)

    def send_object_changes(self, obj):
        self.set_object(obj.name, "BPY_Mesh")
        if self._cur_obj.get("location", {}).get("value") != obj.location[:]:
            self.register_vec3f("location", obj.location[:])
        if self._cur_obj.get("orientation", {}).get("value") != obj.rotation_euler[:]:
            self.register_vec3f("orientation", obj.rotation_euler[:])
        if self._cur_obj.get("scale", {}).get("value") != obj.scale[:]:
            self.register_vec3f("scale", obj.scale[:])
        if obj.type == "LAMP":
            if self._cur_obj.get("color", {}).get("value") != obj.data.color[:]:
                self.register_vec3f("color", obj.data.color[:])
            if self._cur_obj.get("energy", {}).get("value") != obj.data.energy[:]:
                self.register_float("energy", obj.data.energy[:])
            if self._cur_obj.get("distance", {}).get("value") != obj.data.distance[:]:
                self.register_float("color", obj.data.distance[:])
        elif obj.type == "MESH":
            if self._cur_obj.get("color", {}).get("value") != obj.color[:]:
                self.register_vec4f("color", obj.color[:])
        elif obj.type == "CAMERA":
            print("CAAAAAAAAAAAAAAMERAAAAAAAA")
            self._register_camera(obj)


    #########################################
    # Event methods. These can be overwritten
    #########################################
    def on_peer_enter(self, peer, *args, **kwargs):
        print("ZOCP ENTER   : %s" %(peer.hex))
        # create an empty for peer
        name = self.peers[peer].get("_name", peer.hex)
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        bpy.context.object.name = name
        # get projectors on peer
        objects = self.peers[peer].get("objects", {})
        for obj, data in objects.items():
            if data.get("type", "") == "projector":
                loc = data.get("location", (0,0,0))
                ori = data.get("orientation", (0,0,0))
                bpy.ops.object.camera_add(view_align=True,
                                          enter_editmode=False,
                                          location=loc,
                                          rotation=ori,
                                          layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False)
                                          )
                bpy.context.object.name = obj

    def on_peer_exit(self, peer, *args, **kwargs):
        print("ZOCP EXIT    : %s" %(peer.hex))
        bpy.ops.object.select_all(action='DESELECT')
        objects = self.peers[peer].get("objects", {})
        for obj, data in objects.items():
            if data.get("type", "") == "projector":
                bpy.ops.object.select_pattern(pattern=obj)
                bpy.ops.object.delete()
        # delete empty
        name = self.peers[peer].get("_name", peer.hex)
        bpy.ops.object.select_pattern(pattern=name)
        bpy.ops.object.delete()
        bpy.ops.object.select_pattern(pattern=peer.hex)
        bpy.ops.object.delete()
        bpy.ops.object.select_all(action='DESELECT')

    def on_peer_modified(self, peer, data, *args, **kwargs):
        print("ZOCP PEER MODIFIED: %s modified %s" %(peer.hex, data))
        if data.get("_name", "").startswith("BGE"):
            print("WE FOUND A BGE NODE")
            # TODO: If we have camera for it send it the settings
            # otherwise create new camera
            
#         if data.get('objects'):
#             for obj,val in data['objects'].items():
#                 if val.get("Type")
#                 bpy.ops.object.select_all(action='DESELECT')
#                 bpy.ops.object.select_pattern(pattern=obj)
#                 try:
#                     blenderobj = bpy.context.scene.objects[obj]
#                 except KeyError as e:
#                     print(e)
#                 else:
#                     for key,val2 in val.items():
#                         try:
#                             setattr(blenderobj, key, val)
#                         except AttributeError as e:
#                             print(e)
#                         except TypeError as e:
#                             print(e)
#                         except ValueError as e:
#                             print(e)


    #except (KeyboardInterrupt, SystemExit):
    #        self.stop()

z = BpyZOCP()

compobj = {}
for ob in bpy.data.objects:
    print(ob.name)
    compobj[ob.name] = ob.matrix_world.copy()

# Needed for delaying 
toffset = 1/30.0
tstamp = time.time()

@persistent
def clear_objects(context):
    global compobj
    compobj.clear()
    z.clear_objects()

@persistent
def register_objects(context):
    global compobj
    z.register_objects()
    for ob in bpy.data.objects:
        compobj[ob.name] = ob.matrix_world.copy()

@persistent
def scene_update(context):
    global toffset
    global tstamp
    # only once per 'toffset' seconds to lessen the burden
    if time.time() > tstamp + toffset:
        tstamp = time.time()
        z.run_once(timeout=0)
        update_objects()
    #else:
    #    print("delayed", tstamp, time.time())

@persistent
def frame_update(context):
    for ob in bpy.data.objects:
        if not compobj.get(ob.name):
            compobj[ob.name] = ob.matrix_world
            z.send_object_changes(ob)
        elif ob.is_updated and ob.matrix_world != compobj[ob.name]:
            z.send_object_changes(ob)

def update_objects():
    #global compobj
    if bpy.data.objects.is_updated:
        for ob in bpy.data.objects:
            ###### TODO: BETTER CODE FOR MANAGING CHANGED DATA
            if not compobj.get(ob.name):
                compobj[ob.name] = ob.matrix_world
                z.send_object_changes(ob)
            elif ob.is_updated and ob.matrix_world != compobj[ob.name]:
                z.send_object_changes(ob)

#register cameras
#register()
bpy.utils.register_module(__name__)
#bpy.app.handlers.scene_update_post.append(update_data)
#bpy.app.handlers.frame_change_pre.clear()
#bpy.app.handlers.frame_change_pre.append(update_data)
bpy.app.handlers.load_pre.clear()
bpy.app.handlers.load_post.clear()
bpy.app.handlers.load_pre.append(clear_objects)
bpy.app.handlers.load_post.append(register_objects)

bpy.app.handlers.scene_update_post.clear()
bpy.app.handlers.scene_update_post.append(scene_update)
bpy.app.handlers.frame_change_post.clear()
bpy.app.handlers.frame_change_post.append(frame_update)
