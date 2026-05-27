import random

def generate_random_profile(questions_data):
    """Génère un profil utilisateur avec des réponses choisies au hasard."""
    answers = {}
    for question in questions_data.get('questions', []):
        if question.get('options'):
            selected_option = random.choice(question['options'])
            answers[question['id']] = selected_option
    
    return {
        "name": "Random Test User",
        "answers": answers
    }
