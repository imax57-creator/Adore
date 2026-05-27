import customtkinter as ctk

class NameView(ctk.CTkFrame):
    def __init__(self, parent, controller, data_manager):
        super().__init__(parent)
        self.controller = controller
        self.data_manager = data_manager

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, pady=20)

        self.title_label = ctk.CTkLabel(container, text="", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(0, 20))

        self.name_entry = ctk.CTkEntry(container, placeholder_text="", width=300, height=40, font=ctk.CTkFont(size=16))
        self.name_entry.pack(pady=10)
        self.name_entry.bind("<Return>", self.submit_name)

        continue_button = ctk.CTkButton(container, text="Continuer", command=self.submit_name, height=40, font=ctk.CTkFont(size=16, weight="bold"))
        continue_button.pack(pady=20)

    def update_texts(self):
        quiz_mode = self.controller.quiz_to_start
        self.title_label.configure(text=self.controller.text_provider.get_text("name_view_title", quiz_mode))
        self.name_entry.configure(placeholder_text=self.controller.text_provider.get_text("name_view_placeholder", quiz_mode))

    def submit_name(self, event=None):
        """Submits the name and proceeds to the quiz."""
        name = self.name_entry.get()
        if name and name.strip():
            self.controller.user_profile["name"] = name.strip()
        else:
            self.controller.user_profile["name"] = "Anonyme"
        
        # The quiz_type is stored in the controller
        self.controller.start_quiz(self.controller.quiz_to_start)
