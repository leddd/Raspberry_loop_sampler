import time
import threading
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import ImageFont, ImageDraw, Image, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from pyo import *

# Initialize server
s = Server(sr=48000, buffersize=2048, audio='pa', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)
s.boot()
s.start()

# User-defined parameters
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 2
}
latency = 0.115  # Latency in seconds

# Dictionary to store image paths for each time signature
beat_images = {
    "2/4": ['/home/vice/main/djavu/screens/2-4_1.png', '/home/vice/main/djavu/screens/2-4_2.png'],
    "3/4": ['/home/vice/main/djavu/screens/3-4_1.png', '/home/vice/main/djavu/screens/3-4_2.png', '/home/vice/main/djavu/screens/3-4_3.png'],
    "4/4": ['/home/vice/main/djavu/screens/4-4_1.png', '/home/vice/main/djavu/screens/4-4_2.png', '/home/vice/main/djavu/screens/4-4_3.png', '/home/vice/main/djavu/screens/4-4_4.png'],
    "6/8": ['/home/vice/main/djavu/screens/6-8_1.png', '/home/vice/main/djavu/screens/6-8_2.png', '/home/vice/main/djavu/screens/6-8_3.png', '/home/vice/main/djavu/screens/6-8_4.png', '/home/vice/main/djavu/screens/6-8_5.png', '/home/vice/main/djavu/screens/6-8_6.png']
}
# Load the beat images
beat_images_loaded = {}
for key, paths in beat_images.items():
    beat_images_loaded[key] = [Image.open(path).convert('1') for path in paths]

# Metronome class
class Metronome:
    def __init__(self, bpm, beats_per_bar, total_bars):
        self.update_params(bpm, beats_per_bar, total_bars)

    def update_params(self, bpm, beats_per_bar, total_bars):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.total_bars = total_bars
        self.time_signature = config_option_values["TIME SIGNATURE"]

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

# Track class
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
        self.hp_freq = 400  # Highpass filter frequency
        self.lp_freq = 4000  # Lowpass filter frequency

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.playback.out()
        print("Playback...")

    def stop_playback(self):
        self.playback.stop()
        print("Stopped Playback.")
        
    def rec_master_track(self): 
        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar + 1:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.005)
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq)  # Apply highpass filter
            self.lowpass = ButLP(self.highpass, freq=self.lp_freq)
            self.ex = Expand(self.lowpass, downthresh=-90, upthresh=-90, ratio=2, mul=0.1)
            self.harm = Harmonizer(self.ex, transpo=0, winsize=0.05).out()
            self.master_trig = CallAfter(self.start_recording, latency)

        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar * (1 + self.metronome.total_bars) + 1:
            self.metronome.play_clicks = False

    def init_master_track(self):
        self.metronome.init()
        self.trig_rec_master = TrigFunc(self.metronome.countdown_metro, self.rec_master_track)
        
        self.trig_countdown = TrigFunc(self.metronome.countdown_metro, self.metronome.countdown_click)
        
        self.trig_click = TrigFunc(self.metronome.metro, self.metronome.regular_click)
        
    def rec_track(self):
        if not self.initialized:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.01).out()
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq)  # Apply highpass filter
            self.lowpass = ButLP(self.highpass, freq=self.lp_freq)
            self.ex = Expand(self.lowpass, downthresh=-90, upthresh=-90, ratio=2, mul=0.1)
            self.harm = Harmonizer(self.ex, transpo=0, winsize=0.05).out()
            self.track_trig = CallAfter(self.start_recording, latency)
            self.initialized = True
        
    def init_track(self, master):
        self.trig_rec = TrigFunc(master.playback['trig'], self.rec_track)

# LoopStation class
class LoopStation:
    def __init__(self, server, config_option_values):
        self.server = server
        self.config_option_values = config_option_values
        self.update_metronome()

    def update_metronome(self):
        bpm = self.config_option_values["BPM"]
        beats_per_bar = int(self.config_option_values["TIME SIGNATURE"].split('/')[0])
        total_bars = self.config_option_values["TOTAL BARS"]
        self.metronome = Metronome(bpm, beats_per_bar, total_bars)
        self.tracks = []

        self.master_track = Track(self.server, self.metronome)
        self.tracks.append(self.master_track)
        
    def init_master_track(self):
        self.master_track.init_master_track()
        print("Master track initialized")
        
    def init_track(self, track_num):
        track = Track(self.server, self.metronome)
        track.init_track(self.master_track)
        self.tracks.append(track)
        print(f"Track {track_num} initialized")    

class TrackInitializer:
    def __init__(self, loop_station):
        self.loop_station = loop_station

    def init_master_track(self):
        self.loop_station.init_master_track()

    def init_track(self, track_num):
        self.loop_station.init_track(track_num)

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = '/home/vice/main/djavu/fonts/InputSansNarrow-Thin.ttf'

