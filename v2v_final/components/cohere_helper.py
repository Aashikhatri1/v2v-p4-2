
import cohere
import soundfile as sf
import sounddevice as sd
import random
from datetime import datetime as dt
import os
from dotenv import load_dotenv
load_dotenv()

COHERE_API_KEY = os.getenv('COHERE_API_KEY')

prmbl=""
co = cohere.Client(COHERE_API_KEY)
def pick_random_audio_file(folder_path):
    audio_files = [file for file in os.listdir(folder_path) if file.endswith(('.wav', '.mp3', '.ogg'))]
    if audio_files:
        random_audio_file = random.choice(audio_files)
        return f"{folder_path}/{random_audio_file}"
    else:
        return None


def play_filler():
    c= dt.now()
    filler = pick_random_audio_file('assets/chatbot_fillers')
    if filler:
        print("Random Filler selected:", filler)
        d, fs = sf.read(filler)
        print(dt.now()-c)
        sd.play(d, fs)
        
    else:
        print("Filler is empty.")



def call_chat_bot(message, chat_history, preamble):
  print('call chat bot called:',dt.now())

#   play_filler()

  if preamble:   
    print(chat_history,type(chat_history))
    response = co.chat_stream(
          chat_history=chat_history,
          message=message,
          temperature = 0.3,
          model = "command-r-plus",
          preamble = preamble,
          connectors=[],
          prompt_truncation = "OFF",
    )

    print('call chat bot response received:',dt.now())
    return response
    
  else:
      raise("preamble is mandatory")
