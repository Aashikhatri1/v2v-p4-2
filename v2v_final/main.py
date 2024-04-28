import asyncio
import json
from dotenv import load_dotenv
import pyautogui as pg
import os
import sys
import sounddevice as sd
import soundfile as sf
from datetime import datetime
import uuid

load_dotenv()

sys.path.append('./components')
sys.path.append('./assets')
from preamble_file import get_preamble
import tts_cohere
from stt import Transcriber

new_transcript_received = False

transcription_buffer = []
current_processing_task = None
new_data_event = asyncio.Event()

preamble=''

task_status = []  
current_query = ''
previous_query = ''
chat_history = []
stop_playing = False
output_filename  = ''

async def handle_transcript(transcript):
    global stop_playing
    global previous_query
    print('handle transcript called')
    global current_processing_task, transcription_buffer, new_transcript_received

    try: 
        if transcript and not transcript.isspace():
            transcription_buffer.append(transcript)
            
            # Signal that a new transcript has been received.
            new_transcript_received = True
            print('handle_transcript')
            
            if current_processing_task:
                print('current processing task  ', current_processing_task)
                print(get_value_by_name(current_processing_task.get_name()))
                if get_value_by_name(current_processing_task.get_name()) !='done': #and os.path.exists("tts_running.txt"):
                    print('process stopped --handle transcript 1')
                    print('previous_query:', previous_query)
                    print('current_query:', current_query)
                    
                    previous_query = current_query
                    # current_processing_task.cancel()
                    stop_playing = True
                elif get_value_by_name(current_processing_task.get_name()) =='done' and os.path.exists("tts_running.txt"):
                    print('process stopped --handle transcript 2')
                    with open('stop_playing.txt', 'w') as file:
                        file.write('True')
                    previous_query = current_query
                else:
                    previous_query = ''
                    
            if current_processing_task and not current_processing_task.done():

                print('process stopped --handle transcript 3')
                print('previous_query:', previous_query)
                print('current_query:', current_query)
                previous_query = current_query
                
                current_processing_task.cancel()
                stop_playing = True
                print('task cancelled in handle transcript')

            elif current_processing_task and current_processing_task.done() and os.path.exists("tts_running.txt"):
                print('process stopped --handle transcript 4')
                with open('stop_playing.txt', 'w') as file:
                    file.write('True')
                
            else:
                previous_query = ''
                
            
            new_data_event.set()

    except Exception as e:
        print('Error in handle_transcript:', e)

def get_value_by_name(name):
    for task in task_status:
        if task["name"] == name:
            return task["value"]
    return None  

def add_task(name, value):
    task_status.append({"name": name, "value": value})

def set_or_add_value_by_name(name, new_value):
    for task in task_status:
        if task["name"] == name:
            task["value"] = new_value
            return "Updated"
    # If the task is not found, add a new one
    add_task(name, new_value)
    return "Added"
async def process_transcriptions():
    
    global stop_playing, current_query, transcription_buffer, current_processing_task, new_transcript_received

    print('process_transcription called')

    try:
        while True:
            await new_data_event.wait()
            
            # Clear the event early to ensure it's ready for next signaling.
            new_data_event.clear()
            
            if transcription_buffer:
                print('transcription buffer')
                data_to_process = " ".join(transcription_buffer)
                transcription_buffer = []  # Clear buffer after copying
                
                print('current processing task ', current_processing_task )
                
                # Cancel any ongoing processing task before starting a new one.
                if current_processing_task and not current_processing_task.done():
                    print('process stopped --process_transcriptions 1')
                    print('previous_query 2:', previous_query)
                    print('current_query 2 :', current_query)
                    previous_query = current_query
                    print('previous_query 3:', previous_query)

                    print('current_processing_task 2: ' , current_processing_task)
                    current_processing_task.cancel()
                    stop_playing = True
                    print('task cancelled in process_transcriptions')
                    await current_processing_task  # Wait for the task to be cancelled


                print('current query ', current_query)
                current_query = data_to_process
                print('current query ', current_query)
                
                unique_value = uuid.uuid4()
                current_processing_task = asyncio.create_task(process_transcription_data(unique_value))
                if os.path.exists('stop_playing.txt'):
                    os.remove('stop_playing.txt')
                current_processing_task.set_name(unique_value)
                set_or_add_value_by_name(current_processing_task.get_name(), 'in progress')
                stop_playing = False
                # print(current_processing_task.done)
                print('current_processing_task: ' , current_processing_task)
                try:
                    await current_processing_task
                except asyncio.CancelledError:
                    print("Processing was cancelled due to new transcript.")

    except Exception as e:
        print(f"Error in process_transcriptions: {str(e)}")




