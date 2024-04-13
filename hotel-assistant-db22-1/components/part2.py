import json
import soundfile as sf
import sounddevice as sd
# from groq_playht import ask_question, final_answer, rooms_availability_final_answer
# from pplx_playht_final import ask_question, final_answer, rooms_availability_final_answer
from pplx_playht import ask_question, final_answer, rooms_availability_final_answer
import re
import openai
from dotenv import load_dotenv
import os
import requests
import sys
sys.path.append('./assets')
import prompts
prompt3 = prompts.prompt3
prompt4 = prompts.prompt4
from log import print_and_save
from datetime import datetime
from gpt_response import gpt_get_user_info, gpt_final_sub_sub_category
# from gpt_streaming import final_booking

get_user_info_prompt = prompts.get_user_info_prompt
final_sub_sub_category_prompt = prompts.final_sub_sub_category_prompt
ask_question_prompt = prompts.ask_question_prompt
create_db_query_prompt = prompts.create_db_query_prompt

# Load environment variables from .env file
load_dotenv()

# Access environment variables
PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
os.environ["PPLX_API_KEY"] = PPLX_API_KEY

model_name = "llama-2-70b-chat"
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(
    api_key=GROQ_API_KEY,
)

# Path to your JSON file
filename = "data.json"

# Load JSON data from the file
with open(filename, "r") as file:
    data = json.load(file)

with open("room.json", "r") as file:
    rooms_data = json.load(file)

def process_db_query(question):
    url = f"http://localhost:8000/process-query/?question={question}"
    try:
        response = requests.get(url, timeout=30)  # 10-second timeout
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return "Response time exceeded. Please try again later."
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return {}


# Note: This function assumes your data.json structure includes 'Category', 'Sub Category', and optionally 'Sub Sub Category'.
async def fetch_sub_category(category, question_type):
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print("File not found. Ensure 'data.json' exists in the correct path.")
        return {}

    filtered_data = [
        entry
        for entry in data
        if entry["Category"] == category["Category"]
        and entry.get("Sub Category") == category.get("Sub Category")
    ]

    if not filtered_data:
        result_json = json.dumps(
            {
                "Category": category.get("Category", "N/A"),
                "Sub Category": category.get("Sub Category", "N/A"),
                "Sub Sub Category": "",  # Assuming you want an empty string if no sub-sub-category exists
                "QuestionType": question_type,  # Adding QuestionType
            },
            indent=4,
        )
    else:
        result = []
        for item in filtered_data:
            result.append(
                {
                    "Category": item["Category"],
                    "Sub Category": item.get("Sub Category", "N/A"),
                    "Sub Sub Category": item.get("Sub Sub Category", "N/A"),
                    "QuestionType": question_type,  # Adding QuestionType
                }
            )
        result_json = json.dumps(result, indent=4)

    print("Result JSON:", result_json)
    return result_json


async def find_information_all(data, criteria_list):
    results = []
    for criteria in criteria_list:
        # Ensure criteria is a dictionary
        if isinstance(criteria, dict):
            match_found = False
            for item in data:
                if all(item.get(key) == value for key, value in criteria.items()):
                    results.append(item.get("Information Required From Client", "Information not found"))
                    match_found = True
                    break
            if not match_found:
                results.append("Information not found")
        else:
            print("Error: criteria is not a dictionary", criteria)
    return results


async def find_information(data, criteria):
    print('criteria:', criteria)
    results = []

    # Iterate through each item in the JSON data
    for item in data:
        # Check if the item matches the Category and Sub Category in your criteria
        if item.get('Category') == criteria['Category'] and item.get('Sub Category') == criteria['Sub Category']:
            # Extract the required information
            # info_required = item.get('Information Required From Client', 'No information available')
            sample_answer = item.get('Sample Answer', 'No sample answer available')
            
            # Add the extracted information to the results list
            results.append({
                # 'Information Required From Client': info_required,
                'Sample Answer': sample_answer
            })

    return results
    
async def find_information_db(data, criteria):
    print('criteria:', criteria)
    results = []

    # Iterate through each item in the JSON data
    for item in data:
        # Check if the item matches the Category and Sub Category in your criteria
        if item.get('Category') == criteria['Category'] and item.get('Sub Category') == criteria['Sub Category'] and item.get('Sub Sub Category') == criteria['Sub Sub Category']:
            # Extract the required information
            info_required = item.get('Information Required From Client')
            sample_answer = item.get('Sample Answer', 'No sample answer available')
            
            # Add the extracted information to the results list
            results.append({
                'Information Required From Client': info_required,
                'Sample Answer': sample_answer
            })

    return results

