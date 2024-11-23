import cv2
import os


def normaliseImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return img


def loadSprite(path):
    img = cv2.imread(os.path.join('assets', path))
    img = normaliseImg(img)
    w, h = img.shape[::-1]

    return (img, w, h)


def detectSprite(screenshotNormed, sprite, r=1):
    (spriteImg, w, h) = sprite
    spriteImg = cv2.resize(spriteImg, (0, 0), fx=r, fy=r)

    result = cv2.matchTemplate(
        screenshotNormed, spriteImg, cv2.TM_CCOEFF_NORMED)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    start = (int(maxLoc[0]), int(maxLoc[1]))
    end = (int((maxLoc[0] + (w * r))), int((maxLoc[1] + (h * r))))

    return (maxVal, start, end)


def getRandomMiddle(rng, start, end):
    randomX = rng.integers(low=-8, high=8, size=1)[0]
    randomY = rng.integers(low=-8, high=8, size=1)[0]
    x = min(end[0], start[0])
    y = min(end[1], start[1])
    return x + (abs(end[0] - start[0]) / 2) + randomX, y + (abs(end[1] - start[1]) / 2) + randomY
