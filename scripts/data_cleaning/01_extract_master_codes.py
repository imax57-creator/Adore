
import ijson
import json
import os
import sys

def extract_master_codes():
    """
    Lit le référentiel des codes ROME, identifie les fiches métiers principales (maîtres)
    et sauvegarde leurs codes dans un fichier JSON.
    """
    # Définir les chemins relatifs au script
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    
    input_file = os.path.join(project_root, 'RefRomeJson', 'unix_referentiel_code_rome_v460.json')
    output_file = os.path.join(script_dir, 'master_codes.json')

    print("--- Début de l'extraction des codes ROME maîtres ---")
    
    if not os.path.exists(input_file):
        print(f"ERREUR : Le fichier d'entrée n'a pas été trouvé : {input_file}")
        sys.exit(1)

    all_codes = set()

    try:
        # Utilisation de l'encodage 'latin-1' pour gérer les caractères spéciaux
        with open(input_file, 'r', encoding='latin-1') as f:
            # Utilise ijson pour parser le fichier en streaming
            parser = ijson.items(f, 'item')
            for entry in parser:
                # Conserver TOUS les codes ROME valides (maîtres + alias),
                # car chaque code possède sa propre fiche emploi distincte dans ROME v4.60.
                if entry.get('code_rome'):
                    all_codes.add(entry['code_rome'])

        # Convertir le set en liste pour la sérialisation JSON
        all_codes_list = sorted(list(all_codes))

        with open(output_file, 'w', encoding='utf-8') as f_out:
            json.dump(all_codes_list, f_out, indent=2)

        print(f"✅ Succès : {len(all_codes_list)} codes extraits (maîtres + alias).")
        print(f"   -> Sauvegardés dans {output_file}")

    except Exception as e:
        print(f"Une erreur est survenue durant l'extraction : {e}")
        sys.exit(1)

if __name__ == "__main__":
    extract_master_codes()
