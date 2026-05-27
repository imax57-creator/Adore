
import json
import os
import sys
import random
from collections import Counter

# --- Path Setup ---
# Ajoute la racine du projet au sys.path pour permettre l'importation des modules de l'application
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.logic.questionnaire_logic import calculate_recommendations
from app.data_manager import DataManager, DataError # Import DataManager

# --- Data Loading Utilities ---

# Create a single DataManager instance for all tests
# This ensures IDF and tag_profile_freq are calculated once
_data_manager_instance = None

def load_all_data():
    """Charge tous les fichiers de données JSON nécessaires pour les tests."""
    global _data_manager_instance
    if _data_manager_instance is None:
        try:
            _data_manager_instance = DataManager()
        except DataError as e:
            print(f"[ERREUR] Erreur lors du chargement des données : {e}", file=sys.stderr)
            sys.exit(1)

    dm = _data_manager_instance
    return (dm.jobs,
            dm.questions_jeune,
            dm.semantic_map,
            dm.tags_master,
            dm.idf,
            dm.tag_profile_freq,
            dm.term_to_category,
            dm.scoring_config)

# --- Profile Simulation Utilities ---

def get_predefined_profiles(questions_data):
    """Retourne un dictionnaire de profils de test prédéfinis avec des réponses ciblées."""
    
    questions_map = {q['id']: q for q in questions_data.get('questions', [])}
    profiles = {
        "creative_profile": {
            "description": "Profil axé sur la création, l'art et l'expression.",
            "answers": {
                'q01': find_option_with_tag(questions_map['q01'], 'Créativité visuelle'),
                'q03': find_option_with_tag(questions_map['q03'], 'Création artistique'),
                'q04': find_option_with_tag(questions_map['q04'], 'Création artistique'),
                'q05': find_option_with_tag(questions_map['q05'], 'Aime construire'),
                'q09': find_option_with_tag(questions_map['q09'], 'Création artistique'),
            },
            "expected_jobs": ["Designer", "Architecte", "Artiste", "Musicien", "Photographe"]
        },
        "tech_profile": {
            "description": "Profil axé sur la technologie, la logique et la résolution de problèmes.",
            "answers": {
                'q02': find_option_with_tag(questions_map['q02'], 'Résolution de problèmes'),
                'q03': find_option_with_tag(questions_map['q03'], 'Technologie'),
                'q05': find_option_with_tag(questions_map['q05'], 'Logique'),
                'q06': find_option_with_tag(questions_map['q06'], 'Découverte'),
                'q08': find_option_with_tag(questions_map['q08'], 'Rigueur'),
            },
            "expected_jobs": ["Développeur", "Informaticien", "Ingénieur", "Data analyst", "Administrateur systèmes"]
        },
        "social_profile": {
            "description": "Profil axé sur l'aide, le soin et les relations humaines.",
            "answers": {
                'q04': find_option_with_tag(questions_map['q04'], 'Solidarité & Soin'),
                'q07': find_option_with_tag(questions_map['q07'], 'Solidarité & Soin'),
                'q09': find_option_with_tag(questions_map['q09'], 'Empathie'),
                'q11': find_option_with_tag(questions_map['q11'], 'Transmission'),
                'q12': find_option_with_tag(questions_map['q12'], 'helping_others'),
            },
            "expected_jobs": ["Infirmier", "Médecin", "Psychologue", "Assistant social", "Éducateur"]
        }
    }
    # Filtrer les réponses nulles si une option n'a pas été trouvée
    for name, profile in profiles.items():
        profile['answers'] = {k: v for k, v in profile['answers'].items() if v is not None}

    return profiles

def find_option_with_tag(question, target_tag):
    """Utilitaire pour trouver la première option d'une question qui contient un tag spécifique."""
    if not question:
        return None
    for option in question.get('options', []):
        for tag in option.get('tags', []):
            if tag.get('value') == target_tag:
                return option
    return None

# --- Core Logic Wrapper ---

def run_suggestion_engine(user_profile, jobs_data, semantic_map, idf_map, tag_profile_freq, term_to_category_map, scoring_config=None):
    """Wrapper pour exécuter le moteur de suggestion et retourner les résultats."""
    if scoring_config is None:
        # Charger la config par défaut si non fournie
        dm = _data_manager_instance or load_all_data()
        scoring_config = _data_manager_instance.scoring_config
    _, jobs, _, _, _, _, _ = calculate_recommendations(
        user_profile, jobs_data, semantic_map,
        idf_map, tag_profile_freq, term_to_category_map, scoring_config
    )
    return jobs
