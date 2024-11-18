import utils


class Frame:
    matrix = None
    normed = None

    def setMatrix(self, matrix):
        self.matrix = matrix
        self.normed = None

    def getNormed(self):
        if self.normed is None:
            self.normed = utils.normaliseImg(self.matrix)

        return self.normed
