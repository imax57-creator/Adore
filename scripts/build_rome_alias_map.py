
import json
from pathlib import Path
import sys
import ijson

def build_rome_alias_map():
    """
    Reads the ROME code referential and creates a map from any ROME code (alias or master)
    to its corresponding master ROME code.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    source_path = ref_rome_path / "unix_referentiel_code_rome_v460.json"
    output_path = data_path / "rome_alias_map.json"

    print("--- Building ROME Alias Map ---")

    try:
        alias_map = {}
        with source_path.open('r', encoding='latin-1') as f:
            # Use ijson for efficient streaming of the large JSON file
            parser = ijson.items(f, 'item')
            for entry in parser:
                code = entry.get('code_rome')
                parent_code = entry.get('code_rome_parent')
                if code and parent_code:
                    alias_map[code] = parent_code
        
        if not alias_map:
            print("FATAL: No data could be processed from the source file.", file=sys.stderr)
            sys.exit(1)

        data_path.mkdir(exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(alias_map, f, indent=2, sort_keys=True, ensure_ascii=False)
            
        print(f"-> Successfully created ROME alias map with {len(alias_map)} entries.")
        print(f"   Saved to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during processing. Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_rome_alias_map()
