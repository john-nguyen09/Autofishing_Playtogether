import win32gui
import win32ui
import win32api
import win32con
from ctypes import windll
from PIL import Image
import cv2
from scipy.spatial.distance import euclidean
from imutils import perspective
from imutils import contours
import numpy as np
import imutils
import time

ORIGINAL_WIDTH = 998


# Pixel value in store button
ConstStore = (234.3574074074074, 194.31450617283951, 83.9050925925926, 0.0)
ConstStore2 = (152.84799382716048, 201.46435185185186, 177.07577160493827, 0.0)
# Pixel value in Bag
ConstBag = (66.0, 65.0, 228.0, 0.0)
hwnd = win32gui.FindWindow(None, 'LDPlayer')
hwndChild = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
left, top, right, bot = win32gui.GetWindowRect(hwnd)
claim_sprite = None
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
                print('Complete')
                return win32gui.GetCursorPos()
        cv2.waitKey(100)


def GetImage(pt, frame):
    '''Croping around fishing buoy area image that from capture frame'''
    x = pt[0]-left
    y = pt[1]-top
    crop = frame[y-100:y+100, x-100:x+100]
    return crop


def getPixVal(pt, frame):
    '''Get pixel value the exclamation mark'''
    x = pt[0]-left
    y = pt[1]-top
    crop = frame[y-2:y+2, x-2:x+2]
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


def BrokenRope(frame):
    '''Broken rope check'''
    crop = frame[311-3:311+3, 916-3:916+3]
    value = cv2.mean(crop)
    if value == ConstBag:
        return True
    else:
        return False


def BrokenRod(frame):
    '''Broken rod check'''
    crop = frame[264:312, 400:563]
    value = cv2.mean(crop)
    if value[0] > 218 and value[1] > 218 and value[2] > 218:
        return True
    else:
        return False


def Repair(stt):
    '''Repair broken rod'''
    Press(0x42)  # press b
    time.sleep(1)
    Press(0x43)  # press c
    time.sleep(1)
    Press(stt)  # press stt
    time.sleep(1)
    Press(0x4F)
    time.sleep(2)
    Press(0x4F)
    time.sleep(2)


def Incorrect():
    '''Incorrect size procedure '''
    print('Incorrect size')
    Press(0x20)
    time.sleep(1.5)
    print('Continue...')
    Press(0x4B)
    time.sleep(10)


def Getinput():
    list = [0]
    for i in range(1, 5):
        print('Do you want fishing size', i, '?(y/n):')
        temp = input()
        if temp == 'y':
            list.append(i)
    print('Which fishing rod be used ?(1 or 2,..):')
    stt = int(input())
    detectClick()
    print('Select fishing buoy: ')
    pt = detectClick()
    print('Select exclamation mark location: ')
    pt1 = detectClick()
    return list, pt, pt1, stt


def Correct(stt):
    print('''It's real!''')
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
        elif BrokenRope(frame2):
            print('Broken rope')
            time.sleep(0.5)
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
        Repair(stt)
        Press(0x4F)
        time.sleep(1.5)
        Press(0x4B)
    time.sleep(10)


def NormaliseImg(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.Canny(img, 50, 200)

    return img


def LoadSprite(path):
    img = cv2.imread(path)
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
    global claim_sprite

    claim_sprite = LoadSprite('claim.png')
    list, pt, pt1, stt = Getinput()

    if stt == 1:
        sttcode = 0x31
    elif stt == 2:
        sttcode = 0x32
    elif stt == 3:
        sttcode = 0x32
    print('Auto fishing will be started after 2 seconds')
    time.sleep(2)

    while True:
        frame = Capture(hwnd)
        image = GetImage(pt, frame)
        dim = (400, 400)
        image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
        # cnt,area,size = MeansuringSize(image)
        size = 1
        # Draw(cnt,image)
        if size != 0:
            print('Predict size: ', size)
        if size not in list:
            Incorrect()
        elif size != 0:
            preval = getPixVal(pt1, frame)
            count = 0

            while True:
                count = count + 1
                ints = rng.integers(low=90, high=140, size=1)

                if count >= ints[0]:
                    Wait('ok')
                    break

                frame1 = Capture(hwnd)
                image = GetImage(pt, frame1)
                dim = (400, 400)
                image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
                # cnt,area1,size = MeansuringSize(image)
                size = 1
                # Draw(cnt,image)
                currentVal = getPixVal(pt1, frame1)

                def check(currentVal, preval):
                    '''It's real fish if pixel value be changed'''
                    threshold = 3.4
                    diff = np.abs(np.subtract(currentVal, preval))
                    print('currentVal,preVal,diff,result', currentVal, preval, diff, diff >= threshold)
                    return diff >= threshold
                if check(currentVal,preval) and currentVal>100 and currentVal<230:
                    break

                preval = currentVal
                if BrokenRope(frame):
                    cv2.waitKey(500)
                    Press(0x4B)

                Wait('ok')

            print(currentVal)
            Correct(sttcode)
        if BrokenRope(frame):
            cv2.waitKey(500)
            Press(0x4B)

        Wait('fast')


if __name__ == '__main__':
    main()
