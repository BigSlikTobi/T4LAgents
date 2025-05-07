import os
import traceback
from typing import Optional, List, Dict, Any, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

from config import (
    ARTICLE_TABLE_NAME,
    ARTICLE_ID_COLUMN,
    ARTICLE_CONTENT_COLUMN,
    TABLES_FOR_IMAGES
)

class ArticleService:
    """Service to fetch article content from Supabase database"""
    def __init__(self):
        """Initialize the ArticleService with Supabase connection."""
        load_dotenv()
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
            
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("ArticleService initialized with Supabase client.")

    def fetch_article_content(self, article_id: str) -> Optional[str]:
        """Fetch article content from Supabase by ID.
        
        Args:
            article_id: The ID of the article to fetch
            
        Returns:
            The article content as a string, or None if not found or on error
        """
        print(f"Fetching article with ID '{article_id}' from table '{ARTICLE_TABLE_NAME}'...")
        try:
            response = self.supabase.table(ARTICLE_TABLE_NAME)\
                               .select(f"{ARTICLE_CONTENT_COLUMN}")\
                               .eq(ARTICLE_ID_COLUMN, article_id)\
                               .single()\
                               .execute()
                               
            if response.data and ARTICLE_CONTENT_COLUMN in response.data:
                article_content = response.data[ARTICLE_CONTENT_COLUMN]
                print(f"Successfully fetched article content (length: {len(article_content)} chars).")
                return article_content
            else:
                print(f"No article content found for ID '{article_id}' or column '{ARTICLE_CONTENT_COLUMN}' missing.")
                if hasattr(response, 'error') and response.error:
                    err_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
                    print(f"Supabase error: {err_msg}")
                return None
        except Exception as e:
            print(f"Error fetching article from Supabase: {e}\n{traceback.format_exc()}")
            return None
            
    def fetch_articles_without_images(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch articles that don't have images from a specific table.
        
        Args:
            table_name: The name of the table to fetch articles from
            limit: Maximum number of articles to fetch
            
        Returns:
            A list of article dictionaries containing id, content, and cluster_id
        """
        if table_name not in TABLES_FOR_IMAGES:
            raise ValueError(f"Unknown table: {table_name}. Available tables: {list(TABLES_FOR_IMAGES.keys())}")
            
        table_config = TABLES_FOR_IMAGES[table_name]
        id_col = table_config["id_column"]
        content_col = table_config["content_column"]
        has_image_col = table_config["has_image_column"]
        
        print(f"Fetching up to {limit} articles without images from table '{table_name}'...")
        
        try:
            # Also fetch cluster_id for the cluster_images table
            response = self.supabase.table(table_name)\
                                .select(f"{id_col}, {content_col}, cluster_id")\
                                .eq(has_image_col, False)\
                                .limit(limit)\
                                .execute()
                                
            if response.data:
                articles = []
                for article in response.data:
                    if content_col in article and id_col in article:
                        article_data = {
                            "id": article[id_col],
                            "content": article[content_col]
                        }
                        # Add cluster_id if it exists
                        if "cluster_id" in article:
                            article_data["cluster_id"] = article["cluster_id"]
                        articles.append(article_data)
                        
                print(f"Successfully fetched {len(articles)} articles without images from {table_name}.")
                return articles
            else:
                print(f"No articles without images found in table '{table_name}'.")
                return []
        except Exception as e:
            print(f"Error fetching articles from Supabase: {e}\n{traceback.format_exc()}")
            return []
            
    def update_article_has_image(self, table_name: str, article_id: str, image_url: str) -> bool:
        """Update an article to mark it as having an image and store the image URL.
        
        Args:
            table_name: The name of the table containing the article
            article_id: The ID of the article to update
            image_url: The URL of the image to associate with the article (stored in cluster_images table instead)
            
        Returns:
            True if update was successful, False otherwise
        """
        if table_name not in TABLES_FOR_IMAGES:
            raise ValueError(f"Unknown table: {table_name}. Available tables: {list(TABLES_FOR_IMAGES.keys())}")
            
        table_config = TABLES_FOR_IMAGES[table_name]
        id_col = table_config["id_column"]
        has_image_col = table_config["has_image_column"]
        
        print(f"Updating article {article_id} in table {table_name} to set {has_image_col}=True")
        
        try:
            # Only update the hasImage column, as the imageUrl is now stored in the cluster_images table
            response = self.supabase.table(table_name)\
                                .update({has_image_col: True})\
                                .eq(id_col, article_id)\
                                .execute()
                                
            if response.data:
                print(f"Successfully updated article {article_id} to mark as having an image.")
                return True
            else:
                print(f"Failed to update article {article_id}.")
                if hasattr(response, 'error') and response.error:
                    err_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
                    print(f"Supabase error: {err_msg}")
                return False
        except Exception as e:
            print(f"Error updating article: {e}")
            return False