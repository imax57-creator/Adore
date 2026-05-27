import json
import os
import sys

def validate_cleaning():
    """
    Valide le fichier de données nettoyé en le comparant à l'original et
    à la liste des codes maîtres pour assurer l'intégrité des données.
    """
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

    # Fichiers à valider/comparer
    master_codes_file = os.path.join(script_dir, 'master_codes.json')
    clean_jobs_file = os.path.join(script_dir, 'jobs_rome_clean.json')
    original_jobs_file = os.path.join(project_root, 'data', 'jobs_rome.json')

    print("--- Début de la validation du nettoyage ---")

    # Vérification de l'existence des fichiers
    for f in [master_codes_file, clean_jobs_file, original_jobs_file]:
        if not os.path.exists(f):
            print(f"ERREUR : Fichier manquant pour la validation : {f}")
            return False # Le pipeline utilisera ce code de retour

    errors = []

    try:
        # Charger les données
        with open(master_codes_file, 'r', encoding='utf-8') as f:
            master_codes = set(json.load(f))
        with open(clean_jobs_file, 'r', encoding='utf-8') as f:
            clean_data = json.load(f)
        # Utilisation de utf-8-sig pour gérer le BOM
        with open(original_jobs_file, 'r', encoding='utf-8-sig') as f:
            original_data = json.load(f)

        # --- Début des vérifications ---
        print(f"Fichier original : {len(original_data)} fiches.")
        print(f"Fichier nettoyé : {len(clean_data)} fiches.")

        # 1. Vérifier que le nombre de fiches nettoyées correspond au nombre de codes maîtres
        if len(clean_data) != len(master_codes):
            errors.append(f"Échec de la validation du nombre de fiches : {len(clean_data)} fiches trouvées, {len(master_codes)} attendues.")
        else:
            print("✅ 1. Nombre de fiches nettoyées : OK")

        # 2. Vérifier que tous les codes maîtres sont présents
        clean_codes = {entry.get('rome', {}).get('code_rome') for entry in clean_data}
        missing_masters = master_codes - clean_codes
        if missing_masters:
            errors.append(f"{len(missing_masters)} codes maîtres sont manquants dans le fichier nettoyé. Ex: {list(missing_masters)[:5]}")
        else:
            print("✅ 2. Présence de tous les codes maîtres : OK")

        # 3. Vérifier l'absence de doublons dans le fichier final
        if len(clean_codes) != len(clean_data):
            errors.append("Des codes ROME dupliqués existent encore dans le fichier nettoyé.")
        else:
            print("✅ 3. Absence de doublons : OK")

        # 4. Vérifier que chaque fiche a une liste d'appellations
        missing_appellations = [entry.get('rome', {}).get('code_rome') for entry in clean_data if 'appellations' not in entry or not isinstance(entry['appellations'], list)]
        if missing_appellations:
            errors.append(f"{len(missing_appellations)} fiches n'ont pas de liste d'appellations. Ex: {missing_appellations[:5]}")
        else:
            print("✅ 4. Présence de la liste d'appellations : OK")

        # --- Fin des vérifications ---
        print("-------------------------------------")
        if not errors:
            print("🎉 VALIDATION RÉUSSIE : Le fichier de données nettoyé est cohérent.")
            return True
        else:
            print("❌ VALIDATION ÉCHOUÉE : Des problèmes ont été détectés.")
            for error in errors:
                print(f"   - {error}")
            return False

    except Exception as e:
        print(f"Une erreur est survenue durant la validation : {e}")
        return False

if __name__ == "__main__":
    if not validate_cleaning():
        sys.exit(1)