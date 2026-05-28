"""
Teste la couverture du catalogue ROME :
  1. Exclusion structurelle : métiers sans termes de recherche (score = 0 garanti).
  2. Couverture empirique  : % du catalogue atteint sur N profils aléatoires.
  3. Profils ciblés        : métiers pertinents absents des suggestions pour des
                             profils fortement typés (créatif, tech, social).
"""
import sys
import os
from collections import Counter

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.logic.profile_utils import generate_random_profile
from test_utils import load_all_data, get_data_manager, run_suggestion_engine, run_adulte_suggestion_engine, get_predefined_profiles

NUM_SIMULATIONS = 200   # profils aléatoires pour la couverture empirique
TOP_N = 30              # taille de la liste de suggestions inspectée
MIN_COVERAGE_RATE = 0.15  # au moins 15 % du catalogue doit être accessible


# ── 1. EXCLUSION STRUCTURELLE ────────────────────────────────────────────────

def check_structural_exclusions(jobs_data):
    """Détecte les métiers qui n'ont aucun terme de recherche indexé (score = 0 systématique)."""
    excluded = []
    for job in jobs_data:
        terms = job.get('_search_terms_list', [])
        if not terms or len(set(terms)) == 0:
            excluded.append({
                'code': job.get('rome', {}).get('code_rome', '?'),
                'name': job.get('rome', {}).get('intitule', 'Inconnu'),
            })
    return excluded


# ── 2. COUVERTURE EMPIRIQUE ──────────────────────────────────────────────────

def check_empirical_coverage(jobs_data, questions_data, semantic_map, idf_map,
                              tag_profile_freq, term_to_category_map, scoring_config,
                              engine_fn=None, label=""):
    """Calcule le taux de couverture du catalogue sur NUM_SIMULATIONS profils aléatoires.

    engine_fn : fonction(profile, jobs, sem_map, idf, tpf, t2c, cfg) → liste de jobs.
                Par défaut : run_suggestion_engine (moteur jeune).
    label     : libellé affiché dans la console (ex. "jeune", "adulte").
    """
    if engine_fn is None:
        engine_fn = run_suggestion_engine

    all_codes = {
        job.get('rome', {}).get('code_rome')
        for job in jobs_data
        if job.get('rome', {}).get('code_rome')
    }
    name_map = {
        job.get('rome', {}).get('code_rome'): job.get('rome', {}).get('intitule')
        for job in jobs_data
    }

    seen = Counter()
    prefix = f"[{label}] " if label else ""

    print(f"  {prefix}Catalogue : {len(all_codes)} métiers. Simulation de {NUM_SIMULATIONS} profils...")
    for i in range(NUM_SIMULATIONS):
        print(f"\r  {prefix}Simulation {i + 1}/{NUM_SIMULATIONS}...", end="")
        profile = generate_random_profile(questions_data)
        results = engine_fn(
            profile, jobs_data, semantic_map,
            idf_map, tag_profile_freq, term_to_category_map, scoring_config
        )
        for job in results[:TOP_N]:
            code = job.get('rome', {}).get('code_rome')
            if code:
                seen[code] += 1
    print()

    never_seen = sorted(all_codes - set(seen.keys()))
    coverage_rate = len(seen) / len(all_codes) if all_codes else 0.0

    top10 = [
        f"  {name_map.get(c, c)} ({n}/{NUM_SIMULATIONS} = {n/NUM_SIMULATIONS:.0%})"
        for c, n in seen.most_common(10)
    ]
    never_sample = [
        f"  [{c}] {name_map.get(c, 'Inconnu')}"
        for c in never_seen[:20]
    ]

    return coverage_rate, len(never_seen), len(all_codes), top10, never_sample


# ── 3. PROFILS CIBLÉS ────────────────────────────────────────────────────────

def check_targeted_profiles(jobs_data, questions_data, semantic_map, idf_map,
                             tag_profile_freq, term_to_category_map, scoring_config):
    """Vérifie que des profils fortement typés produisent au moins un métier attendu."""
    profiles = get_predefined_profiles(questions_data)
    name_map = {
        job.get('rome', {}).get('code_rome'): job.get('rome', {}).get('intitule', '')
        for job in jobs_data
    }

    errors = []
    messages = []

    for profile_name, profile_def in profiles.items():
        if not profile_def.get('answers'):
            messages.append(f"  [SKIP] {profile_name} : aucune réponse valide construite.")
            continue

        results = run_suggestion_engine(
            profile_def, jobs_data, semantic_map,
            idf_map, tag_profile_freq, term_to_category_map, scoring_config
        )
        suggested_names = [
            (job.get('rome', {}).get('intitule') or '').lower()
            for job in results[:TOP_N]
        ]

        expected = profile_def.get('expected_jobs', [])
        matched = [
            kw for kw in expected
            if any(kw.lower() in name for name in suggested_names)
        ]

        ratio = len(matched) / len(expected) if expected else 1.0
        status = "OK" if matched else "MISS"
        messages.append(
            f"  [{status}] {profile_name} : {len(matched)}/{len(expected)} mots-clés trouvés "
            f"({', '.join(matched) if matched else 'aucun'})"
        )

        if not matched:
            errors.append(
                f"Profil '{profile_name}' ({profile_def['description']}) : "
                f"aucun des métiers attendus ({', '.join(expected)}) n'apparaît dans les {TOP_N} suggestions."
            )

    return errors, messages


