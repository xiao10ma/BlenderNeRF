import os
import shutil
import bpy
from . import helper, blender_nerf_operator


# global addon script variables
EMPTY_NAME = 'BlenderNeRF Sphere'
CAMERA_NAME = 'BlenderNeRF Camera'

# camera on sphere operator class
class CameraOnSphere(blender_nerf_operator.BlenderNeRF_Operator):
    '''Camera on Sphere Operator'''
    bl_idname = 'object.camera_on_sphere'
    bl_label = 'Camera on Sphere COS'

    def execute(self, context):
        scene = context.scene
        
        # Check for errors
        error_messages = self.asserts(scene, method='COS')
        if len(error_messages) > 0:
            self.report({'ERROR'}, error_messages[0])
            return {'FINISHED'}
        
        output_data = {}
        
        if scene.fixed_cameras:
            # Create fixed cameras
            cameras = helper.create_fixed_cameras(scene)
            
            # Get camera intrinsics
            output_data = self.get_camera_intrinsics(scene, cameras[0])
            
            # Create output directory
            output_dir = bpy.path.clean_name(scene.cos_dataset_name)
            output_path = os.path.join(scene.save_path, output_dir)
            os.makedirs(output_path, exist_ok=True)
            
            if scene.logs: 
                self.save_log_file(scene, output_path, method='COS')
            if scene.splats: 
                self.save_splats_ply(scene, output_path)
            
            # Collect all camera transformation matrices
            frames = []
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                
                for i, camera in enumerate(cameras):
                    filename = f"r_{frame:03d}_c_{i:02d}.png"
                    frame_data = {
                        'file_path': os.path.join('train', filename),
                        'transform_matrix': self.listify_matrix(camera.matrix_world)
                    }
                    frames.append(frame_data)
            
            output_data['frames'] = frames
            
            # Save transforms_train.json
            self.save_json(output_path, 'transforms_train.json', output_data)
            
            # Render images
            if scene.render_frames:
                output_train = os.path.join(output_path, 'train')
                os.makedirs(output_train, exist_ok=True)
                
                for frame in range(scene.frame_start, scene.frame_end + 1):
                    scene.frame_set(frame)
                    
                    for i, camera in enumerate(cameras):
                        scene.camera = camera
                        scene.render.filepath = os.path.join(output_train, f'r_{frame:03d}_c_{i:02d}')
                        bpy.ops.render.render(write_still=True)
            
            return {'FINISHED'}