import utils
import constants as cs
import time
import cv2
from datetime import datetime, timezone


class Vision:
    def __init__(self, winCap, message_queue=None):
        self.winCap = winCap
        self.message_queue = message_queue

        self.claimSprite = utils.loadSprite('claim.png')
        self.storeNowBigSprite = utils.loadSprite('store-now-big.png')
        self.storeNowSmallSprite = utils.loadSprite('store-now-small.png')
        self.sellNowSprite = utils.loadSprite('sell-now.png')
        self.fishingButtonSprite = utils.loadSprite('fish-button.png')
        self.brokenRodTitleVi = utils.loadSprite('repair-rod-title-vi.png')
        self.brokenRodTitleEn = utils.loadSprite('repair-rod-title-en.png')
        self.brokenRodTextVi = utils.loadSprite('repair-rod-text-vi.png')
        self.brokenRodTextEn = utils.loadSprite('repair-rod-text-en.png')
        self.openVi = utils.loadSprite('open-vi.png')
        self.openAllVi = utils.loadSprite('open-all-vi.png')
        self.ok = utils.loadSprite('ok.png')
        self.yes = utils.loadSprite('yes.png')
        self.fullBag = utils.loadSprite('full-bag.png')
        self.cantFishForTheDay = utils.loadSprite('cant-fish-for-the-day.png')

        self.clickHere1 = utils.loadSprite('click-here-1.png')
        self.clickHere2 = utils.loadSprite('click-here-2.png')
        self.clickHere3 = utils.loadSprite('click-here-3.png')
        self.clickHere4 = utils.loadSprite('click-here-4.png')

        self.mine = utils.loadSprite('mine.png')
        self.gottaAimAndHit = utils.loadSprite('gotta-aim-and-hit.png')
        self.hitMissing = utils.loadSprite('hit-missing.png')
        self.hitTheVoid = utils.loadSprite('hit-the-void.png')

    def log(self, message):
        """Log message to both console and GUI if message_queue is available"""
        print(message)
        if self.message_queue:
            self.message_queue.put(f"{message}\n")

    def seeBrokenRod(self, frame):
        detectedVi = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.brokenRodTitleVi, self.brokenRodTextVi]]
        detectedEn = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.brokenRodTitleEn, self.brokenRodTextEn]]

        return all(match >= 0.7 for (match, _, _) in detectedVi) or all(match >= 0.7 for (match, _, _) in detectedEn)

    def seeFishingButton(self, frame):
        fishingDetected = utils.detectSprite(
            frame.getNormed(), self.fishingButtonSprite, r=self.winCap.ratio)

        return fishingDetected[0] >= 0.7

    def seeSellNowButton(self, frame):
        sellNowDetected = utils.detectSprite(
            frame.getNormed(), self.sellNowSprite, r=self.winCap.ratio)

        return sellNowDetected[0] >= 0.7, sellNowDetected[1], sellNowDetected[2]

    def seeStoreButton(self, frame):
        storeNowBigDetected = utils.detectSprite(
            frame.getNormed(), self.storeNowBigSprite, r=self.winCap.ratio)
        storeNowSmallDetected = utils.detectSprite(
            frame.getNormed(), self.storeNowSmallSprite, r=self.winCap.ratio)

        if storeNowBigDetected[0] >= 0.7:
            return storeNowBigDetected

        if storeNowSmallDetected[0] >= 0.7:
            return storeNowSmallDetected

        # self.log(f'storeDetected: {storeDetected}')

        return False, None, None

    def seeCardsToOpen(self, frame):
        openDetected = utils.detectSprite(
            frame.getNormed(), self.openVi, r=self.winCap.ratio)

        # self.log(f'openDetected: {openDetected}')

        return openDetected[0] >= 0.83, openDetected[1], openDetected[2]

    def seeOpenAll(self, frame):
        openAllDetected = utils.detectSprite(
            frame.getNormed(), self.openAllVi, r=self.winCap.ratio)

        # self.log(f'openAllDetected: {openAllDetected}')

        return openAllDetected[0] >= 0.7, openAllDetected[1], openAllDetected[2]

    def seeOk(self, frame):
        okDetected = utils.detectSprite(
            frame.getNormed(), self.ok, r=self.winCap.ratio)

        self.log(f'okDetected: {okDetected}')

        return okDetected[0] >= 0.9, okDetected[1], okDetected[2]

    def seeBunchOfClickHere(self, frame):
        detectedClickHere = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.clickHere1, self.clickHere2, self.clickHere3, self.clickHere4]]

        # self.log(f'detectedClickHere: {detectedClickHere}')

        for (match, start, end) in detectedClickHere:
            if match >= 0.7:
                return True, start, end

        return False, None, None

    def seeYes(self, frame):
        yesDetected = utils.detectSprite(
            frame.getNormed(), self.yes, r=self.winCap.ratio)

        self.log(f'yesDetected: {yesDetected}')

        return yesDetected[0] >= 0.7, yesDetected[1], yesDetected[2]

    def seeFullBagOrCantFish(self, frame):
        fullBagDetected = utils.detectSprite(
            frame.getNormed(), self.fullBag, r=self.winCap.ratio)
        cantFishDetected = utils.detectSprite(
            frame.getNormed(), self.cantFishForTheDay, r=self.winCap.ratio)

        if cantFishDetected[0] >= 0.7:
            return cantFishDetected[0] >= 0.7, cantFishDetected[1], cantFishDetected[2]

        # self.log(f'fullBagDetected: {fullBagDetected}')

        return fullBagDetected[0] >= 0.7, fullBagDetected[1], fullBagDetected[2]

    def seeMine(self, frame):
        mineDetected = utils.detectSprite(
            frame.getNormed(), self.mine, r=self.winCap.ratio)

        # self.log(f'mineDetected: {mineDetected}')

        return mineDetected[0] >= 0.55, mineDetected[1], mineDetected[2]

    def seeCannotMine(self, frame):
        cantHitDtected = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.hitMissing, self.hitTheVoid, self.gottaAimAndHit]]

        detected_values = list(
            map(lambda detected: detected[0], cantHitDtected))
        if self.message_queue:
            self.message_queue.put(
                f"Cant Hit Detection values: {detected_values}\n")
        else:
            print(f"Cant Hit Detection values: {detected_values}")

        for (match, start, end) in cantHitDtected:
            if match >= 0.7:
                return True, start, end

        return False, None, None

    def captureAndGetFishColour(self):
        fishColourName = None
        lastFrame = None
        isCrown = False
        lastColourAsKey = None
        lastCrownColourAsKey = None

        for i in range(3):
            frame = self.winCap.capture()
            colour = self.winCap.colourAt(
                frame, cs.CAUGHT_FISH_COLOUR_COORDS)
            colourAsKey = f"{colour[0]}, {colour[1]}, {colour[2]}"

            if colourAsKey in cs.FISH_COLOURS:
                fishColourName = cs.FISH_COLOURS[colourAsKey]

            lastColourAsKey = colourAsKey
            lastFrame = frame

            if fishColourName is not None:
                colour = self.winCap.colourAt(
                    frame, cs.CAUGHT_FISH_CROWN_COORDS)
                colourAsKey = f"{colour[0]}, {colour[1]}, {colour[2]}"

                if colourAsKey in cs.CROWN_COLOURS:
                    isCrown = True
                lastCrownColourAsKey = colourAsKey
                break

            time.sleep(0.1)


        self.log(f"colour: {colour}, lastColourAsKey: {lastColourAsKey}, lastCrownColourAsKey: {lastCrownColourAsKey}, fishColourName: {fishColourName}, isCrown: {isCrown}")
        if fishColourName is None:
            matrix = lastFrame.matrix.copy()
            matrix = cv2.circle(matrix, cs.CAUGHT_FISH_COLOUR_COORDS, 5, (0, 0, 255), 3)
            matrix = cv2.circle(matrix, cs.CAUGHT_FISH_CROWN_COORDS, 5, (0, 0, 255), 3)
            cv2.imwrite(f"data2/{int(datetime.now(timezone.utc).timestamp())}.png", matrix)
            with open(f"data2/{int(datetime.now(timezone.utc).timestamp())}.txt", "w") as f:
                f.write(f"colour: {colour}\n")

        return frame, fishColourName, isCrown
