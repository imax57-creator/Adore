import customtkinter as ctk
from .components.accordion import Accordion
from ..utils import format_definition_as_bullets

class ExplorerView(ctk.CTkFrame):

    NAVIGATION_MODES = {
        "Hiérarchie": {
            "fetch_root": lambda dm: dm.get_main_domains(),
            "fetch_children": lambda dm, item: item.get("domaines") or item.get("metiers"),
            "get_item_label": lambda view, item: view._get_item_label(item),
            "is_leaf": lambda item: "code" in item and not ("domaines" in item or "metiers" in item)
        },
        "Secteurs": {
            "fetch_root": lambda dm: dm.get_all_sectors(),
            "fetch_children": lambda dm, item: dm.get_jobs_by_sector(item) if isinstance(item, str) else None,
            "get_item_label": lambda view, item: view._get_item_label(item),
            "is_leaf": lambda item: not isinstance(item, str)
        },
        "Intérêts": {
            "fetch_root": lambda dm: dm.get_all_interests(),
            "fetch_children": lambda dm, item: dm.get_jobs_by_interest(item.get("libelle", "")),
            "get_item_label": lambda view, item: view._get_item_label(item),
            "is_leaf": lambda item: "metiers" not in item
        },
        "Thèmes": {
            "fetch_root": lambda dm: dm.get_all_themes(),
            "fetch_children": lambda dm, item: dm.get_jobs_by_theme(item.get("libelle", "")),
            "get_item_label": lambda view, item: view._get_item_label(item),
            "is_leaf": lambda item: "metiers" not in item
        }
    }

    STATE_KEY_ITEMS = "items"
    STATE_KEY_TITLE = "title"

    def _get_item_label(self, item):
        """Extracts the display label from a navigation item in a robust way."""
        if isinstance(item, str):
            return item
        if "libelle" in item:
            return item["libelle"]
        if "rome" in item and isinstance(item.get("rome"), dict) and "intitule" in item["rome"]:
            return item["rome"]["intitule"]
        if "intitule" in item:
            return item["intitule"]
        return "Inconnu"

    def _save_state(self, items, title):
        self.navigation_history[self.current_tab].append({
            self.STATE_KEY_ITEMS: items,
            self.STATE_KEY_TITLE: title,
        })

    def _restore_state(self):
        if self.navigation_history[self.current_tab]:
            last_state = self.navigation_history[self.current_tab][-1]
            items_to_display = last_state.get(self.STATE_KEY_ITEMS) or last_state.get('items', []) # Fallback for old state
            title_to_display = last_state.get(self.STATE_KEY_TITLE, "")
            return items_to_display, title_to_display
        return None, None

    def __init__(self, parent, controller, data_manager):
        super().__init__(parent)
        self.controller = controller
        self.data_manager = data_manager

        self.navigation_history = {
            "Hiérarchie": [],
            "Secteurs": [],
            "Intérêts": [],
            "Thèmes": []
        }
        self.current_tab = "Hiérarchie"
        self.current_mode = self.NAVIGATION_MODES[self.current_tab]

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_panel.grid_rowconfigure(2, weight=1) # Row 2 for tabview
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.header_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.back_button = ctk.CTkButton(self.header_frame, text="< Précédent", width=100, command=self.go_back)
        self.back_button.grid(row=0, column=0, sticky="w")

        self.title_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=1, padx=10, sticky="w")

        # --- Centralized Search Frame ---
        self.search_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.search_frame.grid(row=1, column=0, padx=10, pady=(5,0), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1) # Search entry takes available space

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Rechercher...")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_input)

        self.search_clear_button = ctk.CTkButton(self.search_frame, text="✕", width=28, height=28, command=self._clear_search)
        self.search_clear_button.grid(row=0, column=1, padx=(5,0))

        # --- Education Level Filter ---
        self.education_filter_var = ctk.StringVar(value="Tous les niveaux")
        education_levels = ["Tous les niveaux"] + self.data_manager.get_education_levels()
        self.education_filter_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.education_filter_var,
            values=education_levels,
            command=self._on_filter_change
        )
        self.education_filter_menu.grid(row=0, column=2, padx=(10,0))
        # --- End Search Frame ---

        self.tabview = ctk.CTkTabview(self.left_panel, command=self.on_tab_change)
        self.tabview.grid(row=2, column=0, padx=10, pady=10, sticky="nsew") # Moved to row 2
        
        self.tab_scroll_frames = {}
        for tab_name in ["Hiérarchie", "Secteurs", "Intérêts", "Thèmes"]:
            tab = self.tabview.add(tab_name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            # height=1 prevents CTkScrollableFrame from trying to grow to fit all
            # content; sticky="nsew" + grid weight expand it to the available space.
            scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=1)
            scroll_frame.grid(row=0, column=0, sticky="nsew")
            scroll_frame.grid_columnconfigure(0, weight=1)
            self.tab_scroll_frames[tab_name] = scroll_frame

        self.right_panel = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.job_title = ctk.CTkLabel(self.right_panel, text="Sélectionnez un métier", font=ctk.CTkFont(size=24, weight="bold"), anchor="w")
        self.job_title.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.details_accordion = Accordion(self.right_panel)
        self.details_accordion.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.right_panel.bind("<Configure>", self._update_wraplength)
        
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
        home_button = ctk.CTkButton(self.bottom_frame, text="Retour à l'accueil", command=lambda: controller.show_frame("WelcomeView"))
        home_button.pack(side="left", padx=10)

        self._search_job = None
        self.item_widgets = []
        self.no_results_label = None

        # Batch rendering state
        self._batch_pending = []
        self._batch_tab = None
        self._batch_row = 0

        self.on_tab_change() # Affichage initial

    def on_tab_change(self, tab_name=None):
        if tab_name is None:
            tab_name = self.tabview.get()
        self.current_tab = tab_name
        self.current_mode = self.NAVIGATION_MODES[self.current_tab]

        # Show/hide search bar based on tab
        if self.current_tab in ["Secteurs", "Intérêts", "Thèmes"]:
            self.search_frame.grid()
        else:
            self.search_frame.grid_remove()
        
        self._clear_search() # Clear search when changing tabs

        if not self.navigation_history[self.current_tab]:
            title = {
                "Hiérarchie": "Grands Domaines",
                "Secteurs": "Secteurs d'activité",
                "Intérêts": "Centres d'intérêt",
                "Thèmes": "Thèmes d'exploration"
            }.get(self.current_tab, "")
            self._display_current_level_items(self.current_mode["fetch_root"](self.data_manager), title, push_to_history=True)
        else:
            items_to_display, title_to_display = self._restore_state()
            if items_to_display is not None:
                self._display_current_level_items(items_to_display, title_to_display, push_to_history=False)

    def _display_current_level_items(self, items, title, push_to_history=True):
        scroll_frame = self.tab_scroll_frames[self.current_tab]
        scroll_frame.bind("<Configure>", self._update_item_labels_wraplength)

        # Cancel any in-flight batch from a previous call
        self._batch_pending = []
        self._batch_tab = self.current_tab
        self._batch_row = 0

        # Clear previous widgets
        for widget, _ in self.item_widgets:
            widget.destroy()
        self.item_widgets = []
        if self.no_results_label:
            self.no_results_label.destroy()
            self.no_results_label = None

        self.title_label.configure(text=title)

        if push_to_history:
            if not self.navigation_history[self.current_tab] or self.navigation_history[self.current_tab][-1][self.STATE_KEY_TITLE] != title:
                self._save_state(items, title)

        if len(self.navigation_history[self.current_tab]) > 1:
            self.back_button.configure(state="normal")
        else:
            self.back_button.configure(state="disabled")

        # Clear the search entry immediately so it feels responsive
        self.search_entry.delete(0, ctk.END)

        # Schedule batch widget creation to avoid blocking the main thread
        self._batch_pending = list(items)
        self._create_next_batch()

    def _create_item_widget(self, scroll_frame, item, row):
        """Creates a single navigation item widget and appends it to item_widgets."""
        item_label = self.current_mode["get_item_label"](self, item)

        item_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent", corner_radius=5)
        item_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        item_frame.grid_columnconfigure(0, weight=1)

        item_label_widget = ctk.CTkLabel(
            item_frame,
            text=item_label,
            font=ctk.CTkFont(size=16),
            anchor="center",
            justify="center",
            wraplength=120
        )
        item_label_widget.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        item_frame.bind("<Button-1>", lambda event, i=item: self.on_item_selected(i))
        item_label_widget.bind("<Button-1>", lambda event, i=item: self.on_item_selected(i))

        item_frame.bind("<Enter>", lambda event, f=item_frame: f.configure(fg_color="gray25"))
        item_frame.bind("<Leave>", lambda event, f=item_frame: f.configure(fg_color="transparent"))
        item_label_widget.bind("<Enter>", lambda event, f=item_frame: f.configure(fg_color="gray25"))
        item_label_widget.bind("<Leave>", lambda event, f=item_frame: f.configure(fg_color="transparent"))

        self._bind_scroll_to([item_frame, item_label_widget], scroll_frame)
        self.item_widgets.append((item_frame, item))

    def _create_next_batch(self, batch_size=30):
        """Creates the next batch of item widgets, then reschedules itself until done."""
        if self._batch_tab != self.current_tab:
            # Tab changed while batch was in progress — discard
            self._batch_pending = []
            return

        if not self._batch_pending:
            # All items created — now apply filter so visibility is correct
            self._perform_filter()
            return

        scroll_frame = self.tab_scroll_frames[self.current_tab]
        batch = self._batch_pending[:batch_size]
        self._batch_pending = self._batch_pending[batch_size:]

        for item in batch:
            self._create_item_widget(scroll_frame, item, self._batch_row)
            self._batch_row += 1

        # Yield to the event loop before creating the next batch
        self.after(0, self._create_next_batch)

    def on_item_selected(self, item_data):
        current_mode = self.current_mode

        if current_mode["is_leaf"](item_data):
            self.display_job_details(item_data)
        else:
            children = current_mode["fetch_children"](self.data_manager, item_data)
            if children:
                item_label = self.current_mode["get_item_label"](self, item_data)
                self._display_current_level_items(children, item_label, push_to_history=True)
            elif item_data.get("code"):
                 self.display_job_details(item_data)

    def go_back(self):
        if len(self.navigation_history[self.current_tab]) > 1:
            self.navigation_history[self.current_tab].pop()
            items_to_display, title_to_display = self._restore_state()
            if items_to_display is not None:
                self._display_current_level_items(items_to_display, title_to_display, push_to_history=False)

    def display_job_details(self, metier_data):
        self.details_accordion.clear()
        self.details_accordion.update_idletasks()

        code_rome = metier_data.get('code') or metier_data.get('rome', {}).get('code_rome')
        job = self.data_manager.get_job_by_code(code_rome)

        if not job:
            self.job_title.configure(text=f"{self._get_item_label(metier_data)}")
            self.details_accordion.add_section("Détails", "Détails non disponibles pour ce métier.")
            return

        self.job_title.configure(text=job.get('rome', {}).get('intitule', 'Titre manquant'))
        
        description_text = format_definition_as_bullets(job.get('definition', 'Description non disponible.'))
        self.details_accordion.add_section("Description du métier", description_text, is_open=True)

        acces_text = job.get('acces_metier', 'Information non spécifiée')
        self.details_accordion.add_section("Accès au métier", acces_text)

        skills_text = "Non spécifiées"
        savoir_faire_enjeux = job.get('competences', {}).get('savoir_faire', {}).get('enjeux', [])
        if savoir_faire_enjeux:
            all_skills = [item.get('libelle') for enjeu in savoir_faire_enjeux for item in enjeu.get('items', []) if item.get('libelle')]
            skills_text = "- " + "\n- ".join(all_skills)
        self.details_accordion.add_section("Compétences (Savoir-faire)", skills_text)

        qualities_text = "Non spécifiées"
        savoir_etre_enjeux = job.get('competences', {}).get('savoir_etre_professionnel', {}).get('enjeux', [])
        if savoir_etre_enjeux and savoir_etre_enjeux[0].get('items'):
            qualities_text = "- " + "\n- ".join([q.get('libelle') for q in savoir_etre_enjeux[0]['items'] if q.get('libelle')])
        self.details_accordion.add_section("Savoir-être professionnels", qualities_text)

        savoirs_text = "Non spécifiés"
        savoirs_categories = job.get('competences', {}).get('savoirs', {}).get('categories', [])
        if savoirs_categories:
            savoirs_chunks = []
            for cat in savoirs_categories:
                cat_name = cat.get('libelle', 'Catégorie')
                cat_items = "\n  - ".join([item.get('libelle') for item in cat.get('items', []) if item.get('libelle')])
                if cat_items:
                    savoirs_chunks.append(f"{cat_name}:\n  - {cat_items}")
            savoirs_text = "\n\n".join(savoirs_chunks)
        self.details_accordion.add_section("Savoirs", savoirs_text)

        context_text = "Non spécifiés"
        contextes = job.get('contextes_travail', [])
        if contextes:
            context_chunks = []
            for cat in contextes:
                cat_name = cat.get('libelle', 'Catégorie')
                cat_items = "\n  - ".join([item.get('libelle') for item in cat.get('items', []) if item.get('libelle')])
                if cat_items:
                    context_chunks.append(f"{cat_name}:\n  - {cat_items}")
            context_text = "\n\n".join(context_chunks)
        self.details_accordion.add_section("Contextes de travail", context_text)

        sectors_text = "Non spécifiés"
        secteurs = job.get('secteurs_activite', [])
        if secteurs:
            sectors_text = "- " + "\n- ".join(secteurs)
        self.details_accordion.add_section("Secteurs d'activité", sectors_text)

        mobilites_text = "Non spécifiées"
        mobilites = job.get('mobilites', [])
        if mobilites:
            mobilites_text = "- " + "\n- ".join([m.get('rome_cible', '') for m in mobilites])
        self.details_accordion.add_section("Pistes d'évolution", mobilites_text)

    def _on_search_input(self, event=None):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self._perform_filter)

    def _on_filter_change(self, choice=None):
        self._perform_filter()

    def _clear_search(self):
        self.search_entry.delete(0, ctk.END)
        # Don't filter while a batch is still being created — _create_next_batch
        # will call _perform_filter() itself after the last batch.
        if not self._batch_pending:
            self._perform_filter()

    def _perform_filter(self):
        search_text = self.search_entry.get().lower()
        selected_level = self.education_filter_var.get()
        
        if selected_level == "Tous les niveaux":
            allowed_codes = set(self.data_manager._jobs_map.keys())
        else:
            allowed_codes = self.data_manager.get_job_codes_by_level(selected_level)

        visible_items = 0
        
        if self.no_results_label:
            self.no_results_label.grid_remove()

        for widget, item in self.item_widgets: # Unpack the full item data
            # The widget is the CTkFrame, its child is the CTkLabel
            label_widget = widget.winfo_children()[0]
            label_text = label_widget.cget("text").lower()
            text_match = search_text in label_text

            # Determine level match based on whether the item is a leaf (a job)
            if not self.current_mode["is_leaf"](item):
                level_match = True # Always show categories/intermediate nodes
            else:
                # It's a job, so check its ROME code against the filter
                if isinstance(item, dict):
                    code_rome = item.get('code') or item.get('rome', {}).get('code_rome')
                else:
                    code_rome = None
                level_match = code_rome in allowed_codes

            if text_match and level_match:
                widget.grid()
                visible_items += 1
            else:
                widget.grid_remove()
        
        # Show "No results" if either filter is active and nothing is visible
        is_filtering = search_text or selected_level != "Tous les niveaux"
        if visible_items == 0 and is_filtering:
            scroll_frame = self.tab_scroll_frames[self.current_tab]
            if not self.no_results_label:
                self.no_results_label = ctk.CTkLabel(scroll_frame, text="Aucun résultat", font=ctk.CTkFont(size=16, slant="italic"))
            self.no_results_label.grid(row=0, column=0, pady=20)

    def _update_wraplength(self, event):
        # event.width is physical px; divide by CTk scaling to get logical units
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scaling = 1.5
        logical_width = event.width / scaling
        new_wraplength = max(200, int(logical_width) - 20)
        self.job_title.configure(wraplength=new_wraplength)

    @staticmethod
    def _bind_scroll_to(widgets, scrollable_frame):
        """Propagate mouse-wheel events from each widget to scrollable_frame's canvas."""
        def _on_wheel(event):
            if event.num == 4 or event.delta > 0:
                scrollable_frame._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                scrollable_frame._parent_canvas.yview_scroll(1, "units")
        for w in widgets:
            w.bind("<MouseWheel>", _on_wheel, add="+")
            w.bind("<Button-4>",   _on_wheel, add="+")
            w.bind("<Button-5>",   _on_wheel, add="+")

    def _update_item_labels_wraplength(self, event):
        # event.width is physical px; divide by CTk scaling to get logical units
        # Subtract item_frame padx(5*2=10) + label padx(10*2=20) = 30 logical px total
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scaling = 1.5
        logical_width = event.width / scaling
        new_wraplength = max(100, int(logical_width) - 30)
        for widget, _ in self.item_widgets:
            label = widget.winfo_children()[0]
            if isinstance(label, ctk.CTkLabel):
                label.configure(wraplength=new_wraplength)