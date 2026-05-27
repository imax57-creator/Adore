
import sys
import os
import random

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from test_utils import load_all_data, get_predefined_profiles, run_suggestion_engine

def run_all_checks():
    """Exécute les tests de stabilité pour s'assurer que l'ordre des réponses n'a pas d'impact."""
    print("--- Lancement du Test de Stabilité de l'Algorithme ---")
    
    try:
        jobs_data, questions_data, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    profiles = get_predefined_profiles(questions_data)
    errors = []
    overall_success = True

    for name, profile in profiles.items():
        print(f"Vérification de la stabilité pour le profil : '{name}'...")
        
        # Exécution de base
        base_results = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)
        if base_results is None:
            errors.append(f"[{name}]: L'exécution de base a échoué.")
            overall_success = False
            print("   -> ❌ Échec.")
            continue

        # Création d'un profil avec les mêmes réponses, mais dans un ordre différent
        shuffled_answers = list(profile['answers'].items())
        random.shuffle(shuffled_answers)
        shuffled_profile = {
            "name": name,
            "answers": dict(shuffled_answers)
        }
        shuffled_results = run_suggestion_engine(shuffled_profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)

        if shuffled_results is None:
            errors.append(f"[{name}]: L'exécution avec les réponses mélangées a échoué.")
            overall_success = False
            print("   -> ❌ Échec.")
            continue

        # Comparaison des résultats (basée sur les codes ROME)
        base_rome_codes = [job.get('rome', {}).get('code_rome') for job in base_results]
        shuffled_rome_codes = [job.get('rome', {}).get('code_rome') for job in shuffled_results]

        if base_rome_codes != shuffled_rome_codes:
            overall_success = False
            error_msg = f"[{name}]: Les résultats diffèrent lorsque l'ordre des réponses est modifié."
            errors.append(error_msg)
            print(f"   -> ❌ Échec. {error_msg}")
        else:
            print("   -> ✅ OK.")

    print("--- Test de Stabilité Terminé ---")
    return overall_success, errors

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("\nLe test de stabilité a échoué. Erreurs trouvées :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("\nLe test de stabilité a réussi. L'algorithme est insensible à l'ordre des réponses.")
