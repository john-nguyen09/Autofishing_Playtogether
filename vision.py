import utils
import cv2


class Vision:
    def __init__(self, winCap):
        self.winCap = winCap

        self.claimSprite = utils.loadSprite('claim.png')
        self.fishingButtonSprite = utils.loadSprite('fish-button.png')
        self.brokenRodTitleVi = utils.loadSprite('repair-rod-title-vi.png')
        self.brokenRodTitleEn = utils.loadSprite('repair-rod-title-en.png')
        self.brokenRodTextVi = utils.loadSprite('repair-rod-text-vi.png')
        self.brokenRodTextEn = utils.loadSprite('repair-rod-text-en.png')
        self.openVi = utils.loadSprite('open-vi.png')
        self.openAllVi = utils.loadSprite('open-all-vi.png')
        self.ok = utils.loadSprite('ok.png')

    def seeBrokenRod(self, frame):
        detectedVi = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.brokenRodTitleVi, self.brokenRodTextVi]]
        detectedEn = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.brokenRodTitleEn, self.brokenRodTextEn]]

        return all(match >= 0.5 for (match, _, _) in detectedVi) or all(match >= 0.5 for (match, _, _) in detectedEn)

    def seeFishingButton(self, frame):
        fishingDetected = utils.detectSprite(
            frame.getNormed(), self.fishingButtonSprite, r=self.winCap.ratio)

        return fishingDetected[0] >= 0.4

    def seeStoreButton(self, frame):
        storeDetected = utils.detectSprite(
            frame.getNormed(), self.claimSprite, r=self.winCap.ratio)

        return storeDetected[0] >= 0.6

    def seeCardsToOpen(self, frame):
        openDetected = utils.detectSprite(
            frame.getNormed(), self.openVi, r=self.winCap.ratio)

        return openDetected[0] >= 0.6, openDetected[1], openDetected[2]

    def seeOpenAll(self, frame):
        openAllDetected = utils.detectSprite(
            frame.getNormed(), self.openAllVi, r=self.winCap.ratio)

        return openAllDetected[0] >= 0.6, openAllDetected[1], openAllDetected[2]

    def seeOk(self, frame):
        okDetected = utils.detectSprite(
            frame.getNormed(), self.ok, r=self.winCap.ratio)

        print('okDetected', okDetected)

        return okDetected[0] >= 0.6, okDetected[1], okDetected[2]
