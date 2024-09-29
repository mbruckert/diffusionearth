import os
import threading
import cv2
from dotenv import load_dotenv
import fal_client
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import json
from google.cloud import storage, firestore
import time
from googlemaps import Client
import tempfile
import numpy as np
import requests
import logging
from utils import *

app = Flask(__name__)
CORS(app)

# Initialize Firestore
db = firestore.Client.from_service_account_json('diffusionearth-creds.json')

storage_client = storage.Client.from_service_account_json(
    'diffusionearth-creds.json'
)

FAL_KEY = os.getenv('FAL_KEY')
GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY')

user = None


@app.route('/start', methods=['POST'])
@cross_origin()
def start():
    global user

    def download_image(url, mode):
        resp = requests.get(url)
        image_np = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(image_np, mode)
        return img

    if request.content_type.startswith('multipart/form-data'):
        # Handle form data
        upload_type = request.form.get('upload_type')
    elif request.is_json:
        # Handle JSON data
        data = request.get_json()
        upload_type = data.get('upload_type')
    else:
        return jsonify({'status': 'error', 'message': 'Unsupported Media Type'}), 415

    if upload_type == 'street_maps':
        address = data['address']
        image_url = get_street_view_image(address)
        depth_url = marigold_depth_estimation(image_url)
        prompt = generate_prompt_from_image(image_url)
    elif upload_type == 'upload_image':
        file = request.files['image']
        image_url = upload_to_gcs(file)
        depth_url = marigold_depth_estimation(image_url)
        prompt = generate_prompt_from_image(image_url)
    elif upload_type == 'prompt':
        prompt = data['prompt']
        image_url = generate_image_from_prompt(prompt)
        depth_url = marigold_depth_estimation(image_url)
    else:
        return jsonify({'status': 'error', 'message': 'Invalid upload_type'}), 400

    # Rest of your code remains the same
    color_image = download_image(image_url, cv2.IMREAD_COLOR)
    depth_map = download_image(depth_url, cv2.IMREAD_ANYDEPTH)
    color_image = cv2.resize(color_image, (512, 512))
    depth_map = cv2.resize(depth_map, (512, 512))

    cv2.imwrite("color_image.png", color_image)
    cv2.imwrite("depth_map.png", depth_map)

    points, colors, intrinsics, height, width = preprocess(
        depth_map, color_image)

    user = User()

    user.renders[(0, 0)] = GridNode(
        N=GridView(points.copy(), colors.copy(), intrinsics.copy(),
                   height, width, prompt, 0, 0, "0,0 N"),
        NE=GridView(points.copy(), colors.copy(), intrinsics.copy(),
                    height, width, prompt, 0, -45, "0,0 NE"),
        NW=GridView(points.copy(), colors.copy(), intrinsics.copy(),
                    height, width, prompt, 0, 45, "0,0 NW"),
    )
    user.renders[(0, 1)] = GridNode(
        N=GridView(points.copy(), colors.copy(), intrinsics.copy(),
                   height, width, prompt, 5, 0, "0,1 N"),
    )

    return jsonify({'status': 'success', 'image_url': image_url, 'depth_map_url': depth_url})


