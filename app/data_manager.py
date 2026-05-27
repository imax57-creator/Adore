
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import random
import math

# Ajout du chemin de l'application pour trouver le module utils
project_root_path = Path(__file__).parent.parent
sys.path.append(str(project_root_path))

from app.utils import setup_logger

# Configure un logger spécifique pour ce module
log = setup_logger('data_manager')

class DataError(Exception):
    """Custom exception for data loading errors."""
    pass

class DataManager:
    def __init__(self):
        log.info("Initializing DataManager...")
        # Données brutes du questionnaire
        self.questions_jeune = {}
        self.questions_adulte = {}
        self.studies = []
        self.tags_master = {}
        self.semantic_map = {}
        self.scoring_config = {}
        
        # Données de navigation chargées
        self.navigation_arborescence = []
        self.navigation_secteurs = {}
        self.navigation_centres_interet = []
        self.navigation_thematiques = []
        self.competence_graph = {}
        self.rome_alias_map = {}
        
        # Données métiers et index pré-calculés
        self.jobs = []
        self._jobs_map = {}  # Map: code_rome -> job_object
        self._sector_to_jobs = {}
        self._interest_to_jobs = {}
        self._theme_to_jobs = {}

        # Attributes for scoring and bias calculation
        self.idf = {}
        self.tag_profile_freq = {}
        self.term_to_category = {}
        self.job_popularity_bias = {}
        self.job_education_map = {}
        self._education_level_to_jobs = {}

        try:
            self.load_all_data()
            self._build_navigation_indexes()
            log.info("DataManager initialized successfully.")
        except DataError as e:
            log.error(f"A critical error occurred during DataManager initialization: {e}")
            # Dans une vraie application, on pourrait ici décider de quitter
            # ou de continuer dans un mode dégradé.
            sys.exit(1)

    def _load_json(self, file_path, encoding='utf-8-sig'):
        """Loads a single JSON file with detailed logging."""
        if not file_path.exists():
            log.error(f"Data file missing: {file_path.name}")
            raise DataError(f"Fichier de données manquant : {file_path.name}")
        
        try:
            with file_path.open('r', encoding=encoding) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log.error(f"JSON format error in {file_path.name}: {e}")
            raise DataError(f"Erreur de format dans le fichier {file_path.name}: {e}")
        except Exception as e:
            log.error(f"Unexpected error reading {file_path.name}: {e}")
            raise DataError(f"Erreur inattendue en lisant {file_path.name}: {e}")

    def load_all_data(self):
        """Loads all necessary JSON data files."""
        log.info("Loading all data files...")
        data_path = project_root_path / "data"
        config_path = project_root_path / "config"
        
        self.scoring_config = self._load_json(config_path / 'scoring.json')
        self.questions_jeune = self._load_json(data_path / 'questions_jeune_v2.json')
        self.questions_adulte = self._load_json(data_path / 'questions_adulte.json')
        self.jobs = self._load_json(data_path / 'jobs_rome_enriched.json')
        self.studies = self._load_json(data_path / 'studies.json')
        self.tags_master = self._load_json(data_path / 'tags_master.json')
        self.semantic_map = self._load_json(data_path / 'semantic_map.json')
        
        # --- Load navigation data ---
        self.navigation_arborescence = self._load_json(data_path / 'navigation_arborescence.json')
        self.navigation_secteurs = self._load_json(data_path / 'navigation_secteurs.json')
        self.competence_graph = self._load_json(data_path / 'competence_graph.json')
        self.navigation_centres_interet = self._load_json(data_path / 'navigation_centres_interet.json')
        self.navigation_thematiques = self._load_json(data_path / 'navigation_thematiques.json')
        self.rome_alias_map = self._load_json(data_path / 'rome_alias_map.json')
        self.job_education_map = self._load_json(data_path / 'job_education_map.json')
        
        log.info("All data files loaded.")

        # --- Pre-process and build calculation models ---
        log.info("Starting data pre-processing for scoring...")
        self._build_term_to_category_map()
        self._preprocess_jobs_for_search()
        self._calculate_idf()
        self._calculate_tag_profile_freq()

        # Pre-calculate expected random score for each job for performance
        for job in self.jobs:
            job['_expected_random_score'] = sum(self.tag_profile_freq.get(term, 0.0) * self.idf.get(term, 0.0) for term in set(job.get('_search_terms_list', [])) if term)

        # Charger le cache du biais de popularité s'il existe (rapide, pas de calcul)
        cache_file = project_root_path / 'data' / 'popularity_bias.json'
        if cache_file.exists():
            try:
                self.job_popularity_bias = self._load_json(cache_file)
                for job in self.jobs:
                    job_rome_code = job.get('rome', {}).get('code_rome')
                    job['_popularity_bias'] = self.job_popularity_bias.get(job_rome_code, 0.0)
                log.info(f"-> Popularity bias loaded from cache ({len(self.job_popularity_bias)} entries).")
            except DataError as e:
                log.warning(f"Could not load popularity bias cache: {e}. Bias will be 0 for all jobs.")

        log.info("Data pre-processing finished.")

    def _build_navigation_indexes(self):
        """Builds pre-computed indexes for fast UI queries after data is loaded."""
        log.info("Building navigation indexes...")

        # 1. Create a fast lookup map for jobs by ROME code
        self._jobs_map = {job['rome']['code_rome']: job for job in self.jobs}

        def _get_unique_jobs_from_codes(code_list):
            """Resolves codes to job objects, deduplicates, and returns a stable list.

            Priority: direct lookup (alias fiches have their own entry since ROME v4.60),
            then alias-map fallback for legacy codes absent from _jobs_map.
            """
            if not code_list:
                return []

            seen = set()
            result = []
            for code in sorted(code_list):
                if code in self._jobs_map:
                    canonical = code
                else:
                    canonical = self.rome_alias_map.get(code, code)
                if canonical not in seen and canonical in self._jobs_map:
                    seen.add(canonical)
                    result.append(self._jobs_map[canonical])
            return result

        # 2. Index jobs by activity sector
        self._sector_to_jobs = {
            sector: _get_unique_jobs_from_codes(rome_codes)
            for sector, rome_codes in self.navigation_secteurs.items()
        }
        
        # 3. Index jobs by center of interest
        self._interest_to_jobs = {
            interest['libelle']: _get_unique_jobs_from_codes(interest.get('metiers', []))
            for interest in self.navigation_centres_interet
        }

        # 4. Index jobs by theme
        self._theme_to_jobs = {
            theme['libelle']: _get_unique_jobs_from_codes(theme.get('metiers', []))
            for theme in self.navigation_thematiques
        }

        # 5. Index jobs by education level
        temp_level_map = defaultdict(set)
        for rome_code, levels in self.job_education_map.items():
            # Direct lookup first (alias fiches have their own entry since ROME v4.60),
            # then alias-map fallback for legacy codes absent from _jobs_map.
            if rome_code in self._jobs_map:
                canonical = rome_code
            else:
                canonical = self.rome_alias_map.get(rome_code, rome_code)
            if canonical in self._jobs_map:
                for level in levels:
                    temp_level_map[level].add(canonical)
        self._education_level_to_jobs = temp_level_map

        log.info("Navigation indexes built successfully.")

    # --- PUBLIC API ---

    def get_job_by_code(self, rome_code):
        """Returns a single job object by its ROME code.

        Tries direct lookup first (covers all fiches since ROME v4.60 includes alias fiches),
        then falls back to alias-map resolution for legacy codes.
        """
        if not rome_code:
            return None

        if rome_code in self._jobs_map:
            return self._jobs_map[rome_code]

        master_code = self.rome_alias_map.get(rome_code)
        if master_code and master_code in self._jobs_map:
            log.debug(f"Code '{rome_code}' resolved via alias map to '{master_code}'.")
            return self._jobs_map[master_code]

        log.warning(f"Code ROME '{rome_code}' introuvable dans _jobs_map ni dans rome_alias_map.")
        return None

    def get_all_sectors(self):
        """Returns a sorted list of all activity sectors."""
        return sorted(self._sector_to_jobs.keys())

    def get_jobs_by_sector(self, sector_name):
        """Returns a list of job objects for a given activity sector."""
        return self._sector_to_jobs.get(sector_name, [])

    def get_all_interests(self):
        """Returns a list of all center of interest objects (libelle, definition, metiers)."""
        return sorted([{"libelle": i["libelle"], "definition": i["definition"], "metiers": i.get("metiers", [])} for i in self.navigation_centres_interet], key=lambda x: x['libelle'])

    def get_jobs_by_interest(self, interest_name):
        """Returns a list of job objects for a given center of interest."""
        return self._interest_to_jobs.get(interest_name, [])
        
    def get_all_themes(self):
        """Returns a list of all theme objects (libelle, definition, metiers)."""
        return sorted([{"libelle": t["libelle"], "definition": t["definition"], "metiers": t.get("metiers", [])} for t in self.navigation_thematiques], key=lambda x: x['libelle'])

    def get_jobs_by_theme(self, theme_name):
        """Returns a list of job objects for a given theme."""
        return self._theme_to_jobs.get(theme_name, [])

    def get_main_domains(self):
        """Returns the top-level domains for the hierarchical navigation."""
        return self.navigation_arborescence

    def get_education_levels(self):
        """Returns a sorted list of all available education levels."""
        return sorted(self._education_level_to_jobs.keys())

    def get_job_codes_by_level(self, level):
        """Returns a set of ROME codes for a given education level."""
        if level == "ALL": # Special case to return all jobs
            return set(self._jobs_map.keys())
        return self._education_level_to_jobs.get(level, set())

    def _preprocess_jobs_for_search(self):
        log.debug("Preprocessing jobs for search optimization...")
        for job in self.jobs:
            rome_data = job.get('rome', {})
            competences_data = job.get('competences', {})

            appellation_libelles = [app.get('libelle', '') for app in job.get('appellations', []) if isinstance(app, dict)]
            job['_generic_text'] = " ".join([
                rome_data.get('intitule', ''),
                job.get('definition', '')
            ] + appellation_libelles).lower()

            savoir_faire_enjeux = competences_data.get('savoir_faire', {}).get('enjeux', [])
            core_skills, normal_skills = [], []
            for enjeu in savoir_faire_enjeux:
                for item in enjeu.get('items', []):
                    libelle = item.get('libelle', '')
                    if libelle:
                        if item.get('coeur_metier') == 'Principale':
                            core_skills.append(libelle)
                        else:
                            normal_skills.append(libelle)
            job['_core_skills_text'] = " ".join(core_skills).lower()
            job['_normal_skills_text'] = " ".join(normal_skills).lower()

            savoir_etre_enjeux = competences_data.get('savoir_etre_professionnel', {}).get('enjeux', [])
            savoir_etre_items = savoir_etre_enjeux[0].get('items', []) if savoir_etre_enjeux else []
            job['_savoir_etre_text'] = " ".join([se.get('libelle', '') for se in savoir_etre_items]).lower()

            savoirs_categories = competences_data.get('savoirs', {}).get('categories', [])
            savoirs_text = [item.get('libelle', '') for cat in savoirs_categories for item in cat.get('items', [])]
            job['_savoirs_text'] = " ".join(savoirs_text).lower()

            context_text = [item.get('libelle', '') for cat in job.get('contextes_travail', []) for item in cat.get('items', [])]
            job['_context_text'] = " ".join(context_text).lower()

            job['_search_blob'] = " ".join(filter(None, [job.get(f) for f in ['_generic_text', '_core_skills_text', '_normal_skills_text', '_savoir_etre_text', '_savoirs_text', '_context_text']]))
            job['_search_terms_list'] = job['_search_blob'].split()
            job['_total_terms_count'] = len(set(term for term in job['_search_terms_list'] if term)) or 1


    # --- Scoring and Bias Calculation Methods (Restored) ---

    def _build_term_to_category_map(self):
        """
        Crée une carte qui associe chaque terme de recherche (issu de la carte sémantique)
        à sa catégorie parente (ex: 'qualities', 'skills').
        """
        log.debug("Building term-to-category map...")
        term_map = {}
        for category, tags in self.tags_master.items():
            for tag in tags:
                search_terms = self.semantic_map.get(tag, [tag.lower()])
                for term in search_terms:
                    for sub_term in term.split():
                        if sub_term not in term_map:
                            term_map[sub_term] = category
        self.term_to_category = term_map
        log.debug(f"-> term_to_category map built with {len(self.term_to_category)} terms.")

    def _calculate_idf(self):
        log.debug("Calculating IDF for all terms...")
        N_jobs = len(self.jobs)
        doc_freq = defaultdict(int)

        for job in self.jobs:
            job_terms = set(term for term in job.get('_search_terms_list', []) if term)
            for term in job_terms:
                doc_freq[term] += 1

        self.idf = {term: math.log((N_jobs + 1) / (df + 1)) for term, df in doc_freq.items()}
        log.debug(f"-> IDF calculated for {len(self.idf)} terms.")

    def _calculate_tag_profile_freq(self, num_simulations=1000):
        """
        Simule num_simulations profils aléatoires en reproduisant EXACTEMENT la construction
        de user_profile_terms dans le moteur de scoring (tf_count × weight × IDF),
        de sorte que _expected_random_score soit calibré sur la même échelle que
        raw_tf_idf_score — et non sur une simple présence binaire.
        """
        from collections import Counter
        import random
        log.debug(f"Calculating tag profile frequency with {num_simulations} simulations...")

        tag_category_weights = self.scoring_config.get('tag_category_weights', {})
        all_simulated_weighted = Counter()

        for _ in range(num_simulations):
            # Reproduire le build de quality_scores / interest_scores / skill_scores
            quality_scores = Counter()
            interest_scores = Counter()
            skill_scores = Counter()
            for question in self.questions_jeune.get('questions', []):
                if question.get('options'):
                    selected_option = random.choice(question['options'])
                    for tag in selected_option.get('tags', []):
                        tag_type = tag.get('type', '')
                        tag_value = tag.get('value')
                        if tag_value:
                            if tag_type == 'quality':   quality_scores[tag_value] += 1
                            elif tag_type == 'interest': interest_scores[tag_value] += 1
                            elif tag_type == 'skill':    skill_scores[tag_value] += 1

            # Reproduire le build de user_profile_terms (avec tf_count et weight)
            for keyword, count in (quality_scores + interest_scores + skill_scores).items():
                search_terms = self.semantic_map.get(keyword, [keyword.lower()])
                for term in search_terms:
                    for sub_term in term.split():
                        category = self.term_to_category.get(sub_term, 'default')
                        weight = tag_category_weights.get(category, 1.0)
                        all_simulated_weighted[sub_term] += count * weight

        # tag_profile_freq[t] = contribution pondérée moyenne du terme t par profil aléatoire
        # → ERS = sum(tag_profile_freq[t] × idf[t]) ≈ E[raw_tf_idf_score pour un profil aléatoire]
        self.tag_profile_freq = {
            term: total / num_simulations
            for term, total in all_simulated_weighted.items()
        }
        log.debug(f"-> Tag profile frequency calculated for {len(self.tag_profile_freq)} terms.")

    def _calculate_job_popularity_bias(self, num_simulations=100, top_n_check=10):
        from collections import Counter
        from app.logic.questionnaire_logic import calculate_recommendations, calculate_reconversion_recommendations
        from app.logic.profile_utils import generate_random_profile

        log.info(f"Starting job popularity bias calculation with {num_simulations} simulations (50% jeune, 50% adulte)...")
        job_frequency_counter = Counter()
        half = num_simulations // 2

        for i in range(num_simulations):
            if (i + 1) % 10 == 0:
                log.info(f"Running simulation {i + 1}/{num_simulations}...")

            use_adulte = i >= half
            if use_adulte:
                random_profile = generate_random_profile(self.questions_adulte)
                try:
                    _, top_jobs_list, _, _, _, _, _ = calculate_reconversion_recommendations(
                        random_profile, self.jobs, self.semantic_map, self.idf,
                        self.tag_profile_freq, self.term_to_category, self.scoring_config,
                        job_education_map=self.job_education_map,
                        rome_alias_map=self.rome_alias_map,
                    )
                except Exception as e:
                    log.error(f"'calculate_reconversion_recommendations' failed during bias simulation: {e}")
                    top_jobs_list = []
            else:
                random_profile = generate_random_profile(self.questions_jeune)
                try:
                    _, top_jobs_list, _, _, _, _, _ = calculate_recommendations(
                        random_profile, self.jobs, self.semantic_map, self.idf,
                        self.tag_profile_freq, self.term_to_category, self.scoring_config
                    )
                except Exception as e:
                    log.error(f"'calculate_recommendations' failed during bias simulation: {e}")
                    top_jobs_list = []

            if top_jobs_list:
                for job_result in top_jobs_list[:top_n_check]:
                    job_rome_code = job_result.get('rome', {}).get('code_rome')
                    if job_rome_code:
                        job_frequency_counter[job_rome_code] += 1

        self.job_popularity_bias = {}
        for rome_code, count in job_frequency_counter.items():
            self.job_popularity_bias[rome_code] = count / num_simulations

        for job in self.jobs:
            job_rome_code = job.get('rome', {}).get('code_rome')
            job['_popularity_bias'] = self.job_popularity_bias.get(job_rome_code, 0.0)
        log.info(f"-> Job popularity bias calculation finished. {len(self.job_popularity_bias)} biases calculated.")

    def load_or_calculate_bias(self, num_simulations=20, top_n_check=3, force_recalc=False):
        data_path = project_root_path / "data"
        cache_file = data_path / 'popularity_bias.json'

        if not force_recalc and cache_file.exists():
            log.info("Loading job popularity bias from cache...")
            try:
                self.job_popularity_bias = self._load_json(cache_file)
                for job in self.jobs:
                    job_rome_code = job.get('rome', {}).get('code_rome')
                    job['_popularity_bias'] = self.job_popularity_bias.get(job_rome_code, 0.0)
                log.info("-> Popularity bias successfully loaded and applied from cache.")
                return
            except DataError as e:
                log.warning(f"Could not read bias cache file: {e}. Recalculating...")

        self._calculate_job_popularity_bias(num_simulations=num_simulations, top_n_check=top_n_check)

        try:
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(self.job_popularity_bias, f, indent=4)
            log.info(f"-> Popularity bias saved to cache file: {cache_file}")
        except IOError as e:
            log.error(f"Could not save popularity bias cache file: {e}")

