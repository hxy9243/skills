from __future__ import annotations

import re


LAYER_LABEL_RE = re.compile(r"^layer\d+\s*:\s*", re.IGNORECASE)
LAYER_BULLET_RE = re.compile(r"^-\s*layer(?P<depth>\d+)\s*:\s*(?P<label>.+)$", re.IGNORECASE)
NOTE_LINK_RE = re.compile(r"^\s*-\s*\[\[([^\]]+)\]\]\s*$")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "use", "with",
}


def slugify(value: str) -> str:
    """
    Convert a string into a URL-friendly slug.
    
    Replaces non-alphanumeric characters with hyphens, collapses
    multiple spaces/hyphens, and converts to lowercase.
    
    Args:
        value (str): The input string to slugify.
        
    Returns:
        str: The slugified string. Defaults to 'untitled' if empty.
    """
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.ASCII)
    value = re.sub(r"[_\s]+", "-", value.strip().lower())
    return value.strip("-") or "untitled"


def safe_title(value: str) -> str:
    """
    Collapse multiple whitespace characters into a single space and strip edges.
    
    Args:
        value (str): The input string.
        
    Returns:
        str: The cleaned string. Defaults to 'Untitled' if empty.
    """
    value = re.sub(r"\s+", " ", value.strip())
    return value or "Untitled"


def strip_layer_label(value: str) -> str:
    """
    Remove any 'layerN:' prefix from a string.
    
    Args:
        value (str): The input string potentially containing a layer label.
        
    Returns:
        str: The string without the layer label.
    """
    return safe_title(LAYER_LABEL_RE.sub("", value.strip()))


def format_layer_label(depth: int, value: str) -> str:
    """
    Format a string as a specific layer label (e.g., 'layer1: Category').
    
    Args:
        depth (int): The depth integer of the layer.
        value (str): The name of the category or branch.
        
    Returns:
        str: The formatted layer string.
    """
    return f"layer{depth}: {safe_title(value)}"


def markdown_label(value: str) -> str:
    """
    Extract the link text from a markdown link format `[Label](url)`.
    If it's not a markdown link, returns the string itself.
    
    Args:
        value (str): The input string.
        
    Returns:
        str: The extracted label text or the original string.
    """
    match = re.match(r"\[([^\]]+)\]\([^)]+\)$", value.strip())
    if match:
        return match.group(1)
    return value.strip()


def split_sentences(text: str) -> list[str]:
    """
    Split a block of text into sentences based on punctuation.
    
    Args:
        text (str): The input text block.
        
    Returns:
        list[str]: A list of sentences longer than 25 characters.
    """
    chunks = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 25]


def summarize_text(text: str, limit: int = 220) -> str:
    """
    Truncate text to a specified character limit, stopping at the last full word.
    
    Args:
        text (str): The text to summarize.
        limit (int): The maximum number of characters. Defaults to 220.
        
    Returns:
        str: The truncated text appended with '...' if it exceeds the limit.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def tokenize(text: str) -> list[str]:
    """
    Extract alphabetic and hyphenated words from text, converting to lowercase.
    
    Args:
        text (str): The input text.
        
    Returns:
        list[str]: A list of lowercase word tokens.
    """
    return [token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]
