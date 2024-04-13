import sys
sys.path.append('./components')
import json
from async_llama2 import llama_get_category
from playFiles import playAudioFile
import webbrowser
import pyautogui as pg
import time
import threading
from queue import Queue
from datetime import datetime
from speech_to_text_new import transcribe_stream
sys.path.append('./assets')
import part2_new
import prompts
prompt1 = prompts.prompt1
prompt2 = prompts.prompt2
import sounddevice as sd
import soundfile as sf
from log import print_and_save
from main import chat_with_user
# import csv2json
# csv2json.convert_csv_to_json('data.csv')


audio_queue = Queue()
is_audio_playing = False

def audio_worker():
    global is_audio_playing
    while True:
        audio_data, samplerate = audio_queue.get()
        if audio_data is None:
            break  # This is the signal to stop the worker
        is_audio_playing = True
        sd.play(audio_data, samplerate)
        sd.wait()
        is_audio_playing = False
        audio_queue.task_done()


audio_thread = threading.Thread(target=audio_worker)
audio_thread.start()


def open_website(url):
        webbrowser.open(url, new=2)  # new=2 opens in a new tab, if possible

# Opening call hipppo dialer
website = 'https://dialer.callhippo.com/dial'
open_website(website)

time.sleep(7)
pg.scroll(-100)

            
while True:  # Main loop for handling incoming calls
    accept = pg.locateOnScreen("assets/buttons/accept.png", confidence=0.9)
    if accept:
        x, y, width, height = accept
        click_x, click_y = x + width // 2, y + height // 2  # Calculate the center of the button
        print("Call received at coordinates:", (click_x, click_y))
        pg.moveTo(click_x, click_y)  # Move to the center of the button
        time.sleep(0.5)  # Short delay
        pg.mouseDown()
        time.sleep(0.1)  # Short delay to simulate a real click
        pg.mouseUp()
        print("Call accepted")
        chat_with_user()  # Start chat with user
        end_call = pg.locateOnScreen("assets/buttons/end_call.png", confidence = 0.98)
        if end_call:
            pg.click(end_call)
            # pg.mouseDown()
            # time.sleep(0.1)  # Short delay to simulate a real click
            # pg.mouseUp()
            print('Clicked on end call.')
        print("Waiting for next call...")
        time.sleep(5)
    else:
        print("No call detected.")
        time.sleep(5) 
