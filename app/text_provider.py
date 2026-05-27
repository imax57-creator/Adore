import json
from pathlib import Path

class TextProvider:
    def __init__(self, file_path: Path):
        self.texts = {}
        try:
            with file_path.open('r', encoding='utf-8') as f:
                self.texts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[ERROR] Could not load texts file: {e}")

    def get_text(self, key: str, mode: str) -> str:
        """Retrieves a text string for a given key and mode (e.g., 'jeune', 'adulte')."""
        # Fallback to 'jeune' if mode-specific text doesn't exist
        return self.texts.get(key, {}).get(mode, self.texts.get(key, {}).get('jeune', f"<{key}:{mode}>_NOT_FOUND"))
