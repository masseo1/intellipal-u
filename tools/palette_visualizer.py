#!/usr/bin/env python3
"""
Palette Visualizer - Create images showing palette changes from standard.
Highlights which colors differ from the standard palette.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont


def parse_palette(filepath: str) -> Dict[int, Tuple[str, str]]:
    """
    Parse palette file and return dict of {index: (hex_color, name)}
    Supports both formats:
    - 1: #000000 ; Black
    - #000000 ; Black
    """
    colors = {}
    color_index = 0
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            # Try format: N: #RRGGBB ; Name
            match = re.match(r'(\d+):\s*(#[0-9A-Fa-f]{6})\s*;\s*(.*)', line)
            if match:
                idx = int(match.group(1))
                color_hex = match.group(2).upper()
                color_name = match.group(3).strip()
                colors[idx] = (color_hex, color_name)
                continue
            
            # Try format: #RRGGBB ; Name (without index)
            match = re.match(r'(#[0-9A-Fa-f]{6})\s*;\s*(.*)', line)
            if match:
                color_index += 1
                color_hex = match.group(1).upper()
                color_name = match.group(2).strip()
                colors[color_index] = (color_hex, color_name)
                if color_index >= 16:
                    break  # Only 16 colors per palette
    
    return colors


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_palette_image(
    palette_path: str,
    standard_path: str,
    output_path: str = None,
    rows: int = 4,
    cell_size: int = 70,
    highlight_changed: bool = True
) -> str:
    """
    Create a stacked comparison image showing standard vs custom palette.
    Shows which colors differ with red borders.
    
    Args:
        palette_path: Path to the palette file to visualize
        standard_path: Path to the standard palette for comparison
        output_path: Where to save the image
        rows: Number of rows in the grid
        cell_size: Size of each color swatch in pixels
        highlight_changed: Whether to highlight changed colors
    
    Returns:
        Path to the generated image
    """
    # Parse palettes
    custom_colors = parse_palette(palette_path)
    standard_colors = parse_palette(standard_path)
    
    # Determine output path
    if output_path is None:
        palette_name = Path(palette_path).stem
        output_path = f"{palette_name}_comparison.png"
    
    cols = 4
    padding = 15
    label_height = 22
    title_height = 25
    border_width = 3
    
    # Dimensions for one palette grid
    grid_width = cols * cell_size + padding * 2
    grid_height = rows * (cell_size + label_height) + padding * 2
    
    # Total image: standard on top, custom on bottom
    img_width = grid_width
    img_height = title_height + grid_height * 2 + padding * 2
    
    # Create image
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    except:
        font_small = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    
    palette_name = Path(palette_path).stem
    title = f"{palette_name} vs Standard"
    draw.text((padding, 3), title, fill='black', font=font_bold)
    
    def draw_palette(colors, start_y, label):
        """Draw a palette grid at the given Y position."""
        # Draw label
        draw.text((padding, start_y + 2), label, fill='#333333', font=font_bold)
        y_offset = start_y + 20
        
        for idx in range(1, 17):
            if idx not in colors:
                continue
            
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            
            x = padding + col * cell_size
            y = y_offset + row * (cell_size + label_height)
            
            color_hex, color_name = colors[idx]
            rgb = hex_to_rgb(color_hex)
            
            # Check if this color differs from standard
            is_different = (idx not in standard_colors or 
                          standard_colors[idx][0] != custom_colors.get(idx, [''])[0])
            
            # Draw red border if different (only for custom palette)
            if is_different and label == "Custom Palette" and highlight_changed:
                draw.rectangle(
                    [x - border_width, y - border_width,
                     x + cell_size + border_width, y + cell_size + border_width],
                    outline='red', width=border_width
                )
            
            # Draw swatch
            draw.rectangle([x, y, x + cell_size, y + cell_size], 
                         fill=rgb, outline='#333333', width=1)
            
            # Draw index
            text_color = 'white' if sum(rgb) < 384 else 'black'
            draw.text((x + 3, y + 3), str(idx), fill=text_color, font=font_small)
            
            # Draw hex code below swatch
            draw.text((x, y + cell_size + 2), color_hex, fill='#555555', font=font_small)
    
    # Draw both palettes
    draw_palette(standard_colors, title_height + padding, "Standard Palette")
    draw_palette(custom_colors, title_height + grid_height + padding * 2, "Custom Palette")
    
    img.save(output_path)
    print(f"✓ Palette image saved: {output_path}")
    return output_path


def create_comparison_grid(
    palette_path: str,
    standard_path: str,
    output_path: str = None
) -> str:
    """
    Create a side-by-side comparison image.
    """
    custom_colors = parse_palette(palette_path)
    standard_colors = parse_palette(standard_path)
    
    if output_path is None:
        palette_name = Path(palette_path).stem
        output_path = f"{palette_name}_side_by_side.png"
    
    # Image parameters
    cell_size = 60
    padding = 20
    label_height = 20
    cols = 4  # 4x4 grid for 16 colors
    rows = 4
    
    # Calculate dimensions
    swatch_width = cols * cell_size + padding * 2
    swatch_height = rows * (cell_size + label_height) + padding * 2
    comparison_width = swatch_width * 2 + padding * 3
    comparison_height = swatch_height + padding
    
    # Create comparison image
    img = Image.new('RGB', (comparison_width, comparison_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except:
        font = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    
    # Helper to draw palette grid
    def draw_palette_grid(colors, start_x, start_y, title):
        draw.text((start_x, start_y), title, fill='black', font=font_bold)
        y_offset = start_y + 20
        
        for idx in range(1, 17):
            if idx not in colors:
                continue
            
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            
            x = start_x + padding + col * cell_size
            y = y_offset + padding + row * (cell_size + label_height)
            
            color_hex, color_name = colors[idx]
            rgb = hex_to_rgb(color_hex)
            
            # Draw swatch
            draw.rectangle([x, y, x + cell_size, y + cell_size], fill=rgb, outline='black', width=1)
            
            # Draw index
            text_color = 'white' if sum(rgb) < 384 else 'black'
            draw.text((x + 5, y + 5), str(idx), fill=text_color, font=font)
            
            # Draw hex code below
            draw.text((x, y + cell_size + 2), color_hex, fill='#666666', font=font)
    
    # Draw both palettes
    draw_palette_grid(standard_colors, padding, padding, "Standard")
    draw_palette_grid(custom_colors, swatch_width + padding * 2, padding, "Custom")
    
    # Highlight differences
    for idx in custom_colors:
        if idx in standard_colors and standard_colors[idx][0] != custom_colors[idx][0]:
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            x = swatch_width + padding * 2 + padding + col * cell_size
            y = padding + 20 + padding + row * (cell_size + label_height)
            
            # Draw red outline for changed colors
            draw.rectangle([x - 2, y - 2, x + cell_size + 2, y + cell_size + 2],
                         outline='red', width=2)
    
    img.save(output_path)
    print(f"✓ Comparison image saved: {output_path}")
    return output_path


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: palette_visualizer.py <palette_file> [standard_palette]")
        print("       palette_visualizer.py --compare <palette_file> [standard_palette]")
        sys.exit(1)
    
    # Default paths
    palettes_dir = Path(__file__).parent.parent / 'palettes'
    standard = palettes_dir / 'Standard_Intellivision.txt'
    
    if sys.argv[1] == '--compare':
        palette = sys.argv[2] if len(sys.argv) > 2 else None
        custom_standard = sys.argv[3] if len(sys.argv) > 3 else str(standard)
        
        if palette is None:
            print("Usage: palette_visualizer.py --compare <palette_file> [standard_palette]")
            sys.exit(1)
        
        create_comparison_grid(palette, custom_standard)
    else:
        palette = sys.argv[1]
        custom_standard = sys.argv[2] if len(sys.argv) > 2 else str(standard)
        
        create_palette_image(palette, custom_standard)
