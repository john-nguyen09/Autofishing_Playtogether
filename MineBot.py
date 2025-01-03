import cv2
import numpy as np
from windowcapture import WindowCapture
from vision import Vision
import traceback
import tkinter as tk
from functools import partial
from pynput import keyboard
from threading import Lock, Thread
import utils
from queue import Queue


class WindowThread(Thread):
    def __init__(self, window, windowObj):
        super().__init__()
        self.rng = np.random.default_rng(seed=6994420)
        self.window = window
        self.winCap = windowObj['winCap']
        self.vision = windowObj['vision']
        self.commandQueue = windowObj['commandQueue']
        self.isRunning = True

        self.waitFuncs = {
            '2s': lambda: self.rng.integers(low=2000, high=2200, size=1)[0],
            '300-400': lambda: self.rng.integers(low=300, high=400, size=1)[0],
        }

    def repair(self):
        self.winCap.press(0x56)  # press v
        self.wait('2s')
        self.winCap.press(0x56)  # press v

    def run(self):
        while self.isRunning:
            frame = self.winCap.capture()

            if self.vision.seeCannotMine(frame)[0]:
                self.stop()
                print(f'[{self.window}] Can\'t mine stopping')
                self.commandQueue.put({
                    'action': 'threadStop',
                    'window': self.window,
                })
                break
            elif self.vision.seeBrokenRod(frame):
                self.repair()
            elif self.vision.seeStoreButton(frame):
                self.winCap.press(0x4C)  # press(L)
            elif self.vision.seeMine(frame)[0]:
                self.winCap.press(0x4B)  # press k
            else:
                self.winCap.press(0x4B)  # press k

            self.wait('300-400')

    def stop(self):
        self.isRunning = False

    def wait(self, duration):
        return cv2.waitKey(self.waitFuncs[duration]())


class Autokey:
    def __init__(self):
        self.allWindows = dict()
        self.isPaused = False
        self.isAltPressed = False
        self.isFPressed = False
        self.lock = Lock()
        self.commandQueue = Queue()

        self.listener = keyboard.Listener(
            on_press=self.onPress,
            on_release=self.onRelease
        )
        self.listener.start()

        allWindows = WindowCapture.findAll()
        allWindows.sort()
        for window in allWindows:
            winCap = WindowCapture(window)
            self.allWindows[window] = {
                'winCap': winCap,
                'vision': Vision(winCap=winCap),
                'thread': None,
                'commandQueue': self.commandQueue,
            }
            winCap.capture()  # To calculate rect

    def onPress(self, key):
        try:
            if key == keyboard.Key.alt_l:
                self.isAltPressed = True
            elif hasattr(key, 'char') and key.char.lower() == 'f' and self.isAltPressed:
                self.isFPressed = True
            elif hasattr(key, 'char') and key.char in '123' and self.isAltPressed and self.isFPressed:
                self.toggleCheckbox(int(key.char) - 1)
        except AttributeError:
            pass

    def onRelease(self, key):
        if key == keyboard.Key.alt:
            self.isAltPressed = False
        elif hasattr(key, 'char') and key.char.lower() == 'f':
            self.isFPressed = False

    def toggleCheckbox(self, index):
        with self.lock:
            if 0 <= index < len(self.allWindows):
                window = list(self.allWindows.keys())[index]
                obj = self.allWindows[window]
                # Toggle the checkbox value
                obj['active'].set(1 - obj['active'].get())
                self.checkbox(window, obj)

    def startLoop(self):
        mainWindow = tk.Tk()
        mainWindow.title("Autokey Control")

        def checkQueue():
            while not self.commandQueue.empty():
                command = self.commandQueue.get()
                if command['action'] == "threadStop":
                    obj = self.allWindows[command['window']]
                    obj['active'].set(0)
                    self.checkbox(window, obj)
            mainWindow.after(100, checkQueue)  # Check every 100ms

        checkQueue()

        for i, (window, obj) in enumerate(self.allWindows.items()):
            obj['active'] = tk.IntVar(mainWindow)
            tk.Checkbutton(mainWindow, text=f"{window} (Alt+F+{i+1})",
                           variable=obj['active'],
                           command=partial(self.checkbox, window, obj)).grid(
                row=i, sticky=tk.W)

        mainWindow.mainloop()

    def checkbox(self, window, winObj):
        value = winObj['active'].get()

        if value == 1:
            if winObj['thread'] is None or not winObj['thread'].is_alive():
                winObj['thread'] = WindowThread(window, winObj)
                winObj['thread'].start()
        else:
            if winObj['thread'] is not None and winObj['thread'].is_alive():
                winObj['thread'].stop()
                winObj['thread'].join()
                winObj['thread'] = None

    def cleanup(self):
        for window, obj in self.allWindows.items():
            if obj['thread'] is not None and obj['thread'].is_alive():
                obj['thread'].stop()
                obj['thread'].join()

        self.listener.stop()


def main():
    bot = Autokey()
    activeThreads = []

    try:
        for thread in activeThreads:
            thread.start()

        bot.startLoop()
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        for thread in activeThreads:
            thread.stop()
    finally:
        bot.cleanup()


if __name__ == '__main__':
    main()
