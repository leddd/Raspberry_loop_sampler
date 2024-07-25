import time
import RPi.GPIO as GPIO
from gpiozero import Button
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw
from looper import LoopStation, Server

# Define the GPIO pins for the rotary encoder
CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

DIRECTION_CW = 0
DIRECTION_CCW = 1

class GPIOSetup:
    def __init__(self, track_initializer):
        self.row_pins = [12, 1]
        self.col_pins = [13, 6, 5]

        self.key_map = {
            (1, 13): 1, (1, 6): 2, (1, 5): 3,
            (12, 13): 4, (12, 6): 5, (12, 5): 6
        }

        self.track_initializer = track_initializer

        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)

        self.rows = [Button(pin, pull_up=False, bounce_time=0.05) for pin in self.row_pins]

        for col in self.col_pins:
            GPIO.setup(col, GPIO.OUT)
            GPIO.output(col, GPIO.HIGH)

        for row in self.rows:
            row.when_pressed = lambda row=row: self.on_button_pressed(row)
            row.when_released = lambda row=row: self.on_button_released(row)

    def on_button_pressed(self, row_pin):
        for col in self.col_pins:
            GPIO.output(col, GPIO.LOW)

        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)
            time.sleep(0.01)
            if row_pin.is_pressed:
                key = self.key_map.get((row_pin.pin.number, col), None)
                if key:
                    # Placeholder for action based on key press
                    print(f"Key {key} pressed")
                break  # Exit the loop after detecting the key press
            GPIO.output(col, GPIO.LOW)

        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)

    def on_button_released(self, row_pin):
        # Additional logic for button release
        pass

class MenuControls:
    def __init__(self, loop_station):
        self.loop_station = loop_station

        # Initialize OLED display
        serial = i2c(port=1, address=0x3C)
        self.device = sh1106(serial)

        # Initialize GPIO for rotary encoder and keys
        self.gpio_setup = GPIOSetup(self)

        # Initialize rotary encoder
        self.counter = 0
        self.direction = DIRECTION_CW
        self.CLK_state = 0
        self.prev_CLK_state = GPIO.input(CLK_PIN)
        self.prev_DT_state = GPIO.input(DT_PIN)
        self.button_pressed = False
        self.prev_button_state = GPIO.HIGH

        GPIO.setup(CLK_PIN, GPIO.IN)
        GPIO.setup(DT_PIN, GPIO.IN)
        GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def handle_rotary_encoder(self):
        CLK_state = GPIO.input(CLK_PIN)
        DT_state = GPIO.input(DT_PIN)

        if CLK_state != self.prev_CLK_state:
            if DT_state != CLK_state:
                self.counter += 1
                self.direction = DIRECTION_CW
            else:
                self.counter -= 1
                self.direction = DIRECTION_CCW

            print("Rotary Encoder:: direction:", "CLOCKWISE" if self.direction == DIRECTION_CW else "ANTICLOCKWISE",
                  "- count:", self.counter)

        self.prev_CLK_state = CLK_state
        self.prev_DT_state = DT_state

    def handle_encoder_button(self):
        button_state = GPIO.input(SW_PIN)
        if button_state != self.prev_button_state:
            time.sleep(0.01)  # Add a small delay to debounce
            if button_state == GPIO.LOW:
                print("Rotary Encoder Button:: The button is pressed")
                self.button_pressed = True
            else:
                self.button_pressed = False

        self.prev_button_state = button_state

    def display_message(self, message):
        with canvas(self.device) as draw:
            font = ImageFont.load_default()
            draw.text((0, 0), message, font=font, fill=255)

if __name__ == "__main__":
    # Initialize the server
    server = Server(sr=48000, buffersize=2048, audio='pa', nchnls=1, ichnls=1, duplex=1)
    server.setInputDevice(1)
    server.setOutputDevice(0)
    server.boot()
    server.start()

    bpm = 120
    beats_per_bar = 4
    total_bars = 2

    loop_station = LoopStation(server, bpm, beats_per_bar, total_bars)
    menu_controls = MenuControls(loop_station)

    try:
        print("Listening for rotary encoder changes and button presses...")
        while True:
            menu_controls.handle_rotary_encoder()
            menu_controls.handle_encoder_button()
            time.sleep(0.001)  # Small delay to prevent CPU overuse
    except KeyboardInterrupt:
        GPIO.cleanup()  # Clean up GPIO on program exit
