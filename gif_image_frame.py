"""
InvokeAI Node - GIF Image Frame
by Thinkyhead - Sept 11, 2024

nodes / gif-image-frame / gif_image_frame.py

Get a frame from a GIF image using the file path and frame index.
In future the Image
"""

import os, sys, subprocess, shutil, datetime, tempfile
from typing import Literal
from PIL import Image, ImageOps

from invokeai.invocation_api import (
    BaseInvocation,
    Input,
    InvocationContext,
    invocation,
    InputField,
    ImageField,
    ImageOutput,
)

@invocation(
    "GIF_Image_Frame",
    title="GIF Image Frame",
    tags=["image", "GIF", "format", "frame", "extract", "animation"],
    category="image",
    version="0.0.1",
    use_cache=False,
)

class GIFImageFrameInvocation(BaseInvocation):
    """GIF Image Input, selecting a frame"""
    image_path: str = InputField(description="Path to a GIF (or PNG) image file")
    frame_index: int = InputField(default=0, description="The frame index to import (0-based)")
    scale: float = InputField(default=1.0, description="Scale factor for the image (1.0 = 100%)")
    width: int = InputField(default=0, description="Image width (0 for original size)")
    height: int = InputField(default=0, description="Image height (0 for original size)")
    crop: bool = InputField(default=False, description="Crop to fit, otherwise pad with white")

    def gif_image_frame(self, image_path:str, frame_index:int, scale:float, width:int, height:int, crop:bool) -> Image.Image:
        CONVERTERS = Literal["pillow", "ffmpeg", "imagemagick", "imageio"]
        THE_CONVERTER: CONVERTERS = "pillow"
        USE_TEMP_FILES = False

        # Expand ~ if present
        input_path = os.path.expanduser(image_path)

        if THE_CONVERTER == "pillow":
            # Get the specified frame from the GIF image
            try:
                gif_img = Image.open(input_path)
            except Exception as e:
                raise ValueError(f"No GIF (or PNG) image found at {image_path}")

            # Check if the requested frame is within the range of the image
            frame_count = gif_img.n_frames
            if frame_index < 0 or frame_index >= frame_count:
                raise ValueError(f"Frame {frame_index} is out of range (0-{frame_count-1}) for image {image_path}")

            # Try to get the requested frame from the image
            try:
                gif_img.seek(frame_index)
                img = gif_img.copy()
            except Exception as e:
                raise ValueError(f"Failed to read frame {frame_index} from image {image_path}")

            # If width and height are given resize the image with PIL
            if width > 0 and height > 0:
                func = ImageOps.fit if crop else ImageOps.pad
                scaler = Image.LANCZOS if (width < img.size[0] or height < img.size[1]) else Image.BICUBIC
                img = func(img, (width, height), scaler)

            # If a scale other than 1 is given, resize using simple scaling
            elif scale != 1.0 and scale != 0.0:
                box_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(box_size, Image.LANCZOS if scale < 1.0 else Image.BICUBIC)

            return img

        # If a command is set it will be run it to generate an image
        command = None

        if USE_TEMP_FILES:
            # Consider using invoke's temp file support, if there is an API for that.
            # This will allow the image to removed when invoke is clearing caches.
            out_path = tempfile.mktemp(suffix=".png")
        else:
            # Create a new image name in the same folder as the input image
            file_path, filename = os.path.split(input_path)
            file_name, file_ext = os.path.splitext(filename)
            out_path = f"{file_path}/{file_name}--{frame_index}.png"

        extracted_frame_path = os.path.expanduser(out_path)

        if os.path.exists(extracted_frame_path):

            # If the file already exists, return it by default (for other methods)
            pass

        elif THE_CONVERTER == "ffmpeg":
            #
            # ffmpeg -i image_path
            #        -vsync vfr
            #        -q:v 2
            #        -vf "select='eq(n,frame_index)',scale=iw*scale:ih*scale"
            #        extracted_frame_path
            #

            filter = f"select='eq(n,{frame_index})'"
            if scale != 1.0: filter += f",scale=iw*{scale}:ih*{scale}"

            # ffmpeg command to generate an image at extracted_frame_path
            # TODO: Add fitting within the width and height (if not 0)
            command = [
                "ffmpeg",
                "-i", input_path,       # Input file path
                "-vf", filter,          # Frame index, optional scaling
                "-vsync", "vfr",        # Prevent frame drops (Variable Frame Rate) by duplicating / dropping frames as needed.
                "-q:v", "2",            # Output Quality 2 (good)
                extracted_frame_path    # Output file path
            ]

        elif THE_CONVERTER == "imagemagick":
            #
            # Use ImageMagick 'convert' to extract frame 'frame_index' from the GIF at 'image_path'
            #   convert image_path[frame_index] extracted_frame_path
            # To scale the frame before export, use:
            #   convert image_path[frame_index] -resize scale% extracted_frame_path
            #
            # TODO: Add fitting within the given box_size (if not 0,0)
            #
            command = [ "convert", input_path + f"[{frame_index}]" ]
            if scale != 1.0: command += [ "-resize", f"{scale*100}%" ]
            command += [ extracted_frame_path ]

        else:
            raise Exception("No image extraction method selected")

        if command:
            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"\nResult: {result}\n")
            return Image.open(extracted_frame_path)

    def invoke(self, context: InvocationContext) -> ImageOutput:
        image_out = self.gif_image_frame(self.image_path, self.frame_index, self.scale, self.width, self.height, self.crop)
        image_dto = context.images.save(image=image_out)
        return ImageOutput.build(image_dto)
