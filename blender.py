import bpy
import bmesh
import struct
import datetime
from bpy import context, ops
from mathutils import Vector
from math import radians
import sys

# v4 Status (4-20-2018 2:30pm): In Progress

#Script Purpose
#  The user will be prompted to browse for a file
#  The object (2D surface) will be imported, and extruded to a 3D model (calculated height)
#  Finally, the 3D model is exported to original location with the format "<fname>-3D.stl"

#Constraints
#  This code works for both STL and OBJ files, otherwise it will exit out.
#  Extra objects that already exist will not be modified, but will be exported.

# NEXT: Dissolve extra vertices in bottom face
# Improve: baseheight calculation takes too long

# Setup filedialog Class
class CustomDrawOperator(bpy.types.Operator):
    bl_idname = "object.custom_draw"
    bl_label = "Import"
    
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    my_float = bpy.props.FloatProperty(name="Float")
    my_bool = bpy.props.BoolProperty(name="Toggle Option")
    my_string = bpy.props.StringProperty(name="String Value")
    
    def NormalInDirection(self, normal, direction, limit = 0.5 ):
        return direction.dot( normal ) > limit

    def GoingDown(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (0, 0, -1 ) ), limit )

    def execute(self, context):
        tStart = datetime.datetime.now()
        print('\r\n---BEGIN--- ' + str(tStart) + ' ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
        
        # check for argument containing filepath
        if len(sys.argv) > 5:
            self.filepath = sys.argv[5]
        print('  -opening file: ' + self.filepath)
        
        # Import File
        if self.filepath.endswith('.stl'):
            outPath = self.filepath.replace('.stl','-3D.stl')
            bpy.ops.import_mesh.stl(filepath=self.filepath)
            print('  -STL imported successfully')
            # bpy.ops.import_mesh.stl(filepath="C://Users//andrew.shewmaker//Documents//Scripts//SimpleSurface.stl", filter_glob="*.stl",  files=[{"name":"SimpleSurface.stl", "name":"SimpleSurface.stl"}], directory="C://Users//andrew.shewmaker//Documents//Scripts")
        elif self.filepath.endswith('.obj'):
            outPath = self.filepath.replace('.obj','-3D.stl')
            bpy.ops.import_scene.obj(filepath=self.filepath, axis_forward='Y', axis_up='Z')
            print('  -OBJ imported successfully')
# 4-20-2018: Importing an OBJ file causes a context error when entering EDIT mode...
        else:
            print('**INVALID FILE TYPE')
            return { 'FINISHED' }
        
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                print('  -found VIEW_3D area')
                override = bpy.context.copy()
                override['area'] = area
                
                # Select ALL objects (there should only be one)
                object = bpy.context.selected_objects[0]
                bpy.context.scene.objects.active = object
                print('  -active object set')
                
                # Enter EDIT mode
                override = bpy.context.copy()
                override['area'] = area
                bpy.ops.object.mode_set(override, mode='EDIT')
                print('  -EDIT mode enabled')
                
                # Select ALL vertices
                override = bpy.context.copy()
                override['area'] = area
                bpy.ops.mesh.select_all(override, action='SELECT')
                print('  -ALL vertices selected')
                
                # Calculate the lowest point (slower than I'd like)
                vzlist = []
                for vert in object.data.vertices:
                    vzlist.append(vert.co.z)
                if vzlist:
                    smallestz = min(vzlist)
                    biggestz = max(vzlist)
                else:
                    smallestz = 0
                    biggestz = 0
                zdimension = biggestz + smallestz*-1
                baseHeight = -5000 # -1.1*zdimension/2
                print("  -Z Dimension = " + str(zdimension) + "(baseheight=" + str(-1*baseHeight) + ")")
                
                # Extrude all points down in Z-axis
                bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, baseHeight), "constraint_axis":(False, False, True), "constraint_orientation":'GLOBAL', "mirror":False, "proportional":'DISABLED', "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
                print('  -base extruded')
                
                # Flatten bottom extruded surface
                bpy.ops.transform.resize(value=(1, 1, 0), constraint_axis=(False, False, True), constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
                print('  -base flattened')
                
                # Dissolve bottom face (to reduce file size)
                if False:
                    obj = bpy.context.object
                    prevMode = obj.mode
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

                    #Selects faces going DOWN
                    for face in obj.data.polygons:
                        face.select = self.GoingDown( face.normal )
                    print('  -mesh dissolved')
                    
                    #bpy.ops.mesh.edge_face_add()
                    
                    meshes = [o.data for o in context.selected_objects if o.type == 'MESH']
                    print(meshes)
                    bm = bmesh.new()
                    for m in meshes:
                        bm.from_mesh(m)
                        bmesh.ops.dissolve_limit(bm, angle_limit=radians(1.7), verts=bm.verts, edges=bm.edges)
                        bm.to_mesh(m)
                        m.update()
                        bm.clear()
                        print('  -mesh dissolved')

                    bm.free()
                    #bpy.ops.object.mode_set(mode=prevMode, toggle=False)
                    
                    #print('exit early for debug')
                    #break
                
                # Toggle Out of EDIT Mode, back to OBJECT mode
                bpy.ops.object.mode_set(override, mode='OBJECT')
                print('  -OBJECT mode enabled')
                
                # EXPORT model
                bpy.ops.export_mesh.stl(filepath=outPath)
                print('  -STL export complete')
                
                tEnd = datetime.datetime.now()
                elapsed = tEnd-tStart # seconds
                print('---END--- ' + str(elapsed) + ' sec >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                break
        return {'FINISHED'}
            
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Custom Interface!")

        row = col.row()
        row.prop(self, "my_float")
        row.prop(self, "my_bool")

        col.prop(self, "my_string")

bpy.utils.register_class(CustomDrawOperator)

# Main Entry Point
result= bpy.ops.object.custom_draw('INVOKE_DEFAULT')
# if result == 'FINISHED':
#     print('---Script Complete---\r\n')
# else:
#     print(result)
# print('\r\n---BEGIN--- ')