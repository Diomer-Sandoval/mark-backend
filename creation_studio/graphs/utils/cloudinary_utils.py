import os

import cloudinary
import cloudinary.uploader


def _config():
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    )


def upload_image(base64_data: str, folder: str, public_id: str) -> str:
    """Upload a base64 PNG to Cloudinary and return the secure_url."""
    _config()
    result = cloudinary.uploader.upload(
        f"data:image/png;base64,{base64_data}",
        folder=folder,
        public_id=public_id,
    )
    return result["secure_url"]


def upload_video(base64_data: str, folder: str, public_id: str) -> str:
    """Upload a base64 MP4 to Cloudinary and return the secure_url."""
    _config()
    result = cloudinary.uploader.upload(
        f"data:video/mp4;base64,{base64_data}",
        folder=folder,
        public_id=public_id,
        resource_type="video",
    )
    return result["secure_url"]
