from pyo import *
from gpiozero import Button
import RPi.GPIO as GPIO
import time
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw, Image, ImageFont

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
class TrackInitializer:
    def __init__(self, loop_station):
        self.loop_station = loop_station

    def init_master_track(self):
        self.loop_station.init_master_track()

    def init_track(self, track_num):
        self.loop_station.init_track(track_num)
class GPIOSetup:
    def __init__(self, track_initializer):
        # Define the GPIO pins for rows and columns of the matrix keypad
        self.row_pins = [12, 1]
        self.col_pins = [13, 6, 5]

        # Dictionary to hold the key mapping for matrix keypad
        self.key_map = {
            (12, 13): 1, (12, 6): 2, (12, 5): 3,
            (1, 13): 4, (1, 6): 5, (1, 5): 6
        }

        self.track_initializer = track_initializer

        # Disable GPIO warnings
        GPIO.setwarnings(False)

        # Reset the GPIO pins
        GPIO.cleanup()

        # Set up the GPIO mode
        GPIO.setmode(GPIO.BCM)

        # Initialize buttons for rows with pull-down resistors
        self.rows = [Button(pin, pull_up=False) for pin in self.row_pins]

        # Set up columns as output and set them to high
        for col in self.col_pins:
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
                    # Call the corresponding function based on the key
                    if key == 1:
                        self.track_initializer.init_master_track()
                    else:
                        self.track_initializer.init_track(key)
            GPIO.output(col, GPIO.LOW)

        # Re-enable all column outputs
        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)

class MenuScreen:
    def __init__(self, device, track_initializer):
        self.device = device
        self.track_initializer = track_initializer
        self.menu_options = ["GRABAR", "CONFIG"]
        self.current_option = 0

        self.font_path = 'fonts/InputSansNarrow-Thin.ttf'
        self.font_size = 12
        self.font = ImageFont.truetype(self.font_path, self.font_size)

        # Define the GPIO pins for the rotary encoder
        self.CLK_PIN = 22  # GPIO7 connected to the rotary encoder's CLK pin
        self.DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
        self.SW_PIN = 17   # GPIO25 connected to the rotary encoder's SW pin

        self.prev_CLK_state = GPIO.input(self.CLK_PIN)

        GPIO.setup(self.CLK_PIN, GPIO.IN)
        GPIO.setup(self.DT_PIN, GPIO.IN)
        GPIO.setup(self.SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def draw_menu(self):
        # Create an image in portrait mode dimensions
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        
        # Draw menu options
        y_offset = 6
        for i, option in enumerate(self.menu_options):
            bbox = draw.textbbox((0, 0), option, font=self.font)  # Get bounding box
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (64 - text_width) // 2
            text_y = y_offset
            if i == self.current_option:
                # Draw highlight
                highlight_rect = [
                    0,  # Start at the left edge of the screen
                    text_y - 8 + 2,  # Adjust to position the highlight a bit lower
                    64,  # End at the right edge of the screen
                    text_y + text_height + 8 + 2
                ]
                draw.rectangle(highlight_rect, outline="white", fill="white")
                draw.text((text_x, text_y), option, font=self.font, fill="black")  # Draw text in black
            else:
                draw.text((text_x, text_y), option, font=self.font, fill="white")  # Draw text in white
            y_offset += text_height + 16

        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)
        
        # Display the rotated image on the device
        self.device.display(rotated_image)

    def handle_rotary_encoder(self):
        global prev_CLK_state

        # Read the current state of the rotary encoder's CLK pin
        CLK_state = GPIO.input(self.CLK_PIN)

        # If the state of CLK is changed, then pulse occurred
        # React to only the rising edge (from LOW to HIGH) to avoid double count
        if CLK_state != self.prev_CLK_state and CLK_state == GPIO.HIGH:
            # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
            # Decrease the counter
            if GPIO.input(self.DT_PIN) == GPIO.HIGH:
                self.current_option = (self.current_option - 1) % len(self.menu_options)
            else:
                # The encoder is rotating in clockwise direction => increase the counter
                self.current_option = (self.current_option + 1) % len(self.menu_options)

            self.draw_menu()

        # Save last CLK state
        self.prev_CLK_state = CLK_state

    def handle_encoder_button(self):
        button_state = GPIO.input(self.SW_PIN)
        if button_state == GPIO.LOW:
            print("Rotary Encoder Button:: The button is pressed")
            if self.current_option == 0:  # GRABAR selected
                self.track_initializer.init_master_track()
            elif self.current_option == 1:  # CONFIG selected
                config_screen = ConfigScreen(self.device, self.track_initializer)
                config_screen.run()

