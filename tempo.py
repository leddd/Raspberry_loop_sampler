import asyncio
import numpy as np
import sounddevice as sd
from pyo import *

# Initialize the pyo server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 100  # Beats per minute
beats_per_bar = 4  # Beats per bar
total_bars = 2  # Number of bars to record
channels = 1  # Number of audio channels (1 for mono, 2 for stereo)
samplerate = 44100  # Sampling rate for recording

# Calculate beat interval in seconds
beat_interval = 60.0 / bpm

# Click parameters
click_volume = 0.1  # Adjust volume as needed
click2_volume = 0.1  # Adjust volume as needed for the second click sound

# Function to create an original and pitch-shifted version of a sound
def create_clicks(file_path, volume):
    original = SfPlayer(file_path, loop=False, mul=volume)
    factor = 2 ** (5 / 12.0)  # Convert 5 semitones to pitch factor
    pitch_shifted = SfPlayer(file_path, loop=False, speed=factor, mul=volume)
    return original, pitch_shifted

# Create the original and pitch-shifted versions of the clicks
click, click_high = create_clicks('samples/click.wav', click_volume)
click2, click2_high = create_clicks('samples/click2.wav', click2_volume)

# Define a function to play the click sound
def play_click(high_pitch=False):
    if high_pitch:
        click_high.out()
    else:
        click.out()

# Define a function to play the second click sound
def play_click2(high_pitch=False):
    if high_pitch:
        click2_high.out()
    else:
        click2.out()

# Shared state variables
current_bar = 0
current_beat = 0
click2_enabled = True  # Toggle state for click2

# Function to toggle the click2 track
def toggle_click2():
    global click2_enabled
    click2_enabled = not click2_enabled
    print(f"Click2 enabled: {click2_enabled}")

# Countdown before the master clock starts
async def countdown():
    print("Starting countdown...")
    for beat in range(1, beats_per_bar + 1):
        print(f"Countdown - Beat {beat}")
        play_click(high_pitch=(beat == 1))
        await asyncio.sleep(beat_interval)

# Master clock to keep track of bars and beats
async def master_clock():
    global current_bar, current_beat, click2_enabled
    while True:
        for bar in range(1, total_bars + 1):
            current_bar = bar
            for beat in range(1, beats_per_bar + 1):
                current_beat = beat
                print(f"Master Clock - Bar {bar}, Beat {beat}")
                if click2_enabled:
                    play_click2(high_pitch=(beat == 1))
                await asyncio.sleep(beat_interval)
                
                
# Placeholder for recording and playback logic
async def record_and_playback():
    # Your recording and playback logic will go here
    pass

# Main function to run the countdown, clock, and other tasks
async def main():
    # Run countdown first
    await countdown()

    # Start the master clock
    clock_task = asyncio.create_task(master_clock())

    # Start the record and playback task
    record_task = asyncio.create_task(record_and_playback())

    # Wait for tasks to complete
    await asyncio.gather(clock_task, record_task)

# Run the main event loop
asyncio.run(main())
