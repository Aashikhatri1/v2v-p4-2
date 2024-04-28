import webbrowser
import pyautogui as pg
import time
from main import chat_with_user


def open_website(url):
        webbrowser.open(url, new=2)  # new=2 opens in a new tab, if possible

# Opening call hipppo dialer
website = 'https://dialer.callhippo.com/dial'
open_website(website)

time.sleep(7)
pg.scroll(-100)
      
while True:  # Main loop for handling incoming calls
    accept = pg.locateOnScreen("assets/buttons/accept.png", confidence=0.9)
    if accept:
        x, y, width, height = accept
        click_x, click_y = x + width // 2, y + height // 2  # Calculate the center of the button
        print("Call received at coordinates:", (click_x, click_y))
        pg.moveTo(click_x, click_y)  # Move to the center of the button
        time.sleep(0.5)  # Short delay
        pg.mouseDown()
        time.sleep(0.1)  # Short delay to simulate a real click
        pg.mouseUp()
        print("Call accepted")
        chat_with_user()  # Start chat with user
        end_call = pg.locateOnScreen("assets/buttons/end_call.png", confidence = 0.98)
        if end_call:
            pg.click(end_call)
            # pg.mouseDown()
            # time.sleep(0.1)  # Short delay to simulate a real click
            # pg.mouseUp()
            print('Clicked on end call.')
        print("Waiting for next call...")
        time.sleep(5)
    else:
        print("No call detected.")
        time.sleep(5) 
