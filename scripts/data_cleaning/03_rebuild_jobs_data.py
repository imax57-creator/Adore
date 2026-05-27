
import ijson
import json
import os
import sys

def rebuild_jobs_data():
    """
    Reconstruit la base de données des métiers en se basant sur une liste de codes ROME maîtres
    et une carte d'appellations pour produire un fichier propre et dédupliqué.
    Génère également un rapport sur l'opération de nettoyage.
    """
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

    # Fichiers d'entrée
    master_codes_file = os.path.join(script_dir, 'master_codes.json')
    appellation_map_file = os.path.join(script_dir, 'appellation_map.json')
    raw_jobs_file = os.path.join(project_root, 'RefRomeJson', 'unix_fiche_emploi_metier_v460.json')

    # Fichiers de sortie
    clean_output_file = os.path.join(script_dir, 'jobs_rome_clean.json')
    summary_output_file = os.path.join(script_dir, 'cleaning_summary.json')

    print("--- Début de la reconstruction de la base de données métiers ---")

    # Vérification des fichiers d'entrée
    for f in [master_codes_file, appellation_map_file, raw_jobs_file]:
        if not os.path.exists(f):
            print(f"ERREUR : Fichier d'entrée manquant : {f}")
            sys.exit(1)

    # 1. Charger les données préparatoires
    with open(master_codes_file, 'r', encoding='utf-8') as f:
        master_codes = set(json.load(f))
    with open(appellation_map_file, 'r', encoding='utf-8') as f:
        appellation_map = json.load(f)
    
    print(f"{len(master_codes)} codes maîtres et {len(appellation_map)} mappages d'appellations chargés.")

    # 2. Initialiser les compteurs pour le rapport
    stats = {
        "total_fiches_avant": 0,
        "total_fiches_apres": 0,
        "doublons_supprimes": 0,
        "appellations_total": 0
    }

    new_jobs_data = []

    # 3. Traiter le fichier de fiches métiers en streaming
    try:
        # Utilisation de l'encodage 'latin-1'
        with open(raw_jobs_file, 'r', encoding='latin-1') as f_in:
            parser = ijson.items(f_in, 'item')
            for job_entry in parser:
                stats["total_fiches_avant"] += 1
                
                # Correction : le code ROME est dans un sous-objet
                code_rome = job_entry.get('rome', {}).get('code_rome')

                # Filtrer pour ne garder que les fiches maîtres
                if code_rome in master_codes:
                    stats["total_fiches_apres"] += 1
                    
                    # Remplacer/créer la liste des appellations
                    official_appellations = appellation_map.get(code_rome, [])
                    # La fiche brute contient déjà les appellations, nous allons les fusionner par sécurité
                    existing_appellations = [app.get('libelle') for app in job_entry.get('appellations', []) if app.get('libelle')]
                    all_appellations = set(official_appellations + existing_appellations)
                    job_entry['appellations'] = sorted(list(all_appellations))
                    stats["appellations_total"] += len(job_entry['appellations'])

                    new_jobs_data.append(job_entry)
                else:
                    stats["doublons_supprimes"] += 1
        
        # 4. Sauvegarder la base de données nettoyée
        with open(clean_output_file, 'w', encoding='utf-8') as f_out:
            json.dump(new_jobs_data, f_out, indent=2, ensure_ascii=False)
        
        print(f"✅ Base de données nettoyée et sauvegardée dans {clean_output_file}")

        # 5. Sauvegarder le rapport
        with open(summary_output_file, 'w', encoding='utf-8') as f_summary:
            json.dump(stats, f_summary, indent=2)

        print("✅ Rapport de nettoyage généré.")
        print("--- Résumé de l'opération ---")
        print(f"  Fiches métiers lues : {stats['total_fiches_avant']}")
        print(f"  Fiches maîtres conservées : {stats['total_fiches_apres']}")
        print(f"  Doublons supprimés : {stats['doublons_supprimes']}")
        print(f"  Total des appellations intégrées : {stats['appellations_total']}")

    except Exception as e:
        print(f"Une erreur est survenue durant la reconstruction : {e}")
        sys.exit(1)

if __name__ == "__main__":
    rebuild_jobs_data()
