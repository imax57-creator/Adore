






import customtkinter as ctk
from app.main_app import MainApp

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("assets/theme_arcade_gold.json")

    app = MainApp()
    app.mainloop()
