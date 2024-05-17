from pyo import *
import time

# Initialize the server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 120  # Beats per minute
beats_per_bar = 4  # Beats per bar
click_volume = 0.1  # Adjust volume as needed

# Calculate beat interval in seconds
beat_interval = 60.0 / bpm

# Load the click sound
click = SfPlayer('samples/click.wav', loop=False, mul=click_volume)

# Define a function to play the click sound
def play_click():
    click.out()
    print("Click played")  # Debugging line to confirm function call

# Define a function to print the current bar and beat
def print_beat(beat_num):
    bar_num = beat_num // beats_per_bar + 1
    print(f"Bar {bar_num}, Beat {beat_num + 1}")

# Schedule the click and event printing
def schedule_events(total_bars):
    total_beats = total_bars * beats_per_bar
    start_time = time.time()
    
    beat_num = 0
    while True:
        next_beat_time = start_time + beat_num * beat_interval
        time.sleep(max(0, next_beat_time - time.time()))
        
        if beat_num < total_beats:
            play_click()
        
        print_beat(beat_num)
        
        # Debugging statements
        print(f"Scheduled Click for Beat {beat_num + 1} at {next_beat_time}")
        print(f"Current Time: {time.time()}")
        
        beat_num += 1

# Schedule events for a certain number of bars
total_bars = 1  # Number of bars to play the click sound
schedule_events(total_bars)

# Keep the server running
s.gui(locals())
