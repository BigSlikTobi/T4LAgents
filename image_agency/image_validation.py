import requests
from typing import List, Dict, Any, Optional
import traceback

from config import BLACKLISTED_DOMAINS

class ImageValidator:
    """Handles validation of image URLs"""
    
    def __init__(self):
        """Initialize the image validator with blacklist domains"""
        self.blacklisted_domains = BLACKLISTED_DOMAINS
        
    def validate_image_url(self, image_url: str) -> bool:
        """Validate if an image URL is accessible and not blacklisted.
        
        Args:
            image_url: The image URL to validate
            
        Returns:
            True if the URL is valid and accessible, False otherwise
        """
        print(f"Validating URL: {image_url}")
        
        # Basic validation
        if not image_url or not isinstance(image_url, str): 
            print("SKIPPING: Invalid URL.")
            return False
            
        # Check against blacklist
        if any(domain in image_url.lower() for domain in self.blacklisted_domains):
            print(f"SKIPPING: Blacklisted URL: {image_url}")
            return False
            
        # Check if accessible
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"}
            response = requests.head(image_url, allow_redirects=True, timeout=10, headers=headers, verify=True)
            
            if response.status_code != 200:
                print(f"SKIPPING: Status {response.status_code}: {image_url}")
                return False
                
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['image/', 'application/octet-stream']):
                if not any(image_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    print(f"SKIPPING: Invalid content type ({content_type}) and extension: {image_url}")
                    return False
                    
            print(f"SUCCESS: Validated URL: {image_url}")
            return True
            
        except requests.exceptions.SSLError:
            print(f"WARNING: SSL Error for {image_url}. Retrying with verify=False.")
            try:
                retry_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"}
                response_retry = requests.head(image_url, allow_redirects=True, timeout=10, headers=retry_headers, verify=False)
                
                if response_retry.status_code == 200: 
                    print(f"SUCCESS (verify=False): {image_url}")
                    return True
                    
                print(f"SKIPPING (verify=False): Status {response_retry.status_code}: {image_url}")
                return False
                
            except Exception as e_inner: 
                print(f"ERROR (verify=False) validating {image_url}: {e_inner}")
                return False
                
        except requests.exceptions.RequestException as e: 
            print(f"ERROR validating {image_url}: {e}")
            return False
            
        except Exception as e_gen: 
            print(f"UNEXPECTED VALIDATION ERROR for {image_url}: {e_gen}")
            return False
            
    def filter_valid_images(self, candidates: List[Dict[str, Any]], 
                           max_valid: int = 12) -> List[Dict[str, Any]]:
        """Filter a list of image candidates to only those with valid URLs.
        
        Args:
            candidates: List of image candidate objects
            max_valid: Maximum number of valid candidates to return
            
        Returns:
            List of image candidates with valid URLs, limited to max_valid
        """
        valid_candidates = []
        
        for candidate in candidates:
            url = candidate.get('url')
            if self.validate_image_url(url):
                valid_candidates.append(candidate)
                
            if len(valid_candidates) >= max_valid:
                break
                
        return valid_candidates