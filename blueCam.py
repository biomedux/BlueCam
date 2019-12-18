import tkinter
from tkinter import messagebox
import cv2
import PIL.Image
import PIL.ImageTk
import time
import tkinter.font as font
import os
import glob as gb # for file management
import sys

import subprocess as sub
import threading
import queue

MODE_PC = 0
MODE_PI = 1

arg = sys.argv
if len(arg) != 3:
    VIDEO = 0
    MODE = MODE_PC
else:
    VIDEO = int(arg[1])
    MODE = int(arg[2])

if MODE == MODE_PC:
    PATH = './'
    sub.run(['camNo'])
    f = open(PATH + "camNo.txt", 'r')
    VIDEO = int(f.readline()) # Get RecordexUSA Index
    f.close()
elif MODE == MODE_PI:
    PATH = '/home/pi/Desktop/'
    import socket
    import fcntl
    import struct

f = open(PATH + "setting.txt", 'r')
crop_scale = int(f.readline()) # 98
f.close()

camera_width       = 3264  #KJD190319
camera_height      = 2448
camera_frate       = 10

frame_video_width  = 1600
frame_video_height = 1200

preview_width      = 640
preview_height     = 480

still_width        = int((float(camera_width)*float(crop_scale)/100.)) #int(f.readline()) # 3264
still_height       = int((float(camera_height)*float(crop_scale)/100.)) # 2448

video_width        = int((float(frame_video_width)*float(crop_scale)/100.))
video_height       = int((float(frame_video_height)*float(crop_scale)/100.))

exposure_pi_table  = [0.0050, 0.0078, 0.0156, 0.0312, 0.0625, 0.1250, 0.2500, 0.5000, 1.0000]
exposure_pc_table  = [-8, -7, -6, -5, -4, -3, -2, -1, 0]

min_exposure       = 0
max_exposure       = 8

min_pc_focus       = 0
max_pc_focus       = 1023

min_pi_focus       = 0
max_pi_focus       = 99

if (VIDEO == -1):
    print("Camera not found.")

    while True:
        pass

print("mode", MODE, "video", VIDEO)

# snapshot
sx=int((camera_width-still_width)/2)
sy=int((camera_height-still_height)/2)
ex=sx+still_width
ey=sy+still_height

# video
vsx = int((frame_video_width-video_width)/2)
vsy = int((frame_video_height-video_height)/2)
vex = vsx+video_width
vey = vsy+video_height

frames = queue.Queue(10)

class VideoTask(threading.Thread):
    def __init__(self, ui, video_source=VIDEO):
        threading.Thread.__init__(self)
        self.ui = ui
        self.video_source = video_source
        self.task = True

    def run(self):
        global frames

        self.open()

        if self.task:
            self.ui.ready()

        while self.task:
            frames.put(self.vid.read())

        if self.vid.isOpened():
            self.vid.release()

    def open(self):
        # open video source (by default this will try to open the computer webcam)
        self.vid = cv2.VideoCapture(self.video_source)

        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", self.video_source)

        self.vid.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

        if MODE == MODE_PC:
            self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
            self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        elif MODE == MODE_PI:
            self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, frame_video_width)
            self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_video_height)

        self.vid.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)

    def close(self):
        self.task = False

    def getExposure(self):
        exposure = self.vid.get(cv2.CAP_PROP_EXPOSURE)

        minValue = 1
        index = 0

        # get near exposure in table
        for i in range(len(exposure_pc_table)):
            if MODE == MODE_PC:
                if abs(exposure_pc_table[i] - exposure) < minValue:
                    minValue = abs(exposure_pc_table[i] - exposure)
                    index = i
            elif MODE == MODE_PI:
                if abs(exposure_pi_table[i] - exposure) < minValue:
                    minValue = abs(exposure_pi_table[i] - exposure)
                    index = i

        return index

    def setExposure(self, value):
        self.vid.set(cv2.CAP_PROP_EXPOSURE, exposure_pc_table[value])

    def getFocus(self):
        focus = self.vid.get(cv2.CAP_PROP_FOCUS)

        if MODE == MODE_PI:
            focus = int(focus * (max_pi_focus + 1))

        return focus

    def setFocus(self, value):
        self.vid.set(cv2.CAP_PROP_FOCUS, value)

    def setAutoFocus(self, value):
        self.vid.set(cv2.CAP_PROP_AUTOFOCUS, value)

