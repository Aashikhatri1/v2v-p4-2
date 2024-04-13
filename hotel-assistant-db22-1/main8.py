import asyncio
import json
import pyaudio
import websockets
from dotenv import load_dotenv
import pyautogui as pg
import os
import sys
import sounddevice as sd
import soundfile as sf
from datetime import datetime

import subprocess
load_dotenv()

sys.path.append('./components')
sys.path.append('./assets')
import prompts
prompt3 = prompts.prompt3
prompt4 = prompts.prompt4
#from pplx_playht1 import ask_question, final_answer, rooms_availability_final_answer

from gpt_response import gpt_get_user_info, gpt_final_sub_sub_category
# from gpt_streaming import final_booking

get_user_info_prompt = prompts.get_user_info_prompt
final_sub_sub_category_prompt = prompts.final_sub_sub_category_prompt
ask_question_prompt = prompts.ask_question_prompt
create_db_query_prompt = prompts.create_db_query_prompt


from part2 import process_db_query, fetch_sub_category, find_information_all, find_information, find_information_db, final_sub_sub_category, get_user_info, summarise_chat_history, check_room_availability, create_db_query, filter_by_dates

from stt import Transcriber
# from log import print_and_save


new_transcript_received = False

# import csv2json

# csv2json.convert_csv_to_json('data.csv')
# import csv2json
# csv2json.convert_csv_to_json('assets/roomav.csv', 'roomav.json')


# from speech_to_text_new import transcribe_stream
import part2
from async_llama2 import llama_get_category
from playFiles import playAudioFile
import prompts
import uuid
prompt1 = prompts.prompt1
prompt2 = prompts.prompt2

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000
key = os.getenv('DEEPGRAM_API_KEY')

transcription_buffer = []
current_processing_task = None
new_data_event = asyncio.Event()
global current_query 
global previous_query
global task_status
global chat_history
global stop_playing 
task_status = []  #'name' : 'Task-64', 'status': 'done'}
current_query = ''
previous_query = ''
chat_history = []
stop_playing = False
# global output_filename
output_filename  = ''
##########################################

from pymongo import MongoClient
client = MongoClient('mongodb+srv://aiappuser:vYdXfgvsnPL51ExB@cluster0.54uxknw.mongodb.net/')

# Select the database
mongodb = client['V2VBot']

# Select the collection
collection = mongodb['logs']


async def print_and_save(message, file_path='output.txt'):
    
    # print('print_and_save called')
    # Query to find if the document exists
    document = collection.find_one({"time_stamp": file_path})
    # print('document', document)
    # Determine the next message field name
    if document:
        # Find the maximum message index already in use
        message_fields = [field for field in document.keys() if field.startswith("message")]
        if message_fields:
            last_message_index = max([int(field.replace("message", "")) for field in message_fields])
        else:
            last_message_index = 0
        next_message_field = f"message{last_message_index + 1}"
        update_result = collection.update_one({"time_stamp": file_path}, {"$set": {next_message_field: message}})
        # print("Document updated")
    else:
        # If the document does not exist, create a new one with message1
        new_document = {
            "time_stamp": file_path,
            "message1": message
        }
        insert_result = collection.insert_one(new_document)
        # print("Document created")
################################################################################################



################################################################################################
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
    # global previous_query
    global stop_playing
    global current_query
    print('process_transcription called')
    global transcription_buffer, current_processing_task, new_transcript_received

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

    except RuntimeError as e:
        print(f"RuntimeError in process_transcriptions: {str(e)}")
    except Exception as e:
        print(f"Error in process_transcriptions: {str(e)}")


async def step1(query, chat_history, output_filename ):
    print(query)
    print('1')
    category_filler = await llama_get_category(query, chat_history, prompt1, prompt2, output_filename)  # Processes the query to categorize and determine the filler response.
    print('category_filler:', category_filler)
    print('2')
    return category_filler

async def step2(category_filler):
    filler_no, Category, Sub_Category, QuestionType = playAudioFile(category_filler)
    print('3')
    return filler_no, Category, Sub_Category, QuestionType

async def step3(category_filler,filler_no, Category, Sub_Category, QuestionType):
    print('category_filler:', category_filler)
    print('filler_no:', filler_no)
    print('Category:', Category)
    print('Sub_Category:', Sub_Category)
    print('QuestionType:', QuestionType)

    ContextGiven = ''
    for item in category_filler:
        print('4')
        category_dict = json.loads(item[0].replace('\n', ''))
        
        # Check if the dictionary has 'Category' or 'FillerNo' and update the variables accordingly
        if 'Context Given' in category_dict:
            ContextGiven = category_dict['Context Given']

    # Assembling the category information into a dictionary for further processing.
    category = {
        'Category': Category,
        'Sub Category': Sub_Category,
        'QuestionType': QuestionType,
        'ContextGiven': ContextGiven
    }
    print('5')
    return category

