from collections import Counter
import json
import os
from math import log # Needed for normalization

# --- NOUVEAUX PARAMÈTRES DE PONDÉRATION ---
# Les poids sont maintenant chargés depuis config/scoring.json via le DataManager

def generate_profile_summary(quality_scores, interest_scores, skill_scores):
    """Generates summary texts based on user's top qualities, interests, and skills."""
    top_qualities = [q for q, c in quality_scores.most_common(5)]
    top_interests = [i for i, c in interest_scores.most_common(5)]
    top_skills = [s for s, c in skill_scores.most_common(5)]

    def generate_summary_text(keywords, type):
        if not keywords:
            return ""
        
        formatted_keywords = ", ".join(keywords[:-1]) + " et " + keywords[-1] if len(keywords) > 1 else keywords[0]
        
        if type == 'qualities':
            return f"Tu sembles te distinguer par des qualités comme {formatted_keywords.lower()}."
        elif type == 'interests':
            return f"Tu montres un intérêt marqué pour des domaines variés tels que {formatted_keywords.lower()}."
        elif type == 'skills':
            return f"Tes réponses indiquent que tu as des aptitudes pour des compétences comme {formatted_keywords.lower()}."
        return ""

    user_strengths_summary = generate_summary_text(top_qualities, 'qualities')
    user_interests_summary = generate_summary_text(top_interests, 'interests')
    user_skills_summary = generate_summary_text(top_skills, 'skills')

    return user_strengths_summary, user_interests_summary, user_skills_summary


def calculate_recommendations(user_profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config, include_scores=False):
    """
    Calcule les recommandations de métiers en se basant sur le référentiel ROME
    et un dictionnaire sémantique pour une meilleure correspondance, en utilisant TF-IDF, normalisation, 
    soustraction de bruit de fond et une pondération par catégorie de tag.
    """
    # Extraire les paramètres de pondération de la configuration
    tag_category_weights = scoring_config.get("tag_category_weights", {})
    popularity_bias_factor = scoring_config.get("popularity_bias_factor", 2.4)

    # 1. Construire le profil de l'utilisateur
    user_answers = user_profile.get("answers", {})
    quality_scores = Counter()
    interest_scores = Counter()
    skill_scores = Counter()
    user_work_styles = Counter()

    for q_id, answer in user_answers.items():
        if isinstance(answer, dict) and 'tags' in answer:
            for tag in answer.get('tags', []):
                tag_type = tag.get('type')
                tag_value = tag.get('value')
                if tag_value:
                    if tag_type == "quality": quality_scores[tag_value] += 1
                    elif tag_type == "interest": interest_scores[tag_value] += 1
                    elif tag_type == "skill": skill_scores[tag_value] += 1
                    elif tag_type in ["work_style", "tag"]:
                        user_work_styles[tag_value] += 1
    
    user_profile_terms = Counter()
    for keyword, count in (quality_scores + interest_scores + skill_scores).items():
        search_terms = semantic_map.get(keyword, [keyword.lower()])
        for term in search_terms:
            for sub_term in term.split():
                user_profile_terms[sub_term] += count

    job_scores = []

    for job in jobs_data:
        raw_tf_idf_score = 0.0
        
        # Scoring TF-IDF pondéré par catégorie
        for term, tf_count in user_profile_terms.items():
            if term in job.get('_search_terms_list', []):
                # Récupérer la catégorie du terme et appliquer le poids correspondant
                category = term_to_category_map.get(term, "default")
                weight = tag_category_weights.get(category, 1.0)
                
                term_score = tf_count * idf_map.get(term, 0.0)
                raw_tf_idf_score += term_score * weight # Appliquer la pondération

        # Normalisation linéaire par nombre de termes uniques (évite l'avantage des longues descriptions)
        total_job_terms_count = job.get('_total_terms_count', 1)
        normalized_score = raw_tf_idf_score / total_job_terms_count

        # Pénalité adaptative par fiche (bruit de fond normalisé).
        # On n'applique PAS de soustraction hard (max(0, score - ERS)) car l'ERS, calculé sur l'ensemble
        # des termes du job, serait structurellement plus grand que le score du profil sur les seuls termes
        # en commun, ce qui zeriserait même des correspondances légitimes. On utilise uniquement l'ERS
        # comme diviseur adaptatif : plus un job a un fond élevé, moins son score final est amplifié.
        expected_raw = job.get('_expected_random_score', 0.0)
        expected_normalized = expected_raw / total_job_terms_count

        # 1. Pénalité adaptative par fiche (basée sur le bruit de fond normalisé)
        final_score = normalized_score / (1 + popularity_bias_factor * expected_normalized)

        # 2. Pénalité de popularité (basée sur le biais observé en simulation)
        final_score /= (1 + popularity_bias_factor * job.get('_popularity_bias', 0.0))
        
        job_scores.append({"job": job, "score": final_score})

    # 3. Trier et filtrer les résultats (avec clé secondaire pour la stabilité en cas d'égalité des scores)
    sorted_jobs = sorted(job_scores, key=lambda x: (x["score"], x["job"].get('rome', {}).get('code_rome', '')), reverse=True)
    top_jobs = sorted_jobs[:30]
    if include_scores:
        recommended_jobs_list = top_jobs
    else:
        recommended_jobs_list = [item["job"] for item in top_jobs]

    # 4. Extraire un résumé du profil
    user_strengths_summary, user_interests_summary, user_skills_summary = generate_profile_summary(
        quality_scores, interest_scores, skill_scores
    )

    weak_match = False
    if not sorted_jobs or sorted_jobs[0]["score"] < 0.5:
        weak_match = True

    return [], recommended_jobs_list, user_strengths_summary, [], weak_match, user_interests_summary, user_skills_summary


