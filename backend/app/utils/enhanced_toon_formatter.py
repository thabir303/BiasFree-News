"""
Enhanced TOON (Token-Oriented Object Notation) formatter for LLM prompts.
Based on the GitHub library: https://github.com/meetrais/JSON-to-TOON
Reduces token usage by 30-60% compared to JSON.
"""

from typing import Any, Dict, List, Optional, Union
import json
from py_toon_format import encode, decode


class EnhancedToonFormatter:
    """Enhanced TOON formatter with GitHub library integration and LLM optimization."""
    
    def __init__(self, delimiter: str = ",", indent: int = 2, use_tabular: bool = True):
        """
        Initialize enhanced TOON formatter.
        
        Args:
            delimiter: Delimiter for arrays (default: ",")
            indent: Indentation spaces (default: 2)
            use_tabular: Use tabular format for arrays (more efficient)
        """
        self.delimiter = delimiter
        self.indent = indent
        self.use_tabular = use_tabular
    
    def to_toon(self, data: Any, use_length_marker: bool = False) -> str:
        """
        Convert Python data to TOON format using the GitHub library.
        
        Args:
            data: Python dict, list, or primitive to convert
            use_length_marker: Add # prefix to array lengths for validation
            
        Returns:
            TOON-formatted string
        """
        try:
            # Use the py-toon-format library for encoding
            toon_data = encode(data)
            
            # Add length markers if requested
            if use_length_marker and isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        # Add length marker before the key
                        toon_data = toon_data.replace(f"{key}[", f"{key}[#{len(value)}]")
            
            return toon_data
        except Exception as e:
            # Fallback to manual conversion if library fails
            logger.warning(f"TOON library failed, using fallback: {str(e)}")
            return self._fallback_to_toon(data)
    
    def from_toon(self, toon_str: str) -> Any:
        """
        Parse TOON format back to Python data using the GitHub library.
        
        Args:
            toon_str: TOON-formatted string
            
        Returns:
            Python dict, list, or primitive
        """
        try:
            return decode(toon_str)
        except Exception as e:
            logger.warning(f"TOON library decode failed, using fallback: {str(e)}")
            return self._fallback_from_toon(toon_str)
    
    def _fallback_to_toon(self, data: Any) -> str:
        """Fallback TOON conversion when library fails."""
        if isinstance(data, dict):
            items = []
            for key, value in data.items():
                if isinstance(value, str):
                    items.append(f"{key}={value}")
                elif isinstance(value, list):
                    # Handle arrays in tabular format
                    if self.use_tabular and value and all(isinstance(item, dict) for item in value):
                        # Tabular format: declare keys once, stream values
                        if value:
                            keys = list(value[0].keys())
                            items.append(f"{key}[{len(value)}]{{{','.join(keys)}}}:")
                            for item in value:
                                values = [str(item.get(k, "")) for k in keys]
                                items.append(f"  {','.join(values)}")
                    else:
                        items.append(f"{key}={str(value)}")
                else:
                    items.append(f"{key}={str(value)}")
            return "\n".join(items)
        elif isinstance(data, list):
            return self.delimiter.join(str(item) for item in data)
        else:
            return str(data)
    
    def _fallback_from_toon(self, toon_str: str) -> Any:
        """Fallback TOON parsing when library fails."""
        lines = toon_str.strip().split('\n')
        result = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '=' in line:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip()
            elif ':' in line and '[' in line:
                # Handle tabular format
                # Format: key[count]{keys}:
                #   value1,value2,value3
                pass
        
        return result if result else toon_str
    
    def format_article_batch_tabular(self, articles: List[Dict[str, Any]], max_articles: int = 20) -> str:
        """
        Format multiple articles in optimized tabular TOON format.
        
        Args:
            articles: List of article dictionaries
            max_articles: Maximum number of articles (default: 20)
            
        Returns:
            TOON-formatted batch with tabular arrays for maximum efficiency
        """
        # Limit to max_articles
        articles = articles[:max_articles]
        
        if not articles:
            return "articles[0]{}:"
        
        # Use tabular format for maximum token efficiency
        # Format: articles[count]{field1,field2,field3}:
        #   value1,value2,value3
        #   value1,value2,value3
        
        # Define consistent fields for all articles
        fields = ["id", "title", "source", "content", "date"]
        
        # Prepare tabular data
        tabular_lines = [f"articles[{len(articles)}]{{{','.join(fields)}}}:"]
        
        for article in articles:
            # Extract values in consistent order
            values = [
                str(article.get("id", "")),
                article.get("title", "")[:100],  # Truncate title for efficiency
                article.get("source", ""),
                article.get("content", "")[:200],  # Truncate content for efficiency
                article.get("date", "")
            ]
            
            # Escape any commas in values
            escaped_values = [v.replace(',', ';') for v in values]
            tabular_lines.append(f"  {','.join(escaped_values)}")
        
        return "\n".join(tabular_lines)
    
    def format_bias_analysis_prompt(self, articles_data: str) -> str:
        """
        Create optimized bias analysis prompt with TOON format.
        
        Args:
            articles_data: TOON-formatted articles data
            
        Returns:
            Complete prompt for LLM bias analysis
        """
        system_prompt = """You are a bias detection expert for news articles. Analyze the provided articles and respond with JSON containing bias analysis for each article.

Key bias indicators:
- Politically charged language
- Emotional manipulation
- Sensationalism
- One-sided framing
- Loaded words

Response format:
{
  "articles": [
    {
      "id": "article_id",
      "is_biased": boolean,
      "bias_score": 0-100,
      "biased_terms": [{"term": "word", "reason": "explanation", "neutral_alternative": "word"}],
      "summary": "analysis summary"
    }
  ]
}"""

        user_prompt = f"""Analyze these {articles_data.split('[')[1].split(']')[0] if '[' in articles_data else 'articles'} articles for bias:

Input data is provided in TOON format (Token-Oriented Object Notation) for 30-60% token reduction:
```toon
{articles_data}
```

Provide bias analysis in JSON format."""

        return system_prompt, user_prompt
    
    def format_single_article_for_bias(self, article: Dict[str, Any]) -> str:
        """
        Format single article for bias detection with maximum efficiency.
        
        Args:
            article: Article dictionary
            
        Returns:
            TOON-formatted article data
        """
        # Extract only essential fields for bias detection
        article_data = {
            "title": article.get("title", "")[:200],  # Limit title length
            "content": article.get("content", "")[:2000],  # Limit content to 2000 chars
            "source": article.get("source", ""),
        }
        
        # Add optional fields if present and relevant
        if article.get("author"):
            article_data["author"] = article.get("author", "")[:100]
        
        if article.get("published_date"):
            article_data["date"] = article.get("published_date", "")
        
        return self.to_toon(article_data)
    
    def calculate_token_savings(self, original_data: Any, toon_data: str) -> Dict[str, Any]:
        """
        Calculate token savings achieved by using TOON format.
        
        Args:
            original_data: Original data in JSON format
            toon_data: Converted TOON data
            
        Returns:
            Token savings statistics
        """
        # Estimate tokens (rough approximation)
        # JSON: ~1 token per 4 characters
        # TOON: ~1 token per 2-3 characters (more efficient)
        
        original_json = json.dumps(original_data, separators=(',', ':'))
        original_chars = len(original_json)
        toon_chars = len(toon_data)
        
        # Estimated token counts
        original_tokens = original_chars // 4
        toon_tokens = toon_chars // 2.5  # TOON is more token-efficient
        
        savings = max(0, original_tokens - toon_tokens)
        savings_percent = (savings / original_tokens * 100) if original_tokens > 0 else 0
        
        return {
            "original_chars": original_chars,
            "toon_chars": toon_chars,
            "original_tokens": original_tokens,
            "toon_tokens": toon_tokens,
            "token_savings": savings,
            "savings_percent": round(savings_percent, 1)
        }


# Enhanced singleton instance
enhanced_toon_formatter = EnhancedToonFormatter()


def format_articles_for_llm(articles: List[Dict[str, Any]], max_articles: int = 20) -> str:
    """
    Quick helper to format articles for LLM analysis with TOON.
    
    Args:
        articles: List of article dictionaries
        max_articles: Maximum number of articles (default: 20)
        
    Returns:
        TOON-formatted articles ready for LLM prompt
    """
    return enhanced_toon_formatter.format_article_batch_tabular(articles, max_articles)


def create_bias_detection_prompt(article_data: str) -> tuple[str, str]:
    """
    Create optimized bias detection prompt with TOON format.
    
    Args:
        article_data: TOON-formatted article data
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return enhanced_toon_formatter.format_bias_analysis_prompt(article_data)