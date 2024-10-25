import win32gui
import win32ui
import win32api
import win32con
from ctypes import windll
from PIL import Image
import cv2
from scipy.spatial.distance import euclidean
from imutils import perspective
import numpy as np
import imutils
import time
import os


ORIGINAL_WIDTH = 1247


# Pixel value in store button
ConstStore = (234.3574074074074, 194.31450617283951, 83.9050925925926, 0.0)
ConstStore2 = (152.84799382716048, 201.46435185185186, 177.07577160493827, 0.0)
# Pixel value in Bag
ConstBag = (66.0, 65.0, 228.0, 0.0)
hwnd = win32gui.FindWindow(None, 'LDPlayer')
hwndChild = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
left, top, right, bot = win32gui.GetWindowRect(hwnd)
claim_sprite = None
fishing_button_sprite = None
broken_rod_title = None
broken_rod_text = None
rng = np.random.default_rng(seed=6994420)
ratio = 1
prevWidth = ORIGINAL_WIDTH


# Capture LDPlayer window when it's hidden
def Capture(hwnd):
    global prevWidth, ratio

    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w = right - left
    h = bot - top

    if w != prevWidth:
        ratio = w / ORIGINAL_WIDTH
        prevWidth = w

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

    saveDC.SelectObject(saveBitMap)

    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    temp = np.asarray(im)
    final = cv2.cvtColor(temp, cv2.COLOR_RGB2BGR)
    return final


'''def Capture(hwnd):
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    box = (left, top, right, bot)
    # Get the image of the desired section
    image = pyautogui.screenshot(region=(left, top, right-left, bot-top))
    temp= np.asarray(image)
    final = cv2.cvtColor(temp, cv2.COLOR_RGB2BGR)
    return final'''


def Press(vk_code):
    '''Press any key using win32api.Sendmessage'''
    print('vk_code', vk_code)
    win32api.SendMessage(hwndChild, win32con.WM_KEYDOWN, vk_code, 0)
    win32api.SendMessage(hwndChild, win32con.WM_KEYUP, vk_code, 0)


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


def getPixVal(pt, frame, raw=False):
    '''Get pixel value the exclamation mark'''
    x = pt[0]-left
    y = pt[1]-top
    crop = frame[y-1:y+1, x-1:x+1]

    if raw:
        return crop

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    avg = cv2.mean(gray)
    return avg[0]


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


def SeeFishingButton(frame):
    global fishing_button_sprite, ratio

    frame_normed = NormaliseImg(frame)
    fishing_detected = detect_sprite(frame_normed, fishing_button_sprite, r=ratio)

    print('fishing_detected[0]', fishing_detected[0])

    return fishing_detected[0] >= 0.4


def Storing(frame):
    global claim_sprite, ratio

    '''Storing button appear, isn't it'''

    frame_normed = NormaliseImg(frame)
    claim_detected = detect_sprite(frame_normed, claim_sprite, r=ratio)

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


def BrokenRod(frame):
    global broken_rod_title_vi, broken_rod_title_en, broken_rod_text_vi, broken_rod_text_en, ratio

    frame_normed = NormaliseImg(frame)
    detected_vi = [detect_sprite(frame_normed, sprite, r=ratio) for sprite in [broken_rod_title_vi, broken_rod_text_vi]]
    detected_en = [detect_sprite(frame_normed, sprite, r=ratio) for sprite in [broken_rod_title_en, broken_rod_text_en]]

    print('detected_vi, detected_en', detected_vi, detected_en)

    return all(match >= 0.5 for (match, _, _) in detected_vi) or all(match >= 0.5 for (match, _, _) in detected_en)

    '''Broken rod check'''
    crop = frame[264:312, 400:563]
    value = cv2.mean(crop)
    if value[0] > 218 and value[1] > 218 and value[2] > 218:
        return True
    else:
        return False


def Repair():
    '''Repair broken rod'''
    Press(0x56)  # press v
    time.sleep(1)
    Press(0x56)  # press v
    time.sleep(1)


