from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, sh1107, ws0010
import time  # Import the time module

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
# substitute bitbang_6800(RS=7, E=8, PINS=[25,24,23,27]) below if using that interface
serial = i2c(port=1, address=0x3C)

# Initialize the sh1106 device in portrait mode
device = sh1106(serial, width=64, height=128, rotate=1)  # Use rotate=3 for 270° rotation

with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="black", fill="white")
    draw.text((30, 40), "Hello World", fill="black")

# Add a delay to keep the graphic on the screen longer
time.sleep(10)  # Delay for 10 seconds
