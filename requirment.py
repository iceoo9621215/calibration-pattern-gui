#!/usr/bin/env python
"""
requirment.py
A script to check for required packages for the camera calibration pattern project.
"""

import importlib
import sys

dependencies = {
    "numpy": "numpy",
    "Pillow": "PIL",
    "cairosvg": "cairosvg",
    "svgwrite": "svgwrite"
}

def check_dependencies():
    missing = []
    for pkg_name, module_name in dependencies.items():
        try:
            importlib.import_module(module_name)
            print(f"{pkg_name} is installed.")
        except ImportError:
            print(f"{pkg_name} is missing. Please install it using pip.")
            missing.append(pkg_name)
    if missing:
        sys.exit("One or more required packages are missing.")

if __name__ == "__main__":
    check_dependencies()