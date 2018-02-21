'''The text below is from the Software Development Kit (SDK) for BrainAmp around which this interface was built. 
Most of my longform notes will be in the form of triple quotes as seen here.  However, this is the NFT interface
for the BrainAmp system intended to train subjects for the BIAV. -Steven Pillen (SP)'''

"""
Simple Python RDA client for the RDA tcpip NFT of the BrainVision Recorder
It reads all the information from the recorded EEG,
prints EEG and marker information to the console and calculates and
prints the average power every second


Brain Products GmbH
Gilching/Freiburg, Germany
www.brainproducts.com
"""
import serial
import PreBIAV_NFT
import scipy.signal as sig
import numpy as np

# needs socket and struct library to connect to the BrainAMP
from socket import *
from struct import *
import time


import wx
from threading import Thread
import time
import os
#

nowtime = time.time()
initialization = False

wildcard = "EEG raw data (*.eeg)|*.eeg|"    \
           "Comma Separated Values File (*.csv)|*.csv|"       \
           "All files (*.*)|*.*"

TMS_Mark = False
starttime = 0
startflag = False
# Marker class for storing marker information

        
        
        
'''This is the threading mechanism used for initiating the NFT paradigm.
Most of the contents of this class are lifted directly from the BrainAmp SDK.
I never personally invested much effort into trying to understand these methods,
given that they appear to work without issue.  Modify these at your own peril. -SP '''
class testThread(Thread):
    def __init__(self, parent):
        self.parent = parent
        Thread.__init__(self)
        self.start()
        
    def run(self):
        self.TMS_Mark = False
        global nowtime
    # Marker class for storing marker information
        class Marker:
            def __init__(self):
                self.position = 0
                self.points = 0
                self.channel = -1
                self.type = ""
                self.description = ""

        # Helper function for receiving whole message
        def RecvData(socket, requestedSize):
            returnStream = ''
            while len(returnStream) < requestedSize:
                databytes = socket.recv(requestedSize - len(returnStream))
                if databytes == '':
                    raise RuntimeError, "connection broken"
                returnStream += databytes
         
            return returnStream   

            
        # Helper function for splitting a raw array of
        # zero terminated strings (C) into an array of python strings
        def SplitString(raw):
            stringlist = []
            s = ""
            for i in range(len(raw)):
                if raw[i] != '\x00':
                    s = s + raw[i]
                else:
                    stringlist.append(s)
                    s = ""

            return stringlist
            

        # Helper function for extracting eeg properties from a raw data array
        # read from tcpip socket; PART OF BrainAmp SDK
        def GetProperties(rawdata):

            # Extract numerical data
            (channelCount, samplingInterval) = unpack('<Ld', rawdata[:12])

            # Extract resolutions
            resolutions = []
            for c in range(channelCount):
                index = 12 + c * 8
                restuple = unpack('<d', rawdata[index:index+8])
                resolutions.append(restuple[0])

            # Extract channel names
            channelNames = SplitString(rawdata[12 + 8 * channelCount:])

            return (channelCount, samplingInterval, resolutions, channelNames)

        # Helper function for extracting eeg and marker data from a raw data array
        # read from tcpip socket
        '''This is where the data handling actually happens -SP'''
        def GetData(rawdata, channelCount):

            # Extract numerical data
            (block, points, markerCount) = unpack('<LLL', rawdata[:12])

            # Extract eeg data as array of floats
            data = []
            for i in range(points * channelCount):
                index = 12 + 4 * i
                value = unpack('<f', rawdata[index:index+4])
                data.append(value[0])

            # Extract markers
            markers = []
            index = 12 + 4 * points * channelCount
            for m in range(markerCount):
                markersize = unpack('<L', rawdata[index:index+4])

                ma = Marker()
                (ma.position, ma.points, ma.channel) = unpack('<LLl', rawdata[index+4:index+16])
                typedesc = SplitString(rawdata[index+16:index+markersize[0]])
                ma.type = typedesc[0]
                ma.description = typedesc[1]

                markers.append(ma)
                index = index + markersize[0]

            return (block, points, markerCount, data, markers)


        ##############################################################################################
        #
        # Main RDA routine
        #
        ##############################################################################################
        global filename
        # Create a tcpip socket
        con = socket(AF_INET, SOCK_STREAM)
        # Connect to recorder host via 32Bit RDA-port
        # adapt to your host, if recorder is not running on local machine
        # change port to 51234 to connect to 16Bit RDA-port
        con.connect(("localhost", 51244))
        f = open(filename, 'w')
        # Flag for main loop
        finish = False

        # data buffer for calculation, empty in beginning
        data1s = []

        # block counter to check overflows of tcpip buffer
        lastBlock = -1
        #self.ser = serial.Serial('COM1', 9600)
        
        
        #### Main Loop ####
        while not finish:
            '''starttime and startflag are both used as time markers for when the recording starts.  
            these are things I made.  there are probably better methods for timing, but they work
            and I'm a hack, so this is what I have to offer to you.  Improve these methods if you have the time
            and care about doing things properly.  I wrote these when I was a rank amateur, and while I'm not much 
            better now, I'm sure I would have tried to do a better job, knowing what I know now.  Oh well! -SP'''
            global starttime
            global startflag
            if startflag == False:
                starttime = time.time()
                startflag = True
            # Get message header as raw array of chars
            rawhdr = RecvData(con, 24)

            # Split array into usefull information id1 to id4 are constants
            (id1, id2, id3, id4, msgsize, msgtype) = unpack('<llllLL', rawhdr)

            # Get data part of message, which is of variable size
            rawdata = RecvData(con, msgsize - 24)

            # Perform action dependend on the message type
            if msgtype == 1:
                # Start message, extract eeg properties and display them
                (channelCount, samplingInterval, resolutions, channelNames) = GetProperties(rawdata)
                # reset block counter
                lastBlock = -1

                print "Start"
                print "Number of channels: " + str(channelCount)
                print "Sampling interval: " + str(samplingInterval)
                print "Resolutions: " + str(resolutions)
                print "Channel Names: " + str(channelNames)
                for x in channelNames: 
                    f.write(x + ',')
                f.write('Trigger\n') 

            elif msgtype == 4:
                # Data message, extract data and markers
                (block, points, markerCount, data, markers) = GetData(rawdata, channelCount)

                # Check for overflow
                if lastBlock != -1 and block > lastBlock + 1:
                    print "*** Overflow with " + str(block - lastBlock) + " datablocks ***" 
                lastBlock = block

                # Print markers, if there are some in actual block
                if markerCount > 0:
                    for m in range(markerCount):
                        print "Marker " + markers[m].description + " of type " + markers[m].type

                # Put data at the end of actual buffer
                data1s.extend(data)
                
                #This will write the file I opened in the begining.
                #for a in range(0,9)
                '''This is my handiwork right here again.  This is a loop that serves two primary purposes.
                First, it is a mechanism by which data can be recorded from the TCP-IP socket.  The default sampling rate
                is 5000, which means the files generated are going to be very large.  Expect an hour's worth of data to be 
                in the 5-10 gigabytes range.  if you want to reduce these filesizes, I recommend either implementing a downsampling 
                method here, or else reduce the written data to known channels of interest.  I have no excuse for not doing so myself.
                -SP'''
                counter = 0
                if PreBIAV_NFT.Record == True:
                    for item in data:
                        counter = counter+1
                        f.write(str(item))
                        f.write(',')
                        if counter == 32:
                            if self.TMS_Mark == True: #or #NFT.TMS_Mark == True:
                                print 'Event Marked'
                                self.TMS_Mark = False
                                PreBIAV_NFT.TMS_Mark = False
                                self.ser.write('0')
                                f.write('1') 
                                '''#this is for the 33rd column, which will contain the information about the triggers. 
                                the sloppy way I implemented this, there is a shared variable between the NFT script and 
                                this particular loop.  Again, I am a hack, so I have a vague notion that this probably wasn'ta
                                the smartest way to do this, but it worked well enough, so I never investigated the "right way".
                                do not be limited by my own narrow horizons, if you care about such things. 

                                Also, take note of the fact that Left events and Right events are 7 and 8 respectively.
                                A silly way to remember is that 7 looks kind of like a 180 degree flipped 'L', and '8' ends
                                with the letters 'ight', just like 'right'.  If you can only recall one of these rules, you'll figure it out! -SP'''
                            elif PreBIAV_NFT.LeftTag == True:
                                f.write('7')
                                print 'The target is now the LEFT side'
                                PreBIAV_NFT.LeftTag = False
                            elif PreBIAV_NFT.RightTag == True:
                                print 'The target is now the RIGHT side'
                                f.write('8')
                                PreBIAV_NFT.RightTag = False
                            else:
                                f.write('0') #0 is the value for 'no event here today'
                            f.write('\n')    
                            
                            counter = 0
                
                # If more than 1s of data is collected, calculate average power, print it and reset data buffer
                '''We're getting back into the original SDK territory again. Watch your step. -SP'''
                if len(data1s) > channelCount * 1000000 / samplingInterval:
                    index = int(len(data1s) - channelCount * 1000000 / samplingInterval)
                    data1s = data1s[index:]
                    avg = 0
                    # Do not forget to respect the resolution !!!
                    for i in range(len(data1s)):
                        avg = avg + data1s[i]*data1s[i]*resolutions[i % channelCount]*resolutions[i % channelCount]
                    avg = avg / len(data1s)
                    #print "Average power: " + str(avg)
                    #print time.time() - nowtime
                    ''' Now we are back into my domain.  
                    Take note of the fact that SMRTimeSeries and '2' are C3 and C4, respectively.  Alpha is, of course, Oz.
                    The '320th index' thing I have going on here is a crude method of downsampling.  I'm sure it would be better
                    to do some kind of interpolation, and I welcome you to do so if you have the time and inclination.  In any case,
                    the 32nd index of these arrays would be all of the time series of a given channel.  multiply that by 10, and you get 
                    what you see below: the 10th index of every 32nd index, or the 10th index of a given time series. 
                    Also be aware that the channel positions of these methods assume the use of the 32 electrode Easycap. -SP'''
                    nowtime = time.time()
                 
                    SMRTimeSeries = data1s[4::320] 
                    SMRTimeSeries2 = data1s[5::320]
                    AlphaSeries = data1s[19::320]
                    
                    ''' Here below we see the welch function doing the heavy lifting in terms of spectral decomposition.  the thing
                    to know is that the freq output contains the frequency labels, and the density output contains the actual decomposed
                    values.  typically, we are only interested in the indices related to our target bands.  if you are ever in doubt as to 
                    whether you are looking at the correct band, I recommend you print out the freq array while passing data through this 
                    system.  if you are selecting the correct indices, you will see the frequency range you wanted to select being 
                    printed out each time.  -SP'''
                    freq, density = sig.welch(SMRTimeSeries, fs=500, nperseg = 500, scaling='density')
                    freq2, density2 = sig.welch(SMRTimeSeries2, fs=500, nperseg = 500, scaling='density')
                    freqA, densityA = sig.welch(AlphaSeries, fs=500, nperseg = 500, scaling='density')                    
                    data1s = []
                    
                    ''' Here we see a whole bunch of spectral bits being pushed to the NFT paradigm in real time.  these values are populated in real time.  Note that the voltage values are not targetting the 'density' outputs, but rather, the direct voltages themselves
                    that make up the SMR time series.  Do not confuse these two types of outputs!  -SP'''
                    PreBIAV_NFT.SPTruVal = np.average(density[13:16]) - np.average(density2[13:16]) # this is 13-15 Hz
                    PreBIAV_NFT.LoNoise = density[1] #1 Hz
                    PreBIAV_NFT.HiNoise = np.average(density[40:60]) #40-59 Hz
                    PreBIAV_NFT.VoltMax = np.amax(SMRTimeSeries)
                    PreBIAV_NFT.VoltMedian = np.median(SMRTimeSeries)
                    PreBIAV_NFT.VoltMin = np.amin(SMRTimeSeries)
                    PreBIAV_NFT.SMRTimeSeries = SMRTimeSeries
                    PreBIAV_NFT.SMRTimeSeries2 = SMRTimeSeries2
                    PreBIAV_NFT.AlphaSeries = AlphaSeries
                    PreBIAV_NFT.SMRDens = density[8:19]     #This is a pretty wide breadth of values, from 8-18.  The idea is we want to accommodate individual alp
                    PreBIAV_NFT.SMRDens2 = density2[8:19]
                    PreBIAV_NFT.AlphaDensity = densityA
                    
                    '''Below we see the means through which Alpha is tracked.  This is also printed when we are recording from Mu, mostly because I was lazy, but also because it
                        is an adequate sanity check to see that data is being recorded.  Mu and Alpha are both being recorded from no matter which is the target; the only real
                        major bug that happens around here is that it's possible the amplifier is not streaming data.  In that case, this is a sufficient mechanism for
                        identifying that problem.  That being said, an ambitious person could make this display mu in the condition that mu is the target if they really wanted to. -SP'''
                    if PreBIAV_NFT.stage == 1 and PreBIAV_NFT.pausetime == False:
                            Alphas = np.vstack((Alphas, densityA[6:16]))
                            #print 'alphas are ', Alphas
                            PreBIAV_NFT.Alphas = Alphas
                            print 'alphas size is ', len(Alphas)
                            print densityA[6:16]


                    else:
                            Alphas = densityA[6:16]
                            if len(Alphas) > 2:
                                PreBIAV_NFT.Alphas = Alphas
                                PreBIAV_NFT.densityA = densityA
                            

                            
                    

            elif msgtype == 3:
                # Stop message, terminate program
                print "Stop"
                finish = True
                f.write(str(time.time()-starttime))
                f.close()
                con.close()
        # Close tcpip connection

