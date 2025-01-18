import win32process
import win32api
import win32con
import win32gui
import datetime
import re


class ProcessManager:
    def __init__(self):
        self.processes = []
        self.headlessProcesses = []
        self.windows = []
        pids = win32process.EnumProcesses()

        for pid in pids:
            try:
                processHandle = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_INFORMATION, False, pid)
                processName = win32process.GetModuleFileNameEx(processHandle, 0)

                if "dnplayer.exe" in processName:
                    creationTime = win32process.GetProcessTimes(processHandle)[
                        "CreationTime"]
                    self.processes.append({
                        "pid": pid,
                        "creationTime": datetime.datetime.timestamp(creationTime)
                    })
                elif "Ld9BoxHeadless.exe" in processName:
                    creationTime = win32process.GetProcessTimes(processHandle)[
                        "CreationTime"]
                    self.headlessProcesses.append({
                        "pid": pid,
                        "creationTime": datetime.datetime.timestamp(creationTime)
                    })

                win32api.CloseHandle(processHandle)
            except Exception:
                continue

        self.initialiseWindowsFromProcesses()
        self.sortProcessesAndWindowsByCreationTime()

    def initialiseWindowsFromProcesses(self):
        def enumWindowsCallback(hwnd, windows):
            ctid, cpid = win32process.GetWindowThreadProcessId(hwnd)
            for process in self.processes:
                if cpid == process["pid"] and re.match(r'^LDPlayer', win32gui.GetWindowText(hwnd)):
                    windows.append({
                        "hwnd": hwnd,
                        "pid": cpid,
                        "name": win32gui.GetWindowText(hwnd),
                        "creationTime": process['creationTime']
                    })

        matchedWindows = []
        try:
            win32gui.EnumWindows(enumWindowsCallback, matchedWindows)
            self.windows = matchedWindows
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def sortProcessesAndWindowsByCreationTime(self):
        self.processes.sort(key=lambda x: x["creationTime"], reverse=False)
        self.windows.sort(key=lambda x: x["creationTime"], reverse=False)
        self.headlessProcesses.sort(key=lambda x: x["creationTime"], reverse=False)