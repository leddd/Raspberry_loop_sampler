import pygame
from PIL import Image, ImageDraw, ImageFont

# Initialize pygame
pygame.init()
screen_width = 64  # Width of the OLED screen in portrait mode
screen_height = 128  # Height of the OLED screen in portrait mode
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("OLED Simulation - CONFIG")

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

# Padding and margin variables
settings_padding = 4
highlight_offset = 2  # Offset of the highlight position

def draw_config_screen(current_config_option):
    # Create a blank image and get a drawing context
    image = Image.new('1', (screen_width, screen_height), color=0)  # '1' mode for 1-bit color depth
    draw = ImageDraw.Draw(image)

    # Load a custom font
    font_size = 12  # You can adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text height
    sample_text = "Sample"
    bbox = draw.textbbox((0, 0), sample_text, font=font)  # Get bounding box
    text_height = bbox[3] - bbox[1]

    # Draw config options
    y_offset = (screen_height - (len(config_options) * (text_height + settings_padding * 2))) // 2
    for i, option in enumerate(config_options):
        if option == "BPM":
            value = f"BPM{config_option_values[option]}"
        elif option == "TIME SIGNATURE":
            value = config_option_values[option]
        elif option == "TOTAL BARS":
            value = f"{config_option_values[option]}BARS"
        option_text = f"{value}"
        bbox = draw.textbbox((0, 0), option_text, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_x = (screen_width - text_width) // 2
        text_y = y_offset
        if i == current_config_option:
            # Draw highlight
            highlight_rect = [
                0,  # Start at the left edge of the screen
                text_y - settings_padding + highlight_offset,  # Adjust to position the highlight a bit lower
                screen_width,  # End at the right edge of the screen
                text_y + text_height + settings_padding + highlight_offset
            ]
            draw.rectangle(highlight_rect, fill=1)
            draw.text((text_x, text_y), option_text, font=font, fill=0)  # Draw text in black
        else:
            draw.text((text_x, text_y), option_text, font=font, fill=1)  # Draw text in white
        y_offset += text_height + settings_padding * 2

    # Convert image to a format suitable for pygame
    pygame_image = pygame.image.fromstring(image.convert('RGB').tobytes(), image.size, 'RGB')

    return pygame_image

try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:  # Navigate up in config
                    if current_config_option == 0:  # BPM
                        config_option_values["BPM"] = max(1, config_option_values["BPM"] - 1)
                    elif current_config_option == 1:  # TIME SIGNATURE
                        current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                        config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index - 1) % len(time_signature_options)]
                    elif current_config_option == 2:  # TOTAL BARS
                        config_option_values["TOTAL BARS"] = max(1, config_option_values["TOTAL BARS"] - 1)
                elif event.key == pygame.K_d:  # Navigate down in config
                    if current_config_option == 0:  # BPM
                        config_option_values["BPM"] = min(300, config_option_values["BPM"] + 1)
                    elif current_config_option == 1:  # TIME SIGNATURE
                        current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                        config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index + 1) % len(time_signature_options)]
                    elif current_config_option == 2:  # TOTAL BARS
                        config_option_values["TOTAL BARS"] = min(8, config_option_values["TOTAL BARS"] + 1)
                elif event.key == pygame.K_l:  # Move to next config option
                    if current_config_option < len(config_options) - 1:
                        current_config_option += 1
                    else:
                        # Save settings and exit config
                        pygame.quit()
                        exit()

        # Draw the config screen
        config_surface = draw_config_screen(current_config_option)
        screen.blit(config_surface, (0, 0))
        pygame.display.flip()

except KeyboardInterrupt:
    pygame.quit()
