

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
# from log import print_and_save
from datetime import datetime
import asyncio
import pyautogui as pg 
# from main import print_and_save

import sys
sys.path.append('./components')

from log import print_and_save
load_dotenv()  # Load environment variables

PPLX_API_KEY = os.getenv("PPLX_API_KEY")

PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
client = Client(user_id=PLAYHT_USER_ID, api_key=PLAYHT_API_KEY)
# options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")
options = TTSOptions(voice="s3://voice-cloning-zero-shot/2bc098a7-c1fc-4b32-9452-556c5ab4814e/jason/manifest.json")
sample_rate = 24000 


stop_playing = False
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
                time.sleep(0.5)  # Wait for 1 second before retrying
            else:
                raise  

processed_sentences = set()
sentence_end_pattern = re.compile(r'(?<=[.?!])\s')

async def handle_gpt_response(full_content):
    global stop_playing
    await asyncio.sleep(0)
    sentences = re.split(r'[.!?]', full_content)
    # print('1',sentences)
    sentences = [s.strip() for s in sentences if s]
    # print('2',sentences)

    for sentence in sentences:
        # print('3',sentence)
        if sentence not in processed_sentences:
            # print('4',sentence)
            if stop_playing:
                return
            if 'have a great day' in sentence.lower():
                play_audio_from_text(sentence)
                
                print('Call ended from our side.')
                self_end_call = pg.locateOnScreen('assets/buttons/self_end_call.png', confidence = 0.98)
                if self_end_call:
                    pg.click(self_end_call)
                    pg.mouseDown()
                    time.sleep(0.1)  # Short delay to simulate a real click
                    pg.mouseUp()
                else:
                    print('self_end_call button not found')
                
                return
            else:
                play_audio_from_text(sentence)
                print('sentence sent to playht: ', sentence)
                processed_sentences.add(sentence)

# Function to handle chat with user and then play response as audio
async def pplx_streaming(messages, chat_history, query, output_filename):
    global stop_playing
    global processed_sentences
    processed_sentences.clear()
    if query is None:
        print("Query is None. Skipping the request.")
        return chat_history
    chat_history_str = str(chat_history)
    model_name = "llama-2-70b-chat"
    previous_content = ""  # Keep track of what content has already been processed

    response_stream = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        api_base="https://api.perplexity.ai",
        api_key=PPLX_API_KEY,
        stream=True,
    )

    processed_content = ""
    await asyncio.sleep(0)
    for response in response_stream:
        if 'choices' in response:
            content = response['choices'][0]['message']['content']
            new_content = content.replace(processed_content, "", 1).strip()  # Remove already processed content
            # print(new_content)

            if stop_playing:
                return
            # Split the content by sentence-ending punctuations
            parts = sentence_end_pattern.split(new_content)

            # Process each part that ends with a sentence-ending punctuation
            for part in parts[:-1]:  # Exclude the last part for now
                part = part.strip()
                # if part:
                if part and len(part.split()) > 1:
                    # print('part', part)
                    await handle_gpt_response(part + '.')  # Re-add the punctuation for processing
                    processed_content += part + ' '  # Add the processed part to processed_content

            # Now handle the last part separately
            last_part = parts[-1].strip()
            if last_part:
                # If the last part ends with a punctuation, process it directly
                if sentence_end_pattern.search(last_part):
                    await handle_gpt_response(last_part)
                    processed_content += last_part + ' '
                else:
                    # Otherwise, add it to the sentence buffer to process it later
                    processed_content += last_part + ' '
    if last_part:
        # print(f"Processed part sent to FAISS: '{last_part}'")
        await handle_gpt_response(last_part)
        processed_content += last_part + ' '

    # Append only the complete assistant's response to messages
    if content.strip():        

        messages.append({"role": "assistant", "content": content.strip()})
        # chat_history.append({"role": "user", "content": query})
        # chat_history.append({"role": "assistant", "content": content})
        # print_and_save('LlamaPerplexity', output_filename)
        with open('chat_history.txt', 'w') as ch:
            ch.write(f'"role": "assistant", "content": {content}')
        await print_and_save(f'|Bot| {content} | ', output_filename)
        await print_and_save(str(datetime.now()), output_filename)
        # await print_and_save('\n', output_filename)
        print(content)

        

    return chat_history



def rooms_availability_final_answer(rooms_data, info, chat_user_info, chat_history, query, prompt4, output_filename):
    
    messages = [
        {
            "role": "system",
            "content": (
                prompt4 +  
                f'Chat History: {str(chat_history)}' + 
                f'Info: {str(info)}'
                f'Rooms data: {str(rooms_data)}'
                f'The user has provided the following information: {str(chat_user_info)}'
            )
        },
        {"role": "user", "content": 'User query: ' + query }
    ]

    chat_history = asyncio.run(pplx_streaming(messages, chat_history, query, output_filename)) 
    return chat_history





import argparse
if __name__ == "__main__":
    # Set up a parser for command line arguments
    parser = argparse.ArgumentParser(description="Process some text.")
    parser.add_argument('rooms_data', type=str, help='Argument 1')
    parser.add_argument('info', type=str, help='Argument 2')
    parser.add_argument('chat_user_info', type=str, help='Argument 3')
    parser.add_argument('chat_history', type=str, help='Argument 4')
    parser.add_argument('query', type=str, help='Argument 5')
    parser.add_argument('prompt4', type=str, help='Argument 6')
    parser.add_argument('output_filename', type=str, help='Argument 7')

    # Parse arguments from the command line
    args = parser.parse_args()

    with open("tts_running.txt", "w") as file:
        file.write("tts_running")
    # Call the function with the parsed arguments
    rooms_availability_final_answer(args.rooms_data, args.info, args.chat_user_info, args.chat_history, args.query, args.prompt4, args.output_filename)
    if os.path.exists("tts_running.txt"):
        os.remove("tts_running.txt")