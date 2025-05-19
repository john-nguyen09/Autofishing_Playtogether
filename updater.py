import requests
import os
import zipfile
import shutil
import io
import re
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import tempfile
import time


class AutoUpdater:
    """GitHub auto-updater for Autofishing_Playtogether application."""

    def __init__(self, repo_url="https://github.com/john-nguyen09/Autofishing_Playtogether", current_version=None):
        self.repo_url = repo_url
        self.api_url = repo_url.replace(
            "github.com", "api.github.com/repos") + "/releases/latest"
        self.current_version = current_version or self._get_current_version()
        self.temp_dir = None
        self.extracted_path = None

    def _get_current_version(self):
        """Try to get the current version from version.py or default to 0.0.0"""
        try:
            # First try to import version from version.py
            try:
                from version import version
                return version
            except ImportError:
                return '0.0.0'
        except:
            pass
        return "0.0.0"

    def check_for_updates(self):
        """Check if a newer version is available on GitHub"""
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"].lstrip("v")

                # Compare versions
                if self._is_newer_version(latest_version, self.current_version):
                    return {
                        "available": True,
                        "current_version": self.current_version,
                        "latest_version": latest_version,
                        "release_notes": latest_release.get("body", ""),
                        "download_url": latest_release["zipball_url"],
                        "release_date": latest_release["published_at"]
                    }

            return {"available": False}
        except Exception as e:
            print(f"Error checking for updates: {str(e)}")
            return {"available": False, "error": str(e)}

    def _is_newer_version(self, latest, current):
        """Compare two semantic version strings"""
        def normalize(v):
            # Convert to list of integers for easy comparison
            return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.')]

        try:
            latest_parts = normalize(latest)
            current_parts = normalize(current)

            # Pad with zeros to make same length
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)

            # Compare each component
            for i in range(len(latest_parts)):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False

            return False  # Equal versions
        except:
            # If comparison fails, assume newer version is available
            return True

    def download_update(self, download_url, progress_callback=None):
        """Download the latest version but don't install yet"""
        try:
            # Download the update
            if progress_callback:
                progress_callback(0, "Downloading update...")

            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            # Create a temporary directory
            self.temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(self.temp_dir, "AutoFishingUpdate.zip")

            # Save the zip file
            with open(zip_path, 'wb') as f:
                total_length = response.headers.get('content-length')

                if total_length is None:  # No content length header
                    f.write(response.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        if progress_callback:
                            progress_callback(
                                int(dl / total_length * 50), "Downloading update...")

            if progress_callback:
                progress_callback(50, "Extracting files...")

            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                extract_dir = os.path.join(
                    self.temp_dir, "AutoFishingExtracted")
                zip_ref.extractall(extract_dir)

                # Get the extracted folder name (usually includes repo name and commit)
                extracted_folder = os.listdir(extract_dir)[0]
                self.extracted_path = os.path.join(
                    extract_dir, extracted_folder)

                if progress_callback:
                    progress_callback(75, "Update ready to install...")

                return True
        except Exception as e:
            print(f"Error during update download: {str(e)}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False

    def _create_updater_script(self):
        """Create a script that will complete the update after the main app exits"""
        script_path = os.path.join(self.temp_dir, "finish_update.py")

        # Get the path to the main executable or script
        if getattr(sys, 'frozen', False):
            # For PyInstaller executables
            app_path = sys.executable
        else:
            # For Python scripts
            app_path = sys.argv[0]

        app_dir = os.getcwd()

        # Files to exclude from updating (keep originals)
        exclude_files = ['.git', '.gitignore', 'data', '__pycache__',
                         'playground', 'build', 'dist', '.claudesync']

        with open(script_path, 'w') as f:
            f.write(f"""import os
import shutil
import time
import sys
import subprocess

def main():
    # Wait for main application to exit
    print("Waiting for main application to exit...")
    time.sleep(2)

    source_dir = r"{self.extracted_path}"
    dest_dir = r"{app_dir}"

    # Files to exclude from updating
    exclude_files = {exclude_files}

    print("Updating files...")

    # Function to copy files recursively
    def update_files(src, dst):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)

            # Skip excluded directories and files
            if item in exclude_files:
                continue

            if os.path.isdir(s):
                if not os.path.exists(d):
                    os.makedirs(d)
                update_files(s, d)
            else:
                # Try to copy with multiple attempts (files might be locked)
                max_attempts = 5
                for attempt in range(max_attempts):
                    try:
                        shutil.copy2(s, d)
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            print(f"Couldn't copy {{item}}, retrying in 1 second...")
                            time.sleep(1)
                        else:
                            print(f"Failed to copy {{item}} after {{max_attempts}} attempts")

    # Update all files
    update_files(source_dir, dest_dir)

    print("Update completed.")

    # Start the application again
    try:
        if os.path.exists(r"{app_path}"):
            subprocess.Popen([r"{app_path}"])
    except Exception as e:
        print(f"Error restarting application: {{str(e)}}")

    # Clean up
    try:
        shutil.rmtree(r"{self.temp_dir}")
    except:
        pass

    # Exit this script
    sys.exit(0)

if __name__ == "__main__":
    main()
""")
        return script_path

    def prompt_for_update(self, parent=None):
        """Shows a dialog asking if the user wants to update"""
        update_info = self.check_for_updates()

        if not update_info.get("available", False):
            return False

        # Create a custom dialog
        dialog = tk.Toplevel(parent) if parent else tk.Tk()
        dialog.title("Update Available")
        dialog.geometry("400x500")

        # Make dialog modal
        dialog.grab_set()
        dialog.transient(parent) if parent else None

        # Add content
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="A new version is available!",
                 font=("", 12, "bold")).pack(anchor=tk.W)
        tk.Label(frame, text=f"Current version: {update_info['current_version']}").pack(
            anchor=tk.W, pady=(10, 0))
        tk.Label(frame, text=f"Latest version: {update_info['latest_version']}").pack(
            anchor=tk.W)

        # Release notes
        if update_info.get("release_notes"):
            tk.Label(frame, text="Release Notes:", font=(
                "", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
            notes_frame = tk.Frame(frame)
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=5)

            notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=8, width=40)
            notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            notes_text.insert(tk.END, update_info["release_notes"])
            notes_text.config(state=tk.DISABLED)

            scrollbar = tk.Scrollbar(notes_frame, command=notes_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            notes_text.config(yscrollcommand=scrollbar.set)

        # Buttons
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        update_choice = [False]  # Use a list to store the result

        def on_update():
            update_choice[0] = True
            dialog.destroy()

        def on_skip():
            dialog.destroy()

        tk.Button(button_frame, text="Update Now", command=on_update,
                  width=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="Skip", command=on_skip,
                  width=15).pack(side=tk.RIGHT)

        # Center the dialog
        if parent:
            dialog.geometry(
                f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        else:
            dialog.eval('tk::PlaceWindow . center')

        # Wait for the dialog to close
        dialog.wait_window()

        return update_choice[0]

    def show_progress_dialog(self, parent=None):
        """Shows a progress dialog for the update"""
        dialog = tk.Toplevel(parent) if parent else tk.Tk()
        dialog.title("Updating Application")
        dialog.geometry("350x120")
        dialog.resizable(False, False)

        # Make dialog modal
        dialog.grab_set()
        dialog.transient(parent) if parent else None

        # Add content
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        status_label = tk.Label(frame, text="Preparing to update...")
        status_label.pack(fill=tk.X, pady=(0, 10))

        progress = tk.IntVar()
        progress_bar = tk.ttk.Progressbar(
            frame, variable=progress, maximum=100)
        progress_bar.pack(fill=tk.X)

        # Center the dialog
        if parent:
            dialog.geometry(
                f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        else:
            dialog.eval('tk::PlaceWindow . center')

        # Update function
        def update_progress(percent, message):
            progress.set(percent)
            status_label.config(text=message)
            dialog.update()

            if percent >= 100:
                # Wait a bit before closing
                dialog.after(1000, dialog.destroy)

        return dialog, update_progress

    def update_if_available(self, parent=None):
        """Check for updates and install if available and approved by user"""
        if self.prompt_for_update(parent):
            # Get update info again to get download URL
            update_info = self.check_for_updates()
            if update_info.get("available", False):
                # Show progress dialog
                progress_dialog, progress_callback = self.show_progress_dialog(
                    parent)

                # Start the update process
                def do_update():
                    success = self.download_update(
                        update_info["download_url"],
                        progress_callback
                    )

                    if success:
                        # Create the updater script
                        updater_script = self._create_updater_script()

                        progress_callback(90, "Update ready to install...")
                        time.sleep(1)
                        progress_callback(100, "Finishing update...")

                        messagebox.showinfo(
                            "Update Ready",
                            "The update has been downloaded and will be installed when the application restarts. "
                            "The application will now close and restart automatically."
                        )

                        # Launch the updater script
                        self.launch_updater_and_exit(updater_script)
                    else:
                        progress_dialog.destroy()
                        messagebox.showerror(
                            "Update Failed",
                            "There was an error downloading the update. "
                            "Please try again later."
                        )

                # Run update in a separate thread to not block the UI
                import threading
                update_thread = threading.Thread(target=do_update)
                update_thread.daemon = True
                update_thread.start()

                return True

        return False

    def launch_updater_and_exit(self, updater_script):
        """Launch the updater script and exit the current application"""
        try:
            # Start the external updater process
            if sys.platform.startswith('win'):
                # Hide console window on Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen([sys.executable, updater_script],
                                 startupinfo=startupinfo,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # Unix-like systems
                subprocess.Popen([sys.executable, updater_script])

            # Exit this application
            os._exit(0)
        except Exception as e:
            print(f"Error launching updater: {str(e)}")
            messagebox.showerror(
                "Update Error",
                f"Failed to launch updater: {str(e)}"
            )


if __name__ == "__main__":
    # Test the updater
    updater = AutoUpdater()
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    if updater.update_if_available(root):
        print("Update process started")
    else:
        print("No update needed or user skipped")
        root.destroy()
