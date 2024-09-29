import numpy as np
import cv2
import open3d as o3d
from scipy.spatial import cKDTree
from scipy.optimize import minimize
import argparse
import fal_client
import os
import requests
import uuid
from PIL import Image
from io import BytesIO
from google.cloud import storage, firestore
import multiprocessing
from multiprocessing import Manager

db = firestore.Client.from_service_account_json('diffusionearth-creds.json')

storage_client = storage.Client.from_service_account_json(
    'diffusionearth-creds.json'
)

VIEW_MAP = {
    0: 'N',
    1: 'NE',
    2: 'E',
    3: 'SE',
    4: 'S',
    5: 'SW',
    6: 'W',
    7: 'NW'
}
INV_VIEW_MAP = {v: k for k, v in VIEW_MAP.items()}
VIEW_OFFSET_MAP = {
    'N': np.array([0, 1]),
    'NE': np.array([1, 1]),
    'E': np.array([1, 0]),
    'SE': np.array([1, -1]),
    'S': np.array([0, -1]),
    'SW': np.array([-1, -1]),
    'W': np.array([-1, 0]),
    'NW': np.array([-1, 1])
}
NEW = 0
RENDERED = 1
PROPAGATED = 2

class GridView:
    def __init__(self, points, colors, intrinsics, height, width, tf, rh, grid_id):
        self.points = points
        self.colors = colors
        self.intrinsics = intrinsics
        self.height = height
        self.width = width
        # self.image_url = None
        # self.depth_image_url = None
        # self.propagation_data = None
        # self.status = NEW
        manager = Manager()
        self.image_url = manager.Value('image_url', None)
        self.depth_image_url = manager.Value('depth_image_url', None)
        self.propagation_data = manager.list()
        self.status = manager.Value('status', NEW)
        multiprocessing.Process(target=self.render, args=(tf, rh, grid_id)).start()

        # if image and depth url are empty, post a queue message to generate the render
        # the render function must propagate the points and colors and stuff to the new grids

        # call the render function with the coordinate and orientation. Since everything else is ready, the render function
        # can make the render and update the image and depth image url. It will also have created the new points, colors, etc.
        # and since it is coming at this from the top down it can update the grid and start the next batch

    def render(self, tf, rh, grid_id):
        """called when a gridview is created without an image and depth url. This function will render the image and depth
        for this view, and store the new points, colors, etc. until the user lands on this view. Then, they can be propagated
        to the next view"""

        print(f"Rendering {grid_id}...")

        # Step 1. Get the mask cloud of the most recent image, in order to get the camera orientation from that frame.
        # We use the most recent camera position as the starting point for the motion
        alignment_pcd = o3d.geometry.PointCloud()
        alignment_pcd.points = o3d.utility.Vector3dVector(self.points)
        alignment_pcd.colors = o3d.utility.Vector3dVector(np.array([[0, 0, 0]] * self.points.shape[0]))

        # Step 2. Get the camera orientation from the alignment point cloud
        lookat, zoom, transform_factor, pose = get_camera_orientation(alignment_pcd)
        print(f"{grid_id} Lookat: {lookat}, Zoom: {zoom}, Transform Factor: {transform_factor}")

        # Step 3. Update the global point cloud
        # frame_cur = RGBDImages(
        #     torch.tensor(color_image, dtype=torch.float32).unsqueeze(0).unsqueeze(0),
        #     torch.tensor(depth_map, dtype=torch.float32).unsqueeze(0).unsqueeze(0).unsqueeze(-1),
        #     torch.tensor(intrinsics, dtype=torch.float32).unsqueeze(0).unsqueeze(0),
        #     torch.tensor(pose, dtype=torch.float32).unsqueeze(0).unsqueeze(0),
        # )
        # pointclouds, _ = slam.step(pointclouds, frame_cur, frame_prev)
        # frame_prev = frame_cur
        # torch.cuda.empty_cache()

        # Step 4. Transform the local camera motion
        rotate, translate = process_local_transform(tf, rh, transform_factor)

        print(f"{grid_id} Rotate: {rotate}, Translate: {translate}")

        # Step 5. Get the current global point cloud
        # current_pcd = pointclouds.open3d(index=-1)
        current_pcd = o3d.geometry.PointCloud()
        current_pcd.points = o3d.utility.Vector3dVector(self.points)
        current_pcd.colors = o3d.utility.Vector3dVector(self.colors)
        # o3d.io.write_point_cloud(f'{grid_id}.ply', current_pcd)

        current_mask_pcd = o3d.geometry.PointCloud(current_pcd)
        current_mask_pcd.colors = o3d.utility.Vector3dVector(np.array([[0, 0, 0]] * self.points.shape[0]))

        # Step 6. Render the point cloud and mask
        pcd_render = render_pcd(lookat, zoom, self.height, self.width, rotate, translate, current_pcd)
        mask_render = render_pcd(lookat, zoom, self.height, self.width, rotate, translate, current_mask_pcd)

        cv2.imwrite(f'{grid_id}_mask.png', mask_render)
        cv2.imwrite(f'{grid_id}_image.png', pcd_render)

        image, mask = process_renders(pcd_render, mask_render)

        # Step 7. Get the next image and depth
        new_image, self.image_url.value, new_depth, self.depth_image_url.value = get_next_images(image, mask)
        
        # Step 8. Update the current points, colors, and intrinsics
        self.propagation_data.extend(preprocess(new_depth, new_image))

        self.status.value = RENDERED
        print(f"Rendered {grid_id}!")

