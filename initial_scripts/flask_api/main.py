import os
from dotenv import load_dotenv
import fal_client
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import json
from google.cloud import storage
import time

app = Flask(__name__)
CORS(app)

storage_client = storage.Client.from_service_account_json(
    'diffusionearth-creds.json'
)

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
    fal_image_url = upload_to_gcs(file)
    print(fal_image_url)
    
    return jsonify({'depth_map_url': fal_image_url})

if __name__ == '__main__':
    app.run(debug=True)