''' This is the GUI for the control panel.  my general design principle, as is usually my principle in designing these
sorts of GUIs, was to make it as idiot proof as possible.  not only did I improve these elements of it for when
this project ultimately gets passed on to whoever the poor sucker is who has to deal with it after me, but I am 
also a blithering idiot, and benefit from being corralled against messing things up with a stray click.  it's 
important to understand your limits as a person, and it's important to work around the limitations of the 
other people in your life, rather than merely resenting them for not being good enough, don't you think?  
We should try to create a world where making stupid mistakes is really hard, if you ask me.  -SP '''
class testGUI(wx.Frame): 
    def __init__(self): 
    
        self.firstflag = True
        wx.Frame.__init__(self, None, -1, "NFT Control Panel", size=(500,500)) 
        panel = wx.Panel(self, -1)
        wx.CallAfter(self.pollServer)
        
        ''' These are the buttons and the displayed text.  note that I tried to arrange them in the general order you see them
        on screen.  'pos' is the x,y coordinates they appear in.  if you want a nifty button to do something 
        for you, I recommend trying to do it, even if you're not good at this sort of thing!  it's fun to automate the
        drudgery of your life, and it feels so satisfying when it works properly.  you will be grateful you put in the effort. -SP'''
        self.FileText = wx.StaticText(panel, label="Filename:", pos=(30, 30))
        self.buttonFilename = wx.Button(panel, -1, label="Choose Filename", pos=(30,60))
        self.buttonToggleTMS = wx.Button(panel, -1, label="Toggle TMS", pos=(30,100))
        self.buttonConnect = wx.Button(panel, -1, label="Open Fixation Screen", pos=(30,140))
        self.buttonstartThread = wx.Button(panel, -1, label="Begin EEG Recording", pos=(30,180))
        self.buttonToggleAlpha = wx.Button(panel, -1, label="Toggle Alpha/Mu", pos=(30,220))
        self.buttonRounds = wx.Button(panel, -1, label="Number of Rounds", pos=(30,260))
        
  
        self.buttonToggleInvisibility = wx.Button(panel, -1, label="Invisible Marker", pos=(30,360))
  
        self.buttonNextRound = wx.Button(panel, -1, label="Next Round", pos=(360,120))
        self.buttonCoords = wx.Button(panel, -1, label="Input Phosphene", pos=(360,180))
        
        
        '''Take note of the fact that each of the button labels defined above are bound below to specific functions.
        my general practice in nomenclature is to name the buttons 'button(x)', and their corresponding functions 'x'.
        or more properly, 'self.(x)'.  you will find these functions defined below.  -SP'''
        panel.Bind(wx.EVT_BUTTON, self.Filename, id=self.buttonFilename.GetId())
        panel.Bind(wx.EVT_BUTTON, self.Connect, id=self.buttonConnect.GetId())
        panel.Bind(wx.EVT_BUTTON, self.ToggleAlpha, id=self.buttonToggleAlpha.GetId())
        panel.Bind(wx.EVT_BUTTON, self.Rounds, id=self.buttonRounds.GetId())
        panel.Bind(wx.EVT_BUTTON, self.ToggleTMS, id=self.buttonToggleTMS.GetId())
        panel.Bind(wx.EVT_BUTTON, self.startThread, id=self.buttonstartThread.GetId())
        panel.Bind(wx.EVT_BUTTON, self.NextRound, id=self.buttonNextRound.GetId())
        panel.Bind(wx.EVT_BUTTON, self.Coords, id=self.buttonCoords.GetId())
        panel.Bind(wx.EVT_BUTTON, self.Invisibility, id=self.buttonToggleInvisibility.GetId())
        
        
        
        #panel.Bind(wx.EVT_BUTTON, self.Tally, id=self.buttonTally.GetId())
        '''Please also take note of the fact that I have disabled all buttons but the filename button.
        I set it up so that the buttons are enabled one at a time, and at certain points, previous buttons
        that handle sensitive variables (such as whether TMS control is active) are disabled.  I wanted
        this process to be as linear as possible.  I recommend you follow similar design principles unless
        you are a cautious and clever person, and you do not intend to allow this software to fall into 
        the hands of those less capable than you.  including you, on a bad day.  -SP'''
        
        self.buttonConnect.Disable()
        self.buttonToggleAlpha.Disable()
        self.buttonToggleTMS.Disable()
        self.buttonstartThread.Disable() 
        self.buttonNextRound.Disable()    
        self.buttonCoords.Disable()
        self.buttonToggleInvisibility.Disable()
        self.buttonRounds.Disable()
        
        self.sizer = wx.BoxSizer()
        self.sizer.Add(self.FileText, 1)
        #self.sizer.Add(self.button)


        panel.SetSizerAndFit(self.sizer)  
        self.Show()        


    ''' These are the functions that run this script.  It starts with my favorite: I love a good filename dialogue.  
    This one is especially useful because it warns you if you're about to overwrite a file.  Never underestimate
    how much heartache simple countermeasures like these can save you.  You WILL notice them when they are missing. -SP'''
    def Filename(self, event):
        """
        
        Opens up a file saving dialog when the "File" button is pressed.
        """
        global filename
        dlg = wx.FileDialog(self, message="Save EEG data as ...",
                            defaultDir=os.getcwd(), defaultFile="",
                            wildcard=wildcard, style=wx.SAVE)

        dlg.SetFilterIndex(1)

        # Show the dialog and retrieve the user response. If it is the OK response, 
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        
        # If the filename exists, ask for confirmation
        if os.path.exists( fname ):
            dlg = wx.MessageDialog(self, "File already exists. Overwrite?",
                                   "Potential problem with file",
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
                                   )

            response = dlg.ShowModal()
            if response == wx.ID_YES:
                filename = fname

            elif response == wx.ID_NO:
                filename = None

            
        else:
            # If the file does not exists, we can proceed
            filename = fname
        if filename != None:
            filestring = "Filename: " + str(fname)
            self.FileText.SetLabel(filestring)
            self.sizer.Layout()
            print(["Filename: " + fname])
            PreBIAV_NFT.filename = fname
            self.buttonToggleTMS.Enable()
            #self.buttonstartThread.Enable()
            #self.buttonConnect.Enable()
            self.Refresh()
            self.Update()
        PreBIAV_NFT.OutputFilename = fname[:-4] + 'MetaData.csv'       #This is for the metadata file.
        PreBIAV_NFT.ExperimentOutputName = fname[:-4] + 'ContRec.csv'  #This is for the control file, here artifactual.  I suppose it could be removed.
        #self.update_NFT()
        PreBIAV_NFT.CustomName = True
        
        
    '''This is a key function: it determines whether you are sending TMS pulses or not.
        note that this function, like many of its kind, changes the label of the button
        to reflect the current state of the variable.  We want to set this to true
        for the final stages of neurofeedback, when the subjects are nearly ready for BIAV. -SP'''   
    def ToggleTMS(self, event):
        PreBIAV_NFT.TMSFlag = not PreBIAV_NFT.TMSFlag
        print 'TMS is set to ', PreBIAV_NFT.TMSFlag
        self.buttonToggleTMS.SetLabel('TMS is ' + str(PreBIAV_NFT.TMSFlag))
        self.sizer.Layout()
        self.Refresh()
        self.Update() 
        self.buttonConnect.Enable()

        #self.buttonConnect.Enable()
    
    #This function creates the NFT screen.
    def Connect(self, event):
        self.buttonstartThread.Enable()
        self.buttonToggleTMS.Disable()
        self.buttonConnect.Disable()
        PreBIAV_NFT.main()
        #self.the_thread = testThread(self)        
    
    '''This function initializes the thread which communicates with BrainVision Recorder via TCP-IP.
    That is the engine which driving this experiment. Without this working, it's like a kaput automobile.  -SP '''
    def startThread(self, event):
        self.the_thread = testThread(self)
        self.buttonToggleAlpha.Enable()
        self.buttonstartThread.Disable()
        #self.buttonNextRound.Enable()
        
    '''Alpha or MU.  Note that the label changes according to what the value is toggled to,
    and that the variable 'alpha' is in the NFT paradigm's workspace. -SP'''
    def ToggleAlpha(self, event):
        PreBIAV_NFT.alpha = not PreBIAV_NFT.alpha
        print 'Alpha is set to ', PreBIAV_NFT.alpha
        self.buttonRounds.Enable()
        if PreBIAV_NFT.alpha:
            self.buttonToggleAlpha.SetLabel('ALPHA!')
        else:
            self.buttonToggleAlpha.SetLabel('MU!')
        self.sizer.Layout()
        self.Refresh()
        self.Update()   
     
     
    '''The NFT paradigm can be set to either 60 or 100 rounds.  Realize that the first 20 rounds are for baselining.  That means in effect,
    a subject either has 40 or 80 proper rounds in a given paradigm.  for the first 4 times they perform this experiment, you want 60 of both 
    types of NFT.  once they have demonstrated proficiency with one or the other, you want 100 rounds of their best target, alone.  -SP''' 
    def Rounds(self,event):
        if PreBIAV_NFT.trialnumber == 60:
            PreBIAV_NFT.trialnumber = 100
        else:
            PreBIAV_NFT.trialnumber = 60
        self.buttonRounds.SetLabel(str(PreBIAV_NFT.trialnumber) + ' Rounds')
        self.sizer.Layout()
        self.Refresh()        
        
        self.buttonNextRound.Enable() 
        self.buttonCoords.Enable()
        self.buttonToggleInvisibility.Enable()
        
    '''This is a dialogue that lets you specify the X Y coordinates for the phosphene image.  We 
    generally want this to be internally consistent, so refer to the metadata files from previous recordings 
    to figure out the coordinates to use. -SP'''
    def Coords(self, event):
        frame = wx.Frame(None, -1, 'win.py')
        frame.SetDimensions(0,0,200,50)
 
        # Create text input
        dlg = wx.TextEntryDialog(frame, 'Enter the previous X Y coordinates in the format: ''X Y'', i.e. ''150 500''. ','X Y  Entry')
        dlg.SetValue("")
        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            coords = dlg.GetValue()
            coords = coords.split()
            PreBIAV_NFT.pos = [0, 0]
            if len(coords) == 2:
                PreBIAV_NFT.pos[0] = int(coords[0])
                PreBIAV_NFT.pos[1] = int(coords[1])
        
                PreBIAV_NFT.NEXT = True
                PreBIAV_NFT.RecordBypass = True
                self.buttonToggleAlpha.Disable()
                self.buttonCoords.Disable()
                self.buttonRounds.Disable()
                self.firstflag = False
    
    '''This function makes the white ball invisible.  It is to be used when the subject is peforming very well on a standard NFT trial,
    but only after they are using the 100 round paradigm.  Note that this is a 1-way ticket, so click carefully.  -SP'''
    def Invisibility(self, event):
        PreBIAV_NFT.invisibleflag = True
    
    
    '''This function shifts between stages of the NFT.  If you are at the very beginning, it will make it so you can select the 
    phosphene position by clicking on the center point on the screen where a participant is seeing a phosphene when stimulated.
    Ideally, this should only ever happen the first time a person runs this experiment.  From that point forward, the 'input phosphene'
    function should be used to replicate their previous answer. Regardless, this function does switch between baseline and main NFT. -SP'''
    def NextRound(self, event):
        # print('check')
        # self.ser = serial.Serial('COM1', 9600)
        # self.ser.write('0')
        # self.ser.close()
        if self.firstflag:
            self.firstflag = True
            PreBIAV_NFT.stage = -1
            self.firstflag = False
            print 'starting flag flipped'
        else:
            PreBIAV_NFT.NEXT = True
            print 'next round'
        PreBIAV_NFT.RecordBypass = True
        self.buttonToggleAlpha.Disable()
        self.buttonCoords.Disable()
        self.buttonRounds.Disable()
        
    ''' These two are legacy functions from when I used the panel as more of an interactive scoreboard for other projects.
        I didn't have the heart to remove them, as I figured some day I may have another use for them, and they do not harm left alone.
        Do not let my sentimentality get in your way if you have a more exacting mindset about these details, however.  -SP'''
    def pollServer(self):
        self.Tally()
        wx.CallLater(500,self.pollServer)
        

    def Tally(self):
        self.sizer.Layout()
        self.Refresh()
        self.Update()    


    

