import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def fetch_cluster_ids():
    """
    Fetches the oldest cluster ID from the clusters table where status is 'NEW' and isContent is false.
    This function queries the Supabase database for the oldest unprocessed cluster ID.
    Args:
        None
    Returns:
        list: A list containing the oldest unprocessed cluster ID, or empty if none found.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    response = supabase.table('clusters') \
        .select('cluster_id') \
        .eq('status', 'NEW') \
        .eq('isContent', False) \
        .order('created_at') \
        .limit(1) \
        .execute()
    
    cluster_ids = [record['cluster_id'] for record in response.data]
    print("Found oldest cluster ID:", cluster_ids)
    return cluster_ids

def fetch_articles_by_cluster_id(cluster_id: str):
    """
    Fetches all articles associated with a given cluster ID from the SourceArticles table.
    Args:
        cluster_id (str): The ID of the cluster for which to fetch articles.
    Returns:
        list: A list of articles associated with the specified cluster ID.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    response = supabase.table('SourceArticles') \
        .select('*') \
        .eq('cluster_id', cluster_id) \
        .execute()
    
    articles = response.data
    print(f"Fetched {len(articles)} articles for cluster ID {cluster_id}.")
    return articles

def fetch_cluster_contents(article_ids: list[int]):
    """Fetch multiple articles by their IDs from Supabase.
    This function loads the content from the SourceArticles table in Supabase for multiple IDs.
    
    args:
        article_ids (list[int]): List of article IDs to fetch
    returns:
        list: A list of json objects with article headlines and contents
    """
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    # Query all articles by IDs
    response = supabase.table("SourceArticles") \
        .select("Content, headline, created_at") \
        .in_("id", article_ids) \
        .execute()
    
    # Get data from response
    articles = response.data if response.data else []
    
    print(f"Fetched {len(articles)} articles out of {len(article_ids)} requested.")
    return articles
