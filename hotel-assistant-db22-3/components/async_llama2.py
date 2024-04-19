import openai
from dotenv import load_dotenv
import os
import json
from datetime import datetime
# from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from gpt_response import gpt_get_category
# Load environment variables from .env file
load_dotenv()
import sounddevice as sd
import soundfile as sf
import asyncio
# from log import print_and_save


# Access environment variables
PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
os.environ["PPLX_API_KEY"] = PPLX_API_KEY

model_name = "mixtral-8x7b-32768"

from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(
    api_key=GROQ_API_KEY,
)
async def get_category(query, system_message):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"user query: {query}"},
    ]

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
            print(matches)
            matches = matches[0].replace("'", '"')
            print(matches)
            matches = re.sub(r'("\s*:\s*"[^"]*")\s*"', r'\1, "', matches)
            matches = json.loads(matches)
            return matches
                
        else:
            print('--> Sending query to GPT')
            d, fs = sf.read('assets/fillers/one_more_sec.wav')
            sd.play(d, fs)
            matches = gpt_get_category(query, system_message)
            return matches
    

async def run_get_category(query, system_message):
    result = await get_category(query, system_message)  # Assuming get_category can be made async
    result = json.dumps(result)
    result = [result]
    print('result', result)
    return result


async def llama_get_category(query, chat_history, prompt1, prompt2, output_filename):

    prompt1 = prompt1 + f'Ongoing conversation with the user is as follows: {chat_history}'
    prompt2 = prompt2 + f'Ongoing conversation with the user is as follows: {chat_history}'
    
    # Prepare your coroutine tasks
    tasks = [run_get_category(query, prompt1), run_get_category(query, prompt2)]
    
    # Run tasks concurrently and wait for all to finish
    results = await asyncio.gather(*tasks)
    # results = [results]
    print('results:' ,results)
    

    # base, extension = output_filename.rsplit('.', 1)
    # detailed_filename = f"{base}_detailed.{extension}"
    # print(f"Total time taken: {total_time} seconds")

    # print_and_save('LlamaPerplexity', output_filename)
    # await print_and_save(f'|prompt to get category and sub category| {prompt1}{query} | ', output_filename)
    # await print_and_save(f'|prompt to get question type and filler| {prompt2}{query} | ', output_filename)
    # await print_and_save(f'|output category and filler| {results} | ', output_filename)
    # await print_and_save(str(datetime.now()), output_filename)
    # await print_and_save('\n', output_filename)

    return results


