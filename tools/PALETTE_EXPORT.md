# Palette Export Feature

Export your custom palettes as visual images showing which colors differ from the standard.

## Usage

### From the GUI

1. Select a palette from the list
2. Click the **Export** button (camera/image icon) in the toolbar
3. Choose export format:
   - **Full Comparison**: Displays all 16 colors with index numbers, names, and hex codes. Changed colors are highlighted with a red border.
   - **Side-by-Side Comparison**: Shows standard palette and custom palette side-by-side for easy visual comparison.
4. The image is saved in the palettes folder as:
   - `<palette_name>_comparison.png` (Full Comparison)
   - `<palette_name>_side_by_side.png` (Side-by-Side)

### From Command Line

```bash
# Full comparison (highlights changed colors)
python3 tools/palette_visualizer.py palettes/your_palette.txt

# Side-by-side comparison
python3 tools/palette_visualizer.py --compare palettes/your_palette.txt

# Custom standard palette for comparison
python3 tools/palette_visualizer.py palettes/your_palette.txt palettes/your_standard.txt
```

## Features

- **Changed Color Highlighting**: Colors that differ from the standard palette are marked with a red border
- **Color Information**: Each swatch shows:
  - Index number (1-16)
  - Color name
  - Hex code (#RRGGBB)
- **Color Contrast**: Text color automatically adjusts (white on dark colors, black on light colors) for readability
- **Multiple Formats**: Choose between full view and side-by-side comparison

## Example Output

The generated images clearly show which palette entries have been modified, making it easy to:
- Document your custom palette changes
- Share palette modifications with others
- Create visual references for game-specific color adjustments

## Requirements

- Python 3.7+
- Pillow (PIL) for image generation

The feature is automatically integrated into the IntelliPal GUI when you select a palette and click Export.
