import numpy as np
import sounddevice as sd

# User-defined parameters
channels = 1  # Number of audio channels (1 for mono, 2 for stereo)
samplerate = 44100  # Sampling rate for recording


bpm = 100  # Beats per minute
beats_per_bar = 4  # Beats per bar
total_bars = 2  # Number of bars to record
beat_interval = 60.0 / bpm

buffer_duration = total_bars * beats_per_bar * beat_interval
playback_start = buffer_duration - 0.01

# Calculate total frames for the buffer
buffer_size = int(buffer_duration * samplerate)
buffer = np.zeros((buffer_size, channels), dtype='float32')
write_ptr = 0
read_ptr = 0
recording_done = False
playback_started = False

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
    sd.sleep(int(buffer_duration * 1000))  # Sleep for the duration of the buffer
    print("Recording finished. Playing back the buffer in a loop.")
    
    while True:
        sd.sleep(1000)  # Keep the stream running
