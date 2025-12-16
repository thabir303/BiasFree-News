"""
OpenAI API service with optimized cost-effective prompt engineering.
Uses GPT-4o-nano for efficient bias detection and content processing.
"""
import json
import logging
import re
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Service for interacting with OpenAI API.
    Optimized for cost-effectiveness with GPT-4o-nano.
    """
    
    def __init__(self):
        """Initialize OpenAI client with API key from settings."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
    
    def _extract_json(self, response: str) -> str:
        """
        Extract JSON from response that might be wrapped in markdown or have extra text.
        Also attempts to fix truncated JSON.
        
        Args:
            response: Raw response from OpenAI
        
        Returns:
            Clean JSON string
        """
        if not response:
            logger.warning("Empty response received from API")
            return "{}"
        
        original_response = response
        response = response.strip()
            
        # First, try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            logger.debug("Extracted JSON from markdown code block")
            return json_match.group(1).strip()
        
        # Try to find complete JSON object
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            extracted = json_match.group(0).strip()
            # Verify it's actually valid JSON
            try:
                json.loads(extracted)
                return extracted
            except json.JSONDecodeError:
                logger.debug("Found JSON-like structure but it's invalid, trying to repair")
        
        # Handle truncated JSON - if response starts with { but doesn't end properly
        if response.startswith('{'):
            truncated = response
            
            # Remove any trailing incomplete content after last complete value
            # This handles cases like: {"key": "val", "key2": "incompl
            
            # Count open braces and brackets
            open_braces = truncated.count('{') - truncated.count('}')
            open_brackets = truncated.count('[') - truncated.count(']')
            
            # If we have unclosed structures, try to close them
            if open_braces > 0 or open_brackets > 0:
                # Check if we're inside a string (uneven quotes)
                if truncated.count('"') % 2 == 1:
                    truncated += '"'
                # Close any open arrays
                truncated += ']' * open_brackets
                # Close any open objects
                truncated += '}' * open_braces
                
                logger.info(f"Repaired truncated JSON (closed {open_braces} braces, {open_brackets} brackets)")
                return truncated
        
        # If nothing found, return empty JSON
        logger.warning(f"Could not extract JSON from response: {original_response[:200]}...")
        return "{}"
    
    async def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[str] = "json_object"
    ) -> str:
        """
        Generic OpenAI API call with error handling.
        Uses chat.completions.create() for gpt-5-nano without temperature parameter.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User query/content
            response_format: Expected response format (json_object or text)
        
        Returns:
            API response content as string
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
            }
            
            # gpt-5-nano doesn't support temperature parameter, use default (1)
            # Only add temperature for models that support it
            if "gpt-5" not in self.model.lower():
                kwargs["temperature"] = self.temperature
            
            # Use max_completion_tokens for newer models (gpt-4o, gpt-5), max_tokens for older
            if any(prefix in self.model.lower() for prefix in ["gpt-4o", "gpt-5", "o1"]):
                kwargs["max_completion_tokens"] = self.max_tokens
            else:
                kwargs["max_tokens"] = self.max_tokens
            
            # Add response_format for models that support it (gpt-4o, gpt-4o-mini, gpt-4-turbo)
            # Note: gpt-5-nano may not support this, so only add for gpt-4 series
            if response_format == "json_object" and "gpt-4" in self.model.lower():
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            
            # Log token usage and finish reason for debugging
            if hasattr(response, 'usage'):
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                logger.info(
                    f"OpenAI API call - Tokens: {response.usage.total_tokens} "
                    f"(prompt: {response.usage.prompt_tokens}, "
                    f"completion: {response.usage.completion_tokens}) "
                    f"finish_reason: {finish_reason}"
                )
                
                # Warn if response was cut off due to length
                if finish_reason == "length":
                    logger.warning("Response was truncated due to max_tokens limit!")
            
            # Handle None or empty content
            if content is None:
                logger.warning("API returned None content")
                return ""
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def detect_bias(self, content: str, title: Optional[str] = None) -> Dict:
        """
        Detect bias in Bengali article using cost-optimized prompts.
        
        Args:
            content: Article content in Bengali
            title: Optional article title
        
        Returns:
            Structured bias analysis with biased terms and severity
        """
        # Optimized system prompt
        system_prompt = """You are a bias detection expert for Bengali news articles. Analyze the article and respond ONLY with valid JSON.

JSON structure:
{
  "is_biased": boolean,
  "bias_score": number (0-100),
  "biased_terms": [
    {
      "term": "biased word",
      "reason": "explanation",
      "neutral_alternative": "neutral word",
      "severity": "low/medium/high"
    }
  ],
  "summary": "analysis summary",
  "confidence": number (0.0-1.0)
}

