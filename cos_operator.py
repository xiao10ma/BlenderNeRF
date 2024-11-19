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
        
        if scene.fixed_cameras:
            # Create output directory
            output_dir = bpy.path.clean_name(scene.cos_dataset_name)
            output_path = os.path.join(scene.save_path, output_dir)
            os.makedirs(output_path, exist_ok=True)
            
            if scene.logs: 
                self.save_log_file(scene, output_path, method='COS')
            if scene.splats: 
                self.save_splats_ply(scene, output_path)
            
            # Create training cameras and get data
            train_cameras = helper.create_fixed_cameras(scene, is_test=False)
            train_data = self.get_camera_intrinsics(scene, train_cameras[0])
            
            # Collect training camera transforms
            train_frames = []
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                
                for i, camera in enumerate(train_cameras):
                    filename = f"r_{frame:03d}_c_{i:02d}.png"
                    frame_data = {
                        'file_path': os.path.join('train', filename),
                        'transform_matrix': self.listify_matrix(camera.matrix_world)
                    }
                    train_frames.append(frame_data)
            
            train_data['frames'] = train_frames
            self.save_json(output_path, 'transforms_train.json', train_data)
            
            if scene.test_data:
                # Create test cameras and get data
                test_cameras = helper.create_fixed_cameras(scene, is_test=True)
                test_data = self.get_camera_intrinsics(scene, test_cameras[0])
                
                # Collect test camera transforms
                test_frames = []
                for frame in range(scene.frame_start, scene.frame_end + 1):
                    scene.frame_set(frame)
                    
                    for i, camera in enumerate(test_cameras):
                        filename = f"r_{frame:03d}_c_{i:02d}.png"
                        frame_data = {
                            'file_path': os.path.join('test', filename),
                            'transform_matrix': self.listify_matrix(camera.matrix_world)
                        }
                        test_frames.append(frame_data)
                
                test_data['frames'] = test_frames
                self.save_json(output_path, 'transforms_test.json', test_data)
            
            # Render images
            if scene.render_frames:
                # Render training images
                output_train = os.path.join(output_path, 'train')
                os.makedirs(output_train, exist_ok=True)
                
                for frame in range(scene.frame_start, scene.frame_end + 1):
                    scene.frame_set(frame)
                    
                    for i, camera in enumerate(train_cameras):
                        scene.camera = camera
                        scene.render.filepath = os.path.join(output_train, f'r_{frame:03d}_c_{i:02d}')
                        bpy.ops.render.render(write_still=True)
                
                # Render test images if needed
                if scene.test_data:
                    output_test = os.path.join(output_path, 'test')
                    os.makedirs(output_test, exist_ok=True)
                    
                    for frame in range(scene.frame_start, scene.frame_end + 1):
                        scene.frame_set(frame)
                        
                        for i, camera in enumerate(test_cameras):
                            scene.camera = camera
                            scene.render.filepath = os.path.join(output_test, f'r_{frame:03d}_c_{i:02d}')
                            bpy.ops.render.render(write_still=True)
            
            return {'FINISHED'}