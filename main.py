#!/usr/bin/env python3
import asyncio
import sys
import numpy as np
import sounddevice as sd
from pyo import *

# Initialize the pyo server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 120  # Beats per minute
beats_per_bar = 4  # Beats per bar
total_bars = 4  # Number of bars to record

recording_volume = 1.0  # Adjust recording volume as needed
channels = 1  # Number of audio channels (1 for mono, 2 for stereo)
samplerate = 44100  # Sampling rate for recording

# Calculate beat interval in seconds and total recording frames
beat_interval = 60.0 / bpm
record_duration = beat_interval * beats_per_bar * total_bars
frames = int(record_duration * samplerate)

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
        print("High pitch click played")  # Debugging line to confirm function call
    else:
        click.out()
        print("Click played")  # Debugging line to confirm function call

# Define a function to play the second click sound
def play_click2(high_pitch=False):
    if high_pitch:
        click2_high.out()
        print("High pitch click2 played")  # Debugging line to confirm function call
    else:
        click2.out()
        print("Click2 played")  # Debugging line to confirm function call

# Function to perform a countdown click for one bar
def countdown_click():
    for beat_num in range(beats_per_bar):
        if beat_num == 0:
            play_click(high_pitch=True)
        else:
            play_click()
        time.sleep(beat_interval)
        print(f"Countdown - Beat {beat_num + 1}")

# Asynchronous function to play click2 during recording
async def tempo_click():
    beats_played = 0
    total_beats = total_bars * beats_per_bar
    while beats_played < total_beats:
        if beats_played % beats_per_bar == 0:
            play_click2(high_pitch=True)
        else:
            play_click2()
        await asyncio.sleep(beat_interval)
        beats_played += 1

# Record and playback audio buffer asynchronously
async def record_buffer(buffer, volume=1.0, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0

    def callback(indata, frame_count, time_info, status):
        nonlocal idx
        if status:
            print(status)
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        indata = indata[:remainder] * volume
        buffer[idx:idx + len(indata)] = indata
        idx += len(indata)

    stream = sd.InputStream(callback=callback, dtype=buffer.dtype,
                            channels=buffer.shape[1], **kwargs)
    with stream:
        await event.wait()

async def play_buffer(buffer, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0

    def callback(outdata, frame_count, time_info, status):
        nonlocal idx
        if status:
            print(status)
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        valid_frames = frame_count if remainder >= frame_count else remainder
        outdata[:valid_frames] = buffer[idx:idx + valid_frames]
        outdata[valid_frames:] = 0
        idx += valid_frames

    stream = sd.OutputStream(callback=callback, dtype=buffer.dtype,
                             channels=buffer.shape[1], **kwargs)
    with stream:
        await event.wait()

async def main():
    buffer = np.empty((frames, channels), dtype='float32')

    # Perform a countdown before recording
    print('Starting countdown...')
    countdown_click()

    print('Recording buffer ...')
    click2_task = asyncio.create_task(tempo_click())
    await record_buffer(buffer, samplerate=samplerate, volume=recording_volume)
    await click2_task
    print('Recording finished')

    print('Playing buffer ...')
    await play_buffer(buffer, samplerate=samplerate)
    print('Playback finished')

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')

# Keep the pyo server running
s.gui(locals())
