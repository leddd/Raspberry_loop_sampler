import time
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106

class RotaryEncoderConfig:
    DIRECTION_CW = 0
    DIRECTION_CCW = 1

    def __init__(self):
        self.serial = i2c(port=1, address=0x3C)
        self.device = sh1106(self.serial)
        self.font_path = 'fonts/InputSansNarrow-Thin.ttf'
        self.config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
        self.config_option_values = {
            "BPM": 120,
            "TIME SIGNATURE": "4/4",
            "TOTAL BARS": 4
        }
        self.time_signature_options = ["2/4", "3/4", "4/4", "6/8"]
        self.current_config_option = 0
        self.counter = 0
        self.direction = self.DIRECTION_CW
        self.CLK_state = 0
        self.prev_CLK_state = GPIO.HIGH
        self.button_pressed = False
        self.prev_button_state = GPIO.HIGH

        self.CLK_PIN = 17
        self.DT_PIN = 27
        self.SW_PIN = 22

        self.setup_gpio()
        self.draw_config_screen()

    def setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.CLK_PIN, GPIO.IN)
        GPIO.setup(self.DT_PIN, GPIO.IN)
        GPIO.setup(self.SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.prev_CLK_state = GPIO.input(self.CLK_PIN)

    def draw_config_screen(self):
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        font_size = 12
        font = ImageFont.truetype(self.font_path, font_size)

        option = self.config_options[self.current_config_option]
        value = ""
        if option == "BPM":
            value = f"{self.config_option_values[option]} BPM"
        elif option == "TIME SIGNATURE":
            value = self.config_option_values[option]
        elif option == "TOTAL BARS":
            value = f"{self.config_option_values[option]} BARS"

        bbox = draw.textbbox((0, 0), value, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = (128 - text_height) // 2 + 8

        draw.text((text_x, text_y), value, font=font, fill="white")
        rotated_image = image.rotate(270, expand=True)
        self.device.display(rotated_image)

    def handle_rotary_encoder(self):
        CLK_state = GPIO.input(self.CLK_PIN)
        if CLK_state != self.prev_CLK_state:
            if GPIO.input(self.DT_PIN) == GPIO.HIGH:
                self.counter -= 1
                self.direction = self.DIRECTION_CCW
            else:
                self.counter += 1
                self.direction = self.DIRECTION_CW

            if self.direction == self.DIRECTION_CW:
                if self.current_config_option == 0:
                    self.config_option_values["BPM"] = min(300, self.config_option_values["BPM"] + 1)
                elif self.current_config_option == 1:
                    current_ts_index = self.time_signature_options.index(self.config_option_values["TIME SIGNATURE"])
                    self.config_option_values["TIME SIGNATURE"] = self.time_signature_options[(current_ts_index + 1) % len(self.time_signature_options)]
                elif self.current_config_option == 2:
                    self.config_option_values["TOTAL BARS"] = min(8, self.config_option_values["TOTAL BARS"] + 1)
            elif self.direction == self.DIRECTION_CCW:
                if self.current_config_option == 0:
                    self.config_option_values["BPM"] = max(1, self.config_option_values["BPM"] - 1)
                elif self.current_config_option == 1:
                    current_ts_index = self.time_signature_options.index(self.config_option_values["TIME SIGNATURE"])
                    self.config_option_values["TIME SIGNATURE"] = self.time_signature_options[(current_ts_index - 1) % len(self.time_signature_options)]
                elif self.current_config_option == 2:
                    self.config_option_values["TOTAL BARS"] = max(1, self.config_option_values["TOTAL BARS"] - 1)

            self.draw_config_screen()
        self.prev_CLK_state = CLK_state

    def handle_encoder_button(self):
        button_state = GPIO.input(self.SW_PIN)
        if button_state != self.prev_button_state:
            time.sleep(0.01)
            if button_state == GPIO.LOW:
                self.button_pressed = True
                if self.current_config_option < len(self.config_options) - 1:
                    self.current_config_option += 1
                else:
                    print("Configuration complete.")
                    GPIO.cleanup()
                    exit()
                self.draw_config_screen()
            else:
                self.button_pressed = False
        self.prev_button_state = button_state

    def run(self):
        try:
            print(f"Listening for rotary encoder changes...")
            while True:
                self.handle_rotary_encoder()
                self.handle_encoder_button()
                time.sleep(0.001)  # Reduced delay to improve responsiveness
        except KeyboardInterrupt:
            GPIO.cleanup()

if __name__ == "__main__":
    encoder_config = RotaryEncoderConfig()
    encoder_config.run()
