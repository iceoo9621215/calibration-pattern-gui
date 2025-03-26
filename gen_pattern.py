#!/usr/bin/env python

"""gen_pattern.py
A GUI tool for generating and previewing camera calibration patterns.
"""

import argparse
import numpy as np
import json
import gzip
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import io
import cairosvg
import svgwrite


class PatternMaker:
    def __init__(self, cols, rows, output, units, square_size, radius_rate, page_width, page_height, markers, aruco_marker_size, dict_file):
        self.cols = cols
        self.rows = rows
        self.output = output
        self.units = units
        if self.units == "inches":
            self.units = "in"
        self.square_size = square_size
        self.radius_rate = radius_rate
        self.width = page_width
        self.height = page_height
        self.markers = markers
        self.aruco_marker_size = aruco_marker_size
        self.dict_file = dict_file

        # Initialize an SVG drawing with svgwrite
        self.dwg = svgwrite.Drawing(filename=output, size=(f"{self.width}{self.units}", f"{self.height}{self.units}"),
                                    viewBox=f"0 0 {self.width} {self.height}")
        self.g = self.dwg.g()  # Create a group to hold all elements

    def make_circles_pattern(self):
        spacing = self.square_size
        r = spacing / self.radius_rate
        pattern_width = ((self.cols - 1.0) * spacing) + (2.0 * r)
        pattern_height = ((self.rows - 1.0) * spacing) + (2.0 * r)
        x_spacing = (self.width - pattern_width) / 2.0
        y_spacing = (self.height - pattern_height) / 2.0
        for x in range(0, self.cols):
            for y in range(0, self.rows):
                dot = self.dwg.circle(
                    center=((x * spacing) + x_spacing + r, (y * spacing) + y_spacing + r),
                    r=r,
                    fill="black",
                    stroke="none"
                )
                self.g.add(dot)

    def make_acircles_pattern(self):
        spacing = self.square_size
        r = spacing / self.radius_rate
        pattern_width = ((self.cols-1.0) * 2 * spacing) + spacing + (2.0 * r)
        pattern_height = ((self.rows-1.0) * spacing) + (2.0 * r)
        x_spacing = (self.width - pattern_width) / 2.0
        y_spacing = (self.height - pattern_height) / 2.0
        for x in range(0, self.cols):
            for y in range(0, self.rows):
                dot = self.dwg.circle(
                    center=((2 * x * spacing) + (y % 2)*spacing + x_spacing + r, (y * spacing) + y_spacing + r),
                    r=r,
                    fill="black",
                    stroke="none"
                )
                self.g.add(dot)

    def make_checkerboard_pattern(self):
        spacing = self.square_size
        xspacing = (self.width - self.cols * self.square_size) / 2.0
        yspacing = (self.height - self.rows * self.square_size) / 2.0
        for x in range(0, self.cols):
            for y in range(0, self.rows):
                if x % 2 == y % 2:
                    square = self.dwg.rect(
                        insert=(x * spacing + xspacing, y * spacing + yspacing),
                        size=(spacing, spacing),
                        fill="black",
                        stroke="none"
                    )
                    self.g.add(square)

    @staticmethod
    def _make_round_rect(x, y, diam, corners=("right", "right", "right", "right")):
        rad = diam / 2
        path = ["M{},{}".format(x + rad, y)]  # Start at top-left (adjusted for radius)
        cw_point = ((0, 0), (diam, 0), (diam, diam), (0, diam))
        mid_cw_point = ((0, rad), (rad, 0), (diam, rad), (rad, diam))
        n = len(cw_point)
        for i in range(n):
            if corners[i] == "right":
                path.append("L{},{}".format(x + cw_point[i][0], y + cw_point[i][1]))
                path.append("L{},{}".format(x + mid_cw_point[(i + 1) % n][0], y + mid_cw_point[(i + 1) % n][1]))
            elif corners[i] == "round":
                path.append("A{},{} 0 0 1 {},{}".format(rad, rad, x + mid_cw_point[(i + 1) % n][0], y + mid_cw_point[(i + 1) % n][1]))
            else:
                raise TypeError("unknown corner type")
        path.append("Z")  # Close the path
        return " ".join(path)

    def _get_type(self, x, y):
        corners = ["right", "right", "right", "right"]
        is_inside = True
        if x == 0:
            corners[0] = "round"
            corners[3] = "round"
            is_inside = False
        if y == 0:
            corners[0] = "round"
            corners[1] = "round"
            is_inside = False
        if x == self.cols - 1:
            corners[1] = "round"
            corners[2] = "round"
            is_inside = False
        if y == self.rows - 1:
            corners[2] = "round"
            corners[3] = "round"
            is_inside = False
        return corners, is_inside

    def make_radon_checkerboard_pattern(self):
        spacing = self.square_size
        xspacing = (self.width - self.cols * self.square_size) / 2.0
        yspacing = (self.height - self.rows * self.square_size) / 2.0
        for x in range(0, self.cols):
            for y in range(0, self.rows):
                if x % 2 == y % 2:
                    corner_types, is_inside = self._get_type(x, y)
                    if is_inside:
                        square = self.dwg.rect(
                            insert=(x * spacing + xspacing, y * spacing + yspacing),
                            size=(spacing, spacing),
                            fill="black",
                            stroke="none"
                        )
                    else:
                        square = self.dwg.path(
                            d=self._make_round_rect(x * spacing + xspacing, y * spacing + yspacing, spacing, corner_types),
                            fill="black",
                            stroke="none"
                        )
                    self.g.add(square)
        if self.markers is not None:
            r = self.square_size * 0.17
            pattern_width = ((self.cols - 1.0) * spacing) + (2.0 * r)
            pattern_height = ((self.rows - 1.0) * spacing) + (2.0 * r)
            x_spacing = (self.width - pattern_width) / 2.0
            y_spacing = (self.height - pattern_height) / 2.0
            for x, y in self.markers:
                color = "black"
                if x % 2 == y % 2:
                    color = "white"
                dot = self.dwg.circle(
                    center=((x * spacing) + x_spacing + r, (y * spacing) + y_spacing + r),
                    r=r,
                    fill=color,
                    stroke="none"
                )
                self.g.add(dot)

    @staticmethod
    def _create_marker_bits(markerSize_bits, byteList):
        marker = np.zeros((markerSize_bits+2, markerSize_bits+2))
        bits = marker[1:markerSize_bits+1, 1:markerSize_bits+1]
        for i in range(markerSize_bits):
            for j in range(markerSize_bits):
                bits[i][j] = int(byteList[i*markerSize_bits+j])
        return marker

    def make_charuco_board(self):
        if self.aruco_marker_size > self.square_size:
            print("Error: Aruco marker cannot be larger than chessboard square!")
            return

        if self.dict_file.split(".")[-1] == "gz":
            with gzip.open(self.dict_file, 'r') as fin:
                json_bytes = fin.read()
                json_str = json_bytes.decode('utf-8')
                dictionary = json.loads(json_str)
        else:
            with open(self.dict_file) as f:
                dictionary = json.load(f)

        if dictionary["nmarkers"] < int(self.cols * self.rows / 2):
            print("Error: Aruco dictionary contains fewer markers than needed for the chosen board.")
            return

        markerSize_bits = dictionary["markersize"]
        side = self.aruco_marker_size / (markerSize_bits + 2)
        spacing = self.square_size
        xspacing = (self.width - self.cols * self.square_size) / 2.0
        yspacing = (self.height - self.rows * self.square_size) / 2.0
        ch_ar_border = (self.square_size - self.aruco_marker_size) / 2
        if ch_ar_border < side * 0.7:
            print(f"Marker border {ch_ar_border} is less than 70% of ArUco pin size {int(side)}")
        marker_id = 0
        for y in range(0, self.rows):
            for x in range(0, self.cols):
                if x % 2 == y % 2:
                    square = self.dwg.rect(
                        insert=(x * spacing + xspacing, y * spacing + yspacing),
                        size=(spacing, spacing),
                        fill="black",
                        stroke="none"
                    )
                    self.g.add(square)
                else:
                    img_mark = self._create_marker_bits(markerSize_bits, dictionary["marker_" + str(marker_id)])
                    marker_id += 1
                    x_pos = x * spacing + xspacing
                    y_pos = y * spacing + yspacing
                    square = self.dwg.rect(
                        insert=(x_pos + ch_ar_border, y_pos + ch_ar_border),
                        size=(self.aruco_marker_size, self.aruco_marker_size),
                        fill="black",
                        stroke="none"
                    )
                    self.g.add(square)
                    for x_ in range(len(img_mark[0])):
                        for y_ in range(len(img_mark)):
                            if img_mark[y_][x_] != 0:
                                square = self.dwg.rect(
                                    insert=(x_pos + ch_ar_border + (x_ * side), y_pos + ch_ar_border + (y_ * side)),
                                    size=(side, side),
                                    fill="white",
                                    stroke="white",
                                    stroke_width=spacing * 0.01
                                )
                                self.g.add(square)

    def get_svg_string(self):
        self.dwg.add(self.g)
        return self.dwg.tostring()

    def save(self):
        self.dwg.add(self.g)
        self.dwg.save()


