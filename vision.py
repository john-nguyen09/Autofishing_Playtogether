import utils


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
        self.yes = utils.loadSprite('yes.png')
        self.fullBag = utils.loadSprite('full-bag.png')

        self.clickHere1 = utils.loadSprite('click-here-1.png')
        self.clickHere2 = utils.loadSprite('click-here-2.png')
        self.clickHere3 = utils.loadSprite('click-here-3.png')
        self.clickHere4 = utils.loadSprite('click-here-4.png')

        self.mine = utils.loadSprite('mine.png')
        self.gottaAimAndHit = utils.loadSprite('gotta-aim-and-hit.png')
        self.hitMissing = utils.loadSprite('hit-missing.png')
        self.hitTheVoid = utils.loadSprite('hit-the-void.png')

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

    def seeStoreButton(self, frame):
        storeDetected = utils.detectSprite(
            frame.getNormed(), self.claimSprite, r=self.winCap.ratio)

        # print('storeDetected', storeDetected)

        return storeDetected[0] >= 0.7

    def seeCardsToOpen(self, frame):
        openDetected = utils.detectSprite(
            frame.getNormed(), self.openVi, r=self.winCap.ratio)

        # print('openDetected', openDetected)

        return openDetected[0] >= 0.83, openDetected[1], openDetected[2]

    def seeOpenAll(self, frame):
        openAllDetected = utils.detectSprite(
            frame.getNormed(), self.openAllVi, r=self.winCap.ratio)

        # print('openAllDetected', openAllDetected)

        return openAllDetected[0] >= 0.7, openAllDetected[1], openAllDetected[2]

    def seeOk(self, frame):
        okDetected = utils.detectSprite(
            frame.getNormed(), self.ok, r=self.winCap.ratio)

        # print('okDetected', okDetected)

        return okDetected[0] >= 0.9, okDetected[1], okDetected[2]

    def seeBunchOfClickHere(self, frame):
        detectedClickHere = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.clickHere1, self.clickHere2, self.clickHere3, self.clickHere4]]

        # print('detectedClickHere', detectedClickHere)

        for (match, start, end) in detectedClickHere:
            if match >= 0.7:
                return True, start, end

        return False, None, None

    def seeYes(self, frame):
        yesDetected = utils.detectSprite(
            frame.getNormed(), self.yes, r=self.winCap.ratio)

        # print('yesDetected', yesDetected)

        return yesDetected[0] >= 0.85, yesDetected[1], yesDetected[2]

    def seeFullBag(self, frame):
        fullBagDetected = utils.detectSprite(
            frame.getNormed(), self.fullBag, r=self.winCap.ratio)

        # print('fullBagDetected', fullBagDetected)

        return fullBagDetected[0] >= 0.7, fullBagDetected[1], fullBagDetected[2]

    def seeMine(self, frame):
        mineDetected = utils.detectSprite(
            frame.getNormed(), self.mine, r=self.winCap.ratio)

        # print('mineDetected', mineDetected)

        return mineDetected[0] >= 0.55, mineDetected[1], mineDetected[2]

    def seeCannotMine(self, frame):
        cantHitDtected = [utils.detectSprite(frame.getNormed(), sprite, r=self.winCap.ratio) for sprite in [
            self.hitMissing, self.hitTheVoid, self.gottaAimAndHit]]

        print(list(map(lambda detected: detected[0], cantHitDtected)))

        for (match, start, end) in cantHitDtected:
            if match >= 0.7:
                return True, start, end

        return False, None, None
