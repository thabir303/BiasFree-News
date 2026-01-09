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
from app.utils.toon_formatter import toon_formatter

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
        response_format: Optional[str] = "json_object",
        dynamic_max_tokens: bool = True
    ) -> str:
        """
        Generic OpenAI API call with error handling.
        Uses chat.completions.create() for gpt-5-nano without temperature parameter.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User query/content
            response_format: Expected response format (json_object or text)
            dynamic_max_tokens: If True, calculate max_tokens based on input length
        
        Returns:
            API response content as string
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Calculate dynamic max_tokens based on input length
            if dynamic_max_tokens:
                # Estimate input tokens (rough: 1 token ≈ 4 chars for English, ≈ 2-3 for Bengali)
                total_input_chars = len(system_prompt) + len(user_prompt)
                estimated_input_tokens = total_input_chars // 2  # Conservative estimate for Bengali
                
                # For debiasing with 2000 char content, we need ~2500-3000 tokens for output
                if "Rewrite this Bengali article" in system_prompt or "debiased_content" in system_prompt:
                    # Debiasing: 2000 chars ≈ 1000 tokens, plus JSON overhead
                    calculated_max_tokens = min(4000, self.max_tokens)  # Fixed cap for 2000 char content
                else:
                    # Bias detection and headline generation need less
                    calculated_max_tokens = min(2000, self.max_tokens)
                
                max_completion_tokens = calculated_max_tokens
                logger.info(f"Dynamic token calculation: input_chars={total_input_chars}, "
                          f"max_completion_tokens={max_completion_tokens}")
            else:
                max_completion_tokens = self.max_tokens
            
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
                kwargs["max_completion_tokens"] = max_completion_tokens
            else:
                kwargs["max_tokens"] = max_completion_tokens
            
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
        Detect bias in Bengali article using cost-optimized prompts with TOON format.
        
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
        
        # Truncate content to 2000 characters for consistency
        truncated_content = content[:2000] if len(content) > 2000 else content
        
        # Use TOON format for input data to reduce tokens by 30-60%
        article_data = {
            "title": title if title else "N/A",
            "content": truncated_content
        }
        toon_input = toon_formatter.to_toon(article_data)
        
        user_prompt = f"""Article data (TOON format for efficiency):
```toon
{toon_input}
```

Analyze for bias and respond in JSON."""
        
        logger.info(f"Using TOON format - Original size: ~{len(title or '') + len(truncated_content)} chars, TOON size: {len(toon_input)} chars")
        
        response = await self._call_api(system_prompt, user_prompt, "json_object", dynamic_max_tokens=False)
        
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
        Debias article content by replacing biased terms with neutral alternatives.
        Uses programmatic replacement for reliability.
        
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
        
        # Perform programmatic replacement for reliability
        debiased_content = content
        changes = []
        
        for term in biased_terms[:10]:  # Limit to 10 terms
            original_term = term.get("term", "")
            neutral_term = term.get("neutral_alternative", "")
            reason = term.get("reason", "Biased term replaced")
            
            if original_term and neutral_term and original_term in debiased_content:
                # Replace the term
                debiased_content = debiased_content.replace(original_term, neutral_term)
                changes.append({
                    "original": original_term,
                    "debiased": neutral_term,
                    "reason": reason
                })
                logger.debug(f"Replaced '{original_term}' with '{neutral_term}'")
        
        logger.info(f"Programmatic debiasing: {len(changes)} changes made")
        
        return {
            "debiased_content": debiased_content,
            "changes": changes
        }
    
    async def generate_headline(self, content: str, original_title: Optional[str] = None) -> Dict:
        """
        Generate neutral, factual headline for Bengali article using TOON format.
        
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
        
        # Use TOON format for input data
        article_data = {
            "original_title": original_title if original_title else "না দেওয়া হয়নি",
            "content": truncated_content
        }
        toon_input = toon_formatter.to_toon(article_data)
        
        user_prompt = f"""Article data (TOON format):
```toon
{toon_input}
```

Generate 3 neutral Bengali headlines."""
        
        logger.info(f"Using TOON format for headline generation")
        
        response = await self._call_api(system_prompt, user_prompt, "json_object", dynamic_max_tokens=False)
        
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
