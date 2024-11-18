import win32gui
import win32api
import cv2
import numpy as np
import time
from windowcapture import WindowCapture
from vision import Vision
import traceback


class Autofishing:
    rng = None
    winCap = None
    vision = None
    waitFuncs = None

    exclamationPoint = None

    def __init__(self):
        self.rng = np.random.default_rng(seed=6994420)
        self.winCap = WindowCapture.findAndInit()
        self.vision = Vision(winCap=self.winCap)
        self.winCap.capture()  # To calculate rect

        self.waitFuncs = {
            'veryslow': lambda: self.rng.integers(low=2333, high=2720, size=1)[0],
            'slow': lambda: self.rng.integers(low=829, high=1362, size=1)[0],
            'fast': lambda: self.rng.integers(low=202, high=397, size=1)[0],
            'ok': lambda: self.rng.integers(low=420, high=521, size=1)[0],
        }

    def wait(self, duration):
        return cv2.waitKey(self.waitFuncs[duration]())

    def detectClick(self):
        """Detects and returns the click position"""
        prevStateLeftMouse = win32api.GetKeyState(0x01)
        print("Select position")
        while True:
            currentStateLeftMouse = win32api.GetKeyState(0x01)
            if currentStateLeftMouse != prevStateLeftMouse:  # button state changed
                prevStateLeftMouse = currentStateLeftMouse
                if currentStateLeftMouse < 0:
                    return win32gui.GetCursorPos()
            cv2.waitKey(33)

    def repair(self):
        '''Repair broken rod'''
        self.winCap.press(0x56)  # press v
        self.wait('veryslow')
        self.winCap.press(0x56)  # press v
        self.wait('slow')

    def pixelValuesChanged(self, prev, curr):
        normPrev = prev.astype(np.int16).ravel()
        normCurr = curr.astype(np.int16).ravel()
        diff = np.subtract(normCurr, normPrev)
        percentage = (np.mean(np.abs(diff) > 2) * 100)
        percentageNegative = (np.mean(diff < 0) * 100)
        result = percentage >= 50
        resultNegative = percentageNegative >= 25 and percentage > 33

        print('normPrev, normCurr, diff, percentage, percentageNegative, result, resultNegative',
              normPrev, normCurr, diff, percentage, percentageNegative, result, resultNegative)

        return result or resultNegative

    def isInside(self, pt, rect):
        (pt1, pt2) = rect

        if pt[0] < pt1[0] or pt[0] > pt2[0]:
            return False

        if pt[1] < pt1[1] or pt[1] > pt2[1]:
            return False

        return True

    def getInput(self):
        left, top, right, bot = self.winCap.left, self.winCap.top, self.winCap.right, self.winCap.bot

        print('Select exclamation mark location: ')
        while True:
            exclamationPoint = self.detectClick()

            if self.isInside(exclamationPoint, ((left, top), (right, bot))):
                break

        return self.winCap.toRelative(exclamationPoint)

    def correct(self, skipRetract):
        print('''It's real!''')
        if not skipRetract:
            self.winCap.press(0x20)
        count = 0
        while True:
            frame2 = self.winCap.capture()
            if self.vision.seeStoreButton(frame2):
                print('Storing')
                self.wait('ok')
                self.winCap.press(0x4C)  # press(L)
                self.wait('slow')
                break
            elif self.vision.seeFishingButton(frame2):
                break
            else:
                count = count + 1
                ints = self.rng.integers(low=8, high=12, size=1)
                if count >= ints[0]:
                    break

            self.wait('slow')

        print('Continue...')
        self.winCap.press(0x4B)
        time.sleep(2)
        frame2 = self.winCap.capture()
        if self.vision.seeBrokenRod(frame2):
            self.repair()
            self.winCap.press(0x4F)
            self.wait('slow')
            self.winCap.press(0x4B)
        time.sleep(10)

    def prepare(self):
        self.exclamationPoint = self.getInput()

    def startLoop(self):
        while True:
            frame = self.winCap.capture()
            skipRetract = False

            prevalRaw = self.winCap.getPixVal(
                self.exclamationPoint, frame, raw=True)
            count = 0

            while True:
                count = count + 1
                ints = self.rng.integers(low=180, high=289, size=1)

                if count >= ints[0]:
                    self.wait('ok')
                    break

                frame1 = self.winCap.capture()
                currentVal = self.winCap.getPixVal(
                    self.exclamationPoint, frame1)
                currentValRaw = self.winCap.getPixVal(
                    self.exclamationPoint, frame1, raw=True)

                if self.pixelValuesChanged(prevalRaw, currentValRaw) and currentVal > 100 and currentVal < 230:
                    break

                prevalRaw = currentValRaw
                if self.vision.seeFishingButton(frame1):
                    skipRetract = True
                    break

                self.wait('fast')

            self.correct(skipRetract)

            if self.vision.seeBrokenRod(frame):
                self.repair()
                self.winCap.press(0x4F)
                self.wait('slow')
                self.winCap.press(0x4B)

            self.wait('fast')


def main():
    bot = Autofishing()

    theThreads = []

    try:
        for theThread in theThreads:
            theThread.start()

        bot.prepare()

        print('Auto fishing will be started after 2 seconds')
        time.sleep(2)

        bot.startLoop()
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        for theThread in theThreads:
            theThread.stop()


if __name__ == '__main__':
    main()
