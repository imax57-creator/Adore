# README Assistant — Journal de bord du projet Adoré

Ce document sert de pense-bête pour les développements en cours. Il est destiné aux sessions de travail avec un assistant IA.

---

## État Actuel du Projet (27/05/2026)

**Version : V5 — L'Écosystème de Guidance Intelligente**

L'application est stable et fonctionnelle. Les deux parcours (jeune et adulte) sont opérationnels. La suite de tests passe à **8/8** (intégrité des données, cohérence, stabilité, redondance, biais, performance, couverture, mode adulte). Le temps moyen de calcul des recommandations est de ~0.64s (calibré pour un catalogue de 1584 métiers).

### Ce qui est en place

- Deux algorithmes de recommandation : `calculate_recommendations()` (jeune) et `calculate_reconversion_recommendations()` (adulte) dans `app/logic/questionnaire_logic.py`.
- Génération de rapport HTML (Jinja2) et PDF (reportlab) via `app/logic/report_generator.py`.
- Interface `ExplorerView` avec barre de recherche et filtre par niveau d'études.
- Architecture de thème centralisée dans `app/ui_theme.py` et textes UI dans `data/texts.json`.
- Biais de popularité calculé en arrière-plan au démarrage et mis en cache dans `data/popularity_bias.json`.
- Suite de **8 modules de tests** dans `tests/`.
- **Catalogue complet ROME v4.60** : 1584 fiches (532 codes maîtres + 1052 codes alias, chacun avec sa propre fiche métier complète).
- Pipeline de reconstruction du catalogue dans `scripts/data_cleaning/` : `run_cleaning_pipeline.py` orchestre les 4 étapes + enrichissement en un seul appel.

---

## Roadmap V5 — Tâches en cours

### Axe 1 : Fondations Techniques
- [x] ~~Corriger le biais de popularité dans `DataManager`~~ — résolu par l'extension du catalogue à 1584 métiers
- [x] ~~Tests unitaires pour le mode adulte~~ — `test_adulte_suggestions.py` (4 vérifs : cohérence, biais, filtre formation, différenciation)
- [ ] **1.2** Refactoriser `questionnaire_logic.py` avec un pattern Strategy (`YouthStrategy`, `AdultStrategy`).

### Axe 2 : Modules d'Intelligence Métier
- [ ] **2.1** Score de "bonus de transférabilité" amélioré, basé sur les compétences partagées (au-delà du seul secteur d'activité).
- [ ] **2.2** Créer `app/logic/semantic_explainer.py` (justifications contextuelles affichées dans les résultats).
- [ ] **2.3** Créer `app/logic/constraint_engine.py` (filtrage dynamique par études, secteur, compétences).

### Axe 3 : UX d'Exploration Guidée
- [ ] **3.1** Refondre la vue résultats autour d'un "métier pivot" avec métiers voisins.
- [ ] **3.2** Intégrer les contrôles UI pour le `ConstraintEngine` (filtres en temps réel).
- [ ] **3.3** Ajouter des visuels de justification (tags en commun, scores).

### Axe 4 : Métriques Produit
- [ ] **4.1** Définir et implémenter les KPIs (utilisation des filtres, profondeur d'exploration).

---

## Points d'attention techniques

- **ROME codes et lookup direct-first** : depuis l'extension à 1584 fiches, les codes alias (ex. A1102) ont leur propre entrée dans `_jobs_map`. Toujours essayer le code directement dans `_jobs_map` avant de passer par `rome_alias_map`. `DataManager.get_job_by_code()` implémente ce pattern — ne jamais accéder à `_jobs_map` directement avec un code brut.
- **Filtre de formation** : `master_to_levels` (dans `calculate_reconversion_recommendations`) est indexé sous le code direct **et** sous le code alias cible, pour éviter que des métiers alias échappent au filtre.
- **Threading** : tout update UI depuis un thread background passe obligatoirement par `self.after(0, callback)`.
- **Popularité bias** : `data/popularity_bias.json` est un cache auto-généré. Supprimer pour forcer le recalcul (obligatoire après tout changement de catalogue).
- **Poids de scoring** : dans `config/scoring.json`, jamais hardcodés dans le code.
- **Fichier intermédiaire** : `data/jobs_rome.json` est gitignore — il est produit par le pipeline (`run_cleaning_pipeline.py`) et consommé par `enrich_jobs_data.py` pour produire `jobs_rome_enriched.json`.
