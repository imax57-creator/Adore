import ijson
import json
import os
import sys
from collections import defaultdict

def build_appellation_map():
    """
    Lit le référentiel des appellations, crée une carte liant les codes ROME parents
    à leurs appellations, et détecte les éventuelles ambiguïtés (une appellation
    liée à plusieurs parents).
    """
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    
    input_file = os.path.join(project_root, 'RefRomeJson', 'unix_referentiel_appellation_v460.json')
    map_output_file = os.path.join(script_dir, 'appellation_map.json')
    ambiguities_log_file = os.path.join(script_dir, 'ambiguities.log')

    print("--- Début de la construction de la carte des appellations ---")

    if not os.path.exists(input_file):
        print(f"ERREUR : Le fichier d'entrée n'a pas été trouvé : {input_file}")
        sys.exit(1)

    # defaultdict simplifie l'ajout d'éléments à une liste dans un dictionnaire
    appellation_map = defaultdict(list)
    # Dictionnaire pour suivre les parents de chaque appellation et détecter les ambiguïtés
    appellation_to_parents = defaultdict(list)

    try:
        # Utilisation de l'encodage 'latin-1'
        with open(input_file, 'r', encoding='latin-1') as f:
            parser = ijson.items(f, 'item')
            for appellation in parser:
                libelle = appellation.get('libelle')
                code_parent = appellation.get('code_rome_parent')
                
                if libelle and code_parent:
                    # Ajoute l'appellation à la liste de son parent
                    appellation_map[code_parent].append(libelle)
                    # Enregistre le lien pour la détection d'ambiguïté
                    if code_parent not in appellation_to_parents[libelle]:
                        appellation_to_parents[libelle].append(code_parent)

        # Sauvegarde de la carte principale
        with open(map_output_file, 'w', encoding='utf-8') as f_out:
            json.dump(appellation_map, f_out, indent=2)
        print(f"✅ Succès : Carte des appellations créée avec {len(appellation_map)} fiches mères.")
        print(f"   -> Sauvegardé dans {map_output_file}")

        # Détection et sauvegarde des ambiguïtés
        ambiguities = {libelle: parents for libelle, parents in appellation_to_parents.items() if len(parents) > 1}
        
        if ambiguities:
            print(f"⚠️ {len(ambiguities)} ambiguïtés détectées (appellations avec plusieurs parents).")
            with open(ambiguities_log_file, 'w', encoding='utf-8') as f_log:
                f_log.write("Appellations avec plusieurs codes ROME parents :\n\n")
                for libelle, parents in ambiguities.items():
                    f_log.write(f"- '{libelle}' est lié à : {sorted(parents)}\n")
            print(f"   -> Détails sauvegardés dans {ambiguities_log_file}")
        else:
            print("✅ Aucune ambiguïté détectée.")

    except Exception as e:
        print(f"Une erreur est survenue durant la construction de la carte : {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_appellation_map()