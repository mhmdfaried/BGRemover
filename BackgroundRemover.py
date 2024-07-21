import cv2
import numpy as np
from tkinter import Tk, Label, Button, filedialog, Frame, LEFT, BOTH, X, TOP
from PIL import Image, ImageTk

original_image = None
processed_image = None
background_mask = None
current_display_image = None

def remove_background(image):
    global processed_image, background_mask

    mask = np.zeros(image.shape[:2], np.uint8)
    rect = (10, 10, image.shape[1] - 15, image.shape[0] - 10)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    background_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    # Apply morphological operations to clean up the mask
    kernel = np.ones((3, 3), np.uint8)
    background_mask = cv2.erode(background_mask, kernel, iterations=1)
    background_mask = cv2.dilate(background_mask, kernel, iterations=2)

    processed_image = image * background_mask[:, :, np.newaxis]

def change_background_color(color):
    global processed_image, background_mask, original_image, current_display_image

    if processed_image is None or background_mask is None:
        return

    color_options = {
        "red": (255, 0, 0),
        "blue": (0, 0, 255),
        "white": (255, 255, 255)
    }

    if color in color_options:
        background_color = color_options[color]
        new_image = original_image.copy()
        mask = (background_mask == 0)
        new_image[mask] = background_color
        current_display_image = new_image
        display_image(new_image, f"Processed Image - {color.capitalize()} Background")

def save_image():
    global current_display_image
    if current_display_image is None:
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
    if save_path:
        cv2.imwrite(save_path, cv2.cvtColor(current_display_image, cv2.COLOR_RGB2BGR))
        print(f"Image saved successfully as {save_path}")
        root.focus_set()

def save_processed_image():
    global processed_image, background_mask
    if processed_image is None or background_mask is None:
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
    if save_path:
        # Create an RGBA image with a transparent background
        rgba_image = cv2.cvtColor(processed_image, cv2.COLOR_RGB2RGBA)
        rgba_image[:, :, 3] = background_mask * 255
        Image.fromarray(rgba_image).save(save_path)
        print(f"Image saved successfully as {save_path}")
        root.focus_set()

def load_image():
    global original_image
    file_path = filedialog.askopenfilename()
    if not file_path:
        return
    # Load the image with Pillow and remove ICC profile
    pil_image = Image.open(file_path)
    if 'icc_profile' in pil_image.info:
        pil_image.info.pop('icc_profile')
    pil_image = pil_image.convert("RGB")
    original_image = np.array(pil_image)
    display_image(original_image, "Original Image")

def display_image(image, title):
    img = Image.fromarray(image)
    imgtk = ImageTk.PhotoImage(image=img)
    panel.configure(image=imgtk)
    panel.image = imgtk
    title_label.config(text=title)

def display_original_image():
    global original_image
    if original_image is not None:
        display_image(original_image, "Original Image")

def process_image():
    global original_image, processed_image
    if original_image is None:
        return

    remove_background(original_image)
    display_image(processed_image, "Processed Image")

root = Tk()
root.title("Background Removal and Image Saving")
root.geometry("800x600")
root.configure(bg="#f0f0f0")

# Create a frame for the buttons
button_frame = Frame(root, bg="#d9d9d9")
button_frame.pack(fill=X, pady=10)

load_button = Button(button_frame, text="Load Image", command=load_image, width=15, bg="#007BFF", fg="white")
load_button.pack(side=LEFT, padx=5, pady=5)

original_button = Button(button_frame, text="Original", command=display_original_image, width=15, bg="#28A745", fg="white")
original_button.pack(side=LEFT, padx=5, pady=5)

process_button = Button(button_frame, text="Process Image", command=process_image, width=15, bg="#FFC107", fg="black")
process_button.pack(side=LEFT, padx=5, pady=5)

color_label = Label(button_frame, text="Change Background Color:", bg="#d9d9d9")
color_label.pack(side=LEFT, padx=10, pady=5)

button_red = Button(button_frame, text="Red", command=lambda: change_background_color("red"), width=10, bg="#DC3545", fg="white")
button_red.pack(side=LEFT, padx=5, pady=5)

button_blue = Button(button_frame, text="Blue", command=lambda: change_background_color("blue"), width=10, bg="#007BFF", fg="white")
button_blue.pack(side=LEFT, padx=5, pady=5)

button_white = Button(button_frame, text="White", command=lambda: change_background_color("white"), width=10, bg="#f8f9fa", fg="black")
button_white.pack(side=LEFT, padx=5, pady=5)

save_button = Button(button_frame, text="Save Image with Color", command=save_image, width=20, bg="#17A2B8", fg="white")
save_button.pack(side=LEFT, padx=5, pady=5)

save_processed_button = Button(button_frame, text="Save Image without Color", command=save_processed_image, width=20, bg="#17A2B8", fg="white")
save_processed_button.pack(side=LEFT, padx=5, pady=5)

# Panel to display image
image_frame = Frame(root, bg="#ffffff")
image_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

panel = Label(image_frame, bg="#ffffff")
panel.pack(fill=BOTH, expand=True)

# Label for the title
title_label = Label(root, text="No Image Loaded", bg="#f0f0f0", font=("Arial", 16))
title_label.pack(pady=10)

root.mainloop()
