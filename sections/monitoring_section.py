import customtkinter as ctk
import tkinter as tk
import psutil
import datetime

class Colors:
    PRIMARY = "#2D81FF"
    SECONDARY = "#10B981"
    BG_LIGHT = "#F8FAFC"
    BG_DARK = "#1E293B"
    TEXT = "#334155"
    ACCENT = "#6366F1"

class MonitoringSection(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.padding = 16

        header = ctk.CTkLabel(self, text="Monitoring Dashboard", font=("Segoe UI", 16, "bold"))
        header.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        self.log_text = ctk.CTkTextbox(self, height=200)
        self.log_text.pack(pady=self.padding, padx=self.padding, fill="both", expand=True)

        # Add Clear Logs button
        clear_button = ctk.CTkButton(self, text="Clear Logs", command=self.clear_logs, fg_color=Colors.PRIMARY, hover_color=Colors.ACCENT, corner_radius=8)
        clear_button.pack(pady=(0, self.padding), padx=self.padding)

        self.resource_label = ctk.CTkLabel(self, text="CPU: 0% | Memory: 0%")
        self.resource_label.pack(pady=self.padding, padx=self.padding)

        self.update_resources()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def clear_logs(self):
        """Clear all logs in the log_text widget."""
        self.log_text.delete("1.0", tk.END)

    def update_resources(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        self.resource_label.configure(text=f"CPU: {cpu}% | Memory: {memory}%")
        self.after(1000, self.update_resources)