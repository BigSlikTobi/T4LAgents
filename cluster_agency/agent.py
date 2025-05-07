# ADK imports
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents import LoopAgent, SequentialAgent, ParallelAgent

# internal imports
from subagents import agents

import os
from dotenv import load_dotenv

import litellm 
litellm.set_verbose = False 

# --------------------------------------------------------------------------
# Initialize agents
# --------------------------------------------------------------------------
fetch_cluster_id_agent = agents["fetch_cluster_id"]
fetch_cluster_articles_id_agent = agents["fetch_cluster_articles_id"]
extract_article_content_agent = agents["extract_article_content"]
summary_creator_agent = agents["summary_creator"]
timeline_creator_agent = agents["timeline_creator"]
player_detection_agent = agents["player_detection"]
player_perspective_agent = agents["player_perspective"]
coach_detection_agent = agents["coach_detection"]
coach_perspective_agent = agents["coach_perspective"]
team_detection_agent = agents["team_detection"]
team_perspective_agent = agents["team_perspective"]
franchise_perspective_agent = agents["franchise_perspective"]
first_dynamic_perspective_detection_agent = agents["first_dynamic_perspective_detection"]
first_dynamic_perspective_agent = agents["first_dynamic_perspective"]
second_dynamic_perspective_detection_agent = agents["second_dynamic_perspective_detection"]
second_dynamic_perspective_agent = agents["second_dynamic_perspective"]
content_analyst_for_player = agents["content_analyst"]("player_perspective")
content_analyst_for_coach = agents["content_analyst"]("coach_perspective")
content_analyst_for_team = agents["content_analyst"]("team_perspective")
content_analyst_for_franchise = agents["content_analyst"]("franchise_perspective")
content_analyst_for_firstdynamic = agents["content_analyst"]("dynamic_perspective")
content_analyst_for_seconddynamic = agents["content_analyst"]("dynamic_perspective2")
content_analyst_for_summary = agents["content_analyst"]("summary")
data_cleaner_for_summary = agents["data_cleaner"]("summary")
summary_uploader_agent = agents["summary_uploader"]
timeline_uploader_agent = agents["timeline_uploader"]
player_view_uploader_agent = agents["player_view_uploader"]
coach_view_uploader_agent = agents["coach_view_uploader"]
team_view_uploader_agent = agents["team_view_uploader"]
franchise_view_uploader_agent = agents["franchise_view_uploader"]
first_dynamic_view_uploader_agent = agents["first_dynamic_view_uploader"]
second_dynamic_view_uploader_agent = agents["second_dynamic_view_uploader"]
close_cluster_id_agent = agents["close_cluster_id_agent"]

#--------------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key  
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

#--------------------------------------------------------------------------
# Sequential Agents
#--------------------------------------------------------------------------

"""Sequential Agent to prepare the data."""

# -- Sequential Agent: Data Preparation --
fetch_context_agent = SequentialAgent(
    name="FetchContextAgent",
    sub_agents=[
        fetch_cluster_id_agent, 
        fetch_cluster_articles_id_agent, 
        extract_article_content_agent,
    ],
    description="Fetches cluster content from source.",
)

"""Sequential Agents to define the 360 degree view of the player, coach, team, and franchise."""

# -- Sequential Agent: Summary --
summary_agent = SequentialAgent(
    name="SummaryAgent",
    sub_agents=[
        summary_creator_agent,
        content_analyst_for_summary,
        data_cleaner_for_summary,
        summary_uploader_agent
    ],
    description="Creates a summary and timeline from the cluster data.",
)

# -- Sequential Agent: Timeline --
timeline_agent = SequentialAgent(
    name="TimelineAgent",
    sub_agents=[
        timeline_creator_agent,
        timeline_uploader_agent        
    ],
    description="Creates a timeline from the cluster data.",
)

# -- Sequential Agent: Player --
player_agent = SequentialAgent(
    name="PlayerAgent",
    sub_agents=[
        player_detection_agent, 
        player_perspective_agent,
        content_analyst_for_player,
        player_view_uploader_agent
        
    ],
    description="Executes a sequence of player detection and perspective analysis.",
)

# -- Sequential Agent: Coach --
coach_agent = SequentialAgent(
    name="CoachAgent",
    sub_agents=[
        coach_detection_agent, 
        coach_perspective_agent,
        content_analyst_for_coach,
        coach_view_uploader_agent
    ],
    description="Executes a sequence of coach detection and perspective analysis.",
)

# -- Sequential Agent: Team --
team_agent = SequentialAgent(
    name="TeamAgent",
    sub_agents=[
        team_detection_agent, 
        team_perspective_agent, 
        content_analyst_for_team,
        team_view_uploader_agent,
    ],
    description="Executes a sequence of team detection and perspective analysis.",
)

# -- Sequential Agent: Franchise --
franchise_agent = SequentialAgent(
    name="FranchiseAgent",
    sub_agents=[
        franchise_perspective_agent, 
        content_analyst_for_franchise,
        franchise_view_uploader_agent,
    ],
    description="Executes a sequence of franchise perspective analysis.",
)

# -- Sequential Agent: Dynamic Perspective --
first_dynamic_agent = SequentialAgent(
    name="DynamicPerspectiveAgent",
    sub_agents=[
        first_dynamic_perspective_detection_agent, 
        first_dynamic_perspective_agent,
        content_analyst_for_firstdynamic,
        first_dynamic_view_uploader_agent,
    ],
    description="Executes a sequence of dynamic perspective detection and analysis.",
)

second_dynamic_agent = SequentialAgent(
    name="SecondDynamicPerspectiveAgent",
    sub_agents=[
        second_dynamic_perspective_detection_agent, 
        second_dynamic_perspective_agent,
        content_analyst_for_seconddynamic,
        second_dynamic_view_uploader_agent,
    ],
    description="Executes a sequence of dynamic perspective detection and analysis.",
)

# three60_agent = SequentialAgent(
#     name="Three60Agent",
#     sub_agents=[
#         player_agent, 
#         coach_agent, 
#         team_agent, 
#         dynamic_agent, 
#     ],
#     description="Runs multiple agents to create a comprehensive 360-degree view."
# )

#--------------------------------------------------------------------------
# Loop Agent
#--------------------------------------------------------------------------

"""Loop Agent to iterate through the workflow for fetching and processing cluster data."""

cluster_agent = LoopAgent(
    name="cluster_agent",
    max_iterations=1,
    sub_agents=[
        fetch_context_agent, 
        summary_agent,
        #timeline_agent,
        player_agent,
        coach_agent,
        team_agent,
        franchise_agent,
        first_dynamic_agent,
        second_dynamic_agent,
        close_cluster_id_agent
    ]
)

#--------------------------------------------------------------------------
# Root Agent
#--------------------------------------------------------------------------

root_agent = cluster_agent

#--------------------------------------------------------------------------
# Expose agency
#--------------------------------------------------------------------------

# Instantiate constants
APP_NAME = "cluster_agency_app"
USER_ID = "BigSlikTobi"
SESSION_ID = "001"

# Session and Runner
session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
)
runner = Runner(
    agent=root_agent, app_name=APP_NAME, session_service=session_service
)

def call_agent(query):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    for event in events:
        if event.content and event.content.parts:
            final_response = event.content.parts[0].text
            print("Agent Response:", final_response)


call_agent("Start the process.")