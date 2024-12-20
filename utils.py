import cv2
from sprite import Sprite


def normaliseImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return img


def loadSprite(path):
    return Sprite(path)


def detectSprite(screenshotNormed, sprite, r=1):
    result = cv2.matchTemplate(
        screenshotNormed, sprite.getRatio(r), cv2.TM_CCOEFF_NORMED)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    start = (int(maxLoc[0]), int(maxLoc[1]))
    end = (int((maxLoc[0] + (sprite.w * r))), int((maxLoc[1] + (sprite.h * r))))

    return (maxVal, start, end)


def getRandomMiddle(rng, start, end):
    ints = rng.integers(low=-10, high=10, size=2)
    randomX = ints[0] / 100
    randomY = ints[1] / 100
    x = min(end[0], start[0])
    y = min(end[1], start[1])
    xMid = x + (abs(end[0] - start[0]) / 2)
    yMid = y + (abs(end[1] - start[1]) / 2)
    xDist = abs(end[0] - start[0]) / 2
    yDist = abs(end[1] - start[1]) / 2

    return int(xMid + (xDist * randomX)), int(yMid + (yDist * randomY))