def Incorrect():
    '''Incorrect size procedure '''
    print('Incorrect size')
    Press(0x20)
    time.sleep(1.5)
    print('Continue...')
    Press(0x4B)
    time.sleep(10)


def PixelValuesChanged(prev, curr):
    norm_prev = prev.astype(np.int16).ravel()
    norm_curr = curr.astype(np.int16).ravel()
    diff = np.subtract(norm_curr, norm_prev)
    percentage = (np.mean(np.abs(diff) > 2) * 100)
    result = percentage >= 50

    print('norm_prev, norm_curr, diff, percentage, result', norm_prev, norm_curr, diff, percentage, result)

    return result


def IsInside(pt, rect):
    (pt1, pt2) = rect

    if pt[0] < pt1[0] or pt[0] > pt2[0]:
        return False

    if pt[1] < pt1[1] or pt[1] > pt2[1]:
        return False

    return True


def Getinput():
    left, top, right, bot = win32gui.GetWindowRect(hwnd)

    print('Select exclamation mark location: ')
    while True:
        pt1 = detectClick()

        if IsInside(pt1, ((left, top), (right, bot))):
            break

    return pt1

def Correct(skipRetract):
    print('''It's real!''')
    if not skipRetract:
        Press(0x20)
    count = 0
    while True:
        frame2 = Capture(hwnd)
        if Storing(frame2):
            print('Storing')
            Wait('ok')
            Press(0x4C)  # press(L)
            Wait('slow')
            break
        elif SeeFishingButton(frame2):
            break
        else:
            count = count + 1
            ints = rng.integers(low=8, high=12, size=1)
            if count >= ints[0]:
                break

        Wait('slow')

    print('Continue...')
    Press(0x4B)
    time.sleep(2)
    frame2 = Capture(hwnd)
    if BrokenRod(frame2):
        Repair()
        Press(0x4F)
        time.sleep(1.5)
        Press(0x4B)
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
    'slow': lambda : rng.integers(low=829, high=1362, size=1)[0],
    'fast': lambda : rng.integers(low=202, high=397, size=1)[0],
    'ok': lambda : rng.integers(low=420, high=521, size=1)[0],
}
def Wait(duration):
    return cv2.waitKey(WaitFuncs[duration]())


def main():
    global claim_sprite, fishing_button_sprite, broken_rod_title_vi, broken_rod_title_en, broken_rod_text_vi, broken_rod_text_en

    claim_sprite = LoadSprite('claim.png')
    fishing_button_sprite = LoadSprite('fish-button.png')
    broken_rod_title_vi = LoadSprite('repair-rod-title-vi.png')
    broken_rod_title_en = LoadSprite('repair-rod-title-en.png')
    broken_rod_text_vi = LoadSprite('repair-rod-text-vi.png')
    broken_rod_text_en = LoadSprite('repair-rod-text-en.png')
    pt1 = Getinput()

    print('Auto fishing will be started after 2 seconds')
    time.sleep(2)

    while True:
        frame = Capture(hwnd)
        skipRetract = False

        prevalRaw = getPixVal(pt1, frame, raw=True)
        count = 0

        while True:
            count = count + 1
            ints = rng.integers(low=90, high=140, size=1)

            if count >= ints[0]:
                Wait('ok')
                break

            frame1 = Capture(hwnd)
            # Draw(cnt,image)
            currentVal = getPixVal(pt1, frame1)
            currentValRaw = getPixVal(pt1, frame1, raw=True)

            if PixelValuesChanged(prevalRaw, currentValRaw) and currentVal>100 and currentVal<230:
                break

            prevalRaw = currentValRaw
            if SeeFishingButton(frame1):
                skipRetract = True
                break

            # x = pt1[0] - left
            # y = pt1[1] - top
            # cv2.rectangle(frame1, (x-1, y-1), (x+1, y+1), (0, 0, 255), 3)
            # cv2.imshow('currentValRaw', frame1)

            Wait('fast')

        Correct(skipRetract)

        if BrokenRod(frame):
            Repair()
            Press(0x4F)
            time.sleep(1.5)
            Press(0x4B)

        Wait('fast')


if __name__ == '__main__':
    main()