async def process_transcription_data(name):
    global output_filename
    global task_status    
    global chat_history
    if os.path.exists('chat_history.txt'):
        with open('chat_history.txt', 'r') as ch:
            ch = ch.read()
            ch = [ch]
        chat_history.append(ch)
        os.remove('chat_history.txt')
    print('chat_history:', chat_history)
    print('previous_query1:', previous_query)
    print('current_query1:', current_query)
    query = previous_query + '\n'+ current_query
    chat_history.append(f'"role": "user", "content": {query}')
    print(type(chat_history))
    with open("data.json", "r") as file:
        data = json.load(file)
    # output_filename = 'assets/log/'+ datetime.now().strftime('%d-%m-%Y_%H-%M-%S') + '.txt'
    
    
    chat_user_info = {}
    filename = "assets/intro.wav"
    global new_transcript_received
    try: 
        await asyncio.sleep(0)
        await print_and_save(f'|QUERY| {query}' , output_filename)
        chat_history = await summarise_chat_history(chat_history)
        category_filler = await step1(query,chat_history, output_filename)

        await asyncio.sleep(0)
        # await print_and_save(f'|output category and filler | {category_filler} | ', output_filename)
        await print_and_save(str(datetime.now()), output_filename)

        await asyncio.sleep(0)
        filler_no, Category, Sub_Category, QuestionType = await step2(category_filler)

        await print_and_save(f'|filler_no: {filler_no} | Category: {Category} | Sub_Category: {Sub_Category} | QuestionType: {QuestionType}  ', output_filename)
        await print_and_save(str(datetime.now()), output_filename)

        print('running')
        await asyncio.sleep(0)
        category = await step3(category_filler,filler_no, Category, Sub_Category, QuestionType)

        await print_and_save(f'|category | {category} | ', output_filename)
        await print_and_save(str(datetime.now()), output_filename)
        print('category:', category)
        await asyncio.sleep(0)
        # chat_history, chat_user_info = await step4(data, category, output_filename, chat_history, chat_user_info)

        with open("room.json", "r") as file:
            rooms_data = json.load(file)
        # Assuming category now includes 'QuestionType'
        question_type = category.get("QuestionType")
        ContextGiven = category.get('ContextGiven')

        await asyncio.sleep(0)

        if question_type == "FAQ":
            print("General Inquiry - FAQ")
            await print_and_save("General Inquiry - FAQ", output_filename)
            await print_and_save(str(datetime.now()), output_filename)
            if ContextGiven == "No":
                await asyncio.sleep(0)
                await print_and_save("| ContextGiven: " + ContextGiven , output_filename)
                # chat_history = await final_answer('', chat_history, query, prompt3, output_filename)
                # args = ['', str(chat_history), query, prompt3, output_filename]
                args = [
                    f'" "', 
                    f'"{chat_history}"', 
                    f'"{query}"', 
                    f'"{prompt3}"', 
                    f'"{output_filename}"'
                ]
                cmd = ["python", "tts2.py"] + args
                subprocess.Popen(cmd, shell=False)
                
                set_or_add_value_by_name(name, 'done')
                await asyncio.sleep(0)
                return chat_history
            else:
                await asyncio.sleep(0)
                print('ContextGiven 2', ContextGiven)
                await print_and_save("| ContextGiven: " + ContextGiven , output_filename)
                info = await find_information(data, category)  
                print('info: ', info)
                await asyncio.sleep(0)
                # await print_and_save('LlamaPerplexity', output_filename)
                await print_and_save(f'|FAQ INFO| {info} | ', output_filename)
                await print_and_save(str(datetime.now()), output_filename)
                await print_and_save('\n', output_filename)
                await asyncio.sleep(0)
                # chat_history = await final_answer(info, chat_history, query, prompt3, output_filename)
                # args = [info, str(chat_history), query, prompt3, output_filename]
                args = [
                    f'"{info}"', 
                    f'"{chat_history}"', 
                    f'"{query}"', 
                    f'"{prompt3}"', 
                    f'"{output_filename}"'
                ]
                cmd = ["python", "tts2.py"] + args
                subprocess.Popen(cmd, shell=False)

                set_or_add_value_by_name(name, 'done')
                await asyncio.sleep(0)
                return chat_history
        # elif question_type == "DB":
        else:
            await asyncio.sleep(0)
            print("DB Inquiry")
            await print_and_save("DB Inquiry", output_filename)

            sub_sub_category_list = await fetch_sub_category(category, question_type)
            # print('sub_sub_category_list:', sub_sub_category_list)
            await asyncio.sleep(0)
            sub_sub_category_list = json.loads(sub_sub_category_list)

            final_sub_sub_category_ = await final_sub_sub_category(sub_sub_category_list, query, final_sub_sub_category_prompt, output_filename)
            await asyncio.sleep(0)
            # await print_and_save('LlamaPerplexity', output_filename)
            await print_and_save(f'|output| {final_sub_sub_category_} | ', output_filename)
            await print_and_save(str(datetime.now()), output_filename)
            # await print_and_save('\n', output_filename)
            await asyncio.sleep(0)
            print('final_sub_sub_category:', final_sub_sub_category_)
            
            info = await find_information_db(data, final_sub_sub_category_)
            print('db info:',info)
            await asyncio.sleep(0)
            # await print_and_save('LlamaPerplexity', output_filename)
            await print_and_save(f'|DB INFO| {info} | ', output_filename)
            await print_and_save(str(datetime.now()), output_filename)
            # await print_and_save('\n', output_filename)
            await asyncio.sleep(0)
            if info != []:
                await asyncio.sleep(0)
                for info_item in info:
                    if 'Information Required From Client' in info_item:
                        value = info_item['Information Required From Client']
                        # if value is not None and value != 'N/A':
                        if value is not None and value != 'NA':
                            
                            # await print_and_save('LlamaPerplexity', output_filename)
                            await print_and_save(f'|GET USER INFO| {chat_user_info} | ', output_filename)
                            await print_and_save(str(datetime.now()), output_filename)
                            # await print_and_save('\n', output_filename)

                            await asyncio.sleep(0)
                            if chat_user_info == {}:
                                user_info = await get_user_info(info, chat_history, query, get_user_info_prompt)
                                await print_and_save(f'|GET USER INFO| {user_info} | ', output_filename)
                                chat_user_info = {**chat_user_info, **user_info}
                                print('chat_user_info: ', chat_user_info)
                                await print_and_save(f'|chat_user_info: {chat_user_info} | ', output_filename)
                                await asyncio.sleep(0)
                                # chat_history= await ask_question(chat_user_info, chat_history, query, ask_question_prompt, output_filename)

                                # args = [str(chat_user_info), str(chat_history), query, ask_question_prompt, output_filename]
                                args = [
                                    f'"{chat_user_info} "', 
                                    f'"{chat_history}"', 
                                    f'"{query}"', 
                                    f'"{ask_question_prompt}"', 
                                    f'"{output_filename}"'
                                ]
                                print(args)
                                # cmd = ["start", "cmd", "/k", "python", "tts1.py"] + args
                                cmd = ["python", "tts1.py"] + args
                                subprocess.Popen(cmd, shell=False)

                                set_or_add_value_by_name(name, 'done')
                                await asyncio.sleep(0)
                                return chat_history
                            elif 'N/A' in chat_user_info.values():
                                print('Get missing info from user')
                                print('chat_user_info: ', chat_user_info)
                                missing_info = {k: v for k, v in chat_user_info.items() if v == 'N/A'}
                                print('missing_info: ', missing_info)
                                info = str(info) + "The following is the missing info from the user, If it is found in chat history or user query, fill it, otherwise write 'N/A' " +  str(missing_info)
                                user_info = await get_user_info(info, chat_history, query, get_user_info_prompt)
                                await print_and_save(f'|get_user_info: {user_info} | ', output_filename)

                                user_info = {k: v for k, v in user_info.items() if v != 'N/A'}
                                chat_user_info = {**chat_user_info, **user_info}
                                print('chat_user_info: ', chat_user_info)
                                await print_and_save(f'|chat_user_info: {chat_user_info} | ', output_filename)

                                await asyncio.sleep(0)
                                
                                # chat_history= await ask_question(chat_user_info, chat_history, query, ask_question_prompt, output_filename)
                                # args = [str(chat_user_info), str(chat_history), query, ask_question_prompt, output_filename]
                                args = [
                                    f'"{chat_user_info} "', 
                                    f'"{chat_history}"', 
                                    f'"{query}"', 
                                    f'"{ask_question_prompt}"', 
                                    f'"{output_filename}"'
                                ]
                                print(args)
                                cmd = ["python", "tts1.py"] + args
                                subprocess.Popen(cmd, shell=False)

                                set_or_add_value_by_name(name, 'done')
                                await asyncio.sleep(0)
                                return chat_history
                            else:

                                await asyncio.sleep(0)
                                # play filler
                                print('No missing info')

                                filename = 'assets/fillers/one_more_sec.wav'
                                d, fs = sf.read(filename)
                                sd.play(d, fs)
                                
                                dates = await create_db_query(info, chat_history, query, create_db_query_prompt, output_filename)
                                await print_and_save(f'|DB query: {dates} | ', output_filename)
                                print(dates)
                            
                                filtered_rooms_data = await filter_by_dates(rooms_data, dates)
                                print('filtered_rooms_data: ',filtered_rooms_data)
                                await print_and_save(f'|filtered_rooms_data: {filtered_rooms_data} | ', output_filename)
                                await asyncio.sleep(0)
                                # chat_history = final_booking(filtered_rooms_data, info, chat_history, query, prompt4, output_filename)
                                
                                # chat_history = await rooms_availability_final_answer(filtered_rooms_data, info, chat_user_info, chat_history, query, prompt4, output_filename)
                                
                                # args = [str(filtered_rooms_data), str(info), str(chat_user_info), str(chat_history), query, prompt4, output_filename]
                                args = [
                                    f'"{filtered_rooms_data} "', 
                                    f'"{info}"', 
                                    f'"{chat_user_info}"', 
                                    f'"{chat_history}"', 
                                    f'"{query}"', 
                                    f'"{prompt4}"', 
                                    f'"{output_filename}"'
                                ]
                                
                                cmd = ["python", "tts3.py"] + args
                                subprocess.Popen(cmd, shell=False)
                                
                                set_or_add_value_by_name(name, 'done')
                                await asyncio.sleep(0)
                                return chat_history
                        else:
                            await asyncio.sleep(0)
                            print('Information is not required from client.')
                            
                            # chat_history = await rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)
                            
                            # args = ['', str(info), str(chat_user_info), str(chat_history), query, prompt4, output_filename]
                            args = [
                                    f'" "', 
                                    f'"{info}"', 
                                    f'"{chat_user_info}"', 
                                    f'"{chat_history}"', 
                                    f'"{query}"', 
                                    f'"{prompt4}"', 
                                    f'"{output_filename}"'
                                ]
                            cmd = ["python", "tts3.py"] + args
                            subprocess.Popen(cmd, shell=False)
                            
                            set_or_add_value_by_name(name, 'done')
                            await asyncio.sleep(0)
                            return chat_history
                    else:
                        await asyncio.sleep(0)
                        print('Information is not required from client.')
                        
                        # chat_history = await rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)

                        # args = ['', str(info), str(chat_user_info), str(chat_history), query, prompt4, output_filename]
                        args = [
                            f'" "', 
                            f'"{info}"', 
                            f'"{chat_user_info}"', 
                            f'"{chat_history}"', 
                            f'"{query}"', 
                            f'"{prompt4}"', 
                            f'"{output_filename}"'
                        ]
                        cmd = ["python", "tts3.py"] + args
                        subprocess.Popen(cmd, shell=False)
                        
                        set_or_add_value_by_name(name, 'done')
                        await asyncio.sleep(0)
                        return chat_history
            else:
                await asyncio.sleep(0)
                
                # chat_history = await rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)

                # args = ['', str(info), str(chat_user_info), str(chat_history), query, prompt4, output_filename]

                args = [
                    f'" "', 
                    f'"{info}"', 
                    f'"{chat_user_info}"', 
                    f'"{chat_history}"', 
                    f'"{query}"', 
                    f'"{prompt4}"', 
                    f'"{output_filename}"'
                ]
                cmd = ["python", "tts3.py"] + args
                subprocess.Popen(cmd, shell=False)

                set_or_add_value_by_name(name, 'done')
                await asyncio.sleep(0)
                return chat_history
        set_or_add_value_by_name(name, 'done')
        return chat_history


    except asyncio.CancelledError:
        # Perform cleanup here if necessary
        print("Task was cancelled....")
        
        # raise  # It's a good practice to re-raise the CancelledError after handling it
        return
    except Exception as e:
        
        print(f'Error: {str(e)}')
        
        
        # return
    

global stop_pushing
stop_pushing = False  # This flag will control the running tasks.

async def check_call_end_periodically(check_interval=1):
    """Periodically check for the call end button and stop tasks if the end call button is found."""
    global stop_pushing
    # await asyncio.sleep(5)
    end_call = None
    while not stop_pushing:
        end_call = pg.locateOnScreen("assets/buttons/end_call.png", confidence=0.98)
        if end_call:
            print("Call ended")
            stop_pushing = True
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
        chat_history = []
        return

    # Optionally, you can await the cancellation to ensure the tasks are properly cleaned up.
    for task in pending:
        await task  # This ensures that any cleanup in the tasks is executed.


# if __name__ == "__main__":
def chat_with_user():
    global stop_pushing
    global output_filename
    stop_pushing = False
    try:
        filename = "assets/intro.wav"
        data, fs = sf.read(filename)
        sd.play(data, fs)
        output_filename =  datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        asyncio.get_event_loop().run_until_complete(main())
        print("Done!")
        output_filename = ''
        
        return
    
    except RuntimeError as e:
        # Create a new event loop if the default one is closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Error in main function: {str(e)}")


chat_with_user()
# print('End of the program')
