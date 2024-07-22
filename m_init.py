import pygame
from PIL import Image, ImageDraw, ImageFont

# Initialize pygame
pygame.init()
screen_width = 64  # Width of the OLED screen in portrait mode
screen_height = 128  # Height of the OLED screen in portrait mode
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("OLED Simulation")

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

def draw_menu(current_option):
    # Create a blank image and get a drawing context
    image = Image.new('1', (screen_width, screen_height), color=0)  # '1' mode for 1-bit color depth
    draw = ImageDraw.Draw(image)

    # Load a custom font
    font_size = 12  # You can adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Draw menu options
    y_offset = top_margin
    for i, option in enumerate(menu_options):
        bbox = draw.textbbox((0, 0), option, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (screen_width - text_width) // 2
        text_y = y_offset
        if i == current_option:
            # Draw highlight
            highlight_rect = [
                0,  # Start at the left edge of the screen
                text_y - menu_padding + highlight_offset,  # Adjust to position the highlight a bit lower
                screen_width,  # End at the right edge of the screen
                text_y + text_height + menu_padding + highlight_offset
            ]
            draw.rectangle(highlight_rect, fill=1)
            draw.text((text_x, text_y), option, font=font, fill=0)  # Draw text in black
        else:
            draw.text((text_x, text_y), option, font=font, fill=1)  # Draw text in white
        y_offset += text_height + menu_padding * 2

    # Draw current settings
    settings = [f"{bpm}BPM", time_signature, f"{total_bars}BARS"]
    settings_start_y = screen_height - bottom_margin - (len(settings) * (text_height + settings_padding * 2))
    y_offset = max(y_offset, settings_start_y)
    for setting in settings:
        bbox = draw.textbbox((0, 0), setting, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (screen_width - text_width) // 2
        text_y = y_offset
        draw.text((text_x, text_y), setting, font=font, fill=1)  # Draw text in white
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
                if event.key == pygame.K_a:  # Navigate up
                    current_option = (current_option - 1) % len(menu_options)
                elif event.key == pygame.K_d:  # Navigate down
                    current_option = (current_option + 1) % len(menu_options)
                elif event.key == pygame.K_RETURN and current_option == 1:  # CONFIG selected
                    pygame.quit()
                    import config_screen
                    exit()

        # Draw the menu
        menu_surface = draw_menu(current_option)
        screen.blit(menu_surface, (0, 0))
        pygame.display.flip()

except KeyboardInterrupt:
    pygame.quit()
