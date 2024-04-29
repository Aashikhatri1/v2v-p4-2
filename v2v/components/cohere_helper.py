
import cohere
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

COHERE_API_KEY = os.getenv('COHERE_API_KEY')
co = cohere.Client(COHERE_API_KEY)

def call_chat_bot(message, chat_history, preamble):
  print('call chat bot called:',datetime.now())

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

    print('call chat bot response received:',datetime.now())
    return response
    
  else:
      raise("preamble is mandatory")
