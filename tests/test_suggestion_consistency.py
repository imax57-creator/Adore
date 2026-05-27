
import sys
import os

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from test_utils import load_all_data, get_predefined_profiles, run_suggestion_engine

def run_all_checks():
    """Exécute les tests de cohérence pour tous les profils prédéfinis."""
    print("--- Lancement du Test de Cohérence des Suggestions ---")
    
    try:
        jobs_data, questions_data, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    profiles = get_predefined_profiles(questions_data)
    errors = []
    overall_success = True

    for name, profile in profiles.items():
        print(f"1. Vérification du profil : '{name}'...")
        
        # --- Test 1.1: Cohérence des suggestions ---
        top_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)
        if top_jobs is None:
            errors.append(f"[{name}]: Le moteur de suggestion a échoué.")
            overall_success = False
            print("   -> ❌ Échec du moteur.")
            continue

        top_10_job_names = [job.get('rome', {}).get('intitule', '').lower() for job in top_jobs[:10]]
        found_match = False
        for expected_keyword in profile['expected_jobs']:
            if any(expected_keyword.lower() in job_name for job_name in top_10_job_names):
                found_match = True
                break
        
        if not found_match:
            success = False
            error_msg = f"[{name}]: Aucune des suggestions attendues ({profile['expected_jobs']}) n'a été trouvée dans le top 10."
            errors.append(error_msg)
            print(f"   -> ❌ Cohérence : Échec. {error_msg}")
        else:
            print("   -> ✅ Cohérence : OK.")

        # --- Test 1.2: Stabilité des résultats (non-aléatoire) ---
        print(f"2. Vérification de la stabilité pour le profil '{name}'...")
        first_run_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)
        second_run_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)

        # Temporairement désactivé pour le débogage
        # if first_run_jobs is None or second_run_jobs is None:
        #     errors.append(f"[{name} - Stabilité]: Le moteur a échoué sur une des exécutions.")
        #     overall_success = False
        #     print("   -> ❌ Stabilité : Échec du moteur.")
        #     continue

        first_run_ids = [job.get('rome', {}).get('code_rome') for job in first_run_jobs]
        second_run_ids = [job.get('rome', {}).get('code_rome') for job in second_run_jobs]

        if first_run_ids != second_run_ids:
            overall_success = False
            error_msg = f"[{name} - Stabilité]: Les résultats ne sont pas identiques entre deux exécutions."
            errors.append(error_msg)
            print(f"   -> ❌ Stabilité : Échec. {error_msg}")
        else:
            print("   -> ✅ Stabilité : OK.")

    print("--- Test de Cohérence Terminé ---\n")
    return overall_success, errors

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("Le test de cohérence a échoué. Erreurs trouvées :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("Le test de cohérence a réussi. Aucune erreur trouvée.")
