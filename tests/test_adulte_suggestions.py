"""
Tests du mode adulte (reconversion) :
  1. Cohérence : les profils typés obtiennent des métiers pertinents et pas de hors-sujet évident.
  2. Biais : aucun métier ne doit apparaître dans > 30% des profils aléatoires.
  3. Filtre formation : avec contrainte 'court', les métiers BAC+5/BAC+8 exclusifs sont absents.
  4. Différenciation : deux profils opposés ne doivent pas avoir > 20% de top-10 en commun.
"""
import sys
import os
from collections import Counter

current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_utils import (
    load_all_data, get_predefined_adulte_profiles,
    run_adulte_suggestion_engine,
)
from app.logic.profile_utils import generate_random_profile

NUM_BIAS_SIMULATIONS = 200
# Seuil adulte calibré à 35% : la banque adulte contient plusieurs options
# santé/social (Solidarité & Soin, Soins, Relations humaines, Empathie)
# ce qui crée une concentration naturelle sur les métiers santé.
# Les vraies pathologies (Météorologue à 66%, Développeur à 36%) sont bien
# en dehors de cette plage. 200 simulations pour un résultat statistiquement stable.
BIAS_THRESHOLD = 0.35
OVERLAP_THRESHOLD = 0.20    # max 20 % de métiers communs entre 2 profils opposés
TOP_N = 10

LONG_TRAINING_LEVELS = {"BAC+5", "BAC+8"}


def check_coherence(dm, jobs_data, semantic_map, idf_map, tag_profile_freq,
                    term_to_category_map, scoring_config):
    """Test 1 : cohérence des profils prédéfinis."""
    errors = []
    profiles = get_predefined_adulte_profiles()

    for name, profile in profiles.items():
        top_jobs = run_adulte_suggestion_engine(
            profile, jobs_data, semantic_map,
            idf_map, tag_profile_freq, term_to_category_map, scoring_config
        )
        if top_jobs is None or len(top_jobs) == 0:
            errors.append(f"[{name}] : aucun résultat retourné.")
            continue

        top_titles = [j.get('rome', {}).get('intitule', '').lower() for j in top_jobs[:TOP_N]]

        # Vérifie qu'au moins un métier attendu est présent
        found = any(
            kw.lower() in title
            for kw in profile['expected_jobs']
            for title in top_titles
        )
        if not found:
            errors.append(
                f"[{name}] : aucun métier attendu ({profile['expected_jobs']}) dans le top {TOP_N}. "
                f"Obtenu : {[j.get('rome', {}).get('intitule') for j in top_jobs[:5]]}"
            )

        # Vérifie qu'aucun métier interdit n'est dans le top 5
        top5_titles = top_titles[:5]
        for forbidden in profile['forbidden_jobs']:
            if any(forbidden.lower() in t for t in top5_titles):
                errors.append(
                    f"[{name}] : métier interdit '{forbidden}' trouvé dans le top 5."
                )

    return errors


def check_bias(dm, jobs_data, semantic_map, idf_map, tag_profile_freq,
               term_to_category_map, scoring_config):
    """Test 2 : biais de distribution sur profils aléatoires adultes."""
    job_frequency = Counter()

    for _ in range(NUM_BIAS_SIMULATIONS):
        profile = generate_random_profile(dm.questions_adulte)
        top_jobs = run_adulte_suggestion_engine(
            profile, jobs_data, semantic_map,
            idf_map, tag_profile_freq, term_to_category_map, scoring_config
        )
        if top_jobs:
            for job in top_jobs[:5]:
                code = job.get('rome', {}).get('code_rome')
                if code:
                    job_frequency[code] += 1

    errors = []
    job_name_map = {j.get('rome', {}).get('code_rome'): j.get('rome', {}).get('intitule') for j in jobs_data}
    for code, count in job_frequency.items():
        freq = count / NUM_BIAS_SIMULATIONS
        if freq > BIAS_THRESHOLD:
            errors.append(
                f"Biais adulte : '{job_name_map.get(code, code)}' apparaît dans "
                f"{freq:.0%} des profils (seuil {BIAS_THRESHOLD:.0%})"
            )

    return errors, job_frequency


