import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional





@dataclass
class WorkflowData:
    """Data class to store workflow configurations."""
    actions: Dict[str, dict]
    accounts: List[str]





class UIComponent(ctk.CTkFrame):
    """Base class for UI components with consistent padding."""
    def __init__(self, parent, padding: int = 16):
        super().__init__(parent)
        self.padding = padding





class ActionConfig(UIComponent):
    """Configuration panel for selecting and configuring actions."""
    ACTION_TYPES = ["Comments", "Posts", "Live Views", "Likes", "Shares"]

    def __init__(self, parent, log: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.log = log
        self.action_vars = {}
        self.action_inputs = {}
        self.pack(side="left", padx=(0, padding), fill="y")
        self._setup_checkboxes()

    def _setup_checkboxes(self):
        """Create checkboxes for each action type."""
        for action in self.ACTION_TYPES:
            var = ctk.BooleanVar()
            ctk.CTkCheckBox(
                self, 
                text=action, 
                variable=var, 
                command=lambda a=action: self._toggle_input(a)
            ).pack(pady=self.padding // 2, anchor="w")
            self.action_vars[action] = var

    def _toggle_input(self, action: str):
        """Toggle visibility of input fields for selected actions."""
        if action not in self.action_inputs:
            self.action_inputs[action] = self._create_input_frame(action)
        
        frame = self.action_inputs[action]
        if self.action_vars[action].get():
            frame.pack(pady=self.padding // 2, fill="x")
        else:
            frame.pack_forget()

    def _create_input_frame(self, action: str) -> ctk.CTkFrame:
        """Create dynamic input frames for different action types."""
        frame = ctk.CTkFrame(self)
        
        input_configs = {
            "Comments": {
                "label": "Post Link:",
                "width": 150,
                "extras": [("Load Comments (.txt)", self._load_comments_file)]
            },
            "Live Views": {"label": "Views Link:", "width": 200},
            "Likes": {"label": "Likes Link:", "width": 200},
            "Shares": {"label": "Shares Link:", "width": 200},
            "Posts": {"label": "Post Content:", "width": 200, "entry_name": "content_entry"}
        }
        
        config = input_configs[action]
        ctk.CTkLabel(frame, text=config["label"]).pack(side="left")
        
        entry_name = config.get("entry_name", "link_entry")
        frame.__dict__[entry_name] = ctk.CTkEntry(frame, width=config["width"])
        frame.__dict__[entry_name].pack(side="left", padx=5)
        
        if "extras" in config:
            for text, command in config["extras"]:
                ctk.CTkButton(frame, text=text, command=lambda a=action, cmd=command: cmd(a)).pack(side="left")
        
        return frame

    def _load_comments_file(self, action: str):
        """Load comments file for comments action."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.action_inputs[action].comments_file = file_path
            self.log(f"Loaded comments file for {action}: {file_path}")

    def get_selected_actions(self) -> Dict[str, dict]:
        """Retrieve selected actions with their configuration."""
        actions = {}
        for action, var in self.action_vars.items():
            if var.get() and action in self.action_inputs:
                frame = self.action_inputs[action]
                actions[action] = self._get_action_details(action, frame)
        return actions

    def _get_action_details(self, action: str, frame: ctk.CTkFrame) -> dict:
        """Extract action details based on action type."""
        if action == "Comments":
            return {
                "link": frame.link_entry.get(), 
                "comments_file": getattr(frame, "comments_file", None)
            }
        elif action in ["Live Views", "Likes", "Shares"]:
            return {"link": frame.link_entry.get()}
        elif action == "Posts":
            return {"content": frame.content_entry.get()}

    def reset(self):
        """Reset all action configurations."""
        for var in self.action_vars.values():
            var.set(False)
        for frame in self.action_inputs.values():
            frame.pack_forget()





class AccountSelector(UIComponent):
    """UI component for selecting accounts."""
    def __init__(self, parent, accounts: Dict[str, dict], log: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.accounts = accounts
        self.log = log
        self._setup_ui()

    def _setup_ui(self):
        """Set up the account selection user interface."""
        ctk.CTkLabel(self, text="Select Accounts:").pack(anchor="w")
        
        listbox_frame = ctk.CTkFrame(self)
        listbox_frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(
            listbox_frame, 
            height=10, 
            width=30, 
            selectmode=tk.MULTIPLE, 
            font=("Segoe UI", 12)
        )
        
        self.scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="left", fill="y")

        select_frame = ctk.CTkFrame(self)
        select_frame.pack(pady=self.padding // 2, fill="x")
        
        ctk.CTkLabel(select_frame, text="Select IDs (e.g., 001-005):").pack(side="left")
        self.select_entry = ctk.CTkEntry(select_frame, width=100)
        self.select_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(select_frame, text="Select Range", command=self._select_range).pack(side="left")

    def refresh(self):
        """Refresh the list of accounts."""
        self.listbox.delete(0, tk.END)
        for account in self.accounts.values():
            self.listbox.insert(tk.END, f"{account['id']} - {account['email']}")
        self.log(f"Refreshed accounts: {self.listbox.size()} items")

    def get_selected_accounts(self) -> List[str]:
        """Get the emails of selected accounts."""
        return [list(self.accounts.values())[i]["email"] for i in self.listbox.curselection()]

    def _select_range(self):
        """Select accounts within a specified ID range."""
        try:
            start, end = map(int, self.select_entry.get().strip().split("-"))
            self.listbox.selection_clear(0, tk.END)
            
            selected = False
            for i, account in enumerate(self.accounts.values()):
                if start <= int(account["id"]) <= end:
                    self.listbox.selection_set(i)
                    selected = True
            
            if selected:
                self.log(f"Selected accounts in range {start}-{end}")
            else:
                messagebox.showinfo("No Matches", "No accounts in range.")
        
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid range format (e.g., 001-005).")





class WorkflowSaver(UIComponent):
    """UI component for saving workflows."""
    def __init__(self, parent, save_command: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.save_command = save_command
        
        self.entry = ctk.CTkEntry(self, placeholder_text="Workflow Name", width=200)
        self.entry.pack(pady=(0, padding // 2))
        
        ctk.CTkButton(self, text="Save Workflow", command=self._save).pack()

    def _save(self):
        """Save the workflow with the provided name."""
        name = self.entry.get().strip()
        
        if name:
            self.save_command(name)
            self.entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Input Error", "Please provide a workflow name.")





class WorkflowList(ctk.CTkScrollableFrame):
    """Scrollable list of workflows with status and progress tracking."""
    def __init__(self, parent, workflows: Dict[str, WorkflowData], log: Callable[[str], None], padding: int = 16):
        self.min_height, self.max_height, self.row_height = 50, 150, 35
        super().__init__(parent, height=self.min_height)
        
        self.workflows = workflows
        self.log = log
        self.padding = padding
        self.widgets = {}
        
        self.pack(pady=padding, padx=padding, fill="x")

    def add_workflow(self, name: str):
        """Add a new workflow to the list."""
        if name in self.widgets:
            return
        
        frame = ctk.CTkFrame(self)
        frame.pack(pady=5, fill="x")
        
        select_var = ctk.BooleanVar()
        ctk.CTkCheckBox(frame, text="", variable=select_var, width=20).pack(side="left")
        
        label = ctk.CTkLabel(
            frame, 
            text=f"{name} ({len(self.workflows[name].actions)} actions, {len(self.workflows[name].accounts)} accounts)"
        )
        label.pack(side="left", padx=(0, self.padding))
        
        status = ctk.CTkLabel(frame, text="Idle")
        status.pack(side="left", padx=(0, self.padding))
        
        progress = ctk.CTkProgressBar(frame, width=100)
        progress.set(0)
        progress.pack(side="left")
        
        ctk.CTkButton(
            frame, 
            text="Delete", 
            width=60, 
            command=lambda n=name: self._delete(n)
        ).pack(side="right", padx=(self.padding, 0))
        
        self.widgets[name] = {
            "frame": frame, 
            "select_var": select_var, 
            "status": status, 
            "progress": progress
        }
        
        self._update_height()

    def _delete(self, name: str):
        """Delete a workflow from the list."""
        self.widgets[name]["frame"].destroy()
        del self.widgets[name]
        del self.workflows[name]
        self.log(f"Deleted workflow '{name}'")
        self._update_height()

    def _update_height(self):
        """Dynamically update the frame height based on workflow count."""
        height = max(
            self.min_height, 
            min(self.min_height + len(self.widgets) * self.row_height, self.max_height)
        )
        self.configure(height=height)

    def get_selected(self) -> List[str]:
        """Get names of selected workflows."""
        return [name for name, w in self.widgets.items() if w["select_var"].get()]

    def update_status(self, name: str, status: str):
        """Update the status of a specific workflow."""
        if name in self.widgets:
            self.widgets[name]["status"].configure(text=status)

    def update_progress(self, name: str, value: float):
        """Update the progress of a specific workflow."""
        if name in self.widgets:
            self.widgets[name]["progress"].set(value)

    def reset(self):
        """Reset all workflow statuses and progress."""
        for w in self.widgets.values():
            w["status"].configure(text="Idle")
            w["progress"].set(0)





class AutomationRunner:
    """Manages the execution of selected workflows."""
    def __init__(self, workflows: Dict[str, WorkflowData], log: Callable[[str], None], workflow_list: WorkflowList):
        self.workflows = workflows
        self.log = log
        self.workflow_list = workflow_list
        self.running = False

    def start(self, interval: str, randomize: bool):
        """Start the automation process."""
        if not self._can_start():
            return
        
        self.running = True
        threading.Thread(target=self._run, args=(interval, randomize), daemon=True).start()

    def _can_start(self) -> bool:
        """Check if automation can be started."""
        selected = self.workflow_list.get_selected()
        if not selected:
            messagebox.showwarning("No Workflows Selected", "Select at least one workflow.")
            return False
        return True

    def stop(self):
        """Stop the ongoing automation."""
        self.running = False
        self.workflow_list.reset()

    def _run(self, interval: str, randomize: bool):
        """Core method to run selected workflows."""
        self._process_selected()
        if self.running:
            self.workflow_list.reset()
            self.master._on_complete()

    def _process_selected(self):
        """Process workflows selected for automation."""
        for name in self.workflow_list.get_selected():
            if not self.running or name not in self.workflows:
                continue
            self._execute_workflow(name, self.workflows[name])

    def _execute_workflow(self, name: str, data: WorkflowData):
        """Execute a single workflow."""
        self.workflow_list.update_status(name, "Running")
        
        total_steps = len(data.accounts) * len(data.actions)
        step = 0
        
        for email in data.accounts:
            if not self.running:
                return
            
            for action, details in data.actions.items():
                self.log(f"Performing {action} with {email} (Workflow: {name}, Details: {details})")
                step += 1
                self.workflow_list.update_progress(name, step / total_steps)
                time.sleep(0.1)
        
        self.workflow_list.update_status(name, "Completed")





class AutomationSection(ctk.CTkFrame):
    """Main automation section combining all components."""
    def __init__(self, parent, accounts: Dict[str, dict], workflows: Dict[str, WorkflowData], log: Callable[[str], None]):
        super().__init__(parent)
        
        self.accounts = accounts
        self.workflows = workflows
        self.log = log
        self.padding = 16
        
        self.runner = AutomationRunner(workflows, log, None)
        self._setup_ui()
        
        self.runner.workflow_list = self.workflow_list
        self.runner.master = self

    def _setup_ui(self):
        """Set up the complete user interface for automation."""
        ctk.CTkLabel(
            self, 
            text="Automation Control", 
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

        config_frame = ctk.CTkFrame(self)
        config_frame.pack(pady=self.padding, padx=self.padding, fill="both", expand=False)
        config_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.actions = ActionConfig(config_frame, self.log)
        self.actions.grid(row=0, column=0, sticky="ns", padx=(0, self.padding))

        self.accounts_selector = AccountSelector(config_frame, self.accounts, self.log)
        self.accounts_selector.grid(row=0, column=1, sticky="nsew")

        self.saver = WorkflowSaver(config_frame, self._save_workflow)
        self.saver.grid(row=0, column=2, sticky="ns", padx=(0, self.padding))

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=(0, self.padding), padx=self.padding, fill="x")
        
        ctk.CTkLabel(button_frame, text="Interval (min):").pack(side="left")
        
        self.interval_entry = ctk.CTkEntry(button_frame, width=100)
        self.interval_entry.pack(side="left", padx=self.padding // 2)
        
        self.randomize_var = ctk.BooleanVar()
        ctk.CTkCheckBox(button_frame, text="Randomize", variable=self.randomize_var).pack(side="left")
        
        self.run_btn = ctk.CTkButton(button_frame, text="Run Selected", command=self._start)
        self.run_btn.pack(side="left", padx=(self.padding, self.padding // 2), pady=self.padding)
        
        self.stop_btn = ctk.CTkButton(button_frame, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", pady=self.padding)

        self.workflow_list = WorkflowList(self, self.workflows, self.log)

    def refresh_accounts(self):
        """Refresh the list of accounts."""
        self.accounts_selector.refresh()

    def _save_workflow(self, name: str):
        """Save a new workflow."""
        if name in self.workflows:
            messagebox.showwarning("Duplicate Error", f"Workflow '{name}' already exists.")
            return
        
        self.workflows[name] = WorkflowData(
            self.actions.get_selected_actions(), 
            self.accounts_selector.get_selected_accounts()
        )
        
        self.log(f"Saved workflow '{name}'")
        self.workflow_list.add_workflow(name)
        self.actions.reset()

    def _start(self):
        """Start the automation process."""
        if not self.accounts:
            messagebox.showwarning("No Accounts", "Please add accounts first.")
            return
        
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.runner.start(self.interval_entry.get(), self.randomize_var.get())

    def _stop(self):
        """Stop the ongoing automation."""
        self.runner.stop()
        self._on_complete()

    def _on_complete(self):
        """Handle automation completion."""
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")