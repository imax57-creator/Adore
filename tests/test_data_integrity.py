import sys
import os
from collections import Counter

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from test_utils import load_all_data, get_data_manager

MIN_UNIQUE_SEARCH_TERMS = 20  # seuil bas — tous les métiers ont ≥125 termes en pratique

def run_all_checks():
    """Exécute toutes les vérifications d'intégrité des données et retourne les résultats."""
    print("--- Lancement du Test d'Intégrité des Données ---")
    
    try:
        jobs_data, questions_data, semantic_map, tags_master, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    errors = []
    overall_success = True

    # --- Test 1: Cohérence des tags dans les questions ---
    print("1. Vérification des tags dans les questionnaires...")
    q_errors = check_question_tags(questions_data, tags_master)
    if q_errors:
        errors.extend(q_errors)
        overall_success = False
        print("   -> ❌ Problèmes trouvés.")
    else:
        print("   -> ✅ OK.")

    # --- Test 2: Cohérence des clés de la carte sémantique ---
    print("2. Vérification des clés de la carte sémantique...")
    sm_errors = check_semantic_map_keys(semantic_map, tags_master)
    if sm_errors:
        errors.extend(sm_errors)
        overall_success = False
        print("   -> ❌ Problèmes trouvés.")
    else:
        print("   -> ✅ OK.")

    # --- Test 3: Structure et doublons dans les fiches métiers ---
    print("3. Vérification de la structure des fiches métiers...")
    job_errors = check_job_data_structure(jobs_data)
    if job_errors:
        errors.extend(job_errors)
        overall_success = False
        print("   -> ❌ Problèmes trouvés.")
    else:
        print("   -> ✅ OK.")

    dm = get_data_manager()

    # --- Test 4: Prérequis du scoring (champs essentiels + termes indexés) ---
    print("4. Vérification des prérequis de scoring pour chaque métier...")
    scoring_errors = check_scoring_prerequisites(jobs_data)
    if scoring_errors:
        errors.extend(scoring_errors)
        overall_success = False
        print(f"   -> ❌ {len(scoring_errors)} problème(s) trouvé(s).")
        for e in scoring_errors[:5]:
            print(f"      {e}")
        if len(scoring_errors) > 5:
            print(f"      ... et {len(scoring_errors) - 5} autre(s).")
    else:
        print("   -> ✅ OK.")

    # --- Test 5: Présence dans les index de navigation ---
    print("5. Vérification de la couverture des index de navigation...")
    nav_errors = check_navigation_index_coverage(dm)
    if nav_errors:
        errors.extend(nav_errors)
        overall_success = False
        print(f"   -> ❌ {len(nav_errors)} métier(s) absent(s) des index.")
        for e in nav_errors[:5]:
            print(f"      {e}")
    else:
        print("   -> ✅ OK.")

    # --- Test 6: Complétude de rome_alias_map ---
    print("6. Vérification de la complétude de rome_alias_map...")
    alias_errors = check_alias_map_completeness(dm)
    if alias_errors:
        errors.extend(alias_errors)
        overall_success = False
        print(f"   -> ❌ {len(alias_errors)} code(s) ROME manquant(s) dans l'alias map.")
        for e in alias_errors[:5]:
            print(f"      {e}")
    else:
        print("   -> ✅ OK.")

    print("--- Test d'Intégrité Terminé ---\n")
    return overall_success, errors

SEMANTIC_TAG_TYPES = {"quality", "interest", "skill"}

def check_question_tags(questions_data, tags_master):
    """Vérifie que les tags sémantiques dans les questions existent dans tags_master.

    Les tags fonctionnels (work_context_pref, work_style, experience_sector,
    formation_constraint, tag, domain) sont ignorés car ils ne sont pas des
    entrées sémantiques destinées au scoring TF-IDF.
    """
    errors = []
    master_tags = set()
    for category in tags_master.values():
        master_tags.update(category)

    for question in questions_data.get('questions', []):
        q_id = question.get('id', 'ID inconnu')
        for option in question.get('options', []):
            for tag in option.get('tags', []):
                tag_type = tag.get('type')
                tag_value = tag.get('value')
                if tag_type in SEMANTIC_TAG_TYPES and tag_value and tag_value not in master_tags:
                    errors.append(f"[Question {q_id}]: Le tag '{tag_value}' n'existe pas dans tags_master.json")
    return errors

