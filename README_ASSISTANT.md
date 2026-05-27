# README Assistant — Journal de bord du projet Adoré

Ce document sert de pense-bête pour les développements en cours. Il est destiné aux sessions de travail avec un assistant IA.

---

## État Actuel du Projet (26/05/2026)

**Version : V5 — L'Écosystème de Guidance Intelligente**

L'application est stable et fonctionnelle. Les deux parcours (jeune et adulte) sont opérationnels. La suite de tests passe à **7/7** (intégrité des données, cohérence, stabilité, redondance, biais, performance, couverture). Le temps moyen de calcul des recommandations est de ~0.22s.

### Ce qui est en place

- Deux algorithmes de recommandation : `calculate_recommendations()` (jeune) et `calculate_reconversion_recommendations()` (adulte) dans `app/logic/questionnaire_logic.py`.
- Génération de rapport HTML (Jinja2) et PDF (reportlab) via `app/logic/report_generator.py`.
- Interface `ExplorerView` avec barre de recherche et filtre par niveau d'études.
- Architecture de thème centralisée dans `app/ui_theme.py` et textes UI dans `data/texts.json`.
- Biais de popularité calculé en arrière-plan au démarrage et mis en cache dans `data/popularity_bias.json`.
- Suite de 7 modules de tests dans `tests/`.

---

## Roadmap V5 — Tâches en cours

### Axe 1 : Fondations Techniques
- [ ] **1.1** Corriger le biais de popularité dans `DataManager` pour le parcours adulte.
- [ ] **1.1** Tests unitaires `test_recommendation_logic.py` pour valider la correction.
- [ ] **1.2** Refactoriser `questionnaire_logic.py` avec un pattern Strategy (`YouthStrategy`, `AdultStrategy`).

### Axe 2 : Modules d'Intelligence Métier
- [ ] **2.1** Intégrer un `SemanticNavigator` dans l'`AdultStrategy` pour les métiers-passerelles.
- [ ] **2.1** Score de "bonus de transférabilité" basé sur `competence_graph.json`.
- [ ] **2.2** Créer `app/logic/semantic_navigator.py` (modélise `semantic_map.json`).
- [ ] **2.2** Créer `app/logic/semantic_explainer.py` (justifications contextuelles).
- [ ] **2.3** Créer `app/logic/constraint_engine.py` (filtrage dynamique par études, secteur, compétences).

### Axe 3 : UX d'Exploration Guidée
- [ ] **3.1** Refondre la vue résultats autour d'un "métier pivot" avec métiers voisins.
- [ ] **3.2** Intégrer les contrôles UI pour le `ConstraintEngine` (filtres en temps réel).
- [ ] **3.3** Ajouter des visuels de justification (tags en commun, scores).

### Axe 4 : Métriques Produit
- [ ] **4.1** Définir et implémenter les KPIs (utilisation des filtres, profondeur d'exploration).

---

## Points d'attention techniques

- **ROME codes** : toujours résoudre via `DataManager.get_job_by_code()` qui applique `rome_alias_map`. Ne jamais accéder à `_jobs_map` directement.
- **Threading** : tout update UI depuis un thread background passe obligatoirement par `self.after(0, callback)`.
- **Popularité bias** : `data/popularity_bias.json` est un cache auto-généré. Supprimer pour forcer le recalcul.
- **Poids de scoring** : dans `config/scoring.json`, jamais hardcodés dans le code.
