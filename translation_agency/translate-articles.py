import os
import argparse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import time
import json

# --- Load environment variables ---
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# --- Check for required environment variables ---
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase URL and Key must be set as environment variables.")
    print("Please set SUPABASE_URL and SUPABASE_KEY.")
    exit(1)

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY must be set as an environment variable.")
    exit(1)

# --- Initialize Gemini ---
genai.configure(api_key=GEMINI_API_KEY)

# --- Initialize Supabase client ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Default configuration ---
DEFAULT_SOURCE_TABLE = 'cluster_coach_view'
DEFAULT_TRANSLATIONS_TABLE = 'cluster_coach_view_int'
DEFAULT_FOREIGN_KEY_COLUMN = 'cluster_coach_view_id'
DEFAULT_LANGUAGE = 'de'  # German as default
DEFAULT_TIME_LIMIT_HOURS = 72
DEFAULT_BATCH_SIZE = 5

# --- Gemini model configuration ---
MODEL_NAME = "gemini-2.0-flash"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

def find_untranslated_articles(source_table: str, translations_table: str,
                              foreign_key_column: str, target_lang: str,
                              time_limit_hours: int, batch_size: int) -> List[Dict[str, Any]]:
    """
    Find articles in the source table that don't have translations in the target language.
    
    Args:
        source_table: The table containing source articles
        translations_table: The table containing translations
        foreign_key_column: Column in translations table referencing source table
        target_lang: Language code to check for translations
        time_limit_hours: Only look for articles within this time window
        batch_size: Maximum number of articles to return
        
    Returns:
        List of untranslated articles or empty list if none found
    """
    try:
        # Calculate the timestamp for the start of the time window
        time_limit = datetime.utcnow() - timedelta(hours=time_limit_hours)
        time_limit_iso = time_limit.isoformat(timespec='seconds') + 'Z'
        
        # Get IDs of articles that already have translations for the target language
        response_translated_ids = supabase.from_(translations_table)\
            .select(foreign_key_column)\
            .eq('language_code', target_lang)\
            .execute()
            
        translated_ids = []
        if response_translated_ids.data:
            translated_ids = [item[foreign_key_column] for item in response_translated_ids.data]
            
        # Query for untranslated articles within time limit
        query = supabase.from_(source_table).select('*')
        query = query.gte('created_at', time_limit_iso)
        
        if translated_ids:
            query = query.not_.in_('id', translated_ids)
            
        if batch_size > 0:
            query = query.limit(batch_size)
            
        response_untranslated = query.execute()
        
        if not response_untranslated.data:
            print(f"No untranslated articles found for language '{target_lang}' within the last {time_limit_hours} hours.")
            return []
            
        print(f"Found {len(response_untranslated.data)} untranslated articles for language '{target_lang}'")
        return response_untranslated.data
        
    except Exception as e:
        print(f"Error finding untranslated articles: {e}")
        return []

