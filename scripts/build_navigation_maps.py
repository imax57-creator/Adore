import json
from pathlib import Path
import sys
import ijson
from collections import defaultdict

def build_hierarchy_map():
    """
    Processes the main ROME hierarchy file to create a simplified, navigable
    JSON map for the application.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    source_hierarchy_path = ref_rome_path / "unix_arborescence_principale_v460.json"
    output_path = data_path / "navigation_arborescence.json"

    print("--- Building Main Hierarchy Map ---")

    try:
        with source_hierarchy_path.open('r', encoding='latin-1') as f:
            source_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FATAL: Could not read or parse the source hierarchy file. Error: {e}", file=sys.stderr)
        sys.exit(1)

    navigation_map = []
    try:
        for grand_domaine in source_data.get("arbo_principale", []):
            gd_code = grand_domaine.get("code_metier")
            gd_libelle = grand_domaine.get("libelle", "Sans nom")

            if not gd_code or not gd_libelle:
                continue

            grand_domaine_node = {
                "code": gd_code,
                "libelle": gd_libelle,
                "domaines": []
            }

            for domaine_prof in grand_domaine.get("liste_domaine_prof", []):
                dp_code = domaine_prof.get("code_metier")
                dp_libelle = domaine_prof.get("libelle", "Sans nom")

                if not dp_code or not dp_libelle:
                    continue

                domaine_prof_node = {
                    "code": dp_code,
                    "libelle": dp_libelle,
                    "metiers": []
                }

                for metier in domaine_prof.get("liste_metier", []):
                    metier_code = metier.get("code_rome")
                    metier_libelle = metier.get("libelle", "Sans nom")

                    if not metier_code or not metier_libelle:
                        continue
                    
                    metier_node = {
                        "code": metier_code,
                        "libelle": metier_libelle
                    }
                    domaine_prof_node["metiers"].append(metier_node)
                
                if domaine_prof_node["metiers"]:
                    grand_domaine_node["domaines"].append(domaine_prof_node)

            if grand_domaine_node["domaines"]:
                navigation_map.append(grand_domaine_node)
        
        processed_data = navigation_map
        
        data_path.mkdir(exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        print(f"-> Successfully saved hierarchy map to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during hierarchy processing. Error: {e}", file=sys.stderr)
        sys.exit(1)

def build_sectors_map():
    """
    Processes the activity sectors ROME file using a streaming parser (ijson)
    to create a simplified map for the application.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    source_sectors_path = ref_rome_path / "unix_arborescence_secteur_activite_v460.json"
    output_path = data_path / "navigation_secteurs.json"

    print("\n--- Building Activity Sectors Map ---")

    sectors_map = defaultdict(list)
    try:
        print(f"Streaming source file: {source_sectors_path.name}...")
        with source_sectors_path.open('r', encoding='latin-1') as f:
            parser = ijson.items(f, 'arbo_secteur.item')
            for sector in parser:
                sector_libelle = sector.get("libelle")
                if not sector_libelle:
                    continue

                rome_codes_in_sector = set()
                for metier in sector.get("liste_metier", []):
                    if metier.get("code_rome"):
                        rome_codes_in_sector.add(metier.get("code_rome"))
                for sub_sector in sector.get("liste_sous_secteur", []):
                    for metier in sub_sector.get("liste_metier", []):
                        if metier.get("code_rome"):
                            rome_codes_in_sector.add(metier.get("code_rome"))
                
                if rome_codes_in_sector:
                    sectors_map[sector_libelle].extend(sorted(list(rome_codes_in_sector)))

        print(f"-> Processing complete. Found {len(sectors_map)} sectors.")

        data_path.mkdir(exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(sectors_map, f, indent=2, ensure_ascii=False)
        print(f"-> Successfully saved sectors map to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during sectors processing. Error: {e}", file=sys.stderr)
        sys.exit(1)

def build_competence_index():
    """
    Builds a complete, clean index of all competences from the arborescence and referential files.
    """
    project_root = Path(__file__).parent.parent
    ref_rome_path = project_root / "RefRomeJson"
    data_path = project_root / "data"

    arbo_path = ref_rome_path / "unix_arborescence_competence_v460.json"
    ref_path = ref_rome_path / "unix_referentiel_competence_v460.json"
    output_path = data_path / "competence_index.json"

    print("\n--- Building Competence Index ---")

    # 1. Load details from the referential file
    details_map = {}
    try:
        print(f"Streaming referential file: {ref_path.name}...")
        with ref_path.open('r', encoding='latin-1') as f:
            parser = ijson.items(f, 'item_referentiel_competence.item')
            for comp in parser:
                if comp.get("code_ogr"):
                    details_map[comp["code_ogr"]] = {
                        "libelle": comp.get("libelle"),
                        "categorie": comp.get("libelle_categorie")
                    }
        print(f"-> Found details for {len(details_map)} competences.")
    except Exception as e:
        print(f"FATAL: Could not process referential file {ref_path.name}. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Build the hierarchy and enrich it with details
    competence_index = {}
    try:
        print(f"Streaming arborescence file: {arbo_path.name}...")
        with arbo_path.open('r', encoding='latin-1') as f:
            parser = ijson.items(f, 'arborescence_competence.domaine_competence.item')
            for domaine in parser:
                path_domaine = [domaine.get("libelle_domaine_competence")]
                for enjeu in domaine.get("liste_enjeux", []):
                    path_enjeu = path_domaine + [enjeu.get("libelle_enjeu")]
                    for objectif in enjeu.get("liste_objectifs", []):
                        path_objectif = path_enjeu + [objectif.get("libelle_objectif")]
                        for macro in objectif.get("liste_macro_competences", []):
                            path_macro = path_objectif + [macro.get("libelle_macro_competence")]
                            for comp in macro.get("liste_competences", []):
                                code_ogr = comp.get("code_ogr_competence")
                                if code_ogr:
                                    details = details_map.get(code_ogr, {})
                                    competence_index[code_ogr] = {
                                        "libelle": details.get("libelle", comp.get("libelle_competence")),
                                        "categorie": details.get("categorie"),
                                        "hierarchie": path_macro
                                    }
        print(f"-> Processing complete. Indexed {len(competence_index)} competences.")

        # 3. Save the index
        data_path.mkdir(exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(competence_index, f, indent=2, ensure_ascii=False)
        print(f"-> Successfully saved competence index to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during competence index building. Error: {e}", file=sys.stderr)
        sys.exit(1)

def build_competence_graph():
    """
    Builds a competence -> jobs graph using the competence index and enriched job data.
    """
    project_root = Path(__file__).parent.parent
    data_path = project_root / "data"

    jobs_path = data_path / "jobs_rome_enriched.json"
    index_path = data_path / "competence_index.json"
    output_path = data_path / "competence_graph.json"

    print("\n--- Building Competence-Jobs Graph ---")

    # 1. Load the competence index
    try:
        with index_path.open('r', encoding='utf-8') as f:
            competence_graph = json.load(f)
        # Initialize metiers list for each competence
        for code_ogr in competence_graph:
            competence_graph[code_ogr]['metiers'] = []
        print(f"-> Competence index loaded with {len(competence_graph)} entries.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"FATAL: Could not load competence index file. Please run build_competence_index first. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Stream jobs data and build the inverted map
    try:
        print(f"Streaming jobs file: {jobs_path.name}...")
        with jobs_path.open('r', encoding='utf-8-sig') as f:
            parser = ijson.items(f, 'item')
            for job in parser:
                code_rome = job.get('rome', {}).get('code_rome')
                if not code_rome:
                    continue
                
                # Gather all competence codes from the job
                job_comp_codes = set()
                competences = job.get('competences', {})
                for comp_category in ['savoir_faire', 'savoir_etre_professionnel', 'savoirs']:
                    if comp_category in competences:
                        for enjeu in competences[comp_category].get('enjeux', []) or competences[comp_category].get('categories', []):
                            for item in enjeu.get('items', []):
                                if item.get('code_ogr'):
                                    job_comp_codes.add(str(item['code_ogr'])) # Ensure code is string

                # Add the job to the graph for each competence it has
                for code_ogr in job_comp_codes:
                    if code_ogr in competence_graph:
                        competence_graph[code_ogr]['metiers'].append(code_rome)

        print("-> Finished processing jobs.")

        # 3. Save the final graph
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(competence_graph, f, indent=2, ensure_ascii=False)
        print(f"-> Successfully saved competence graph to: {output_path.name}")

    except Exception as e:
        print(f"FATAL: An error occurred during graph building. Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    print("--- Starting Full Navigation Data Build ---")
    build_hierarchy_map()
    build_sectors_map()
    build_competence_index()
    build_competence_graph()
    print("\n--- Full Navigation Data Build Finished Successfully ---")
