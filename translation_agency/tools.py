import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def fetch_untranslated_articles_with_cluster():
    """Fetch untranslated articles with non-empty cluster_id from Supabase.
    This function queries the Supabase database for articles that are not translated
    and have a non-empty cluster_id. It returns a dictionary with article IDs.
    An article is untranslated if the isTranslated field is False.
    
    args:
        None
    returns: 
        dict: A dictionary where keys are indices and values are article IDs
    """


    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    # Query: cluster_id is not null/empty and isTranslated is False, ordered by id desc
    response = supabase.table("SourceArticles") \
        .select("id,cluster_id,isTranslated") \
        .filter("isTranslated", "eq", False) \
        .order("id", desc=True) \
        .execute()
    
    # Get data from response using .data property
    articles = response.data

    # Filter for cluster_id not null/empty
    filtered_articles = [a for a in articles if a.get("cluster_id") not in (None, "", [])]

    # Only keep the first 1 filtered articles
    filtered_articles = filtered_articles[:1]

    # Create dictionary with article IDs using string keys to prevent type errors
    article_dict = {str(i): article["id"] for i, article in enumerate(filtered_articles)}
    
    return article_dict

def fetch_untranslated_articles_by_id(article_id: int):
    """Fetch untranslated articles by ID from Supabase.
    This function loads the content from the SourceArticles table in Supabase by id and returns the content. 
    
    args:
        article_id (int): The ID of the article to fetch
    returns:
        a json object with article id and content
    """
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    # Query the article by ID
    response = supabase.table("SourceArticles") \
        .select("id,Content,headline") \
        .eq("id", article_id) \
        .execute()
    
    # Get data from response
    article = response.data[0] if response.data else None
    
    return article

def write_to_database(article_id: int, Content: str, german_content: str, Headline: str, germanHeadline: str):
    """Write translated content to the database.
    This function takes the created translation and writes it into the Translation Database table.

    Args:
        article_id (int): The ID of the source article.
        english_content (str): The original English content.
        german_content (str): The translated German content.
        englishHeadline (str): The original English headline.
        germanHeadline (str): The translated German headline.
    Returns:
        dict: The inserted row or response from Supabase.
    """
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    # Insert the translation into the Translation table
    data = {
        "englishContent": Content,
        "germanContent": german_content,
        "englishHeadline": Headline,
        "germanHeadline": germanHeadline,
        "source": article_id
    }
    response = supabase.table("Translation").insert(data).execute()
    return response.data

def mark_article_as_translated(article_id: int):
    """Mark an article as translated in the database.
    This function updates the isTranslated field of the article to True.

    Args:
        article_id (int): The ID of the article to mark as translated.
    Returns:
        dict: The updated row or response from Supabase.
    """
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    # Update the article to mark it as translated
    response = supabase.table("SourceArticles").update({"isTranslated": True}).eq("id", article_id).execute()
    return response.data


# if __name__ == "__main__":
#     article_id = 128587  # Example article ID
#     result = write_to_database(article_id, "Sample English Content", "Sample German Content", "Sample English Headline", "Sample German Headline")
#     print(result)