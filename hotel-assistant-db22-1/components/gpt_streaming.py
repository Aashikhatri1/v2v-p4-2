

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

load_dotenv()  # Load environment variables

PPLX_API_KEY = os.getenv("PPLX_API_KEY")

PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
client = Client(user_id=PLAYHT_USER_ID, api_key=PLAYHT_API_KEY)
# options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")
options = TTSOptions(voice="s3://voice-cloning-zero-shot/2bc098a7-c1fc-4b32-9452-556c5ab4814e/jason/manifest.json")
sample_rate = 24000 

def play_audio_from_text(text):
    success = False
    attempts = 0

    while not success and attempts < 3:  # Try up to 3 times
        try:
            stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32')
            stream.start()

            for chunk in client.tts(text, options):
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
                time.sleep(0.5)  # Wait for 1 second before retrying
            else:
                raise  

processed_sentences = set()
sentence_end_pattern = re.compile(r'(?<=[.?!])\s')

def handle_gpt_response(full_content):
    sentences = re.split(r'[.!?]', full_content)
    sentences = [s.strip() for s in sentences if s]

    for sentence in sentences:
        if sentence not in processed_sentences:
            play_audio_from_text(sentence)
            print('sentence sent to playht: ', sentence)
            processed_sentences.add(sentence)


import re
import os


sentence_end_pattern = re.compile(r'[.!?]')



def gpt_streaming(messages, chat_history, query, output_filename):
    openai_api_key = os.getenv("OPENAI_API_KEY_GPT")
    if openai_api_key is None:
        raise ValueError("The OPENAI_API_KEY is not set in the environment.")
    
    if query is None:
        print("Query is None. Skipping the request.")
        return chat_history

    model_name = "gpt-3.5-turbo"

    response_stream = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        api_key=openai_api_key,
        stream=True,
    )

    sentence_buffer = ""

    for response in response_stream:
        if 'choices' in response and len(response['choices']) > 0:
            choice = response['choices'][0]
            if 'delta' in choice and 'content' in choice['delta']:
                content = choice['delta']['content']
                sentence_buffer += content  # Accumulate content
                
                # Split the accumulated content by sentence-ending punctuations
                parts = sentence_end_pattern.split(sentence_buffer)
                if sentence_end_pattern.search(sentence_buffer):  # Check if there's a sentence end
                    for part in parts[:-1]:  # Process all but the last part
                        handle_gpt_response(part.strip() + '.')  # Re-add the punctuation for processing
                    sentence_buffer = parts[-1]  # The last part is the start of a new sentence

    # If there's remaining content in the buffer after the loop, decide how to handle it
    if sentence_buffer.strip():
        # For example, you might want to process it as well, or log that it's incomplete
        handle_gpt_response(sentence_buffer.strip())
    
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "No answer found.")
        .strip()
    )
    if content.strip():
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": content})

    
    return chat_history

# Make sure to define or adjust `handle_gpt_response` as per your requirements.


def final_booking(rooms_data, info, chat_history, query, prompt4, output_filename):

    print('final_booking_chathistory_input:', chat_history)
    messages = [
        {
            "role": "system",
            "content": (
                prompt4 +  
                f'Chat History: {str(chat_history)}' + 
                f'Info: {str(info)}'
                f'Rooms data: {str(rooms_data)}'
            )
        },
        {"role": "user", "content": query if query else "Default query text."}
    ]
    
    chat_history = gpt_streaming(messages, chat_history, query, output_filename)
    print('final_booking_chathistory_output:', chat_history)
    return chat_history

