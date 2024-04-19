import json
import sounddevice as sd
import soundfile as sf

def getjson(text):
    print('Processing text to extract details...')
    filler_no, Category, Sub_Category, QuestionType = '', '', '', ''
    for item in text:
        
        # Remove newline characters and load the JSON string into a Python dictionary
        category_dict = json.loads(item[0].replace('\n', ''))
        
        # Check if the dictionary has 'Category' or 'FillerNo' and update the variables accordingly
        
        if 'Category' in category_dict:
            Category = category_dict['Category']
        if 'Sub Category' in category_dict:
            Sub_Category = category_dict['Sub Category']
        if 'Sub Sub Category' in category_dict:
            Sub_Sub_Category = category_dict['Sub Sub Category']
        if 'FillerNo' in category_dict:
            filler_no = category_dict['FillerNo']
        if 'QuestionType' in category_dict:
            QuestionType = category_dict['QuestionType']
           
    return filler_no, Category, Sub_Category, QuestionType



def playAudioFile(answer):
    # Extract category details from the answer
    filler_no, Category, Sub_Category, QuestionType = getjson(answer)

    if QuestionType == 'FAQ':
        type_value = 1
    else:
        type_value = 2
    
    file_name = f'assets/fillers/cat{type_value}fillerno{filler_no}.wav'
    print(f'Playing audio file: {file_name}')
    
    # Play the selected audio file
    play_audio(file_name)
    
    # Return the extracted details for further processing if needed
    return filler_no, Category, Sub_Category,QuestionType

def play_audio(filename):
    # Read and play the specified audio file
    try:
        data, fs = sf.read(filename)
        sd.play(data, fs)
        # sd.wait()  # Wait until the audio file has finished playing
    except Exception as e:
        print(f"Error playing audio file {filename}: {e}")

