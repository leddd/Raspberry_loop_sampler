import asyncio
import numpy as np
import sounddevice as sd
from pyo import *
import tkinter as tk
import time

# Initialize the pyo server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 128  # Beats per minute
beats_per_bar = 4  # Beats per bar
total_bars = 2  # Number of bars to record
channels = 1  # Number of audio channels (1 for mono, 2 for stereo)
samplerate = 44100  # Sampling rate for recording

# Calculate beat interval in seconds
beat_interval = 60.0 / bpm

# Calculate the buffer duration
buffer_duration = total_bars * beats_per_bar * beat_interval
playback_start = buffer_duration - 0.25

# Calculate total frames for the buffer
buffer_size = int(buffer_duration * samplerate)

# Buffers for each track
buffers = [np.zeros((buffer_size, channels), dtype='float32') for _ in range(6)]
write_ptrs = [0] * 6
read_ptr = 0
recording_done = [False] * 6
playback_started = False
overdub_requested = [False] * 6
overdub_recording = [False] * 6
overdub_write_ptrs = [0] * 6

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
    global current_bar, current_beat, click2_enabled, overdub_requested, overdub_recording, overdub_write_ptrs
    while True:
        start_time = time.perf_counter()
        for bar in range(1, total_bars + 1):
            current_bar = bar
            for beat in range(1, beats_per_bar + 1):
                current_beat = beat
                print(f"Master Clock - Bar {bar}, Beat {beat}")
                if click2_enabled:
                    play_click2(high_pitch=(beat == 1))
                for track_id in range(1, 6):  # Check overdub for each track except master
                    if overdub_requested[track_id] and bar == 1 and beat == 1:
                        overdub_requested[track_id] = False
                        overdub_recording[track_id] = True
                        overdub_write_ptrs[track_id] = 0
                        print(f"Starting overdub recording for track {track_id + 1}")
                next_beat_time = start_time + beat * beat_interval
                await asyncio.sleep(max(0, next_beat_time - time.perf_counter()))

# Recording and playback logic
async def record_and_playback():
    global write_ptrs, read_ptr, recording_done, playback_started, overdub_requested, overdub_recording, overdub_write_ptrs

    def callback(indata, outdata, frames, time, status):
        global write_ptrs, read_ptr, recording_done, playback_started, overdub_recording, overdub_write_ptrs

        if status:
            print(status)

        # Recording for each track
        for track_id in range(6):
            if not recording_done[track_id]:
                if write_ptrs[track_id] + frames <= buffer_size:
                    buffers[track_id][write_ptrs[track_id]:write_ptrs[track_id] + frames] = indata
                    write_ptrs[track_id] += frames
                else:
                    remaining_space = buffer_size - write_ptrs[track_id]
                    buffers[track_id][write_ptrs[track_id]:] = indata[:remaining_space]
                    buffers[track_id][:frames - remaining_space] = indata[remaining_space:]
                    write_ptrs[track_id] = frames - remaining_space
                    recording_done[track_id] = True
                if track_id == 0:
                    recording_done[track_id] = True

        # Overdub recording for each track
        for track_id in range(1, 6):
            if overdub_recording[track_id]:
                if overdub_write_ptrs[track_id] + frames <= buffer_size:
                    buffers[track_id][overdub_write_ptrs[track_id]:overdub_write_ptrs[track_id] + frames] = indata
                    overdub_write_ptrs[track_id] += frames
                else:
                    remaining_space = buffer_size - overdub_write_ptrs[track_id]
                    buffers[track_id][overdub_write_ptrs[track_id]:] = indata[:remaining_space]
                    buffers[track_id][:frames - remaining_space] = indata[remaining_space:]
                    overdub_write_ptrs[track_id] = frames - remaining_space
                    overdub_recording[track_id] = False
                    print(f"Overdub recording finished for track {track_id + 1}")

        # Start playback
        if write_ptrs[0] >= int(playback_start * samplerate) and not playback_started:
            playback_started = True
            read_ptr = 0  # Reset read pointer for playback
            print(f"Starting playback at second {playback_start}")

        # Playback
        if playback_started:
            outdata[:] = sum(buffers[track_id][read_ptr:read_ptr + frames] for track_id in range(6))
            read_ptr += frames
            if read_ptr >= buffer_size:
                read_ptr = 0

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

# GUI class
class LooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("6-Track Looper")
        self.root.geometry("500x350")
        self.root.configure(bg='darkgray')

        self.track_buttons = []
        for i in range(2):  # Two rows
            root.grid_rowconfigure(i, weight=1)
            for j in range(3):  # Three columns
                root.grid_columnconfigure(j, weight=1)
                track_id = i * 3 + j
                button = tk.Button(root, text=f"Track {track_id + 1}", bg='gray', activebackground='lightgray', command=lambda track_id=track_id: self.on_button_press(track_id))
                button.grid(row=i, column=j, padx=10, pady=10, sticky="nsew")
                self.track_buttons.append(button)

    def on_button_press(self, track_id):
        if track_id == 0:
            asyncio.run_coroutine_threadsafe(main(), loop)
        else:
            global overdub_requested
            overdub_requested[track_id] = True
            print(f"Overdub requested for track {track_id + 1}")

# Start the GUI
def start_gui():
    root = tk.Tk()
    app = LooperApp(root)
    root.mainloop()

# Create an asyncio event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Run the GUI in the event loop
loop.run_in_executor(None, start_gui)

# Run the asyncio event loop
loop.run_forever()
