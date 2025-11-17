"""
Generate PWA icons for the Badminton Matchup Manager.
Creates 192x192 and 512x512 icons with a simple badminton-themed design.
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    has_pillow = True
except ImportError:
    has_pillow = False
    print("Pillow not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont
    print("Pillow installed successfully!")

import os

# Create icons directory if it doesn't exist
icons_dir = os.path.join("static", "icons")
os.makedirs(icons_dir, exist_ok=True)

def create_icon(size, filename, maskable=False):
    """Create a simple badminton-themed icon."""
    # Green background matching the theme color
    bg_color = (11, 132, 87)  # #0b8457
    
    # Create image with green background
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # For maskable icons, add safe zone padding (80% of size in center)
    if maskable:
        padding = int(size * 0.1)  # 10% padding on each side
    else:
        padding = int(size * 0.15)  # 15% padding for regular icons
    
    # Draw a simple badminton shuttlecock representation
    # White circle for the cork
    cork_radius = int((size - padding * 2) * 0.2)
    cork_center = (size // 2, size // 2 - cork_radius)
    draw.ellipse(
        [cork_center[0] - cork_radius, cork_center[1] - cork_radius,
         cork_center[0] + cork_radius, cork_center[1] + cork_radius],
        fill='white'
    )
    
    # Draw feathers (simplified as triangular shape)
    feather_height = int((size - padding * 2) * 0.4)
    feather_width = int((size - padding * 2) * 0.3)
    
    # Triangle points for shuttlecock feathers
    points = [
        (size // 2 - feather_width // 2, cork_center[1] + cork_radius),
        (size // 2 + feather_width // 2, cork_center[1] + cork_radius),
        (size // 2, cork_center[1] + cork_radius + feather_height)
    ]
    draw.polygon(points, fill='white', outline='white')
    
    # Add some feather details (lines)
    for i in range(3):
        x_offset = (i - 1) * (feather_width // 4)
        draw.line([
            (size // 2 + x_offset, cork_center[1] + cork_radius),
            (size // 2 + x_offset, cork_center[1] + cork_radius + feather_height)
        ], fill=bg_color, width=max(1, size // 100))
    
    # Save the icon
    filepath = os.path.join(icons_dir, filename)
    img.save(filepath, 'PNG')
    print(f"Created {filepath}")

# Generate all required icons
print("Generating PWA icons...")
create_icon(192, "icon-192.png", maskable=False)
create_icon(512, "icon-512.png", maskable=False)
create_icon(192, "maskable-192.png", maskable=True)
create_icon(512, "maskable-512.png", maskable=True)

print("\n✅ All icons generated successfully!")
print("Icons are located in: static/icons/")
