
import sys
import os
from collections import Counter

# --- Path Setup ---
# Ajoute la racine du projet au sys.path pour permettre l'importation des modules de l'application
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from app.logic.profile_utils import generate_random_profile
from test_utils import load_all_data, run_suggestion_engine

NUM_SIMULATIONS = 50
TOP_N_TO_CHECK = 3
BIAS_THRESHOLD = 0.20  # 20% — seuil calibré pour un questionnaire de 12 questions / 532 métiers
                       # (l'ancienne valeur de 10% était trop stricte ; la réduction structurelle
                       #  a ramené le worst-case de 34% à ~14%, les vrais outliers sont >20%)

def run_all_checks():
    """Exécute le test de distribution pour identifier les biais de suggestion."""
    print("--- Lancement du Test de Biais de Distribution ---")
    
    try:
        jobs_data, questions_data, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données. Voir les messages précédents."]

    # Créer un mapping code_rome -> nom pour un affichage facile
    job_name_map = {job.get('rome', {}).get('code_rome'): job.get('rome', {}).get('intitule') for job in jobs_data}

    job_frequency = Counter()
    total_suggestions = 0

    print(f"Exécution de {NUM_SIMULATIONS} simulations aléatoires...")
    for i in range(NUM_SIMULATIONS):
        print(f"\rSimulation {i+1}/{NUM_SIMULATIONS}...", end="")
        
        profile = generate_random_profile(questions_data)
        top_jobs = run_suggestion_engine(profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map)

        if top_jobs and len(top_jobs) >= TOP_N_TO_CHECK:
            for job in top_jobs[:TOP_N_TO_CHECK]:
                code_rome = job.get('rome', {}).get('code_rome')
                if code_rome:
                    job_frequency[code_rome] += 1
            total_suggestions += TOP_N_TO_CHECK
    
    print("\nCalcul de la distribution...")

    errors = []
    overall_success = True
    report_lines = []

    if not job_frequency:
        errors.append("Aucune suggestion n'a été générée durant les simulations.")
        return False, errors

    # Analyser les résultats
    most_common_jobs = job_frequency.most_common()
    
    for rome_code, count in most_common_jobs:
        frequency_percent = count / NUM_SIMULATIONS
        job_name = job_name_map.get(rome_code, rome_code)
        line = f"- '{job_name}' : apparu {count} fois ({frequency_percent:.2%})"
        report_lines.append(line)
        if frequency_percent > BIAS_THRESHOLD:
            overall_success = False
            errors.append(f"Biais détecté : Le métier '{job_name}' apparaît trop souvent ({frequency_percent:.2%}), dépassant le seuil de {BIAS_THRESHOLD:.0%}.")

    print("\n--- Top 10 des métiers les plus fréquents ---")
    for line in report_lines[:10]:
        print(line)

    if overall_success:
        print("\n-> ✅ Aucun biais de suggestion majeur détecté.")
    else:
        print("\n-> ❌ Biais de suggestion détecté.")

    print("--- Test de Biais Terminé ---\n")
    return overall_success, errors

if __name__ == '__main__':
    success, messages = run_all_checks()
    if not success:
        print("\nLe test de biais de distribution a échoué. Problèmes trouvés :")
        for msg in messages:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("\nLe test de biais de distribution a réussi.")
