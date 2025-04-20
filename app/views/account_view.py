"""
Account view for managing Facebook accounts.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict

import customtkinter as ctk

from app.utils.logger import logger

from .base_view import BaseView


class AccountView(BaseView):
    """
    View for managing Facebook accounts.
    """

    def __init__(self, parent, controllers: Dict[str, Any]):
        
        super().__init__(parent, controllers)

    def setup_ui(self):
        
        self.create_header("Account Management")

        # Account entry form
        self._setup_entry_form()
       
        self._setup_accounts_table()
        self._setup_action_buttons()

    def _setup_entry_form(self):
        """Set up the account entry form."""
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(pady=self.padding, padx=self.padding, fill="x")

        self.user_entry = ctk.CTkEntry(
            add_frame, placeholder_text="Username", width=200
        )
        self.user_entry.pack(side="left", padx=(0, self.padding // 2))

        self.pw_entry = ctk.CTkEntry(
            add_frame, placeholder_text="Password", width=200, show="*"
        )
        self.pw_entry.pack(side="left", padx=(0, self.padding // 2))

        add_btn = ctk.CTkButton(add_frame, text="Add", command=self._add_account)
        add_btn.pack(side="left")

        import_btn = self.create_button("Import from .txt", self._import_accounts)
        import_btn.pack(padx=(0, self.padding // 2), fill='x')

        

    def _setup_accounts_table(self):
        """Set up the accounts table."""
        self.accounts_tree = ttk.Treeview(
            self,
            columns=(
                "ID",
                "Username",
                "Password",
                "Activity",
                "Status",
                "Last activity",
            ),
            show="headings",
            height=10,
            selectmode="extended",  # Allow multi-selection
        )
        self.accounts_tree.pack(
            pady=self.padding, padx=self.padding, fill="both", expand=True
        )

        columns = {
            "ID": {"text": "ID", "width": 50},
            "Username": {"text": "Username", "width": 150},
            "Password": {"text": "Password", "width": 100},
            "Activity": {"text": "Activity", "width": 100},
            "Status": {"text": "Status", "width": 80},
            "Last activity": {"text": "Last Activity", "width": 120}
        }

        # Set headings and column widths
        for col, config in columns.items():
            self.accounts_tree.heading(col, text=config["text"])
            self.accounts_tree.column(col, width=config["width"])

        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.accounts_tree.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)

    def _setup_action_buttons(self):
        """Set up the action buttons."""
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=self.padding // 2, padx=self.padding, fill="x")

        edit_btn = ctk.CTkButton(button_frame, text="Edit", command=self._edit_account)
        edit_btn.pack(side="left", padx=(0, self.padding // 2))

        delete_btn = ctk.CTkButton(
            button_frame, text="Delete", command=self._delete_account
        )
        delete_btn.pack(side="left", padx=(0, self.padding // 2))

        run_browser_btn = ctk.CTkButton(button_frame, text="Run browser(s)", command=self._test_account)
        run_browser_btn.pack(side="left")

        auto_login_btn = ctk.CTkButton(button_frame, text="Auto login", command=self._test_account)
        auto_login_btn.pack(side='right')

        

    def refresh(self):
        """Refresh the accounts table."""
        
        self.accounts_tree.delete(*self.accounts_tree.get_children())

        
        accounts = self.controllers["account"].get_all_accounts()

        # If accounts is None or empty, just return
        if not accounts:
            return

        # Insert accounts into treeview
        for account_id, account in accounts.items():
            try:
                self.accounts_tree.insert(
                    "",
                    "end",
                    values=(
                        account_id,
                        account.get("user", ""),
                        "*" * len(account.get("password", "")),  # Mask password
                        account.get("activity", ""),
                        account.get("status", ""),
                        account.get("last_activity", ""),
                    ),
                    iid=account_id,
                )
            except Exception as e:
                logger.error(f"Error adding account {account_id} to view: {str(e)}")

    def _add_account(self):
       
        user = self.user_entry.get()
        password = self.pw_entry.get()

        account_id, error_message = self.controllers["account"].add_account(user, password)

        if account_id:
            self.user_entry.delete(0, tk.END)
            self.pw_entry.delete(0, tk.END)
            self.refresh()
            messagebox.showinfo("Success", "Account addded sucessfully")
        else:
            messagebox.showerror("Error", error_message or "Failed to add account")

    def _edit_account(self):
        
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an account to edit")
            return

        account_id = selected[0]
        account = self.controllers["account"].get_account(account_id)
        if not account:
            messagebox.showerror("Error", "Account not found")
            return

        edit_win = ctk.CTkToplevel(self)
        edit_win.title("Edit Account")
        edit_win.geometry("300x200")
        edit_win.transient(self)  # Make the window modal
        edit_win.grab_set()

        ctk.CTkLabel(edit_win, text="Username").grid(row=0, column=0, padx=5, pady=5)
        user_entry = ctk.CTkEntry(edit_win, width=200)
        user_entry.grid(row=0, column=1, padx=5, pady=5)
        user_entry.insert(0, account["user"])

        ctk.CTkLabel(edit_win, text="Password").grid(row=1, column=0, padx=5, pady=5)
        pw_entry = ctk.CTkEntry(edit_win, width=200, show="*")
        pw_entry.grid(row=1, column=1, padx=5, pady=5)
        pw_entry.insert(0, account["password"])

        def save_changes():
            success = self.controllers["account"].update_account(
                account_id, user_entry.get(), pw_entry.get()
            )
            if success:
                edit_win.destroy()
                self.refresh()
            else:
                messagebox.showerror("Error", "Failed to update account")

        save_btn = ctk.CTkButton(edit_win, text="Save", command=save_changes)
        save_btn.grid(row=2, column=0, columnspan=2, pady=10)

    def _delete_account(self):
        
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an account to delete")
            return

        if messagebox.askyesno(
            "Confirm", f"Are you sure you want to delete {len(selected)} account(s)?"
        ):
            for account_id in selected:
                self.controllers["account"].delete_account(account_id)
            self.refresh()
    


    ##------------------------------test_account(s)-------------------°°°°!!!!!!!!!
    def _test_account(self):
        
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning(
                "Warning", "Please select at least one account to test"
            )
            return

        if len(selected) == 1:
            
            self.controllers["account"].test_account(selected[0])
        else:
            
            self.controllers["account"].test_multiple_accounts(list(selected))

        # Update status immediately
        for account_id in selected:
            self.accounts_tree.item(
                account_id,
                values=(
                    account_id,
                    self.accounts_tree.item(account_id)["values"][1],  # Username
                    self.accounts_tree.item(account_id)["values"][2],  # Password
                    "Testing",
                    "Testing",
                    "",
                ),
            )

    def _import_accounts(self):
        
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            count = self.controllers["account"].import_accounts_from_file(file_path)
            messagebox.showinfo(
                "Import Accounts", f"Successfully imported {count} accounts"
            )
            self.refresh()
