import numpy as np
import win32gui
import win32ui
import win32con
import win32api
from ctypes import windll
import cv2
import pymem
from frame import Frame
from ProcessManager import ProcessManager
import math
import time
import constants as cs


class WindowCapture:
    # BYTES_SEARCH_PATTERN = b'\x20\x41\xCD\xCC\x4C\x3E.....\x7F\x00\x00.....\x7F'
    BYTES_SEARCH_PATTERNS = [
        b'\xAB\xAA\xAA\x3E\xCD\xCC\x4C\x3E\xCD\xCC\xCC\x3D\x00\x00\xA0\x40\xFF\xFF\x00\x00............\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.....\x76\x00\x00.....\x76\x00\x00\x00\x00\x00\x00............',
        b'\xAB\xAA\xAA\x3E\xCD\xCC\x4C\x3E\xCD\xCC\xCC\x3D\x00\x00\xA0\x40\xFF\xFF\x00\x00............\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.....\x7F\x00\x00.....\x7F\x00\x00\x00\x00\x00\x00............',
        b'\xAB\xAA\xAA\x3E\xCD\xCC\x4C\x3E\xCD\xCC\xCC\x3D\x00\x00\xA0\x40\xFF\xFF\x00\x00............\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00......\x00\x00......\x00\x00\x00\x00\x00\x00............'
    ]
    # 012C = 300 - Balo open
    # OFFSET_BALO = 214
    OFFSET_BALO = 428
    OFFSET_FISING_STATE = 308
    OFFSET_ROD = 497
    ORIGINAL_WIDTH = 1247
    TITLE_BAR_HEIGHT = 34

    # threading properties
    stopped = True
    screenshot = None
    # properties
    w = 0
    h = 0
    window_rect = None
    hwnd = None
    hwndChild = None
    ratio = 1
    prevWidth = ORIGINAL_WIDTH
    frame = Frame()

    # constructor
    def __init__(self, windowName, headlessPID, noMem=False, messageQueue=None, fishingVariables=None):
        self.messageQueue = messageQueue
        self.windowName = windowName
        self.hwnd = win32gui.FindWindow(None, windowName)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(windowName))
        self.hwndChild = win32gui.GetWindow(self.hwnd, win32con.GW_CHILD)
        self.scaleRate = self.getWindowDpiScale(self.hwndChild)
        self.headlessPID = headlessPID
        self.fishingVariables = fishingVariables or {}
        self.lockedBaloAddr = False

        if not noMem:
            self.pm = pymem.Pymem()
            self.pm.open_process_from_id(self.headlessPID)

            if self.fishingVariables['locked_address'] is not None:
                self.baloAddr = self.fishingVariables['locked_address']
                self.log(f"Using locked address: {format(self.baloAddr, 'x')}")
                self.lockedBaloAddr = True
                return

            self.readMemoryTilDeath()

    def log(self, message):
        """Log message to both console and GUI if message_queue is available"""
        print(message)
        if self.messageQueue:
            self.messageQueue.put(f"{message}\n")

    def readMemoryTilDeath(self):
        self.baloAddr = None

        nextIdx = 0

        while self.baloAddr is None:
            searchPattern = self.BYTES_SEARCH_PATTERNS[nextIdx]

            self.log(
                f'Reading LDPlayer\'s memory state, please wait. Process ID: {self.headlessPID}, {nextIdx}')
            # self.log(self.BYTES_SEARCH_PATTERN)
            self.baloAddresses = pymem.pattern.pattern_scan_all(
                self.pm.process_handle, searchPattern, return_multiple=True)

            if self.messageQueue:
                self.messageQueue.put(
                    f"Found addresses: {[format(addr, 'X') for addr in self.baloAddresses]}\n")
            else:
                print(
                    f"Found addresses: {[format(addr, 'X') for addr in self.baloAddresses]}")

            for x in self.baloAddresses:
                if x == 1378250972:
                    self.log(f"Found special address: {x}")
            self.baloAddresses = [
                x + self.OFFSET_BALO for x in self.baloAddresses]

            if len(self.baloAddresses) == 0:
                self.log('No memory addresses found, retrying...')
                if nextIdx >= len(self.BYTES_SEARCH_PATTERNS) - 1:
                    nextIdx = 0
                else:
                    nextIdx += 1
                continue

            self.baloAddr = self.baloAddresses[0]
        self.log('Successfully read memory state')

    def getWindowSize(self):
        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.left, self.top, self.right, self.bot = window_rect
        self.w = math.ceil((self.right - self.left) * self.scaleRate)
        self.h = math.ceil((self.bot - self.top) * self.scaleRate)

        if self.w != self.prevWidth:
            self.ratio = self.w / self.ORIGINAL_WIDTH
            self.prevWidth = self.w

    def partialCapture(self, pos, width, height):
        self.getWindowSize()

        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)

        cDC.BitBlt((0, 0), (width, height), dcObj,
                   (int(pos[0] - width / 2), int(pos[1] - height / 2)), win32con.SRCCOPY)

        bmpinfo = dataBitMap.GetInfo()
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype=np.uint8).reshape(
            (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        frame = Frame()
        frame.setMatrix(img, pos, width, height)

        return frame

    def capture(self):
        self.getWindowSize()

        # get the window image data
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)

        # cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (0, 0), win32con.SRCCOPY)
        windll.user32.PrintWindow(self.hwnd, cDC.GetSafeHdc(), 3)

        bmpinfo = dataBitMap.GetInfo()
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype=np.uint8).reshape(
            (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

        # free resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        self.frame.setMatrix(
            img, width=bmpinfo['bmWidth'], height=bmpinfo['bmHeight'])

        def click_event(event, x, y, flags, param):
            # Check if left mouse button was clicked
            if event == cv2.EVENT_LBUTTONDOWN:
                # Get image from param
                img = param

                # Get the color at clicked coordinates
                # Note: OpenCV uses BGR format by default, not RGB
                # Get BGR values, ignoring alpha if present
                b, g, r = img[y, x, 0:3]

                # Get hex color code
                hex_color = f"#{r:02x}{g:02x}{b:02x}"

                originalX = x / self.ratio
                originalY = (y + self.TITLE_BAR_HEIGHT) / self.ratio

                # Print color information
                print(f"W x H: {self.w} x {self.h}")
                print(f"Coordinates: ({originalX},{originalY})")
                print(f"BGR Color: ({b},{g},{r})")
                print(f"Hex Color: {hex_color}")

                # Optional: Display color info on the image
                cv2.putText(img, f"({x},{y}): {hex_color}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(img, f"({x},{y}): {hex_color}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (b, g, r), 1)

                # Show the image with color information
                cv2.imshow('Test', img)

        # print(self.w)

        # frame = self.frame.matrix.copy()
        # frame = cv2.circle(frame, self.pointAtResized(
        #     self.frame, cs.CAUGHT_FISH_COLOUR_COORDS), 4, (0, 0, 255), 1)
        # print(self.colourAt(self.frame, cs.CAUGHT_FISH_COLOUR_COORDS))

        # cv2.imshow('Test', frame)
        # cv2.setMouseCallback('Test', click_event, frame)
        # cv2.waitKey(0)

        return self.frame

    def getPixVal(self, pt, frame, raw=False):
        '''Get pixel value the exclamation mark'''
        x = pt[0]
        y = pt[1]
        crop = frame.matrix[y-1:y+1, x-1:x+1]

        if raw:
            return crop

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        avg = cv2.mean(gray)
        return avg[0]

    def colourAt(self, frame, pt):
        ptResized = self.pointAtResized(frame, pt)
        b, g, r = frame.matrix[ptResized[1], ptResized[0], 0:3]

        return r, g, b

    def toRelative(self, pt):
        return pt[0] - self.left, pt[1] - self.top

    def press(self, vk_code, single=False):
        '''Press any key using win32api.Sendmessage'''
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
        time.sleep(0.011)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)
        time.sleep(0.007)
        if not single:
            win32api.SendMessage(
                self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
            time.sleep(0.011)
            win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)

    def leftClick(self, pos):
        posLong = win32api.MAKELONG(
            math.ceil(pos[0] / self.scaleRate), math.ceil((pos[1] / self.scaleRate) - self.TITLE_BAR_HEIGHT))
        win32gui.SendMessage(
            self.hwndChild, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        win32gui.PostMessage(self.hwndChild, win32con.WM_MOUSEMOVE, 0, posLong)
        time.sleep(0.030)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, posLong)
        time.sleep(0.010)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, posLong)

    def adjustBaloAddr(self, expectedStates):
        if self.lockedBaloAddr:
            return

        found = False

        for addr in self.baloAddresses:
            state = self.pm.read_int(addr + self.OFFSET_FISING_STATE)
            self.log(
                f'adjustBaloAddr state: {state}, address: {format(addr, "x")}')
            if state in expectedStates:
                if self.baloAddr == addr:
                    found = True
                    break
                self.log(
                    f'Self-adjusting to address {format(addr, "x")} because state {state} is in expected states {expectedStates}')
                self.baloAddr = addr
                found = True
                break

        if not found:
            self.log("No valid address found, reinitializing memory search...")
            self.readMemoryTilDeath()

    def getFishingState(self):
        return self.pm.read_int(self.baloAddr + self.OFFSET_FISING_STATE)

    def getWindowDpiScale(self, hwnd):
        return windll.user32.GetDpiForWindow(hwnd) / 96.0

    def onFailedReel(self):
        self.log(
            f"Failed reel detected, removing address {format(self.baloAddr, 'x')} from valid addresses")
        self.baloAddresses.remove(self.baloAddr)

    def pointAtResized(self, frame, pt):
        x = pt[0] - frame.origin[0]
        y = pt[1] - frame.origin[1]
        print(x, y, frame.origin, self.ratio, self.scaleRate)
        x, y = math.ceil(x / self.scaleRate) * \
            self.ratio, math.ceil(y / self.scaleRate) * self.ratio

        if x < 0:
            x = 0
        elif x > self.w:
            x = self.w

        if y < 0:
            y = 0
        elif y > self.h:
            y = self.h

        return (int(x), int(y))

    @staticmethod
    def findAndInit(messageQueue=None):
        processManager = ProcessManager()

        if messageQueue:
            messageQueue.put(f"Found processes: {processManager.processes}\n")
        else:
            print(f"Found processes: {processManager.processes}")

        windowName = None
        headlessPID = None
        index = None

        if len(processManager.windows) == 0:
            error_msg = 'No LDPlayer found'
            if messageQueue:
                messageQueue.put(f"{error_msg}\n")
            else:
                print(error_msg)
            exit(1)
        elif len(processManager.windows) == 1:
            index = 0
        else:
            window_list = []
            for i, window in enumerate(processManager.windows):
                window_info = f'{i}. {window["name"]}'
                window_list.append(window_info)
                if messageQueue:
                    messageQueue.put(f"{window_info}\n")
                else:
                    print(window_info)

            input_msg = 'What window?: '
            if messageQueue:
                messageQueue.put(f"{input_msg}\n")
            else:
                print(input_msg)

            while index is None:
                idx = int(input())

                if idx < 0 or idx > len(processManager.windows):
                    error_msg = 'Invalid input, try again'
                    if messageQueue:
                        messageQueue.put(f"{error_msg}\n")
                    else:
                        print(error_msg)
                else:
                    index = idx

        windowName = processManager.windows[index]['name']
        headlessPID = processManager.headlessProcesses[index]['pid']

        return WindowCapture(windowName, headlessPID, messageQueue=messageQueue)
