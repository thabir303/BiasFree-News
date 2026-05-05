"""
TOON (Token-Oriented Object Notation) formatter for LLM prompts.
Reduces token usage by 30-60% compared to JSON.
"""

from typing import Any, Dict, List, Optional
from py_toon_format import encode, decode


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
        # py-toon-format's encode function takes data directly
        return encode(data)
    
# Singleton instance for easy import
toon_formatter = ToonFormatter()

