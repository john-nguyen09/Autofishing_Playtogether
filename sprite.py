import cv2
import utils
import os


class Sprite:
    def __init__(self, path):
        self.img = cv2.imread(os.path.join('assets', path))
        self.img = utils.normaliseImg(self.img)
        self.w, self.h = self.img.shape[::-1]
        self.ratioMapping = {}

    def getRatio(self, r):
        if not r in self.ratioMapping:
            self.ratioMapping[r] = cv2.resize(self.img, (0, 0), fx=r, fy=r)

        return self.ratioMapping[r]
