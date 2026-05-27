
import json
from pathlib import Path
import sys
from collections import defaultdict

# Ajout du chemin de l'application pour trouver le module utils
project_root_path = Path(__file__).parent.parent
sys.path.append(str(project_root_path))

from app.utils import setup_logger

# Configure un logger spécifique pour ce script
log = setup_logger('enrich_jobs', log_file='logs/enrich_jobs_data.log')

def load_json(path, encoding='utf-8'):
    """Loads a JSON file with robust error handling."""
    try:
        log.info(f"Loading {path.name}...")
        with path.open("r", encoding=encoding) as f:
            data = json.load(f)
            log.info(f"-> Successfully loaded {path.name}")
            return data
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        log.error(f"FATAL: Could not read or parse {path.name}. Error: {e}")
        return None
    except Exception as e:
        log.error(f"FATAL: An unexpected error occurred while loading {path.name}. Error: {e}")
        return None

def build_rich_jobs_map(data):
    """Builds a lookup map from ROME code to job object."""
    if not data: return {}
    return {job['rome']['code_rome']: job for job in data}

def build_rome_to_sectors_map(data):
    """Builds a map from ROME code to a list of activity sectors."""
    if not data: return {}
    rome_map = defaultdict(list)
    for sector in data.get('arbo_secteur', []):
        sector_libelle = sector.get('libelle')
        if not sector_libelle:
            continue
        for metier in sector.get('liste_metier', []):
            code_rome = metier.get('code_rome')
            if code_rome and sector_libelle not in rome_map[code_rome]:
                rome_map[code_rome].append(sector_libelle)
    return rome_map

def enrich_job(base_job, rich_jobs_map, sectors_map, naf_map):
    """Enriches a single job object with data from various maps."""
    code_rome = base_job.get('rome', {}).get('code_rome')
    if not code_rome:
        log.warning("Found a base job without a ROME code. Skipping.")
        return None

    if code_rome not in rich_jobs_map:
        log.warning(f"Code ROME '{code_rome}' from base file not found in rich source. Skipping.")
        return None

    # Start with the rich data object
    enriched_job = rich_jobs_map[code_rome].copy()

    # Add activity sector and NAF information
    enriched_job['secteurs_activite'] = sorted(sectors_map.get(code_rome, []))
    
    naf_data = naf_map.get(code_rome, [])
    if not naf_data:
        log.debug(f"No NAF data found for ROME code '{code_rome}'.")
    
    enriched_job['secteurs_naf'] = sorted(naf_data, key=lambda x: x.get('libelle', ''))
    
    return enriched_job

def main():
    """Main orchestration function."""
    log.info("--- Starting Data Enrichment Script (Refactored) ---")

    # --- Define Paths ---
    data_path = project_root_path / "data"
    ref_rome_path = project_root_path / "RefRomeJson"
    
    base_jobs_path = data_path / "jobs_rome.json"
    rich_source_path = ref_rome_path / "unix_fiche_emploi_metier_v460.json"
    sectors_path = ref_rome_path / "unix_arborescence_secteur_activite_v460.json"
    rome_to_naf_path = data_path / "rome_to_naf_map.json"
    output_path = data_path / "jobs_rome_enriched.json"

    # --- Load all data sources ---
    base_jobs = load_json(base_jobs_path, encoding='utf-8-sig')
    rich_data = load_json(rich_source_path, encoding='latin-1')
    sectors_data = load_json(sectors_path, encoding='latin-1')
    rome_to_naf_map = load_json(rome_to_naf_path)

    if any(data is None for data in [base_jobs, rich_data, sectors_data, rome_to_naf_map]):
        log.error("One or more source files failed to load. Aborting enrichment.")
        sys.exit(1)

    # --- Build lookup maps ---
    log.info("Building lookup maps...")
    rich_jobs_map = build_rich_jobs_map(rich_data)
    rome_to_sectors_map = build_rome_to_sectors_map(sectors_data)
    log.info("-> Lookup maps built successfully.")

    # --- Enrich data ---
    log.info("Enriching job data...")
    enriched_jobs = []
    enriched_count = 0
    
    for job in base_jobs:
        enriched_version = enrich_job(job, rich_jobs_map, rome_to_sectors_map, rome_to_naf_map)
        if enriched_version:
            enriched_jobs.append(enriched_version)
            enriched_count += 1
            
    log.info(f"-> Enrichment complete. {enriched_count} jobs processed successfully.")

    # --- Save the new enriched file ---
    try:
        log.info(f"Saving enriched data to: {output_path.name}...")
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(enriched_jobs, f, indent=2, ensure_ascii=False)
        log.info("-> Successfully saved the enriched file.")
    except IOError as e:
        log.error(f"FATAL: Could not write the output file. Error: {e}")
        sys.exit(1)

    log.info("--- Data Enrichment Script Finished Successfully ---")

if __name__ == "__main__":
    main()
