from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, sh1107, ws0010
from PIL import Image, ImageDraw, ImageFont  # Import Image modules for image manipulation
import time  # Import the time module

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
# substitute bitbang_6800(RS=7, E=8, PINS=[25,24,23,27]) below if using that interface
serial = i2c(port=1, address=0x3C)

# Initialize the sh1106 device with default resolution (landscape mode)
device = sh1106(serial)

# Create an image in landscape mode
image = Image.new('1', (device.width, device.height), "black")
draw = ImageDraw.Draw(image)

# Draw the content
draw.rectangle((0, 0, device.width, device.height), outline="black", fill="white")
draw.text((30, 40), "Hello World", fill="black")

# Rotate the image by 90 degrees to achieve portrait mode
rotated_image = image.rotate(90, expand=True)

# Display the rotated image on the device
device.display(rotated_image)

# Add a delay to keep the graphic on the screen longer
time.sleep(10)  # Delay for 10 seconds
