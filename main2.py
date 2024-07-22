from pyo import *
from gpiozero import Button
import RPi.GPIO as GPIO
import time
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

# Menu options
menu_options = ["GRABAR", "CONFIG"]
current_option = 0

# CONFIG options
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 4
}
time_signature_options = ["2/4", "3/4", "4/4", "6/8"]
current_config_option = 0

DIRECTION_CW = 0
DIRECTION_CCW = 1

# Padding and margin variables for menu
top_margin = 6
bottom_margin = 8
menu_padding = 8
settings_padding = 4
highlight_offset = 2  # Offset of the highlight position

# Rotary encoder and button state
counter = 0
direction = DIRECTION_CW
CLK_state = 0
prev_CLK_state = 0
button_pressed = False
prev_button_state = GPIO.HIGH

# Disable GPIO warnings
GPIO.setwarnings(False)

# Reset the GPIO pins
GPIO.cleanup()

# Set up the GPIO mode
GPIO.setmode(GPIO.BCM)

# Define the GPIO pins for the rotary encoder
CLK_PIN = 22  # GPIO22 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO27 connected to the rotary encoder's DT pin
SW_PIN = 17   # GPIO17 connected to the rotary encoder's SW pin

# Set up GPIO pins for rotary encoder
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Read the initial state of the rotary encoder's CLK pin
prev_CLK_state = GPIO.input(CLK_PIN)

# Initialize server
s = Server(sr=48000, buffersize=2048, audio='pa', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)
s.boot()
s.start()

# User-defined parameters
bpm = config_option_values["BPM"]
beats_per_bar = 4
total_bars = config_option_values["TOTAL BARS"]
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

# Define function to initialize master track
def init_master_track():
    loop_station.init_master_track()

# Define function to initialize additional tracks
def init_track_2():
    loop_station.init_track(2)

def init_track_3():
    loop_station.init_track(3)

def init_track_4():
    loop_station.init_track(4)

def init_track_5():
    loop_station.init_track(5)

def init_track_6():
    loop_station.init_track(6)

# Define the GPIO pins for rows and columns of the matrix keypad
row_pins = [12, 1]
col_pins = [13, 6, 5]

# Initialize buttons for rows with pull-down resistors
rows = [Button(pin, pull_up=False) for pin in row_pins]

# Set up columns as output and set them to high
for col in col_pins:
    GPIO.setup(col, GPIO.OUT)
    GPIO.output(col, GPIO.HIGH)

# Dictionary to hold the key mapping for matrix keypad
key_map = {
    (12, 13): 1, (12, 6): 2, (12, 5): 3,
    (1, 13): 4, (1, 6): 5, (1, 5): 6
}

# Map button actions
def matrix_button_pressed(row_pin):
    # Disable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.LOW)

    # Detect which button was pressed
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)
        time.sleep(0.01)  # Debounce delay
        if row_pin.is_pressed:
            key = key_map.get((row_pin.pin.number, col), None)
            if key:
                # Call the corresponding function based on the key
                if key == 1:
                    init_master_track()
                elif key == 2:
                    init_track_2()
                elif key == 3:
                    init_track_3()
                elif key == 4:
                    init_track_4()
                elif key == 5:
                    init_track_5()
                elif key == 6:
                    init_track_6()
        GPIO.output(col, GPIO.LOW)

    # Re-enable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)

# Attach the callback function to the button press event for each row
for row in rows:
    row.when_pressed = lambda row=row: matrix_button_pressed(row)

def draw_config_screen():
    # Create an image in portrait mode dimensions
    image = Image.new('1', (64, 128), "black")
    draw = ImageDraw.Draw(image)
    
    # Load a custom font
    font_size = 12  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Draw config option
    option = config_options[current_config_option]
    if option == "BPM":
        value = f"{config_option_values[option]} BPM"
    elif option == "TIME SIGNATURE":
        value = config_option_values[option]
    elif option == "TOTAL BARS":
        value = f"{config_option_values[option]} BARS"

    # Calculate text position
    bbox = draw.textbbox((0, 0), value, font=font)  # Get bounding box
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (64 - text_width) // 2
    text_y = (128 - text_height) // 2 + 8  # Slightly below center, moved 8 pixels up

    # Draw text on the screen
    draw.text((text_x, text_y), value, font=font, fill="white")
    
    # Rotate the image by 90 degrees to fit the landscape display
    rotated_image = image.rotate(270, expand=True)
    
    # Display the rotated image on the device
    device.display(rotated_image)

