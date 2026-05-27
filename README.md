# Adoré — Assistant d'Orientation

**Adoré** est une application de bureau Python qui guide les utilisateurs dans leur réflexion d'orientation professionnelle. Elle propose deux parcours distincts :

- **Jeune (12–18 ans)** : exploration des intérêts et découverte de métiers.
- **Adulte (reconversion)** : recommandations tenant compte des compétences transférables du secteur d'expérience.

L'application génère à la fin un rapport HTML personnalisé avec les métiers suggérés, les réponses au questionnaire et des insights sur le profil de l'utilisateur.

---

## Installation

### Prérequis

- Python 3.10 ou supérieur
- (Recommandé) PyCharm ou VS Code

### Mise en place de l'environnement

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement (Windows)
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### Lancement

```bash
python main.py
```

---

## Utilisation

Le parcours complet se déroule en 5 écrans :

1. **Accueil (`WelcomeView`)** — choix entre le mode *jeune* et le mode *adulte*.
2. **Prénom (`NameView`)** — saisie du prénom de l'utilisateur.
3. **Questionnaire (`QuizView`)** — questions sur les intérêts, matières préférées et compétences. Le parcours adulte inclut une question sur le secteur d'expérience passée.
4. **Résultats (`ResultsView`)** — liste des métiers recommandés avec scores et détails. Bouton *Générer mon rapport* pour produire le fichier HTML.
5. **Explorateur (`ExplorerView`)** *(optionnel)* — navigation libre dans toute la base de métiers, avec recherche textuelle et filtre par niveau d'études.

Les rapports HTML sont sauvegardés dans le dossier `orientation/`.

---

## Tests

```bash
# Suite complète (8 modules) — rapport sauvegardé dans tests/
python run_all_tests.py

# Module individuel
python tests/test_data_integrity.py
python tests/test_algorithm_stability.py
```

Chaque module expose `run_all_checks() -> (bool, list[str])`. Les rapports sont nommés `tests_report_TIMESTAMP.md`.

---

## Structure du projet

```
Adoré/
├── main.py                     # Point d'entrée
├── run_all_tests.py            # Lance tous les tests
├── requirements.txt
│
├── app/
│   ├── main_app.py             # Contrôleur principal (ctk.CTk)
│   ├── data_manager.py         # Chargement et pré-traitement des données
│   ├── text_provider.py        # Textes UI selon le mode (jeune/adulte)
│   ├── ui_theme.py             # Couleurs, polices et constantes UI
│   ├── utils.py                # Logger partagé
│   ├── logic/
│   │   ├── questionnaire_logic.py   # Algorithme de scoring TF-IDF
│   │   ├── report_generator.py      # Génération HTML (Jinja2) et PDF (reportlab)
│   │   └── profile_utils.py
│   ├── views/
│   │   ├── welcome_view.py
│   │   ├── name_view.py
│   │   ├── quiz_view.py
│   │   ├── results_view.py
│   │   ├── explorer_view.py
│   │   └── components/
│   │       └── accordion.py
│   └── templates/              # Templates Jinja2 pour le rapport HTML
│
├── data/
│   ├── jobs_rome_enriched.json         # Base de métiers (ROME v4.60, enrichie — 1584 fiches)
│   ├── questions_jeune_v2.json         # Questions du parcours jeune
│   ├── questions_adulte.json           # Questions du parcours adulte
│   ├── tags_master.json                # Taxonomie des tags
│   ├── semantic_map.json               # Expansion sémantique des termes
│   ├── rome_alias_map.json             # Alias des codes ROME (code → code parent)
│   ├── job_education_map.json          # Niveaux de formation requis par code ROME
│   ├── navigation_secteurs.json        # Index de navigation par secteur
│   ├── navigation_centres_interet.json # Index par centre d'intérêt
│   ├── navigation_thematiques.json     # Index par thématique
│   ├── navigation_arborescence.json    # Arborescence hiérarchique
│   ├── texts.json                      # Textes UI (jeune/adulte)
│   └── popularity_bias.json            # Cache auto-généré (supprimer pour recalculer)
│
├── config/
│   └── scoring.json            # Poids de l'algorithme (tag_category_weights, etc.)
│
├── assets/
│   └── theme_arcade_gold.json  # Thème visuel CustomTkinter
│
├── tests/                      # Modules de test + rapports générés
├── orientation/                # Rapports HTML générés pour les utilisateurs
├── profiles/                   # Sessions utilisateurs (JSON)
├── scripts/data_cleaning/      # Pipeline de construction des données enrichies
└── RefRomeJson/                # Source brute ROME v4.60
```

---

## Architecture technique

### Contrôleur

`MainApp` (`app/main_app.py`) est la fenêtre principale (`ctk.CTk`). Les 5 vues sont instanciées au démarrage dans un dict `frames` et empilées via `show_frame(page_name)`. Les vues accèdent au contrôleur via `self.controller`.

### Données partagées

`MainApp.user_profile` (dict) accumule l'état de la session :
- `QuizView` écrit les réponses dans `controller.user_profile["answers"]`
- `ResultsView` appelle `calculate_recommendations()` et écrit les résultats
- `report_generator.generate_html_report()` lit le profil complet pour rendre le template

### Algorithme de scoring

`app/logic/questionnaire_logic.py` expose deux fonctions :
- `calculate_recommendations()` — parcours jeune
- `calculate_reconversion_recommendations()` — parcours adulte (bonus de transférabilité basé sur le secteur d'expérience)

Les deux utilisent TF-IDF pondéré, soustraction du bruit de fond et pénalité de popularité. Les poids viennent de `config/scoring.json`.

### Threading

Le calcul du biais de popularité (démarrage) et le scoring des recommandations (`ResultsView`) tournent dans des threads séparés. **Toutes les mises à jour UI depuis ces threads passent par `self.after(0, callback)`.**

---

## Dépendances

| Librairie | Usage |
|---|---|
| `customtkinter` | Interface graphique |
| `Jinja2` | Rendu du rapport HTML |
| `reportlab` | Génération du rapport PDF |