async def final_sub_sub_category(sub_category, query,final_sub_sub_category_prompt, output_filename):
    messages = [
        {
            "role": "system",
            "content": (
                final_sub_sub_category_prompt 
                + f'Options: {str(sub_category)}'
            ),
        }
    ]

    messages.append({"role": "user", "content": f"user query: {query}"})

    chat_completion = client.chat.completions.create(
        messages=messages,
        model= "mixtral-8x7b-32768",
        temperature=0.5,
        max_tokens=32768,
        top_p=1,
        stop=None,
    )

    content = chat_completion.choices[0].message.content
    
    # base, extension = output_filename.rsplit('.', 1)
    # detailed_filename = f"{base}_detailed.{extension}"

    # await print_and_save('LlamaPerplexity', output_filename)
    await print_and_save(f'|prompt to get final_sub_sub_category| {messages} | ', output_filename)
    await print_and_save(str(datetime.now()), output_filename)
    # await print_and_save('\n', output_filename)

    pattern = r"\{.*?\}"
    if content.strip() and re.findall(pattern, content, re.DOTALL):
        matches = re.findall(pattern, content, re.DOTALL)
        matches = matches[0].replace("'", '"')
        matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
        matches = json.loads(matches)
        return matches
    
    else:    
        print('--> Sending query to Llama again')
        chat_completion = client.chat.completions.create(
            messages=messages,
            model= "mixtral-8x7b-32768",
            temperature=0.5,
            max_tokens=32768,
            top_p=1,
            stop=None,
        )

        content = chat_completion.choices[0].message.content
        if content.strip() and re.findall(pattern, content, re.DOTALL):
            matches = re.findall(pattern, content, re.DOTALL)
            matches = matches[0].replace("'", '"')
            matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
            matches = json.loads(matches)
            return matches
        else:
            print('--> Sending query to GPT')
            d, fs = sf.read('assets/fillers/one_more_sec.wav')
            sd.play(d, fs)
            matches = gpt_final_sub_sub_category(sub_category, query,final_sub_sub_category_prompt, output_filename)
            return matches


async def get_user_info(info, chat_history, query, get_user_info_prompt):
    model_name ="mixtral-8x7b-32768"
    messages = [
        {
            "role": "system",
            "content": (
                
                
                f'Info: {str(info)}' +
                get_user_info_prompt +
                f'Chat History: {str(chat_history)}'
            ),
        }
    ]

    messages.append({"role": "user", "content": f"user query: {query}"})

    chat_completion = client.chat.completions.create(
        messages=messages,
        model= model_name,
        temperature=0.5,
        max_tokens=32768,
        top_p=1,
        stop=None,
    )

    content = chat_completion.choices[0].message.content
    print('content' , content)

    pattern = r"\{.*?\}"
    
    if content.strip() and re.findall(pattern, content, re.DOTALL):
        matches = re.findall(pattern, content, re.DOTALL)
        matches = matches[0].replace("'", '"')
        matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
        matches = json.loads(matches)
        for i in matches:
            if not 'Information Required From Client' in i:
                return matches
            else:
                print('--> Sending query to Llama again')
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model= model_name,
                    temperature=0.5,
                    max_tokens=32768,
                    top_p=1,
                    stop=None,
                )

                content = chat_completion.choices[0].message.content
                if content.strip()  and re.findall(pattern, content, re.DOTALL):
                    matches = re.findall(pattern, content, re.DOTALL)
                    matches = matches[0].replace("'", '"')
                    matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
                    matches = json.loads(matches)
                    for i in matches:
                        if not 'Information Required From Client' in i:
                            return matches 
                        else:
                            matches = gpt_get_user_info(info, chat_history, query, get_user_info_prompt)
                            return matches
                else:
                    matches = gpt_get_user_info(info, chat_history, query, get_user_info_prompt)
                    return matches
    else:
        print('--> Sending query to Llama again')
        chat_completion = client.chat.completions.create(
            messages=messages,
            model= model_name,
            temperature=0.5,
            max_tokens=32768,
            top_p=1,
            stop=None,
        )

        content = chat_completion.choices[0].message.content
        if content.strip()  and re.findall(pattern, content, re.DOTALL):
            matches = re.findall(pattern, content, re.DOTALL)
            matches = matches[0].replace("'", '"')
            matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
            matches = json.loads(matches)
            for i in matches:
                if not 'Information Required From Client' in i:
                    return matches 
                else:
                    matches = gpt_get_user_info(info, chat_history, query, get_user_info_prompt)
                    return matches
        else:
            matches = gpt_get_user_info(info, chat_history, query, get_user_info_prompt)
            return matches
        

