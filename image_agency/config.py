# Configuration constants for image agency services

# Article configuration - Legacy single table config
ARTICLE_TABLE_NAME = "cluster_summary"
ARTICLE_ID_COLUMN = "id"
ARTICLE_CONTENT_COLUMN = "content"

# Multi-table configuration
TABLES_FOR_IMAGES = {
    "cluster_coach_view": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"},
    "cluster_dynamic_view": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"},
    "cluster_franchise_view": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"},
    "cluster_player_view": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"},
    "cluster_team_view": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"},
    "cluster_summary": {"id_column": "id", "content_column": "content", "has_image_column": "hasImage"}
}

# LLM configuration
LLM_MODEL_NAME = "gemini-1.5-flash-latest"
MAX_ARTICLE_CHARS_FOR_LLM_QUERY_GEN = 15000  # For generating search query
MAX_ARTICLE_CHARS_FOR_LLM_SELECTION = 4000   # For image selection prompt
CANDIDATES_TO_LLM_FOR_SELECTION = 7          # How many image candidates to present to LLM for final choice

# Image search configuration
MIN_DDGS_IMAGE_DIMENSION = 100  # Minimal heuristic: smallest dimension for a DDGS result to be considered

# Image preferences
DESIRED_MIN_WIDTH = 1200
DESIRED_MIN_HEIGHT = 400

# Domain blacklist for image sources
BLACKLISTED_DOMAINS = [
    'lookaside.instagram.com',
    'gettyimages.com',
    'shutterstock.com', 
    'istockphoto.com',
    'tiktok.com/',
    'fanatics.com',
    'static.nike.com'
]