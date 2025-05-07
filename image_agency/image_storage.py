import os
import time
import hashlib
import re
import requests
import traceback
from typing import Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

class ImageStorage:
    """Handles image downloading and storage operations"""
    
    def __init__(self):
        """Initialize the image storage service with Supabase connection"""
        load_dotenv()
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
            
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.supabase_project_url = SUPABASE_URL
        
    def download_image(self, url: str, max_retries: int = 1) -> Optional[bytes]:
        """Download image data from a URL.
        
        Args:
            url: The image URL to download
            max_retries: Maximum number of retry attempts
            
        Returns:
            Image bytes if download is successful, None otherwise
        """
        print(f"Downloading image from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for attempt in range(max_retries + 1):
            try:
                verify_ssl = True if attempt == 0 else False  # Try verify=False on retry
                response = requests.get(
                    url, 
                    allow_redirects=True, 
                    timeout=15, 
                    headers=headers, 
                    stream=True, 
                    verify=verify_ssl
                )
                response.raise_for_status()
                image_data = response.content
                
                if len(image_data) < 500:
                    print(f"WARNING: Downloaded data small ({len(image_data)} bytes) from {url}.")
                    
                print(f"SUCCESS: Downloaded {len(image_data)} bytes from {url}" + 
                      (" (verify=False)" if not verify_ssl else ""))
                return image_data
                
            except requests.exceptions.RequestException as e_req:  # Catches SSLError, ConnectionError, Timeout, HTTPError
                print(f"REQUEST ERROR (attempt {attempt+1}) downloading {url}: {e_req}.")
                if attempt >= max_retries:
                    print(f"Max retries for {url}.")
                    return None
                time.sleep(1)  # Simple 1s wait
                
            except Exception as e_gen:  # Catch-all for unexpected errors
                print(f"UNEXPECTED ERROR (attempt {attempt+1}) downloading {url}: {e_gen}.")
                if attempt >= max_retries:
                    print(f"Max retries for {url}.")
                    return None
                time.sleep(1)
                
        return None
        
    def upload_to_supabase(self, image_bytes: bytes, destination_path: str) -> Optional[str]:
        """Upload image bytes to Supabase storage.
        
        Args:
            image_bytes: The image data to upload
            destination_path: The destination path in the storage bucket
            
        Returns:
            Public URL of the uploaded image, or None if upload fails
        """
        bucket_name = 'images'
        content_type = "image/jpeg"
        print(f"Uploading {len(image_bytes)} bytes to Supabase: {bucket_name}/{destination_path}")
        
        try:
            self.supabase.storage.from_(bucket_name).upload(
                path=destination_path, 
                file=image_bytes, 
                file_options={"contentType": content_type, "cacheControl": "3600", "upsert": "true"}
            )
            
            if not self.supabase_project_url:
                print("ERROR: SUPABASE_URL missing.")
                return None
                
            public_url = f"{self.supabase_project_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{destination_path}"
            print(f"SUCCESS: Uploaded to Supabase. URL: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"ERROR: Supabase upload failed: {e}\n{traceback.format_exc()}")
            return None
            
    def save_image_info(self, cluster_id: str, image_url: str, original_url: str, view: str) -> bool:
        """Save image information to the cluster_images table.
        
        Args:
            cluster_id: The ID of the cluster the image belongs to
            image_url: The URL of the stored image in Supabase
            original_url: The original URL the image was downloaded from
            view: The view/perspective (e.g., "coach", "team", "player", etc.)
            
        Returns:
            True if the save was successful, False otherwise
        """
        print(f"Saving image info to cluster_images table: cluster_id={cluster_id}, view={view}")
        
        try:
            data = {
                "cluster_id": cluster_id,
                "image_url": image_url,
                "original_url": original_url,
                "view": view
            }
            
            response = self.supabase.table("cluster_images").insert(data).execute()
            
            if response.data:
                print(f"Successfully saved image info to cluster_images table for cluster {cluster_id}, view {view}")
                return True
            else:
                print(f"Failed to save image info to cluster_images. Response: {response}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to save image info to cluster_images table: {e}\n{traceback.format_exc()}")
            return False
            
    def process_and_upload_image(self, image_data: Dict[str, Any], query_for_filename: str) -> Optional[str]:
        """Download an image and upload it to Supabase storage.
        
        Args:
            image_data: Dictionary containing image URL and metadata
            query_for_filename: Search query to use in the filename
            
        Returns:
            Public URL of the uploaded image, or None if processing fails
        """
        image_url = image_data.get("url")
        if not image_url:
            print("No URL in selected image data.")
            return None
        
        print(f"Processing image for upload: {image_url}")
        image_bytes = self.download_image(image_url)
        if not image_bytes:
            return None
        
        safe_query_part = re.sub(r'\W+', '_', query_for_filename.split()[0] if query_for_filename else "ai_img")[:20]
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        destination_path = f"public/{safe_query_part}_{url_hash}.jpg"
        
        return self.upload_to_supabase(image_bytes, destination_path)