class PatternMakerGUI:
    def __init__(self, root):
        self.img = None
        self.root = root
        self.root.title("Camera Calibration Pattern Generator")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f5f5f5")  # Light gray background for the root window

        # Color scheme
        self.colors = {
            "bg": "#f5f5f5",            # Light gray background
            "frame_bg": "#ffffff",      # White frame background
            "accent": "#1a73e8",        # Blue accent color
            "text": "#202124",          # Dark gray text
            "border": "#dadce0",        # Light border color
            "canvas_bg": "#ffffff",     # White canvas background
            "button_bg": "#1a73e8",     # Blue button background
            "button_fg": "#ffffff",     # White button text
            "hover_bg": "#1765cc"       # Darker blue for button hover
        }

        # Apply a custom theme and style to improve UI appearance
        self.configure_styles()

        # Dictionary of page sizes (ISO standard, mm)
        self.page_sizes = {
            "A0": [840, 1188],
            "A1": [594, 840],
            "A2": [420, 594],
            "A3": [297, 420],
            "A4": [210, 297],
            "A5": [148, 210]
        }

        # Default values
        self.output_file = "out.svg"
        self.columns = 8
        self.rows = 11
        self.pattern_type = "circles"
        self.units = "mm"
        self.square_size = 20.0
        self.radius_rate = 5.0
        self.page_size = "A4"
        self.page_width = self.page_sizes[self.page_size][0]
        self.page_height = self.page_sizes[self.page_size][1]
        self.markers = None
        self.aruco_marker_size = 10.0
        self.dict_file = "DICT_ARUCO_ORIGINAL.json"

        # Create main container with padding
        self.main_container = ttk.Frame(root, padding=15, style="Main.TFrame")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create left and right panels with a separator
        self.left_frame = ttk.Frame(self.main_container, style="Left.TFrame")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        self.separator = ttk.Separator(self.main_container, orient=tk.VERTICAL)
        self.separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.right_frame = ttk.Frame(self.main_container, style="Right.TFrame")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create settings controls
        self.create_settings_controls()

        # Create preview canvas
        self.create_preview_canvas()

        # Create buttons
        self.create_buttons()

        # Generate initial preview
        self.generate_preview()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure frame styles
        style.configure("Main.TFrame", background=self.colors["bg"])
        style.configure("Left.TFrame", background=self.colors["bg"])
        style.configure("Right.TFrame", background=self.colors["bg"])
        
        # Configure label frame styles
        style.configure("TLabelframe", background=self.colors["frame_bg"], foreground=self.colors["text"])
        style.configure("TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["accent"], 
                        font=('Segoe UI', 10, 'bold'))
        
        # Configure regular label styles
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=('Segoe UI', 9))
        
        # Configure entry and spinbox styles
        style.configure("TEntry", fieldbackground=self.colors["frame_bg"], bordercolor=self.colors["border"])
        style.map("TEntry", fieldbackground=[("focus", self.colors["frame_bg"])])
        
        style.configure("TSpinbox", fieldbackground=self.colors["frame_bg"], bordercolor=self.colors["border"])
        style.map("TSpinbox", fieldbackground=[("focus", self.colors["frame_bg"])])
        
        # Configure combobox styles
        style.configure("TCombobox", fieldbackground=self.colors["frame_bg"], 
                        background=self.colors["frame_bg"], foreground=self.colors["text"])
        
        # Configure button styles
        style.configure("TButton", background=self.colors["button_bg"], foreground=self.colors["button_fg"],
                        bordercolor=self.colors["accent"], font=('Segoe UI', 9))
        style.map("TButton", background=[("active", self.colors["hover_bg"])])
        
        # Create special button styles
        style.configure("Accent.TButton", background=self.colors["button_bg"], foreground=self.colors["button_fg"],
                        bordercolor=self.colors["accent"], font=('Segoe UI', 9, 'bold'))
        style.map("Accent.TButton", background=[("active", self.colors["hover_bg"])])
        
        style.configure("Exit.TButton", background="#f44336", foreground="#ffffff",
                        bordercolor="#d32f2f", font=('Segoe UI', 9))
        style.map("Exit.TButton", background=[("active", "#d32f2f")])

    def create_settings_controls(self):
        # Pattern settings frame with improved styling
        pattern_frame = ttk.LabelFrame(self.left_frame, text="Pattern Settings", padding=15)
        pattern_frame.pack(fill=tk.X, pady=10, ipady=5)

        # Add a little more spacing between rows
        row_padding = 8

        # Pattern type selection
        ttk.Label(pattern_frame, text="Pattern Type:").grid(row=0, column=0, sticky=tk.W, pady=row_padding)
        self.type_var = tk.StringVar(value=self.pattern_type)
        type_combo = ttk.Combobox(pattern_frame, textvariable=self.type_var,
                                  values=["circles", "acircles", "checkerboard", "radon_checkerboard"],
                                  state="readonly", width=20)
        type_combo.grid(row=0, column=1, sticky=tk.W+tk.E, pady=row_padding, padx=(5, 0))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.generate_preview())

        # Rows and columns with improved layout
        ttk.Label(pattern_frame, text="Rows:").grid(row=1, column=0, sticky=tk.W, pady=row_padding)
        self.rows_var = tk.IntVar(value=self.rows)
        rows_spinbox = ttk.Spinbox(pattern_frame, from_=1, to=50, textvariable=self.rows_var, width=8)
        rows_spinbox.grid(row=1, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        rows_spinbox.bind("<Return>", lambda e: self.generate_preview())
        rows_spinbox.bind("<<Increment>>", lambda e: self.generate_preview())
        rows_spinbox.bind("<<Decrement>>", lambda e: self.generate_preview())

        ttk.Label(pattern_frame, text="Columns:").grid(row=2, column=0, sticky=tk.W, pady=row_padding)
        self.cols_var = tk.IntVar(value=self.columns)
        cols_spinbox = ttk.Spinbox(pattern_frame, from_=1, to=50, textvariable=self.cols_var, width=8)
        cols_spinbox.grid(row=2, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        cols_spinbox.bind("<Return>", lambda e: self.generate_preview())
        cols_spinbox.bind("<<Increment>>", lambda e: self.generate_preview())
        cols_spinbox.bind("<<Decrement>>", lambda e: self.generate_preview())

        # Square size and radius rate
        ttk.Label(pattern_frame, text="Square Size:").grid(row=3, column=0, sticky=tk.W, pady=row_padding)
        self.square_size_var = tk.DoubleVar(value=self.square_size)
        square_size_entry = ttk.Entry(pattern_frame, textvariable=self.square_size_var, width=10)
        square_size_entry.grid(row=3, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        square_size_entry.bind("<Return>", lambda e: self.generate_preview())
        square_size_entry.bind("<FocusOut>", lambda e: self.generate_preview())

        ttk.Label(pattern_frame, text="Radius Rate:").grid(row=4, column=0, sticky=tk.W, pady=row_padding)
        self.radius_rate_var = tk.DoubleVar(value=self.radius_rate)
        radius_rate_entry = ttk.Entry(pattern_frame, textvariable=self.radius_rate_var, width=10)
        radius_rate_entry.grid(row=4, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        radius_rate_entry.bind("<Return>", lambda e: self.generate_preview())
        radius_rate_entry.bind("<FocusOut>", lambda e: self.generate_preview())

        # ArUco marker settings in a separate subframe with a separator
        ttk.Separator(pattern_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky=tk.E+tk.W, pady=10)
        
        aruco_label = ttk.Label(pattern_frame, text="ArUco Settings", font=('Segoe UI', 9, 'bold'))
        aruco_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(5, 10))

        ttk.Label(pattern_frame, text="Marker Size:").grid(row=7, column=0, sticky=tk.W, pady=row_padding)
        self.marker_size_var = tk.DoubleVar(value=self.aruco_marker_size)
        marker_size_entry = ttk.Entry(pattern_frame, textvariable=self.marker_size_var, width=10)
        marker_size_entry.grid(row=7, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        marker_size_entry.bind("<Return>", lambda e: self.generate_preview())
        marker_size_entry.bind("<FocusOut>", lambda e: self.generate_preview())

        # Dictionary file with improved layout
        ttk.Label(pattern_frame, text="Dictionary File:").grid(row=8, column=0, sticky=tk.W, pady=row_padding)
        
        dict_file_frame = ttk.Frame(pattern_frame)
        dict_file_frame.grid(row=8, column=1, sticky=tk.W+tk.E, pady=row_padding, padx=(5, 0))
        
        self.dict_file_var = tk.StringVar(value=self.dict_file)
        dict_file_entry = ttk.Entry(dict_file_frame, textvariable=self.dict_file_var, width=15)
        dict_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        dict_file_button = ttk.Button(dict_file_frame, text="Browse",
                                      command=self.browse_dict_file, width=8)
        dict_file_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Page settings frame with improved styling
        page_frame = ttk.LabelFrame(self.left_frame, text="Page Settings", padding=15)
        page_frame.pack(fill=tk.X, pady=10, ipady=5)

        # Page size selection
        ttk.Label(page_frame, text="Page Size:").grid(row=0, column=0, sticky=tk.W, pady=row_padding)
        self.page_size_var = tk.StringVar(value=self.page_size)
        page_size_combo = ttk.Combobox(page_frame, textvariable=self.page_size_var,
                                      values=["A0", "A1", "A2", "A3", "A4", "A5", "Custom"],
                                      state="readonly", width=10)
        page_size_combo.grid(row=0, column=1, sticky=tk.W+tk.E, pady=row_padding, padx=(5, 0))
        page_size_combo.bind("<<ComboboxSelected>>", self.update_page_size)

        # Custom page dimensions with better spacing
        ttk.Label(page_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=row_padding)
        self.page_width_var = tk.DoubleVar(value=self.page_width)
        self.page_width_entry = ttk.Entry(page_frame, textvariable=self.page_width_var, width=10)
        self.page_width_entry.grid(row=1, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        self.page_width_entry.bind("<Return>", lambda e: self.generate_preview())
        self.page_width_entry.bind("<FocusOut>", lambda e: self.generate_preview())

        ttk.Label(page_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=row_padding)
        self.page_height_var = tk.DoubleVar(value=self.page_height)
        self.page_height_entry = ttk.Entry(page_frame, textvariable=self.page_height_var, width=10)
        self.page_height_entry.grid(row=2, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        self.page_height_entry.bind("<Return>", lambda e: self.generate_preview())
        self.page_height_entry.bind("<FocusOut>", lambda e: self.generate_preview())

        # Units selection
        ttk.Label(page_frame, text="Units:").grid(row=3, column=0, sticky=tk.W, pady=row_padding)
        self.units_var = tk.StringVar(value=self.units)
        units_combo = ttk.Combobox(page_frame, textvariable=self.units_var,
                                  values=["mm", "px"],
                                  state="readonly", width=10)
        units_combo.grid(row=3, column=1, sticky=tk.W, pady=row_padding, padx=(5, 0))
        units_combo.bind("<<ComboboxSelected>>", lambda e: self.generate_preview())

    def create_preview_canvas(self):
        preview_frame = ttk.LabelFrame(self.right_frame, text="Pattern Preview", padding=15)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas frame with border to make it stand out
        canvas_frame = ttk.Frame(preview_frame, style="Canvas.TFrame")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure canvas frame style with border
        style = ttk.Style()
        style.configure("Canvas.TFrame", background=self.colors["border"])
        
        # Inner frame for the canvas with padding to create a border effect
        inner_frame = ttk.Frame(canvas_frame, padding=2)
        inner_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(inner_frame, bg=self.colors["canvas_bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img = None  # Reference to avoid garbage collection

        # Add status text below the canvas
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(preview_frame, textvariable=self.status_var, 
                                font=('Segoe UI', 8), foreground="#666666")
        status_label.pack(side=tk.RIGHT, pady=(5, 0))

    def create_buttons(self):
        button_frame = ttk.Frame(self.left_frame, padding=(0, 15, 0, 0))
        button_frame.pack(fill=tk.X)

        generate_button = ttk.Button(button_frame, text="Update Preview",
                                    command=self.generate_preview, style="Accent.TButton")
        generate_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        save_button = ttk.Button(button_frame, text="Save SVG",
                                command=self.save_pattern, style="Accent.TButton")
        save_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        exit_button = ttk.Button(button_frame, text="Exit",
                                command=self.exit_program, style="Exit.TButton")
        exit_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def update_page_size(self, event=None):
        selected = self.page_size_var.get()
        if selected != "Custom":
            self.page_width_var.set(self.page_sizes[selected][0])
            self.page_height_var.set(self.page_sizes[selected][1])
            self.generate_preview()

    def browse_dict_file(self):
        filename = filedialog.askopenfilename(
            title="Select ArUco Dictionary File",
            filetypes=[("JSON files", "*.json"), ("Compressed JSON", "*.json.gz"), ("All files", "*.*")]
        )
        if filename:
            self.dict_file_var.set(filename)
            self.generate_preview()

    def exit_program(self):
        self.root.destroy()

    def generate_preview(self):
        try:
            self.status_var.set("Generating preview...")
            self.root.update_idletasks()
            
            # Get values from UI
            pattern_type = self.type_var.get()
            columns = self.cols_var.get()
            rows = self.rows_var.get()
            square_size = self.square_size_var.get()
            radius_rate = self.radius_rate_var.get()
            page_width = self.page_width_var.get()
            page_height = self.page_height_var.get()
            units = self.units_var.get()
            aruco_marker_size = self.marker_size_var.get()
            dict_file = self.dict_file_var.get()

            # Create pattern maker instance
            pm = PatternMaker(
                cols=columns,
                rows=rows,
                output=self.output_file,
                units=units,
                square_size=square_size,
                radius_rate=radius_rate,
                page_width=page_width,
                page_height=page_height,
                markers=self.markers,
                aruco_marker_size=aruco_marker_size,
                dict_file=dict_file
            )

            # Generate the pattern
            pattern_methods = {
                "circles": pm.make_circles_pattern,
                "acircles": pm.make_acircles_pattern,
                "checkerboard": pm.make_checkerboard_pattern,
                "radon_checkerboard": pm.make_radon_checkerboard_pattern
            }

            if pattern_type == "charuco_board":
                pm.make_charuco_board()
            else:
                pattern_methods[pattern_type]()

            # Get SVG string
            svg_str = pm.get_svg_string()

            # Convert SVG to PNG in memory using cairosvg
            png_data = cairosvg.svg2png(bytestring=svg_str.encode('utf-8'))

            # Clear canvas
            self.canvas.delete("all")

            # Load image from PNG data
            image = Image.open(io.BytesIO(png_data))

            # Get canvas size
            self.canvas.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                image_ratio = image.width / image.height
                canvas_ratio = canvas_width / canvas_height

                if image_ratio > canvas_ratio:
                    new_width = canvas_width
                    new_height = int(canvas_width / image_ratio)
                else:
                    new_height = canvas_height
                    new_width = int(canvas_height * image_ratio)

                image = image.resize((new_width, new_height), Image.LANCZOS)

            # Convert PIL image to Tkinter PhotoImage
            self.img = ImageTk.PhotoImage(image)

            # Display image in canvas
            self.canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.img,
                anchor=tk.CENTER
            )
            
            # Update status
            self.status_var.set(f"Preview of {pattern_type} pattern ({columns}×{rows})")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate preview: {str(e)}")

    def save_pattern(self):
        try:
            # Show file save dialog
            filename = filedialog.asksaveasfilename(
                title="Save Pattern",
                defaultextension=".svg",
                filetypes=[("SVG files", "*.svg")]
            )

            if not filename:
                return

            # Generate and save pattern
            self.output_file = filename

            # Get values from UI
            pattern_type = self.type_var.get()
            columns = self.cols_var.get()
            rows = self.rows_var.get()
            square_size = self.square_size_var.get()
            radius_rate = self.radius_rate_var.get()
            page_width = self.page_width_var.get()
            page_height = self.page_height_var.get()
            units = self.units_var.get()
            aruco_marker_size = self.marker_size_var.get()
            dict_file = self.dict_file_var.get()

            # Create pattern maker instance
            pm = PatternMaker(
                cols=columns,
                rows=rows,
                output=filename,
                units=units,
                square_size=square_size,
                radius_rate=radius_rate,
                page_width=page_width,
                page_height=page_height,
                markers=self.markers,
                aruco_marker_size=aruco_marker_size,
                dict_file=dict_file
            )

            # Generate the pattern
            pattern_methods = {
                "circles": pm.make_circles_pattern,
                "acircles": pm.make_acircles_pattern,
                "checkerboard": pm.make_checkerboard_pattern,
                "radon_checkerboard": pm.make_radon_checkerboard_pattern
            }

            if pattern_type == "charuco_board":
                pm.make_charuco_board()
            else:
                pattern_methods[pattern_type]()

            # Save the pattern
            pm.save()

            self.status_var.set(f"Saved: {filename}")
            messagebox.showinfo("Success", f"Pattern saved to {filename}")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to save pattern: {str(e)}")


def main():
    # Check if command-line arguments are provided
    if len(sys.argv) > 1:
        # Parse command line options
        parser = argparse.ArgumentParser(description="generate camera-calibration pattern")
        parser.add_argument("-o", "--output", help="output file", default="out.svg", action="store", dest="output")
        parser.add_argument("-c", "--columns", help="pattern columns", default="8", action="store", dest="columns", type=int)
        parser.add_argument("-r", "--rows", help="pattern rows", default="11", action="store", dest="rows", type=int)
        parser.add_argument("-T", "--type", help="type of pattern", default="circles", action="store", dest="p_type",
                            choices=["circles", "acircles", "checkerboard", "radon_checkerboard"])
        parser.add_argument("-u", "--units", help="length unit", default="mm", action="store", dest="units",
                            choices=["mm", "px"])
        parser.add_argument("-s", "--square_size", help="size of squares in pattern", default="20.0", action="store",
                            dest="square_size", type=float)
        parser.add_argument("-R", "--radius_rate", help="circles_radius = square_size/radius_rate", default="5.0",
                            action="store", dest="radius_rate", type=float)
        parser.add_argument("-w", "--page_width", help="page width in units", default=argparse.SUPPRESS, action="store",
                            dest="page_width", type=float)
        parser.add_argument("-H", "--page_height", help="page height in units", default=argparse.SUPPRESS, action="store",
                            dest="page_height", type=float)
        parser.add_argument("-a", "--aruco_marker_size", help="aruco marker size", default="10.0", action="store",
                            dest="aruco_marker_size", type=float)
        parser.add_argument("-d", "--dict_file", help="aruco dictionary file", default="DICT_ARUCO_ORIGINAL.json",
                            action="store", dest="dict_file")
        parser.add_argument("-m", "--markers", help="list of markers as 'x,y;x,y;...'", default=None,
                            action="store", dest="markers")

        args = parser.parse_args()

        # Process markers if provided
        markers = None
        if args.markers:
            markers = []
            for marker in args.markers.split(';'):
                x, y = marker.split(',')
                markers.append((int(x), int(y)))

        # Set default page size if not specified
        if not hasattr(args, 'page_width') or not hasattr(args, 'page_height'):
            # Default to A4 in mm
            if args.units == "mm":
                args.page_width = 210 if not hasattr(args, 'page_width') else args.page_width
                args.page_height = 297 if not hasattr(args, 'page_height') else args.page_height
            elif args.units == "in":
                args.page_width = 8.27 if not hasattr(args, 'page_width') else args.page_width
                args.page_height = 11.7 if not hasattr(args, 'page_height') else args.page_height
            else:
                args.page_width = 595 if not hasattr(args, 'page_width') else args.page_width
                args.page_height = 842 if not hasattr(args, 'page_height') else args.page_height

        # Create pattern maker
        pm = PatternMaker(
            cols=args.columns,
            rows=args.rows,
            output=args.output,
            units=args.units,
            square_size=args.square_size,
            radius_rate=args.radius_rate,
            page_width=args.page_width,
            page_height=args.page_height,
            markers=markers,
            aruco_marker_size=args.aruco_marker_size,
            dict_file=args.dict_file
        )

        # Generate pattern based on type
        if args.p_type == "circles":
            pm.make_circles_pattern()
        elif args.p_type == "acircles":
            pm.make_acircles_pattern()
        elif args.p_type == "checkerboard":
            pm.make_checkerboard_pattern()
        elif args.p_type == "radon_checkerboard":
            pm.make_radon_checkerboard_pattern()

        # Save the pattern
        pm.save()

        print(f"Pattern saved to {args.output}")
    else:
        # Launch GUI
        root = tk.Tk()
        app = PatternMakerGUI(root)
        root.protocol("WM_DELETE_WINDOW", app.exit_program)
        root.mainloop()


if __name__ == "__main__":
    import sys
    main()