def draw_menu(current_option):
    # Create an image in portrait mode dimensions
    image = Image.new('1', (64, 128), "black")
    draw = ImageDraw.Draw(image)
    
    # Draw menu options
    y_offset = top_margin
    for i, option in enumerate(menu_options):
        bbox = draw.textbbox((0, 0), option, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = y_offset
        if i == current_option:
            # Draw highlight
            highlight_rect = [
                0,  # Start at the left edge of the screen
                text_y - menu_padding + highlight_offset,  # Adjust to position the highlight a bit lower
                64,  # End at the right edge of the screen
                text_y + text_height + menu_padding + highlight_offset
            ]
            draw.rectangle(highlight_rect, outline="white", fill="white")
            draw.text((text_x, text_y), option, font=font, fill="black")  # Draw text in black
        else:
            draw.text((text_x, text_y), option, font=font, fill="white")  # Draw text in white
        y_offset += text_height + menu_padding * 2

    # Draw current settings
    settings = [f"{bpm}BPM", time_signature, f"{total_bars}BARS"]
    settings_start_y = 128 - bottom_margin - (len(settings) * (text_height + settings_padding * 2))
    y_offset = max(y_offset, settings_start_y)
    for setting in settings:
        bbox = draw.textbbox((0, 0), setting, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = y_offset
        draw.text((text_x, text_y), setting, font=font, fill="white")  # Draw text in white
        y_offset += text_height + settings_padding * 2

    # Rotate the image by 90 degrees to fit the landscape display
    rotated_image = image.rotate(270, expand=True)
    
    # Display the rotated image on the device
    device.display(rotated_image)

# Function to handle rotary encoder for menu
def handle_rotary_encoder_menu():
    global current_option, prev_CLK_state

    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)

    # If the state of CLK is changed, then pulse occurred
    # React to only the rising edge (from LOW to HIGH) to avoid double count
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        # Decrease the counter
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            current_option = (current_option - 1) % len(menu_options)
        else:
            # The encoder is rotating in clockwise direction => increase the counter
            current_option = (current_option + 1) % len(menu_options)

        draw_menu(current_option)

    # Save last CLK state
    prev_CLK_state = CLK_state

# Function to handle button press on rotary encoder
def handle_encoder_button():
    global current_option, config_mode

    # State change detection for the button
    button_state = GPIO.input(SW_PIN)
    if button_state == GPIO.LOW:
        if current_option == 0:  # GRABAR selected
            init_master_track()
        elif current_option == 1:  # CONFIG selected
            config_mode = True
            draw_config_screen()
        time.sleep(0.5)  # Debounce delay

# Function to handle rotary encoder in config mode
def handle_rotary_encoder_config():
    global current_config_option, prev_CLK_state, config_option_values

    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)

    # If the state of CLK is changed, then pulse occurred
    # React to only the rising edge (from LOW to HIGH) to avoid double count
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        # Decrease the counter
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            if current_config_option == 0:  # BPM
                config_option_values["BPM"] = max(1, config_option_values["BPM"] - 1)
            elif current_config_option == 1:  # TIME SIGNATURE
                current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index - 1) % len(time_signature_options)]
            elif current_config_option == 2:  # TOTAL BARS
                config_option_values["TOTAL BARS"] = max(1, config_option_values["TOTAL BARS"] - 1)
        else:
            if current_config_option == 0:  # BPM
                config_option_values["BPM"] = min(300, config_option_values["BPM"] + 1)
            elif current_config_option == 1:  # TIME SIGNATURE
                current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index + 1) % len(time_signature_options)]
            elif current_config_option == 2:  # TOTAL BARS
                config_option_values["TOTAL BARS"] = min(8, config_option_values["TOTAL BARS"] + 1)

        draw_config_screen()

    # Save last CLK state
    prev_CLK_state = CLK_state

# Initial screen
config_mode = False
draw_menu(current_option)

try:
    print("Listening for button presses on matrix keypad and rotary encoder...")
    while True:
        if config_mode:
            handle_rotary_encoder_config()
        else:
            handle_rotary_encoder_menu()
            handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit