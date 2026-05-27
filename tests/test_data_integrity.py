import sys
import os
from collections import Counter

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from test_utils import load_all_data

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

    print("--- Test d'Intégrité Terminé ---\n")
    return overall_success, errors

def check_question_tags(questions_data, tags_master):
    """Vérifie que tous les tags dans les questions existent dans tags_master."""
    errors = []
    master_tags = set()
    for category in tags_master.values():
        master_tags.update(category)

    for question in questions_data.get('questions', []):
        q_id = question.get('id', 'ID inconnu')
        for option in question.get('options', []):
            for tag in option.get('tags', []):
                tag_value = tag.get('value')
                if tag_value and tag_value not in master_tags:
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

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("Le test d'intégrité des données a échoué. Erreurs trouvées :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("Le test d'intégrité des données a réussi. Aucune erreur trouvée.")
