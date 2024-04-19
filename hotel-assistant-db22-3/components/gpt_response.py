
import json
import os
import openai
from dotenv import load_dotenv
import time
import re
import sounddevice as sd
import soundfile as sf
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY_GPT")
if openai_api_key is None:
    raise ValueError("The OPENAI_API_KEY is not set in the environment.")
model = "gpt-3.5-turbo"

# Format the prompt as a conversation, if necessary

# Load the environment variables from .env file


def gpt_get_category(query, system_message):

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"user query: {query}"},
    ]
    # Call to OpenAI chat API
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        api_key=openai_api_key,  # Use the API key from the environment variable
    )

    # Get the answer from OpenAI
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "No answer found.")
        .strip()
    )
    if content.strip():
            
        pattern = r"\{.*?\}"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches

    
    return content


def gpt_get_user_info(info, chat_history, query, get_user_info_prompt):
    print('--> Sending query to GPT')
    filename = 'assets/fillers/cat1fillerno3.wav'
    d, fs = sf.read(filename)
    sd.play(d, fs)

    # Format the prompt as a conversation, if necessary
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

    # Call to OpenAI chat API
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        api_key=openai_api_key,  # Use the API key from the environment variable
    )

    # Get the answer from OpenAI
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "No answer found.")
        .strip()
    )
    if content.strip():
            
        pattern = r"\{.*?\}"
        matches = re.findall(pattern, content, re.DOTALL)
        matches = json.loads(matches[0])
        return matches

    return content



def gpt_final_sub_sub_category(sub_category, query,final_sub_sub_category_prompt, output_filename):
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

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        api_key=openai_api_key,  # Use the API key from the environment variable
    )

    # Get the answer from OpenAI
    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "No answer found.")
        .strip()
    )
    # if content.strip():
            
    pattern = r"\{.*?\}"
    matches = re.findall(pattern, content, re.DOTALL)
    matches = json.loads(matches[0])
    return matches

