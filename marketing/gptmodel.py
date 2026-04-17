from openai import OpenAI
from PIL import Image, ImageDraw
from dotenv import load_dotenv
import os

load_dotenv()
import os
from openai import OpenAI, APIConnectionError, APITimeoutError
from PIL import Image, ImageDraw
from dotenv import load_dotenv
import time

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0, 
    max_retries=3
)

def get_chat_completion(prompt, json_mode=False):
    """Wrapper with error handling for network instability."""
    response_format = {"type": "json_object"} if json_mode else None
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format
        )
        return response.choices[0].message.content
    
    except APITimeoutError:
        print("❌ Request timed out. Checking your internet connection...")
        return "{}" if json_mode else "Error: Timeout"
    except APIConnectionError:
        print("❌ Connection error. Is your Firewall/VPN blocking OpenAI?")
        return "{}" if json_mode else "Error: Connection"
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return "{}" if json_mode else f"Error: {e}"
def create_personal_poster(customer_name, product_name):
    """Creates a branded PNG flyer using Pillow."""
    img = Image.new('RGB', (800, 500), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    gold, white, blue = (234, 179, 8), (255, 255, 255), (56, 189, 248)
    
    draw.rectangle([20, 20, 780, 480], outline=gold, width=3)
    draw.text((60, 60), "EXCLUSIVE PRE-ORDER", fill=gold)
    draw.text((60, 140), f"Hello, {customer_name}!", fill=white)
    draw.text((60, 220), f"We saw you loved your {product_name}.", fill=white)
    draw.text((60, 300), "Upgrade to the NEW Buds Pro today!", fill=blue)
    draw.text((60, 400), "REDEEM 20% OFF", fill=gold)
    
    file_name = f"poster_{customer_name.replace(' ', '_')}.png"
    img.save(file_name)
    return file_name