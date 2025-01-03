import utils
import cv2


class Frame:
    matrix = None
    normed = None

    def setMatrix(self, matrix, pos = (0, 0), width = None, height = None):
        self.matrix = matrix
        self.normed = None
        self.pos = pos
        self.width = width
        self.height = height

        self.origin = self.pos
        if self.width and self.height:
            self.origin = (int(self.pos[0] - self.width / 2), int(self.pos[1] - self.height / 2))

    def getNormed(self):
        if self.normed is None:
            self.normed = utils.normaliseImg(self.matrix)

        return self.normed

    def getPixVal(self, pt, raw=False):
        x = pt[0] - self.origin[0]
        y = pt[1] - self.origin[1]
        crop = self.matrix[y-1:y+1, x-1:x+1]

        if raw:
            return crop

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        avg = cv2.mean(gray)

        return avg[0]
