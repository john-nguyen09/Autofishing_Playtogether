import cv2
import os


def normaliseImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.Canny(img, 50, 200)

    return img


def loadSprite(path):
    img = cv2.imread(os.path.join('assets', path))
    img = normaliseImg(img)
    w, h = img.shape[::-1]

    return (img, w, h)


def detectSprite(screenshot_normed, sprite, r=1):
    (sprite_img, w, h) = sprite
    sprite_img = cv2.resize(sprite_img, (0, 0), fx=r, fy=r)

    result = cv2.matchTemplate(
        screenshot_normed, sprite_img, cv2.TM_CCOEFF_NORMED)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    start = (int(maxLoc[0] / r), int(maxLoc[1] / r))
    end = (int((maxLoc[0] + w) / r), int((maxLoc[1] + h) / r))

    return (maxVal, start, end)
