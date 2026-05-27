
import customtkinter as ctk
from customtkinter import CTkFont
from ..logic.questionnaire_logic import calculate_recommendations, calculate_reconversion_recommendations
from ..logic.report_generator import generate_html_report, generate_pdf_report
from tkinter import messagebox
from .components.accordion import Accordion
import threading
from .. import ui_theme
from ..utils import format_definition_as_bullets as _format_definition_as_bullets

class ResultsView(ctk.CTkFrame):
    def __init__(self, parent, controller, data_manager):
        super().__init__(parent)
        self.controller = controller
        self.data_manager = data_manager
        self.job_buttons = []
        self.default_button_color = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Panel (Jobs List) ---
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="nsew")
        self.left_panel.grid_rowconfigure(3, weight=1)

        results_title = ctk.CTkLabel(self.left_panel, text="Métiers suggérés", font=CTkFont(**ui_theme.FONT_DEFINITIONS["title_small"]))
        results_title.grid(row=0, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"])

        self.domains_label = ctk.CTkLabel(self.left_panel, text="Domaines :", wraplength=200, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_medium_normal"]))
        self.domains_label.grid(row=1, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["small"])

        self.intro_label = ctk.CTkLabel(self.left_panel, text="", wraplength=200, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_small_italic"]))
        self.intro_label.grid(row=2, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["small"])

        self.job_list_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="Clique sur un métier pour voir les détails")
        self.job_list_frame.grid(row=3, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="nsew")

        # --- Right Panel (Job Details) ---
        self.right_panel = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.job_title = ctk.CTkLabel(self.right_panel, text="Sélectionne un métier", font=CTkFont(**ui_theme.FONT_DEFINITIONS["title_medium"]), anchor="w", wraplength=350, height=70)
        self.job_title.grid(row=0, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="ew")

        self.details_accordion = Accordion(self.right_panel)
        self.details_accordion.grid(row=1, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="nsew")

        self.loading_label = ctk.CTkLabel(self.right_panel, text="", font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_large"]))
        self.loading_label.grid(row=1, column=0, padx=ui_theme.PADDINGS["medium"], pady=ui_theme.PADDINGS["medium"], sticky="nsew")
        self.loading_label.grid_remove() # Hide by default

        # Bind resize event to update wraplength
        self.right_panel.bind("<Configure>", self._update_wraplength)

        # --- Navigation and Actions ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, columnspan=2, padx=ui_theme.PADDINGS["medium"], pady=(ui_theme.PADDINGS["medium"], ui_theme.PADDINGS["large"]), sticky="ew")

        restart_button = ctk.CTkButton(self.bottom_frame, text="Recommencer", command=self.restart_quiz, height=35, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_small"]))
        restart_button.pack(side="left", padx=ui_theme.PADDINGS["medium"])

        explorer_button = ctk.CTkButton(self.bottom_frame, text="Explorer les métiers", command=self.show_explorer, height=35, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_small"]))
        explorer_button.pack(side="left", padx=ui_theme.PADDINGS["medium"]) # Pack next to restart button

        self.export_pdf_button = ctk.CTkButton(self.bottom_frame, text="Exporter en PDF", command=self.export_pdf_report, height=35, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_small"]))
        self.export_pdf_button.pack(side="right", padx=(0, ui_theme.PADDINGS["small"]))

        self.export_button = ctk.CTkButton(self.bottom_frame, text="Générer votre rapport", command=self.export_report, height=35, font=CTkFont(**ui_theme.FONT_DEFINITIONS["body_small"]))
        self.export_button.pack(side="right", padx=ui_theme.PADDINGS["medium"])

    def update_results(self):
        # Clear previous results
        for widget in self.job_list_frame.winfo_children():
            widget.destroy()
        self.intro_label.configure(text="") # Clear intro label

        # Show loading indicator and hide accordion
        self.loading_label.grid()
        self._start_spinner() # Start the spinner
        self.details_accordion.grid_remove()
        self.job_title.configure(text="Calcul en cours...")
        
        # Disable buttons during calculation
        self.export_button.configure(state="disabled")
        self.export_pdf_button.configure(state="disabled")

        # Start calculation in a separate thread
        calculation_thread = threading.Thread(target=self._calculate_recommendations_thread, daemon=True)
        calculation_thread.start()

    def _calculate_recommendations_thread(self):
        # Perform the heavy calculation
        quiz_type = self.controller.quiz_to_start
        scoring_config = self.data_manager.scoring_config

        if quiz_type == 'adulte':
            # Utiliser le nouvel algorithme pour le parcours adulte
            domains, jobs, strengths, subjects, weak_match, interests, skills = calculate_reconversion_recommendations(
                self.controller.user_profile,
                self.controller.jobs_data,
                self.data_manager.semantic_map,
                self.data_manager.idf,
                self.data_manager.tag_profile_freq,
                self.data_manager.term_to_category,
                scoring_config,
                job_education_map=self.data_manager.job_education_map,
                rome_alias_map=self.data_manager.rome_alias_map,
            )
        else:
            # Utiliser l'algorithme standard pour le parcours jeune
            domains, jobs, strengths, subjects, weak_match, interests, skills = calculate_recommendations(
                self.controller.user_profile,
                self.controller.jobs_data,
                self.data_manager.semantic_map,
                self.data_manager.idf,
                self.data_manager.tag_profile_freq,
                self.data_manager.term_to_category,
                scoring_config
            )
        
        # Use after to update GUI from the main thread
        self.after(0, lambda: self._post_recommendations_calculation(domains, jobs, strengths, subjects, weak_match, interests, skills))

    def _post_recommendations_calculation(self, domains, jobs, strengths, subjects, weak_match, interests, skills):
        # Hide loading indicator and show accordion
        self._stop_spinner() # Stop the spinner
        self.loading_label.grid_remove()
        self.details_accordion.grid()
        self.job_title.configure(text="Sélectionne un métier") # Reset title

        # Set intro message
        quiz_mode = self.controller.quiz_to_start
        self.intro_label.configure(text=self.controller.text_provider.get_text("results_view_intro", quiz_mode))

        # Re-enable buttons
        self.export_button.configure(state="normal")
        self.export_pdf_button.configure(state="normal")

        self.controller.user_profile["recommended_domains"] = domains
        if interests:
            self.domains_label.configure(text=interests)
        elif domains:
            self.domains_label.configure(text="Domaines : " + ", ".join(str(d) for d in domains[:3]))
        else:
            self.domains_label.configure(text="")
        self.controller.user_profile["recommended_jobs"] = jobs
        self.controller.user_profile["user_strengths"] = strengths
        self.controller.user_profile["recommended_subjects"] = subjects
        self.controller.user_profile["weak_match"] = weak_match
        self.controller.user_profile["user_interests"] = interests
        self.controller.user_profile["user_skills"] = skills

        # Transformer les données brutes en données prêtes pour l'affichage
        display_jobs = self._transform_job_data(jobs)

        # Display jobs
        self.job_buttons = [] # Clear the list before repopulating
        self.default_button_color = None # Reset default color
        for job in display_jobs:
            button_label = job.get('name', 'Titre manquant')
            if job.get('emergente_ratio', 0) >= 0.12:
                button_label = button_label + " (Avenir)"
            job_button = ctk.CTkButton(self.job_list_frame, text=button_label, anchor="w")
            if job_button._text_label:
                job_button._text_label.configure(wraplength=120)
            job_button.configure(command=lambda j=job, b=job_button: self.show_job_details(j, b))
            job_button.pack(fill="x", padx=8, pady=2)
            # Propagate scroll events to the job list scrollable frame
            self._bind_scroll_to_listframe(job_button)
            self.job_buttons.append(job_button)
            if self.default_button_color is None:
                self.default_button_color = job_button.cget("fg_color")

        # Bind resize event to update wraplength of job buttons
        self.job_list_frame.bind("<Configure>", self._update_job_buttons_wraplength)

        # Mettre à jour le profil utilisateur avec les données transformées pour le rapport
        self.controller.user_profile["recommended_jobs"] = display_jobs

        # Clear details panel (already done by self.details_accordion.clear() in show_job_details)
        self.details_accordion.clear()

    def show_job_details(self, job, clicked_button):
        # Highlight the selected button
        for button in self.job_buttons:
            button.configure(fg_color=self.default_button_color) # Reset to default color

        # Use a distinct color for highlighting, e.g., from the theme
        highlight_color = "#ff9900" # A color from the theme for hover/selection
        clicked_button.configure(fg_color=highlight_color)

        self.job_title.configure(text=job.get('name', 'Titre manquant'))
        self.details_accordion.clear() # Clear previous sections
        self._populate_job_details(job)
        self.after(10, self._refresh_detail_wraplengths)

    def _populate_job_details(self, job):
        # Description du métier
        description_text = job.get('description', 'Description non disponible.')
        self.details_accordion.add_section("Description du métier", description_text, is_open=True)

        # Raisons du match (pour le parcours adulte)
        match_reasons = job.get('_match_reasons')
        if match_reasons:
            reasons_text = "\n- ".join(match_reasons)
            self.details_accordion.add_section("Pourquoi ce métier vous correspond", "- " + reasons_text)

        # Accès au métier
        acces_text = job.get('studies_access', 'Information non spécifiée')
        self.details_accordion.add_section("Accès au métier", acces_text)

        # Compétences (Savoir-faire)
        skills_to_show = job.get('skills', [])
        skills_text = "Non spécifiées"
        if skills_to_show:
            skills_text = "- " + "\n- ".join([s.get('libelle', '') for s in skills_to_show])
        self.details_accordion.add_section("Compétences (Savoir-faire)", skills_text)

        # Qualités Professionnelles (Savoir-être)
        qualities_to_show = job.get('qualities', [])
        qualities_text = "Non spécifiées"
        if qualities_to_show:
            qualities_text = "- " + "\n- ".join([q.get('libelle', '') for q in qualities_to_show])
        self.details_accordion.add_section("Qualités Professionnelles", qualities_text)

        # Pistes d'évolution (Mobilités)
        mobilites_obj = job.get('mobilites', {})
        mobilites_proches = mobilites_obj.get('proches', [])
        mobilites_possibles = mobilites_obj.get('possibles', [])
        mobilites_text = ""
        if mobilites_proches:
            mobilites_text += "Accès rapide :\n- "
            mobilites_text += "\n- ".join([m.get('rome_cible', '') for m in mobilites_proches])
        if mobilites_possibles:
            if mobilites_text: mobilites_text += "\n\n"
            mobilites_text += "Avec formation :\n- "
            mobilites_text += "\n- ".join([p.get('rome_cible', '') for p in mobilites_possibles])
        if not mobilites_text:
            mobilites_text = "Non spécifiées"
        self.details_accordion.add_section("Pistes d'évolution", mobilites_text)

        # Compétences d'avenir (Émergentes)
        if job.get('emergente_ratio', 0) >= 0.12:
            emergente_list = job.get('emergente_competences', [])
            if emergente_list:
                emergente_text = "- " + "\n- ".join(emergente_list)
            else:
                emergente_text = "Non spécifiées"
            self.details_accordion.add_section("Compétences d'avenir", emergente_text)

        # Savoirs (from transformed data)
        savoirs_text = "Non spécifiés"
        savoirs_data = job.get('savoirs') # This is already processed in _transform_job_data
        if savoirs_data and savoirs_data.get('categories'):
            savoirs_categories = savoirs_data.get('categories', [])
            savoirs_chunks = []
            for cat in savoirs_categories:
                cat_name = cat.get('libelle', 'Catégorie')
                cat_items = "\n  - ".join([item.get('libelle', '') for item in cat.get('items', []) if item.get('libelle')])
                if cat_items:
                    savoirs_chunks.append(f"{cat_name}:\n  - {cat_items}")
            savoirs_text = "\n\n".join(savoirs_chunks)
        self.details_accordion.add_section("Savoirs", savoirs_text)

        # Contextes de travail (from transformed data)
        context_text = "Non spécifiés"
        contextes_data = job.get('work_context') # This is already processed in _transform_job_data
        if contextes_data:
            context_chunks = []
            for cat in contextes_data:
                cat_name = cat.get('libelle', 'Catégorie')
                cat_items = "\n  - ".join([item.get('libelle', '') for item in cat.get('items', []) if item.get('libelle')])
                if cat_items:
                    context_chunks.append(f"{cat_name}:\n  - {cat_items}")
            context_text = "\n\n".join(context_chunks)
        self.details_accordion.add_section("Contextes de travail", context_text)

        # Secteurs d'activité (from transformed data)
        sectors_text = "Non spécifiés"
        secteurs = job.get('secteurs_activite', [])
        if secteurs:
            sectors_text = "- " + "\n- ".join(secteurs)
        self.details_accordion.add_section("Secteurs d'activité", sectors_text)

    def _transform_job_data(self, raw_jobs):
        """Transforme les données brutes des métiers en une structure plate pour l'affichage."""
        display_jobs = []
        for job in raw_jobs:
            # Compétences
            skills = []
            savoir_faire = job.get('competences', {}).get('savoir_faire', {}).get('enjeux', [])
            for enjeu in savoir_faire:
                for item in enjeu.get('items', []):
                    skills.append({
                        'libelle': item.get('libelle'),
                        'is_core': item.get('coeur_metier') == 'Principale'
                    })

            # Qualités (Savoir-être)
            qualities = []
            savoir_etre = job.get('competences', {}).get('savoir_etre_professionnel', {}).get('enjeux', [])
            if savoir_etre:
                qualities = savoir_etre[0].get('items', [])

            # --- Transformation des mobilités (basée sur ordre_mobilite) ---
            mobilites_raw = job.get('mobilites', [])
            transformed_mobilites = {
                'proches': [m for m in mobilites_raw if 1 <= m.get('ordre_mobilite', 99) <= 3],
                'possibles': [m for m in mobilites_raw if 4 <= m.get('ordre_mobilite', 99) <= 6],
            }

            display_job = {
                'name': job.get('rome', {}).get('intitule', 'N/A'),
                'description': _format_definition_as_bullets(job.get('definition', 'Description non disponible.')),
                'studies_access': job.get('acces_metier', 'Information non spécifiée'),
                'skills': skills,
                'qualities': qualities,
                'mobilites': transformed_mobilites,
                # Ajouter d'autres champs si nécessaire pour le rapport
                'savoirs': job.get('competences', {}).get('savoirs'),
                'savoir_etre_professionnels': job.get('competences', {}).get('savoir_etre_professionnel'),
                'work_context': job.get('contextes_travail'),
                'secteurs_activite': job.get('secteurs_activite', []),
                'emergente_ratio': job.get('_emergente_ratio', 0.0),
                'emergente_competences': job.get('_emergente_competences', []),
            }
            display_jobs.append(display_job)
        return display_jobs



    def restart_quiz(self):
        self.controller.show_frame("WelcomeView")

    def export_report(self):
        try:
            filepath = generate_html_report(self.controller.user_profile, self.controller.jobs_data,
self.controller.active_questions)
            messagebox.showinfo(

                "Rapport généré", f"Votre rapport personnalisé a été sauvegardé ici:\n{filepath}")
        except Exception as e:
            import traceback
            traceback.print_exc()  # Ajout pour imprimer l'erreur détaillée dans la console
            messagebox.showerror("Erreur", f"Impossible de générer le rapport :\\n{e}")

    def export_pdf_report(self):
        try:
            filepath = generate_pdf_report(
                self.controller.user_profile,
                self.controller.jobs_data,
                self.controller.active_questions
            )
            messagebox.showinfo("PDF généré", f"Votre rapport PDF a été sauvegardé ici :\n{filepath}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Impossible de générer le PDF :\n{e}")

    def show_explorer(self):
        self.controller.show_frame("ExplorerView")

    def _start_spinner(self):
        self.spinner_running = True
        self.spinner_chars = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        def update():
            if self.spinner_running:
                self.loading_label.configure(text=self.spinner_chars[self.spinner_index])
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
                self.after(100, update)
        update()

    def _stop_spinner(self):
        self.spinner_running = False

    def _refresh_detail_wraplengths(self):
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scaling = 1.5
        rp_width = self.right_panel.winfo_width()
        if rp_width > 1:
            # winfo_width() returns physical pixels; divide by scaling to get CTk logical pixels
            title_wrap = max(250, int(rp_width / scaling) - 2 * ui_theme.PADDINGS["medium"] - 10)
            self.job_title.configure(wraplength=title_wrap)
            acc_width = self.details_accordion.winfo_width()
            if acc_width > 1:
                content_wrap = max(200, int(acc_width / scaling) - 40)
                self.details_accordion.current_wraplength = content_wrap
                for section in self.details_accordion.sections:
                    if isinstance(section.content_label, ctk.CTkLabel):
                        section.content_label.configure(wraplength=content_wrap)

    def _bind_scroll_to_listframe(self, widget):
        """Propagate mouse-wheel events from widget to the job-list scrollable frame."""
        def _on_wheel(event):
            if event.num == 4 or event.delta > 0:
                self.job_list_frame._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.job_list_frame._parent_canvas.yview_scroll(1, "units")
        widget.bind("<MouseWheel>", _on_wheel, add="+")
        widget.bind("<Button-4>",   _on_wheel, add="+")
        widget.bind("<Button-5>",   _on_wheel, add="+")

    def _update_wraplength(self, event):
        # event.width may be physical pixels; divide by 1.5 scaling to get CTk logical pixels
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scaling = 1.5
        logical_width = event.width / scaling
        new_wraplength = max(280, logical_width - 2 * ui_theme.PADDINGS["medium"] - 10)
        self.job_title.configure(wraplength=int(new_wraplength))

    def _update_job_buttons_wraplength(self, event):
        # event.width = inner canvas physical px; subtract button padx(16) + internal text padding(~24)
        new_wraplength = max(120, event.width - 50)
        for button in self.job_buttons:
            if button._text_label:
                button._text_label.configure(wraplength=new_wraplength)