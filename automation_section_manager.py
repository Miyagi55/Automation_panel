import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional

@dataclass
class WorkflowData:
    actions: Dict[str, dict]
    accounts: List[str]



class UIComponent(ctk.CTkFrame):
    """Base class for reusable UI components."""
    def __init__(self, parent, padding: int = 16):
        super().__init__(parent)
        self.padding = padding



class ActionConfig(UIComponent):
    """Manages action selection and inputs."""
    def __init__(self, parent, log: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.log = log
        self.action_vars = {}
        self.action_inputs = {}
        self.pack(side="left", padx=(0, padding), fill="y")
        self._setup_checkboxes()

    def _setup_checkboxes(self):
        for action in ["Comments", "Posts", "Live Views", "Likes", "Shares"]:
            var = ctk.BooleanVar()
            ctk.CTkCheckBox(self, text=action, variable=var, command=lambda a=action: self._toggle_input(a)).pack(pady=self.padding // 2, anchor="w")
            self.action_vars[action] = var

    def _toggle_input(self, action: str):
        if action in self.action_inputs:
            self.action_inputs[action].pack(pady=self.padding // 2, fill="x") if self.action_vars[action].get() else self.action_inputs[action].pack_forget()
        elif self.action_vars[action].get():
            self.action_inputs[action] = self._create_input_frame(action)
            self.action_inputs[action].pack(pady=self.padding // 2, fill="x")

    def _create_input_frame(self, action: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self)
        if action == "Comments":
            ctk.CTkLabel(frame, text="Post Link:").pack(side="left")
            frame.link_entry = ctk.CTkEntry(frame, width=150)
            frame.link_entry.pack(side="left", padx=5)
            ctk.CTkButton(frame, text="Load Comments (.txt)", command=lambda: self._load_comments_file(action)).pack(side="left")
            frame.comments_file = None
        elif action in ["Live Views", "Likes", "Shares"]:
            ctk.CTkLabel(frame, text=f"{action} Link:").pack(side="left")
            frame.link_entry = ctk.CTkEntry(frame, width=200)
            frame.link_entry.pack(side="left", padx=5)
        elif action == "Posts":
            ctk.CTkLabel(frame, text="Post Content:").pack(side="left")
            frame.content_entry = ctk.CTkEntry(frame, width=200)
            frame.content_entry.pack(side="left", padx=5)
        return frame

    def _load_comments_file(self, action: str):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.action_inputs[action].comments_file = file_path
            self.log(f"Loaded comments file for {action}: {file_path}")

    def get_selected_actions(self) -> Dict[str, dict]:
        actions = {}
        for action, var in self.action_vars.items():
            if var.get() and action in self.action_inputs:
                frame = self.action_inputs[action]
                if action == "Comments":
                    actions[action] = {"link": frame.link_entry.get(), "comments_file": getattr(frame, "comments_file", None)}
                elif action in ["Live Views", "Likes", "Shares"]:
                    actions[action] = {"link": frame.link_entry.get()}
                elif action == "Posts":
                    actions[action] = {"content": frame.content_entry.get()}
        return actions

    def reset(self):
        for var in self.action_vars.values():
            var.set(False)
        for frame in self.action_inputs.values():
            frame.pack_forget()




class AccountSelector(UIComponent):
    """Manages account selection."""
    def __init__(self, parent, accounts: Dict[str, dict], log: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.accounts = accounts
        self.log = log
        self._setup_ui()

    def _setup_ui(self):
        ctk.CTkLabel(self, text="Select Accounts:").pack(anchor="w")
        listbox_frame = ctk.CTkFrame(self)
        listbox_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.MULTIPLE, font=("Segoe UI", 12))
        self.scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)  # Store scrollbar
        self.listbox.config(yscrollcommand=self.scrollbar.set)  # Bind to instance's set method
        self.listbox.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="left", fill="y")

        select_frame = ctk.CTkFrame(self)
        select_frame.pack(pady=self.padding // 2, fill="x")
        ctk.CTkLabel(select_frame, text="Select IDs (e.g., 001-005):").pack(side="left")
        self.select_entry = ctk.CTkEntry(select_frame, width=100)
        self.select_entry.pack(side="left", padx=5)
        ctk.CTkButton(select_frame, text="Select Range", command=self._select_range).pack(side="left")

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for account in self.accounts.values():
            self.listbox.insert(tk.END, f"{account['id']} - {account['email']}")
        self.log(f"Refreshed accounts: {self.listbox.size()} items")

    def get_selected_accounts(self) -> List[str]:
        return [list(self.accounts.values())[i]["email"] for i in self.listbox.curselection()]

    def _select_range(self):
        try:
            start, end = map(int, self.select_entry.get().strip().split("-"))
            self.listbox.selection_clear(0, tk.END)
            selected = False
            for i, account in enumerate(self.accounts.values()):
                if start <= int(account["id"]) <= end:
                    self.listbox.selection_set(i)
                    selected = True
            self.log(f"Selected accounts in range {start}-{end}") if selected else messagebox.showinfo("No Matches", "No accounts in range.")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid range format (e.g., 001-005).")




class WorkflowSaver(UIComponent):
    """Handles workflow saving."""
    def __init__(self, parent, save_command: Callable[[str], None], padding: int = 16):
        super().__init__(parent, padding)
        self.save_command = save_command
        self.entry = ctk.CTkEntry(self, placeholder_text="Workflow Name", width=200)
        self.entry.pack(pady=(0, padding // 2))
        ctk.CTkButton(self, text="Save Workflow", command=self._save).pack()

    def _save(self):
        name = self.entry.get().strip()
        if name:
            self.save_command(name)
            self.entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Input Error", "Please provide a workflow name.")





class WorkflowList(ctk.CTkScrollableFrame):
    """Manages workflow display and selection."""
    def __init__(self, parent, workflows: Dict[str, WorkflowData], log: Callable[[str], None], padding: int = 16):
        self.min_height, self.max_height, self.row_height = 50, 150, 35
        super().__init__(parent, height=self.min_height)
        self.workflows = workflows
        self.log = log
        self.padding = padding
        self.widgets = {}
        self.pack(pady=padding, padx=padding, fill="x")

    def add_workflow(self, name: str):
        if name in self.widgets:
            return
        frame = ctk.CTkFrame(self)
        frame.pack(pady=5, fill="x")
        select_var = ctk.BooleanVar()
        ctk.CTkCheckBox(frame, text="", variable=select_var, width=20).pack(side="left")
        label = ctk.CTkLabel(frame, text=f"{name} ({len(self.workflows[name].actions)} actions, {len(self.workflows[name].accounts)} accounts)")
        label.pack(side="left", padx=(0, self.padding))
        status = ctk.CTkLabel(frame, text="Idle")
        status.pack(side="left", padx=(0, self.padding))
        progress = ctk.CTkProgressBar(frame, width=100)
        progress.set(0)
        progress.pack(side="left")
        ctk.CTkButton(frame, text="Delete", width=60, command=lambda n=name: self._delete(n)).pack(side="right", padx=(self.padding, 0))
        self.widgets[name] = {"frame": frame, "select_var": select_var, "status": status, "progress": progress}
        self._update_height()

    def _delete(self, name: str):
        self.widgets[name]["frame"].destroy()
        del self.widgets[name]
        del self.workflows[name]
        self.log(f"Deleted workflow '{name}'")
        self._update_height()

    def _update_height(self):
        height = max(self.min_height, min(self.min_height + len(self.widgets) * self.row_height, self.max_height))
        self.configure(height=height)

    def get_selected(self) -> List[str]:
        return [name for name, w in self.widgets.items() if w["select_var"].get()]

    def update_status(self, name: str, status: str):
        if name in self.widgets:
            self.widgets[name]["status"].configure(text=status)

    def update_progress(self, name: str, value: float):
        if name in self.widgets:
            self.widgets[name]["progress"].set(value)

    def reset(self):
        for w in self.widgets.values():
            w["status"].configure(text="Idle")
            w["progress"].set(0)




class AutomationRunner:
    """Handles workflow execution (sync now, async-ready)."""
    def __init__(self, workflows: Dict[str, WorkflowData], log: Callable[[str], None], workflow_list: WorkflowList):
        self.workflows = workflows
        self.log = log
        self.workflow_list = workflow_list
        self.running = False

    def start(self, interval: str, randomize: bool):
        if not self._can_start():
            return
        self.running = True
        threading.Thread(target=self._run, args=(interval, randomize), daemon=True).start()

    def _can_start(self) -> bool:
        selected = self.workflow_list.get_selected()
        if not selected:
            messagebox.showwarning("No Workflows Selected", "Select at least one workflow.")
            return False
        return True

    def stop(self):
        self.running = False
        self.workflow_list.reset()

    def _run(self, interval: str, randomize: bool):
        self._process_selected()
        if self.running:
            self.workflow_list.reset()
            self.master._on_complete()

    def _process_selected(self):
        for name in self.workflow_list.get_selected():
            if not self.running or name not in self.workflows:
                continue
            self._execute_workflow(name, self.workflows[name])

    def _execute_workflow(self, name: str, data: WorkflowData):
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
    """Main automation panel."""
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
        ctk.CTkLabel(self, text="Automation Control", font=("Segoe UI", 16, "bold")).pack(pady=(self.padding, 0), padx=self.padding, anchor="w")

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
        self.accounts_selector.refresh()

    def _save_workflow(self, name: str):
        if name in self.workflows:
            messagebox.showwarning("Duplicate Error", f"Workflow '{name}' already exists.")
            return
        self.workflows[name] = WorkflowData(self.actions.get_selected_actions(), self.accounts_selector.get_selected_accounts())
        self.log(f"Saved workflow '{name}'")
        self.workflow_list.add_workflow(name)
        self.actions.reset()

    def _start(self):
        if not self.accounts:
            messagebox.showwarning("No Accounts", "Please add accounts first.")
            return
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.runner.start(self.interval_entry.get(), self.randomize_var.get())

    def _stop(self):
        self.runner.stop()
        self._on_complete()

    def _on_complete(self):
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")