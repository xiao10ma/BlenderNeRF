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
            # Create output directory structure
            scene_dir = os.path.join(scene.save_path, scene.scene_name)
            os.makedirs(scene_dir, exist_ok=True)
            
            if scene.logs:
                self.save_log_file(scene, scene_dir, method='COS')
            if scene.splats:
                self.save_splats_ply(scene, scene_dir)
            
            # Create all cameras (train + test)
            train_cameras = helper.create_fixed_cameras(scene, is_test=False)
            test_cameras = helper.create_fixed_cameras(scene, is_test=True)
            all_cameras = train_cameras + test_cameras
            
            # Get camera intrinsics data
            train_data = self.get_camera_intrinsics(scene, train_cameras[0])
            test_data = self.get_camera_intrinsics(scene, test_cameras[0])
            
            # Collect transforms for global json files
            train_frames = []
            test_frames = []
            frame_count = 1
            
            # Render images and save per-frame transforms
            if scene.render_frames:
                for frame in range(scene.frame_start, scene.frame_end + 1):
                    scene.frame_set(frame)
                    
                    # Create frame directory
                    frame_dir = os.path.join(scene_dir, f'frame{frame_count:06d}')
                    os.makedirs(frame_dir, exist_ok=True)
                    
                    # Collect transforms for this frame
                    current_train_frames = []
                    current_test_frames = []
                    
                    # Training cameras
                    for i, camera in enumerate(train_cameras):
                        filename = f"frame{frame_count:06d}/cam{i:02d}"
                        current_filename = f"cam{i:02d}"
                        
                        # For global transforms
                        frame_data = {
                            'file_path': filename,
                            'transform_matrix': self.listify_matrix(camera.matrix_world)
                        }
                        train_frames.append(frame_data)
                        
                        # For per-frame transforms
                        current_frame_data = {
                            'file_path': current_filename,
                            'transform_matrix': self.listify_matrix(camera.matrix_world)
                        }
                        current_train_frames.append(current_frame_data)
                    
                    # Test cameras
                    for i, camera in enumerate(test_cameras):
                        filename = f"frame{frame_count:06d}/cam{i+scene.num_train_cameras:02d}"
                        current_filename = f"cam{i+scene.num_train_cameras:02d}"
                        
                        # For global transforms
                        frame_data = {
                            'file_path': filename,
                            'transform_matrix': self.listify_matrix(camera.matrix_world)
                        }
                        test_frames.append(frame_data)
                        
                        # For per-frame transforms
                        current_frame_data = {
                            'file_path': current_filename,
                            'transform_matrix': self.listify_matrix(camera.matrix_world)
                        }
                        current_test_frames.append(current_frame_data)
                    
                    # Save per-frame transforms
                    current_train_data = train_data.copy()
                    current_test_data = test_data.copy()
                    current_train_data['frames'] = current_train_frames
                    current_test_data['frames'] = current_test_frames
                    self.save_json(frame_dir, 'transforms_train.json', current_train_data)
                    self.save_json(frame_dir, 'transforms_test.json', current_test_data)
                    
                    # Render from all cameras
                    for i, camera in enumerate(all_cameras):
                        scene.camera = camera
                        scene.render.filepath = os.path.join(frame_dir, f'cam{i:02d}')
                        bpy.ops.render.render(write_still=True)
                    
                    frame_count += 1
            
            # Save global transforms json files
            train_data['frames'] = train_frames
            test_data['frames'] = test_frames
            self.save_json(scene_dir, 'transforms_train.json', train_data)
            self.save_json(scene_dir, 'transforms_test.json', test_data)
            
            return {'FINISHED'}