Look for: politically charged language, emotional manipulation, sensationalism, one-sided framing."""
        
        # Truncate content to control costs (first 1500 chars usually sufficient)
        truncated_content = content[:1500] if len(content) > 1500 else content
        
        user_prompt = f"""Title: {title if title else 'N/A'}

Content: {truncated_content}

Analyze for bias."""
        
        response = await self._call_api(system_prompt, user_prompt, "json_object")
        
        try:
            # Extract JSON from response (handles markdown wrapping)
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse bias detection response. Error: {str(e)}. Raw response: {response[:500]}...")
            # Fallback response
            return {
                "is_biased": False,
                "bias_score": 0.0,
                "biased_terms": [],
                "summary": "Analysis failed - JSON parsing error",
                "confidence": 0.0
            }
    
    async def debias_content(self, content: str, biased_terms: List[Dict]) -> Dict:
        """
        Debias article content with surgical precision.
        Only replaces identified biased terms to minimize token usage.
        
        Args:
            content: Original article content
            biased_terms: List of biased terms with neutral alternatives
        
        Returns:
            Debiased content with change tracking
        """
        if not biased_terms:
            return {
                "debiased_content": content,
                "changes": []
            }
        
        # Provide specific replacements
        terms_list = "\n".join([
            f"{i+1}. Replace '{term['term']}' with '{term['neutral_alternative']}'"
            for i, term in enumerate(biased_terms[:10])
        ])
        
        system_prompt = f"""You are a content editor. Rewrite this Bengali article by replacing biased terms with neutral alternatives. Respond ONLY with valid JSON.

Replacements needed:
{terms_list}

JSON structure:
{{
  "debiased_content": "full rewritten article",
  "changes": [
    {{"original": "biased term", "debiased": "neutral term", "reason": "explanation"}}
  ]
}}"""
        
        user_prompt = f"Article:\n\n{content}"
        
        response = await self._call_api(system_prompt, user_prompt, "json_object")
        
        try:
            # Extract JSON from response (handles markdown wrapping)
            json_str = self._extract_json(response)
            parsed = json.loads(json_str)
            logger.info(f"Debiasing successful: {len(parsed.get('changes', []))} changes made")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse debias response. Error: {str(e)}. Raw response: {response[:500]}...")
            return {
                "debiased_content": content,
                "changes": []
            }
    
    async def generate_headline(self, content: str, original_title: Optional[str] = None) -> Dict:
        """
        Generate neutral, factual headline for Bengali article.
        
        Args:
            content: Article content
            original_title: Original headline (for comparison)
        
        Returns:
            Generated headlines with reasoning
        """
        # Use first 800 chars for headline generation
        truncated_content = content[:800]
        
        system_prompt = """You are a headline writer for Bengali news. Generate 3 neutral, unbiased headlines. Respond ONLY with valid JSON.

JSON structure:
{
  "headlines": ["headline 1 in Bengali", "headline 2 in Bengali", "headline 3 in Bengali"],
  "recommended": "best headline from the list",
  "reasoning": "why this headline is best"
}

Guidelines:
- Headlines should be neutral and factual
- Avoid sensationalism and emotional language
- Keep headlines under 20 words
- Write in Bengali"""
        
        user_prompt = f"""Original Title: {original_title if original_title else 'না দেওয়া হয়নি'}

Article Content:
{truncated_content}

Generate 3 neutral Bengali headlines."""
        
        response = await self._call_api(system_prompt, user_prompt, "json_object")
        
        # Log raw response for debugging
        logger.debug(f"Headline raw response: {response[:300]}...")
        
        try:
            # Extract JSON from response (handles markdown wrapping)
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            headlines = data.get("headlines", [])
            
            # Validate we got headlines
            if not headlines or len(headlines) == 0:
                logger.warning(f"No headlines in parsed response. Data: {data}")
                # Create fallback headlines based on original title or content
                fallback_headline = original_title if original_title else truncated_content[:50] + "..."
                return {
                    "generated_headlines": [fallback_headline],
                    "recommended_headline": fallback_headline,
                    "reasoning": "Auto-generated fallback"
                }
            
            logger.info(f"Headlines generated: {len(headlines)} options")
            return {
                "generated_headlines": headlines,
                "recommended_headline": data.get("recommended", headlines[0] if headlines else ""),
                "reasoning": data.get("reasoning", "")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse headline response. Error: {str(e)}. Raw response: {response[:500]}...")
            fallback_headline = original_title if original_title else "শিরোনাম তৈরি করা সম্ভব হয়নি"
            return {
                "generated_headlines": [fallback_headline],
                "recommended_headline": fallback_headline,
                "reasoning": "JSON parsing error - using fallback"
            }
