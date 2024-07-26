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

# Disable GPIO warnings
GPIO.setwarnings(False)

# Set up the GPIO mode
GPIO.setmode(GPIO.BCM)

# Set up GPIO pins for rotary encoder
GPIO.setup(CLK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initial state
last_state = GPIO.input(CLK_PIN)
current_option = 0

# Interrupt handlers for rotary encoder
def rotary_callback(channel):
    global last_state, current_option
    clk_state = GPIO.input(CLK_PIN)
    dt_state = GPIO.input(DT_PIN)

    if clk_state != last_state:
        if dt_state != clk_state:
            current_option = (current_option + 1) % len(menu_options)
        else:
            current_option = (current_option - 1) % len(menu_options)

        draw_menu(current_option)

    last_state = clk_state

def button_callback(channel):
    global current_option
    if GPIO.input(SW_PIN) == GPIO.LOW:
        # Trigger the action for the current menu option
        if current_option == 0:
            print("Action: GRABAR")
            # Add action for GRABAR
        elif current_option == 1:
            print("Action: CONFIG")
            # Add action for CONFIG

# Set up event detection for rotary encoder
GPIO.add_event_detect(CLK_PIN, GPIO.BOTH, callback=rotary_callback, bouncetime=1)
GPIO.add_event_detect(SW_PIN, GPIO.FALLING, callback=button_callback, bouncetime=200)

try:
    print("Listening for rotary encoder changes and button presses...")
    draw_menu(current_option)  # Draw the initial menu
    while True:
        time.sleep(0.1)  # Main loop can be slow since we're using interrupts
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
