import win32gui
import win32api
import cv2
import numpy as np
import time
import utils
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
        self.pause = False

        self.waitFuncs = {
            '5s': lambda: self.rng.integers(low=4666, high=5222, size=1)[0],
            'veryslow': lambda: self.rng.integers(low=2333, high=2720, size=1)[0],
            'slow': lambda: self.rng.integers(low=829, high=1362, size=1)[0],
            'nottooslow': lambda: self.rng.integers(low=473, high=597, size=1)[0],
            'fast': lambda: self.rng.integers(low=258, high=297, size=1)[0],
            'fishBiting': lambda: self.rng.integers(low=248, high=311, size=1)[0],
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
        diffTotal = np.sum(np.abs(diff))

        result = percentage >= 50
        resultNegative = percentageNegative >= 25 and percentage > 33
        resultDiffTotal = diffTotal > 21

        print('diff, percentage, percentageNegative, result, resultNegative, resultDiffTotal',
              diff, percentage, percentageNegative, result, resultNegative, resultDiffTotal)

        return result or resultNegative or resultDiffTotal

    def isInside(self, pt, rect):
        (pt1, pt2) = rect

        if pt[0] < pt1[0] or pt[0] > pt2[0]:
            return False

        if pt[1] < pt1[1] or pt[1] > pt2[1]:
            return False

        return True

    # def getInput(self):
    #     left, top, right, bot = self.winCap.left, self.winCap.top, self.winCap.right, self.winCap.bot

    #     print('Select exclamation mark location: ')
    #     while True:
    #         exclamationPoint = self.detectClick()

    #         if self.isInside(exclamationPoint, ((left, top), (right, bot))):
    #             break

    #     return self.winCap.toRelative(exclamationPoint)

    def correct(self, skipRetract):
        if not skipRetract:
            self.winCap.press(0x20)
        count = 0
        while True:
            self.wait('nottooslow')

            frame2 = self.winCap.capture()
            if self.vision.seeStoreButton(frame2):
                print('seeStoreButton')
                self.wait('ok')
                self.winCap.press(0x4C)  # press(L)
                self.wait('slow')
                break
            elif self.vision.seeFishingButton(frame2):
                print('seeFishingButton')
                break
            elif (open := self.vision.seeCardsToOpen(frame2))[0]:
                self.winCap.leftClick(
                    utils.getRandomMiddle(self.rng, open[1], open[2]))
                self.wait('ok')
            elif (openAll := self.vision.seeOpenAll(frame2))[0]:
                self.winCap.leftClick(utils.getRandomMiddle(
                    self.rng, openAll[1], openAll[2]))
                self.wait('ok')
            elif (clickHere := self.vision.seeBunchOfClickHere(frame2))[0]:
                self.winCap.leftClick(utils.getRandomMiddle(
                    self.rng, clickHere[1], clickHere[2]))
                self.wait('ok')
            elif (ok := self.vision.seeOk(frame2))[0]:
                self.winCap.leftClick(
                    utils.getRandomMiddle(self.rng, ok[1], ok[2]))
                self.wait('slow')
                break
            elif (yes := self.vision.seeYes(frame2))[0]:
                self.winCap.leftClick(
                    utils.getRandomMiddle(self.rng, yes[1], yes[2]))
                skipRetract = True
                break
            else:
                count = count + 1
                ints = self.rng.integers(low=25, high=30, size=1)
                if count >= ints[0]:
                    print('correct timeout')
                    break

            print('correct continue')

        print('Continue...')
        self.winCap.press(0x4B)  # press k

        for i in range(3):
            frame2 = self.winCap.capture()
            if self.vision.seeFullBag(frame2)[0]:
                print('Bag is full - pausing')
                self.pause = True
                break
            self.wait('fast')

        self.wait('nottooslow')
        self.winCap.adjustBaloAddr([1, 2, 3])
        time.sleep(1)
        frame2 = self.winCap.capture()
        if self.vision.seeBrokenRod(frame2):
            self.repair()
            self.winCap.press(0x4F)
            self.wait('slow')
            self.winCap.press(0x4B)
        time.sleep(10)

    # def prepare(self):
    #     self.exclamationPoint = self.getInput()

    def startLoop(self):
        while True:
            if self.pause:
                self.wait('veryslow')
                continue

            frame = self.winCap.capture()
            skipRetract = False

            count = 0
            previousState = None

            while True:
                count = count + 1
                ints = self.rng.integers(low=180, high=289, size=1)

                if previousState not in [15, 16, 17, 18, 20, 24, 25]:
                    if count >= ints[0]:
                        self.wait('ok')
                        break

                state = self.winCap.getFishingState()

                print('state', state)

                if state == 0:  # Idle state
                    # print('Idle???')
                    pass
                elif state == 1:
                    # print("Starting fishing")
                    pass
                elif state == 3:
                    # print("Fishing")
                    pass
                elif state == 4:
                    # print("Fish appears")
                    pass
                elif state == 5:
                    print("It's reel")
                    self.winCap.press(0x20)
                elif state == 9:
                    frame1 = self.winCap.capture()
                    if (open := self.vision.seeCardsToOpen(frame1))[0]:
                        self.winCap.leftClick(
                            utils.getRandomMiddle(self.rng, open[1], open[2]))
                    elif (openAll := self.vision.seeOpenAll(frame1))[0]:
                        self.winCap.leftClick(utils.getRandomMiddle(
                            self.rng, openAll[1], openAll[2]))
                    elif (yes := self.vision.seeOk(frame1))[0]:
                        self.winCap.leftClick(
                            utils.getRandomMiddle(self.rng, yes[1], yes[2]))
                        skipRetract = True
                        break
                    elif (yes := self.vision.seeYes(frame1))[0]:
                        self.winCap.leftClick(
                            utils.getRandomMiddle(self.rng, yes[1], yes[2]))
                        skipRetract = True
                        break
                    else:
                        skipRetract = True
                        break
                elif state == 11:  # Rod broken
                    self.repair()
                    self.winCap.press(0x4F)
                    self.wait('slow')
                    self.winCap.press(0x4B)
                elif state == 12:  # Line broken
                    print("Rotten luck")
                    skipRetract = True
                    break
                elif state == 15:  # VIP fish states
                    if previousState != 15:
                        print('Got giant fish')
                        self.winCap.press(0x20, single=True)
                elif state == 16:
                    print('Waiting for giant fish')
                elif state == 17:
                    print('Giant fish trying to get away')
                    self.winCap.press(0x20, single=True)
                elif state == 18:
                    print('Got a hold of giant fish')
                elif state == 20:
                    print('Got giant fish')
                    self.wait('5s')
                elif state == 24:
                    print('Giant fish stunned')
                    self.winCap.press(0x20, single=True)
                elif state == 25:
                    print('Giant fish not stunned')

                if count % 7 == 0:
                    frame1 = self.winCap.capture()
                    if self.vision.seeFishingButton(frame1):
                        skipRetract = True
                        break

                if previousState != state:
                    previousState = state
                self.wait('fishBiting')

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

        # bot.prepare()

        # print('Auto fishing will be started after 2 seconds')
        # time.sleep(2)

        bot.startLoop()
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        for theThread in theThreads:
            theThread.stop()


if __name__ == '__main__':
    main()
