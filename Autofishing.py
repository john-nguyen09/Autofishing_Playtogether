import win32gui
import win32api
import cv2
from scipy.spatial.distance import euclidean
from imutils import perspective
import numpy as np
import imutils
import time
import os
from windowcapture import WindowCapture
import traceback


ORIGINAL_WIDTH = 1247


claim_sprite = None
fishing_button_sprite = None
broken_rod_title = None
broken_rod_text = None
rng = np.random.default_rng(seed=6994420)



def show_images(images):
    '''Showing around fishing buoy area image'''
    for i, img in enumerate(images):
        cv2.imshow('Fishing buoy area', img)
    cv2.waitKey(1)


def detectClick():
    """Detects and returns the click position"""
    state_left = win32api.GetKeyState(0x01)
    print("Select position")
    while True:
        a = win32api.GetKeyState(0x01)
        if a != state_left:  # button state changed
            state_left = a
            if a < 0:
                return win32gui.GetCursorPos()
        cv2.waitKey(100)


def MeansuringSize(image):
    '''Get image and return fish shadow, area of fish shadow, Size'''
    # Preprocess
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    temp = cv2.mean(gray)
    avg = temp[0]
    if avg > 140 and avg < 155:
        ret, thresh2 = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY_INV)
    elif avg >= 155:
        ret, thresh2 = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    elif avg > 57 and avg < 90:
        ret, thresh2 = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    elif avg > 90 and avg < 140:
        ret, thresh2 = cv2.threshold(gray, 65, 255, cv2.THRESH_BINARY_INV)
    else:
        ret, thresh2 = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY_INV)
    edged = cv2.Canny(thresh2, 10, 100)
    edged = cv2.dilate(edged, None, iterations=1)
    edged = cv2.erode(edged, None, iterations=1)

    # Detect fish shadow in image
    cnts = cv2.findContours(
        edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = [x for x in cnts if cv2.contourArea(x) > 300]
    if cnts:
        for cnt in cnts:
            area = cv2.contourArea(cnt)
            if area < 420 and area > 300:
                return cnt, area, 1
            elif area < 1100 and area > 700:
                return cnt, area, 2
            elif area < 2100 and area > 1300:
                return cnt, area, 3
            elif area > 2100:
                return cnt, area, 4
            else:
                return cnts, area, 0
    else:
        return cnts, 10.0, 0


def Draw(cnts, image):
    '''Draw fish shadow in image'''
    for cnt in cnts:
        box = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(box)
        box = np.array(box, dtype="int")
        box = perspective.order_points(box)
        (tl, tr, br, bl) = box
        cv2.drawContours(image, [box.astype("int")], -1, (0, 0, 255), 2)
        mid_pt_horizontal = (
            tl[0] + int(abs(tr[0] - tl[0])/2), tl[1] + int(abs(tr[1] - tl[1])/2))
        mid_pt_verticle = (tr[0] + int(abs(tr[0] - br[0])/2),
                           tr[1] + int(abs(tr[1] - br[1])/2))
        wid = euclidean(tl, tr)
        ht = euclidean(tr, br)
    show_images([image])


def detect_sprite(screenshot_normed, sprite, r=1):
    (sprite_img, w, h) = sprite
    sprite_img = cv2.resize(sprite_img, (0, 0), fx=r, fy=r)

    result = cv2.matchTemplate(
        screenshot_normed, sprite_img, cv2.TM_CCOEFF_NORMED)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    start = (int(maxLoc[0] / r), int(maxLoc[1] / r))
    end = (int((maxLoc[0] + w) / r), int((maxLoc[1] + h) / r))

    return (maxVal, start, end)


def SeeFishingButton(win_cap, frame):
    global fishing_button_sprite

    frame_normed = NormaliseImg(frame)
    fishing_detected = detect_sprite(frame_normed, fishing_button_sprite, r=win_cap.ratio)

    print('fishing_detected[0]', fishing_detected[0])

    return fishing_detected[0] >= 0.4


def Storing(win_cap, frame):
    global claim_sprite

    '''Storing button appear, isn't it'''

    frame_normed = NormaliseImg(frame)
    claim_detected = detect_sprite(frame_normed, claim_sprite, r=win_cap.ratio)

    return claim_detected[0] >= 0.6

    crop = frame[432:486, 630:750]
    crop2 = frame[432:486, 710:830]
    # cv2.imshow('asdf', crop)
    # cv2.imshow('asdf2', crop2)
    value = cv2.mean(crop)
    value2 = cv2.mean(crop2)
    # cv2.waitKey(2000)
    # print(value, value2)
    if value == ConstStore or value2 == ConstStore2:
        return True
    else:
        return False


def BrokenRod(win_cap, frame):
    global broken_rod_title_vi, broken_rod_title_en, broken_rod_text_vi, broken_rod_text_en

    frame_normed = NormaliseImg(frame)
    detected_vi = [detect_sprite(frame_normed, sprite, r=win_cap.ratio) for sprite in [broken_rod_title_vi, broken_rod_text_vi]]
    detected_en = [detect_sprite(frame_normed, sprite, r=win_cap.ratio) for sprite in [broken_rod_title_en, broken_rod_text_en]]

    print('detected_vi, detected_en', detected_vi, detected_en)

    return all(match >= 0.5 for (match, _, _) in detected_vi) or all(match >= 0.5 for (match, _, _) in detected_en)

    '''Broken rod check'''
    crop = frame[264:312, 400:563]
    value = cv2.mean(crop)
    if value[0] > 218 and value[1] > 218 and value[2] > 218:
        return True
    else:
        return False


def Repair(win_cap):
    '''Repair broken rod'''
    win_cap.press(0x56)  # press v
    time.sleep(1)
    win_cap.press(0x56)  # press v
    time.sleep(1)


def Incorrect(win_cap):
    '''Incorrect size procedure '''
    print('Incorrect size')
    win_cap.press(0x20)
    time.sleep(1.5)
    print('Continue...')
    win_cap.press(0x4B)
    time.sleep(10)


def PixelValuesChanged(prev, curr):
    norm_prev = prev.astype(np.int16).ravel()
    norm_curr = curr.astype(np.int16).ravel()
    diff = np.subtract(norm_curr, norm_prev)
    percentage = (np.mean(np.abs(diff) > 2) * 100)
    percentage_negative = (np.mean(diff < 0) * 100)
    result = percentage >= 50
    result_negative = percentage_negative >= 25 and percentage > 33

    print('norm_prev, norm_curr, diff, percentage, percentage_negative, result, result_negative', norm_prev, norm_curr, diff, percentage, percentage_negative, result, result_negative)

    return result or result_negative


def IsInside(pt, rect):
    (pt1, pt2) = rect

    if pt[0] < pt1[0] or pt[0] > pt2[0]:
        return False

    if pt[1] < pt1[1] or pt[1] > pt2[1]:
        return False

    return True


def Getinput(win_cap):
    left, top, right, bot = win_cap.left, win_cap.top, win_cap.right, win_cap.bot

    print('Select exclamation mark location: ')
    while True:
        pt1 = detectClick()

        if IsInside(pt1, ((left, top), (right, bot))):
            break

    return win_cap.toRelative(pt1)


def Correct(win_cap, skipRetract):
    print('''It's real!''')
    if not skipRetract:
        win_cap.press(0x20)
    count = 0
    while True:
        frame2 = win_cap.capture()
        if Storing(win_cap, frame2):
            print('Storing')
            Wait('ok')
            win_cap.press(0x4C)  # press(L)
            Wait('slow')
            break
        elif SeeFishingButton(win_cap, frame2):
            break
        else:
            count = count + 1
            ints = rng.integers(low=8, high=12, size=1)
            if count >= ints[0]:
                break

        Wait('slow')

    print('Continue...')
    win_cap.press(0x4B)
    time.sleep(2)
    frame2 = win_cap.capture()
    if BrokenRod(win_cap, frame2):
        Repair(win_cap)
        win_cap.press(0x4F)
        time.sleep(1.5)
        win_cap.press(0x4B)
    time.sleep(10)


def NormaliseImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.Canny(img, 50, 200)

    return img


def LoadSprite(path):
    img = cv2.imread(os.path.join('assets', path))
    img = NormaliseImg(img)
    w, h = img.shape[::-1]

    return (img, w, h)


WaitFuncs = {
    'veryslow': lambda : rng.integers(low=1870, high=2720, size=1)[0],
    'slow': lambda : rng.integers(low=829, high=1362, size=1)[0],
    'fast': lambda : rng.integers(low=202, high=397, size=1)[0],
    'ok': lambda : rng.integers(low=420, high=521, size=1)[0],
}
def Wait(duration):
    return cv2.waitKey(WaitFuncs[duration]())


def main():
    global claim_sprite, fishing_button_sprite, broken_rod_title_vi, broken_rod_title_en, broken_rod_text_vi, broken_rod_text_en

    win_cap = WindowCapture.find_and_init()
    win_cap.capture() # To calculate rect

    the_threads = []

    try:
        for the_thread in the_threads:
            the_thread.start()

        claim_sprite = LoadSprite('claim.png')
        fishing_button_sprite = LoadSprite('fish-button.png')
        broken_rod_title_vi = LoadSprite('repair-rod-title-vi.png')
        broken_rod_title_en = LoadSprite('repair-rod-title-en.png')
        broken_rod_text_vi = LoadSprite('repair-rod-text-vi.png')
        broken_rod_text_en = LoadSprite('repair-rod-text-en.png')
        pt1 = Getinput(win_cap)

        print('Auto fishing will be started after 2 seconds')
        time.sleep(2)

        while True:
            frame = win_cap.capture()
            skipRetract = False

            prevalRaw = win_cap.getPixVal(pt1, frame, raw=True)
            count = 0

            while True:
                count = count + 1
                ints = rng.integers(low=180, high=289, size=1)

                if count >= ints[0]:
                    Wait('ok')
                    break

                frame1 = win_cap.capture()
                currentVal = win_cap.getPixVal(pt1, frame1)
                currentValRaw = win_cap.getPixVal(pt1, frame1, raw=True)

                if PixelValuesChanged(prevalRaw, currentValRaw) and currentVal>100 and currentVal<230:
                    break

                prevalRaw = currentValRaw
                if SeeFishingButton(win_cap, frame1):
                    skipRetract = True
                    break

                Wait('fast')

            Correct(win_cap, skipRetract)

            if BrokenRod(win_cap, frame):
                Repair()
                win_cap.press(0x4F)
                Wait('veryslow')
                win_cap.press(0x4B)

            Wait('fast')
    except Exception as e:
        print(e)
        print(traceback.format_exc())

        for the_thread in the_threads:
            the_thread.stop()


if __name__ == '__main__':
    main()
