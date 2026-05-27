import random

def generate_random_profile(questions_data):
    """Génère un profil utilisateur avec des réponses choisies au hasard.

    Supporte deux formats :
    - Jeune : {"questions": [...]}
    - Adulte : {"recipe": {...}, "dimensions": {"dim": [...]}}
    """
    answers = {}

    if 'questions' in questions_data:
        # Format jeune — tableau plat
        for question in questions_data['questions']:
            if question.get('options'):
                answers[question['id']] = random.choice(question['options'])
    elif 'dimensions' in questions_data:
        # Format adulte — dimensions + recipe
        recipe = questions_data.get('recipe', {})
        dimensions = questions_data['dimensions']
        for category, count in recipe.items():
            pool = [q for q in dimensions.get(category, [])
                    if q.get('options') and q.get('type') != 'dynamic_sector_choice']
            for q in random.sample(pool, min(count, len(pool))):
                if q.get('options'):
                    answers[q['id']] = random.choice(q['options'])

    return {"name": "Random Test User", "answers": answers}