async def summarise_chat_history(chat_history):
    # if len(chat_history) > 3:
    if len(chat_history) > 10:
        messages = [
            {
                "role": "system",
                "content": (
                    '''Summarise the given chat history very accurately in 150 words or less. Retain the important information such as date of booking, no. of guests etc. Start with "The user" not "A User".'
                    For room booking conversation, write 'user wants to book a room', not 'user booked a room'. Do not assume any information. Please Do not make any mistakes. '''
                ),
            }
        ]

        messages.append({"role": "user", "content": f'Chat History: {str(chat_history)}'})

        # response_stream = openai.ChatCompletion.create(
        #     model=model_name,
        #     messages=messages,
        #     api_base="https://api.perplexity.ai",
        #     api_key=PPLX_API_KEY,
        #     stream=True,
        # )

        # for response in response_stream:
        #     if "choices" in response:
        #         content = response["choices"][0]["message"]["content"]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model= "mixtral-8x7b-32768",
            temperature=0.5,
            max_tokens=32768,
            top_p=1,
            stop=None,
        )

        content = chat_completion.choices[0].message.content
        print('content' , content)

        # if content.strip():
        content = [content]

        return content
    else:
        return chat_history

def check_room_availability(rooms_data, dates):
    
    # Function to find available rooms for given dates
    def find_available_rooms_for_dates(rooms_data, dates):
        available_rooms_by_date = {}
        for date in dates:
            available_rooms_by_date[date] = [room for room in rooms_data if room.get(date, 0) > 0]
        return available_rooms_by_date

    # Fetching available rooms for the specified dates
    available_rooms = find_available_rooms_for_dates(rooms_data, dates)
    
    return available_rooms


async def create_db_query(info, chat_history, query, create_db_query_prompt, output_filename):
    messages = [
        {
            "role": "system",
            "content": (
                create_db_query_prompt +
                f'Info: {str(info)}' +
                f'Chat History: {str(chat_history)}' 
            
            ),
        }
    ]

    messages.append({"role": "user", "content": f"user query: {query}"})

    response_stream = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        api_base="https://api.perplexity.ai",
        api_key=PPLX_API_KEY,
        stream=True,
    )

    for response in response_stream:
        if "choices" in response:
            content = response["choices"][0]["message"]["content"]

    if content.strip():
        print('create_db_query content' , content)
        
        list_start = content.find('["')
        list_end = content.find('"]') + 2
        list_str = content[list_start:list_end]

        # Use a regular expression to find all dates in the format "dd-Mmm-yyyy" within the list
        dates = re.findall(r'\d{2}-[A-Za-z]{3}-\d{2}', list_str)
        dates1 = re.findall(r'\d{1}-[A-Za-z]{3}-\d{2}', list_str)
        dates = dates + dates1
        print('dates:',dates)

    # base, extension = output_filename.rsplit('.', 1)
    # detailed_filename = f"{base}_detailed.{extension}"

    print_and_save('LlamaPerplexity', output_filename)
    print_and_save(f'|DB QUERY DATES| {dates} | ', output_filename)
    print_and_save(str(datetime.now()), output_filename)
    print_and_save('\n', output_filename)

    return dates

async def filter_by_dates(rooms_data, dates):
    filtered_data = [entry for entry in rooms_data if entry["Date"] in dates]
    return filtered_data


