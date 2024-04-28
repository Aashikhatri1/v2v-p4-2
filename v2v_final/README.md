# v2v-p4

###########################################################################3
To run the code using Call Hippo:

1. Create an account on call Hippo and purchase a number. Call Hippo should be logged in for the code to run.

2. Kamatera default play back device: Line 2(VAC)

3. Call Hippo Audio Settings:

    Output Device: Line 1(VAC)

    Input Device: Line 2(VAC)

4. pip install -r requirements.txt

5. create .env file with all the environment variables: 
    DEEPGRAM_API_KEY
    PLAYHT_API_KEY
    PLAYHT_USER_ID
    OPENAI_API_KEY_GPT
    COHERE_API_KEY 

6. Run main_call_hippo.py

###########################################################################
To run the code on command line interface:

1. Follow previous steps no. 4 and 5. 
2. Run main.py
###########################################################################3

Voice to Voice Bot works in the following way:


It is mainly divided into 3 parts: 

1. Speech To Text:
    The user's voice is converted to text using Deepgram API.

2. Get response from LLM:
    Suitable response is retrieved from LLM according to the data given.
    Cohere's "command-r-plus" model is used to generate the answer.

3. Text To Speech:
    The text is then converted to speech to be sent to the user.
    This is done using Playht API.

