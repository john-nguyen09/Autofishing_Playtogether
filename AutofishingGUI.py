import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import multiprocessing
from multiprocessing import Process, Queue, Event
import queue
import time
import traceback
import win32gui
import sys
import io
import os
from Autofishing import Autofishing
from ProcessManager import ProcessManager
from windowcapture import WindowCapture
from updater import AutoUpdater


class AutofishingProcess(Process):
    """Process for running Autofishing without freezing the GUI."""

    def __init__(self, windowName, processId, messageQueue, controlQueue, stopEvent):
        super().__init__()
        self.windowName = windowName
        self.processId = processId
        self.messageQueue = messageQueue
        self.controlQueue = controlQueue
        self.stopEvent = stopEvent
        self.daemon = True

    def run(self):
        try:
            # Initialize Autofishing bot
            self.messageQueue.put(
                f"Initializing Autofishing for {self.windowName}...\n")

            winCap = WindowCapture(
                self.windowName, self.processId, messageQueue=self.messageQueue)

            # Pass the message queue to the Autofishing instance
            bot = Autofishing(winCap, self.messageQueue)

            # Start the fishing loop with output redirected to GUI
            self.messageQueue.put(
                f"Starting autofishing on {self.windowName}...\n")

            if not self.stopEvent.is_set():
                bot.startLoop(self.stopEvent)
        except Exception as e:
            self.messageQueue.put(f"Error in fishing process: {str(e)}\n")
            self.messageQueue.put(traceback.format_exc())
        except KeyboardInterrupt:
            try:
                sys.exit(130)
            except SystemExit:
                os._exit(130)
        finally:
            self.messageQueue.put(
                f"Fishing process terminated for {self.windowName}\n")


