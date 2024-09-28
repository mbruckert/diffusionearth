import numpy as np
import cv2
import open3d as o3d

# Load the color image and depth map
color_image = cv2.imread('mine.png', cv2.IMREAD_COLOR)
depth_map = cv2.imread('depth_mine.png', cv2.IMREAD_UNCHANGED)

# Ensure depth map is single-channel
if len(depth_map.shape) > 2:
    depth_map = depth_map[:, :, 0]

# Get image dimensions
height, width = depth_map.shape

# Define camera intrinsic parameters (we can tweak these)
# Replace these with your camera's actual parameters
fx = fy = 525.0  # Focal length in pixels
cx = width / 2.0  # Principal point x-coordinate
cy = height / 2.0  # Principal point y-coordinate

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
colors = color_image.reshape(-1, 3)
colors = colors[valid]
colors = colors.astype(np.float32) / 255.0  # Normalize to [0, 1]

# Create the point cloud
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)
pcd.colors = o3d.utility.Vector3dVector(colors)

# Set up the visualizer
vis = o3d.visualization.Visualizer()
vis.create_window(visible=False)
vis.add_geometry(pcd)

# Set the camera parameters for a nice view
ctr = vis.get_view_control()
parameters = ctr.convert_to_pinhole_camera_parameters()

# Calculate the bounding box around the point cloud
bbox = pcd.get_axis_aligned_bounding_box()

# Set the look_at point to the center of the bounding box
center = bbox.get_center()

# Set the camera's position directly in front of the object
# Here we are moving the camera by 2 units on the z-axis
camera_position = center + np.array([0, 0, 2])

# Set the up to be the y-axis
up_vector = np.array([0, 1, 0])

# Determine the front vector for the camera
front_vector = np.array([0, 0, -1])

# Adjust the view control to set the lookat, up and front vectors
ctr.set_lookat(center)
ctr.set_up(up_vector)
ctr.set_front(front_vector)
ctr.set_zoom(0.45)  # Adjust the zoom accordingly

# Capture the rendered image
vis.poll_events()
vis.update_renderer()
image = vis.capture_screen_float_buffer(do_render=True)
vis.destroy_window()

# Convert Open3D float image to uint8
image = np.asarray(image)
image = (255 * image).astype(np.uint8)

# Save the image using OpenCV
cv2.imwrite('point_cloud_render.png', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))