async def process_transcription_data(name):
    global output_filename, task_status, chat_history, preamble
   
    if os.path.exists('chat_history.txt'):
        with open('chat_history.txt', 'r') as ch:
            ch = ch.read()
            ch = json.loads(ch)
        chat_history.append(ch)
        os.remove('chat_history.txt')
    print('query rec:',datetime.now())
    print('chat_history:', chat_history)
    print('previous_query1:', previous_query)
    print('current_query1:', current_query)
    query = previous_query + '\n'+ current_query
    chat_history.append({"role": "USER", "message": query})

    print(type(chat_history))
    
    try: 
        await asyncio.sleep(0)

        print('query sent to tts cohere:',datetime.now())
        

        await tts_cohere.cohere_response(chat_history,query, output_filename, str(preamble))
        
        set_or_add_value_by_name(name, 'done')
        print('process_transcription_data done:',datetime.now())
        await asyncio.sleep(0)
        return chat_history    

    except asyncio.CancelledError:
        
        print("Task was cancelled....")
        return
    except Exception as e:
        
        print(f'Error: {str(e)}')

        # return
    

global stop_pushing
stop_pushing = False  # This flag will control the running tasks.

async def check_call_end_periodically(check_interval=1):
    """Periodically check for the call end button and stop tasks if the end call button is found."""
    global stop_pushing
    
    end_call = None
    while not stop_pushing:
        end_call = pg.locateOnScreen("assets/buttons/end_call.png", confidence=0.98)
        if end_call:
            print("Call ended")
            stop_pushing = True
            return
        await asyncio.sleep(check_interval)

async def main():
    global chat_history
    DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
    if DEEPGRAM_API_KEY is None:
        print("Please set the DEEPGRAM_API_KEY environment variable.")
        return
    print('Start Speaking...')
    transcriber = Transcriber(on_transcript=handle_transcript)
    transcription_task = asyncio.create_task(transcriber.run(DEEPGRAM_API_KEY))
    processing_task = asyncio.create_task(process_transcriptions())
    call_end_check_task = asyncio.create_task(check_call_end_periodically())

    # Wait for any task to complete. If call_end_check_task completes, it indicates the call ended.
    done, pending = await asyncio.wait(
        [transcription_task, processing_task, call_end_check_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # If the call_end_check_task is done, cancel other tasks.
    if call_end_check_task in done:
        transcription_task.cancel()
        processing_task.cancel()
        print("All tasks cancelled due to call end.")
        
        if os.path.exists('chat_history.txt'):
            os.remove('chat_history.txt')
    
        chat_history = []
        return

    # Optionally, we  can await the cancellation to ensure the tasks are properly cleaned up.
    for task in pending:
        await task  # This ensures that any cleanup in the tasks is executed.


def exitCall():
    global chat_history
    print("Exiting call")
    if os.path.exists('chat_history.txt'):
        os.remove('chat_history.txt')
        chat_history = []

def chat_with_user():
    global stop_pushing
    global output_filename
    global preamble
    stop_pushing = False
    try:
        filename = "assets/intro.wav"
        data, fs = sf.read(filename)
        sd.play(data, fs)
        preamble=get_preamble()
        output_filename =  datetime.now().strftime('%d-%m-%Y_%H-%M-%S')

        asyncio.get_event_loop().run_until_complete(main())
        print("Done!")
        output_filename = ''
        
        return
    
    except KeyboardInterrupt as ke:
        print(ke,"Key Pressed")
        exitCall()
    except RuntimeError as e:
        # Create a new event loop if the default one is closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Error in main function: {str(e)}")


chat_with_user()

