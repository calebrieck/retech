import base64
import os
from uuid import uuid4

from api.supabase.supabase_client import get_supabase

SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "tickets")
SIGNED_URL_TTL_SECONDS = os.getenv("SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS")

def upload_image(file_data: bytes, filename: str, content_type: str, ticket_id: str) -> dict:
    """
    Upload image to Supabase Storage and return both URL and base64
    
    Args:
        file_data: Raw bytes of the image
        filename: Original filename
        content_type: MIME type (e.g., 'image/jpeg')
        ticket_id: Ticket ID for organizing images
        
    Returns:
        Dict with 'url' (signed URL) and 'base64' (for AI analysis)
    """
    try:
        extension = filename.split('.')[-1] if '.' in filename else 'jpg'
        object_path = f"tickets/{ticket_id}/{uuid4()}.{extension}"

        print(f"Uploading image to: {object_path}")

        sb = get_supabase()
        bucket = sb.storage.from_(SUPABASE_STORAGE_BUCKET)
        bucket.upload(
            object_path,
            file_data,
            file_options={"content-type": content_type, "upsert": False},
        )

        print(f"Image uploaded successfully: {object_path}")

        signed_url = None
        if SIGNED_URL_TTL_SECONDS:
            signed = bucket.create_signed_url(object_path, int(SIGNED_URL_TTL_SECONDS))
            signed_url = signed.get("signedURL") or signed.get("signedUrl")

        public_response = bucket.get_public_url(object_path)
        public_url = (
            public_response.get("publicUrl")
            if isinstance(public_response, dict)
            else public_response
        )
        final_url = signed_url or public_url
        
        # Also encode as base64 for direct AI input
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        return {
            'url': final_url,
            'base64': base64_data,
            'content_type': content_type
        }
    except Exception as e:
        print(f"Error uploading image: {e}")
        import traceback
        print(traceback.format_exc())
        raise
