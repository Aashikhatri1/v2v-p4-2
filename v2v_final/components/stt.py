import asyncio
import json
import pyaudio
import websockets
from dotenv import load_dotenv
import os

load_dotenv()

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000
key = os.getenv('DEEPGRAM_API_KEY')



class Transcriber:
    def __init__(self, on_transcript=None):
        self.audio_queue = asyncio.Queue()
        self.stream = None
        self.stop_pushing = False
        self.on_transcript = on_transcript
        self.reconnect_delay = 0.3  # Time to wait before retrying connection
        self.max_reconnect_attempts = 10  # Max attempts to reconnect
        self.full_transcript = ""

    async def connect_and_transcribe(self, key):
        attempt_count = 0
        while attempt_count < self.max_reconnect_attempts:
            try:
                async with websockets.connect(
                        "wss://api.deepgram.com/v1/listen?punctuate=true&encoding=linear16&sample_rate=16000&endpointing=400",
                        extra_headers={"Authorization": f"Token {key}"}) as ws:
                    self.stop_pushing = False
                    sender_coroutine = self.sender(ws)
                    receiver_coroutine = self.receiver(ws)
                    await asyncio.gather(sender_coroutine, receiver_coroutine)
                    break  # Exit loop if successfully connected and messages are processed
            except websockets.exceptions.ConnectionClosed as e:
                print(f"WebSocket connection closed: {e}. Attempting to reconnect...")
                attempt_count += 1
                await asyncio.sleep(self.reconnect_delay)
        
        if attempt_count >= self.max_reconnect_attempts:
            print("Maximum reconnect attempts reached. Stopping transcription.")

    def mic_callback(self, input_data, frame_count, time_info, status_flag):
        if not self.stop_pushing:
            self.audio_queue.put_nowait(input_data)
        return (input_data, pyaudio.paContinue)

    async def attempt_reconnect(self):
        self.stop_pushing = True  # Stop pushing data to ensure a clean state for reconnection
        
        # Check if the stream is open before trying to stop it
        if self.stream and not self.stream.is_stopped():
            self.stream.stop_stream()
        if self.stream:
            self.stream.close()
        
        self.audio_queue = asyncio.Queue()  # Reset the audio queue
        
        # Ensure the audio stream is properly reset
        self.stream = None
        
        await asyncio.sleep(0.5)  # Wait for a few seconds before attempting to reconnect
        
        # Reset flag to start pushing data again
        self.stop_pushing = False
        
        # Reinitialize the stream as it was closed
        p = pyaudio.PyAudio()
        self.stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=1024, stream_callback=self.mic_callback)
        
        # Attempt to run the transcriber again with the current API key
        await self.connect_and_transcribe(key)


    async def sender(self, ws, timeout=10):
        while not self.stop_pushing:
            try:
                if self.audio_queue.empty():
                    await asyncio.sleep(0.1)  # Give some time to accumulate audio data
                    continue  # Skip this iteration if there's no data to send

                mic_data = await asyncio.wait_for(self.audio_queue.get(), timeout)
                await ws.send(mic_data)
            except asyncio.TimeoutError:
                print("Timeout in sender coroutine. Stopping the push.")
                break
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"WebSocket connection closed unexpectedly in sender: {e}")
                if "1011" in str(e):
                    self.stop_pushing = True  # Ensure to stop pushing data on specific error
                    await self.attempt_reconnect()  # Attempt to reconnect
                    break
                    # continue
                else:
                    raise  # Reraise the exception if it's not the specific error we're handling

    async def receiver(self, ws):
        try:
            async for msg in ws:
                res = json.loads(msg)
                # print(res)
                transcript = (
                    res.get("channel", {})
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                
                if transcript.strip():
                    print('transcript', transcript)
                    self.full_transcript += transcript + " "  # Append the current transcript
                    print('full_transcript',self.full_transcript)
                
                if self.full_transcript.strip() and res.get("speech_final"):
                    print('speech_final')
                    if self.on_transcript:
                        print('full_transcript',self.full_transcript)
                        await self.on_transcript(self.full_transcript.strip())
                        self.full_transcript = ""  # Reset the full transcript after processing

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection closed unexpectedly in receiver: {e}")
            if "1011" in str(e):
                await self.attempt_reconnect()
            else:
                raise

    async def run(self, key):
        # Initialize and start the audio stream
        p = pyaudio.PyAudio()
        self.stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=1024, stream_callback=self.mic_callback)
        self.stream.start_stream()

        await self.connect_and_transcribe(key)  # Attempt to connect and transcribe

        # Cleanup
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()
        p.terminate()

        print("Transcription stopped.")