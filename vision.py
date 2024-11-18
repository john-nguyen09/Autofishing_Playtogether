import utils


class Vision:
    claimSprite = None
    fishingButtonSprite = None
    brokenRodTitleVi = None
    brokenRodTitleEn = None
    brokenRodTextVi = None
    brokenRodTextEn = None
    winCap = None

    def __init__(self, winCap):
        self.winCap = winCap

        self.claimSprite = utils.loadSprite('claim.png')
        self.fishingButtonSprite = utils.loadSprite('fish-button.png')
        self.brokenRodTitleVi = utils.loadSprite('repair-rod-title-vi.png')
        self.brokenRodTitleEn = utils.loadSprite('repair-rod-title-en.png')
        self.brokenRodTextVi = utils.loadSprite('repair-rod-text-vi.png')
        self.brokenRodTextEn = utils.loadSprite('repair-rod-text-en.png')

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

        print('storeDetected', storeDetected)

        return storeDetected[0] >= 0.6
