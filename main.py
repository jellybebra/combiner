import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import re
import json
import threading
import queue

CONFIG_FILE = "text_combiner_settings.json"

class TextCombinerApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Text File Combiner")
        try:
            # Make it a bit larger for better layout
            self.root.geometry("600x350")
        except tk.TclError:
            pass # Some environments might restrict this

        self.input_folder_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.exclude_files_regex_var = tk.StringVar()
        self.exclude_folders_regex_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.status_var.set("Ready.")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = None # Will be created later if ttk is available

        # --- UI Elements ---
        frame = ttk.Frame(self.root, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # Input Folder
        ttk.Label(frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.input_folder_var, width=50).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Browse...", command=self.browse_input_folder).grid(row=0, column=2, sticky=tk.EW, pady=2)

        # Output File
        ttk.Label(frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.output_file_var, width=50).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Save As...", command=self.browse_output_file).grid(row=1, column=2, sticky=tk.EW, pady=2)

        # Exclude Files Regex
        ttk.Label(frame, text="Exclude Files (Regex):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.exclude_files_regex_var, width=50).grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        # Exclude Folders Regex
        ttk.Label(frame, text="Exclude Folders (Regex):").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.exclude_folders_regex_var, width=50).grid(row=3, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        # Combine Button
        self.combine_button = ttk.Button(frame, text="Combine Files", command=self.start_combination_thread)
        self.combine_button.grid(row=4, column=0, columnspan=3, pady=10)

        # Progress Bar
        try:
            self.progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=100, mode='determinate', variable=self.progress_var)
            self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=5)
        except tk.TclError: # ttk.Progressbar might not be available on very old tk
            self.progress_bar = None
            ttk.Label(frame, text="Progress bar not available on this system.").grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=5)


        # Status Label
        ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)

        frame.columnconfigure(1, weight=1) # Make entry fields expandable

        self.load_settings()
        self.msg_queue = queue.Queue()
        self.check_queue() # Start checking the queue for messages

    def check_queue(self):
        """ Check for messages from worker thread and update GUI. """
        try:
            while True:
                message_type, data = self.msg_queue.get_nowait()
                if message_type == "status":
                    self.status_var.set(data)
                elif message_type == "progress_max":
                    if self.progress_bar:
                        self.progress_bar.config(maximum=data)
                        self.progress_var.set(0)
                elif message_type == "progress_update":
                    if self.progress_bar:
                        self.progress_var.set(data)
                elif message_type == "done":
                    self.status_var.set(data)
                    self.combine_button.config(state=tk.NORMAL)
                    if self.progress_bar:
                        self.progress_var.set(self.progress_bar['maximum']) # Fill bar on completion
                elif message_type == "error":
                    messagebox.showerror("Error", data)
                    self.status_var.set(f"Error: {data}")
                    self.combine_button.config(state=tk.NORMAL)
                    if self.progress_bar:
                        self.progress_var.set(0)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)


    def load_settings(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                settings = json.load(f)
                self.exclude_files_regex_var.set(settings.get("exclude_files_regex", ""))
                self.exclude_folders_regex_var.set(settings.get("exclude_folders_regex", ""))
                # Optionally, load last used paths, but be careful if they no longer exist
                # self.input_folder_var.set(settings.get("last_input_folder", ""))
                # self.output_file_var.set(settings.get("last_output_file", ""))
                self.status_var.set("Settings loaded.")
        except FileNotFoundError:
            self.status_var.set("No settings file found. Using defaults.")
        except json.JSONDecodeError:
            self.status_var.set("Error reading settings file. Using defaults.")
        except Exception as e:
            self.status_var.set(f"Error loading settings: {e}")


    def save_settings(self):
        settings = {
            "exclude_files_regex": self.exclude_files_regex_var.get(),
            "exclude_folders_regex": self.exclude_folders_regex_var.get(),
            # "last_input_folder": self.input_folder_var.get(), # Optional
            # "last_output_file": self.output_file_var.get()   # Optional
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            # Don't overwrite "Ready." or other important status with "Settings saved."
            # self.status_var.set("Settings saved.")
        except Exception as e:
            self.status_var.set(f"Error saving settings: {e}")
            messagebox.showerror("Settings Error", f"Could not save settings: {e}")

    def browse_input_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_folder_var.set(folder_selected)

    def browse_output_file(self):
        file_selected = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_selected:
            self.output_file_var.set(file_selected)

    def start_combination_thread(self):
        input_folder = self.input_folder_var.get()
        output_file = self.output_file_var.get()
        exclude_files_regex_str = self.exclude_files_regex_var.get()
        exclude_folders_regex_str = self.exclude_folders_regex_var.get()

        if not input_folder or not os.path.isdir(input_folder):
            messagebox.showerror("Error", "Please select a valid input folder.")
            return
        if not output_file:
            messagebox.showerror("Error", "Please specify an output file.")
            return

        # Prevent writing output file into itself if it's in the input folder and not excluded
        abs_output_file = os.path.abspath(output_file)
        abs_input_folder = os.path.abspath(input_folder)
        if abs_output_file.startswith(abs_input_folder + os.sep):
            # Check if the output file itself would be processed
            output_filename = os.path.basename(abs_output_file)
            try:
                file_regex = re.compile(exclude_files_regex_str) if exclude_files_regex_str else None
                if file_regex and file_regex.search(output_filename):
                    pass # It's excluded, fine
                elif not file_regex: # No file exclusion, so it would be included
                    # This is tricky. If output is in input path, and not excluded by file regex,
                    # and it's a text file, it might read itself.
                    # A simple solution is to warn or add a specific check in the worker.
                    # For now, we will add a direct check in the worker.
                    pass
            except re.error:
                # Invalid regex handled later, but for this check, assume it might not exclude
                pass


        self.save_settings() # Save current regex settings

        self.combine_button.config(state=tk.DISABLED)
        self.status_var.set("Starting combination...")
        if self.progress_bar:
            self.progress_var.set(0)
            self.progress_bar.config(maximum=100) # Placeholder, will be updated

        # Run the combination in a separate thread
        thread = threading.Thread(target=self.combine_files_worker,
                                  args=(input_folder, output_file, exclude_files_regex_str, exclude_folders_regex_str, abs_output_file),
                                  daemon=True)
        thread.start()

    def combine_files_worker(self, input_folder, output_file, exclude_files_regex_str, exclude_folders_regex_str, abs_output_file_path):
        try:
            file_re = re.compile(exclude_files_regex_str) if exclude_files_regex_str else None
        except re.error as e:
            self.msg_queue.put(("error", f"Invalid file exclusion regex: {e}"))
            return

        try:
            folder_re = re.compile(exclude_folders_regex_str) if exclude_folders_regex_str else None
        except re.error as e:
            self.msg_queue.put(("error", f"Invalid folder exclusion regex: {e}"))
            return

        files_to_process = []
        # First pass: collect all files to process and count them for progress bar
        for root, dirs, files in os.walk(input_folder, topdown=True):
            # Folder exclusion: modify dirs in-place to prevent os.walk from descending
            if folder_re:
                # Check full path of directory against regex
                # dirs[:] = [d for d in dirs if not folder_re.search(os.path.join(root, d))]
                # Or check just the directory name
                dirs[:] = [d for d in dirs if not folder_re.search(d)]

            # Also, if current root itself matches folder exclusion, skip its files (and subdirs already pruned)
            # This is for cases where input_folder itself might be excluded by regex (e.g. `.*/my_project_root`)
            # For simplicity, let's assume the regex applies to folder names, not full paths.
            # So the above `dirs[:]` modification is the main pruning mechanism.
            # If `os.path.basename(root)` matches `folder_re`, we technically shouldn't process files in it.
            # However, os.walk yields `input_folder` as the first `root`. If `input_folder` name
            # matches `folder_re`, `dirs[:]` would be cleared, but files in `input_folder` itself
            # would still be processed. This is a nuance.
            # A more robust folder exclusion:
            # current_folder_name = os.path.basename(root)
            # if folder_re and folder_re.search(current_folder_name):
            #    # And if it's not the initial input_folder itself (to allow processing files in input_folder even if its name matches)
            #    if os.path.abspath(root) != os.path.abspath(input_folder): 
            #       dirs[:] = [] # Prune subdirectories
            #       continue    # Skip files in this directory
            # This gets complex. The current `dirs[:] = [d for d in dirs if not folder_re.search(d)]` is simpler and
            # usually what users expect (exclude folders named X).

            for filename in files:
                if file_re and file_re.search(filename):
                    continue

                file_path = os.path.join(root, filename)
                abs_file_path = os.path.abspath(file_path)

                # Critical check: Do not read the output file itself if it's part of the input
                if abs_file_path == abs_output_file_path:
                    self.msg_queue.put(("status", f"Skipping output file itself: {filename}"))
                    continue

                files_to_process.append(abs_file_path)

        self.msg_queue.put(("progress_max", len(files_to_process)))

        count = 0
        processed_count = 0
        skipped_binary_count = 0

        try:
            with open(output_file, 'w', encoding='utf-8', errors='ignore') as outfile:
                for i, file_path in enumerate(files_to_process):
                    self.msg_queue.put(("status", f"Processing: {os.path.basename(file_path)}"))
                    self.msg_queue.put(("progress_update", i + 1))

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as infile:
                            # Using surrogateescape to handle potential lone surrogates if files aren't strictly UTF-8
                            # but are mostly text. Binary files will likely still fail or produce garbage.
                            # A more robust way for "is this text?" is to try decoding a small chunk.
                            # For now, we rely on the broad UnicodeDecodeError.

                            # Try reading a small chunk to detect binary files more proactively
                            try:
                                chunk = infile.read(1024) # Read 1KB
                                if '\0' in chunk: # Null byte typically indicates binary
                                    self.msg_queue.put(("status", f"Skipping likely binary file: {os.path.basename(file_path)}"))
                                    skipped_binary_count += 1
                                    continue
                                content = chunk + infile.read() # Read the rest
                            except UnicodeDecodeError:
                                self.msg_queue.put(("status", f"Skipping binary/non-UTF-8 file: {os.path.basename(file_path)}"))
                                skipped_binary_count += 1
                                continue

                            outfile.write(f"--- File: {file_path} ---\n\n")
                            outfile.write(content)
                            outfile.write("\n\n")
                            processed_count += 1
                    except UnicodeDecodeError: # This catch is a fallback
                        self.msg_queue.put(("status", f"Skipping binary/non-UTF-8 file (on full read): {os.path.basename(file_path)}"))
                        skipped_binary_count += 1
                    except IOError as e:
                        self.msg_queue.put(("status", f"Skipping unreadable file {os.path.basename(file_path)}: {e}"))
                        skipped_binary_count += 1
                    except Exception as e:
                        self.msg_queue.put(("status", f"Error processing file {os.path.basename(file_path)}: {e}"))
                        skipped_binary_count += 1

                    count +=1

            final_msg = f"Done. Combined {processed_count} files. Skipped {skipped_binary_count} (binary/unreadable)."
            self.msg_queue.put(("done", final_msg))

        except IOError as e:
            self.msg_queue.put(("error", f"Error writing output file: {e}"))
        except Exception as e:
            self.msg_queue.put(("error", f"An unexpected error occurred: {e}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = TextCombinerApp(root_window=root)
    root.mainloop()
