"""
Main Image Service - Orchestrates the image search, selection and upload process
"""
import argparse
import sys
import time
from typing import Optional, List, Dict, Any
from article_service import ArticleService
from llm_service import LLMService
from image_search import ImageSearch
from image_validation import ImageValidator
from image_storage import ImageStorage
from config import CANDIDATES_TO_LLM_FOR_SELECTION, TABLES_FOR_IMAGES

class MainImageService:
    """Main orchestration service that coordinates the image search workflow"""
    
    def __init__(self):
        """Initialize the main image service with all required components"""
        self.article_service = ArticleService()
        self.llm_service = LLMService()
        self.image_search = ImageSearch()
        self.image_validator = ImageValidator()
        self.image_storage = ImageStorage()
        print("Main Image Service initialized with all components.")
        
    def process_article_and_upload_image(self, article_id: str, table_name: str = None) -> Optional[str]:
        """Process an article and find, select, and upload a relevant image.
        
        Args:
            article_id: The ID of the article to process
            table_name: The name of the table containing the article
            
        Returns:
            URL of uploaded image or None if any step fails
        """
        print(f"\n--- Processing image for article ID: {article_id} in table: {table_name or 'default'} ---")
        
        # Step 1: Fetch article content
        if table_name:
            # Fetch from specific table
            articles = self.article_service.fetch_articles_without_images(table_name, limit=10)
            
            # Search for the requested article in the fetched list
            article_data = None
            for article in articles:
                if str(article['id']) == str(article_id):
                    article_data = article
                    break
                    
            if not article_data:
                print(f"Failed to fetch article {article_id} from table {table_name}. Aborting.")
                return None
                
            article_content = article_data['content']
            
            # Extract cluster_id from article
            cluster_id = None
            if 'cluster_id' in article_data:
                cluster_id = article_data['cluster_id']
            else:
                print(f"Warning: No cluster_id found in article. Database tracking will be skipped.")
        else:
            # Legacy approach using default table
            article_content = self.article_service.fetch_article_content(article_id)
        
        if not article_content:
            print("Failed to fetch article content. Aborting.")
            return None

        # Step 2: Generate search query with LLM
        if not self.llm_service.is_available():
            print("LLM service not available. Aborting.")
            return None
            
        search_query = self.llm_service.generate_search_query(article_content)
        if not search_query:
            print("Failed to generate search query. Aborting.")
            return None

        # Step 3: Search for image candidates with enhanced retry logic
        image_candidates = self.image_search.search_images(
            search_query, 
            num_to_fetch=20,
            max_retries=3  # Explicitly set max retries for rate limit handling
        )
        
        if not image_candidates:
            # Try again with a more generic query if specific one failed
            alt_query = " ".join(search_query.split()[:2] + ["photos"])
            print(f"No results with specific query. Trying alternative query: '{alt_query}'")
            image_candidates = self.image_search.search_images(alt_query, num_to_fetch=15, max_retries=2)
            
        if not image_candidates:
            print(f"No suitable image candidates found for '{search_query}'. Aborting.")
            return None

        # Step 4: Validate image URLs
        valid_image_candidates = self.image_validator.filter_valid_images(
            image_candidates, 
            max_valid=CANDIDATES_TO_LLM_FOR_SELECTION + 5  # Get a few more than needed for LLM
        )
        
        if not valid_image_candidates:
            print("No valid image URLs after validation. Aborting.")
            return None
            
        print(f"Found {len(valid_image_candidates)} valid image candidates.")

        # Step 5: Select the best image with LLM
        article_snippet = article_content[:4000]  # Limit for LLM context
        selected_image = self.llm_service.select_best_image(
            valid_image_candidates[:CANDIDATES_TO_LLM_FOR_SELECTION],
            article_snippet,
            search_query
        )
        
        if not selected_image:
            print("LLM did not select an image or selection failed. Aborting.")
            return None

        # Step 6: Download and upload the selected image
        final_image_url = self.image_storage.process_and_upload_image(selected_image, search_query)
        
        if final_image_url:
            print(f"SUCCESS: Image processed and uploaded for article {article_id}. URL: {final_image_url}")
            
            # Save image information to cluster_images table (if we have a table_name and cluster_id)
            if table_name and cluster_id:
                # Extract view from table name (e.g., "coach" from "cluster_coach_view")
                view = None
                if table_name.startswith("cluster_"):
                    table_parts = table_name.split('_')
                    if len(table_parts) >= 3:
                        view = table_parts[1]  # Extract middle part (e.g., "coach" from "cluster_coach_view")
                    elif len(table_parts) == 2:
                        view = table_parts[1]  # For tables like "cluster_summary", use "summary"
                
                if view:
                    original_url = selected_image.get("url", "unknown")
                    success = self.image_storage.save_image_info(
                        cluster_id=cluster_id,
                        image_url=final_image_url,
                        original_url=original_url,
                        view=view
                    )
                    if not success:
                        print(f"Warning: Image uploaded but failed to save metadata to cluster_images table.")
                else:
                    print(f"Warning: Could not extract view from table name '{table_name}'. Skipping metadata save.")
            
            # Update the article in database to mark it as having an image
            if table_name:
                success = self.article_service.update_article_has_image(table_name, article_id, final_image_url)
                if not success:
                    print(f"Warning: Image uploaded but failed to update article {article_id} in {table_name}.")
            
            return final_image_url
        else:
            print(f"FAILED to download/upload the selected image for article {article_id}.")
            return None

    def process_table_articles(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Process multiple articles from a specific table that don't have images.
        
        Args:
            table_name: The name of the table to process articles from
            limit: Maximum number of articles to process
            
        Returns:
            List of results with article IDs and status
        """
        print(f"\n=== Processing up to {limit} articles from table '{table_name}' ===\n")
        
        # Validate table exists in config
        if table_name not in TABLES_FOR_IMAGES:
            print(f"Error: Unknown table '{table_name}'. Available tables: {list(TABLES_FOR_IMAGES.keys())}")
            return []
            
        # Fetch articles without images
        articles = self.article_service.fetch_articles_without_images(table_name, limit=limit)
        if not articles:
            print(f"No articles without images found in table '{table_name}'.")
            return []
            
        print(f"Found {len(articles)} articles without images in '{table_name}'. Starting processing...")
        
        results = []
        for article in articles:
            article_id = article["id"]
            print(f"\nProcessing article {article_id} from {table_name}...")
            
            try:
                # Process and upload image
                start_time = time.time()
                image_url = self.process_article_and_upload_image(article_id, table_name)
                process_time = time.time() - start_time
                
                if image_url:
                    results.append({
                        "article_id": article_id,
                        "status": "success",
                        "image_url": image_url,
                        "process_time_sec": round(process_time, 2)
                    })
                else:
                    results.append({
                        "article_id": article_id,
                        "status": "failed",
                        "process_time_sec": round(process_time, 2)
                    })
                    
            except Exception as e:
                print(f"Error processing article {article_id}: {e}")
                results.append({
                    "article_id": article_id,
                    "status": "error",
                    "error_message": str(e)
                })
            
            # Add a small delay between articles to avoid rate limits
            time.sleep(1)
                
        # Summary report
        success_count = sum(1 for r in results if r.get("status") == "success")
        print(f"\n=== Finished processing {len(results)} articles from '{table_name}' ===")
        print(f"Success: {success_count}, Failed: {len(results) - success_count}")
        
        return results

def main():
    """Main entry point with CLI argument parsing for different processes"""
    parser = argparse.ArgumentParser(description='Image Service for Articles')
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add "process" command for single article processing
    process_parser = subparsers.add_parser('process', help='Process a single article')
    process_parser.add_argument('--id', required=True, help='Article ID to process')
    process_parser.add_argument('--table', required=False, help='Table name containing the article')
    
    # Add "batch" command for batch processing of a specific table
    batch_parser = subparsers.add_parser('batch', help='Process multiple articles from a table')
    batch_parser.add_argument('--table', required=True, choices=TABLES_FOR_IMAGES.keys(), 
                             help='Table name to process articles from')
    batch_parser.add_argument('--limit', type=int, default=5, 
                             help='Maximum number of articles to process (default: 5)')
    
    # Add "tables" command to list available tables
    subparsers.add_parser('tables', help='List all available tables')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize service
    service = MainImageService()
    
    # Execute appropriate command
    if args.command == 'process':
        # Process a single article
        image_url = service.process_article_and_upload_image(args.id, args.table)
        if image_url:
            print(f"Article processed successfully. Image URL: {image_url}")
            return 0
        else:
            print("Failed to process article.")
            return 1
            
    elif args.command == 'batch':
        # Process multiple articles from a table
        results = service.process_table_articles(args.table, args.limit)
        success_count = sum(1 for r in results if r.get("status") == "success")
        if results and success_count > 0:
            print(f"Processed {len(results)} articles with {success_count} successes.")
            return 0
        else:
            print("Batch processing completed with no successful articles.")
            return 1
            
    elif args.command == 'tables':
        # List available tables
        print("Available tables for image processing:")
        for table in TABLES_FOR_IMAGES:
            print(f"- {table}")
        return 0
        
    else:
        # No command specified
        parser.print_help()
        return 0
        
if __name__ == "__main__":
    sys.exit(main())