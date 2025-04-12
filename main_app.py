import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import psutil
from automation_section_manager import AutomationSection
from account_section_manager import AccountsSection
from settings_section import SettingsSection
import datetime

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class Colors:
    PRIMARY = "#2D81FF"
    SECONDARY = "#10B981"
    BG_LIGHT = "#F8FAFC"
    BG_DARK = "#1E293B"
    TEXT = "#334155"
    ACCENT = "#6366F1"

class SocialMediaAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Facebook Automation Panel")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.colors = Colors()
        self.padding = 16
        self.corner_radius = 8
        self.workflows = {}

        self.sidebar = Sidebar(self, self.show_section)
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.pack(side="right", fill="both", expand=True)

        self.sections = {
            "monitoring": MonitoringSection(self.content_frame),
            "accounts": None,
            "automation": None,
            "settings": None
        }
        # Initialize AccountsSection without passing accounts (loaded from JSON internally)
        self.sections["accounts"] = AccountsSection(self.content_frame, self.sections["monitoring"].log, self._refresh_automation_accounts)
        # Pass the accounts from AccountsSection to AutomationSection
        self.sections["automation"] = AutomationSection(self.content_frame, self.sections["accounts"].accounts, self.workflows, self.sections["monitoring"].log)
        self.sections["settings"] = SettingsSection(self.content_frame, self.sections["monitoring"].log)

        self.show_section("accounts")
        self.sections["monitoring"].log("App initialized")

    def show_section(self, section_name):
        for frame in self.sections.values():
            frame.pack_forget()
        self.sections[section_name].pack(fill="both", expand=True)

    def _refresh_automation_accounts(self):
        # Update the accounts in AutomationSection when accounts change
        self.sections["automation"].accounts = self.sections["accounts"].accounts
        self.sections["automation"].refresh_accounts()

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, show_section_callback):
        super().__init__(parent, width=250, corner_radius=0)
        self.pack(side="left", fill="y", expand=False)
        self.colors = Colors()
        self.padding = 16
        self.corner_radius = 8
        self.show_section = show_section_callback

        title_label = ctk.CTkLabel(self, text="Automation Panel", font=("Segoe UI", 18, "bold"), text_color=self.colors.TEXT)
        title_label.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        buttons = [
            ("Accounts", lambda: self.show_section("accounts")),
            ("Automation", lambda: self.show_section("automation")),
            ("Monitoring", lambda: self.show_section("monitoring")),
            ("Settings", lambda: self.show_section("settings"))
        ]
        for btn_text, cmd in buttons:
            btn = ctk.CTkButton(self, text=btn_text, command=cmd, fg_color=self.colors.PRIMARY,
                                hover_color=self.colors.ACCENT, corner_radius=self.corner_radius)
            btn.pack(pady=self.padding // 2, padx=self.padding, fill="x")

        self.theme_switch = ctk.CTkSwitch(self, text="Dark Mode", command=self.toggle_theme, onvalue="Dark", offvalue="Light")
        self.theme_switch.pack(pady=self.padding, padx=self.padding, side="bottom")

    def toggle_theme(self):
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)
        parent_frame = self.master.content_frame
        parent_frame.configure(fg_color=self.colors.BG_DARK if mode == "Dark" else self.colors.BG_LIGHT)

class MonitoringSection(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.padding = 16

        header = ctk.CTkLabel(self, text="Monitoring Dashboard", font=("Segoe UI", 16, "bold"))
        header.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        self.log_text = ctk.CTkTextbox(self, height=200)
        self.log_text.pack(pady=self.padding, padx=self.padding, fill="both", expand=True)

        self.resource_label = ctk.CTkLabel(self, text="CPU: 0% | Memory: 0%")
        self.resource_label.pack(pady=self.padding, padx=self.padding)

        self.update_resources()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def update_resources(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        self.resource_label.configure(text=f"CPU: {cpu}% | Memory: {memory}%")
        self.after(1000, self.update_resources)

if __name__ == "__main__":
    app = SocialMediaAutomationApp()
    app.mainloop()