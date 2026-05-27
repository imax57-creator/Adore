
import subprocess
import sys
import os

def run_pipeline():
    """
    Exécute l'ensemble du pipeline de nettoyage de données, un script après l'autre,
    en s'assurant que chaque étape réussit avant de passer à la suivante.
    """
    script_dir = os.path.dirname(__file__)
    
    # L'ordre est crucial
    scripts_to_run = [
        '01_extract_master_codes.py',
        '02_build_appellation_map.py',
        '03_rebuild_jobs_data.py',
        '04_validate_cleaning.py'
    ]

    print("==================================================")
    print(" Lancement du Pipeline de Nettoyage des Données ROME ")
    print("==================================================")

    for script_name in scripts_to_run:
        script_path = os.path.join(script_dir, script_name)
        
        if not os.path.exists(script_path):
            print(f"\n❌ ERREUR : Script manquant : {script_name}")
            sys.exit(1)

        print(f"\n▶️  Exécution de : {script_name}...")
        
        try:
            # Utilise le même interpréteur Python pour exécuter le script
            # check=True lève une exception si le script retourne un code de sortie non nul
            subprocess.run([sys.executable, script_path], check=True, text=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Le script '{script_name}' a échoué avec le code de sortie {e.returncode}.")
            print("   Arrêt du pipeline.")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Une erreur inattendue est survenue lors de l'exécution de '{script_name}': {e}")
            print("   Arrêt du pipeline.")
            sys.exit(1)

    print("\n==================================================")
    print("🎉 Pipeline de Nettoyage Terminé avec Succès ! ")
    print("==================================================")
    print("\nProchaines étapes recommandées :")
    print("1. Remplacer 'data/jobs_rome.json' par le fichier 'scripts/data_cleaning/jobs_rome_clean.json'.")
    print("2. Lancer la suite de tests complète (`run_all_tests.py`) pour confirmer la correction du biais.")

if __name__ == "__main__":
    run_pipeline()