@app.route('/move', methods=['POST'])
@cross_origin()
def move():
    global user

    if user is None:
        return jsonify({'error': 'Please call /start first'}), 400

    data = request.get_json()
    if 'action' not in data:
        return jsonify({'error': 'Please provide action'}), 400

    action = data['action']

    if action == 'w':  # go forward

        # get the new view
        node = user.renders.get(
            tuple(user.position + VIEW_OFFSET_MAP[user.orientation]))
        if node is None:
            return jsonify({'info': 'This view has not been rendered yet'}), 200

        view = node.views.get(user.orientation)
        if view is None or view.status.value < RENDERED:
            return jsonify({'info': 'This view has not been rendered yet'}), 200

        # update the position
        user.position += VIEW_OFFSET_MAP[user.orientation]

    else:  # turn

        # rotate the user's view
        orientation_num = INV_VIEW_MAP[user.orientation]
        new_orientation = VIEW_MAP[(
            orientation_num - 1) % 8] if action == 'a' else VIEW_MAP[(orientation_num + 1) % 8]

        # get the new view
        node = user.renders.get(tuple(user.position))
        if node is None:
            raise Exception("Something is seriously wrong")

        view = node.views.get(new_orientation)

        if view is None or view.status.value < RENDERED:
            return jsonify({'info': 'This view has not been rendered yet'}), 200

        # update the orientation
        user.orientation = new_orientation

    def propagate(user, node, view):
        orientation_num = INV_VIEW_MAP[user.orientation]

        # Left of current view
        if node.views.get(VIEW_MAP[(orientation_num - 1) % 8]) is None:
            node.views[VIEW_MAP[(orientation_num - 1) % 8]] = GridView(*view.propagation_data, tf=0, rh=45,
                                                                       grid_id=f"{user.position[0]},{user.position[1]} {VIEW_MAP[(orientation_num - 1) % 8]}")

        # Right of current view
        if node.views.get(VIEW_MAP[(orientation_num + 1) % 8]) is None:
            node.views[VIEW_MAP[(orientation_num + 1) % 8]] = GridView(*view.propagation_data, tf=0, rh=-45,
                                                                       grid_id=f"{user.position[0]},{user.position[1]} {VIEW_MAP[(orientation_num + 1) % 8]}")

        # Forward from current view
        nn = tuple(user.position + VIEW_OFFSET_MAP[user.orientation])
        if user.renders.get(nn) is None:
            user.renders[nn] = GridNode(
                **{
                    user.orientation: GridView(*view.propagation_data, tf=5, rh=0, grid_id=f"{nn[0]},{nn[1]} {user.orientation}"),
                }
            )
        elif user.renders[nn].views.get(user.orientation) is None:
            user.renders[nn].views[user.orientation] = GridView(
                *view.propagation_data, tf=5, rh=0, grid_id=f"{nn[0]},{nn[1]} {user.orientation}")

        node.views[user.orientation].status.value = PROPAGATED

    # propagate the view data
    if view.status.value < PROPAGATED:
        threading.Thread(target=propagate, args=(user, node, view)).start()

    return jsonify({'image_url': view.image_url.value, 'depth_map_url': view.depth_image_url.value})


@app.route('/image-to-image', methods=['POST'])
@cross_origin()
def image_to_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    # Upload image to gcs server
    gcp_image_url = upload_to_gcs(file)
    print(gcp_image_url)

    depth_map_url = marigold_depth_estimation(gcp_image_url)
    # Save to Firestore
    doc_ref = add_to_firestore(gcp_image_url, depth_map_url)
    print(doc_ref)

    return jsonify({'image_url': gcp_image_url, 'depth_map_url': depth_map_url})


@app.route('/image-to-prompt', methods=['POST'])
@cross_origin()
def image_to_prompt():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    # Upload image to gcs server
    gcp_image_url = upload_to_gcs(file)
    print(gcp_image_url)

    prompt = generate_prompt_from_image(gcp_image_url)
    return jsonify({'prompt': prompt, 'image_url': gcp_image_url})


@app.route('/prompt-to-image', methods=['POST'])
@cross_origin()
def prompt_to_image():
    data = request.get_json()
    if 'prompt' not in data:
        return jsonify({'error': 'No prompt provided in the request'}), 400

    prompt = data['prompt']
    print("I got the prompt", prompt)
    # Generate image from prompt
    image_url = generate_image_from_prompt(prompt)

    # Generate depth map
    depth_map_url = marigold_depth_estimation(image_url)

    # Save to Firestore
    doc_ref = add_to_firestore(image_url, depth_map_url)
    print(doc_ref)

    return jsonify({'image_url': image_url, 'depth_map_url': depth_map_url, 'user_prompt': prompt})


@app.route('/address-to-image', methods=['POST'])
@cross_origin()
def address_to_image():
    data = request.get_json()
    if 'address' not in data:
        return jsonify({'error': 'No address provided in the request'}), 400

    address = data['address']

    # For now, just return the address string
    return jsonify({'address': address})

# This route takes two images 'render' and 'mask' as an upload and a prompt and returns the final view