def check_semantic_map_keys(semantic_map, tags_master):
    """Vérifie que les clés de la carte sémantique sont des tags valides."""
    errors = []
    master_tags = set()
    for category in tags_master.values():
        master_tags.update(category)

    for key in semantic_map.keys():
        if key not in master_tags:
            errors.append(f"[Semantic Map]: La clé '{key}' n'est pas un tag valide défini dans tags_master.json")
    return errors

def check_job_data_structure(jobs_data):
    """Vérifie les clés essentielles et les doublons de code_rome dans jobs_data."""
    errors = []
    rome_codes = []
    for i, job in enumerate(jobs_data):
        # Accéder à la structure imbriquée
        rome_info = job.get('rome', {})
        code_rome = rome_info.get('code_rome')
        intitule = rome_info.get('intitule')

        if not code_rome:
            errors.append(f"[Job #{i+1}]: Clé 'code_rome' manquante ou vide dans le sous-objet 'rome'.")
        else:
            rome_codes.append(code_rome)
        
        if not intitule:
            errors.append(f"[Job {code_rome or '#' + str(i+1)}]: Clé 'intitule' (nom) manquante ou vide dans le sous-objet 'rome'.")

    code_counts = Counter(rome_codes)
    for code, count in code_counts.items():
        if count > 1:
            errors.append(f"[Jobs Data]: Le code ROME '{code}' est dupliqué {count} fois.")
            
    return errors

def check_scoring_prerequisites(jobs_data):
    """Vérifie que chaque métier possède les champs essentiels au scoring et un minimum de termes indexés."""
    errors = []
    for job in jobs_data:
        rome = job.get('rome', {})
        code = rome.get('code_rome', '?')
        name = rome.get('intitule', '?')

        if not job.get('definition', '').strip():
            errors.append(f"[{code}] '{name}' : champ 'definition' vide ou absent.")

        if not job.get('secteurs_activite'):
            errors.append(f"[{code}] '{name}' : champ 'secteurs_activite' vide ou absent.")

        competences = job.get('competences', {})
        if not competences or not any(competences.values()):
            errors.append(f"[{code}] '{name}' : champ 'competences' vide ou absent.")

        unique_terms = len(set(job.get('_search_terms_list', [])))
        if unique_terms < MIN_UNIQUE_SEARCH_TERMS:
            errors.append(
                f"[{code}] '{name}' : seulement {unique_terms} terme(s) de recherche unique(s) "
                f"(minimum requis : {MIN_UNIQUE_SEARCH_TERMS})."
            )

    return errors


def _extract_codes_from_index(index_dict):
    """Extrait l'ensemble des codes ROME depuis un index de navigation."""
    codes = set()
    for items in index_dict.values():
        if isinstance(items, set):
            codes.update(items)
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    codes.add(item)
                elif isinstance(item, dict):
                    code = item.get('rome', {}).get('code_rome') or item.get('code_rome')
                    if code:
                        codes.add(code)
    return codes


def check_navigation_index_coverage(dm):
    """Vérifie que chaque métier apparaît dans au moins un des index secteur ou intérêt."""
    errors = []
    all_codes = {j['rome']['code_rome'] for j in dm.jobs}
    in_sector = _extract_codes_from_index(dm._sector_to_jobs)
    in_interest = _extract_codes_from_index(dm._interest_to_jobs)
    in_any = in_sector | in_interest

    missing = sorted(all_codes - in_any)
    for code in missing:
        job = dm.get_job_by_code(code)
        name = job['rome']['intitule'] if job else '???'
        errors.append(
            f"[{code}] '{name}' absent des index 'secteur' et 'intérêt' "
            f"(métier non navigable depuis l'ExplorerView)."
        )
    return errors


def check_alias_map_completeness(dm):
    """Vérifie que chaque code ROME du catalogue est résolvable via rome_alias_map."""
    errors = []
    all_codes = {j['rome']['code_rome'] for j in dm.jobs}
    missing = sorted(all_codes - set(dm.rome_alias_map.keys()))
    for code in missing:
        job = next((j for j in dm.jobs if j['rome']['code_rome'] == code), None)
        name = job['rome']['intitule'] if job else '???'
        errors.append(
            f"[{code}] '{name}' absent de rome_alias_map.json — "
            f"get_job_by_code('{code}') retournera None."
        )
    return errors


if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("Le test d'intégrité des données a échoué. Erreurs trouvées :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("Le test d'intégrité des données a réussi. Aucune erreur trouvée.")