class App:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        self.window.protocol('WM_DELETE_WINDOW', self.onDestroy)

        if MODE == MODE_PI:
            self.window.attributes("-fullscreen", 1)

        # self.window.wm_iconbitmap('biomedux.ico')

        spinFont = font.Font(family='Times New Roman', size=18)
        txtFont = font.Font(family='Times New Roman', size=14)

        # Create a canvas that can fit the above video source size
        self.canvas = tkinter.Canvas(window, width = preview_width, height = preview_height)

        # control layout
        controlFrame = tkinter.Frame(self.window)

        # in the control frame
        #exposure group
        exposureFrame = tkinter.Frame(controlFrame, bd=2, relief=tkinter.SUNKEN)
        self.exposureLabel = tkinter.Label(exposureFrame, text="exposure: -", font=txtFont)
        exposureBtnFrame=tkinter.Frame(exposureFrame)
        self.btn_exposureLeft = tkinter.Button(exposureBtnFrame, text='<', font=spinFont, command=self.exposureLeft)
        self.btn_exposureRight = tkinter.Button(exposureBtnFrame, text='>', font=spinFont, command=self.exposureRight)
        self.exposureLabel.pack()
        exposureBtnFrame.pack()
        self.btn_exposureLeft.pack(side='left')
        self.btn_exposureRight.pack()
        exposureFrame.pack(pady=10, fill='x', padx=5)

        #focus group
        focusFrame = tkinter.Frame(controlFrame, bd=2, relief=tkinter.SUNKEN)
        focusLabel = tkinter.Label(focusFrame, text='focus', font=txtFont)
        focusBtnFrame=tkinter.Frame(focusFrame)
        self.btn_focusLeft = tkinter.Button(focusBtnFrame, text='<', font=spinFont, command=self.focusLeft)
        self.btn_focusRight = tkinter.Button(focusBtnFrame, text='>', font=spinFont, command=self.focusRight)
        ### auto frame
        autoFrame=tkinter.Frame(focusBtnFrame)
        alabel = tkinter.Label(autoFrame,text='auto')
        self.isAuto = tkinter.IntVar()
        self.btn_autoCheck = tkinter.Checkbutton(autoFrame, variable=self.isAuto, command=self.focusAuto)
        self.isAuto.set(True)
        alabel.pack()
        self.btn_autoCheck.pack()
        ### auto end
        if MODE == MODE_PC:
            self.focusSlider = tkinter.Scale(focusFrame, from_=min_pc_focus, to=max_pc_focus, orient=tkinter.HORIZONTAL)
        elif MODE == MODE_PI:
            self.focusSlider = tkinter.Scale(focusFrame, from_=min_pi_focus, to=max_pi_focus, orient=tkinter.HORIZONTAL)
        self.focusSlider.bind('<ButtonRelease-1>',self.sliderMoved)
        focusLabel.pack()
        focusBtnFrame.pack()
        self.btn_focusLeft.pack(side='left')
        autoFrame.pack(side='left')
        self.btn_focusRight.pack(side='left')
        self.focusSlider.pack()
        focusFrame.pack(pady=10, fill='x')
        #file group
        fileFrame = tkinter.Frame(controlFrame, bd=2, relief=tkinter.SUNKEN)
        fileLabel = tkinter.Label(fileFrame, text='file', font=txtFont)
        fileBtnFrame=tkinter.Frame(fileFrame)
        self.btn_fileLeft = tkinter.Button(fileBtnFrame, text='<', font=spinFont, command=self.fileLeft)
        self.btn_fileRight = tkinter.Button(fileBtnFrame, text='>', font=spinFont, command=self.fileRight)
        self.btn_delete = tkinter.Button(fileFrame, text='delete', font=txtFont, command=self.fileDelete)
        fileLabel.pack()
        fileBtnFrame.pack()
        self.btn_fileLeft.pack(side='left')
        self.btn_fileRight.pack()
        self.btn_delete.pack()
        fileFrame.pack(pady=10, fill='x', padx=5)

        #live, snapshot buttons
        self.btn_live=tkinter.Button(controlFrame, text="Live", font=txtFont, command=self.live)
        self.btn_snapshot=tkinter.Button(controlFrame, text="Snapshot", font=txtFont, command=self.snapshot)
        self.btn_live.pack(anchor=tkinter.CENTER, padx=5)
        self.btn_snapshot.pack(anchor=tkinter.CENTER, padx=5)

        #local ip
        if MODE == MODE_PI:
            ipLabel = tkinter.Label(controlFrame, text=self.getIP(), font=txtFont)
            ipLabel.pack(side='left')

        self.canvas.pack(side='left')
        controlFrame.pack(side='left', padx=17)

        self.live()

        self.window.mainloop()

    def getIP(self):
        ifname = 'wlan0'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        info = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15], 'utf-8')))
        return ' '.join(['%d' % b for b in info[20:24]])

    def ready(self):
        self.exposure = self.video.getExposure()
        self.focus = self.video.getFocus()

        if MODE == MODE_PC:
            exTxt = 'exposure: %d'%exposure_pc_table[self.exposure]
        elif MODE == MODE_PI:
            exTxt = 'exposure: %d'%self.exposure

        self.exposureLabel['text'] = exTxt
        self.focusSlider.set(self.focus)

        #file manage group initialization
        self.isLive = True
        self.btnStateChange()
        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 15  #delay 15 was not enough
        self.update()

    def btnStateChange(self):
        if self.isLive:
            self.btn_snapshot.config(state=tkinter.NORMAL)
            self.btn_exposureLeft.config(state=tkinter.NORMAL)
            self.btn_exposureRight.config(state=tkinter.NORMAL)
            self.btn_autoCheck.config(state=tkinter.NORMAL)
            #self.btn_focusLeft.config(state=tkinter.NORMAL)
            #self.btn_focusRight.config(state=tkinter.NORMAL)
            #self.focusSlider.config(state=tkinter.NORMAL)
            self.btn_live.config(state=tkinter.DISABLED)
            self.btn_fileLeft.config(state=tkinter.DISABLED)
            self.btn_fileRight.config(state=tkinter.DISABLED)
            self.btn_delete.config(state=tkinter.DISABLED)

            self.focusAuto()
        else:
            self.btn_snapshot.config(state=tkinter.DISABLED)
            self.btn_exposureLeft.config(state=tkinter.DISABLED)
            self.btn_exposureRight.config(state=tkinter.DISABLED)
            self.btn_autoCheck.config(state=tkinter.DISABLED)
            self.btn_focusLeft.config(state=tkinter.DISABLED)
            self.btn_focusRight.config(state=tkinter.DISABLED)
            self.focusSlider.config(state=tkinter.DISABLED)
            self.btn_live.config(state=tkinter.NORMAL)
            self.btn_fileLeft.config(state=tkinter.NORMAL)
            self.btn_fileRight.config(state=tkinter.NORMAL)
            self.btn_delete.config(state=tkinter.NORMAL)

    def showCurrentImage(self):
        if self.nof == 0:
            fname = PATH + 'NoImage.jpg'
        else:
            fl = gb.glob(PATH + 'Pictures/frame-*')
            fname = fl[self.fileptr]
        img = cv2.imread(fname,cv2.IMREAD_COLOR)
        img = cv2.resize(img, (preview_width, preview_height), 0,0,interpolation = cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(img))
        self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

    def live(self):
        img = cv2.imread(PATH + 'Wait.jpg',cv2.IMREAD_COLOR)
        img = cv2.resize(img, (preview_width, preview_height), 0,0,interpolation = cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(img))
        self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        self.btn_snapshot.config(state=tkinter.DISABLED)
        self.btn_exposureLeft.config(state=tkinter.DISABLED)
        self.btn_exposureRight.config(state=tkinter.DISABLED)
        self.btn_autoCheck.config(state=tkinter.DISABLED)
        self.btn_focusLeft.config(state=tkinter.DISABLED)
        self.btn_focusRight.config(state=tkinter.DISABLED)
        self.focusSlider.config(state=tkinter.DISABLED)
        self.btn_live.config(state=tkinter.DISABLED)
        self.btn_fileLeft.config(state=tkinter.DISABLED)
        self.btn_fileRight.config(state=tkinter.DISABLED)
        self.btn_delete.config(state=tkinter.DISABLED)

        self.video = VideoTask(self)
        self.video.start()

    def fileDelete(self):
        fl = gb.glob(PATH + 'Pictures/frame-*')
        print(self.fileptr)
        print(fl)
        print(fl[self.fileptr])
        fname = fl[self.fileptr]
        isOk = tkinter.messagebox.askokcancel('delete', 'Are you sure to delete this file: '+fname)
        if isOk:
            print(fname)
            os.remove(fname)
            self.nof = self.nof-1
            self.fileptr = self.fileptr-1
            if self.fileptr < 0:
                self.fileptr = 0
            print(self.nof)
            print(self.fileptr)
            if self.nof == 0:
                self.btn_delete.config(state=tkinter.DISABLED)
                self.btn_fileLeft.config(state=tkinter.DISABLED)
                self.btn_fileRight.config(state=tkinter.DISABLED)
            elif self.nof == 1:
                self.btn_fileLeft.config(state=tkinter.DISABLED)
                self.btn_fileRight.config(state=tkinter.DISABLED)
            self.showCurrentImage()

    def fileLeft(self):
        self.fileptr = self.fileptr - 1
        if self.fileptr == 0:
            self.btn_fileLeft.config(state=tkinter.DISABLED)
        if self.fileptr < self.nof - 1:
            self.btn_fileRight.config(state=tkinter.NORMAL)
        self.showCurrentImage()

    def fileRight(self):
        self.fileptr = self.fileptr + 1
        if self.fileptr == self.nof - 1:
            self.btn_fileRight.config(state=tkinter.DISABLED)
        if self.fileptr > 0:
            self.btn_fileLeft.config(state=tkinter.NORMAL)
        self.showCurrentImage()

    def exposureLeft(self):
        self.exposure = self.exposure - 1
        if self.exposure < min_exposure:
            self.exposure = min_exposure

        if MODE == MODE_PC:
            self.video.setExposure(exposure_pc_table[self.exposure])
            exTxt = 'exposure: %d'%exposure_pc_table[self.exposure]
        elif MODE == MODE_PI:
            self.video.setExposure(exposure_pi_table[self.exposure])
            exTxt = 'exposure: %d'%self.exposure

        self.exposureLabel['text'] = exTxt

    def exposureRight(self):
        self.exposure = self.exposure + 1
        if self.exposure > max_exposure:
            self.exposure = max_exposure

        if MODE == MODE_PC:
            self.video.setExposure(exposure_pc_table[self.exposure])
            exTxt = 'exposure: %d'%exposure_pc_table[self.exposure]
        elif MODE == MODE_PI:
            self.video.setExposure(exposure_pi_table[self.exposure])
            exTxt = 'exposure: %d'%self.exposure
        self.exposureLabel['text'] = exTxt

    def focusAuto(self):
        if self.isAuto.get():
            self.btn_focusLeft.config(state=tkinter.DISABLED)
            self.btn_focusRight.config(state=tkinter.DISABLED)
            self.focusSlider.config(state=tkinter.DISABLED)
            self.video.setAutoFocus(1)
        else:
            self.btn_focusLeft.config(state=tkinter.NORMAL)
            self.btn_focusRight.config(state=tkinter.NORMAL)
            self.focusSlider.config(state=tkinter.NORMAL)
            self.video.setAutoFocus(0)

    def sliderMoved(self,event):
        self.focus = self.focusSlider.get()
        if MODE == MODE_PC:
            self.video.setFocus(self.focus)
        elif MODE == MODE_PI:
            self.video.setFocus(self.focus / (max_pi_focus + 1.))

    def focusLeft(self):
        self.focus = self.focus - 1

        if MODE == MODE_PC:
            if self.focus < min_pc_focus:
                self.focus = min_pc_focus
            self.video.setFocus(self.focus)
        elif MODE == MODE_PI:
            if self.focus < min_pi_focus:
                self.focus = min_pi_focus
            self.video.setFocus(self.focus / (max_pi_focus + 1.))

        self.focusSlider.set(self.focus)

    def focusRight(self):
        self.focus = self.focus + 1
        if MODE == MODE_PC:
            if self.focus > max_pc_focus:
                self.focus = max_pc_focus
            self.video.setFocus(self.focus)
        elif MODE == MODE_PI:
            if self.focus > max_pi_focus:
                self.focus = max_pi_focus
            self.video.setFocus(self.focus / (max_pi_focus + 1.))
        self.focusSlider.set(self.focus)

    def snapshot(self):
        self.isLive=False
        self.btnStateChange()
        self.video.close()

        fname = PATH + "Pictures/frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + "_" + str(crop_scale) + ".jpg"

        if MODE == MODE_PC:
            startupinfo = sub.STARTUPINFO()
            startupinfo.dwFlags |= sub.STARTF_USESHOWWINDOW
            sub.run(['stillcap', '/device', 'RecordexUSA','/format', str(camera_width), str(camera_height), str(camera_frate), 'MJPG', '/out', PATH + 'temp.jpg','100'], startupinfo=startupinfo)
        else:
            sub.run(['fswebcam', '--crop', "%dx%d,%dx%d" % (ex-sx,ey-sy,sx,sy), '-r', "%dx%d" % (camera_width, camera_height), '--no-subtitle', '--no-timestamp', '--no-overlay', '--no-banner', '--jpeg', '95', fname])

        if MODE == MODE_PC:
            frame = cv2.imread(PATH + 'temp.jpg')
            frame = frame[sy:ey, sx:ex] #crop
            cv2.imwrite(fname, frame)

        while 1:
            self.nof = len(gb.glob(PATH + 'Pictures/frame-*'))
            if self.nof > 0:
                break
            else:
                print('sleep')
                time.sleep(0.1)

        self.fileptr = self.nof - 1
        self.btn_fileRight.config(state=tkinter.DISABLED)
        if self.nof == 1:
            self.btn_fileLeft.config(state=tkinter.DISABLED)
        else:
            self.btn_fileLeft.config(state=tkinter.NORMAL)

    def update(self):
        global frames

        # Get a frame from the video source
        if self.isLive:
            self.btn_delete.config(state=tkinter.DISABLED)
        else:
            self.btn_delete.config(state=tkinter.NORMAL)

        try:
            ret, frame = frames.get(0)
            frames.queue.clear()

            if ret:
                if MODE == MODE_PC:
                    frame = frame[sy:ey,sx:ex] # crop
                elif MODE == MODE_PI:
                    frame = frame[vsy:vey,vsx:vex] # crop
                frame = cv2.resize(frame, (preview_width, preview_height), 0,0, interpolation = cv2.INTER_CUBIC)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if self.isLive:
                    self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
                    self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        except queue.Empty:
            pass

        if self.isLive:
            self.window.after(self.delay, self.update)

    def onDestroy(self):
        self.video.close()
        self.window.destroy()

# Create a window and pass it to the Application object
App(tkinter.Tk(), "Biomedux Blue")
