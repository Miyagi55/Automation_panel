import tkinter as tk
from tkinter import ttk, messagebox

def edit_row():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a row to edit")
        return
    
    # Get the selected row's values
    item = tree.item(selected[0])
    values = item["values"]
    
    # Create an edit window
    edit_win = tk.Toplevel(root)
    edit_win.title("Edit Row")
    
    # Labels and entry fields
    tk.Label(edit_win, text="ID").grid(row=0, column=0, padx=5, pady=5)
    id_entry = tk.Entry(edit_win)
    id_entry.grid(row=0, column=1, padx=5, pady=5)
    id_entry.insert(0, values[0])
    
    tk.Label(edit_win, text="Name").grid(row=1, column=0, padx=5, pady=5)
    name_entry = tk.Entry(edit_win)
    name_entry.grid(row=1, column=1, padx=5, pady=5)
    name_entry.insert(0, values[1])
    
    tk.Label(edit_win, text="Age").grid(row=2, column=0, padx=5, pady=5)
    age_entry = tk.Entry(edit_win)
    age_entry.grid(row=2, column=1, padx=5, pady=5)
    age_entry.insert(0, values[2])
    
    def save_changes():
        new_values = (id_entry.get(), name_entry.get(), age_entry.get())
        tree.item(selected[0], values=new_values)
        edit_win.destroy()
    
    tk.Button(edit_win, text="Save", command=save_changes).grid(row=3, column=0, columnspan=2, pady=10)

def delete_row():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a row to delete")
        return
    if messagebox.askyesno("Confirm", "Are you sure you want to delete this row?"):
        tree.delete(selected[0])

# Create main window
root = tk.Tk()
root.title("Editable Table")

# Create Treeview
tree = ttk.Treeview(root, columns=("ID", "Name", "Age"), show="headings", height=5)
tree.pack(pady=10)

# Define column headings
tree.heading("ID", text="ID")
tree.heading("Name", text="Name")
tree.heading("Age", text="Age")

# Set column widths
tree.column("ID", width=50)
tree.column("Name", width=100)
tree.column("Age", width=50)

# Add initial data
data = [
    (1, "Alice", 25),
    (2, "Bob", 30),
    (3, "Charlie", 35)
]
for row in data:
    tree.insert("", tk.END, values=row)

# Buttons for editing and deleting
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Edit", command=edit_row).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Delete", command=delete_row).pack(side=tk.LEFT, padx=5)

root.mainloop()