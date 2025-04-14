import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import MainV9
import threading

def run_search():
    """Convert user input into a list of keywords and run MainV9.main."""
    user_input = text_box.get("1.0", tk.END).strip()  # Get text from the text box
    if not user_input:
        messagebox.showerror("Error", "Please enter at least one keyword.")
        return

    # Convert user input into a list of keywords
    keywords = [keyword.strip() for keyword in user_input.split("\n") if keyword.strip()]
    if not keywords:
        messagebox.showerror("Error", "Please enter valid keywords.")
        return

    # Disable the search button
    search_button.config(state=tk.DISABLED)

    # Clear the output box
    output_box.delete("1.0", tk.END)

    # Function to send messages to the output box
    def print_to_interface(message):
        output_box.insert(tk.END, message + "\n")
        output_box.see(tk.END)  # Auto-scroll to the bottom

    # Run the search in a separate thread to keep the GUI responsive
    def search():
        try:
            # Pass the entire list of keywords and the print_to_interface callback to MainV9.main
            MainV9.main(keywords, print_to_interface)
            messagebox.showinfo("Success", "Search completed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # Re-enable the search button
            search_button.config(state=tk.NORMAL)

    threading.Thread(target=search).start()

# Create the GUI window
root = tk.Tk()
root.title("University Course Search")
root.geometry("600x500")  # Set the window size

# Add a label
label = tk.Label(root, text="Enter keywords (one per line):", font=("Arial", 12))
label.pack(pady=10)

# Add a text box for user input and pre-fill it with the keywords
text_box = tk.Text(root, height=10, width=50, font=("Arial", 10))
text_box.pack(pady=10)

# Pre-fill the text box with the specified keywords
pre_filled_keywords = """Cognitive
generative
large language model
Cyber
genAI
llm
deep learning
Artificial Intelligence
artificial intelligence
Neural Network
Deep Learning
AI Ethics
Machine Learning
Computer Vision
Natural Language Processing
Reinforcement Learning
AI Safety
Generative Models
Artificial General Intelligence"""
text_box.insert("1.0", pre_filled_keywords)

# Add a "Search" button
search_button = tk.Button(root, text="Search", command=run_search, font=("Arial", 12), bg="blue", fg="white")
search_button.pack(pady=10)

# Add an output box to display messages
output_box = tk.Text(root, height=10, width=70, font=("Arial", 10), state=tk.NORMAL)
output_box.pack(pady=10)

# Run the GUI event loop
root.mainloop()