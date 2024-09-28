# Initial Script for receiving an image, binary mask, and prompt
import os
from dotenv import load_dotenv
import fal_client
import base64

load_dotenv()

ORIGINAL_FILE_PATH = 'dog.png'
MASK_FILE_PATH = 'dog_mask.png'
PROMPT = "a dog sitting on a park bench"

FAL_KEY = os.getenv('FAL_KEY')

def upload_to_fal(file_path):
    url = fal_client.upload_file(file_path)
    return url

def inpaint_image(original_file_path, mask_file_path, prompt):
    handler = fal_client.submit(
        "fal-ai/fast-sdxl/inpainting",
        arguments={
            "image_url": original_file_path,
            "mask_url": mask_file_path,
            "prompt": prompt
        }
    )

    result = handler.get()
    if 'images' in result and len(result['images']) > 0:
        return result['images'][0]['url']
    return None

def marigold_depth_estimation(img_url):
    handler = fal_client.submit(
        "fal-ai/imageutils/marigold-depth",
        arguments={
            "image_url": img_url
        },
    )
    result = handler.get()
    print(result)
    if 'image' in result:
        return result['image']['url']
    return None

if __name__ == "__main__":
    # original = upload_to_fal(ORIGINAL_FILE_PATH)
    # mask = upload_to_fal(MASK_FILE_PATH)
    # result = inpaint_image(original, mask, PROMPT)
    dog = upload_to_fal(ORIGINAL_FILE_PATH)
    result = marigold_depth_estimation(dog)
    print(result)