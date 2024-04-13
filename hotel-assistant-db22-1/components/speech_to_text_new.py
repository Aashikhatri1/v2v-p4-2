# Speech to text along with chat history summarisation in parallel.

import os
import asyncio
import json
import pyaudio
import websockets
from dotenv import load_dotenv
import pyautogui as pg
import threading
import queue  
import sys

sys.path.append('./components')
from part2_new import summarise_chat_history

load_dotenv()

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000
last_transcript = ""
class Transcriber:
    def __init__(self):
        self.audio_queue = asyncio.Queue()
        self.stream = None  # Placeholder for the PyAudio stream
        self.stop_pushing = False  # Flag to stop pushing data to the queue

    def mic_callback(self, input_data, frame_count, time_info, status_flag):
        if not self.stop_pushing:
            self.audio_queue.put_nowait(input_data)
        return (input_data, pyaudio.paContinue)

    async def sender(self, ws, timeout=1):
        """Send audio data from the microphone to Deepgram."""
        try:
            while not self.stop_pushing:
                mic_data = await asyncio.wait_for(self.audio_queue.get(), timeout)
                await ws.send(mic_data)
        except asyncio.TimeoutError:
            print("Timeout in sender coroutine. Stopping the push.")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection closed unexpectedly in sender: {e}")
        finally:
            self.stop_pushing = True


    async def receiver(self, ws):
        """Receive transcription results from Deepgram."""
        full_transcript = ""  # Initialize an empty string to hold the full transcript
        try:
            async for msg in ws:
                res = json.loads(msg)
                # print(res)
                # Extract transcript from the current message
                transcript = (
                    res.get("channel", {})
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                if transcript.strip():
                    # Append the current transcript to the full transcript
                    full_transcript += transcript + " "
                if res.get("speech_final"):
                    # If the message is marked as speech_final, return the full transcript
                    if full_transcript.strip():
                        return full_transcript.strip()
        except asyncio.TimeoutError:
            print("Timeout occurred in receiver coroutine.")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection closed unexpectedly in receiver: {e}")
        finally:
            if ws.open:
                await ws.close()

    def check_call_end(self):
        """Check for the call end button."""
        end_call = pg.locateOnScreen("assets/buttons/end_call.PNG", confidence=0.98)
        if end_call:
            print("Call ended")
            self.stop_pushing = True

    async def check_call_end_periodically(self, check_interval=1):
        """Periodically check for the call end button."""
        while not self.stop_pushing:
            self.check_call_end()
            await asyncio.sleep(check_interval)

    async def run(self, key):
        deepgram_url = f"wss://api.deepgram.com/v1/listen?punctuate=true&encoding=linear16&sample_rate=16000&endpointing=500"
        
        # Open the microphone stream
        p = pyaudio.PyAudio()
        self.stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, stream_callback=self.mic_callback)
        self.stream.start_stream()

        try:
            async with websockets.connect(
                deepgram_url, 
                extra_headers={"Authorization": f"Token {key}"}, 
                timeout=1
            ) as ws:

                sender_coroutine = self.sender(ws)
                receiver_coroutine = self.receiver(ws)
                call_end_check_task = asyncio.create_task(self.check_call_end_periodically())

                results = await asyncio.gather(sender_coroutine, receiver_coroutine, call_end_check_task, return_exceptions=True)
                
                transcript = next((r for r in results if isinstance(r, str)), None)
                return transcript

        except Exception as e:
            print(f"Error during transcription: {e}")
            return None

        finally:
            # Ensure resources are released
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            p.terminate()



def run_summarisation_in_background(chat_history, summary_queue):
    """
    Function to run summarise_chat_history in a separate thread.
    Places the result in a thread-safe queue.
    """
    summary = summarise_chat_history(chat_history)
    summary_queue.put(summary)  # Put the summary into the queue

def transcribe_stream(chat_history):
    global last_transcript
    DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
    if DEEPGRAM_API_KEY is None:
        print("Please set the DEEPGRAM_API_KEY environment variable.")
        return

    # Create a thread-safe queue for the summary
    summary_queue = queue.Queue()

    # Start the summarization in a separate thread, passing the queue
    background_thread = threading.Thread(target=run_summarisation_in_background, args=(chat_history, summary_queue))
    background_thread.start()

    print("Start speaking...")
    transcriber = Transcriber()
    
    loop = asyncio.get_event_loop()
    transcript = loop.run_until_complete(transcriber.run(DEEPGRAM_API_KEY))
    # current_transcript =  transcript
    # if last_transcript is not None:
    #  transcript = last_transcript + " " + transcript
    # Store the current transcript as the last transcript
    # last_transcript = current_transcript
    # Wait for the background task to complete
    background_thread.join()
    
    # Retrieve the summary from the queue
    summary = summary_queue.get() if not summary_queue.empty() else "Summary not available"
    return transcript, summary  # Return both the transcript and the summary

# chat_history = [{'role': 'user', 'content': 'Are there any amenities available?'}, {'role': 'assistant', 'content': 'Yes, we have a range of amenities available, including a fitness center, a business center, and a swimming pool. We also offer laundry services, a concierge service, and a tour desk. Additionally, we have a childcare service available, located just a short distance from our hotel. Would you like more information about any of these amenities?'}]
    
# # Example usage
# if __name__ == "__main__":
#     start_time = datetime.now()
#     print(start_time)
#     transcript, summary = transcribe_stream(chat_history)
#     print(f"Transcript: {transcript}")
#     print(f"Summary: {summary}")
#     print((datetime.now() - start_time).total_seconds())