# Menu options
menu_options = ["GRABAR", "CONFIG"]
current_menu_option = 0

# CONFIG options
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
time_signature_options = ["2/4", "3/4", "4/4"]
current_config_option = 0

# Screen display functions
def draw_countdown_screen(beat_count, beat_image):
    with lock:
        # Create a new image for the countdown screen
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)

        # Load the beat image
        image.paste(beat_image, (0, 0))

        # Load a custom font
        font_size = 30  # Adjust the font size as needed
        font = ImageFont.truetype(font_path, font_size)

        # Draw the countdown number
        text = str(beat_count)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = (128 - text_height) // 2
        draw.text((text_x, text_y), text, font=font, fill="white")  # White text

        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)

        # Display the rotated image on the device
        device.display(rotated_image)

def draw_menu():
    global current_menu_option
    with lock:
        # Create an image in portrait mode dimensions
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        
        # Load a custom font
        font_size = 12  # Adjust the font size as needed
        font = ImageFont.truetype(font_path, font_size)

        # Draw menu options
        y_offset = 0  # Adjust as needed
        for i, option in enumerate(menu_options):
            bbox = draw.textbbox((0, 0), option, font=font)  # Get bounding box
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (64 - text_width) // 2
            text_y = y_offset
            if i == current_menu_option:
                # Draw highlight
                highlight_rect = [
                    0,  # Start at the left edge of the screen
                    text_y - 2,  # Adjust to position the highlight a bit lower
                    64,  # End at the right edge of the screen
                    text_y + text_height + 2
                ]
                draw.rectangle(highlight_rect, outline="white", fill="white")
                draw.text((text_x, text_y), option, font=font, fill="black")  # Draw text in black
            else:
                draw.text((text_x, text_y), option, font=font, fill="white")  # Draw text in white
            y_offset += text_height + 4  # Adjust spacing as needed

        # Draw current settings
        settings = [f"{config_option_values['BPM']} BPM", config_option_values["TIME SIGNATURE"], f"{config_option_values['TOTAL BARS']} BARS"]
        settings_start_y = 128 - (len(settings) * (text_height + 4))  # Adjust the bottom margin if necessary
        y_offset = max(y_offset, settings_start_y)
        for setting in settings:
            bbox = draw.textbbox((0, 0), setting, font=font)  # Get bounding box
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (64 - text_width) // 2
            text_y = y_offset
            draw.text((text_x, text_y), setting, font=font, fill="white")  # Draw text in white
            y_offset += text_height + 4  # Adjust spacing as needed

        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)
        
        # Display the rotated image on the device
        device.display(rotated_image)

def draw_config_screen():
    global current_config_option
    with lock:
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
        text_y = (128 - text_height) // 2  # Slightly below center, moved 5 pixels up

        # Draw text on the screen
        draw.text((text_x, text_y), value, font=font, fill="white")
        
        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)
        
        # Display the rotated image on the device
        device.display(rotated_image)

# Rotary encoder handling
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, current_config_option, current_menu_option, current_screen
    while True:
        # Read the current state of the rotary encoder's CLK and DT pins
        CLK_state = GPIO.input(CLK_PIN)
        DT_state = GPIO.input(DT_PIN)

        # If the state of CLK is changed, then pulse occurred
        if CLK_state != prev_CLK_state:
            # Determine the direction
            if DT_state != CLK_state:
                direction = DIRECTION_CW
            else:
                direction = DIRECTION_CCW

            counter += 1
            if counter % 2 == 0:  # Only update on every second step
                with lock:
                    if current_screen == "menu":
                        if direction == DIRECTION_CW:
                            current_menu_option = (current_menu_option + 1) % len(menu_options)
                        else:
                            current_menu_option = (current_menu_option - 1) % len(menu_options)
                        print(f"Menu Option: {menu_options[current_menu_option]}")
                    elif current_screen == "config":
                        option = config_options[current_config_option]
                        if option == "BPM":
                            if direction == DIRECTION_CW:
                                config_option_values[option] += 1
                                if config_option_values[option] > 200:
                                    config_option_values[option] = 200
                            else:
                                config_option_values[option] -= 1
                                if config_option_values[option] < 40:
                                    config_option_values[option] = 40
                        elif option == "TIME SIGNATURE":
                            index = time_signature_options.index(config_option_values[option])
                            if direction == DIRECTION_CW:
                                index = (index + 1) % len(time_signature_options)
                            else:
                                index = (index - 1) % len(time_signature_options)
                            config_option_values[option] = time_signature_options[index]
                        elif option == "TOTAL BARS":
                            if direction == DIRECTION_CW:
                                config_option_values[option] += 1
                                if config_option_values[option] > 16:
                                    config_option_values[option] = 16
                            else:
                                config_option_values[option] -= 1
                                if config_option_values[option] < 1:
                                    config_option_values[option] = 1

                        print(f"{option}: {config_option_values[option]}")
                        loop_station.update_metronome()  # Update metronome with new config

        # Save last CLK state
        prev_CLK_state = CLK_state

        time.sleep(0.001)  # Small delay to prevent CPU overuse