if __name__ == '__main__': 
    app = wx.App(redirect=False)
    frame = testGUI() 
    frame.Show(True) 
    app.MainLoop()            
            
''' All of the functions below were part of the BrainAmp SDK.  So again, modify these at your own peril--
personally, I say, if it ain't broke, don't fix it.  So ask yourself: is it broke?  -SP'''


# Helper function for receiving whole message
def RecvData(socket, requestedSize):
    returnStream = ''
    while len(returnStream) < requestedSize:
        databytes = socket.recv(requestedSize - len(returnStream))
        if databytes == '':
            raise RuntimeError, "connection broken"
        returnStream += databytes
 
    return returnStream   

    
# Helper function for splitting a raw array of
# zero terminated strings (C) into an array of python strings
def SplitString(raw):
    stringlist = []
    s = ""
    for i in range(len(raw)):
        if raw[i] != '\x00':
            s = s + raw[i]
        else:
            stringlist.append(s)
            s = ""

    return stringlist
    

# Helper function for extracting eeg properties from a raw data array
# read from tcpip socket
def GetProperties(rawdata):

    # Extract numerical data
    (channelCount, samplingInterval) = unpack('<Ld', rawdata[:12])

    # Extract resolutions
    resolutions = []
    for c in range(channelCount):
        index = 12 + c * 8
        restuple = unpack('<d', rawdata[index:index+8])
        resolutions.append(restuple[0])

    # Extract channel names
    channelNames = SplitString(rawdata[12 + 8 * channelCount:])

    return (channelCount, samplingInterval, resolutions, channelNames)

# Helper function for extracting eeg and marker data from a raw data array
# read from tcpip socket       
def GetData(rawdata, channelCount):

    # Extract numerical data
    (block, points, markerCount) = unpack('<LLL', rawdata[:12])

    # Extract eeg data as array of floats
    data = []
    for i in range(points * channelCount):
        index = 12 + 4 * i
        value = unpack('<f', rawdata[index:index+4])
        data.append(value[0])

    # Extract markers
    markers = []
    index = 12 + 4 * points * channelCount
    for m in range(markerCount):
        markersize = unpack('<L', rawdata[index:index+4])

        ma = Marker()
        (ma.position, ma.points, ma.channel) = unpack('<LLl', rawdata[index+4:index+16])
        typedesc = SplitString(rawdata[index+16:index+markersize[0]])
        ma.type = typedesc[0]
        ma.description = typedesc[1]

        markers.append(ma)
        index = index + markersize[0]

    return (block, points, markerCount, data, markers)





