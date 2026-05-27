import sys
import os
import time
import statistics

# Assurer que test_utils peut être importé
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)
from app.logic.profile_utils import generate_random_profile
from test_utils import load_all_data, run_suggestion_engine

NUM_SIMULATIONS = 50
PERFORMANCE_THRESHOLD_AVG_S = 0.5 # Seuil acceptable pour le temps de réponse moyen en secondes

def run_all_checks():
    """Exécute le test de charge pour mesurer les performances du moteur de suggestion."""
    print("--- Lancement du Test de Performance en Charge ---")
    
    try:
        jobs_data, questions_data, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    # --- Générer les profils en amont pour ne pas mesurer ce temps ---
    print(f"Génération de {NUM_SIMULATIONS} profils aléatoires...")
    profiles = [generate_random_profile(questions_data) for _ in range(NUM_SIMULATIONS)]
    print("Profils générés. Début des mesures de performance...")

    execution_times = []
    errors = []
    overall_success = True

    start_total_time = time.perf_counter()

    for i, profile in enumerate(profiles):
        print(f"\rExécution du profil {i+1}/{NUM_SIMULATIONS}...", end="")
        
        start_time = time.perf_counter()
        top_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)
        end_time = time.perf_counter()

        if top_jobs is None:
            errors.append(f"[Profil #{i+1}] L'exécution du moteur a échoué.")
            overall_success = False
            continue
        
        execution_times.append(end_time - start_time)

    end_total_time = time.perf_counter()
    total_duration = end_total_time - start_total_time

    print("\n\n--- Résultats de Performance ---")
    if not execution_times:
        errors.append("Aucune simulation n'a pu être complétée avec succès.")
        return False, errors

    avg_time = statistics.mean(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)
    
    result_summary = [
        f"Nombre de simulations : {len(execution_times)}",
        f"Temps total d\'exécution : {total_duration:.2f} secondes",
        f"Temps moyen par suggestion : {avg_time:.4f} secondes",
        f"Temps max pour une suggestion : {max_time:.4f} secondes",
        f"Temps min pour une suggestion : {min_time:.4f} secondes"
    ]

    print("\n".join(result_summary))

    if avg_time > PERFORMANCE_THRESHOLD_AVG_S:
        overall_success = False
        errors.append(f"Le temps moyen ({avg_time:.4f}s) dépasse le seuil de performance de {PERFORMANCE_THRESHOLD_AVG_S}s.")
        print(f"\n-> ❌ Performance insuffisante.")
    else:
        print(f"\n-> ✅ Performance acceptable.")

    print("--- Test de Performance Terminé ---\n")
    # Pour ce test, les messages sont informatifs plutôt que des erreurs pures
    return overall_success, errors + result_summary

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("\nLe test de performance a échoué. Problèmes trouvés :")
        for msg in messages:
            if "dépasse le seuil" in msg:
                print(f"- {msg}")
        sys.exit(1)
    else:
        print("\nLe test de performance a réussi.")