# ── RUNNER ────────────────────────────────────────────────────────────────────

def run_all_checks():
    print("--- Lancement du Test de Couverture des Métiers ---")

    try:
        jobs_data, questions_data, semantic_map, _, idf_map, \
            tag_profile_freq, term_to_category_map, scoring_config = load_all_data()
    except SystemExit:
        return False, ["Échec du chargement des données."]

    errors = []
    messages = []
    overall_success = True

    # 1. Exclusion structurelle
    print("\n[1/3] Vérification des exclusions structurelles...")
    excluded = check_structural_exclusions(jobs_data)
    if excluded:
        errors.append(
            f"{len(excluded)} métier(s) sans termes indexés (toujours score 0) : "
            + ", ".join(f"[{j['code']}] {j['name']}" for j in excluded[:10])
        )
        overall_success = False
        messages.append(f"  Exclusions structurelles : {len(excluded)} métier(s) détecté(s).")
    else:
        messages.append("  Exclusions structurelles : aucune détectée.")

    # 2. Couverture empirique — quiz jeune
    print("\n[2/3] Couverture empirique du catalogue...")
    print("  --- Quiz Jeune ---")
    coverage_rate, never_count, total, top10, never_sample = check_empirical_coverage(
        jobs_data, questions_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config,
        engine_fn=run_suggestion_engine, label="jeune"
    )
    messages.append("  [Quiz Jeune]")
    messages.append(
        f"  Couverture : {total - never_count}/{total} métiers atteints "
        f"({coverage_rate:.1%}) sur {NUM_SIMULATIONS} profils aléatoires."
    )
    messages.append(f"  Métiers jamais suggérés : {never_count}/{total} ({never_count/total:.1%})")
    messages.append("  Top 10 des plus suggérés :")
    messages.extend(top10)
    if never_sample:
        messages.append(f"  Exemple de métiers jamais vus (sur {NUM_SIMULATIONS} tirages) :")
        messages.extend(never_sample)

    if coverage_rate < MIN_COVERAGE_RATE:
        errors.append(
            f"[Jeune] Couverture trop faible : {coverage_rate:.1%} du catalogue atteint "
            f"(minimum requis : {MIN_COVERAGE_RATE:.0%})."
        )
        overall_success = False

    # 2b. Couverture empirique — quiz adulte
    dm = get_data_manager()
    questions_adulte = dm.questions_adulte if dm else None
    if questions_adulte:
        print("  --- Quiz Adulte ---")
        coverage_adulte, never_adulte, _, top10_adulte, never_sample_adulte = check_empirical_coverage(
            jobs_data, questions_adulte, semantic_map,
            idf_map, tag_profile_freq, term_to_category_map, scoring_config,
            engine_fn=run_adulte_suggestion_engine, label="adulte"
        )
        messages.append("  [Quiz Adulte]")
        messages.append(
            f"  Couverture : {total - never_adulte}/{total} métiers atteints "
            f"({coverage_adulte:.1%}) sur {NUM_SIMULATIONS} profils aléatoires."
        )
        messages.append(f"  Métiers jamais suggérés : {never_adulte}/{total} ({never_adulte/total:.1%})")
        messages.append("  Top 10 des plus suggérés :")
        messages.extend(top10_adulte)
        if never_sample_adulte:
            messages.append(f"  Exemple de métiers jamais vus (sur {NUM_SIMULATIONS} tirages) :")
            messages.extend(never_sample_adulte)

        if coverage_adulte < MIN_COVERAGE_RATE:
            errors.append(
                f"[Adulte] Couverture trop faible : {coverage_adulte:.1%} du catalogue atteint "
                f"(minimum requis : {MIN_COVERAGE_RATE:.0%})."
            )
            overall_success = False

    # 3. Profils ciblés
    print("\n[3/3] Vérification des profils ciblés...")
    targeted_errors, targeted_msgs = check_targeted_profiles(
        jobs_data, questions_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config
    )
    messages.extend(targeted_msgs)
    if targeted_errors:
        errors.extend(targeted_errors)
        overall_success = False

    # Résumé
    adulte_summary = f" | adulte {coverage_adulte:.1%}" if questions_adulte else ""
    if overall_success:
        print(f"\n-> Jeune {coverage_rate:.1%}{adulte_summary} | {never_count} métiers jamais vus (jeune) | profils ciblés OK")
        print("-> Test de couverture réussi.")
    else:
        print(f"\n-> Jeune {coverage_rate:.1%}{adulte_summary} | {never_count} métiers jamais vus (jeune)")
        print("-> Test de couverture échoué.")

    print("--- Test de Couverture Terminé ---\n")
    return overall_success, errors + messages


if __name__ == '__main__':
    success, messages = run_all_checks()
    print("\n".join(messages))
    if not success:
        sys.exit(1)
