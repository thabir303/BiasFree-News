"""
TOON (Token-Oriented Object Notation) formatter for LLM prompts.
Reduces token usage by 30-60% compared to JSON.
"""

from typing import Any, Dict, List, Optional
from toon import encode, decode, EncodeOptions


class ToonFormatter:
    """Utility class for formatting data in TOON format for LLM prompts."""
    
    def __init__(self, delimiter: str = ",", indent: int = 2):
        """
        Initialize TOON formatter.
        
        Args:
            delimiter: Delimiter for arrays (default: ",")
            indent: Indentation spaces (default: 2)
        """
        self.delimiter = delimiter
        self.indent = indent
    
    def to_toon(self, data: Any, use_length_marker: bool = False) -> str:
        """
        Convert Python data to TOON format.
        
        Args:
            data: Python dict, list, or primitive to convert
            use_length_marker: Add # prefix to array lengths for validation
            
        Returns:
            TOON-formatted string
        """
        options: EncodeOptions = {
            "indent": self.indent,
            "delimiter": self.delimiter,
            "lengthMarker": "#" if use_length_marker else False,
        }
        return encode(data, options)
    
    def from_toon(self, toon_str: str) -> Any:
        """
        Parse TOON format back to Python data.
        
        Args:
            toon_str: TOON-formatted string
            
        Returns:
            Python dict, list, or primitive
        """
        return decode(toon_str)
    
    def format_article_for_bias_detection(self, article: Dict[str, Any]) -> str:
        """
        Format article data in TOON for bias detection prompt.
        
        Args:
            article: Article dictionary with fields like title, content, etc.
            
        Returns:
            TOON-formatted article data
        """
        # Extract relevant fields for bias detection
        article_data = {
            "title": article.get("title", ""),
            "content": article.get("content", ""),
            "source": article.get("source", ""),
        }
        
        # Add optional fields if present
        if article.get("author"):
            article_data["author"] = article["author"]
        
        return self.to_toon(article_data)
    
    def format_articles_batch(self, articles: List[Dict[str, Any]]) -> str:
        """
        Format multiple articles in tabular TOON format.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            TOON-formatted batch with tabular arrays for efficiency
        """
        # Prepare articles with consistent fields
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "id": article.get("id", ""),
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "content": article.get("content", "")[:500] if article.get("content") else "",  # Truncate for batch
            })
        
        return self.to_toon({"articles": formatted_articles}, use_length_marker=True)
    
    def format_bias_result(self, result: Dict[str, Any]) -> str:
        """
        Format bias detection result in TOON.
        
        Args:
            result: Bias detection result dictionary
            
        Returns:
            TOON-formatted result
        """
        return self.to_toon(result)
    
    def create_prompt_with_toon(
        self,
        instruction: str,
        data: Any,
        output_format: str = "JSON",
        use_code_block: bool = True
    ) -> str:
        """
        Create an LLM prompt with TOON-formatted data.
        
        Args:
            instruction: Instruction text for the LLM
            data: Data to include in TOON format
            output_format: Expected output format (default: "JSON")
            use_code_block: Wrap TOON in markdown code block
            
        Returns:
            Complete prompt string
        """
        toon_data = self.to_toon(data)
        
        if use_code_block:
            toon_section = f"```toon\n{toon_data}\n```"
        else:
            toon_section = toon_data
        
        prompt = f"""{instruction}

Input data is provided in TOON format (Token-Oriented Object Notation) for efficiency:
{toon_section}

Please respond in {output_format} format."""
        
        return prompt


# Singleton instance for easy import
toon_formatter = ToonFormatter()


def format_for_llm(data: Any, instruction: str, output_format: str = "JSON") -> str:
    """
    Quick helper to format data with instruction for LLM.
    
    Args:
        data: Data to format in TOON
        instruction: Instruction for the LLM
        output_format: Expected output format
        
    Returns:
        Complete prompt with TOON data
    """
    return toon_formatter.create_prompt_with_toon(instruction, data, output_format)