def calculate_reconversion_recommendations(user_profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config):
    """
    Calcule les recommandations de métiers spécifiquement pour un profil adulte en reconversion.
    Cette fonction utilisera un algorithme hybride qui pondère :
    1. Le score d'affinité (basé sur les intérêts et préférences).
    2. Un bonus de transférabilité (basé sur les compétences et l'expérience passée).
    3. Des filtres de contraintes (durée de formation, etc. - à implémenter).
    """
    # Extraire les paramètres de pondération de la configuration
    tag_category_weights = scoring_config.get("tag_category_weights", {})
    popularity_bias_factor = scoring_config.get("popularity_bias_factor", 2.4)
    reconversion_engine_weights = scoring_config.get("reconversion_engine_weights", {})
    
    affinity_weight = reconversion_engine_weights.get("affinity_score", 0.6)
    transferability_weight = reconversion_engine_weights.get("transferability_bonus", 0.4)

    # 1. Construire le profil de l'utilisateur
    user_answers = user_profile.get("answers", {})
    quality_scores = Counter()
    interest_scores = Counter()
    skill_scores = Counter()
    user_work_styles = Counter()
    domain_scores = Counter()
    user_experience_sector = None

    for q_id, answer in user_answers.items():
        if isinstance(answer, dict) and 'tags' in answer:
            for tag in answer.get('tags', []):
                tag_type = tag.get('type')
                tag_value = tag.get('value')
                if tag_value:
                    if tag_type == "quality": quality_scores[tag_value] += 1
                    elif tag_type == "interest": interest_scores[tag_value] += 1
                    elif tag_type == "skill": skill_scores[tag_value] += 1
                    elif tag_type == "domain": domain_scores[tag_value] += 1
                    elif tag_type == "experience_sector":
                        user_experience_sector = tag_value
                    elif tag_type in ["work_style", "tag"]:
                        user_work_styles[tag_value] += 1

    user_profile_terms = Counter()
    for keyword, count in (quality_scores + interest_scores + skill_scores + user_work_styles + domain_scores).items():
        search_terms = semantic_map.get(keyword, [keyword.lower()])
        for term in search_terms:
            for sub_term in term.split():
                user_profile_terms[sub_term] += count

    # Passe 1 : calcul des scores d'affinité bruts pour tous les métiers
    raw_job_scores = []
    for job in jobs_data:
        raw_tf_idf_score = 0.0
        match_reasons = []

        for term, tf_count in user_profile_terms.items():
            if term in job.get('_search_terms_list', []):
                category = term_to_category_map.get(term, "default")
                weight = tag_category_weights.get(category, 1.0)
                term_score = tf_count * idf_map.get(term, 0.0)
                raw_tf_idf_score += term_score * weight
                match_reasons.append(f"Affinité avec '{term}' (score: {term_score * weight:.2f})")

        _n = job.get('_total_terms_count', 1)
        raw_job_scores.append({
            "job": job,
            "affinity": raw_tf_idf_score / _n,
            "match_reasons": match_reasons,
        })

    # Normalisation de l'affinité sur [0, 1] pour calibrer le bonus de transférabilité
    max_affinity = max((item["affinity"] for item in raw_job_scores), default=1.0) or 1.0

    # Passe 2 : combinaison affinité + transférabilité + pénalités
    job_scores = []
    job_sectors_lower_cache = {
        job.get('rome', {}).get('code_rome'): [s.lower() for s in job.get('secteurs_activite', [])]
        for job in jobs_data
    }

    for item in raw_job_scores:
        job = item["job"]
        match_reasons = item["match_reasons"]
        normalized_affinity = item["affinity"] / max_affinity  # dans [0, 1]
        _n = job.get('_total_terms_count', 1)

        # --- 3. Calcul du bonus de transférabilité (normalisé) ---
        transferability_score = 0.0
        if user_experience_sector and user_experience_sector != "aucun":
            code = job.get('rome', {}).get('code_rome')
            if user_experience_sector.lower() in job_sectors_lower_cache.get(code, []):
                transferability_score = 1.0
                match_reasons = match_reasons + [f"Bonus de transférabilité : secteur '{user_experience_sector}'"]

        # --- 4. Combinaison pondérée (affinité et transférabilité dans [0, 1]) ---
        combined_score = (normalized_affinity * affinity_weight) + (transferability_score * transferability_weight)

        # --- 5. Pénalités bruit de fond et popularité ---
        expected_normalized = job.get('_expected_random_score', 0.0) / _n
        final_score = combined_score / (1 + popularity_bias_factor * expected_normalized)
        final_score /= (1 + popularity_bias_factor * job.get('_popularity_bias', 0.0))

        job_scores.append({"job": job, "score": final_score, "match_reasons": match_reasons})

    # --- 6. Trier et filtrer les résultats ---
    sorted_jobs = sorted(job_scores, key=lambda x: (x["score"], x["job"].get('rome', {}).get('code_rome', '')), reverse=True)
    top_jobs = sorted_jobs[:30]
    
    recommended_jobs_list = []
    for item in top_jobs:
        # Enrichir l'objet job avec les raisons du match pour l'affichage
        job_with_reasons = item["job"].copy()
        job_with_reasons["_match_reasons"] = item["match_reasons"]
        recommended_jobs_list.append(job_with_reasons)

    # --- 7. Extraire un résumé du profil ---
    user_strengths_summary, user_interests_summary, user_skills_summary = generate_profile_summary(
        quality_scores, interest_scores, skill_scores
    )

    weak_match = False
    if not sorted_jobs or sorted_jobs[0]["score"] < 0.5:
        weak_match = True

    return [], recommended_jobs_list, user_strengths_summary, [], weak_match, user_interests_summary, user_skills_summary