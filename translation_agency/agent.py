from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import google_search
from litellm import completion
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from .utils import load_instruction_from_file
from .tools import fetch_untranslated_articles_with_cluster, fetch_untranslated_articles_by_id, write_to_database, mark_article_as_translated

import os
from dotenv import load_dotenv

#--------------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key  
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

#--------------------------------------------------------------------------
# Agent definitions 
# -------------------------------------------------------------------------

# --- Sub Agent 1: Article Controller ---
article_controller_agent = LlmAgent(
    name="ArticleController",
    model="gemini-2.0-flash-lite",  # This can now be easily changed to other models via LiteLLM
    instruction=load_instruction_from_file("article_controller_instructions.txt"),
    tools=[fetch_untranslated_articles_with_cluster],
    output_key="untranslated_articles",  # Save result to state
)

# --- Sub Agent 2: Content Fetcher ---
content_fetcher_agent = LlmAgent(
    name="ContentFetcher",
    model="gemini-2.0-flash",
    instruction=load_instruction_from_file("content_fetcher_instruction.txt"),
    tools=[fetch_untranslated_articles_by_id],
    output_key="generated_content",  # Save result to state
)

# --- Sub Agent 2b: Content cleaner ---
content_cleaner_agent = LlmAgent(
    name="ContentCleaner",
    model="gemini-2.5-flash-preview-04-17",
    instruction=load_instruction_from_file("content_cleaner_instruction.txt"),
    description="cleans content for further processing.",
    output_key="cleaned_content",  # Save result to state
)

# --- Sub Agent 3: German Translator ---
german_agent = LlmAgent(
    name="GermanTranslator",
    model="gemini-2.0-flash",
    instruction=load_instruction_from_file("german_translator_instruction.txt"),
    description="Generates translations from English to German.",
    output_key="german_content",  # Save result to state
)

# # --- Sub Agent 4: France Translator ---
# france_agent = LlmAgent(
#     name="FranceTranslator",
#     model="gemini-2.0-flash-001",
#     instruction=load_instruction_from_file("france_translator_instruction.txt"),
#     description="Generates translations from English to French.",
#     output_key="france_content",
# )

# # --- Sub Agent 5: Spanish Translator ---
# spanish_agent = LlmAgent(
#     name="SpanishTranslator",
#     model="gemini-2.0-flash-001",
#     instruction=load_instruction_from_file("spanish_translator_instruction.txt"),
#     description="Generates translations from English to Spanish.",
#     output_key="spanish_content",
# )

# # --- Sub Agent 6: Portuguese Translator ---
# portuguese_agent = LlmAgent(
#     name="PortugueseTranslator",
#     model="gemini-2.0-flash-001",
#     instruction=load_instruction_from_file("portuguese_translator_instruction.txt"),
#     description="Generates translations from English to Portuguese.",
#     output_key="portuguese_content",
# )

# --- Sub Agent 7: Database Writer ---
database_writer_agent = LlmAgent(
    name="DatabaseWriter",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("database_writer_instruction.txt"),
    tools=[write_to_database],
    output_key="article_id",  # Save result to state
)

# --- Sub Agent 8: Database Clean Up ---
database_clean_up_agent = LlmAgent(
    name="DatabaseCleanUp",
    model="gemini-2.0-flash-lite",
    instruction=load_instruction_from_file("database_clean_up_instruction.txt"),
    tools=[mark_article_as_translated],
    output_key="response",  # Save result to state
)

# --- Loop Agent Workflow ---
translation_agent = LoopAgent(
    name="translation_agent",
    max_iterations=2,
    sub_agents=[article_controller_agent, content_fetcher_agent, content_cleaner_agent, german_agent, database_writer_agent, database_clean_up_agent]
)

# --- Root Agent for the Runner ---
# The runner will now execute the workflow
root_agent = translation_agent

#--------------------------------------------------------------------------
# Make the agency programmatically runnable.
#--------------------------------------------------------------------------

# Instantiate constants
APP_NAME = "translation_agency_app"
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

# Agent Interaction
def call_agent(query):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    for event in events:
        if event.content and event.content.parts:
            final_response = event.content.parts[0].text
            print("Agent Response:", final_response)


call_agent("Start the process of translating the articles.")