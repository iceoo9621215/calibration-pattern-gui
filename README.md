# Camera Calibration Pattern Generator

A Python-based tool for generating camera calibration patterns, featuring circles, checkerboards, and ChArUco boards.

![UI Preview](UI\ Preview.png)

## Requirements

- Python 3.x
- \`GTK3\` (required for the Tkinter-based GUI to function properly)
- The following Python packages:
  - \`numpy\`
  - \`Pillow\`
  - \`cairosvg\`
  - \`svgwrite\`
  - (Optionally) \`tkinter\` if not included with your Python installation

You can run \`python requirment.py\` to check for any missing dependencies.  
If packages are missing, install them:  
**Note:** On some systems, you may need to install \`GTK3\` separately (e.g., using a package manager).

## Usage

- **GUI Mode**  
  Run \`python gen_pattern.py\` to launch the GUI and preview generated patterns.

- **Command Line Mode**  
  Use \`python gen_pattern.py --help\` to see available options. For example:  
  This will create a pattern with 8 columns, 11 rows, and a square size of 20 mm, saving it to \`out.svg\`.
