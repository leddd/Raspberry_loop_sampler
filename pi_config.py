import time
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import sh1106

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

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
    text_y = (128 - text_height) // 2 + 5  # Slightly below center, moved 5 pixels up

    # Draw text on the screen
    draw.text((text_x, text_y), value, font=font, fill="white")
    
    # Rotate the image by 90 degrees to fit the landscape display
    rotated_image = image.rotate(270, expand=True)
    
    # Display the rotated image on the device
    device.display(rotated_image)

# Function to handle rotary encoder
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, current_config_option

    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)

    # If the state of CLK is changed, then pulse occurred
    # React to only the rising edge (from LOW to HIGH) to avoid double count
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        # Decrease the counter
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            direction = DIRECTION_CCW
        else:
            # The encoder is rotating in clockwise direction => increase the counter
            direction = DIRECTION_CW

        if direction == DIRECTION_CW:
            if current_config_option == 0:  # BPM
                config_option_values["BPM"] = min(300, config_option_values["BPM"] + 1)
            elif current_config_option == 1:  # TIME SIGNATURE
                current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index + 1) % len(time_signature_options)]
            elif current_config_option == 2:  # TOTAL BARS
                config_option_values["TOTAL BARS"] = min(8, config_option_values["TOTAL BARS"] + 1)
        elif direction == DIRECTION_CCW:
            if current_config_option == 0:  # BPM
                config_option_values["BPM"] = max(1, config_option_values["BPM"] - 1)
            elif current_config_option == 1:  # TIME SIGNATURE
                current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index - 1) % len(time_signature_options)]
            elif current_config_option == 2:  # TOTAL BARS
                config_option_values["TOTAL BARS"] = max(1, config_option_values["TOTAL BARS"] - 1)

        draw_config_screen()

    # Save last CLK state
    prev_CLK_state = CLK_state

# Function to handle button press on rotary encoder
def handle_encoder_button():
    global button_pressed, prev_button_state, current_config_option

    # State change detection for the button
    button_state = GPIO.input(SW_PIN)
    if button_state != prev_button_state:
        time.sleep(0.01)  # Add a small delay to debounce
        if button_state == GPIO.LOW:
            button_pressed = True
            if current_config_option < len(config_options) - 1:
                current_config_option += 1
            else:
                # Save settings and exit config
                print("Configuration complete.")
                exit()
            draw_config_screen()
        else:
            button_pressed = False

    prev_button_state = button_state

try:
    print(f"Listening for rotary encoder changes...")
    draw_config_screen()
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