# Matrix keypad handling
def setup_rotary_encoder():
    global CLK_PIN, DT_PIN, SW_PIN, DIRECTION_CW, DIRECTION_CCW, prev_CLK_state, lock, direction, counter, button_pressed, prev_button_state

    # Define the GPIO pins for the rotary encoder
    CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
    DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
    SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

    DIRECTION_CW = 0
    DIRECTION_CCW = 1

    counter = 0
    direction = DIRECTION_CW
    prev_CLK_state = GPIO.HIGH
    button_pressed = False
    prev_button_state = GPIO.HIGH

    lock = threading.Lock()
    
    # Disable GPIO warnings
    GPIO.setwarnings(False)

    # Reset the GPIO pins
    GPIO.cleanup()

    # Set up the GPIO mode
    GPIO.setmode(GPIO.BCM)

    # Set up GPIO pins for rotary encoder
    GPIO.setup(CLK_PIN, GPIO.IN)
    GPIO.setup(DT_PIN, GPIO.IN)
    GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Read the initial state of the rotary encoder's CLK pin
    prev_CLK_state = GPIO.input(CLK_PIN)

def setup_matrix_keypad():
    global row_pins, col_pins, rows, key_map, debounce_time
    debounce_time = 0.05  # 50 ms debounce time

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
        (1, 13): 1, (1, 6): 2, (1, 5): 3,
        (12, 13): 4, (12, 6): 5, (12, 5): 6
    }

    # Attach the callback function to the button press event for each row
    for row in rows:
        row.when_pressed = lambda row=row: matrix_button_pressed(row)

def matrix_button_pressed(row_pin):
    global current_config_option, current_screen, current_menu_option

    # Disable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.LOW)

    # Detect which button was pressed
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)
        time.sleep(debounce_time)  # Debounce delay
        if row_pin.is_pressed:
            key = key_map.get((row_pin.pin.number, col), None)
            if key:
                print(f"Matrix Keypad:: Key pressed: {key}")
                with lock:
                    if current_screen == "menu":
                        if menu_options[current_menu_option] == "GRABAR":
                            if key == 1:
                                track_initializer.init_master_track()
                            else:
                                track_initializer.init_track(key)
                        elif menu_options[current_menu_option] == "CONFIG":
                            if key == 1:
                                current_screen = "config"
                    elif current_screen == "config":
                        if key == 1:
                            if config_options[current_config_option] == "TOTAL BARS":
                                current_screen = "menu"  # Return to menu after setting TOTAL BARS
                            current_config_option = (current_config_option + 1) % len(config_options)
                            print(f"Switched to: {config_options[current_config_option]}")
                            loop_station.update_metronome()  # Update metronome with new config
        GPIO.output(col, GPIO.LOW)

    # Re-enable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)

# Countdown screen thread
def countdown_screen_thread():
    while True:
        if current_screen == "countdown":
            beat_count = int(loop_station.metronome.countdown_counter.get())
            if beat_count <= loop_station.metronome.beats_per_bar:
                image_index = beat_count - 1
                beat_image = beat_images_loaded[loop_station.metronome.time_signature][image_index]
                draw_countdown_screen(beat_count, beat_image)
        time.sleep(0.1)

# Update screen thread
def update_screen():
    while True:
        if current_screen == "menu":
            draw_menu()
        elif current_screen == "config":
            draw_config_screen()
        time.sleep(0.1)  # Update the screen every 0.1 seconds

# Set up the rotary encoder and matrix keypad
setup_rotary_encoder()
setup_matrix_keypad()

# Current screen ("menu" or "config" or "countdown")
current_screen = "menu"

# Initialize the LoopStation and TrackInitializer
server = s  # Replace with your server instance
loop_station = LoopStation(server, config_option_values)
track_initializer = TrackInitializer(loop_station)

try:
    print(f"Listening for rotary encoder changes and button presses...")

    # Start threads for handling the rotary encoder, button press, and screen update
    threading.Thread(target=handle_rotary_encoder, daemon=True).start()
    threading.Thread(target=update_screen, daemon=True).start()
    threading.Thread(target=countdown_screen_thread, daemon=True).start()

    # Keep the main thread running
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
