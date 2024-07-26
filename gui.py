import time
import threading
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

# Global Variables and Constants
DIRECTION_CW = 0
DIRECTION_CCW = 1

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'
font_size = 12  # Adjust the font size as needed
font = ImageFont.truetype(font_path, font_size)

# Menu options
menu_options = ["GRABAR", "CONFIG"]
current_option = 0

# Config options
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 4
}
time_signature_options = ["2/4", "3/4", "4/4"]
current_config_option = 0

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

# Define GPIO pins for the rotary encoder
CLK_PIN = 17
DT_PIN = 27
SW_PIN = 22

# Set up GPIO pins for rotary encoder
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

prev_CLK_state = GPIO.input(CLK_PIN)

# Set up locks and other variables
lock = threading.Lock()
in_config_menu = False

def draw_menu(current_option):
    image = Image.new('1', (64, 128), "black")
    draw = ImageDraw.Draw(image)
    
    y_offset = top_margin
    for i, option in enumerate(menu_options):
        bbox = draw.textbbox((0, 0), option, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = y_offset
        if i == current_option:
            highlight_rect = [
                0,
                text_y - menu_padding + highlight_offset,
                64,
                text_y + text_height + menu_padding + highlight_offset
            ]
            draw.rectangle(highlight_rect, outline="white", fill="white")
            draw.text((text_x, text_y), option, font=font, fill="black")
        else:
            draw.text((text_x, text_y), option, font=font, fill="white")
        y_offset += text_height + menu_padding * 2

    settings = [f"{bpm}BPM", time_signature, f"{total_bars}BARS"]
    settings_start_y = 128 - bottom_margin - (len(settings) * (text_height + settings_padding * 2))
    y_offset = max(y_offset, settings_start_y)
    for setting in settings:
        bbox = draw.textbbox((0, 0), setting, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = y_offset
        draw.text((text_x, text_y), setting, font=font, fill="white")
        y_offset += text_height + settings_padding * 2

    rotated_image = image.rotate(270, expand=True)
    device.display(rotated_image)

def draw_config_screen():
    with lock:
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        
        option = config_options[current_config_option]
        if option == "BPM":
            value = f"{config_option_values[option]} BPM"
        elif option == "TIME SIGNATURE":
            value = config_option_values[option]
        elif option == "TOTAL BARS":
            value = f"{config_option_values[option]} BARS"

        bbox = draw.textbbox((0, 0), value, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = (128 - text_height) // 2

        draw.text((text_x, text_y), value, font=font, fill="white")
        
        rotated_image = image.rotate(270, expand=True)
        device.display(rotated_image)

def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, current_config_option, current_option, in_config_menu
    while True:
        CLK_state = GPIO.input(CLK_PIN)
        DT_state = GPIO.input(DT_PIN)

        if CLK_state != prev_CLK_state:
            if DT_state != CLK_state:
                direction = DIRECTION_CW
            else:
                direction = DIRECTION_CCW

            counter += 1
            if counter % 2 == 0:
                with lock:
                    if in_config_menu:
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
                    else:
                        if direction == DIRECTION_CW:
                            current_option = (current_option + 1) % len(menu_options)
                        else:
                            current_option = (current_option - 1) % len(menu_options)

        prev_CLK_state = CLK_state
        time.sleep(0.001)

def update_screen():
    while True:
        if in_config_menu:
            draw_config_screen()
        else:
            draw_menu(current_option)
        time.sleep(0.1)

def handle_button_press():
    global in_config_menu
    while True:
        if GPIO.input(SW_PIN) == GPIO.LOW:
            time.sleep(0.05)  # Debounce
            if GPIO.input(SW_PIN) == GPIO.LOW:
                with lock:
                    if in_config_menu:
                        # Add any actions you want to perform in the config menu when button is pressed
                        pass
                    else:
                        if menu_options[current_option] == "CONFIG":
                            in_config_menu = True
                while GPIO.input(SW_PIN) == GPIO.LOW:
                    time.sleep(0.01)  # Wait for button release

try:
    setup_matrix_keypad()

    print(f"Listening for rotary encoder changes and button presses...")

    threading.Thread(target=handle_rotary_encoder, daemon=True).start()
    threading.Thread(target=update_screen, daemon=True).start()
    threading.Thread(target=handle_button_press, daemon=True).start()

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
