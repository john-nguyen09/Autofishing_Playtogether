import numpy as np
import win32gui, win32ui, win32con, win32api
from ctypes import windll
import re
from PIL import Image
import cv2


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

    # constructor
    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(window_name))

        self.hwndChild = win32gui.GetWindow(self.hwnd, win32con.GW_CHILD)


    def capture(self):

        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.left, self.top, self.right, self.bot = window_rect
        self.w = self.right - self.left
        self.h = self.bot - self.top

        if self.w != self.prevWidth:
            self.ratio = self.w / self.ORIGINAL_WIDTH
            self.prevWidth = self.w

        # get the window image data
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)

        windll.user32.PrintWindow(self.hwnd, cDC.GetSafeHdc(), 3)

        bmpinfo = dataBitMap.GetInfo()
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.fromstring(signedIntsArray, dtype='uint8')
        img.shape = (self.h, self.w, 4)

        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            signedIntsArray, 'raw', 'BGRX', 0, 1)

        # free resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


    def getPixVal(self, pt, frame, raw=False):
        '''Get pixel value the exclamation mark'''
        x = pt[0] - self.left
        y = pt[1] - self.top
        crop = frame[y-1:y+1, x-1:x+1]

        if raw:
            return crop

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        avg = cv2.mean(gray)
        return avg[0]


    def press(self, vk_code):
        '''Press any key using win32api.Sendmessage'''
        print('vk_code', vk_code)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
        win32api.SendMessage(self.hwndChild, win32con.WM_KEYUP, vk_code, 0)


    # find the name of the window you're interested in.
    # once you have it, update window_capture()
    # https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window
    @staticmethod
    def list_window_names():
        names = []
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                names.append(win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(winEnumHandler, None)
        return names


    @staticmethod
    def find_and_init():
        matched_names = []
        for name in WindowCapture.list_window_names():
            if re.search('^LDPlayer', name):
                matched_names.append(name)

        target_name = ''
        if len(matched_names) == 0:
            print('No LDPlayer found')
            exit(1)
        elif len(matched_names) == 1:
            target_name = matched_names[0]
        else:
            for i, name in enumerate(matched_names):
                print(f'{i}. {name}')
            print('What window?: ')

            while len(target_name) == 0:
                idx = int(input())

                if idx < 0 or idx > len(matched_names):
                    print('Invalid input, try again')
                else:
                    target_name = matched_names[idx]

        return WindowCapture(target_name)
