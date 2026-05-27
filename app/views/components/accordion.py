import customtkinter as ctk

class Accordion(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.sections = []
        self.row_counter = 0
        self.current_wraplength = 300  # Valeur par défaut initiale

        # Écouter les événements de redimensionnement pour ajuster le wraplength
        self.bind("<Configure>", self._on_resize)
        # Propagate scroll on the accordion frame itself (between sections)
        self.bind("<MouseWheel>", self._on_mouse_scroll, add="+")
        self.bind("<Button-4>",   self._on_mouse_scroll, add="+")
        self.bind("<Button-5>",   self._on_mouse_scroll, add="+")

    def _find_parent_scrollable(self):
        parent = self.master
        while parent:
            if isinstance(parent, ctk.CTkScrollableFrame):
                return parent
            parent = parent.master
        return None

    def _on_mouse_scroll(self, event):
        scrollable_parent = self._find_parent_scrollable()
        if not scrollable_parent:
            return
        if event.num == 4 or event.delta > 0:
            scrollable_parent._parent_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            scrollable_parent._parent_canvas.yview_scroll(1, "units")

    def _on_resize(self, event):
        # event.width is in physical pixels; divide by CTk scaling to get logical units
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scaling = 1.5
        logical_width = event.width / scaling
        new_length = max(200, int(logical_width) - 40)

        if abs(new_length - self.current_wraplength) > 10:
            self.current_wraplength = new_length
            for section in self.sections:
                if isinstance(section.content_label, ctk.CTkLabel):
                    section.content_label.configure(wraplength=self.current_wraplength)

    def clear(self):
        """Destroys all sections within the accordion and resets it."""
        for section in self.sections:
            section.destroy()
        self.sections = []
        self.row_counter = 0

    def add_section(self, title, content_text, is_open=False):
        section = AccordionSection(self, title, content_text, is_open=is_open)
        section.grid(row=self.row_counter, column=0, sticky="ew", pady=5)
        self.sections.append(section)
        self.row_counter += 1
        # Appliquer le wraplength initial au label de contenu
        section.content_label.configure(wraplength=self.current_wraplength)

class AccordionSection(ctk.CTkFrame):
    def __init__(self, master, title, content_text, is_open=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.content_visible = is_open

        # Bouton pour le titre de la section
        self.title_button = ctk.CTkButton(self, text=title, 
                                          command=self._toggle_content,
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          anchor="w",
                                          fg_color="gray30",
                                          hover_color="gray25")
        self.title_button.grid(row=0, column=0, sticky="ew", pady=(5,0))

        # Frame pour le contenu
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Créer et ajouter le widget de contenu avec le bon parent
        self.content_label = ctk.CTkLabel(self.content_frame, text=content_text, justify="left", anchor="w")
        self.content_label.pack(fill="both", expand=True, padx=10, pady=5)

        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))
        if not is_open: # Cacher le contenu seulement s'il n'est pas initialement ouvert
            self.content_frame.grid_remove()

        # Bind mouse scroll event to all widgets in the section
        self.bind_mouse_scroll_to_children()

    def _find_parent_scrollable(self):
        """Traverse up the widget hierarchy to find the CTkScrollableFrame."""
        parent = self.master
        while parent:
            if isinstance(parent, ctk.CTkScrollableFrame):
                return parent
            parent = parent.master
        return None

    def _toggle_content(self):
        """Toggle the visibility of the content frame and update the scroll region."""
        if self.content_visible:
            self.content_frame.grid_remove()
        else:
            self.content_frame.grid()
        self.content_visible = not self.content_visible

        # Give time for the grid change to register before updating the scroll region
        self.after(10, self._update_parent_scroll_region)

    def _update_parent_scroll_region(self):
        """Force the parent scrollable frame to update its scroll region."""
        scrollable_parent = self._find_parent_scrollable()
        if scrollable_parent:
            scrollable_parent._parent_canvas.configure(scrollregion=scrollable_parent._parent_canvas.bbox("all"))

    def bind_mouse_scroll_to_children(self):
        """Bind mouse wheel event to all children of this section."""
        widgets = [self, self.title_button, self.content_frame, self.content_label]
        for widget in widgets:
            widget.bind("<MouseWheel>", self._on_mouse_scroll, add="+")
            widget.bind("<Button-4>", self._on_mouse_scroll, add="+") # For Linux scroll up
            widget.bind("<Button-5>", self._on_mouse_scroll, add="+") # For Linux scroll down

    def _on_mouse_scroll(self, event):
        """
        Propagate mouse wheel event to the nearest parent CTkScrollableFrame.
        This implementation is cross-platform.
        """
        scrollable_parent = self._find_parent_scrollable()
        if not scrollable_parent:
            return

        if event.num == 4 or event.delta > 0:  # Linux scroll up or Windows/macOS scroll up
            scrollable_parent._parent_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:  # Linux scroll down or Windows/macOS scroll down
            scrollable_parent._parent_canvas.yview_scroll(1, "units")