from pyo import *


# Initialize server
s = Server().boot()
s.start()

# User-defined parameters
bpm = 128
beats_per_bar = 4
total_bars = 2
volume = 0.2  # Control the volume of the clicks

# Calculate the interval in seconds per beat
interval = 60 / bpm
duration = interval * beats_per_bar * total_bars  # Loop duration in seconds

# Load samples with volume control
click = SfPlayer("samples/click.wav", speed=1, loop=False, mul=volume)
click_high = SfPlayer("samples/click.wav", speed=1.5, loop=False, mul=volume)  # High pitch for first countdown beat
click2 = SfPlayer("samples/click2.wav", speed=1, loop=False, mul=volume)
click2_high = SfPlayer("samples/click2.wav", speed=1.5, loop=False, mul=volume)  # High pitch for first beat of regular bars

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
            click_high.out()
        else:
            click.out()

def regular_click():
    if play_clicks:
        if current_beat % beats_per_bar == 0:
            click2_high.out()
        else:
            click2.out()

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

    
# Continue running the server
s.gui(locals())
