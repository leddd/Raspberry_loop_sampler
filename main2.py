from pyo import *
from gpiozero import Button
import RPi.GPIO as GPIO
import time

class Keypad:
    def __init__(self, row_pins, col_pins, key_map):
        self.row_pins = row_pins
        self.col_pins = col_pins
        self.key_map = key_map

        # Initialize buttons for rows with pull-down resistors
        self.rows = [Button(pin, pull_up=False) for pin in row_pins]

        # Set up columns as output and set them to high
        for col in col_pins:
            GPIO.setup(col, GPIO.OUT)
            GPIO.output(col, GPIO.HIGH)

        # Attach the callback function to the button press event for each row
        for row in self.rows:
            row.when_pressed = lambda row=row: self.matrix_button_pressed(row)

    def matrix_button_pressed(self, row_pin):
        # Disable all column outputs
        for col in self.col_pins:
            GPIO.output(col, GPIO.LOW)

        # Detect which button was pressed
        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)
            time.sleep(0.01)  # Debounce delay
            if row_pin.is_pressed:
                key = self.key_map.get((row_pin.pin.number, col), None)
                if key:
                    print(f"Matrix Keypad:: Key pressed: {key}")
            GPIO.output(col, GPIO.LOW)

        # Re-enable all column outputs
        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)

class RotaryEncoder:
    DIRECTION_CW = 0
    DIRECTION_CCW = 1

    def __init__(self, clk_pin, dt_pin, sw_pin):
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.sw_pin = sw_pin

        self.counter = 0
        self.direction = RotaryEncoder.DIRECTION_CW
        self.prev_clk_state = None
        self.button_pressed = False
        self.prev_button_state = GPIO.HIGH

        self.setup_pins()

    def setup_pins(self):
        # Set up GPIO pins for rotary encoder
        GPIO.setup(self.clk_pin, GPIO.IN)
        GPIO.setup(self.dt_pin, GPIO.IN)
        GPIO.setup(self.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Read the initial state of the rotary encoder's CLK pin
        self.prev_clk_state = GPIO.input(self.clk_pin)

    def handle_rotary_encoder(self):
        # Read the current state of the rotary encoder's CLK pin
        clk_state = GPIO.input(self.clk_pin)

        # If the state of CLK is changed, then pulse occurred
        # React to only the rising edge (from LOW to HIGH) to avoid double count
        if clk_state != self.prev_clk_state and clk_state == GPIO.HIGH:
            # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
            # Decrease the counter
            if GPIO.input(self.dt_pin) == GPIO.HIGH:
                self.counter -= 1
                self.direction = RotaryEncoder.DIRECTION_CCW
            else:
                # The encoder is rotating in clockwise direction => increase the counter
                self.counter += 1
                self.direction = RotaryEncoder.DIRECTION_CW

            print("Rotary Encoder:: direction:", "CLOCKWISE" if self.direction == RotaryEncoder.DIRECTION_CW else "ANTICLOCKWISE",
                  "- count:", self.counter)

        # Save last CLK state
        self.prev_clk_state = clk_state

    def handle_encoder_button(self):
        # State change detection for the button
        button_state = GPIO.input(self.sw_pin)
        if button_state != self.prev_button_state:
            time.sleep(0.01)  # Add a small delay to debounce
            if button_state == GPIO.LOW:
                print("Rotary Encoder Button:: The button is pressed")
                self.button_pressed = True
            else:
                self.button_pressed = False

        self.prev_button_state = button_state

def setup_gpio():
    # Disable GPIO warnings and reset GPIO pins
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    # Define the GPIO pins for rows and columns of the matrix keypad
    row_pins = [12, 1]
    col_pins = [13, 6, 5]

    # Dictionary to hold the key mapping for matrix keypad
    key_map = {
        (12, 13): 1, (12, 6): 2, (12, 5): 3,
        (1, 13): 4, (1, 6): 5, (1, 5): 6,
    }

    keypad = Keypad(row_pins, col_pins, key_map)

    # Define the GPIO pins for the rotary encoder
    clk_pin = 22  # GPIO7 connected to the rotary encoder's CLK pin
    dt_pin = 27   # GPIO8 connected to the rotary encoder's DT pin
    sw_pin = 17   # GPIO25 connected to the rotary encoder's SW pin

    rotary_encoder = RotaryEncoder(clk_pin, dt_pin, sw_pin)

    return keypad, rotary_encoder

# Set up GPIO and get Keypad and RotaryEncoder instances
keypad, rotary_encoder = setup_gpio()

# Initialize server
s = Server(sr=48000, buffersize=2048, audio='pa', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)

s.boot()
s.start()

# User-defined parameters
bpm = 120
beats_per_bar = 4
total_bars = 2
latency = 0.2  # Latency in seconds
class Metronome:
    def __init__(self, bpm, beats_per_bar, total_bars):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.total_bars = total_bars

        self.interval = 60 / bpm
        self.duration = self.interval * beats_per_bar * total_bars  # Loop duration in seconds

        self.countdown_metro = Metro(time=self.interval)
        self.countdown_counter = Counter(self.countdown_metro, min=1)
        self.metro = Metro(time=self.interval)
        self.current_beat = Counter(self.metro, min=1, max=(total_bars * beats_per_bar) + 1)
        
        # click setup
        self.fcount = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fcount2 = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fclick = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.fclick2 = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.sine2 = Sine(freq=[800], mul=self.fcount).out()
        self.sine = Sine(freq=[600], mul=self.fcount2).out()
        self.click = Noise(self.fclick).out()
        self.click2 = PinkNoise(self.fclick2).out()
        self.clickhp = ButHP(self.click, freq=5000).out()  # Apply highpass filter

        self.play_clicks = True

        self.metro_trig = None
        self.stop_trig = None

    def init(self):
        self.countdown_metro.play()

        self.metro_trig = TrigFunc(self.countdown_metro, self.start_metro)
        self.stop_trig = TrigFunc(self.countdown_metro, self.stop_metro)

    def start_metro(self):
        if self.countdown_counter.get() > self.beats_per_bar:
            self.metro.play()

    def stop_metro(self):
        if self.countdown_counter.get() > self.beats_per_bar * (1 + self.total_bars) + 1:
            self.countdown_metro.stop()

    def countdown_click(self):
        if self.countdown_counter.get() <= self.beats_per_bar:
            if self.countdown_counter.get() == 1.0:
                self.fcount.play()
            else:
                self.fcount2.play()

    def regular_click(self):
        if self.play_clicks:
            if self.current_beat.get() == 1.0 or (self.current_beat.get() - 1) % self.beats_per_bar == 0:
                self.fclick.play()
            else:
                self.fclick2.play()
class Track:
    def __init__(self, server, metronome, channels=2, feedback=0.5):
        self.server = server
        self.metronome = metronome
        self.channels = channels
        self.feedback = feedback
        self.master_trig = None
        self.track_trig = None
        self.playback = None
        self.recorder = None
        self.initialized = False  # Flag to ensure initialization only happens once
        self.hp_freq = 650  # Highpass filter frequency

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.playback.out()
        print("Playback...")

    def stop_playback(self):
        self.playback.stop()
        print("Stopped Playback.")
        
    def print_countdown(self):
        if self.metronome.countdown_counter.get() <= self.metronome.beats_per_bar:
            print("Countdown counter:", self.metronome.countdown_counter.get())
    
    def print_beat(self):
        print("Current beat:", self.metronome.current_beat.get())
        
    def rec_master_track(self): 
        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar + 1:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.005)
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq).out()  # Apply highpass filter
            self.master_trig = CallAfter(self.start_recording, latency)

        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar * (1 + self.metronome.total_bars) + 1:
            self.metronome.play_clicks = False

    def init_master_track(self):
        self.metronome.init()
        self.trig_rec_master = TrigFunc(self.metronome.countdown_metro, self.rec_master_track)
        
        self.trig_countdown = TrigFunc(self.metronome.countdown_metro, self.metronome.countdown_click)
        self.trig_print_countdown = TrigFunc(self.metronome.countdown_metro, self.print_countdown)
        
        self.trig_click = TrigFunc(self.metronome.metro, self.metronome.regular_click)
        self.trig_print_beat = TrigFunc(self.metronome.metro, self.print_beat)
        
    def rec_track(self):
        if not self.initialized:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.01).out()
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq).out()  # Apply highpass filter
            self.track_trig = CallAfter(self.start_recording, latency)
            self.initialized = True
        
    def init_track(self, master):
        self.trig_rec = TrigFunc(master.playback['trig'], self.rec_track)
