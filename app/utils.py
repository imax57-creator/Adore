
import logging
import sys
from pathlib import Path

def setup_logger(name='data_pipeline', level=logging.INFO, log_file=None):
    """
    Configures and returns a logger with console and optional file handlers.

    Args:
        name (str): The name of the logger.
        level (int): The logging level for the console handler (e.g., logging.INFO).
        log_file (str, optional): Path to the log file. If provided, logs will
                                  also be written to this file.

    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Prevent adding duplicate handlers
    if logger.hasHandlers():
        return logger

    # Set the base level of the logger to the lowest possible to capture all messages
    logger.setLevel(logging.DEBUG)

    # --- Console Handler ---
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    # --- Optional File Handler ---
    if log_file:
        log_path = Path(log_file)
        # Ensure the directory for the log file exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        # The file handler logs everything from DEBUG level upwards
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# Default logger instance for simple, direct import
log = setup_logger()

# ---------------------------------------------------------------------------
# ROME definition formatter — shared between ResultsView and ExplorerView
# ---------------------------------------------------------------------------
import re as _re

# Prepositions / articles / conjunctions that precede proper nouns in French —
# when the NEXT word is capitalised they are NOT activity starters.
_PARTICLES = frozenset([
    'en', 'à', 'de', 'du', 'des', 'le', 'la', 'les', 'un', 'une',
    'ou', 'et', 'ni', 'au', 'aux', 'par', 'pour', 'sur', 'sous',
    'dans', 'avec', 'sans', 'selon', "d'", "l'",
])

def format_definition_as_bullets(text):
    """Format a ROME definition string: intro sentence + '- Activity' bullet lines.

    The ROME ``definition`` field concatenates several activity clauses into one
    paragraph.  This function restores the list structure so that each clause
    is shown as a separate bullet point under the introductory sentence.

    Rules (safe — avoids splitting proper nouns such as "Poste Central"):
    * Split on ". " boundaries first (the most reliable separator).
    * Within each remaining segment, split at a capitalised word that is
      - outside all parenthetical expressions (tracked depth), AND
      - NOT preceded by a preposition / article / conjunction.
    """
    if not text:
        return text

    # Split into major sentences at period + space boundaries
    sentences = _re.split(r'\.\s+', text)
    intro = sentences[0].strip().rstrip('.') + '.'
    remaining = ' '.join(s.strip() for s in sentences[1:] if s.strip())
    if not remaining:
        return text

    # Tokenise and find activity-start positions outside parentheses
    activities = []
    current = []
    paren_depth = 0
    words = remaining.split(' ')
    for i, word in enumerate(words):
        paren_depth += word.count('(') - word.count(')')
        is_start = (
            i > 0
            and paren_depth == 0
            and word
            and word[0].isupper()
            and not words[i - 1].endswith(',')
            and words[i - 1].lower().rstrip("'.") not in _PARTICLES
        )
        if is_start:
            if current:
                activities.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        activities.append(' '.join(current))

    if not activities:
        return text
    return intro + '\n' + '\n'.join(f'- {a.strip()}' for a in activities if a.strip())

