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
        # Get the specified frame from the GIF image
        try:
            gif_img = Image.open(os.path.expanduser(image_path))
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

    def invoke(self, context: InvocationContext) -> ImageOutput:
        image_out = self.gif_image_frame(self.image_path, self.frame_index, self.scale, self.width, self.height, self.crop)
        image_dto = context.images.save(image=image_out)
        return ImageOutput.build(image_dto)
