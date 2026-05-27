
import json
import re
from pathlib import Path
import sys
from collections import defaultdict

# Add the project root to the path to find the app.utils module
project_root_path = Path(__file__).parent.parent
sys.path.append(str(project_root_path))

from app.utils import setup_logger

# Configure a logger for this script
log = setup_logger('build_education_map', log_file='logs/build_education_map.log')

def load_json(path, encoding='utf-8'):
    """Loads a JSON file with robust error handling."""
    try:
        log.info(f"Loading {path.name}...")
        with path.open("r", encoding=encoding) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"FATAL: Could not load {path.name}. Error: {e}")
        return None

def main():
    """Main function to build the job to education level map."""
    log.info("--- Starting Education Level Map Build Script ---")

    # --- Define Paths ---
    data_path = project_root_path / "data"
    ref_rome_path = project_root_path / "RefRomeJson"

    keywords_path = data_path / "education_keywords.json"
    rich_source_path = ref_rome_path / "unix_fiche_emploi_metier_v460.json"
    output_path = data_path / "job_education_map.json"

    # --- Load Source Files ---
    keywords_data = load_json(keywords_path)
    jobs_data = load_json(rich_source_path, encoding='latin-1')

    if not keywords_data or not jobs_data:
        log.error("Aborting due to missing source files.")
        sys.exit(1)

    log.info("Building job to education level map...")
    job_education_map = defaultdict(set)

    for job in jobs_data:
        code_rome = job.get('rome', {}).get('code_rome')
        if not code_rome:
            continue

        # Find the certifications category
        savoirs = job.get('competences', {}).get('savoirs', {})
        for category in savoirs.get('categories', []):
            if category.get('libelle') == "Certifications et habilitations":
                # Check each certification libelle against our keywords
                for item in category.get('items', []):
                    libelle = item.get('libelle', '').lower()
                    if not libelle:
                        continue
                    
                    for level, patterns in keywords_data.items():
                        for pattern in patterns:
                            # Using regex for robust matching, ignoring case
                            if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', libelle):
                                job_education_map[code_rome].add(level)
                                break # Move to next keyword list once a level is found for this item

    # Convert sets to sorted lists for stable JSON output
    final_map = {code: sorted(list(levels)) for code, levels in job_education_map.items()}

    log.info(f"-> Map built. Found education levels for {len(final_map)} jobs.")

    # --- Save the new map file ---
    try:
        log.info(f"Saving map to: {output_path.name}...")
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(final_map, f, indent=2, ensure_ascii=False)
        log.info("-> Successfully saved the map file.")
    except IOError as e:
        log.error(f"FATAL: Could not write the output file. Error: {e}")
        sys.exit(1)

    log.info("--- Education Level Map Build Script Finished Successfully ---")

if __name__ == "__main__":
    main()
