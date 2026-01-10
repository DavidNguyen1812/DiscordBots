import re

# Define a regular expression pattern for emoji detection
emoji_pattern = re.compile(
    "[\U0001F600-\U0001F64F]"  # Emoticons
    "|[\U0001F300-\U0001F5FF]"  # Symbols & Pictographs
    "|[\U0001F680-\U0001F6FF]"  # Transport & Map Symbols
    "|[\U0001F700-\U0001F77F]"  # Alchemical Symbols
    "|[\U0001F780-\U0001F7FF]"  # Geometric Shapes Extended
    "|[\U0001F800-\U0001F8FF]"  # Supplemental Arrows-C
    "|[\U0001F900-\U0001F9FF]"  # Supplemental Symbols & Pictographs
    "|[\U0001FA00-\U0001FA6F]"  # Chess Symbols
    "|[\U0001FA70-\U0001FAFF]"  # Symbols & Pictographs Extended-A
    "|[\U00002702-\U000027B0]"  # Dingbats
    "|[\U000024C2-\U0001F251]"  # Enclosed Characters
    "|[\U0001F1E6-\U0001F1FF]"  # Flags (iOS)
    "|[\U0001F004]"             # Mahjong Tile Red Dragon
    "|[\U0001F0CF]"             # Playing Card Black Joker
    "|[\U00002600-\U000026FF]"  # Miscellaneous Symbols
    "|[\U0001F18E]"             # Negative Squared Ab
    "|[\U0001F191-\U0001F19A]"  # Squared CJK Unified Ideographs
    "|[\U0001F1E6-\U0001F1FF]"  # Regional Indicator Symbols
    "|[\U0001F201-\U0001F251]"  # Enclosed Ideographic Supplement
    "|[\U0001F004]"             # Mahjong Tiles
    "|[\U0001F0CF]"             # Playing Card Black Joker
    "|[\U0001F300-\U0001F5FF]"  # Miscellaneous Symbols and Pictographs
    "|[\U0001F600-\U0001F64F]"  # Emoticons
    "|[\U0001F680-\U0001F6FF]"  # Transport and Map Symbols
    "|[\U0001F700-\U0001F77F]"  # Alchemical Symbols
    "|[\U0001F780-\U0001F7FF]"  # Geometric Shapes Extended
    "|[\U0001F800-\U0001F8FF]"  # Supplemental Arrows-C
    "|[\U0001F900-\U0001F9FF]"  # Supplemental Symbols and Pictographs
    "|[\U0001FA00-\U0001FA6F]"  # Symbols and Pictographs Extended-A
    "|[\U0001FA70-\U0001FAFF]"  # Chess Symbols
    "|[\U00002500-\U00002BEF]"  # Dingbats
    "|[\U0001F100-\U0001F64F]",  # Emoji modifiers
    flags=re.UNICODE)


# Function to check for emojis
def is_emoji(char):
    return bool(emoji_pattern.match(char))