class GridNode:
    def __init__(self, N=None, NE=None, E=None, SE=None, S=None, SW=None, W=None, NW=None):
        self.views: dict[str, GridView] = {
            'N': N,
            'NE': NE,
            'E': E,
            'SE': SE,
            'S': S,
            'SW': SW,
            'W': W,
            'NW': NW
        }

class User:
    def __init__(self):
        self.position = np.array([0, 0])
        self.orientation = 'N'
        self.renders: dict[tuple[int, int], GridNode] = {}

def preprocess(depth_map, rgb_image):
    """Convert the depth image into an array of 3D coordinates and and align the colors with those points"""

    # Get image dimensions
    print(depth_map.shape)
    height, width = depth_map.shape

    # Define camera intrinsic parameters
    fx = fy = 525.0  # Focal length in pixels
    cx = width / 2.0  # Principal point x-coordinate
    cy = height / 2.0  # Principal point y-coordinate

    # Create the intrinsic matrix
    intrinsics = np.array([
        [fx, 0, cx, 0],
        [0, fy, cy, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

    # Create a mesh grid of pixel coordinates
    u = np.arange(width)
    v = np.arange(height)
    u, v = np.meshgrid(u, v)

    # Flatten the arrays
    u = u.flatten()
    v = v.flatten()
    depth = depth_map.flatten()

    # Filter out zero depth values
    valid = depth > 0
    u = u[valid]
    v = v[valid]
    depth = depth[valid]

    # Compute the 3D coordinates
    Z = depth.astype(np.float32) / 1000.0  # Convert to meters if necessary
    X = (u - cx) * Z / fx
    Y = (v - cy) * Z / fy

    # Stack the coordinates
    points = np.stack((X, Y, Z), axis=-1)

    # Get the corresponding colors
    colors = rgb_image.reshape(-1, 3)
    colors = colors[valid]
    colors = colors.astype(np.float32) / 255.0  # Normalize to [0, 1]

    return points, colors, intrinsics, height, width

def get_camera_orientation(mask_pcd) -> tuple:
    """Get the lookat and zoom of the camera"""

    # Compute the lookat vector
    _pcd = o3d.geometry.PointCloud(mask_pcd)
    _pcd = _pcd.random_down_sample(0.1)
    _pcd.estimate_normals()
    _pcd.orient_normals_consistent_tangent_plane(100)
    normals = np.asarray(_pcd.normals)
    average_normal = np.mean(np.asarray(normals), axis=0)
    average_normal /= np.linalg.norm(average_normal)
    lookat = -average_normal

    # compute the zoom
    def compute_whitespace(zoom: float):
        mask_render = render_pcd(lookat, zoom, 480, 640, [0, 0], [0, 0, 0], mask_pcd)
        gray_mask_pcd_render = cv2.cvtColor(mask_render, cv2.COLOR_RGB2GRAY)
        _, binary_mask = cv2.threshold(gray_mask_pcd_render, 127, 255, cv2.THRESH_BINARY)
        return np.sum(binary_mask == 255)
    
    zoom = minimize(compute_whitespace, 0.001, method='Nelder-Mead').x[0]

    # Computer rotation transform factor
    bbox = mask_pcd.get_axis_aligned_bounding_box()
    view_ratio = zoom * bbox.get_max_extent()
    distance = view_ratio / np.tan(np.deg2rad(30))
    degrees_per_unit = 100 / distance
    shift_factor = 2 * view_ratio / 1080
    transform_factor = 1 / (degrees_per_unit * shift_factor)

    # Compute pose (extrinsics) matrix
    pos = np.array([lookat[0], lookat[1], lookat[2]+distance])
    forward = np.array([0, 0, -1])
    up = np.array([0, -1, 0])
    s = np.cross(forward, up)
    s = s / np.linalg.norm(s)
    up = np.cross(s, forward)
    view_matrix = [
        s[0],            up[0],            -forward[0],          0,
        s[1],            up[1],            -forward[1],          0,
        s[2],            up[2],            -forward[2],          0,
        -np.dot(s, pos), -np.dot(up, pos), np.dot(forward, pos), 1,
    ]
    view_matrix = np.array(view_matrix).reshape(4, 4).T
    pose_matrix = np.linalg.inv(view_matrix)
    pose_matrix[:, 1:3] = -pose_matrix[:, 1:3]
    
    return lookat, zoom, transform_factor, pose_matrix

def render_pcd(lookat, zoom, height, width, rotate, translate, pcd):
    """Render a 2D image of the point cloud with a certain camera orientation. The rotate and translate arguments must already
    be converted to the Open3D format, and should NOT be an angle or xyz translateion respectively"""

    # Visualize the point cloud
    vis = o3d.visualization.Visualizer()
    vis.create_window(visible=False)
    vis.add_geometry(pcd)

    # Set the camera parameters for a nice view
    ctr = vis.get_view_control()

    # get to the start position
    ctr.set_up([0, -1, 0])
    ctr.set_front([0, 0, -1])
    ctr.set_lookat(lookat)
    ctr.set_zoom(zoom)

    # perform local rotations
    ctr.camera_local_rotate(*rotate)
    ctr.camera_local_translate(*translate)

    # Capture the rendered image
    vis.poll_events()
    vis.update_renderer()
    image = vis.capture_screen_float_buffer(do_render=True)
    vis.destroy_window()

    image = np.asarray(image)
    image = (255 * image).astype(np.uint8)

    return image

def process_local_transform(tf, rh, transform_factor):
    """Translate the local rotation (an angle in degrees) and translation (a distance in meters) to the Open3D format"""

    # process the rotation
    rotate = [-rh*transform_factor, 0]

    # process the translation
    translate = [tf, 0, 0]

    return rotate, translate

def process_renders(image_render, mask_render):
    """Clean the mask by converting it to binary and removing the smallest components"""

    # Convert mask to binary
    gray_mask_pcd_render = cv2.cvtColor(mask_render, cv2.COLOR_RGB2GRAY)
    _, binary_mask = cv2.threshold(gray_mask_pcd_render, 127, 255, cv2.THRESH_BINARY)

    height, width = binary_mask.shape

    # Get the bounding box of the region containing any points
    rows_with_0 = np.where(np.any(binary_mask == 0, axis=1))[0]
    cols_with_0 = np.where(np.any(binary_mask == 0, axis=0))[0]

    row_start = 0 if len(rows_with_0) == 0 else rows_with_0[0]
    row_end = height - 1 if len(rows_with_0) == 0 else rows_with_0[-1]
    col_start = 0 if len(cols_with_0) == 0 else cols_with_0[0]
    col_end = width - 1 if len(cols_with_0) == 0 else cols_with_0[-1]

    bbox = [row_start, row_end, col_start, col_end]

    # Crop the image and mask
    image_render = image_render[bbox[0]:bbox[1], bbox[2]:bbox[3]]
    binary_mask = binary_mask[bbox[0]:bbox[1], bbox[2]:bbox[3]]

    # grow the whitespace in the mask
    kernel = np.ones((5, 5), np.uint8)
    binary_mask = cv2.dilate(binary_mask, kernel, iterations=3)

    return image_render, binary_mask

def get_next_images(image, mask):
    """Use the current image and inpainting mask to get a new image for the point cloud, and its depth"""

    # upload the renders to google cloud storage
    def upload_to_gcs(image_arr):
        # Initialize a storage client
        bucket_name = "diffusionearth-images"
        bucket = storage_client.bucket(bucket_name)

        filename = f"{uuid.uuid4()}.png"
        blob = bucket.blob(blob_name=filename)

        # Save the image to a temporary file
        cv2.imwrite(filename, image_arr)

        # Upload the file to GCS
        blob.upload_from_filename(filename)

        os.remove(filename)

        # Return the public url
        return blob.public_url

    image_url = upload_to_gcs(image)
    mask_url = upload_to_gcs(mask)

    print(f"Image URL: {image_url}")
    print(f"Mask URL: {mask_url}")

    # get a description of the rgb image
    handler = fal_client.submit(
        "fal-ai/moondream/batched",
        arguments={
            "inputs": [{
                "prompt": "Describe what is visible in this image in detail. Pretend you are trying to prompt a diffusion model to generate this exact image.",
                "image_url": image_url,
                "max_tokens": 256
            }]
        }
    )
    image_description = handler.get()['outputs'][0]
    
    # perform inpainting on the image using the mask and description
    handler = fal_client.submit(
        "fal-ai/fast-turbo-diffusion/inpainting",
        arguments={
            "image_url": image_url,
            "mask_url": mask_url,
            "prompt": image_description,
            "sync_mode": False,
            "negative_prompt": "cartoon, illustration, animation. face. male, distorted, low-quality, blurred, pixelated, abstract, white, transparent, random, glitchy.",
            "image_size": "square_hd",
            "num_inference_steps": 21,
            "guidance_scale": 1,
            "strength": 0.97,
            "seed": 42
        }
    )
    new_image_url = handler.get()['images'][0]['url']

    # # perform upscaling on the depth image
    # handler = fal_client.submit(
    #     "fal-ai/creative-upscaler",
    #     arguments={
    #         "image_url": render_url,
    #         "scale": 1,
    #         "creativity": 0.1,
    #         "detail": 2,
    #         "shape_preservation": 2.5,
    #         "seed": 42,
    #         "skip_ccsr": True,
    #     },
    # )
    # new_image_url = handler.get()['image']['url']

    print(f"New image URL ready!: {new_image_url}")

    # estimate the depth of the new image
    handler = fal_client.submit(
        "fal-ai/imageutils/marigold-depth",
        arguments={
            "image_url": new_image_url
        },
    )
    new_depth_image_url = handler.get()['image']['url']

    # download the new images
    def download_image(url, mode):
        resp = requests.get(url)
        # image = Image.open(BytesIO(response.content))
        # image_np = np.array(image)
        image_np = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(image_np, mode)
        return img
    
    new_image = download_image(new_image_url, cv2.IMREAD_COLOR)
    new_depth = download_image(new_depth_image_url, cv2.IMREAD_ANYDEPTH)

    return new_image, new_image_url, new_depth, new_depth_image_url