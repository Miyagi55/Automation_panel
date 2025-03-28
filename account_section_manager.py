import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime
import asyncio
from playwright_manager import playwright_mgr

class Colors:
    PRIMARY = "#2D81FF"
    SECONDARY = "#10B981"
    BG_LIGHT = "#F8FAFC"
    BG_DARK = "#1E293B"
    TEXT = "#334155"
    ACCENT = "#6366F1"

class AccountsSection(ctk.CTkFrame):
    def __init__(self, parent, accounts, log_func, refresh_callback):
        super().__init__(parent)
        self.accounts = accounts if accounts is not None else {}
        self.log = log_func
        self.refresh_callback = refresh_callback
        self.padding = 16
        self.colors = Colors()
        self.next_id = 1

        header = ctk.CTkLabel(self, text="Account Management", font=("Segoe UI", 16, "bold"))
        header.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        add_frame = ctk.CTkFrame(self)
        add_frame.pack(pady=self.padding, padx=self.padding, fill="x")

        self.email_entry = ctk.CTkEntry(add_frame, placeholder_text="Email", width=200)
        self.email_entry.pack(side="left", padx=(0, self.padding // 2))

        self.pw_entry = ctk.CTkEntry(add_frame, placeholder_text="Password", width=200, show="*")
        self.pw_entry.pack(side="left", padx=(0, self.padding // 2))

        add_btn = ctk.CTkButton(add_frame, text="Add", command=self.add_account)
        add_btn.pack(side="left")

        import_btn = ctk.CTkButton(self, text="Import from .txt", command=self.import_accounts)
        import_btn.pack(pady=self.padding // 2, padx=self.padding)

        self.accounts_tree = ttk.Treeview(
            self,
            columns=("ID", "Email", "Password", "Activity", "Status", "Last activity"),
            show="headings",
            height=10,
            selectmode="browse"
        )
        self.accounts_tree.pack(pady=self.padding, padx=self.padding, fill="both", expand=True)

        self.accounts_tree.heading("ID", text="ID")
        self.accounts_tree.heading("Email", text="Email")
        self.accounts_tree.heading("Password", text="Password")
        self.accounts_tree.heading("Activity", text="Activity")
        self.accounts_tree.heading("Status", text="Status")
        self.accounts_tree.heading("Last activity", text="Last Activity")

        self.accounts_tree.column("ID", width=50)
        self.accounts_tree.column("Email", width=150)
        self.accounts_tree.column("Password", width=100)
        self.accounts_tree.column("Activity", width=100)
        self.accounts_tree.column("Status", width=80)
        self.accounts_tree.column("Last activity", width=120)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.accounts_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=self.padding // 2, padx=self.padding, fill="x")

        edit_btn = ctk.CTkButton(button_frame, text="Edit", command=self.edit_account, fg_color=self.colors.PRIMARY, hover_color=self.colors.ACCENT)
        edit_btn.pack(side="left", padx=(0, self.padding // 2))

        delete_btn = ctk.CTkButton(button_frame, text="Delete", command=self.delete_account, fg_color=self.colors.SECONDARY, hover_color=self.colors.ACCENT)
        delete_btn.pack(side="left", padx=(0, self.padding // 2))

        test_btn = ctk.CTkButton(button_frame, text="Test", command=self.test_account, fg_color=self.colors.ACCENT, hover_color=self.colors.PRIMARY)
        test_btn.pack(side="left")

        self.log("AccountsSection initialized")
        self.refresh_treeview()

    def add_account(self, email=None, password=None):
        email = email or self.email_entry.get()
        password = password or self.pw_entry.get()

        if not email or not password:
            messagebox.showwarning("Input Error", "Please provide both email and password.")
            return

        if any(acc["email"] == email for acc in self.accounts.values()):
            messagebox.showerror("Duplicate Error", f"Account '{email}' already exists.")
            return

        try:
            account_id = f"{self.next_id:03d}"
            self.next_id += 1

            account_data = {
                "id": account_id,
                "email": email,
                "password": password,
                "activity": "Inactive",
                "status": "Logged Out",
                "last_activity": ""
            }
            self.accounts[account_id] = account_data

            self.accounts_tree.insert("", tk.END, iid=account_id, values=(
                account_id, email, password, "Inactive", "Logged Out", ""
            ))

            self.log(f"Added account: {email} (ID: {account_id}, Total: {len(self.accounts)})")
            self.email_entry.delete(0, tk.END)
            self.pw_entry.delete(0, tk.END)
            self.refresh_callback()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add account: {str(e)}")
            self.log(f"Error adding account: {str(e)}")

    def import_accounts(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, "r") as f:
                for line in f:
                    try:
                        email, password = line.strip().split(",")
                        self.add_account(email, password)
                    except ValueError:
                        self.log(f"Skipping invalid line in file: {line.strip()}")

    def edit_account(self):
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an account to edit")
            return

        account_id = selected[0]
        account = self.accounts[account_id]
        old_email = account["email"]

        edit_win = ctk.CTkToplevel(self)
        edit_win.title("Edit Account")
        edit_win.geometry("300x200")

        ctk.CTkLabel(edit_win, text="Email").grid(row=0, column=0, padx=5, pady=5)
        email_entry = ctk.CTkEntry(edit_win, width=200)
        email_entry.grid(row=0, column=1, padx=5, pady=5)
        email_entry.insert(0, account["email"])

        ctk.CTkLabel(edit_win, text="Password").grid(row=1, column=0, padx=5, pady=5)
        pw_entry = ctk.CTkEntry(edit_win, width=200, show="*")
        pw_entry.grid(row=1, column=1, padx=5, pady=5)
        pw_entry.insert(0, account["password"])

        def save_changes():
            new_email = email_entry.get()
            new_password = pw_entry.get()

            if not new_email or not new_password:
                messagebox.showwarning("Input Error", "Please provide both email and password.")
                return

            if new_email != old_email and any(acc["email"] == new_email for acc in self.accounts.values()):
                messagebox.showerror("Duplicate Error", f"Account '{new_email}' already exists.")
                return

            self.accounts[account_id].update({
                "email": new_email,
                "password": new_password
            })

            self.accounts_tree.item(account_id, values=(
                account_id, new_email, new_password,
                self.accounts[account_id]["activity"],
                self.accounts[account_id]["status"],
                self.accounts[account_id]["last_activity"]
            ))
            self.log(f"Edited account: {old_email} -> {new_email} (ID: {account_id})")
            self.refresh_callback()
            edit_win.destroy()

        save_btn = ctk.CTkButton(edit_win, text="Save", command=save_changes)
        save_btn.grid(row=2, column=0, columnspan=2, pady=10)

    def delete_account(self):
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an account to delete")
            return

        account_id = selected[0]
        email = self.accounts[account_id]["email"]

        if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{email}'?"):
            del self.accounts[account_id]
            self.accounts_tree.delete(account_id)
            self.log(f"Deleted account: {email} (ID: {account_id}, Total: {len(self.accounts)})")
            self.refresh_callback()

    def update_account_status(self, updates):
        for account_id, update_data in updates.items():
            if account_id in self.accounts:
                self.accounts[account_id].update({
                    "activity": update_data.get("activity", self.accounts[account_id]["activity"]),
                    "status": update_data.get("status", self.accounts[account_id]["status"]),
                    "last_activity": update_data.get("last_activity", self.accounts[account_id]["last_activity"])
                })
                self.accounts_tree.item(account_id, values=(
                    account_id,
                    self.accounts[account_id]["email"],
                    self.accounts[account_id]["password"],
                    self.accounts[account_id]["activity"],
                    self.accounts[account_id]["status"],
                    self.accounts[account_id]["last_activity"]
                ))
                self.log(f"Updated status for account ID {account_id}: {self.accounts[account_id]['status']}")

    def refresh_treeview(self):
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for account_id, account in self.accounts.items():
            self.accounts_tree.insert("", tk.END, iid=account_id, values=(
                account_id, account["email"], account["password"],
                account["activity"], account["status"], account["last_activity"]
            ))

    def test_account(self):
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an account to test")
            return

        account_id = selected[0]
        email = self.accounts[account_id]["email"]
        password = self.accounts[account_id]["password"]
        self.log(f"Testing account: {email}")

        success = asyncio.run(playwright_mgr.test_browser(email, password, self.log))
        if success:
            self.accounts[account_id]["last_activity"] = datetime.datetime.now().strftime("%Y-%m-d %H:%M:%S")
            self.accounts[account_id]["status"] = "Tested"
            self.refresh_treeview()