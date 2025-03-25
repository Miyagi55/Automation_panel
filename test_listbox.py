import customtkinter as ctk

# Set the appearance mode and default color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Create the main window
app = ctk.CTk()
app.geometry("300x300")
app.title("Multi-Select Preconfiguration")

# List of preconfiguration options
options = ["Feature A", "Feature B", "Feature C", "Feature D"]

# Dictionary to store checkbox states
checkbox_vars = {}

# Function to display selected options
def update_selection():
    selected = [opt for opt, var in checkbox_vars.items() if var.get() == 1]
    label.configure(text="Selected: " + ", ".join(selected) if selected else "Selected: None")
    print("Selected options:", selected)

# Create a frame for checkboxes
frame = ctk.CTkFrame(master=app)
frame.pack(pady=20, padx=20, fill="both", expand=True)

# Add checkboxes for each option
for option in options:
    var = ctk.IntVar(value=0)  # 0 = unchecked, 1 = checked
    checkbox = ctk.CTkCheckBox(
        master=frame,
        text=option,
        variable=var,
        command=update_selection
    )
    checkbox.pack(pady=5, padx=10, anchor="w")
    checkbox_vars[option] = var

# Label to display selected options
label = ctk.CTkLabel(master=app, text="Selected: None", font=("Arial", 14))
label.pack(pady=10)

# Run the application
app.mainloop()