class LoopStation:
    def __init__(self, server, bpm, beats_per_bar, total_bars):
        self.server = server
        self.metronome = Metronome(bpm, beats_per_bar, total_bars)
        self.tracks = []
        
        self.master_track = Track(server, self.metronome)
        self.tracks.append(self.master_track)
        
    def init_master_track(self):
        self.master_track.init_master_track()
        print("Master track initialized")
        
    def init_track(self, track_num):
        track = Track(self.server, self.metronome)
        track.init_track(self.master_track)
        self.tracks.append(track)
        print(f"Track {track_num} initialized")
        
# Initialize loop station
loop_station = LoopStation(s, bpm, beats_per_bar, total_bars)

# Define functions to initialize tracks
def init_track(track_num):
    if track_num == 1:
        loop_station.init_master_track()
    else:
        loop_station.init_track(track_num)
    print(f"Track {track_num} initialized")

# Dictionary to map keys to track initialization functions
track_init_functions = {
    1: lambda: init_track(1),
    2: lambda: init_track(2),
    3: lambda: init_track(3),
    4: lambda: init_track(4),
    5: lambda: init_track(5),
    6: lambda: init_track(6),
}

# Set up GPIO and get Keypad and RotaryEncoder instances
keypad, rotary_encoder = setup_gpio()

try:
    print("Listening for button presses on matrix keypad and rotary encoder...")
    while True:
        rotary_encoder.handle_rotary_encoder()
        rotary_encoder.handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit