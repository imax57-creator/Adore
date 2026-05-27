
import json
from pathlib import Path
import sys

def build_themes_map():
    """
    Processes the ROME themes file to create a simplified, 
    navigable JSON map for the application.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    source_path = ref_rome_path / "unix_arborescence_thematique_v460.json"
    output_path = data_path / "navigation_thematiques.json"

    print("--- Building Themes Map ---")

    try:
        # The source file has a 'latin-1' encoding
        with source_path.open('r', encoding='latin-1') as f:
            source_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FATAL: Could not read or parse the source file. Error: {e}", file=sys.stderr)
        sys.exit(1)

    navigation_map = []
    try:
        for theme_group in source_data.get("arbo_thematique", []):
            libelle = theme_group.get("libelle_theme")
            definition = theme_group.get("definition_theme")

            if not libelle:
                continue

            # Extract all associated ROME codes
            rome_codes = sorted(list({
                metier.get("code_rome")
                for metier in theme_group.get("liste_metier", [])
                if metier.get("code_rome")
            }))

            if not rome_codes:
                continue

            theme_node = {
                "libelle": libelle,
                "definition": definition,
                "metiers": rome_codes
            }
            navigation_map.append(theme_node)
        
        # Ensure the output directory exists
        data_path.mkdir(exist_ok=True)
        
        # Save the new map with 'utf-8' encoding
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(navigation_map, f, indent=2, ensure_ascii=False)
            
        print(f"-> Successfully saved {len(navigation_map)} themes to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during processing. Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_themes_map()

