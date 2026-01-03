import os
from uuid import uuid4
from firebase_admin import storage
from datetime import timedelta
import base64

def get_bucket():
    """Get the Firebase Storage bucket"""
    try:
        return storage.bucket()
    except Exception as e:
        print(f"Error getting storage bucket: {e}")
        raise

def upload_image(file_data: bytes, filename: str, content_type: str, ticket_id: str) -> dict:
    """
    Upload image to Firebase Storage and return both URL and base64
    
    Args:
        file_data: Raw bytes of the image
        filename: Original filename
        content_type: MIME type (e.g., 'image/jpeg')
        ticket_id: Ticket ID for organizing images
        
    Returns:
        Dict with 'url' (signed URL) and 'base64' (for AI analysis)
    """
    try:
        # Create a unique filename to avoid collisions
        extension = filename.split('.')[-1] if '.' in filename else 'jpg'
        blob_name = f"tickets/{ticket_id}/{uuid4()}.{extension}"
        
        print(f"Uploading image to: {blob_name}")
        
        # Get bucket
        bucket = get_bucket()
        
        # Upload to Firebase Storage
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_data, content_type=content_type)
        
        # Make blob publicly readable (temporary for AI to access)
        blob.make_public()
        
        print(f"Image uploaded successfully: {blob_name}")
        
        # Get public URL
        public_url = blob.public_url
        
        # Also encode as base64 for direct AI input
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        return {
            'url': public_url,
            'base64': base64_data,
            'content_type': content_type
        }
    except Exception as e:
        print(f"Error uploading image: {e}")
        import traceback
        print(traceback.format_exc())
        raise