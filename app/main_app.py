import customtkinter as ctk
import threading
from tkinter import messagebox

from app.utils import log
from .views.welcome_view import WelcomeView
from .views.quiz_view import QuizView
from .views.results_view import ResultsView
from .views.name_view import NameView
from .views.explorer_view import ExplorerView
from .data_manager import DataManager, DataError
from .text_provider import TextProvider
from pathlib import Path

class MainApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ctk.set_appearance_mode("dark")

        self.title("Orientation Assistant")
        self.center_window(800, 600)
        self.minsize(800, 600)
        self.resizable(True, True)

        # --- Data Loading ---
        try:
            self.data_manager = DataManager()
        except DataError as e:
            messagebox.showerror("Erreur de données", f"Impossible de charger les fichiers de l'application.\n\n{e}")
            self.destroy()
            return

        # --- Text Loading ---
        texts_path = Path(__file__).parent.parent / "data" / "texts.json"
        self.text_provider = TextProvider(texts_path)

        # Pass data to attributes
        self.jobs_data = self.data_manager.jobs
        self.studies_data = self.data_manager.studies
        self.active_questions = None # Pour garder en mémoire le questionnaire utilisé
        self.quiz_to_start = None # Pour stocker le type de quiz à lancer

        # --- User Profile ---
        self.user_profile = {
            "name": "",
            "answers": {},
            "recommended_domains": [],
            "recommended_jobs": []
        }

        # --- Container for views ---
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # Pass the controller and data_manager to each view
        for F in (WelcomeView, NameView, QuizView, ResultsView, ExplorerView):
            page_name = F.__name__
            frame = F(parent=container, controller=self, data_manager=self.data_manager)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("WelcomeView")

        # --- Lancer le calcul du biais en arrière-plan ---
        log.info("Lancement du calcul de biais en arrière-plan...")
        bias_thread = threading.Thread(target=self.data_manager.load_or_calculate_bias, daemon=True)
        bias_thread.start()

    def center_window(self, width=800, height=600):
        # get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # calculate position x and y coordinates
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def prompt_for_name(self, quiz_type):
        """Stores the quiz type and shows the name entry screen."""
        self.quiz_to_start = quiz_type
        self.show_frame("NameView")

    def start_quiz(self, quiz_type):
        """ Starts the quiz with the appropriate set of questions. """
        if quiz_type == 'jeune':
            questions = self.data_manager.questions_jeune
        elif quiz_type == 'adulte':
            questions = self.data_manager.questions_adulte
        else:
            # Fallback or error
            messagebox.showerror("Erreur", "Type de questionnaire non reconnu.")
            return

        self.active_questions = questions # Stocker le questionnaire actif

        self.user_profile["answers"] = {} # Reset answers
        quiz_frame = self.frames["QuizView"]
        quiz_frame.set_questions(questions) # Pass questions to the quiz view
        quiz_frame.start_quiz() # Reset and start the quiz UI
        self.show_frame("QuizView")

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        # Call update_results if we are showing the ResultsView
        if page_name == "ResultsView":
            frame.update_results()
        elif page_name == "NameView":
            frame.update_texts()
        frame.tkraise()

    def show_explorer(self):
        """Shows the explorer view."""
        self.show_frame("ExplorerView")
