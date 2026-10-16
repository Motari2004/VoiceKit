import shutil
import os
from gradio_client import Client

# Connect to your Hugging Face Space
client = Client("Motari/txt2speech")

# Call the /tts endpoint
temp_path, _ = client.predict(
    text="Here's the test: can you tell the difference between me and a human?",
    voice="am_adam",
    speed=1.0,
    api_name="/tts"
)

# Define the local file name in the same folder
local_filename = "output_audio.wav"
local_path = os.path.join(os.getcwd(), local_filename)

# Copy the file from the temp path to your current directory
shutil.copy(temp_path, local_path)

print(f"Audio file successfully saved in the same folder at: {local_path}")