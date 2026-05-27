
import subprocess
import sys
import os
import shutil

def run_pipeline():
    """
    Exécute l'ensemble du pipeline de nettoyage et d'enrichissement des données ROME.
    Étapes :
      1-4. Nettoyage (extraction des codes, appellations, reconstruction, validation)
      5.   Copie automatique vers data/jobs_rome.json
      6.   Enrichissement (enrich_jobs_data.py) → data/jobs_rome_enriched.json
    """
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

    # L'ordre est crucial.
    # La copie vers data/jobs_rome.json (étape 5) est faite AVANT la validation (étape 4)
    # car le script de validation compare jobs_rome_clean.json contre data/jobs_rome.json.
    cleaning_scripts = [
        '01_extract_master_codes.py',
        '02_build_appellation_map.py',
        '03_rebuild_jobs_data.py',
    ]

    print("==================================================")
    print(" Lancement du Pipeline de Nettoyage des Données ROME ")
    print("==================================================")

    for script_name in cleaning_scripts:
        script_path = os.path.join(script_dir, script_name)

        if not os.path.exists(script_path):
            print(f"\n❌ ERREUR : Script manquant : {script_name}")
            sys.exit(1)

        print(f"\n▶️  Exécution de : {script_name}...")

        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            subprocess.run([sys.executable, '-X', 'utf8', script_path], check=True, text=True, encoding='utf-8', env=env)
        except subprocess.CalledProcessError as e:
            print(f"\nERREUR : Le script '{script_name}' a échoué avec le code de sortie {e.returncode}.")
            print("   Arrêt du pipeline.")
            sys.exit(1)
        except Exception as e:
            print(f"\nERREUR inattendue lors de l'exécution de '{script_name}': {e}")
            print("   Arrêt du pipeline.")
            sys.exit(1)

    # Étape 4 : Copie vers data/jobs_rome.json (avant validation)
    clean_file = os.path.join(script_dir, 'jobs_rome_clean.json')
    dest_file = os.path.join(project_root, 'data', 'jobs_rome.json')
    print(f"\n▶️  Copie de jobs_rome_clean.json → data/jobs_rome.json...")
    try:
        shutil.copy2(clean_file, dest_file)
        print(f"   -> Copié avec succès ({dest_file})")
    except Exception as e:
        print(f"\n❌ Échec de la copie : {e}")
        sys.exit(1)

    # Étape 5 : Validation
    validate_script = os.path.join(script_dir, '04_validate_cleaning.py')
    print(f"\n>>> Execution : 04_validate_cleaning.py...")
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, '-X', 'utf8', validate_script], check=True, text=True, encoding='utf-8', env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERREUR : La validation a échoué avec le code de sortie {e.returncode}.")
        sys.exit(1)

    # Étape 6 : Enrichissement
    enrich_script = os.path.join(project_root, 'scripts', 'enrich_jobs_data.py')
    print(f"\n>>> Execution : enrich_jobs_data.py...")
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, '-X', 'utf8', enrich_script], check=True, text=True, encoding='utf-8', env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERREUR : L'enrichissement a échoué avec le code de sortie {e.returncode}.")
        sys.exit(1)

    # Supprimer le cache de biais de popularité (sera recalculé avec le nouveau catalogue)
    bias_cache = os.path.join(project_root, 'data', 'popularity_bias.json')
    if os.path.exists(bias_cache):
        os.remove(bias_cache)
        print(f"\n🗑  Cache popularity_bias.json supprimé (sera recalculé au prochain démarrage).")

    print("\n==================================================")
    print("Pipeline Terminé avec Succès !")
    print("==================================================")
    print("\nProchaine étape :")
    print("  Lancer la suite de tests complète : python run_all_tests.py")

if __name__ == "__main__":
    run_pipeline()
