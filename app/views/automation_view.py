import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List

import customtkinter as ctk

from app.utils.logger import logger

from .base_view import BaseView





#------------------------------------------class-----------------------------------------#

class ActionConfigPanel(ctk.CTkFrame):
    """Panel for configuring actions for a workflow."""

    ACTION_TYPES = ["Comments", "Posts", "Live Views", "Likes", "Shares"]

    def __init__(self, parent, padding: int = 16):
        super().__init__(parent)
        self.padding = padding
        self.action_vars = {}
        self.action_inputs = {}
        self.pack(side="left", padx=(0, padding), fill="y")
        self._setup_checkboxes()

    def _setup_checkboxes(self):
        """Create checkboxes with input fields to the right for each action type."""
        title = ctk.CTkLabel(
            self, text="Select Actions:", font=("Segoe UI", 12, "bold")
        )
        title.pack(pady=(0, self.padding // 2), anchor="w")

        for action in self.ACTION_TYPES:

            # Create a frame for each action to hold checkbox and input
            action_frame = ctk.CTkFrame(self)
            action_frame.pack(pady=(0, 2), fill="x")  

            var = ctk.BooleanVar()
            checkbox = ctk.CTkCheckBox(
                action_frame,
                text=action,
                variable=var,
                command=lambda a=action: self._toggle_input_visibility(a),
                height=30,  # Set a fixed height to prevent "fat" appearance
                
            )
            checkbox.pack(side="left", padx=(0, self.padding // 2), pady=0)  # No vertical padding

            # Create input field based on action type
            input_configs = {
                "Comments": {
                    "width": 150,  # Will be overridden by fill="x"
                    "load_comments": [("Load file", self._load_comments_file)],
                },
                "Live Views": {"width": 300},
                "Likes": {"width": 300},
                "Shares": {"width": 300},
                "Posts": {
                    "width": 300,
                    "entry_name": "content_entry",
                },
            }

            config = input_configs[action]
            # Create a subframe for the entry and button to allow fill="x"
            input_subframe = ctk.CTkFrame(action_frame, height=30)  # Match checkbox height
            input_subframe.pack(side="left", fill="x", expand=True)

            entry_name = config.get("entry_name", "link_entry")
            entry = ctk.CTkEntry(input_subframe, width=config["width"], height=30, placeholder_text="Link post/URL")
            entry.pack(side="left", fill="x", expand=True, pady=0)  # No vertical padding
            entry.pack_forget()  # Initially hidden

            self.action_vars[action] = var
            self.action_inputs[action] = [entry]  # Store entry in list

            if "load_comments" in config:
                for text, command in config["load_comments"]:
                    button = ctk.CTkButton(
                        input_subframe,
                        text=text,
                        command=lambda a=action, cmd=command: cmd(a),
                        height=30,  
                    )
                    button.pack(side="left", padx=(5, 0), pady=0)
                    button.pack_forget()  
                    self.action_inputs[action].append(button)  # Store button

    def _toggle_input_visibility(self, action: str):
        """Toggle visibility of input fields for the selected action."""
        entry = self.action_inputs[action][0]  # Entry widget
        if self.action_vars[action].get():
            entry.pack(side="left", fill="x", expand=True, pady=0)
            if len(self.action_inputs[action]) > 1:  # Check for extra button (Comments)
                self.action_inputs[action][1].pack(side="left", padx=(5, 0), pady=0)
        else:
            entry.pack_forget()
            if len(self.action_inputs[action]) > 1:
                self.action_inputs[action][1].pack_forget()

    def _load_comments_file(self, action: str):
        """Load comments file for comments action."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.action_inputs[action].append(file_path)  # Store file path
            filename = file_path.split("/")[-1]
            self.action_inputs[action][0].delete(0, tk.END)
            self.action_inputs[action][0].insert(0, f"File: {filename}")

    def get_selected_actions(self) -> Dict[str, dict]:
        """Retrieve selected actions with their configuration."""
        actions = {}
        for action, var in self.action_vars.items():
            if var.get() and action in self.action_inputs:
                actions[action] = self._get_action_details(action)
        return actions

    def _get_action_details(self, action: str) -> dict:
        
        entry = self.action_inputs[action][0]
        if action == "Comments":
            file_path = self.action_inputs[action][2] if len(self.action_inputs[action]) > 2 else None
            return {
                "link": entry.get(),
                "comments_file": file_path,
            }
        elif action in ["Live Views", "Likes", "Shares"]:
            return {"link": entry.get()}
        elif action == "Posts":
            return {"content": entry.get()}

    def reset(self):
        
        for action, var in self.action_vars.items():
            var.set(False)
            self._toggle_input_visibility(action)






#------------------------------------------class-----------------------------------------#

class AccountSelector(ctk.CTkFrame):
    """UI component for selecting accounts."""

    def __init__(self, parent, save_callback, padding: int = 16):
        super().__init__(parent)
        self.padding = padding
        self.save_callback = save_callback  # Store the save callback
        self._setup_ui()

    def _setup_ui(self):
        
        title = ctk.CTkLabel(
            self, text="Select Accounts:", font=("Segoe UI", 12, "bold")
        )
        title.pack(anchor="w", pady=(0, self.padding // 2))

        listbox_frame = ctk.CTkFrame(self)
        listbox_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            listbox_frame,
            height=10,
            width=30,
            selectmode=tk.MULTIPLE,
            font=("Segoe UI", 12),
        )

        self.scrollbar = tk.Scrollbar(
            listbox_frame, orient="vertical", command=self.listbox.yview
        )
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.listbox.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="left", fill="y")

        select_frame = ctk.CTkFrame(self)
        select_frame.pack(pady=(self.padding // 2, 0), fill="x")  # Reduced bottom padding

        ctk.CTkLabel(select_frame, text="Select Range:").pack(side="left")
        self.select_entry = ctk.CTkEntry(select_frame, width=100, placeholder_text="001-012")
        self.select_entry.pack(side="left", padx=5)

        ctk.CTkButton(select_frame, text="Select", command=self._select_range).pack(
            side="left"
        )

        # Workflow save section (below Select Range)
        save_frame = ctk.CTkFrame(self)
        save_frame.pack(pady=(self.padding // 2, 0), fill="x")

        ctk.CTkLabel(save_frame, text="Workflow Name:").pack(
            side="left", padx=(0, self.padding // 2)
        )
        self.workflow_name_entry = ctk.CTkEntry(save_frame, width=150, placeholder_text="wf-masslikes-01")
        self.workflow_name_entry.pack(side="left", padx=(0, self.padding // 2))

        save_btn = ctk.CTkButton( 
            save_frame, text="Save Workflow", command=self.save_callback
            
        )
        save_btn.pack(side="left")

    def set_accounts(self, accounts: Dict[str, Dict[str, Any]]):
        
        self.listbox.delete(0, tk.END)

        if not accounts:
            return

        for account_id, account in accounts.items():
            try:
                account_id = account.get("id", account_id)
                email = account.get("user")
                self.listbox.insert(tk.END, f"{account_id} - {email}")
            except Exception as e:
                logger.error(
                    f"Error adding account {account_id} to automation selector: {str(e)}"
                )

    def get_selected_accounts(self) -> List[str]:
        
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return []

        items = [self.listbox.get(i) for i in selected_indices]
        return [item.split(" - ")[1] for item in items]

    def _select_range(self):
        """Select accounts within a specified ID range."""
        try:
            range_text = self.select_entry.get().strip()
            if not range_text:
                return

            if "-" in range_text:
                start, end = map(int, range_text.split("-"))
                self.listbox.selection_clear(0, tk.END)
                for i in range(self.listbox.size()):
                    item = self.listbox.get(i)
                    item_id = int(item.split(" - ")[0])
                    if start <= item_id <= end:
                        self.listbox.selection_set(i)
            else:
                id_num = int(range_text)
                for i in range(self.listbox.size()):
                    item = self.listbox.get(i)
                    item_id = int(item.split(" - ")[0])
                    if id_num == item_id:
                        self.listbox.selection_clear(0, tk.END)
                        self.listbox.selection_set(i)
                        break
        except ValueError:
            messagebox.showwarning(
                "Input Error",
                "Invalid format. Use '001-005' for range or '003' for single.",
            )




#------------------------------------------class-----------------------------------------#

class WorkflowList(ctk.CTkScrollableFrame):
    """Scrollable list of workflows with status and progress tracking."""

    def __init__(self, parent, padding: int = 16):
        self.min_height, self.max_height, self.row_height = 50, 300, 35
        super().__init__(parent, height=self.min_height)
        self.padding = padding
        self.widgets = {}
        self.pack(pady=padding, padx=padding, fill="x")

    def add_workflow(self, name: str):
        
        if name in self.widgets:
            return

        frame = ctk.CTkFrame(self)
        frame.pack(pady=(0, self.padding // 2), fill="x")

        check_var = ctk.BooleanVar()
        check = ctk.CTkCheckBox(frame, text=name, variable=check_var)
        check.pack(side="left", padx=self.padding)

        progress = ctk.CTkProgressBar(frame, width=150)
        progress.pack(side="left", padx=self.padding)
        progress.set(0)

        status = ctk.CTkLabel(frame, text="Ready")
        status.pack(side="left", padx=self.padding)

        delete_btn = ctk.CTkButton(
            frame, text="Delete", width=80, command=lambda n=name: self._delete(n)
        )
        delete_btn.pack(side="right", padx=self.padding)

        self.widgets[name] = {
            "frame": frame,
            "check": check,
            "check_var": check_var,
            "progress": progress,
            "status": status,
            "delete_btn": delete_btn,
        }
        self._update_height()

    def _delete(self, name: str):
        
        if name in self.widgets:
            self.widgets[name]["frame"].destroy()
            del self.widgets[name]
            self._update_height()

    def _update_height(self):
        
        num_workflows = len(self.widgets)
        height = min(
            self.max_height, max(self.min_height, num_workflows * self.row_height)
        )
        self.configure(height=height)

    def get_selected(self) -> List[str]:
        
        return [
            name for name, widgets in self.widgets.items() if widgets["check_var"].get()
        ]

    def update_status(self, name: str, status: str):
        
        if name in self.widgets:
            self.widgets[name]["status"].configure(text=status)

    def update_progress(self, name: str, value: float):
        
        if name in self.widgets:
            self.widgets[name]["progress"].set(value)

    def reset(self):
        
        for widgets in self.widgets.values():
            widgets["check_var"].set(False)
            widgets["progress"].set(0)
            widgets["status"].configure(text="Ready")





#------------------------------------------class-----------------------------------------#
class AutomationView(BaseView):
    """View for managing workflows and automation."""

    def __init__(self, parent, controllers: Dict[str, Any]):
        super().__init__(parent, controllers)

    def setup_ui(self):
        
        self.create_header("Automation")

        # Create the workflow configuration section (top section)
        config_frame = ctk.CTkFrame(self)
        config_frame.pack(pady=(self.padding, self.padding), padx=self.padding, fill="x")

        # Action configuration panel
        self.action_config = ActionConfigPanel(config_frame)

        # Account selector (includes Workflow save section)
        self.account_selector = AccountSelector(config_frame, self._save_workflow)
        self.account_selector.pack(side="left", fill="both", expand=True)

        # Workflow list section (bottom section)
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(pady=(0, self.padding), padx=self.padding, fill="both", expand=True)

        # Automation control (header for workflow list)
        control_frame = ctk.CTkFrame(list_frame)
        control_frame.pack(pady=(0, self.padding // 2), fill="x")

        ctk.CTkLabel(control_frame, text="Run Interval (seconds):").pack(
            side="left", padx=(0, self.padding // 2)
        )
        self.interval_entry = ctk.CTkEntry(control_frame, width=80)
        self.interval_entry.pack(side="left", padx=(0, self.padding // 2))
        self.interval_entry.insert(0, "60")

        self.randomize_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            control_frame, text="Randomize", variable=self.randomize_var
        ).pack(side="left", padx=(0, self.padding))

        self.start_btn = ctk.CTkButton(
            control_frame, text="Start Automation", command=self._start_automation
        )
        self.start_btn.pack(side="left", padx=(0, self.padding // 2))

        self.stop_btn = ctk.CTkButton(
            control_frame, text="Stop", command=self._stop_automation, state="disabled"
        )
        self.stop_btn.pack(side="left")

        # Workflow list
        ctk.CTkLabel(
            list_frame, text="Saved Workflows", font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=self.padding, pady=(0, self.padding // 2))

        self.workflow_list = WorkflowList(list_frame)

    def refresh(self):
        """Refresh the view's content."""
        try:
            if "account" in self.controllers:
                accounts = self.controllers["account"].get_all_accounts()
                self.account_selector.set_accounts(accounts)

            if "automation" in self.controllers:
                workflows = self.controllers["automation"].get_all_workflows()
                if workflows:
                    for name in workflows:
                        self.workflow_list.add_workflow(name)
        except Exception as e:
            logger.error(f"Error refreshing automation view: {str(e)}")

    def _save_workflow(self):
        
        workflow_name = self.account_selector.workflow_name_entry.get().strip()
        if not workflow_name:
            messagebox.showwarning("Input Error", "Please provide a workflow name.")
            return

        actions = self.action_config.get_selected_actions()
        if not actions:
            messagebox.showwarning("Input Error", "Please select at least one action.")
            return

        accounts = self.account_selector.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("Input Error", "Please select at least one account.")
            return

        success = self.controllers["automation"].save_workflow(
            workflow_name, actions, accounts
        )

        if success:
            self.workflow_list.add_workflow(workflow_name)
            self.account_selector.workflow_name_entry.delete(0, tk.END)
            self.action_config.reset()
            messagebox.showinfo(
                "Success", f"Workflow '{workflow_name}' saved successfully."
            )
        else:
            messagebox.showerror("Error", f"Failed to save workflow '{workflow_name}'.")

    def _start_automation(self):
        
        selected_workflows = self.workflow_list.get_selected()
        if not selected_workflows:
            messagebox.showwarning(
                "Warning", "Please select at least one workflow to run."
            )
            return

        try:
            interval = int(self.interval_entry.get())
            if interval < 1:
                raise ValueError("Interval must be at least 1 second.")
        except ValueError as e:
            messagebox.showwarning("Input Error", f"Invalid interval: {str(e)}")
            return

        randomize = self.randomize_var.get()
        success = self.controllers["automation"].start_automation(
            selected_workflows, interval, randomize
        )

        if success:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            logger.info(f"Started automation with {len(selected_workflows)} workflows.")

    def _stop_automation(self):
        
        if self.controllers["automation"].stop_automation():
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def update_workflow_progress(self, workflow_name: str, progress: float):
        
        self.workflow_list.update_progress(workflow_name, progress)
        if progress < 1.0:
            status = f"Running ({int(progress * 100)}%)"
        else:
            status = "Complete"
        self.workflow_list.update_status(workflow_name, status)