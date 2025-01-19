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


class WindowCapture:
    BYTES_SEARCH_PATTERN = b'\\x02\\x00\\x00\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00.\\x00\\x00\\x00.\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00...........................\\x3E\\xCD\\xCC......................\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00....\\x00.......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00......\\x00\\x00......\\x00\\x00\\x00.....\\x00\\x00........................\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x20\\x41\\xCD\\xCC\\x4C\\x3E......\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00......\\x00\\x00......\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00......\\x00\\x00......\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x80\\x3F\\x00\\x00\\x00\\x00....\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00.\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00..\\x00\\x00\\x00\\x00\\x00\\x00......\\x00\\x00......\\x00\\x00'
    OFFSET_BALO = 501
    OFFSET_FISING_STATE = 296
    OFFSET_ROD = 497
    ORIGINAL_WIDTH = 1247

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
    def __init__(self, windowName, headlessPID):
        self.hwnd = win32gui.FindWindow(None, windowName)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(windowName))
        self.hwndChild = win32gui.GetWindow(self.hwnd, win32con.GW_CHILD)
        self.scaleRate = self.getWindowDpiScale(self.hwndChild)
        self.headlessPID = headlessPID
        self.pm = pymem.Pymem()
        self.pm.open_process_from_id(self.headlessPID)

        print('Reading LDPlayer\' memory state, please wait')
        self.baloAddresses = pymem.pattern.pattern_scan_all(
            self.pm.process_handle, self.BYTES_SEARCH_PATTERN, return_multiple=True)
        self.baloAddresses = [x + self.OFFSET_BALO for x in self.baloAddresses]
        self.baloAddr = self.baloAddresses[0]
        print('Done reading memory')

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

        self.frame.setMatrix(img)

        # cv2.imshow('Test', self.frame.matrix)

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

    def toRelative(self, pt):
        return pt[0] - self.left, pt[1] - self.top

    def press(self, vk_code, single=False):
        '''Press any key using win32api.Sendmessage'''
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
        cv2.waitKey(11)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)
        cv2.waitKey(7)
        if not single:
            win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
            cv2.waitKey(11)
            win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)

    def leftClick(self, pos):
        posLong = win32api.MAKELONG(math.ceil(pos[0] / self.scaleRate), math.ceil((pos[1] / self.scaleRate) - 20))
        win32gui.SendMessage(
            self.hwndChild, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        win32gui.PostMessage(self.hwndChild, win32con.WM_MOUSEMOVE, 0, posLong)
        cv2.waitKey(30)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, posLong)
        cv2.waitKey(10)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, posLong)

    def adjustBaloAddr(self, expectedStates):
        for addr in self.baloAddresses:
            state = self.pm.read_int(addr + self.OFFSET_FISING_STATE)
            print('adjustBaloAddr state', state)
            if state in expectedStates:
                if self.baloAddr == addr:
                    break
                print(
                    f'self adjusting to {addr} because {state} in {expectedStates}')
                self.baloAddr = addr
                break

    def getFishingState(self):
        return self.pm.read_int(self.baloAddr + self.OFFSET_FISING_STATE)

    def getWindowDpiScale(self, hwnd):
        return windll.user32.GetDpiForWindow(hwnd) / 96.0

    @staticmethod
    def findAndInit():
        processManager = ProcessManager()

        windowName = None
        headlessPID = None
        index = None

        if len(processManager.windows) == 0:
            print('No LDPlayer found')
            exit(1)
        elif len(processManager.windows) == 1:
            index = 0
        else:
            for i, window in enumerate(processManager.windows):
                print(f'{i}. %s'.format(window['name']))
            print('What window?: ')

            while windowName is None:
                idx = int(input())

                if idx < 0 or idx > len(processManager.windows):
                    print('Invalid input, try again')
                else:
                    index = idx

        windowName = processManager.windows[index]['name']
        headlessPID = processManager.headlessProcesses[index]['pid']

        return WindowCapture(windowName, headlessPID)