@app.route('/image-and-mask-to-image', methods=['POST'])
@cross_origin()
def image_and_mask_to_image():
    if 'render' not in request.files:
        return jsonify({'error': 'No render image part in the request'}), 400
    if 'mask' not in request.files:
        return jsonify({'error': 'No mask image part in the request'}), 400

    render = request.files['render']
    mask = request.files['mask']
    if render.filename == '':
        return jsonify({'error': 'No render image selected for uploading'}), 400
    if mask.filename == '':
        return jsonify({'error': 'No mask image selected for uploading'}), 400

    # Upload images to gcs server
    gcp_render_url = upload_to_gcs(render)
    gcp_mask_url = upload_to_gcs(mask)
    print(gcp_render_url, gcp_mask_url)

    prompt = generate_prompt_from_image(gcp_render_url)
    final_view = generate_final_view_from_image_mask_prompt(
        gcp_render_url, gcp_mask_url, prompt)
    return jsonify({'final_view': final_view, 'prompt': prompt, 'render_url': gcp_render_url, 'mask_url': gcp_mask_url})


@app.route('/street-view', methods=['POST'])
@cross_origin()
def street_view():
    data = request.get_json()
    if 'address' not in data:
        return jsonify({'error': 'No address provided in the request'}), 400

    address = data['address']
    return jsonify(get_street_view_image(address)[0])


def marigold_depth_estimation(image_url):
    handler = fal_client.submit(
        "fal-ai/imageutils/marigold-depth",
        arguments={
            "image_url": image_url
        },
    )
    result = handler.get()
    if 'image' in result:
        return result['image']['url']
    return None


def generate_image_from_prompt(prompt):
    handler = fal_client.submit(
        "fal-ai/fast-turbo-diffusion",
        arguments={
            "prompt": prompt,
            "sync_mode": False
        },
    )

    result = handler.get()
    print(result)
    if 'images' in result:
        return result['images'][0]['url']
    return None


def generate_prompt_from_image(prompt):
    handler = fal_client.submit(
        "fal-ai/moondream/batched",
        arguments={
            "inputs": [{
                "prompt": "Describe what is visible in this image in detail. Pretend you are trying to prompt a diffusion model to generate this exact image.",
                "image_url": prompt,
                "max_tokens": 256
            }]
        }
    )
    result = handler.get()
    if 'outputs' in result:
        return result['outputs'][0]
    return None


def generate_final_view_from_image_mask_prompt(image_url, mask_url, prompt):
    handler = fal_client.submit(
        "fal-ai/fast-turbo-diffusion/inpainting",
        arguments={
            "image_url": image_url,
            "mask_url": mask_url,
            "prompt": prompt,
            "sync_mode": False,
            "negative_prompt": "cartoon, illustration, animation. face. male, distorted, low-quality, blurred, pixelated, abstract, white, transparent, random, glitchy.",
            "image_size": "square_hd",
            "num_inference_steps": 21,
            "guidance_scale": 1,
            "strength": 0.97,
            "seed": 42
        }
    )
    result = handler.get()
    print(result)
    if 'images' in result and len(result['images']) > 0:
        return result['images'][0]['url']
    return None


def get_street_view_image(address) -> str:
    gmaps = Client(key=GOOGLE_MAPS_KEY)

    geocode_result = gmaps.geocode(address)
    if not geocode_result:
        return "Could not find coordinates for address", 400

    lat = geocode_result[0]['geometry']['location']['lat']
    lng = geocode_result[0]['geometry']['location']['lng']

    temp_dir = tempfile.gettempdir()
    output_dir = os.path.join(temp_dir, "temp_images")
    os.makedirs(output_dir, exist_ok=True)

    url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={
        lat},{lng}&fov=90&heading=0&key={GOOGLE_MAPS_KEY}"
    response = requests.get(url)

    address_hash = str(hash(address))
    filename = os.path.join(
        output_dir, "streetview_" + address_hash + ".png")
    with open(filename, 'wb') as file:
        file.write(response.content)
    gcs_url = upload_to_gcs(filename)
    return gcs_url


def add_to_firestore(original_url, depth_url, point_cloud_url=''):
    doc_ref = db.collection('images').add({
        'original': original_url,
        'depth': depth_url,
        'point_cloud': point_cloud_url
    })
    return doc_ref


def upload_to_gcs(file):
    # Initialize a storage client
    bucket_name = "diffusionearth-images"
    bucket = storage_client.bucket(bucket_name)

    if isinstance(file, str):
        # If file is a string, assume it's a filepath
        filename = os.path.basename(file)
        blob = bucket.blob(filename)
        blob.upload_from_filename(file)
    else:
        # Assume file is a file-like object
        filename = file.filename
        blob = bucket.blob(filename)
        blob.upload_from_file(file)

    # Return the public url
    return blob.public_url


if __name__ == '__main__':
    app.run(debug=True)
