import numpy as np
import win32gui
import win32ui
import win32con
import win32api
import re
import cv2
from frame import Frame


class WindowCapture:

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
    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(window_name))

        self.hwndChild = win32gui.GetWindow(self.hwnd, win32con.GW_CHILD)

    def getWindowSize(self):
        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.left, self.top, self.right, self.bot = window_rect
        self.w = self.right - self.left
        self.h = self.bot - self.top

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

        cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (0, 0), win32con.SRCCOPY)
        # windll.user32.PrintWindow(self.hwnd, cDC.GetSafeHdc(), 3)

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

    def press(self, vk_code):
        '''Press any key using win32api.Sendmessage'''
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
        cv2.waitKey(11)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)
        cv2.waitKey(7)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
        cv2.waitKey(11)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)

    def leftClick(self, pos):
        posLong = win32api.MAKELONG(int(pos[0]), int(pos[1] - 20))
        win32gui.SendMessage(
            self.hwndChild, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        win32gui.PostMessage(self.hwndChild, win32con.WM_MOUSEMOVE, 0, posLong)
        cv2.waitKey(30)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, posLong)
        cv2.waitKey(10)
        win32api.PostMessage(
            self.hwndChild, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, posLong)

    # find the name of the window you're interested in.
    # once you have it, update window_capture()
    # https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window

    @staticmethod
    def listWindowNames():
        names = []

        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                names.append(win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(winEnumHandler, None)
        return names

    @staticmethod
    def findAll():
        matchedNames = []
        for name in WindowCapture.listWindowNames():
            if re.search('^LDPlayer', name):
                matchedNames.append(name)

        return matchedNames

    @staticmethod
    def findAndInit():
        matchedNames = WindowCapture.findAll()

        targetName = ''
        if len(matchedNames) == 0:
            print('No LDPlayer found')
            exit(1)
        elif len(matchedNames) == 1:
            targetName = matchedNames[0]
        else:
            for i, name in enumerate(matchedNames):
                print(f'{i}. {name}')
            print('What window?: ')

            while len(targetName) == 0:
                idx = int(input())

                if idx < 0 or idx > len(matchedNames):
                    print('Invalid input, try again')
                else:
                    targetName = matchedNames[idx]

        return WindowCapture(targetName)
