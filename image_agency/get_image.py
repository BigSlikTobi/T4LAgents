"""
Entry point for image search functionality.
This file provides backward compatibility by using the new modular architecture
while exposing the same interface as the original AISimplifiedImageSearcher.
"""
from typing import Optional
from image_agency.main_image_service import MainImageService
from image_agency.article_service import ArticleService
from image_agency.llm_service import LLMService
from image_agency.image_search import ImageSearch
from image_agency.image_validation import ImageValidator
from image_agency.image_storage import ImageStorage

class AISimplifiedImageSearcher:
    """Legacy wrapper class that uses the new modular architecture"""
    
    def __init__(self):
        """Initialize using the new MainImageService"""
        self.main_service = MainImageService()
        print("AISimplifiedImageSearcher initialized (using new architecture).")

    def process_article_and_upload_image(self, article_id: str) -> Optional[str]:
        """Process an article and find a suitable image.
        
        This method maintains backward compatibility with the original implementation,
        but delegates the work to the new modular architecture.
        
        Args:
            article_id: The ID of the article to process
            
        Returns:
            URL of uploaded image or None if any step fails
        """
        return self.main_service.process_article_and_upload_image(article_id)

# For backwards compatibility, maintain these methods with deprecation notices
    def _fetch_article_from_supabase(self, article_id: str) -> Optional[str]:
        """DEPRECATED - Use ArticleService directly"""
        print("Warning: _fetch_article_from_supabase is deprecated")
        return self.main_service.article_service.fetch_article_content(article_id)

    def _generate_search_query_with_llm(self, article_content: str) -> Optional[str]:
        """DEPRECATED - Use LLMService directly"""
        print("Warning: _generate_search_query_with_llm is deprecated")  
        return self.main_service.llm_service.generate_search_query(article_content)

    def _validate_image_url_sync(self, image_url: str) -> bool:
        """DEPRECATED - Use ImageValidator directly"""
        print("Warning: _validate_image_url_sync is deprecated")
        validator = ImageValidator()
        return validator.validate_image_url(image_url)

    def _search_ddgs_candidates_sync(self, query: str, num_to_fetch: int = 10) -> list:
        """DEPRECATED - Use ImageSearch directly"""
        print("Warning: _search_ddgs_candidates_sync is deprecated")
        searcher = ImageSearch()
        return searcher.search_images(query, num_to_fetch)

    def _select_best_image_with_llm(self, image_candidates: list, article_snippet: str, search_query: str):
        """DEPRECATED - Use LLMService directly"""
        print("Warning: _select_best_image_with_llm is deprecated")
        return self.main_service.llm_service.select_best_image(image_candidates, article_snippet, search_query)

    def _download_image_sync(self, url: str, max_retries: int = 1) -> Optional[bytes]:
        """DEPRECATED - Use ImageStorage directly"""
        print("Warning: _download_image_sync is deprecated")
        storage = ImageStorage() 
        return storage.download_image(url, max_retries)

    def _upload_image_to_supabase_sync(self, image_bytes: bytes, destination_path: str) -> Optional[str]:
        """DEPRECATED - Use ImageStorage directly"""
        print("Warning: _upload_image_to_supabase_sync is deprecated")
        storage = ImageStorage()
        return storage.upload_to_supabase(image_bytes, destination_path)

    def _download_and_upload_selected_image(self, image_data: dict, query_for_filename: str) -> Optional[str]:
        """DEPRECATED - Use ImageStorage directly"""
        print("Warning: _download_and_upload_selected_image is deprecated")
        storage = ImageStorage()
        return storage.process_and_upload_image(image_data, query_for_filename)