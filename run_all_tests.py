

import sys
import os
import time
import traceback
from datetime import datetime

# Force UTF-8 sur Windows (évite les crashes sur les emojis ✅ ❌ ▶️)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# --- Configuration et Importation des modules de test ---

def setup_path():
    """Ajoute le répertoire des tests au path pour l'importation."""
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

setup_path()

try:
    import test_data_integrity
    import test_suggestion_consistency
    import test_algorithm_stability
    import test_redundant_suggestions
    import test_bias_distribution
    import test_performance_load
    import test_job_coverage
except ImportError as e:
    print(f"[ERREUR] Impossible d'importer un module de test : {e}")
    print("Veuillez vous assurer que tous les scripts de test sont bien dans le dossier /tests.")
    sys.exit(1)

# --- Définition de la Suite de Tests ---

TEST_SUITE = [
    ("Test d'Intégrité des Données", test_data_integrity.run_all_checks),
    ("Test de Cohérence des Suggestions", test_suggestion_consistency.run_all_checks),
    ("Test de Stabilité de l'Algorithme", test_algorithm_stability.run_all_checks),
    ("Test de Redondance des Suggestions", test_redundant_suggestions.run_all_checks),
    ("Test de Biais de Distribution", test_bias_distribution.run_all_checks),
    ("Test de Performance en Charge", test_performance_load.run_all_checks),
    ("Test de Couverture des Métiers", test_job_coverage.run_all_checks),
]

# --- Moteur d'Exécution ---

def run_all_tests():
    """Exécute tous les tests définis dans la suite et génère un rapport."""
    print("==================================================")
    print("    Lancement de la Suite de Tests 'Adoré'      ")
    print("==================================================\n")

    results = []
    overall_success_count = 0
    total_start_time = time.perf_counter()

    for name, test_function in TEST_SUITE:
        test_start_time = time.perf_counter()
        success = False
        messages = []
        
        try:
            # Rediriger stdout pour capturer les prints des sous-scripts
            # (Non implémenté ici pour garder la sortie console en direct)
            print(f"▶️  Exécution de : {name}...")
            success, messages = test_function()
        except Exception:
            success = False
            messages = ["Le script de test a rencontré une erreur inattendue.", traceback.format_exc()]
        
        test_end_time = time.perf_counter()
        duration = test_end_time - test_start_time

        status_icon = "✅" if success else "❌"
        print(f"{status_icon} Résultat pour '{name}' : {'Succès' if success else 'Échec'} (en {duration:.2f}s)\n")

        results.append({
            "name": name,
            "success": success,
            "messages": messages,
            "duration": duration
        })

        if success:
            overall_success_count += 1

    total_end_time = time.perf_counter()
    total_duration = total_end_time - total_start_time

    # --- Génération du Rapport ---
    report_filename = generate_report(results, total_duration, overall_success_count, len(TEST_SUITE))

    print("==================================================")
    print("             Suite de Tests Terminée            ")
    print(f"RÉSULTAT GLOBAL : {overall_success_count}/{len(TEST_SUITE)} tests ont réussi.")
    print(f"Temps total : {total_duration:.2f} secondes.")
    print(f"Un rapport détaillé a été généré : {report_filename}")
    print("==================================================")

def generate_report(results, total_duration, success_count, total_count):
    """Génère un rapport de test en Markdown."""
    project_root = os.path.abspath(os.path.dirname(__file__))
    
    # Générer un nom de fichier unique avec horodatage
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"tests_report_{timestamp}.md"
    
    # Définir le chemin complet du rapport dans le dossier 'tests'
    report_dir = os.path.join(project_root, 'tests')
    os.makedirs(report_dir, exist_ok=True) # Assurer que le dossier 'tests' existe
    report_path = os.path.join(report_dir, report_filename)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Rapport de Test - Projet Adoré\n\n")
        f.write(f"**Date du rapport :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Durée totale :** {total_duration:.2f} secondes\n")
        f.write(f"**Résultat global :** {success_count}/{total_count} tests passés\n\n")
        f.write("## Résumé des Tests\n\n")

        for result in results:
            status_icon = "✅" if result["success"] else "❌"
            f.write(f"- **{status_icon} {result['name']}** ({result['duration']:.2f}s)\n")

        f.write("\n---\n\n## Détails des Tests\n\n")

        for result in results:
            status_icon = "✅" if result["success"] else "❌"
            f.write(f"### {status_icon} {result['name']}\n\n")
            f.write(f"- **Statut :** {'Succès' if result['success'] else 'Échec'}\n")
            f.write(f"- **Durée :** {result['duration']:.2f}s\n")
            
            if not result["success"]:
                f.write("- **Messages d'erreur :**\n")
                for msg in result["messages"]:
                    f.write(f"  ```\n  {msg}\n  ```\n")
            elif result['name'] == "Test de Performance en Charge": # Cas spécial pour afficher les métriques
                f.write("- **Métriques :**\n")
                for msg in result["messages"]:
                    f.write(f"  - {msg}\n")
            
            
            f.write("\\n---\n")
        return report_filename

if __name__ == "__main__":
    run_all_tests()