class ConfigScreen:
    def __init__(self, device, track_initializer):
        self.device = device
        self.track_initializer = track_initializer
        self.config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
        self.config_option_values = {
            "BPM": 120,
            "TIME SIGNATURE": "4/4",
            "TOTAL BARS": 4
        }
        self.time_signature_options = ["2/4", "3/4", "4/4", "6/8"]
        self.current_config_option = 0

        self.font_path = 'fonts/InputSansNarrow-Thin.ttf'
        self.font_size = 12
        self.font = ImageFont.truetype(self.font_path, self.font_size)

        self.CLK_PIN = 22  # GPIO22 connected to the rotary encoder's CLK pin
        self.DT_PIN = 27   # GPIO27 connected to the rotary encoder's DT pin
        self.SW_PIN = 17   # GPIO17 connected to the rotary encoder's SW pin

        GPIO.setup(self.CLK_PIN, GPIO.IN)
        GPIO.setup(self.DT_PIN, GPIO.IN)
        GPIO.setup(self.SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.prev_CLK_state = GPIO.input(self.CLK_PIN)
        self.button_pressed = False
        self.prev_button_state = GPIO.HIGH

    def draw_config_screen(self):
        # Create an image in portrait mode dimensions
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        
        # Draw config option
        option = self.config_options[self.current_config_option]
        if option == "BPM":
            value = f"{self.config_option_values[option]} BPM"
        elif option == "TIME SIGNATURE":
            value = self.config_option_values[option]
        elif option == "TOTAL BARS":
            value = f"{self.config_option_values[option]} BARS"

        # Calculate text position
        bbox = draw.textbbox((0, 0), value, font=self.font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = (128 - text_height) // 2 + 8  # Slightly below center, moved 5 pixels up

        # Draw text on the screen
        draw.text((text_x, text_y), value, font=self.font, fill="white")
        
        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)
        
        # Display the rotated image on the device
        self.device.display(rotated_image)

    def handle_rotary_encoder(self):
        global prev_CLK_state

        # Read the current state of the rotary encoder's CLK pin
        CLK_state = GPIO.input(self.CLK_PIN)

        # If the state of CLK is changed, then pulse occurred
        # React to only the rising edge (from LOW to HIGH) to avoid double count
        if CLK_state != self.prev_CLK_state and CLK_state == GPIO.HIGH:
            # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
            # Decrease the counter
            if GPIO.input(self.DT_PIN) == GPIO.HIGH:
                direction = -1
            else:
                # The encoder is rotating in clockwise direction => increase the counter
                direction = 1

            if direction == 1:
                if self.current_config_option == 0:  # BPM
                    self.config_option_values["BPM"] = min(300, self.config_option_values["BPM"] + 1)
                elif self.current_config_option == 1:  # TIME SIGNATURE
                    current_ts_index = self.time_signature_options.index(self.config_option_values["TIME SIGNATURE"])
                    self.config_option_values["TIME SIGNATURE"] = self.time_signature_options[(current_ts_index + 1) % len(self.time_signature_options)]
                elif self.current_config_option == 2:  # TOTAL BARS
                    self.config_option_values["TOTAL BARS"] = min(8, self.config_option_values["TOTAL BARS"] + 1)
            elif direction == -1:
                if self.current_config_option == 0:  # BPM
                    self.config_option_values["BPM"] = max(1, self.config_option_values["BPM"] - 1)
                elif self.current_config_option == 1:  # TIME SIGNATURE
                    current_ts_index = self.time_signature_options.index(self.config_option_values["TIME SIGNATURE"])
                    self.config_option_values["TIME SIGNATURE"] = self.time_signature_options[(current_ts_index - 1) % len(self.time_signature_options)]
                elif self.current_config_option == 2:  # TOTAL BARS
                    self.config_option_values["TOTAL BARS"] = max(1, self.config_option_values["TOTAL BARS"] - 1)

            self.draw_config_screen()

        # Save last CLK state
        self.prev_CLK_state = CLK_state

    def handle_encoder_button(self):
        global button_pressed, prev_button_state, current_config_option

        # State change detection for the button
        button_state = GPIO.input(self.SW_PIN)
        if button_state != self.prev_button_state:
            time.sleep(0.01)  # Add a small delay to debounce
            if button_state == GPIO.LOW:
                self.button_pressed = True
                if self.current_config_option < len(self.config_options) - 1:
                    self.current_config_option += 1
                else:
                    # Save settings and exit config
                    print("Configuration complete.")
                    exit()
                self.draw_config_screen()
            else:
                self.button_pressed = False

        self.prev_button_state = button_state

    def run(self):
        try:
            self.draw_config_screen()
            while True:
                self.handle_rotary_encoder()
                self.handle_encoder_button()
                time.sleep(0.01)  # Small delay to prevent CPU overuse
        except KeyboardInterrupt:
            GPIO.cleanup()  # Clean up GPIO on program exit

# Initialize loop station
loop_station = LoopStation(s, bpm, total_bars, total_bars)

# Initialize track initializer
track_initializer = TrackInitializer(loop_station)

# Setup GPIO keys
gpio_setup = GPIOSetup(track_initializer)

# Initialize the OLED screen
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Initialize the menu screen
menu_screen = MenuScreen(device, track_initializer)

try:
    print("Listening for button presses on matrix keypad...")
    while True:
        menu_screen.handle_rotary_encoder()
        menu_screen.handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit