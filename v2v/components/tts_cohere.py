
import json
from dotenv import load_dotenv
import os
import numpy as np
import sounddevice as sd
import soundfile as sf
from pyht import Client
from pyht.client import TTSOptions
import time
import re 
import grpc
import sys
import random
from datetime import datetime
import asyncio
import pyautogui as pg 
sys.path.append('./components')
from cohere_helper import call_chat_bot

load_dotenv()  # Load environment variables

PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
client = Client(user_id=PLAYHT_USER_ID, api_key=PLAYHT_API_KEY)
options = TTSOptions(voice="s3://voice-cloning-zero-shot/2bc098a7-c1fc-4b32-9452-556c5ab4814e/jason/manifest.json")
sample_rate = 24000 
processed_sentences = set()
sentence_end_pattern = re.compile(r'(?<=[.?!])\s')
stop_playing = False

def close_call():
    d, fs = sf.read("assets/outro.wav")
    sd.play(d, fs)
    sd.wait()
    print('Call ended from our side.')
    self_end_call = pg.locateOnScreen('assets/buttons/self_end_call.png', confidence = 0.98)
    if self_end_call:
        pg.click(self_end_call)
        pg.mouseDown()
        asyncio.sleep(0.1)  
        pg.mouseUp()
    else:
        print('self_end_call button not found')

def play_audio_from_text(text):
    global stop_playing 
    success = False
    attempts = 0

    while not success and attempts < 3:  # Try up to 3 times
        try:
            stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32')
            stream.start()

            for chunk in client.tts(text, options):

                if os.path.exists('stop_playing.txt'):
                    stop_playing = True
                if stop_playing:
                    stream.stop()
                    stream.close()
                    return
                else:
                    audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / np.iinfo(np.int16).max
                    stream.write(audio_data)
            print('audio Played:', text)

            stream.stop()
            stream.close()
            success = True  # If we reach this line, it means no error was raised


        except grpc._channel._MultiThreadedRendezvous as e:
            if e._state.code == grpc.StatusCode.RESOURCE_EXHAUSTED:
                attempts += 1
                print(f"Resource exhausted, retrying... Attempt {attempts}")
                time.sleep(0.5)  # Wait for 0.5 second before retrying
            else:
                raise  



async def handle_llm_response(full_content,play_audio):
    global stop_playing
    await asyncio.sleep(0)
    sentences = re.split(r'[.!?]', full_content)
    sentences = [s.strip() for s in sentences if s]

    for sentence in sentences:
        if sentence not in processed_sentences:

            if stop_playing:
                return
            else:
                if play_audio == True:
                    play_audio_from_text(sentence)
                    print('sentence sent to playht: ', sentence)
                    processed_sentences.add(sentence)


def pick_random_audio_file(folder_path):
    audio_files = [file for file in os.listdir(folder_path) if file.endswith(('.wav', '.mp3', '.ogg'))]
    if audio_files:
        random_audio_file = random.choice(audio_files)
        return f"{folder_path}/{random_audio_file}"
    else:
        return None


def play_filler():
    
    filler = pick_random_audio_file('assets/chatbot_fillers')
    if filler:
        print("Random Filler selected:", filler)
        d, fs = sf.read(filler)
        sd.play(d, fs)   
    else:
        print("Filler is empty.")

async def cohere_response(chat_history, query, output_filename, preamble):
    print('cohere response function called:',datetime.now())
    global stop_playing
    global processed_sentences
    print(chat_history)
    print(type(chat_history))
    
    processed_sentences.clear()
    if query is None:
        print("Query is None. Skipping the request.")
        return chat_history

    play_filler()
    response_stream =  call_chat_bot(query, chat_history, preamble)  

    processed_content = ""
    await asyncio.sleep(0)
    for event in response_stream:
        if event.event_type == "stream-end":
            content = event.response.text
            content = content.replace("'", '"')
            content = content.replace("```json","")
            content = content.replace("```","")
            content = content.strip()
            jsonResponse = {}

            try:
                json_start = content.rfind("{")
                if json_start != -1:
                    json_string = content[json_start:]
                    jsonResponse = json.loads(json_string)
                    print(jsonResponse)
                    play_audio = False
                    await handle_llm_response(json_string, play_audio)
                else:
                    print("No JSON found in the response.")
                    play_audio = True
                    await handle_llm_response(content, play_audio)
            except json.JSONDecodeError as e:
                print("Failed to decode JSON:", e)
                play_audio = False
                await handle_llm_response(content, play_audio)

    if content.strip():
       
        chat_history.append({"role": "CHATBOT", "message": content.strip()})
        
        with open('chat_history.txt', 'w') as ch:
            ch.write(json.dumps({"role": "CHATBOT", "message": content.strip()}))
        
        print("Content",content)
        print("Processed Content --------------",processed_content.strip())
        print("Object ",type(processed_content))
        print("Content",content)
        message_string = None
        if play_audio == False:
            print(jsonResponse["func"],len(jsonResponse["params"]))
            if jsonResponse["func"] == "checkRoomAvailable" and len(jsonResponse["params"]) == 3:
                message_string = """{"func_Response": "Tell the user Room is available and Price for this room is 250 usd. Also Ask the user to confirm if we can make the booking?"}
                    Above is the response from the function call. Please respond to the user accordingly."""
                
            elif jsonResponse["func"] == "book_room" and len(jsonResponse["params"]) == 4:
                message_string = """{"func_Response": "Tell the user your room is booked. Is there anything else we can help you with."}
                    Above is the response from the function call. Please respond to the user accordingly."""
                
            elif jsonResponse["func"] == "changedates" and len(jsonResponse["params"]) == 3:
                message_string = """{"func_Response": "Tell the user The change of dates have been Done for your booking."}"
                    Above is the response from the function call. Please respond to the user accordingly."""
                
            elif jsonResponse["func"] == "roomtypecheck" and len(jsonResponse["params"]) == 3:
                message_string = """{"func_Response" :"Tell the user as of now we have single room available for these dates}"
                    Above is the response from the function call. Please respond to the user accordingly."""
                
            elif jsonResponse["func"] == "rateforroom" and len(jsonResponse["params"]) == 2:
                message_string = """{"func_Response ":"Tell the user The price for this room is 100 usd for 1 day}"
                    Above is the response from the function call. Please respond to the user accordingly."""
            elif jsonResponse["func"] == "closeCall" and (jsonResponse["params"].lower()) == "yes":
                close_call()
                

            if message_string:
                print(message_string)
                
                chat_history.append({"role": "USER", "message": message_string.strip()})
                
                with open('chat_history.txt', 'w') as ch:
                    ch.write(json.dumps({"role": "USER", "message": message_string.strip()}))
                
                response_stream =  call_chat_bot(query, chat_history, preamble)   
                processed_content = ""
                await asyncio.sleep(0)
                for event in response_stream:
                    if event.event_type == "stream-end":
                        content = event.response.text
                        chat_history.append({"role": "CHATBOT", "message": content.strip()})
                        
                        with open('chat_history.txt', 'w') as ch:
                            ch.write(json.dumps({"role": "USER", "message": content.strip()}))
                        
                        await handle_llm_response(content, True)

    return chat_history
