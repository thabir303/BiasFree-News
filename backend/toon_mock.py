"""
Mock TOON module to bypass compilation issues.
This provides basic functionality for testing.
"""

def encode(data, delimiter=","):
    """Simple mock encode function."""
    if isinstance(data, dict):
        items = []
        for key, value in data.items():
            if isinstance(value, str):
                items.append(f"{key}={value}")
            else:
                items.append(f"{key}={str(value)}")
        return delimiter.join(items)
    elif isinstance(data, list):
        return delimiter.join(str(item) for item in data)
    else:
        return str(data)

def decode(data_str, delimiter=","):
    """Simple mock decode function."""
    items = data_str.split(delimiter)
    result = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        else:
            result[item.strip()] = ""
    return result

class EncodeOptions:
    """Mock EncodeOptions class."""
    def __init__(self, delimiter=",", indent=2):
        self.delimiter = delimiter
        self.indent = indent