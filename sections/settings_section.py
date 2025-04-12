import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
from sections.playwright_manager import playwright_mgr

class SettingsSection(ctk.CTkFrame):
    def __init__(self, parent, log_func):
        super().__init__(parent)
        self.log = log_func
        self.padding = 16

        header = ctk.CTkLabel(self, text="Settings", font=("Segoe UI", 16, "bold"))
        header.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        download_btn = ctk.CTkButton(self, text="Download Webdrivers", command=self.download_webdrivers)
        download_btn.pack(pady=self.padding, padx=self.padding)


    def download_webdrivers(self):
        """Start webdriver download in a separate thread and show progress window."""
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("Downloading Webdrivers")
        progress_win.geometry("300x150")
        progress_win.transient(self)  # Tie to parent window
        progress_win.grab_set()  # Make modal

        status_label = ctk.CTkLabel(progress_win, text="Starting download...")
        status_label.pack(pady=10)
        progress_bar = ctk.CTkProgressBar(progress_win, width=250)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        def update_progress(message, value):
            status_label.configure(text=message)
            progress_bar.set(value)
            if value >= 1.0:
                progress_win.after(1000, progress_win.destroy)  # Close after 1s

        def run_installation():
            success = playwright_mgr.install_webdrivers(self.log, update_progress)
            if success:
                messagebox.showinfo("Success", "Webdrivers downloaded successfully!")
            else:
                messagebox.showerror("Error", "Failed to download webdrivers. Check logs for details.")

        threading.Thread(target=run_installation, daemon=True).start()