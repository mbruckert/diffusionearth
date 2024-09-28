import os
from dotenv import load_dotenv
import fal_client
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import json
from google.cloud import storage, firestore
import time

app = Flask(__name__)
CORS(app)

# Initialize Firestore
db = firestore.Client.from_service_account_json('diffusionearth-creds.json')

storage_client = storage.Client.from_service_account_json(
    'diffusionearth-creds.json'
)

FAL_KEY = os.getenv('FAL_KEY')


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

    # Create a new filename to the file with the current timestamp
    filename = file.filename

    # Create a new blob and upload the file's content
    blob = bucket.blob(filename)
    blob.upload_from_file(file)

    # Return the public url
    return blob.public_url


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

    return jsonify({'image_url':gcp_image_url, 'depth_map_url': depth_map_url})


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
    final_view = generate_final_view_from_image_mask_prompt(gcp_render_url, gcp_mask_url, prompt)
    return jsonify({'final_view': final_view, 'prompt': prompt, 'render_url': gcp_render_url, 'mask_url': gcp_mask_url})

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


if __name__ == '__main__':
    app.run(debug=True)
