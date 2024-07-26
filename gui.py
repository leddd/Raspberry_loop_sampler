from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw, Image
import RPi.GPIO as GPIO
import time

# Initialize the OLED screen
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

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

# Load a custom font
font_size = 12  # You can adjust the font size as needed
font = ImageFont.truetype(font_path, font_size)

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

# Define the GPIO pins for the rotary encoder
CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

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

# Set up GPIO pins for rotary encoder
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Read the initial state of the rotary encoder's CLK pin
prev_CLK_state = GPIO.input(CLK_PIN)
prev_DT_state = GPIO.input(DT_PIN)

# Function to handle rotary encoder
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, prev_DT_state, current_option

    # Read the current state of the rotary encoder's CLK and DT pins
    CLK_state = GPIO.input(CLK_PIN)
    DT_state = GPIO.input(DT_PIN)

    # If the state of CLK is changed, then pulse occurred
    if CLK_state != prev_CLK_state:
        # Determine the direction
        if DT_state != CLK_state:
            counter += 1
            direction = DIRECTION_CW
            current_option = (current_option + 1) % len(menu_options)
        else:
            counter -= 1
            direction = DIRECTION_CCW
            current_option = (current_option - 1) % len(menu_options)

        print("Rotary Encoder:: direction:", "CLOCKWISE" if direction == DIRECTION_CW else "ANTICLOCKWISE",
              "- count:", counter)

        # Redraw the menu with the updated current_option
        draw_menu(current_option)

    # Save last CLK and DT state
    prev_CLK_state = CLK_state
    prev_DT_state = DT_state

# Function to handle button press on rotary encoder
def handle_encoder_button():
    global button_pressed, prev_button_state

    # State change detection for the button
    button_state = GPIO.input(SW_PIN)
    if button_state != prev_button_state:
        time.sleep(0.01)  # Add a small delay to debounce
        if button_state == GPIO.LOW:
            print("Rotary Encoder Button:: The button is pressed")
            button_pressed = True
            # Trigger the action for the current menu option
            if current_option == 0:
                print("Action: GRABAR")
                # Add action for GRABAR
            elif current_option == 1:
                print("Action: CONFIG")
                # Add action for CONFIG
        else:
            button_pressed = False

    prev_button_state = button_state

try:
    print(f"Listening for rotary encoder changes and button presses...")
    draw_menu(current_option)  # Draw the initial menu
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.001)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
