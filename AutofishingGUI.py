import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import traceback
import win32gui
import sys
import io
from Autofishing import Autofishing
from ProcessManager import ProcessManager
from windowcapture import WindowCapture

# This will hide the console window
import win32con
import win32gui
import win32process


class AutofishingThread(threading.Thread):
    """Thread for running Autofishing without freezing the GUI."""

    def __init__(self, window_name, process_id, message_queue):
        super().__init__()
        self.window_name = window_name
        self.process_id = process_id
        self.message_queue = message_queue
        self.daemon = True
        self.running = True
        self.paused = False
        self.bot = None

    def run(self):
        try:
            # Initialize Autofishing bot
            self.message_queue.put(
                f"Initializing Autofishing for {self.window_name}...\n")

            winCap = WindowCapture(self.window_name, self.process_id)

            # Pass the message queue to the Autofishing instance
            self.bot = Autofishing(winCap, self.message_queue)

            # Start the fishing loop with output redirected to GUI
            self.message_queue.put(
                f"Starting autofishing on {self.window_name}...\n")

            # Set the pause flag based on thread state
            def check_pause():
                if self.paused and not self.bot.pause:
                    self.bot.pause = True
                elif not self.paused and self.bot.pause:
                    self.bot.pause = False
                if self.running:
                    threading.Timer(1.0, check_pause).start()

            check_pause()

            # Start the fishing loop
            self.bot.startLoop()

        except Exception as e:
            self.message_queue.put(f"Error in fishing thread: {str(e)}\n")
            self.message_queue.put(traceback.format_exc())

    def stop(self):
        self.running = False
        if self.bot:
            self.bot.pause = True

    def pause(self):
        self.paused = True
        if self.bot:
            self.bot.pause = True

    def resume(self):
        self.paused = False
        if self.bot:
            self.bot.pause = False


class AutofishingGUI:
    """Main GUI class for Autofishing control."""

    def __init__(self, root):
        self.root = root
        self.root.title("Autofishing Control Panel")
        self.root.geometry("450x200")

        # Initialize process manager
        self.process_manager = ProcessManager()

        # Create message queues for communication between threads and GUI
        self.message_queues = {}
        self.log_widgets = {}

        # Store running threads
        self.fishing_threads = {}

        # Create GUI components
        self.create_widgets()

        # Start the message checking loop
        self.check_messages()

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
            top_frame, text="↻", width=2, command=self.refresh_windows)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 10))

        # Start button
        self.start_button = ttk.Button(
            top_frame, text="Start", command=self.start_fishing)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        # Pause button
        self.pause_button = ttk.Button(
            top_frame, text="Pause", command=self.pause_fishing)
        self.pause_button.pack(side=tk.LEFT)
        self.pause_button.config(state=tk.DISABLED)  # Initially disabled

        # Main frame for log display
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tab control for logs from different windows
        self.tab_control = ttk.Notebook(main_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_selected)

        # Populate windows dropdown
        self.refresh_windows()

    def refresh_windows(self):
        # Reinitialize process manager to get updated window list
        self.process_manager = ProcessManager()

        # Clear combobox
        self.window_combobox.set('')
        self.window_combobox['values'] = []

        # Get window names
        window_names = [window['name']
                        for window in self.process_manager.windows]

        if window_names:
            self.window_combobox['values'] = window_names
            self.window_combobox.current(0)
            self.start_button.config(state=tk.NORMAL)

            # Update button state for the selected window
            self.on_window_selected(None)
        else:
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.DISABLED)

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
        for window, process in zip(self.process_manager.windows, self.process_manager.headlessProcesses):
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
        self.message_queues[window_name] = queue.Queue()

        return log_widget

    def update_button_state(self, window_name):
        """Update button states based on the current window and its thread status"""
        if window_name in self.fishing_threads and self.fishing_threads[window_name].running:
            thread = self.fishing_threads[window_name]
            if thread.paused:
                self.start_button.config(state=tk.NORMAL)
                self.pause_button.config(state=tk.DISABLED)
            else:
                self.start_button.config(state=tk.DISABLED)
                self.pause_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)

    def start_fishing(self):
        """Start or resume fishing for the selected window"""
        window_info = self.get_selected_window_info()
        if not window_info:
            return

        window_name = window_info['name']

        # If thread exists and is paused, resume it
        if window_name in self.fishing_threads and self.fishing_threads[window_name].running:
            thread = self.fishing_threads[window_name]
            if thread.paused:
                thread.resume()
                self.update_button_state(window_name)
        else:
            # Create new fishing thread
            if window_name not in self.message_queues:
                log_widget = self.create_log_tab(window_name)
                self.tab_control.select(self.tab_control.index(
                    'end')-1)  # Select the new tab

            thread = AutofishingThread(
                window_name,
                window_info['pid'],
                self.message_queues[window_name]
            )
            thread.start()

            self.fishing_threads[window_name] = thread
            self.update_button_state(window_name)

    def pause_fishing(self):
        """Pause fishing for the selected window"""
        window_info = self.get_selected_window_info()
        if not window_info:
            return

        window_name = window_info['name']

        if window_name in self.fishing_threads and self.fishing_threads[window_name].running:
            thread = self.fishing_threads[window_name]
            if not thread.paused:
                thread.pause()
                self.update_button_state(window_name)

    def check_messages(self):
        """Check message queues and update log widgets."""
        for window_name, msg_queue in list(self.message_queues.items()):
            # Get the log widget for this window
            log_widget = self.log_widgets.get(window_name)

            if log_widget:
                # Process all waiting messages
                while not msg_queue.empty():
                    try:
                        message = msg_queue.get(block=False)
                        log_widget.insert(tk.END, message)
                        log_widget.see(tk.END)  # Auto-scroll to the end
                    except queue.Empty:
                        break

        # Schedule next check
        self.root.after(100, self.check_messages)

    def on_closing(self):
        """Handle window closing event."""
        # Stop all fishing threads
        for thread in self.fishing_threads.values():
            if thread.running:
                thread.stop()

        self.root.destroy()


def hide_console():
    """Hide the console window"""
    hwnd = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)


if __name__ == "__main__":
    # hide_console()

    root = tk.Tk()
    app = AutofishingGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
