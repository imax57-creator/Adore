
import json
from pathlib import Path
import sys
from collections import defaultdict

def build_naf_maps():
    """
    Processes the ROME NAF sectors file to create two maps:
    1. A map from NAF sector to a list of ROME codes.
    2. An inverted map from a ROME code to a list of NAF sectors.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    source_path = ref_rome_path / "unix_arborescence_secteur_naf_v460.json"
    naf_to_rome_output_path = data_path / "naf_to_rome_map.json"
    rome_to_naf_output_path = data_path / "rome_to_naf_map.json"

    print("--- Building NAF Sector Maps (Production-Grade) ---")

    try:
        with source_path.open('r', encoding='latin-1') as f:
            source_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FATAL: Could not read or parse the source file. Error: {e}", file=sys.stderr)
        sys.exit(1)

    naf_to_rome_map = {}
    rome_to_naf_map = defaultdict(list)

    try:
        for naf_group in source_data.get("arbo_secteur_naf", []):
            naf_code = naf_group.get("code_secteur_naf") # Assumed key, will be None
            naf_libelle = naf_group.get("libelle_secteur_naf")

            if not naf_libelle:
                continue
            
            # Use the label as a stable key
            key = naf_libelle.strip()

            rome_codes_in_sector = sorted(list({
                metier.get("code_rome")
                for metier in naf_group.get("liste_metier", [])
                if metier.get("code_rome")
            }))

            if not rome_codes_in_sector:
                continue

            # 1. Build the NAF -> ROME map
            naf_to_rome_map[key] = {
                "code_naf": naf_code,
                "metiers": rome_codes_in_sector
            }

            # 2. Build the ROME -> NAF inverted map
            naf_info_for_rome = {"code_naf": naf_code, "libelle": naf_libelle}
            for code_rome in rome_codes_in_sector:
                if naf_info_for_rome not in rome_to_naf_map[code_rome]:
                    rome_to_naf_map[code_rome].append(naf_info_for_rome)

        # --- Save the two map files ---
        data_path.mkdir(exist_ok=True)

        with naf_to_rome_output_path.open('w', encoding='utf-8') as f:
            json.dump(naf_to_rome_map, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"-> Successfully saved NAF-to-ROME map to: {naf_to_rome_output_path.name}")

        with rome_to_naf_output_path.open('w', encoding='utf-8') as f:
            json.dump(rome_to_naf_map, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"-> Successfully saved ROME-to-NAF map to: {rome_to_naf_output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during NAF maps processing. Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_naf_maps()
