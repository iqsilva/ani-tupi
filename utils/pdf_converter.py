"""PDF converter for manga chapters.

Converts directories of images (PNG, JPG, JPEG, WebP) into multi-page PDF files
with optional compression for efficient storage.
"""

from pathlib import Path

from PIL import Image


def create_pdf_from_images(
    image_dir: Path,
    output_pdf: Path,
    quality: int = 85,
) -> Path:
    """Convert directory of images to single PDF.

    Supports PNG, JPG, JPEG, and WebP image formats.
    Processes images in sorted order, maintains reading sequence,
    and applies JPEG compression within the PDF for file size optimization.

    Args:
        image_dir: Directory containing images (in reading order)
        output_pdf: Output PDF file path
        quality: JPEG quality for compression (0-100, default 85)

    Returns:
        Path to created PDF file

    Raises:
        ValueError: If no images found in directory
        Exception: If image processing or PDF creation fails
    """
    # List and sort images by filename (ensures correct reading order)
    # Support multiple image formats: png, jpg, jpeg, webp
    images = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        images.extend(image_dir.glob(ext))

    # Sort by filename
    images = sorted(images)

    if not images:
        msg = f"No images found in {image_dir}"
        raise ValueError(msg)

    # Open first image (cover) and convert to RGB
    first_image = Image.open(images[0]).convert("RGB")

    # Open remaining images and convert to RGB
    other_images = [Image.open(img).convert("RGB") for img in images[1:]]

    # Save as multi-page PDF with compression
    first_image.save(
        output_pdf,
        "PDF",
        save_all=True,
        append_images=other_images,
        quality=quality,
        optimize=True,
    )

    return output_pdf