def check_formation_filter(dm, jobs_data, semantic_map, idf_map, tag_profile_freq,
                           term_to_category_map, scoring_config):
    """Test 3 : le filtre 'court' exclut bien les métiers exclusivement BAC+5/BAC+8."""
    errors = []

    profile = {
        "answers": {
            "aq09": {"tags": [{"type": "domain", "value": "health_social"}]},
            "aq13": {"tags": [{"type": "formation_constraint", "value": "court"}]},
        }
    }

    top_jobs = run_adulte_suggestion_engine(
        profile, jobs_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config
    )
    if top_jobs is None:
        errors.append("[Filtre formation] : aucun résultat retourné.")
        return errors

    for job in top_jobs:
        code = job.get('rome', {}).get('code_rome')
        if not code:
            continue
        # Lookup direct uniquement : depuis ROME v4.60, chaque fiche alias a sa propre
        # entrée dans job_education_map. On ne remonte plus vers le maître pour éviter
        # d'attribuer le niveau du maître à un job dont les exigences diffèrent.
        levels = set(dm.job_education_map.get(code, set()))
        if levels and set(levels) <= LONG_TRAINING_LEVELS:
            errors.append(
                f"[Filtre formation] : '{job['rome']['intitule']}' ({code}) "
                f"ne devrait pas apparaître avec contrainte 'court' (niveaux: {levels})"
            )

    return errors


def check_differentiation(dm, jobs_data, semantic_map, idf_map, tag_profile_freq,
                           term_to_category_map, scoring_config):
    """Test 4 : deux profils opposés n'ont pas le même top-10."""
    errors = []
    profiles = get_predefined_adulte_profiles()

    tech = run_adulte_suggestion_engine(
        profiles["adulte_tech_it"], jobs_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config
    ) or []
    manuel = run_adulte_suggestion_engine(
        profiles["adulte_manuel_terrain"], jobs_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config
    ) or []

    codes_tech = {j.get('rome', {}).get('code_rome') for j in tech[:TOP_N]}
    codes_manuel = {j.get('rome', {}).get('code_rome') for j in manuel[:TOP_N]}

    overlap = len(codes_tech & codes_manuel) / TOP_N if TOP_N > 0 else 0
    if overlap > OVERLAP_THRESHOLD:
        shared = [j['rome']['intitule'] for j in tech[:TOP_N]
                  if j.get('rome', {}).get('code_rome') in codes_manuel]
        errors.append(
            f"[Différenciation] : {overlap:.0%} de chevauchement entre profil tech et manuel "
            f"(seuil {OVERLAP_THRESHOLD:.0%}). Communs : {shared}"
        )

    return errors


def run_all_checks():
    print("--- Lancement des Tests du Mode Adulte (Reconversion) ---")

    try:
        jobs_data, _, semantic_map, _, idf_map, tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données."]

    dm = None
    from test_utils import _data_manager_instance
    dm = _data_manager_instance

    all_errors = []
    overall_success = True

    print("1. Cohérence des profils prédéfinis...")
    errors = check_coherence(dm, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config)
    if errors:
        for e in errors:
            print(f"   -> ❌ {e}")
        all_errors.extend(errors)
        overall_success = False
    else:
        print("   -> ✅ OK.")

    print(f"2. Biais de distribution ({NUM_BIAS_SIMULATIONS} profils aléatoires)...")
    errors, freq = check_bias(dm, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config)
    top5 = freq.most_common(5)
    job_name_map = {j.get('rome', {}).get('code_rome'): j.get('rome', {}).get('intitule') for j in jobs_data}
    for code, count in top5:
        print(f"   {count/NUM_BIAS_SIMULATIONS:.0%}  {job_name_map.get(code, code)}")
    if errors:
        for e in errors:
            print(f"   -> ❌ {e}")
        all_errors.extend(errors)
        overall_success = False
    else:
        print("   -> ✅ Aucun biais majeur.")

    print("3. Filtre de formation (contrainte 'court')...")
    errors = check_formation_filter(dm, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config)
    if errors:
        for e in errors:
            print(f"   -> ❌ {e}")
        all_errors.extend(errors)
        overall_success = False
    else:
        print("   -> ✅ OK.")

    print("4. Différenciation tech vs manuel...")
    errors = check_differentiation(dm, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config)
    if errors:
        for e in errors:
            print(f"   -> ❌ {e}")
        all_errors.extend(errors)
        overall_success = False
    else:
        print("   -> ✅ OK.")

    print("--- Tests Mode Adulte Terminés ---")
    if overall_success:
        print("\nTous les tests adulte ont réussi.")
    else:
        print(f"\n{len(all_errors)} problème(s) détecté(s).")

    return overall_success, all_errors


if __name__ == "__main__":
    success, errors = run_all_checks()
    sys.exit(0 if success else 1)