def translate_article(article: Dict[str, Any], target_lang: str) -> Optional[Dict[str, Any]]:
    """
    Translate an article using Gemini 2.0 Flash.
    
    Args:
        article: Dictionary containing article data
        target_lang: Target language code
        
    Returns:
        Dictionary with translated content or None on failure
    """
    try:
        # Extract the content to translate
        headline = article.get('headline', '')
        content = article.get('content', '')
        article_id = article.get('id')
        
        # Skip if no content to translate
        if not headline or not content:
            print(f"Article ID {article_id} is missing headline or content. Skipping.")
            return None
            
        # Create the prompt for translation
        language_name = {'de': 'German', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian'}.get(target_lang, target_lang)
        
        prompt = f"""
        Act as a professional translator with expertise in American Football terminology.

        Translate the following article from English to {language_name}. 
        Preserve names, maintain proper football terminology, and keep the same meaning and tone.

        HEADLINE: {headline}

        CONTENT: {content}

        Please return a structured JSON response with the following fields:
        - original_headline: The original headline in English
        - translated_headline: The translated headline in {language_name}
        - original_content: The original content in English
        - translated_content: The translated content in {language_name}

        Response format:
        {{
            "original_headline": "...",
            "translated_headline": "...",
            "original_content": "...",
            "translated_content": "..."
        }}
        """
        
        # Configure Gemini model
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
        
        # Set safety settings
        safety_settings = [
            {"category": c, "threshold": "BLOCK_NONE"} 
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                      "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]
        
        # Initialize model
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Call Gemini API with retry logic
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                if not response.text:
                    print(f"Empty response from Gemini API for article ID {article_id}. Retrying...")
                    attempts += 1
                    time.sleep(RETRY_DELAY)
                    continue
                    
                # Parse the JSON response
                translation_data = json.loads(response.text)
                
                # Construct result
                result = {
                    'article_id': article_id,
                    'original_headline': translation_data.get('original_headline', headline),
                    'translated_headline': translation_data.get('translated_headline', ''),
                    'original_content': translation_data.get('original_content', content),
                    'translated_content': translation_data.get('translated_content', ''),
                    'language_code': target_lang
                }
                
                # Verify we have translations
                if not result['translated_headline'] or not result['translated_content']:
                    print(f"Missing translations for article ID {article_id}. Retrying...")
                    attempts += 1
                    time.sleep(RETRY_DELAY)
                    continue
                    
                print(f"Successfully translated article ID {article_id} to {language_name}")
                return result
                
            except Exception as e:
                print(f"Error translating article ID {article_id}: {e}")
                attempts += 1
                time.sleep(RETRY_DELAY)
        
        print(f"Failed to translate article ID {article_id} after {MAX_RETRIES} attempts")
        return None
        
    except Exception as e:
        print(f"Unexpected error during translation: {e}")
        return None

def save_translation(translation: Dict[str, Any], translations_table: str, foreign_key_column: str) -> bool:
    """
    Save a translated article to the database.
    
    Args:
        translation: Dictionary with translation data
        translations_table: Table to save to
        foreign_key_column: Foreign key column name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        article_id = translation.get('article_id')
        language_code = translation.get('language_code')
        
        # Prepare data for insert
        data = {
            foreign_key_column: article_id,
            'language_code': language_code,
            'headline': translation.get('translated_headline', ''),
            'content': translation.get('translated_content', '')
        }
        
        # Insert into database
        response = supabase.from_(translations_table).insert(data).execute()
        
        if response.data:
            print(f"Successfully saved translation for article ID {article_id} in {language_code}")
            return True
        else:
            print(f"Failed to save translation for article ID {article_id}")
            return False
    
    except Exception as e:
        print(f"Error saving translation to database: {e}")
        return False

def batch_translate_articles(source_table: str, translations_table: str,
                           foreign_key_column: str, target_lang: str,
                           time_limit_hours: int, batch_size: int) -> Dict[str, Any]:
    """
    Find and translate a batch of untranslated articles.
    
    Args:
        source_table: Table containing articles to translate
        translations_table: Table to save translations to
        foreign_key_column: Column in translations table referencing source table
        target_lang: Target language code
        time_limit_hours: Time window for articles to check
        batch_size: Maximum number of articles to process
        
    Returns:
        Dictionary with statistics about the operation
    """
    start_time = time.time()
    stats = {
        "target_language": target_lang,
        "articles_found": 0,
        "articles_processed": 0,
        "articles_translated": 0,
        "articles_saved": 0,
        "errors": 0,
        "time_taken_seconds": 0
    }
    
    # Find untranslated articles
    articles = find_untranslated_articles(
        source_table, translations_table, foreign_key_column, 
        target_lang, time_limit_hours, batch_size
    )
    
    stats["articles_found"] = len(articles)
    if not articles:
        stats["time_taken_seconds"] = round(time.time() - start_time, 2)
        return stats
        
    # Process each article
    for article in articles:
        stats["articles_processed"] += 1
        try:
            # Translate the article
            translation = translate_article(article, target_lang)
            
            if translation:
                stats["articles_translated"] += 1
                
                # Save the translation
                if save_translation(translation, translations_table, foreign_key_column):
                    stats["articles_saved"] += 1
            else:
                stats["errors"] += 1
        except Exception as e:
            print(f"Error processing article {article.get('id')}: {e}")
            stats["errors"] += 1
            
    # Calculate time taken
    stats["time_taken_seconds"] = round(time.time() - start_time, 2)
    
    # Print summary
    print(f"\nTranslation Summary:")
    print(f"Target language: {target_lang}")
    print(f"Articles found: {stats['articles_found']}")
    print(f"Articles processed: {stats['articles_processed']}")
    print(f"Articles translated: {stats['articles_translated']}")
    print(f"Articles saved to database: {stats['articles_saved']}")
    print(f"Errors: {stats['errors']}")
    print(f"Time taken: {stats['time_taken_seconds']} seconds")
    
    return stats

def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Batch translate articles using Gemini AI')
    
    parser.add_argument('--source-table', type=str, default=DEFAULT_SOURCE_TABLE,
                       help=f'Source table name (default: {DEFAULT_SOURCE_TABLE})')
    parser.add_argument('--translations-table', type=str, default=DEFAULT_TRANSLATIONS_TABLE,
                       help=f'Translations table name (default: {DEFAULT_TRANSLATIONS_TABLE})')
    parser.add_argument('--foreign-key', type=str, default=DEFAULT_FOREIGN_KEY_COLUMN,
                       help=f'Foreign key column name (default: {DEFAULT_FOREIGN_KEY_COLUMN})')
    parser.add_argument('--language', type=str, default=DEFAULT_LANGUAGE,
                       help=f'Target language code (default: {DEFAULT_LANGUAGE})')
    parser.add_argument('--time-limit', type=int, default=DEFAULT_TIME_LIMIT_HOURS,
                       help=f'Time limit in hours (default: {DEFAULT_TIME_LIMIT_HOURS})')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                       help=f'Maximum number of articles to process (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Only find untranslated articles without translating')
    
    args = parser.parse_args()
    
    print(f"Starting batch translation to {args.language}")
    print(f"Source table: {args.source_table}")
    print(f"Translations table: {args.translations_table}")
    
    if args.dry_run:
        print("DRY RUN MODE: Will only find untranslated articles without translating")
        articles = find_untranslated_articles(
            args.source_table, args.translations_table, args.foreign_key,
            args.language, args.time_limit, args.batch_size
        )
        
        if articles:
            print(f"Found {len(articles)} untranslated articles:")
            for article in articles:
                print(f"- Article ID: {article.get('id')}, Headline: {article.get('headline', 'N/A')}")
        else:
            print("No untranslated articles found.")
    else:
        # Run the full translation process
        batch_translate_articles(
            args.source_table, args.translations_table, args.foreign_key,
            args.language, args.time_limit, args.batch_size
        )

if __name__ == "__main__":
    main()