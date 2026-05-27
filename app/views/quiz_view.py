import customtkinter as ctk
import random
from collections import defaultdict

class QuizView(ctk.CTkFrame):
    def __init__(self, parent, controller, data_manager):
        super().__init__(parent)
        self.controller = controller
        self.data_manager = data_manager

        # --- State ---
        self.questions = []
        self.current_question_index = 0
        self.answers = {}

        # --- Widgets ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.progress_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=16))
        self.progress_label.grid(row=0, column=0, padx=30, pady=(20, 10), sticky="ew")

        self.question_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=22, weight="bold"), wraplength=700)
        self.question_label.grid(row=1, column=0, padx=30, pady=30, sticky="ew")

        self.options_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=0)
        self.options_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.options_frame.grid_columnconfigure(0, weight=1)

        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.grid(row=3, column=0, padx=30, pady=(10, 20), sticky="ew")
        self.nav_frame.grid_columnconfigure(1, weight=1)

        self.back_button = ctk.CTkButton(self.nav_frame, text="Retour", command=self.prev_question)
        self.back_button.grid(row=0, column=0, sticky="w")

        self.skip_button = ctk.CTkButton(self.nav_frame, text="Passer", command=self.skip_question, fg_color="transparent", border_color="#ffd700", text_color=("#e8e8e8", "#e8e8e8"))
        self.skip_button.grid(row=0, column=2, sticky="e")

    def set_questions(self, questions_data):
        """Receives the question data from the controller."""
        if "recipe" in questions_data and "dimensions" in questions_data:
            self.quiz_recipe = questions_data["recipe"]
            self.quiz_dimensions = questions_data["dimensions"]
            self.questions = [] # Les questions seront construites par _build_quiz_from_recipe
        else:
            self.questions = questions_data.get("questions", [])
            self.quiz_recipe = None
            self.quiz_dimensions = None

    def _build_quiz_from_recipe(self, recipe, dimensions, excluded_ids=None):
        if excluded_ids is None:
            excluded_ids = set()

        quiz_questions = []
        for category, count in recipe.items():
            pool = dimensions.get(category, [])
            
            # Filtrer les questions déjà exclues
            filtered_pool = [q for q in pool if q['id'] not in excluded_ids]

            # Gérer la question dynamique du secteur d'expérience
            if category == "experience" and any(q.get('type') == 'dynamic_sector_choice' for q in filtered_pool):
                dynamic_question = next((q for q in filtered_pool if q.get('type') == 'dynamic_sector_choice'), None)
                if dynamic_question:
                    # Générer les options dynamiquement
                    sectors = self.data_manager.get_all_sectors()
                    dynamic_options = []
                    for sector in sectors:
                        dynamic_options.append({
                            "text": sector,
                            "tags": [{"type": "experience_sector", "value": sector}]
                        })
                    dynamic_question_copy = dynamic_question.copy()
                    dynamic_question_copy["options"] = dynamic_options
                    quiz_questions.append(dynamic_question_copy)
                    # S'assurer que cette question compte pour le 'count'
                    count -= 1 
                    # Retirer la question dynamique du pool pour éviter de la sampler à nouveau
                    filtered_pool = [q for q in filtered_pool if q['id'] != dynamic_question['id']]

            num_to_sample = min(count, len(filtered_pool))
            if num_to_sample > 0:
                quiz_questions.extend(random.sample(filtered_pool, num_to_sample))
        
        random.shuffle(quiz_questions)
        return quiz_questions

    def start_quiz(self):
        """Starts the main quiz using the pre-loaded questions."""
        if self.quiz_recipe and self.quiz_dimensions:
            # Pour le quiz adulte avec la nouvelle structure
            self.questions = self._build_quiz_from_recipe(self.quiz_recipe, self.quiz_dimensions)
        else:
            # Pour le quiz jeune ou l'ancienne structure
            all_questions = self.questions
            # Combined recipe for a single, more comprehensive quiz (ancienne logique)
            full_recipe = {
                "interest": 3,
                "work_style": 5,
                "values": 2,
                "projection": 1,
                "problem_solving": 1
            }
            # Adapter l'appel pour le quiz jeune
            # Créer une structure 'dimensions' compatible pour l'ancienne logique
            dimensions_for_jeune = defaultdict(list)
            for q in all_questions:
                dimensions_for_jeune[q.get('category', 'default')].append(q)
            
            self.questions = self._build_quiz_from_recipe(full_recipe, dimensions_for_jeune)

        self.current_question_index = 0
        self.answers = {}
        self.controller.user_profile["answers"] = {}
        self.display_current_question()



    def display_current_question(self):
        # Clear previous options
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        # Check if quiz is finished
        if self.current_question_index >= len(self.questions):
            self.finish_quiz()
            return

        # Update progress
        self.progress_label.configure(text=f"Question {self.current_question_index + 1} / {len(self.questions)}")

        # Update question text
        question_data = self.questions[self.current_question_index]
        self.question_label.configure(text=question_data["question"])

        # Create new option buttons
        for i, option in enumerate(question_data["options"]):
            option_button = ctk.CTkButton(self.options_frame,
                                          text=option["text"],
                                          font=ctk.CTkFont(size=14),
                                          fg_color="#2d004f",
                                          hover_color="#410073",
                                          text_color=("#E8E8E8", "#E8E8E8"),
                                          anchor="w",
                                          command=lambda o=option: self.answer_question(o))
            if option_button._text_label:
                option_button._text_label.configure(wraplength=680)
            option_button.grid(row=i, column=0, padx=50, pady=8, sticky="ew")

        # Update back button state
        self.back_button.configure(state="normal" if self.current_question_index > 0 else "disabled")

    def answer_question(self, selected_option):
        question_id = self.questions[self.current_question_index]["id"]
        self.answers[question_id] = selected_option
        self.next_question()

    def next_question(self):
        self.current_question_index += 1
        self.display_current_question()

    def prev_question(self):
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.display_current_question()

    def skip_question(self):
        question_id = self.questions[self.current_question_index]["id"]
        self.answers[question_id] = "skipped"
        self.next_question()

    def finish_quiz(self):
        self.controller.user_profile["answers"] = self.answers
        results_frame = self.controller.frames["ResultsView"]
        
        # The quiz is now a single session, so we always show the final results.
        results_frame.update_results()
        
        self.controller.show_frame("ResultsView")
