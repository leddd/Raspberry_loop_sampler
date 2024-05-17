import asyncio
import numpy as np
import sounddevice as sd
from pyo import *

# Initialize the pyo server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 100  # Beats per minute
beats_per_bar = 3  # Beats per bar
total_bars = 2  # Number of bars to record
channels = 1  # Number of audio channels (1 for mono, 2 for stereo)
samplerate = 44100  # Sampling rate for recording

# Calculate beat interval in seconds
beat_interval = 60.0 / bpm

# Calculate the buffer duration in one line
buffer_duration = total_bars * beats_per_bar * beat_interval
playback_start = buffer_duration - 0.25

# Calculate total frames for the buffer
buffer_size = int(buffer_duration * samplerate)
buffer = np.zeros((buffer_size, channels), dtype='float32')
write_ptr = 0
read_ptr = 0
recording_done = False
playback_started = False

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

# Recording and playback logic
async def record_and_playback():
    global write_ptr, read_ptr, recording_done, playback_started

    def callback(indata, outdata, frames, time, status):
        global write_ptr, read_ptr, recording_done, playback_started

        if status:
            print(status)

        # Recording
        if not recording_done:
            if write_ptr + frames <= buffer_size:
                buffer[write_ptr:write_ptr + frames] = indata
                write_ptr += frames
            else:
                remaining_space = buffer_size - write_ptr
                buffer[write_ptr:] = indata[:remaining_space]
                buffer[:frames - remaining_space] = indata[remaining_space:]
                write_ptr = frames - remaining_space
                recording_done = True

        # Start playback
        if write_ptr >= int(playback_start * samplerate) and not playback_started:
            playback_started = True
            read_ptr = 0  # Reset read pointer for playback
            print(f"Starting playback at second {playback_start}")

        # Playback
        if playback_started:
            if read_ptr + frames <= buffer_size:
                outdata[:] = buffer[read_ptr:read_ptr + frames]
                read_ptr += frames
            else:
                remaining_space = buffer_size - read_ptr
                outdata[:remaining_space] = buffer[read_ptr:]
                outdata[remaining_space:] = buffer[:frames - remaining_space]
                read_ptr = frames - remaining_space

    # Create the audio stream with the callback function
    with sd.Stream(callback=callback, channels=channels, samplerate=samplerate, dtype='float32'):
        print("Recording and playback in real-time using a circular buffer.")
        print(f"Recording for {buffer_duration} seconds...")
        await asyncio.sleep(buffer_duration + 1)  # Sleep for the duration of the buffer + 1 second for safety

        print("Recording finished. Playing back the buffer in a loop.")
        while True:
            await asyncio.sleep(1)  # Keep the stream running

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
