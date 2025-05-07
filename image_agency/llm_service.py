import os
import traceback
import google.generativeai as genai
import json
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv

from config import (
    LLM_MODEL_NAME,
    MAX_ARTICLE_CHARS_FOR_LLM_QUERY_GEN,
    MAX_ARTICLE_CHARS_FOR_LLM_SELECTION,
    DESIRED_MIN_WIDTH,
    DESIRED_MIN_HEIGHT
)

class LLMService:
    def __init__(self):
        """Initialize the LLM service with Google Generative AI"""
        load_dotenv()
        self.llm_model = None
        google_api_key = os.environ.get("GEMINI_API_KEY")
        
        if google_api_key:
            try:
                genai.configure(api_key=google_api_key)
                self.llm_model = genai.GenerativeModel(LLM_MODEL_NAME)
                print(f"Successfully initialized LLM: {LLM_MODEL_NAME}")
            except Exception as e:
                print(f"ERROR: Failed to initialize LLM ({LLM_MODEL_NAME}): {e}. LLM features unavailable.")
        else:
            print("WARNING: GEMINI_API_KEY not set. LLM features will be disabled.")
    
    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        return self.llm_model is not None
        
    def generate_search_query(self, article_content: str) -> Optional[str]:
        """Generate an image search query from article content.
        
        Args:
            article_content: The article content to analyze
            
        Returns:
            A search query string or None if generation failed
        """
        if not self.is_available():
            return None
            
        print("Generating search query with LLM...")
        truncated_content = article_content[:MAX_ARTICLE_CHARS_FOR_LLM_QUERY_GEN]
        prompt = f"""
        Analyze the following article text and generate a concise, effective image search query (3-7 words)
        suitable for finding a single, compelling, representative main image for the article.
        Focus on visually descriptive terms.

        Article Text:
        ---
        {truncated_content}
        ---

        Output only the generated search query, and nothing else. For example: "red cat jumping"
        Search Query:
        """
        
        try:
            safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in [
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            response = self.llm_model.generate_content(prompt, safety_settings=safety_settings)
            if response.parts:
                generated_query = response.text.strip()
                if generated_query.lower().startswith("search query:"):
                    generated_query = generated_query.split(":", 1)[1].strip()
                generated_query = generated_query.replace('"', '').replace("'", "").strip()
                if not generated_query:
                    print("LLM generated an empty query.")
                    return None
                print(f"LLM generated search query: '{generated_query}'")
                return generated_query
            else:
                print("LLM response for query generation was empty or blocked.")
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     print(f"LLM Prompt Feedback: Blocked due to {response.prompt_feedback.block_reason_message}")
                return None
        except Exception as e:
            print(f"Error during LLM query generation: {e}\n{traceback.format_exc()}")
            return None
    
    def select_best_image(self, image_candidates: List[Dict[str, Any]], article_snippet: str, 
                         search_query: str) -> Optional[Dict[str, Any]]:
        """Select the best image from candidates using LLM.
        
        Args:
            image_candidates: List of image candidate objects
            article_snippet: A snippet of the article for context
            search_query: Original search query used
            
        Returns:
            The selected image object or None if selection failed
        """
        if not self.is_available():
            print("LLM not available for image selection.")
            return None
            
        if not image_candidates:
            print("No image candidates to select from.")
            return None

        print(f"Presenting {len(image_candidates)} candidates to LLM for final selection...")

        candidates_text_list = []
        for i, candidate in enumerate(image_candidates):
            candidates_text_list.append(
                f"{i+1}. Title: \"{candidate.get('title', 'N/A')}\"\n"
                f"   URL: \"{candidate.get('url')}\"\n"
                f"   Dimensions: {candidate.get('width', 'N/A')}x{candidate.get('height', 'N/A')}"
            )
        candidates_prompt_str = "\n\n".join(candidates_text_list)

        prompt = f"""
        You are an expert image curator. Your task is to select the single best image from the provided list to be the main visual for an article.

        Article Snippet:
        ---
        {article_snippet[:MAX_ARTICLE_CHARS_FOR_LLM_SELECTION]}
        ---

        Original Search Query Used: "{search_query}"

        Desirable Image Characteristics:
        - Highly relevant to the article snippet and search query.
        - Visually appealing and engaging.
        - Good quality (e.g., clear, not pixelated, not an icon unless specifically relevant).
        - Prefer landscape orientation (width greater than height).
        - Ideal dimensions around {DESIRED_MIN_WIDTH}x{DESIRED_MIN_HEIGHT} pixels or larger, but relevance is key.

        Image Candidates:
        ---
        {candidates_prompt_str}
        ---

        Instructions:
        Carefully review each candidate. Choose the one that best fits the criteria.
        Output your response in JSON format with two keys:
        1. "selected_image_index": The 1-based index of the image you selected from the list above (e.g., 1, 2, 3, ...).
        2. "justification": A brief (1-2 sentences) explanation for your choice.

        If absolutely none of the candidates are suitable, output:
        {{
          "selected_image_index": null,
          "justification": "None of the provided candidates were suitable because [brief reason]."
        }}

        Example of a good selection:
        {{
          "selected_image_index": 2,
          "justification": "Candidate 2's title and dimensions suggest it's a relevant and high-quality photograph directly related to the article's main subject."
        }}
        """
        
        try:
            safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in [
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
            response = self.llm_model.generate_content(prompt, safety_settings=safety_settings, generation_config=generation_config)

            if response.parts:
                llm_output_text = response.text.strip()
                try:
                    parsed_json = json.loads(llm_output_text)
                    selected_index_0_based = None
                    if parsed_json.get("selected_image_index") is not None:
                        selected_index_0_based = int(parsed_json["selected_image_index"]) - 1 # Convert 1-based to 0-based
                    
                    justification = parsed_json.get("justification", "No justification provided.")
                    print(f"LLM Selection Justification: {justification}")

                    if selected_index_0_based is not None and 0 <= selected_index_0_based < len(image_candidates):
                        selected_image = image_candidates[selected_index_0_based]
                        print(f"LLM selected image at index {selected_index_0_based+1}: '{selected_image.get('title', 'N/A')[:50]}...'")
                        return selected_image
                    else:
                        if selected_index_0_based is not None: # Index was out of bounds
                             print(f"LLM selected an invalid index: {selected_index_0_based+1}. No image chosen.")
                        else: # Index was null
                             print("LLM indicated no suitable image was found among candidates.")
                        return None
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    print(f"LLM Selection: Failed to parse JSON or invalid content: {e}")
                    print(f"LLM Raw Output: {llm_output_text}")
                    return None
            else:
                print("LLM response for image selection was empty or blocked.")
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     print(f"LLM Prompt Feedback: Blocked due to {response.prompt_feedback.block_reason_message}")
                return None
        except Exception as e:
            print(f"Error during LLM image selection: {e}\n{traceback.format_exc()}")
            return None