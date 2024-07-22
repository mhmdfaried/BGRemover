import cv2
import numpy as np
from tkinter import Tk, Label, Button, filedialog, Frame, LEFT, BOTH, X
from PIL import Image, ImageTk
from rembg import remove

original_image = None
processed_image = None
background_mask = None
current_display_image = None


def remove_background(image):
    global processed_image, background_mask

    # Convert the image to RGB mode
    pil_image = Image.fromarray(image)
    # Use rembg to remove the background
    output_image = remove(pil_image)
    rembg_image = np.array(output_image)

    # Convert the image to BGR for OpenCV processing
    rembg_image_bgr = cv2.cvtColor(rembg_image, cv2.COLOR_RGBA2BGR)
    # Apply GrabCut to refine the mask
    refined_image, background_mask = refine_with_grabcut(image, rembg_image_bgr)
    processed_image = refined_image


def refine_with_grabcut(original_image, rembg_image_bgr):
    mask = np.zeros(original_image.shape[:2], np.uint8)

    # Create the initial mask from rembg output
    initial_mask = cv2.cvtColor(rembg_image_bgr, cv2.COLOR_BGR2GRAY)
    mask[initial_mask > 0] = cv2.GC_PR_FGD
    mask[initial_mask == 0] = cv2.GC_BGD

    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (1, 1, original_image.shape[1] - 2, original_image.shape[0] - 2)

    # Apply GrabCut with the initial mask
    cv2.grabCut(original_image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    # Apply Gaussian blur to smooth edges
    blurred_mask = cv2.GaussianBlur(mask2, (7, 7), 0)
    _, smooth_mask = cv2.threshold(blurred_mask, 127, 255, cv2.THRESH_BINARY)

    # Apply morphological operations to clean up the mask
    kernel = np.ones((7, 7), np.uint8)
    smooth_mask = cv2.erode(smooth_mask, kernel, iterations=1)
    smooth_mask = cv2.dilate(smooth_mask, kernel, iterations=2)

    # Edge Detection
    edges = cv2.Canny(smooth_mask, 50, 150)
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Find and filter contours to remove small noise
    contours, _ = cv2.findContours(smooth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered_mask = np.zeros_like(smooth_mask)
    for contour in contours:
        if cv2.contourArea(contour) > 500:  # Adjust the area threshold as needed
            cv2.drawContours(filtered_mask, [contour], -1, 255, thickness=cv2.FILLED)

    # Combine edges with filtered mask
    refined_mask = np.maximum(filtered_mask, edges)

    # Refine with additional iterations
    cv2.grabCut(original_image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)
    final_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    # Apply the final mask to the original image
    refined_image = cv2.bitwise_and(original_image, original_image, mask=final_mask)
    return refined_image, final_mask


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
        new_image = np.zeros_like(original_image)
        mask = (background_mask == 1)
        new_image[mask] = processed_image[mask]
        new_image[~mask] = background_color
        current_display_image = new_image
        display_image(new_image, f"Processed Image - {color.capitalize()} Background")
        save_button.config(state="normal")
        save_processed_button.config(state="disabled")


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

    # Enable buttons after loading an image
    original_button.config(state="normal")
    process_button.config(state="normal")
    button_red.config(state="normal")
    button_blue.config(state="normal")
    button_white.config(state="normal")


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
        save_button.config(state="disabled")
        save_processed_button.config(state="disabled")


def process_image():
    global original_image, processed_image
    if original_image is None:
        return

    remove_background(original_image)
    display_image(processed_image, "Processed Image")
    save_processed_button.config(state="normal")
    save_button.config(state="disabled")


root = Tk()
root.title("BG Remover")
root.geometry("800x600")
root.configure(bg="#f0f0f0")

# Create a frame for the buttons
button_frame = Frame(root, bg="#d9d9d9")
button_frame.pack(fill=X, pady=10)

load_button = Button(button_frame, text="Load Image", command=load_image, width=15, bg="#007BFF", fg="white")
load_button.pack(side=LEFT, padx=5, pady=5)

original_button = Button(button_frame, text="Original", command=display_original_image, width=15, bg="#28A745",
                         fg="white", state="disabled")
original_button.pack(side=LEFT, padx=5, pady=5)

process_button = Button(button_frame, text="Process Image", command=process_image, width=15, bg="#FFC107", fg="black",
                        state="disabled")
process_button.pack(side=LEFT, padx=5, pady=5)

color_label = Label(button_frame, text="Change Background Color:", bg="#d9d9d9")
color_label.pack(side=LEFT, padx=10, pady=5)

button_red = Button(button_frame, text="Red", command=lambda: change_background_color("red"), width=10, bg="#DC3545",
                    fg="white", state="disabled")
button_red.pack(side=LEFT, padx=5, pady=5)

button_blue = Button(button_frame, text="Blue", command=lambda: change_background_color("blue"), width=10, bg="#007BFF",
                     fg="white", state="disabled")
button_blue.pack(side=LEFT, padx=5, pady=5)

button_white = Button(button_frame, text="White", command=lambda: change_background_color("white"), width=10,
                      bg="#f8f9fa", fg="black", state="disabled")
button_white.pack(side=LEFT, padx=5, pady=5)

save_button = Button(button_frame, text="Save Image with Color", command=save_image, width=20, bg="#17A2B8", fg="white",
                     state="disabled")
save_button.pack(side=LEFT, padx=5, pady=5)

save_processed_button = Button(button_frame, text="Save Image without Color", command=save_processed_image, width=20,
                               bg="#17A2B8", fg="white", state="disabled")
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