async def response_type(query, category, chat_history, output_filename, chat_user_info):

    base, extension = output_filename.rsplit('.', 1)
    detailed_filename = f"{base}_detailed.{extension}"
    
    with open("room.json", "r") as file:
        rooms_data = json.load(file)
    # Assuming category now includes 'QuestionType'
    question_type = category.get("QuestionType")
    ContextGiven = category.get('ContextGiven')
    if question_type == "FAQ":
        print("General Inquiry - FAQ")

        if ContextGiven == "No":
            chat_history = final_answer('', chat_history, query, prompt3, output_filename)
        else:
            info = find_information(data, category)  
            print('info: ', info)

            print_and_save('LlamaPerplexity', detailed_filename)
            print_and_save(f'|FAQ INFO| {info} | ', detailed_filename)
            print_and_save(str(datetime.now()), detailed_filename)
            print_and_save('\n', detailed_filename)

            chat_history = final_answer(info, chat_history, query, prompt3, output_filename)

    # elif question_type == "DB":
    else:
        print("DB Inquiry")

        sub_sub_category_list = fetch_sub_category(category, question_type)
        # print('sub_sub_category_list:', sub_sub_category_list)
       
        sub_sub_category_list = json.loads(sub_sub_category_list)

        final_sub_sub_category_ = final_sub_sub_category(sub_sub_category_list, query, final_sub_sub_category_prompt, output_filename)

        print_and_save('LlamaPerplexity', detailed_filename)
        print_and_save(f'|output| {final_sub_sub_category_} | ', detailed_filename)
        print_and_save(str(datetime.now()), detailed_filename)
        print_and_save('\n', detailed_filename)

        print('final_sub_sub_category:', final_sub_sub_category_)
        
        info = find_information_db(data, final_sub_sub_category_)
        print('db info:',info)

        print_and_save('LlamaPerplexity', detailed_filename)
        print_and_save(f'|DB INFO| {info} | ', detailed_filename)
        print_and_save(str(datetime.now()), detailed_filename)
        print_and_save('\n', detailed_filename)
        
        if info != []:
            for info_item in info:
                if 'Information Required From Client' in info_item:
                    value = info_item['Information Required From Client']
                    # if value is not None and value != 'N/A':
                    if value is not None and value != 'NA':
                        
                        

                        # print_and_save('LlamaPerplexity', detailed_filename)
                        # print_and_save(f'|GET USER INFO| {chat_user_info} | ', detailed_filename)
                        # print_and_save(str(datetime.now()), detailed_filename)
                        # print_and_save('\n', detailed_filename)


                        if chat_user_info == {}:
                            user_info = get_user_info(info, chat_history, query, get_user_info_prompt)

                            chat_user_info = {**chat_user_info, **user_info}
                            print('chat_user_info: ', chat_user_info)
                            chat_history= ask_question(chat_user_info, chat_history, query, ask_question_prompt, output_filename)
                            

                        elif 'N/A' in chat_user_info.values():
                            print('Get missing info from user')
                            print('chat_user_info: ', chat_user_info)
                            missing_info = {k: v for k, v in chat_user_info.items() if v == 'N/A'}
                            print('missing_info: ', missing_info)
                            info = str(info) + "The following is the missing info from the user, If it is found in chat history or user query, fill it, otherwise write 'N/A' " +  str(missing_info)
                            user_info = get_user_info(info, chat_history, query, get_user_info_prompt)
                            user_info = {k: v for k, v in user_info.items() if v != 'N/A'}
                            chat_user_info = {**chat_user_info, **user_info}
                            print('chat_user_info: ', chat_user_info)
                            chat_history= ask_question(chat_user_info, chat_history, query, ask_question_prompt, output_filename)
                        
                            
                        else:
                            # play filler
                            print('No missing info')

                            filename = 'assets/fillers/cat2fillerno1.wav'
                            d, fs = sf.read(filename)
                            sd.play(d, fs)
                            
                            dates = create_db_query(info, chat_history, query, create_db_query_prompt, output_filename)
                            print(dates)
                            filtered_rooms_data = filter_by_dates(rooms_data, dates)
                            print('filtered_rooms_data: ',filtered_rooms_data)
                            
                            # chat_history = final_booking(filtered_rooms_data, info, chat_history, query, prompt4, output_filename)
                            chat_history = rooms_availability_final_answer(filtered_rooms_data, info, chat_user_info, chat_history, query, prompt4, output_filename)
                            
                    else:
                        print('Information is not required from client.')
                        chat_history = rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)
                
                else:
                    print('Information is not required from client.')
                    chat_history = rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)

        else:
            chat_history = rooms_availability_final_answer("", info, chat_user_info, chat_history, query, prompt4, output_filename)
        
    # print('chat_user_info: ', chat_user_info)
    return chat_history, chat_user_info
