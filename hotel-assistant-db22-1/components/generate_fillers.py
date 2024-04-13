import openai
from dotenv import load_dotenv
import os
import numpy as np
import sounddevice as sd
from pyht import Client
from pyht.client import TTSOptions
import time
import re 
import grpc
from log import print_and_save
from datetime import datetime
import wave

# load_dotenv()  # Load environment variables

# PPLX_API_KEY = os.getenv("PPLX_API_KEY")

# PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
# PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
# client = Client(user_id=PLAYHT_USER_ID, api_key=PLAYHT_API_KEY)
# # options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")
# options = TTSOptions(voice="s3://voice-cloning-zero-shot/2bc098a7-c1fc-4b32-9452-556c5ab4814e/jason/manifest.json")
# sample_rate = 24000 

# def play_audio_from_text(text, filename):
#     success = False
#     attempts = 0

#     while not success and attempts < 3:  # Try up to 3 times
#         try:
#             stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32')
#             stream.start()

#             audio_data = bytes()
#             for chunk in client.tts(text, options):
#                 audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / np.iinfo(np.int16).max
#                 audio_data += chunk


#             with wave.open(filename, "wb") as wf:
#                 wf.setnchannels(1)  # Mono audio
#                 wf.setsampwidth(2)  # 16 bits per sample, as numpy int16 has 2 bytes
#                 wf.setframerate(sample_rate)
#                 wf.writeframes(audio_data)
#             print(f'Audio saved to {filename}:', text)
#             #     stream.write(audio_data)
#             # print('audio Played:', text)

#             # stream.stop()
#             # stream.close()
#             # success = True  # If we reach this line, it means no error was raised
                


#         except grpc._channel._MultiThreadedRendezvous as e:
#             if e._state.code == grpc.StatusCode.RESOURCE_EXHAUSTED:
#                 attempts += 1
#                 print(f"Resource exhausted, retrying... Attempt {attempts}")
#                 time.sleep(0.5)  # Wait for 1 second before retrying
#             else:
#                 raise  

# play_audio_from_text('Sure...', 'sure.wav')


import os
import grpc
from pyht import Client
from pyht.client import TTSOptions
import time
import wave

load_dotenv()  # Load environment variables

PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
client = Client(user_id=PLAYHT_USER_ID, api_key=PLAYHT_API_KEY)
options = TTSOptions(voice="s3://voice-cloning-zero-shot/2bc098a7-c1fc-4b32-9452-556c5ab4814e/jason/manifest.json")
sample_rate = 24000 

def save_audio_from_text(text, filename="output.wav"):
    success = False
    attempts = 0

    while not success and attempts < 3:  # Try up to 3 times
        try:
            audio_data = bytes()
            for chunk in client.tts(text, options):
                audio_data += chunk  # Correctly accumulate byte chunks
            
            # Now, save the collected audio data to a WAV file
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)  # Mono audio
                wf.setsampwidth(2)  # 16 bits per sample. This assumes the TTS service returns 16-bit PCM audio.
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)
            print(f'Audio saved to {filename}:', text)

            success = True  # If we reach this line, it means no error was raised

        except grpc._channel._MultiThreadedRendezvous as e:
            if e._state.code == grpc.StatusCode.RESOURCE_EXHAUSTED:
                attempts += 1
                print(f"Resource exhausted, retrying... Attempt {attempts}")
                time.sleep(0.5)  # Wait for 1 second before retrying
            else:
                raise

save_audio_from_text('Sure...', 'sure.wav')
