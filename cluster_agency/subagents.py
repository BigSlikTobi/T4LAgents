# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.models.lite_llm import LiteLlm

# Internal Imports
from utils import load_instruction_from_file
from tools import fetch_cluster_ids, fetch_articles_by_cluster_id, fetch_cluster_contents, write_summary_to_db, write_timeline_to_db, write_player_view_to_db, write_coaches_view_to_db, write_team_view_to_db, write_franchise_view_to_db, write_dynamic_view_to_db, close_cluster_by_id

#--------------------------------------------------------------------------
# Agent definitions Group  1

"""
The following group of agents will be used to fetch the cluster id, fetch the articles by cluster id, extract the content of the articles and create a summary and timeline of the articles 
to create the baseline for the 360 degree view.
    1. **FetchClusterId**: Fetches the oldest cluster ID from the clusters table where status is 'NEW' and isContent is false.
    2. **FetchClusterArticlesId**: Fetches all articles associated with a given cluster ID from the SourceArticles table.
    3. **ExtractArticleContent**: Extracts the content of the articles by their IDs from Supabase.
    4. **SummaryCreator**: Creates a summary of the articles.
    5. **TimelineCreator**: Creates a timeline of the articles.
    6. **CoachViewCreator**: Creates a view of the articles from the coach's perspective.
    7. **TeamViewCreator**: Creates a view of the articles from the team's perspective.
    8. **FranchiseViewCreator**: Creates a view of the articles from the franchise's perspective.
    9. **DynamicViewCreator**: Creates a dynamic view of the articles based on various inputs.
"""
# -------------------------------------------------------------------------

# --- Sub Agent 1.1: Article Cluster Id Fetcher ---
fetch_cluster_id_agent = LlmAgent(
    name="FetchClusterId",
    model=LiteLlm(model="openai/gpt-4.1-mini"),
    instruction=load_instruction_from_file("fetch_cluster_id_instructions.txt"),
    tools=[fetch_cluster_ids],
    output_key="cluster_id",  # Save result to state
)

# --- Sub Agent 1.2: Article Fetcher ---
fetch_cluster_articles_id_agent = LlmAgent(
    name="FetchClusterArticlesId",
    model=LiteLlm(model="openai/gpt-4.1-mini"),
    instruction=load_instruction_from_file("fetch_cluster_articles_ids_instructions.txt"),
    tools=[fetch_articles_by_cluster_id],
    output_key="article_ids",  # Save result to state
)

# --- Sub Agent 1.3: Article Content Extractor ---
extract_article_content_agent = LlmAgent(
    name="ExtractArticleContent",
    model=LiteLlm(model="openai/gpt-4.1-mini"),
    instruction=load_instruction_from_file("extract_article_content_instructions.txt"),
    tools=[fetch_cluster_contents],
    output_key="cluster_content",  # Save result to state
)

# --- Sub Agent 1.4: Summary Creator ---
summary_creator_agent = LlmAgent(
    name="SummaryCreator",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("summary_creator_instructions.txt"),
    tools=[],
    output_key="summary",  # Save result to state
)

# --- Sub Agent 1.5: Timeline Creator ---
timeline_creator_agent = LlmAgent(
    name="TimelineCreator",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("timeline_creator_instructions.txt"),
    tools=[],
    output_key="timeline",  # Save result to state
)

#--------------------------------------------------------------------------
# Agent definitions Group  2
""" 
The following group of agents will be used to review the content of the cluster articles from different perspectives.
    1. **Players perspective: The main player of this article needs to be detected and then the articles get analyzed to create a 360 degree view from the players perspective.
    2. **Coaches perspective. The main coach of the team needs to be detected and then the articles get analyzed to create a 360 degree view from the coaches perspective.
    3. **Team perspective. The main team of the player needs to be detected and then the articles get analyzed to create a 360 degree view from the teams perspective.
    4. **Franchise perspective. The main franchise of the player needs to be detected and then the articles get analyzed to create a 360 degree view from the franchises perspective.
"""
#--------------------------------------------------------------------------

# --- Sub Agent 2.1: Player Detection ---
player_detection_agent = LlmAgent(
    name="PlayerDetection",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("player_detection_instructions.txt"),
    tools=[google_search],
    output_key="player_name", 
)

# --- Sub Agent 2.2: Player Perspective ---
player_perspective_agent = LlmAgent(
    name="PlayerPerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("player_perspective_instructions.txt"),
    tools=[google_search],
    output_key="player_perspective", 
)