class AutofishingGUI:
    """Main GUI class for Autofishing control."""

    def __init__(self, root):
        self.root = root
        self.root.title("Autofishing Control Panel")
        self.root.geometry("450x400")  # Increased height for more log space

        # Initialize auto updater
        self.updater = AutoUpdater(
            repo_url="https://github.com/john-nguyen09/Autofishing_Playtogether")

        # Initialize process manager
        self.processManager = ProcessManager()

        # Create message queues for communication between processes and GUI
        self.message_queues = {}
        self.control_queues = {}
        self.stop_events = {}
        self.log_widgets = {}

        # Store running processes
        self.fishing_processes = {}

        # Create GUI components
        self.create_widgets()

        # Start the message checking loop
        self.check_messages()

        self.root.after(1000, self.check_for_updates)

    def create_widgets(self):
        # Top frame for controls
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # Dropdown for window selection
        self.window_combobox = ttk.Combobox(
            top_frame, width=20, state="readonly")
        self.window_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.window_combobox.bind(
            "<<ComboboxSelected>>", self.on_window_selected)

        # Refresh button
        self.refresh_button = ttk.Button(
            top_frame, text="Refresh", command=self.refresh_windows)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 10))

        # Start button
        self.start_button = ttk.Button(
            top_frame, text="Start", command=self.start_fishing)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        # Stop button (added for better process control)
        self.stop_button = ttk.Button(
            top_frame, text="Stop", command=self.stop_fishing)
        self.stop_button.pack(side=tk.LEFT, padx=(5, 0))
        self.stop_button.config(state=tk.DISABLED)  # Initially disabled

        # Main frame for log display
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tab control for logs from different windows
        self.tab_control = ttk.Notebook(main_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_selected)

        # Add a status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Populate windows dropdown
        self.refresh_windows()

    def check_for_updates(self):
        """Check for updates and prompt user if an update is available"""
        self.status_var.set("Checking for updates...")
        self.root.update_idletasks()

        # Run update check in a separate thread to not block UI
        def check_update_thread():
            update_available = self.updater.update_if_available(self.root)
            if not update_available:
                self.status_var.set("Ready - No updates available")

        threading.Thread(target=check_update_thread, daemon=True).start()

    def refresh_windows(self):
        # Reinitialize process manager to get updated window list
        self.processManager = ProcessManager()

        # Clear combobox
        self.window_combobox.set('')
        self.window_combobox['values'] = []

        # Get window names
        window_names = [window['name']
                        for window in self.processManager.windows]

        if window_names:
            self.window_combobox['values'] = window_names
            self.window_combobox.current(0)
            self.start_button.config(state=tk.NORMAL)

            # Update button state for the selected window
            self.on_window_selected(None)
        else:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def on_tab_selected(self, event):
        """Handle tab selection to update the combobox selection"""
        # Get the currently selected tab index
        selected_tab_idx = self.tab_control.index("current")

        # Get the tab text (window name) for the selected tab
        if selected_tab_idx >= 0:
            tab_text = self.tab_control.tab(selected_tab_idx, "text")

            # Update combobox without triggering its event
            self.window_combobox.set(tab_text)

            # Update button state for this window
            self.update_button_state(tab_text)

    def on_window_selected(self, event):
        """Handle window selection from dropdown"""
        selected_window = self.window_combobox.get()

        # Update button state for the selected window
        self.update_button_state(selected_window)

        # If tab exists for this window, switch to it
        for i in range(self.tab_control.index('end')):
            if self.tab_control.tab(i, "text") == selected_window:
                self.tab_control.select(i)
                break

    def get_selected_window_info(self):
        selected_name = self.window_combobox.get()
        for window, process in zip(self.processManager.windows, self.processManager.headlessProcesses):
            if window['name'] == selected_name:
                return {
                    'name': window['name'],
                    'hwnd': window['hwnd'],
                    'pid': process['pid']
                }
        return None

    def create_log_tab(self, window_name):
        # Create a new tab for this window
        tab = ttk.Frame(self.tab_control)
        self.tab_control.add(tab, text=window_name)

        # Add scrolled text widget for logs
        log_widget = scrolledtext.ScrolledText(tab, wrap=tk.WORD, height=20)
        log_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Store reference to log widget
        self.log_widgets[window_name] = log_widget

        # Create message queue for this window
        self.message_queues[window_name] = multiprocessing.Queue()
        self.control_queues[window_name] = multiprocessing.Queue()
        self.stop_events[window_name] = multiprocessing.Event()

        return log_widget

    def update_button_state(self, window_name):
        """Update button states based on the current window and its process status"""
        if window_name in self.fishing_processes and self.fishing_processes[window_name].is_alive():
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def start_fishing(self):
        """Start or resume fishing for the selected window"""
        window_info = self.get_selected_window_info()
        if not window_info:
            return

        window_name = window_info['name']

        if window_name not in self.fishing_processes or not self.fishing_processes[window_name].is_alive():
            # Create new fishing process
            if window_name not in self.message_queues:
                log_widget = self.create_log_tab(window_name)
                self.tab_control.select(self.tab_control.index(
                    'end')-1)  # Select the new tab

            self.stop_events[window_name].clear()

            process = AutofishingProcess(
                window_name,
                window_info['pid'],
                self.message_queues[window_name],
                self.control_queues[window_name],
                self.stop_events[window_name]
            )
            process.start()

            self.fishing_processes[window_name] = process
            self.update_button_state(window_name)

    def stop_fishing(self):
        """Stop fishing for the selected window"""
        window_info = self.get_selected_window_info()
        if not window_info:
            return

        window_name = window_info['name']

        if window_name in self.fishing_processes and self.fishing_processes[window_name].is_alive():
            # Signal the process to stop
            self.control_queues[window_name].put("STOP")
            self.stop_events[window_name].set()

            # Don't wait for it to finish here to avoid blocking GUI
            # The process should terminate on its own
            self.message_queues[window_name].put(
                f"Stopping fishing for {window_name}...\n")
            self.update_button_state(window_name)

    def check_messages(self):
        """Check message queues and update log widgets."""
        for window_name, msg_queue in list(self.message_queues.items()):
            # Get the log widget for this window
            log_widget = self.log_widgets.get(window_name)

            if log_widget:
                # Process all waiting messages
                try:
                    while True:  # Process all available messages
                        try:
                            message = msg_queue.get_nowait()

                            if 'Fishing process terminated' in message:
                                self.root.after(
                                    1000, lambda: self.update_button_state(window_name))

                            log_widget.insert(tk.END, message)
                            log_widget.see(tk.END)  # Auto-scroll to the end
                        except queue.Empty:
                            break
                except Exception as e:
                    print(f"Error processing message queue: {e}")

            if (window_name in self.fishing_processes and self.stop_events[window_name].is_set()):
                # Process died unexpectedly
                if log_widget:
                    log_widget.insert(
                        tk.END, f"Process for {window_name} has terminated unexpectedly.\n")
                    log_widget.see(tk.END)
                self.stop_events[window_name].set()  # Mark as stopped
                self.update_button_state(window_name)

        # Schedule next check
        self.root.after(100, self.check_messages)

    def on_closing(self):
        """Handle window closing event."""
        # Stop all fishing processes
        for window_name, process in list(self.fishing_processes.items()):
            if process.is_alive():
                self.control_queues[window_name].put("STOP")
                self.stop_events[window_name].set()

                # Give processes a moment to terminate cleanly
                process.join(0.5)

                if process.is_alive():
                    process.terminate()

        self.root.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()

    root = tk.Tk()
    app = AutofishingGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
