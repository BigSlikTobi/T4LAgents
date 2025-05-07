import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any, List, Optional, Set

load_dotenv()

# --------------------------------------------------------------------------
# Tools to fetch cluster information and articles from Supabase
# --------------------------------------------------------------------------

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


#--------------------------------------------------------------------------
# Tools to write results and articles back to Supabase
#--------------------------------------------------------------------------

def write_summary_to_db(cluster_id: str, headline: str, content: str, language: str = "en"):
    """
    Write the summary to the cluster_summary table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_summary') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def write_timeline_to_db(
    timeline_name: str,
    timeline_json_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Inserts a single timeline's data into the Supabase tables
        (timelines and timeline_article_links). Does NOT interact with the articles table.

        Args:
            timeline_name: The name for this timeline (e.g., "Vikings QB Search Timeline").
            timeline_json_data: The JSON dictionary containing the timeline data
                                (expected to have a "ClusterId" key with an array).

        Returns:
            The ID of the newly created timeline record if successful, None otherwise.
        """
        # Initialize Supabase client
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        supabase: Client = create_client(url, key)
        
        new_timeline_id = None
        try:
            # 1. Insert into the timelines table
            # Ensure timeline_name is not empty and timeline_json_data is valid
            if not timeline_name or not timeline_json_data or "ClusterId" not in timeline_json_data:
                print("Error: Invalid timeline name or data provided.")
                return None

            timeline_response = supabase.table('timelines').insert({
                'timeline_name': timeline_name,
                'timeline_data': timeline_json_data
            }).execute()

            if not timeline_response.data:
                print(f"Error inserting timeline '{timeline_name}': No data returned from insert.")
                # Consider checking response status code or error property for more details
                return None

            new_timeline_id = timeline_response.data[0]['id']
            print(f"Successfully inserted timeline: '{timeline_name}' with ID: {new_timeline_id}")

            # 2. Extract all unique article_ids from the JSON data
            all_article_ids: Set[str] = set()
            if isinstance(timeline_json_data.get("ClusterId"), list):
                for cluster in timeline_json_data["ClusterId"]:
                    if isinstance(cluster.get("article_id"), list):
                        for article_id in cluster["article_id"]:
                            if isinstance(article_id, str):
                                all_article_ids.add(article_id)
                            else:
                                print(f"Warning: Found non-string article_id: {article_id} in timeline '{timeline_name}'. Skipping.")
                    else:
                        print(f"Warning: 'article_id' not found or not a list in a cluster for timeline '{timeline_name}'.")
            else:
                print(f"Warning: 'ClusterId' not found or not a list in timeline data for '{timeline_name}'. No articles or links to process.")


            # 3. Prepare data for batch insert into timeline_article_links
            link_insert_data: List[Dict[str, str]] = []
            for art_id in all_article_ids:
                link_insert_data.append({
                    'timeline_id': new_timeline_id,
                    'article_id': art_id
                })

            # 4. Insert links into timeline_article_links table
            if link_insert_data:
                # Use on_conflict to ignore if the timeline_id, article_id pair already exists
                # This is primarily to handle potential edge cases, though unlikely with a new timeline ID
                link_insert_response = supabase.table('timeline_article_links').insert(
                    link_insert_data,
                    on_conflict='timeline_id, article_id'
                ).execute()

                if link_insert_response.data:
                    print(f"Successfully inserted {len(link_insert_response.data)} timeline_article links for timeline '{timeline_name}'.")
                else:
                    # This might indicate an issue or simply that no links were extracted (empty ClusterId array)
                    print(f"No new timeline_article links inserted for timeline '{timeline_name}'.") # Consider adding more specific error check here


            # If we reached here without errors, return the new timeline ID
            return new_timeline_id

        except Exception as e:
            print(f"An error occurred during insertion of timeline '{timeline_name}': {e}")
            # Consider adding cleanup logic here to delete the partially inserted
            # timeline and links if the process fails mid-way. This would require
            # transaction support or explicit delete calls.
            return None

def write_player_view_to_db(cluster_id: str, headline: str, content: str, player: str, language: str = "en"):
    """
    Write the summary to the cluster_player_view table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
        player (str): The name of the player
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "player": player,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_player_view') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def write_coaches_view_to_db(cluster_id: str, headline: str, content: str, coach: str, language: str = "en"):
    """
    Write the summary to the cluster_coaches_view table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
        coach (str): The name of the coach
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "coach": coach,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_coach_view') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def write_franchise_view_to_db(cluster_id: str, headline: str, content: str, team: str, language: str = "en"):
    """
    Write the summary to the cluster_franchise_view table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
        team (str): The name of the team
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "team": team,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_franchise_view') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def write_team_view_to_db(cluster_id: str, headline: str, content: str, team: str, language: str = "en"):
    """
    Write the summary to the cluster_team_view table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
        team (str): The name of the team
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "team": team,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_team_view') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def write_dynamic_view_to_db(cluster_id: str, headline: str, content: str, view: str, language: str = "en"):
    """
    Write the summary to the cluster_dynamic_view table in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster
        headline (str): The summary headline
        content (str): The summary content
        language (str, optional): The language of the summary. Defaults to "en"
        view (str): The name of the view
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    data = {
        "cluster_id": cluster_id,
        "language": language,
        "view": view,
        "headline": headline,
        "content": content
    }
    
    response = supabase.table('cluster_dynamic_view') \
        .insert(data) \
        .execute()
    
    print(f"Written summary for cluster {cluster_id} to database.")
    return response.data

def close_cluster_by_id(cluster_id: str):
    """
    Marks a cluster as processed by setting its isContent field to True in Supabase.
    
    Args:
        cluster_id (str): The ID of the cluster to mark as processed
    
    Returns:
        dict: Response data from the database operation
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    # Use explicit boolean True value for PostgreSQL compatibility
    response = supabase.table('clusters') \
        .update({"isContent": bool(True)}) \
        .eq("cluster_id", cluster_id) \
        .execute()
    
    print(f"Marked cluster {cluster_id} as processed.")
    return response.data