# --- Sub Agent 2.3: Coach Detection ---
coach_detection_agent = LlmAgent(
    name="CoachDetection",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("coach_detection_instructions.txt"),
    tools=[google_search],
    output_key="coach_name", 
)

# --- Sub Agent 2.4: Coach Perspective ---
coach_perspective_agent = LlmAgent(
    name="CoachPerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("coach_perspective_instructions.txt"),
    tools=[google_search],
    output_key="coach_perspective", 
)

# --- Sub Agent 2.5: Team Detection ---
team_detection_agent = LlmAgent(
    name="TeamDetection",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("team_detection_instructions.txt"),
    tools=[google_search],
    output_key="team_name", 
)
# --- Sub Agent 2.6: Team Perspective ---
team_perspective_agent = LlmAgent(
    name="TeamPerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("team_perspective_instructions.txt"),
    tools=[google_search],
    output_key="team_perspective", 
)

# --- Sub Agent 2.7: Franchise Perspective ---
franchise_perspective_agent = LlmAgent(
    name="FranchisePerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("franchise_perspective_instructions.txt"),
    tools=[google_search],
    output_key="franchise_perspective", 
)

#--------------------------------------------------------------------------
# Agent definitions Group  3
""" 
The following group of agents will be used to create dynamic perspectives of the articles to enrich the 360 degree view. 
Therefore the articles will be analyzed for 1 additional dynamic perspective that will further enrich the 360 degree view.
"""
#--------------------------------------------------------------------------

# --- Sub Agent 3.1: Dynamic Perspective Detection ---
first_dynamic_perspective_detection_agent = LlmAgent(
    name="firstDynamicPerspectiveDetection",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("first_dynamic_perspective_detection_instructions.txt"),
    tools=[google_search],
    output_key="dynamic_name1", 
)
# --- Sub Agent 3.2: Dynamic Perspective ---   
first_dynamic_perspective_agent = LlmAgent(
    name="firstDynamicPerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("first_dynamic_perspective_instructions.txt"),
    tools=[google_search],
    output_key="dynamic_perspective", 
)

# --- Sub Agent 3.3: Dynamic Perspective ---
second_dynamic_perspective_detection_agent = LlmAgent(
    name="secondDynamicPerspectiveDetection",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("second_dynamic_perspective_detection_instructions.txt"),
    tools=[google_search],
    output_key="dynamic_name2", 
)
# --- Sub Agent 3.4: Dynamic Perspective ---   
second_dynamic_perspective_agent = LlmAgent(
    name="secondDynamicPerspective",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("second_dynamic_perspective_instructions.txt"),
    tools=[google_search],
    output_key="dynamic_perspective2", 
)

#--------------------------------------------------------------------------
# Agent definitions Group  4
""" 
These agents are used to clean up the data and to finally prepare them to be send to the database and therefore shown to the user.
    1. **Content Analyst**: After the contents are created this agent will analyze and fact check the content and either approve or reject the content.
    2. **DataCleaner**: Cleans up the data by seperating Headline and content and enrich the contnet with proper html tags.
    3. **Database Uploader**: Uploads the data to the database and creates a new entry in the database.
These agents are created to be reusable and can be used for every content created in this project.
"""
#--------------------------------------------------------------------------

# --- Sub Agent 4.1: Content Analyst ---
def make_content_analyst(content_key: str) -> LlmAgent:
    # load+inject the key name into the instruction so the LLM knows which variable to use
    raw = load_instruction_from_file("content_analyst_instructions.txt")
    instruction = (
        raw
        .replace("{{CONTENT_KEY}}", content_key)
    )

    return LlmAgent(
        name=f"ContentAnalyst_{content_key}",   # brackets → underscore
        model="gemini-2.0-flash-lite",
        instruction=instruction,
        tools=[],
        output_key="analysis_report",
    )

# --- Sub Agent 4.2: Data Cleaner ---
def make_data_cleaner(content_key: str) -> LlmAgent:
    # load+inject the key name into the instruction so the LLM knows which variable to use
    raw = load_instruction_from_file("data_cleaner_instructions.txt")
    instruction = (
        raw
        .replace("{{CONTENT_KEY}}", content_key)
    )
    return LlmAgent(
        name=f"DataCleaner_{content_key}",
        model="gemini-2.5-flash-preview-04-17",
        instruction=instruction,    
        tools=[],
        output_key="cleaned_data",  # Save result to state
    )

