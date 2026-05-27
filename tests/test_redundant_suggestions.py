
import sys
import os
from difflib import SequenceMatcher

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from app.logic.profile_utils import generate_random_profile
from test_utils import load_all_data, run_suggestion_engine

SIMILARITY_THRESHOLD = 0.9 # Seuil de similarité textuelle
NUM_SIMULATIONS = 20       # Nombre de profils aléatoires à tester
TOP_N_TO_CHECK = 5         # Comparer les N premiers résultats

def run_all_checks():
    """Exécute le test de redondance sur plusieurs simulations."""
    print("--- Lancement du Test de Redondance des Suggestions ---")
    
    try:
        jobs_data, questions_data, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    errors = []
    overall_success = True

    for i in range(NUM_SIMULATIONS):
        print(f"\rSimulation {i+1}/{NUM_SIMULATIONS}...", end="")
        
        profile = generate_random_profile(questions_data)
        top_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)

        if top_jobs is None or len(top_jobs) < TOP_N_TO_CHECK:
            # Pas assez de résultats pour comparer, on passe au suivant
            continue

        # Comparer les paires de métiers dans le top N
        jobs_to_check = top_jobs[:TOP_N_TO_CHECK]
        for i in range(len(jobs_to_check)):
            for j in range(i + 1, len(jobs_to_check)):
                job1 = jobs_to_check[i]
                job2 = jobs_to_check[j]

                desc1 = job1.get('description', '')
                desc2 = job2.get('description', '')

                if not desc1 or not desc2:
                    continue

                similarity = SequenceMatcher(a=desc1, b=desc2).ratio()

                if similarity > SIMILARITY_THRESHOLD:
                    overall_success = False
                    error_msg = (f"[Simulation {i+1}] Forte similarité ({similarity:.2f}) détectée entre "
                                 f"'{job1['name']}' et '{job2['name']}'.")
                    errors.append(error_msg)
    
    print("\n--- Test de Redondance Terminé ---\n")
    if overall_success:
        print("Aucune redondance excessive détectée dans les suggestions.")
    
    return overall_success, errors

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("\nLe test de redondance a échoué. Problèmes trouvés :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("\nLe test de redondance a réussi.")
