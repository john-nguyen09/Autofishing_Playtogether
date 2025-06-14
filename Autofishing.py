import win32gui
import win32api
import cv2
import numpy as np
import time
import utils
from windowcapture import WindowCapture
from vision import Vision
import traceback
import threading
import json


class Autofishing:
    rng = None
    winCap = None
    vision = None
    waitFuncs = None

    exclamationPoint = None

    addressCounters = {}

    def __init__(self, winCap=None, messageQueue=None, taskQueue=None, resultQueue=None, fishingVariables=None):
        self.rng = np.random.default_rng(seed=6994420)
        if winCap is not None:
            self.winCap = winCap
        else:
            self.winCap = WindowCapture.findAndInit()
        self.vision = Vision(winCap=self.winCap, message_queue=messageQueue)
        self.winCap.capture()  # To calculate rect
        self.pause = False
        self.messageQueue = messageQueue
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue
        self.fishingVariables = fishingVariables or {}

        self.waitFuncs = {
            '5s': lambda: self.rng.integers(low=4666, high=5222, size=1)[0],
            'veryslow': lambda: self.rng.integers(low=2333, high=2720, size=1)[0],
            'slow': lambda: self.rng.integers(low=829, high=1362, size=1)[0],
            'nottooslow': lambda: self.rng.integers(low=473, high=597, size=1)[0],
            'fast': lambda: self.rng.integers(low=258, high=297, size=1)[0],
            'fishBiting': lambda: self.rng.integers(low=248, high=311, size=1)[0],
            'fasterOk': lambda: self.rng.integers(low=356, high=384, size=1)[0],
            'ok': lambda: self.rng.integers(low=420, high=521, size=1)[0],
        }

    def log(self, message):
        """Log message to both console and GUI if message_queue is available"""
        print(message)
        if self.messageQueue:
            self.messageQueue.put(f"{message}\n")

    def wait(self, duration):
        sleep_time = self.waitFuncs[duration]() / 1000.0
        time.sleep(sleep_time)

    def detectClick(self):
        """Detects and returns the click position"""
        prevStateLeftMouse = win32api.GetKeyState(0x01)
        self.log("Select position")
        while True:
            currentStateLeftMouse = win32api.GetKeyState(0x01)
            if currentStateLeftMouse != prevStateLeftMouse:  # button state changed
                prevStateLeftMouse = currentStateLeftMouse
                if currentStateLeftMouse < 0:
                    return win32gui.GetCursorPos()
            time.sleep(0.033)

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

        self.log(
            f'diff, percentage, percentageNegative, result, resultNegative, resultDiffTotal: {diff}, {percentage}, {percentageNegative}, {result}, {resultNegative}, {resultDiffTotal}')

        return result or resultNegative or resultDiffTotal

    def isInside(self, pt, rect):
        (pt1, pt2) = rect

        if pt[0] < pt1[0] or pt[0] > pt2[0]:
            return False

        if pt[1] < pt1[1] or pt[1] > pt2[1]:
            return False

        return True

    def correct(self, skipRetract):
        if not skipRetract:
            self.winCap.press(0x20)
        count = 0
        while True:
            self.wait('nottooslow')

            frame2 = self.winCap.capture()
            if (store := self.vision.seeStoreButton(frame2))[0]:
                self.log('seeStoreButton')
                self.onCaughtFish(store)
                self.wait('slow')
                break
            elif self.vision.seeFishingButton(frame2):
                self.log('seeFishingButton')
                break
            elif (open := self.vision.seeCardsToOpen(frame2))[0]:
                self.onGotCard()
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
                    self.log('correct timeout')
                    break

            self.log('correct continue')

        self.log('Continue...')
        self.onCasting()
        self.winCap.press(0x4B, single=True)  # press k

        self.ensureInitAddressCounters()
        counters = self.addressCounters[self.winCap.baloAddr]
        if counters['numCasting'] > 1 and counters['numReel'] == 0 and counters['numBrokenRod'] == 0 and counters['numCards'] == 0:
            self.winCap.onFailedReel()

        for i in range(3):
            frame2 = self.winCap.capture()
            if self.vision.seeFullBagOrCantFish(frame2)[0]:
                self.log('Bag is full or can no longer fish - pausing')
                self.pause = True
                return
            self.wait('slow')

        self.wait('nottooslow')
        if counters['numReel'] == 0:
            self.winCap.adjustBaloAddr([1, 2, 3, 11])
        time.sleep(1)
        frame2 = self.winCap.capture()
        if self.vision.seeBrokenRod(frame2):
            self.onBrokenRod()
            self.repair()
            self.winCap.press(0x4F)
            self.wait('slow')
            self.winCap.press(0x4B)
        time.sleep(8)

    def ensureInitAddressCounters(self):
        if self.winCap.baloAddr in self.addressCounters:
            return

        self.addressCounters[self.winCap.baloAddr] = {
            'numCaughtFish': 0,
            'numCasting': 0,
            'numBrokenRod': 0,
            'numReel': 0,
            'numCards': 0,
        }

    def onCasting(self):
        self.ensureInitAddressCounters()
        self.addressCounters[self.winCap.baloAddr]['numCasting'] += 1

    def onCaughtFish(self, store):
        self.wait('fasterOk')
        self.handleSellOrStore(store)

        self.ensureInitAddressCounters()
        self.addressCounters[self.winCap.baloAddr]['numCaughtFish'] += 1

    def onBrokenRod(self):
        self.ensureInitAddressCounters()
        self.addressCounters[self.winCap.baloAddr]['numBrokenRod'] += 1

    def onReel(self):
        self.ensureInitAddressCounters()
        self.log("It's reel")
        self.addressCounters[self.winCap.baloAddr]['numReel'] += 1

    def onGotCard(self):
        self.ensureInitAddressCounters()
        self.addressCounters[self.winCap.baloAddr]['numCards'] += 1

    def handleSellOrStore(self, store):
        frame, fishColourName, isCrown = self.vision.captureAndGetFishColour()

        shouldSellFish = self.fishingVariables.get('should_sell_fish', False)
        if shouldSellFish and (fishColourName == 'white' or fishColourName == 'green'):
            sell = self.vision.seeSellNowButton(frame)

            if sell[0]:
                self.winCap.leftClick(
                    utils.getRandomMiddle(self.rng, sell[1], sell[2]))
                self.wait('nottooslow')
                frame = self.winCap.capture()
                if (yes := self.vision.seeYes(frame))[0]:
                    self.winCap.leftClick(
                        utils.getRandomMiddle(self.rng, yes[1], yes[2]))
                    self.wait('nottooslow')

                self.winCap.press(0x56)  # press v
            else:
                self.winCap.leftClick(
                    utils.getRandomMiddle(self.rng, store[1], store[2]))
        else:
            self.winCap.leftClick(
                utils.getRandomMiddle(self.rng, store[1], store[2]))

    def startLoopIteration(self):
        """Run a single iteration of the fishing loop. Returns False if should stop."""
        if self.pause:
            return False

        frame = self.winCap.capture()
        skipRetract = False

        count = 0
        previousState = None

        while True:
            if self.pause:
                break

            count = count + 1

            state = self.winCap.getFishingState()

            self.log(f'state: {state}')

            if state == 0:  # Idle state
                # self.log('Idle???')
                pass
            elif state == 1:
                # self.log("Starting fishing")
                pass
            elif state == 3:
                # self.log("Fishing")
                pass
            elif state == 4:
                # self.log("Fish appears")
                pass
            elif state == 5:
                self.onReel()
                self.winCap.press(0x20, single=True)
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
                self.log("Rotten luck")
                skipRetract = True
                break
            elif state == 15:  # VIP fish states
                if previousState != 15:
                    self.log('Got giant fish')
                    self.winCap.press(0x20, single=True)
            elif state == 16:
                self.log('Waiting for giant fish')
            elif state == 17:
                self.log('Giant fish trying to get away')
                self.winCap.press(0x20, single=True)
            elif state == 18:
                self.log('Got a hold of giant fish')
            elif state == 20:
                self.log('Got giant fish')
                self.wait('5s')
            elif state == 24:
                self.log('Giant fish stunned')
                self.winCap.press(0x20, single=True)
            elif state == 25:
                self.log('Giant fish not stunned')

            frame1 = self.winCap.capture()
            if self.vision.seeFishingButton(frame1):
                skipRetract = True
                break

            if previousState != state:
                previousState = state
            self.wait('fishBiting')

        self.correct(skipRetract)

        if self.pause:
            return False

        if self.vision.seeBrokenRod(frame):
            self.onBrokenRod()
            self.repair()
            self.winCap.press(0x4F)
            self.wait('slow')
            self.winCap.press(0x4B)

        self.wait('fast')
        return True

    def loopInThread(self, stopEvent):
        while True:
            if not self.startLoopIteration():
                stopEvent.set()
                break

    def startLoop(self, stopEvent=None):
        if stopEvent is not None:
            task = threading.Thread(
                target=self.loopInThread, args=(stopEvent,), daemon=True)
            task.start()
            controlListener = threading.Thread(
                target=self.checkControls, daemon=True)
            controlListener.start()
            stopEvent.wait()

            self.taskQueue.put({
                "window_name": self.winCap.windowName,
                "command": "STOP_LISTENING"
            })
        else:
            while True:
                if not self.startLoopIteration():
                    break

    def checkControls(self):
        while True:
            payload = self.taskQueue.get()
            window_name = payload['window_name']
            command = payload['command']

            if window_name != self.winCap.windowName:
                continue

            if command == "GET_BALO_ADDRESS":
                self.resultQueue.put({
                    "window_name": self.winCap.windowName,
                    "command": "BALO_ADDRESS",
                    "data": self.winCap.baloAddr
                })
            elif command == "STOP_LISTENING":
                break
            elif command == "UPDATE_FISHING_VARIABLES":
                self.fishingVariables = payload['data']
                self.log(f"Updated fishing variables: {self.fishingVariables}")


def main():
    bot = Autofishing()

    theThreads = []

    try:
        for theThread in theThreads:
            theThread.start()

        # bot.prepare()

        # self.log('Auto fishing will be started after 2 seconds')
        # time.sleep(2)

        bot.startLoop()
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        for theThread in theThreads:
            theThread.stop()


if __name__ == '__main__':
    main()
