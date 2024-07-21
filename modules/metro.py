from pyo import *


# Initialize server
s = Server(sr=48000, buffersize=1024, audio='portaudio', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)

s.boot()
s.start()

# User-defined parameters
bpm = 128
beats_per_bar = 4
total_bars = 2
volume = 0.2  # Control the volume of the clicks

# Calculate the interval in seconds per beat
interval = 60 / bpm
duration = interval * beats_per_bar * total_bars  # Loop duration in seconds



fcount = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
fcount2 = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
fclick = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.1)
fclick2 = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.1)

sine2 = Sine(freq=[800], mul=fcount).out()
sine = Sine(freq=[600], mul=fcount2).out()

click = Noise(fclick).out()
click2 = PinkNoise(fclick2).out()
clickhp = ButHP(click, freq=5000).out()  # Apply highpass filter


# Metro setup
metronome = Metro(time=interval, poly=7).play()

# Global variables to track the current state
current_beat = 0
current_bar = 0
countdown_complete = False
play_clicks = True  # Flag to control click playback

def countdown_click():
    if play_clicks:
        if current_beat % beats_per_bar == 0:
            fcount.play()
        else:
            fcount2.play()

def regular_click():
    if current_beat % beats_per_bar == 0:
        fclick.play()
    else:
        fclick2.play()

def update_counters():
    global current_beat, current_bar, countdown_complete
    if not countdown_complete:
        countdown_click()  # Play countdown clicks
        current_beat += 1
        print(f"Countdown: {current_beat}")
        if current_beat >= beats_per_bar:
            countdown_complete = True  # End of countdown
            current_beat = 0  # Reset beat counter for the main loop
            current_bar = 1  # Start counting bars for the main session
            print("Countdown complete. Starting main loop.")
    else:
        regular_click()  # Play regular clicks
        current_beat += 1
        print(f"Main Loop - Current Bar: {current_bar}, Current Beat: {current_beat}")
        if current_beat >= beats_per_bar:
            current_beat = 0
            current_bar += 1
            if current_bar > total_bars:
                current_bar = 1  # Reset bar count after reaching the total bars



# Use TrigFunc to call update_counters every time metronome ticks
trigger = TrigFunc(metronome, update_counters)

    
try:
    while True:
        time.sleep(100)  # Sleep to keep the script alive
except KeyboardInterrupt:
    # Graceful shutdown on user interrupt
    print("Stopping Pyo server...")
    s.stop()
    s.shutdown()
