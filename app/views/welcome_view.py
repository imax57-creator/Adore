
import customtkinter as ctk

class WelcomeView(ctk.CTkFrame):
    def __init__(self, parent, controller, data_manager):
        super().__init__(parent)
        self.controller = controller
        self.data_manager = data_manager

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Title ---
        title_label = ctk.CTkLabel(self, text="Bienvenue sur l'Assistant d'Orientation", font=ctk.CTkFont(size=32, weight="bold"))
        title_label.grid(row=0, column=0, padx=30, pady=(60, 20))

        # --- Description ---
        desc_label = ctk.CTkLabel(self, 
                                  text="Cet assistant vous accompagne dans l'exploration de votre avenir professionnel.\nRépondez à une série de questions pour découvrir les domaines et les métiers qui correspondent le mieux à votre profil.",
                                  font=ctk.CTkFont(size=16),
                                  wraplength=650, justify="center")
        desc_label.grid(row=1, column=0, padx=30, pady=20)

        # --- Buttons Frame ---
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, padx=30, pady=(40, 20))
        buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)

        discover_button = ctk.CTkButton(buttons_frame, 
                                        text="Parcours Découverte\n(Collège/Lycée)", 
                                        command=lambda: self.controller.prompt_for_name('jeune'), 
                                        height=80, font=ctk.CTkFont(size=18, weight="bold"))
        discover_button.grid(row=0, column=0, padx=10, pady=20, sticky="ew")

        reconversion_button = ctk.CTkButton(buttons_frame, 
                                          text="Parcours Reconversion\n(Expérience & Évolution)", 
                                          command=lambda: self.controller.prompt_for_name('adulte'), 
                                          height=80, font=ctk.CTkFont(size=18, weight="bold"))
        reconversion_button.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

        explorer_button = ctk.CTkButton(buttons_frame, 
                                         text="Explorer les métiers", 
                                         command=self.controller.show_explorer, 
                                         height=80, font=ctk.CTkFont(size=18, weight="bold"))
        explorer_button.grid(row=0, column=2, padx=10, pady=20, sticky="ew")

    def prompt_for_name_and_start(self, quiz_type):
        """Prompts for user's name and then starts the selected quiz."""
        dialog = ctk.CTkInputDialog(text="Veuillez entrer votre prénom :", title="Identification")
        name = dialog.get_input()

        if name and name.strip():
            self.controller.user_profile["name"] = name.strip()
        else:
            self.controller.user_profile["name"] = "Anonyme"
        
        self.controller.start_quiz(quiz_type)
