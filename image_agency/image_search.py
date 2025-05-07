import traceback
import time
import random
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException

from config import MIN_DDGS_IMAGE_DIMENSION

class ImageSearch:
    """Handles image search functionality using DDGS"""
    
    def search_images(self, query: str, num_to_fetch: int = 10, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Search for images using DDGS with retry logic.
        
        Args:
            query: Search query string
            num_to_fetch: Maximum number of images to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of image candidate objects with pre-filtering applied
        """
        print(f"Searching DDGS for '{query}' (fetching ~{num_to_fetch})...")
        raw_results = []
        
        # Try with backoff for rate limiting
        for attempt in range(max_retries + 1):
            if attempt > 0:
                # Exponential backoff with jitter
                backoff_time = min(30, 2 ** attempt) + random.uniform(0, 2)
                print(f"Rate limit encountered. Retry attempt {attempt}/{max_retries} after {backoff_time:.2f}s delay...")
                time.sleep(backoff_time)
                
                # Slightly modify query on retries to avoid identical requests
                retry_query = f"{query} {'' if attempt % 2 == 0 else 'photos'}"
                print(f"Using modified query: '{retry_query}'")
            else:
                retry_query = query
            
            try:
                with DDGS() as ddgs:
                    # Add a small delay to prevent immediate rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    ddgs_gen = ddgs.images(
                        keywords=retry_query, 
                        region='wt-wt', 
                        safesearch='moderate', 
                        size=None, 
                        max_results=num_to_fetch + 5
                    )
                    
                    if not ddgs_gen: 
                        print("DDGS returned no generator.")
                        continue  # Try again with modified query
                        
                    result_count = 0
                    for r in ddgs_gen:
                        # Add intentional small random delays between result processing
                        if result_count > 0 and result_count % 5 == 0:
                            time.sleep(random.uniform(0.1, 0.3))
                            
                        if r and r.get('image'): 
                            raw_results.append(r)
                            result_count += 1
                            
                        if len(raw_results) >= num_to_fetch: 
                            break  # Stop if we have enough
                    
                    if raw_results:  # If we got any results, break the retry loop
                        print(f"DDGS returned {len(raw_results)} raw results on attempt {attempt+1}.")
                        break
                        
            except RatelimitException as e:
                print(f"Rate limit error on attempt {attempt+1}: {e}")
                if attempt >= max_retries:
                    print("Max retries exceeded for rate limit. Trying fallback search method...")
                    fallback_results = self._search_images_fallback(query, num_to_fetch)
                    if fallback_results:
                        raw_results = fallback_results
                        break
                    print("Fallback search also failed. Giving up.")
                # Continue to next retry attempt if not max retries yet
                    
            except Exception as e:
                print(f"ERROR in DDGS search attempt {attempt+1}: {e}\n{traceback.format_exc()}")
                if attempt >= max_retries:
                    print("Trying fallback search method...")
                    fallback_results = self._search_images_fallback(query, num_to_fetch)
                    if fallback_results:
                        raw_results = fallback_results
                        break
        
        # If no results after all retries, return empty list
        if not raw_results:
            print(f"No suitable image candidates found for '{query}' after {max_retries+1} attempts.")
            return []

        # Apply minimal heuristic pre-filter for dimensions
        pre_filtered_candidates = []
        for r in raw_results:
            width = r.get('width', 0)
            height = r.get('height', 0)
            
            if isinstance(width, int) and isinstance(height, int) and \
               width >= MIN_DDGS_IMAGE_DIMENSION and height >= MIN_DDGS_IMAGE_DIMENSION:
                pre_filtered_candidates.append({
                    'url': r.get('image'),
                    'title': r.get('title', ''),
                    'thumbnailUrl': r.get('thumbnail', ''),  # Though not used, keep for structure
                    'width': width,
                    'height': height
                })
            else:
                print(f"DDGS pre-filter: Discarding candidate due to small/missing dimensions: {r.get('title', 'No Title')[:50]}")
        
        print(f"{len(pre_filtered_candidates)} candidates after minimal pre-filtering.")
        return pre_filtered_candidates
    
    def _search_images_fallback(self, query: str, num_to_fetch: int = 20) -> List[Dict[str, Any]]:
        """Alternative search method when main DDGS image search fails.
        This method attempts to find image URLs from text search results.
        
        Args:
            query: Search query string
            num_to_fetch: Maximum number of results to fetch
            
        Returns:
            List of image candidates in same format as the main search method
        """
        print(f"Using fallback text search for '{query}' + 'images'...")
        raw_results = []
        
        image_query = f"{query} images high resolution photos"
        
        try:
            with DDGS() as ddgs:
                # Use text search instead of image search
                time.sleep(random.uniform(1.0, 2.0))  # Slightly longer delay for fallback
                
                text_results = ddgs.text(
                    keywords=image_query,
                    region='wt-wt',
                    safesearch='moderate',
                    max_results=num_to_fetch * 2  # Get more text results to find images
                )
                
                result_count = 0
                for result in text_results:
                    # Extract potential image sites from domains
                    if not result or not result.get('href'):
                        continue
                        
                    domain = result.get('href', '').lower()
                    # Only include results from likely image sources
                    if any(img_site in domain for img_site in [
                        'flickr.com', 'imgur.com', 'unsplash.com', 'pexels.com', 
                        'pixabay.com', 'images', 'photos', 'pics', '.jpg', '.png'
                    ]):
                        # Create a mock image result with estimated dimensions
                        # These will be verified later during validation
                        raw_results.append({
                            'image': result.get('href'),
                            'title': result.get('title', ''),
                            'width': 800,  # Placeholder
                            'height': 600,  # Placeholder
                            'thumbnail': '',
                            'is_fallback': True  # Mark as coming from fallback
                        })
                        result_count += 1
                        
                    # Add occasional small delay
                    if result_count % 3 == 0:
                        time.sleep(random.uniform(0.1, 0.2))
                        
                    if len(raw_results) >= num_to_fetch:
                        break
                        
                print(f"Fallback search found {len(raw_results)} potential image candidates.")
                        
        except Exception as e:
            print(f"ERROR in fallback search: {e}\n{traceback.format_exc()}")
            
        return raw_results