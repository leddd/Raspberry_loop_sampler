from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw
import RPi.GPIO as GPIO
import time

# Initialize the OLED screen
serial = i2c(port=1, address=0x3C)
device = sh1106(serial, rotate=0)  # rotate=0 for portrait mode

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

# Menu options
menu_options = ["GRABAR", "CONFIG"]
current_option = 0

# Current settings
bpm = 120
time_signature = "4/4"
total_bars = 4

# Padding and margin variables
top_margin = 6
bottom_margin = 8
menu_padding = 8
settings_padding = 4
highlight_offset = 2  # Offset of the highlight position

# Define the GPIO pins for the rotary encoder
CLK_PIN = 22  # GPIO7 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
SW_PIN = 17   # GPIO25 connected to the rotary encoder's SW pin

# Set up GPIO pins for rotary encoder
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

prev_CLK_state = GPIO.input(CLK_PIN)

# Load a custom font
font_size = 12  # You can adjust the font size as needed
font = ImageFont.truetype(font_path, font_size)

def draw_menu(current_option):
    with canvas(device) as draw:
        # Draw menu options
        y_offset = top_margin
        for i, option in enumerate(menu_options):
            bbox = draw.textbbox((0, 0), option, font=font)  # Get bounding box
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (device.width - text_width) // 2
            text_y = y_offset
            if i == current_option:
                # Draw highlight
                highlight_rect = [
                    0,  # Start at the left edge of the screen
                    text_y - menu_padding + highlight_offset,  # Adjust to position the highlight a bit lower
                    device.width,  # End at the right edge of the screen
                    text_y + text_height + menu_padding + highlight_offset
                ]
                draw.rectangle(highlight_rect, outline="white", fill="white")
                draw.text((text_x, text_y), option, font=font, fill="black")  # Draw text in black
            else:
                draw.text((text_x, text_y), option, font=font, fill="white")  # Draw text in white
            y_offset += text_height + menu_padding * 2

        # Draw current settings
        settings = [f"{bpm}BPM", time_signature, f"{total_bars}BARS"]
        settings_start_y = device.height - bottom_margin - (len(settings) * (text_height + settings_padding * 2))
        y_offset = max(y_offset, settings_start_y)
        for setting in settings:
            bbox = draw.textbbox((0, 0), setting, font=font)  # Get bounding box
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (device.width - text_width) // 2
            text_y = y_offset
            draw.text((text_x, text_y), setting, font=font, fill="white")  # Draw text in white
            y_offset += text_height + settings_padding * 2

# Function to handle rotary encoder
def handle_rotary_encoder():
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
    button_state = GPIO.input(SW_PIN)
    if button_state == GPIO.LOW:
        print("Rotary Encoder Button:: The button is pressed")
        if current_option == 1:  # CONFIG selected
            # Handle CONFIG option
            print("CONFIG option selected")
            # You can add code here to handle the CONFIG option

try:
    draw_menu(current_option)
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
