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
    
    return jsonify({'depth_map_url': depth_map_url})

"""@app.route('/prompt-to-image', methods=['POST'])
@cross_origin()
def prompt_to_image():
    data = request.get_json()
    if 'prompt' not in data:
        return jsonify({'error': 'No prompt provided in the request'}), 400
    
    prompt = data['prompt']
    
    # Generate image from prompt
    image_url = generate_image_from_prompt(prompt)
    
    # Save to Firestore
    doc_ref = db.collection('images').add({
        'depth': '',  # Assuming depth URL is not available for prompt-to-image
        'original': image_url,
        'point_cloud': ''  # Assuming point_cloud URL is not available yet
    })
    
    return jsonify({'image_url': image_url})

@app.route('/address-to-image', methods=['POST'])
@cross_origin()
def address_to_image():
    data = request.get_json()
    if 'address' not in data:
        return jsonify({'error': 'No address provided in the request'}), 400
    
    address = data['address']
    
    # For now, just return the address string
    return jsonify({'address': address})"""

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
        "fal-ai/fast-sdxl/text-to-image",
        arguments={
            "prompt": prompt
        }
    )
    result = handler.get()
    if 'images' in result and len(result['images']) > 0:
        return result['images'][0]['url']
    return None

if __name__ == '__main__':
    app.run(debug=True)