# --- Sub Agent 4.3.1.: Summary Uploader ---
summary_uploader = LlmAgent(
    name="SummaryUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("summary_uploader_instructions.txt"),
    tools=[write_summary_to_db],
    output_key="summary_response", 
)

# --- Sub Agent 4.3.2.: timeline Uploader ---
timeline_uploader = LlmAgent(
    name="TimelineUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("timeline_uploader_instructions.txt"),
    tools=[write_timeline_to_db],
    output_key="timeline_response", 
)

# --- Sub Agent 4.3.3.: Player view Uploader ---
player_view_uploader = LlmAgent(
    name="PlayerViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("player_view_uploader_instructions.txt"),
    tools=[write_player_view_to_db],
    output_key="player_view_response", 
)

# --- Sub Agent 4.3.4.: Coach view Uploader ---
coach_view_uploader = LlmAgent(
    name="CoachViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("coach_view_uploader_instructions.txt"),
    tools=[write_coaches_view_to_db],
    output_key="coach_view_response", 
)

# --- Sub Agent 4.3.5.: Team view Uploader ---
team_view_uploader = LlmAgent(
    name="TeamViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("team_view_uploader_instructions.txt"),
    tools=[write_team_view_to_db],
    output_key="team_view_response", 
)

# --- Sub Agent 4.3.6.: Franchise view Uploader ---
franchise_view_uploader = LlmAgent(
    name="FranchiseViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("franchise_view_uploader_instructions.txt"),
    tools=[write_franchise_view_to_db],
    output_key="franchise_view_response", 
)

# --- Sub Agent 4.3.7.: First Dynamic view Uploader ---
first_dynamic_view_uploader = LlmAgent(
    name="DynamicViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("dynamic_view1_uploader_instructions.txt"),
    tools=[write_dynamic_view_to_db],
    output_key="first_dynamic_view_response", 
)

# --- Sub Agent 4.3.8.: Second Dynamic view Uploader ---
second_dynamic_view_uploader = LlmAgent(
    name="DynamicViewUploader",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("dynamic_view2_uploader_instructions.txt"),
    tools=[write_dynamic_view_to_db],
    output_key="second_dynamic_view_response", 
)

# ------------------------------------------------------
# Agent definitions Group 5
"""
Finally the cluster will be closed and the isContent status of the cluster will be set to 'TRUE' in the database.
"""
# ----------------------------------------------------

# --- Sub Agent 5.1: Close Cluster ---
close_cluster_id_agent = LlmAgent(
    name="CloseClusterId",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("close_cluster_id_instructions.txt"),
    tools=[close_cluster_by_id],
    output_key="close_cluster_response", 
)


# Dictionary containing all agents for export
agents = {
    "fetch_cluster_id": fetch_cluster_id_agent,
    "fetch_cluster_articles_id": fetch_cluster_articles_id_agent,
    "extract_article_content": extract_article_content_agent,
    "summary_creator": summary_creator_agent,
    "timeline_creator": timeline_creator_agent,
    "player_detection": player_detection_agent,
    "player_perspective": player_perspective_agent,
    "coach_detection": coach_detection_agent,
    "coach_perspective": coach_perspective_agent,
    "team_detection": team_detection_agent,
    "team_perspective": team_perspective_agent,
    "franchise_perspective": franchise_perspective_agent,
    "first_dynamic_perspective_detection": first_dynamic_perspective_detection_agent,
    "first_dynamic_perspective": first_dynamic_perspective_agent,
    "second_dynamic_perspective_detection": second_dynamic_perspective_detection_agent,
    "second_dynamic_perspective": second_dynamic_perspective_agent,
    "content_analyst": make_content_analyst,
    "data_cleaner": make_data_cleaner,
    "summary_uploader": summary_uploader,
    "timeline_uploader": timeline_uploader,
    "player_view_uploader": player_view_uploader,
    "coach_view_uploader": coach_view_uploader,
    "team_view_uploader": team_view_uploader,
    "franchise_view_uploader": franchise_view_uploader,
    "first_dynamic_view_uploader": first_dynamic_view_uploader,
    "second_dynamic_view_uploader": second_dynamic_view_uploader,
    "close_cluster_id_agent": close_cluster_id_agent,
}

# Export statement
__all__ = ["agents"]
