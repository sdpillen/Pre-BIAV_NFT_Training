'''This is the BrainAmp-based NFT paradigm used for the BIAV training.  Note the commentary from Steven Pillen (SP), original author.  Direct your fury at him from
across the Atlantic Ocean for the woeful structural oddities employed in making this.'''

import pygame, sys
from pygame.locals import *
import numpy as np
import time
from random import randrange  # for starfield, random number generator

print("Initializing the Neurofeedback Paradigm...")
import CCDLUtil.MagStimRapid2Interface.ArmAndFire as CCDLtms

'''Once again, we are seeing some amateur hour elements of my methods.  These global variables probably should have been
defined in a configuration file.  If I had more time... I still probably wouldn't have gotten around to it, because there's always
a more pressing matter, isn't there?  Regardless, take stock of the HIGH_INTENSITY and LOW_INTENSITY variables.  Hardcode these values
according to the TMS threshold of your subjects.  I recommend leaving everything else alone unless you have a good reason. -SP'''

HIGH_INTENSITY = 70  # High TMS pulse value for "phosphene"
LOW_INTENSITY = 25  # Low TMS pulse value for "no phosphene"

''' These are flags used if the device is ever disconnected.
This should essentially never happen, but these are a holdover from the Emotiv days.'''
DISCONNECT = False
LastDISCONNECT = False

DelayPeriod = 4  # 4 seconds is the original "delayperiod"-- this is the period of time between several transitions in the NFT sequence
ResponsePeriod = 26  # 26 by default, this is the number of seconds a user has to respond to a NFT cue.

# Number of frames per second
# Change this value to speed up or slow down your game
FPS = 20

alpha = False  # By Default, Alpha is "false", meaning we look at mu.
trialnumber = 100

'''There may have been a more elegant way of shuffling the rounds, but this is what I did: I made several individual segments of 6 values,
and then individually shuffled them.  In theory, the longest chain of consecutive values is 6 in a row, but that's highly unlikely.
Note also that the loop of 5 segments is just appended into an extremely long list.  No kill like overkill, huh?  
Note the final print statement: you will see the actual left-right values when you initialize the script.  This is so you can
restart the paradigm if for some reason, you get something that looks very predictable.  I suppose if you are feeling ambitious,
maybe you could make a shuffling button on the MainGui, if you really wanted to. -SP'''

LRSegment = [0, 0, 0, 1, 1, 1]
np.random.shuffle(LRSegment)

Seg1 = LRSegment
LRSegment = [0, 0, 0, 1, 1, 1]
np.random.shuffle(LRSegment)

Seg2 = LRSegment
LRSegment = [0, 0, 0, 1, 1, 1]
np.random.shuffle(LRSegment)

Seg3 = LRSegment
LRSegment = [0, 0, 0, 1, 1, 1]
np.random.shuffle(LRSegment)

Seg4 = LRSegment
LRSegment = [0, 0, 0, 1, 1, 1]
np.random.shuffle(LRSegment)

Seg5 = LRSegment

LRValues = Seg1 + Seg2 + Seg3 + Seg4 + Seg5
LRValues = LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues + LRValues
LRValues = LRValues[0:(trialnumber - 20)]
print 'LR Values are ', LRValues

# Funny variable
CustomName = False

# The default filename for the NFT paradigm:
OutputFilename = 'NFT_MetaData.csv'
ExperimentOutputName = 'NFT_ContRec.csv'

# This is for whether a file is being used for the subject's condition.
ControlRecording = False

pygame.display.init()
disp = pygame.display.Info()
WINDOWWIDTH = disp.current_w  # I like the screen slightly smaller than window size for ease of portability
WINDOWHEIGHT = disp.current_h
size = [WINDOWWIDTH, WINDOWHEIGHT]

# DEBUG Defaults  (These generally are fed to Png.py from NeuroTrainer.py; if you run Png.py alone, these values are used.

deviance = 0.5  # DEBUG default for stdev of target Hz baseline data
HiDev = 0.5  # DEBUG default for stdev of Hi noise freq baseline data
LoDev = 0.5  # DEBUG default for stdev of Lo noise freq baseline data
Threshold = 1.0  # EEG threshold for changing NFT parameter
HiNoise = 1.0  # High amplitude noise amplitude; Dummy value for the electrode
LoNoise = 1.0  # Low amplitude noise; Dummy value for the electrode
TargetVal = 0  # Signal amplitude; Dummy value for the electrode
SPTruVal = 0  # Value that gets exported from the visualizer
successjar = 0
CONTROL = False  # This decides whether this running of the experiment is real or not.
ControlFile = 'No control selected'

# These are the time intervals for the training in seconds.
BlocInterval = 100000  # 300
FixationInterval = 60  # 180
if alpha == True:
    FixationInterval = 60
# Flags for high and low noise; false until noise thresholds are passed.
HighNoiseFlag = False
LowNoiseFlag = False

# Debug
DebugFlag = False

resultsarray = []
NEXT = False
Record = False

# The number of pixels in pygame line functions, by default
LINETHICKNESS = 10

# Initialize the sound engine then load a sound
pygame.mixer.init()
coin = pygame.mixer.Sound('mariocoin.wav')

# Stars Parameters
MAX_STARS = 200
STAR_SPEED = 1
stage = 0

# Set up the colours (RGB values). static variables
BLACK = (0, 0, 0)
GREY = (190, 190, 190)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
RED = (255, 0, 0)
CYAN = (52, 221, 221)
BLUE = (0, 95, 235)
VIOLET = (128, 0, 128)
TEXTCOLOR = BLACK

# Baselining variable declarations; dummy values
output = 0
HiOutput = 0
LoOutput = 0
consolidatedoutput = []
consolidatedhi = []
consolidatedlo = []

TMSFlag = True

''' This function draws and colors the reticle as is appropriate for the stage of a given round.
    This means it shifts to RED when it's nearly time for stimulation (real or simulated), and 
    that it shifts to BLUE when it's time for the participant to respond as best as they can. -SP '''


def reticle(color):
    pygame.draw.line(DISPLAYSURF, color, ((WINDOWWIDTH / 2), WINDOWHEIGHT / 2 - 40),
                     ((WINDOWWIDTH / 2), WINDOWHEIGHT / 2 + 40), (int(LINETHICKNESS * 1.5)))
    pygame.draw.line(DISPLAYSURF, color, ((WINDOWWIDTH / 2 - 40), WINDOWHEIGHT / 2),
                     ((WINDOWWIDTH / 2 + 40), WINDOWHEIGHT / 2), (int(LINETHICKNESS * 1.5)))


''' This is both the initial prompt and the breaks between blocks.  This basic structure has governed NFT of my design since
    the days of Emotiv.  I am still struck with the feeling that this could have been done more elegantly.  But we must live
    with our inadequacies as individuals in this life, and no matter who we may have become today, we cannot entirely erase our
    more limted selves from the past.  -SP'''


def Pausepoint(stage, score):
    # These are scores we want to keep

    global score1
    global score2
    global score3
    global score4
    global ontimer
    global ontime
    global successflag
    global successjar
    global Level
    global remainder
    global ControlRecording
    global ControlFile

    # Black out everything on the screen
    DISPLAYSURF.fill(GREY)

    '''This stage mechanism is another throwback.  Note that stage -1 is where we go when a person is clicking to position
    phosphenes because no phosphene was given through the "input phosphene" function in the GUI.  -SP'''
    if stage == -1:
        resultSurf = SCOREFONT.render('Phosphene Testing Round', True, TEXTCOLOR)

    if stage == 0:
        if time.time() < initialization:  # if I don't make a 5 scond delay, things go funny
            resultSurf = SCOREFONT.render('PLEASE WAIT WHILE INITIALIZING', True, TEXTCOLOR)
        else:
            if CONTROL == True or ControlRecording == True:
                resultSurf = SCOREFONT.render('BASELINE OR TMS LOCALIZATION', True, TEXTCOLOR)
            else:
                resultSurf = SCOREFONT.render('BASELINE OR TMS LOCALIZATION', True, TEXTCOLOR)
    if stage == 1:
        resultSurf = SCOREFONT.render('PRESS NEXT TO BEGIN STAGE 1', True, TEXTCOLOR)

    ''' this displays the text that is specified by the stage above. -SP'''
    resultRect = resultSurf.get_rect()
    resultRect.center = (WINDOWWIDTH / 2, WINDOWHEIGHT / 2 - 300)
    DISPLAYSURF.blit(resultSurf, resultRect)


# BASELINING FIXATION CROSS
def fixation(recordtick):
    # Clear the screen
    DISPLAYSURF.fill(GREY)
    # Draw the reticle
    reticle(TEXTCOLOR)


# Draws the arena the game will be played in.  Unused for now, could be populated if useful later
def drawArena():
    DISPLAYSURF.fill(GREY)
    reticle(TEXTCOLOR)


# draws a sprite for the circle.  this function was originally used for the glider
def drawSprite(b):
    # Stops it from going too far left
    if b.rect.right > WINDOWWIDTH - LINETHICKNESS + 90:
        b.rect.right = WINDOWWIDTH - LINETHICKNESS + 90
    # Stops sprite moving too far right
    elif b.rect.left < LINETHICKNESS:
        b.rect.left = LINETHICKNESS
    DISPLAYSURF.blit(b.image, b.rect)  # this draws the image onto the display surface


# Displays the current score on the screen.
def displayScore(score):
    global resultarray
    resultSurf = SCOREFONT.render('Score = %s' % (score), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.center = (WINDOWWIDTH / 2, 40)
    DISPLAYSURF.blit(resultSurf, resultRect)


'''This one is an artifact I also didn't have the heart to eliminate, in case it came in useful to try to display things
in debug mode.  Only thing is, it has been defanged-- all its useful functions are gone.  -SP'''


def displayDEBUG():
    global VoltMax
    global VoltMin
    global VoltBaseline
    global stage
    print 'deb'

    resultSurf = BASICFONT.render('stage = %s' % (stage), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (1165, 190)
    DISPLAYSURF.blit(resultSurf, resultRect)


''' This is the loop of PyGame that actually drives the experiment.  I would like you to take note of the collosal list of global variables.
    This is probably really stupid practice, but again, we are looking at the legacy of my early work when I didn't really understand
    the proper way to build interaction between different objects.  It works, but it's unsightly, and I haven't had the nerve to even
    prune away some of the variables that serve no purpose in this particular paradigm.  It's harmless, but unaesthetic.  -SP'''


# Main function
def main():
    #Start Pygame
    pygame.init()

    global DISPLAYSURF

    ##Font information
    global BASICFONT, BASICFONTSIZE
    global SCOREFONTSIZE, SCOREFONT

    global DebugFlag
    global RecordBypass
    global stage
    global consolidatedoutput
    global consolidatedhi
    global consolidatedlo
    global HiOutput
    global LoOutput
    global initialization
    global Level
    global ontime
    global successflag
    global successtimer
    global successjar
    global Threshold
    global ContinualSuccessTimer
    global FirstSuccessTimer
    global CONTROL
    global TargetVal
    global remainder
    global countdown
    global OutputFilename
    global BlocInterval
    global FixationInterval
    global NEXT
    global ControlRecording
    global CB1
    global C1
    global CB2
    global C2
    global CB3
    global C3
    global CB4
    global C4
    global VoltMedian
    global VoltMax
    global VoltMin
    global VoltBaseline
    global consolidatedloNext
    global consolidatedhiNext
    global consolidatedoutputNext
    global Record
    global LeftTag
    global RightTag
    global resultarray
    global grandresultarray
    global Alphas
    global Alphamax
    global pausetime
    global alpha
    global TMSFlag
    global invisibleflag
    global tms
    global pos
    global trialnumber

    '''These are all dynamic variables.  The empty arrays will be filled with results.  The flags can be manipulated with the buttons on the 
    console.  -SP'''
    invisibleflag = False
    grandresultarray = []
    resultarray = []
    LeftTag = False
    RightTag = False
    # Hopefully this will be read from the recording function at the baseline stages.
    RecordBypass = False

    moveflag = False

    # This is the period of time the threshold is surpassed, starting at zero:
    ontime = 0

    recordtick = 0
    countdown = 0

    # For the control period, these are dummy values.  They will be replaced by the real ones after the baseline.
    ControlIndex = 0
    Alphamax = 10

    '''This fires the TMS wand when the main round starts, if TMS is set to true.  This is a workaround of a strange bug that causes the TMS 
    to fire twice, the first time it is sent a command from the computer.  Puzzling, and an obstacle besides.  -SP'''
    if TMSFlag:  # This is for when the TMS is set to fire.  Do a test fire real quick
        tms = CCDLtms.TMS()  # this calls a tms object from the CCDLtms library, courtesy of Darby
        tms.tms_arm()  # this actually fires the TMS

    # 5 seconds are needed for the data stream to connect properly.
    initialization = time.time() + 5

    # Initializing the font values
    BASICFONTSIZE = 20
    SCOREFONTSIZE = 40
    BASICFONT = pygame.font.Font('freesansbold.ttf', BASICFONTSIZE)
    SCOREFONT = pygame.font.Font('freesansbold.ttf', SCOREFONTSIZE)
    Level = 0  # this is the starting point of threshold challenge.

    '''These are dummy values for voltage based thresholds.  They will be replaced by true inputs almost instantaneously. 
    It's the 'almost' that's the kicker here: without these dummy values, the whole thing crashes.  -SP'''
    VoltMax = 1001
    VoltMedian = 1000
    VoltMin = 999
    VoltBaseline = 1000
    VoltMedianArrayNext = []

    # When reading from the control, this time mark will be used for a timing function:
    ControlTimer = time.time() + .25

    # Flags for whether to quit or pause; starts paused.
    quittingtime = False
    pausetime = True
    Disconnect = False
    LastDISCONNECT = False

    # This is used in counting success time; the "success time" counter goes forward only if this is true
    successflag = False

    # Initialize the pygame FPS clock
    FPSCLOCK = pygame.time.Clock()

    # Set the size of the screen and label it
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('NeuroFeedback')

    # Start with 0 points
    score = 0

    '''These are the sprite features.'''
    Phos = pygame.sprite.Sprite()  # initializes the phosphene image as a sprite
    Phos.image = pygame.image.load("images/Phos.png").convert_alpha()  # this formats the image into something compatible with the surface
    Phos.rect = Phos.image.get_rect()  # this gets details about the instruction sprite, such as size
    Phos.rect.center = [10000,
                        10000]  # this puts the sprite far out of sight by default.  It moves when either defining it with mouse clicks, or by typing in the coordinates.

    '''This is legacy code.  If we wanted soemthing different for "no phosphene", this is how we would do it.'''
    NoPhos = pygame.sprite.Sprite()
    NoPhos.image = pygame.image.load("images/NoPhos.png").convert_alpha()
    NoPhos.rect = NoPhos.image.get_rect()
    NoPhos.rect.center = [10000, 10000]

    '''This is for the orb.'''
    b = pygame.sprite.Sprite()  # define parameters of glider sprite
    b.image = pygame.image.load("images/orb.png").convert_alpha()  # Load the glider sprite
    b.rect = b.image.get_rect()  # use image extent values
    b.rect.center = [WINDOWWIDTH / 2, WINDOWHEIGHT / 2]  # put the image in the center of the player window

    '''Let the games (loop) begin!  Once this is initiated, which is nearly instantaneously after the main loop is initialized through the MainGui's righthand buttons, this
    will continue to cycle until the game is ended. -SP'''
    while True:
        # Checks if the headset is connected
        # When disconnect first happens:


        '''This portion handles events such as button presses, pressing the 'x' to close the window, and mouse clicks.  The debug and control modes are legacy features.
        Expand or delete as you see fit.  -SP'''
        # Processes game events like quitting or keypresses
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                f.close()
                if ControlRecording == False:
                    ses.close()
                else:
                    con.close()
                quittingtime = True
                break

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                # this condition is for if a mouse click happens during the maze response period
                if stage == 0 and not pausetime:
                    Phos.rect.center = pos
                    NoPhos.rect.center = pos

            # This portion does keypresses
            if event.type == pygame.KEYDOWN:  # press space to terminate pauses between blocs
                if event.key == pygame.K_d:
                    DebugFlag = not DebugFlag
                if event.key == pygame.K_SPACE:
                    if pausetime == True and stage != 5:
                        NEXT = True



                        # If the control key is pressed
                if event.key == pygame.K_q:
                    if stage == 0:
                        if pausetime == True:
                            print("CONTROL mode initiated.")
                            CONTROL = True
                if event.key == pygame.K_p:
                    if stage == 0:
                        BlocInterval = 300  # 300
                        FixationInterval = 4  # 180
                        print('Debug values enabled')

        # This checks SPTruVal, which it should be receiving from the Visualizer script.
        '''This variable is key.  SPTruVal is the array of spectral data for Mu.'''
        if alpha == False:
            TargetVal = SPTruVal

        '''The following is for when the stage is triggered by using the Visualizer interface.  This is made to happen by hitting
        'next round'.  It also happens when you give the X Y coordinates.  It is the all purpose clearing of variables for
        the start of a new round, the same as in other NFT paradigms.  All of those empty arrays are used for calculating averages at the end of the round,
        but I think they are actually artifacts from previous versions I never got rid of.  I just haven't had the time or inclination to figure out 
        how to remove these things without making it all crash.  -SP'''
        if NEXT and stage != 0:
            if pausetime == True:
                pausetime = False
                NEXT = False
                RecordBypass = False  # Likely unnecessary, but I'm playing it safe for now.  This variable makes sure that the means through which recording lets you progress is stopped right after 1 step forward.
                ontime = 0  # This sets the beginning period of time to zero
                countdown = time.time() + BlocInterval  # This is the number of seconds in a Glider game block; set to 300 when done debugging
                FirstSuccessTimer = time.time()
                score = 0
                successjar = 0
                remainder = 0
                moveflag = False
                recordtick = time.time() + .25  # Collecting values at a 250 ms interval; decrease to up sampling rate
                consolidatedoutput = []
                consolidatedhi = []
                consolidatedlo = []
                consolidatedoutputNext = []
                consolidatedhiNext = []
                consolidatedloNext = []
                ControlCountdown = time.time()
                ControlTimer = time.time()
                VoltMedianArrayNext = []
                resultarray = []
                trials = []
                b.rect.center = [WINDOWWIDTH / 2, WINDOWHEIGHT / 2]
                # This is for the baselining stages at the beginning and end


                if stage == 0:
                    countdown = time.time() + FixationInterval  # Number of seconds for Baseline block
                else:
                    LeftRightTimer = time.time() + 5
                    LeftFlag = True
                    LRPauseFlag = True

                stage = stage + 1  # this makes the stage go forward a step.

        '''This is a disconnect function I wrote for the emotiv, that I think in principle could also work for a disconnected BrainAmp.
            However, if the BrainAmp is disconnected, you have much bigger problems than you would if it were the emotiv in the same
            situation.  Accordingly, this is mostly legacy.  -SP'''
        if DISCONNECT == True:
            print('DISCONNECT' + str(round(time.time(), 1)))
            if LastDISCONNECT == False:
                PauseStart = time.time()
                time.sleep(.1)
                LastDISCONNECT = True
                pygame.display.flip()  # needed to draw the >|<~STARS~>|<
                pygame.display.update()  # Refresh all the details that do not fall under the "flip" method. SP NOTE: I don't understand the difference very well.

                FPSCLOCK.tick(FPS)
                continue
            else:  # If disconnection remains, just skip everything
                time.sleep(.250)
                pygame.display.flip()  # needed to draw the >|<~STARS~>|<
                pygame.display.update()  # Refresh all the details that do not fall under the "flip" method. SP NOTE: I don't understand the difference very well.

                FPSCLOCK.tick(FPS)
                continue
        if DISCONNECT == False:
            if LastDISCONNECT == True:
                PauseTotal = time.time() - PauseStart
                recordtick = recordtick + PauseTotal
                countdown = countdown + PauseTotal
                initialization = initialization + PauseTotal
                ContinualSuccessTimer = ContinualSuccessTimer + PauseTotal
                FirstSuccessTimer = FirstSuccessTimer + PauseTotal
                ontime = ontime + PauseTotal
                successjar = successjar + PauseTotal
        LastDISCONNECT = DISCONNECT

        '''This condition is met when X Y coordinates are being determined by clicking on the screen.  You get a readout of the X Y values in the print statement below.'''
        if stage == -1 and RecordBypass == True:
            if not pausetime:
                pausetime = False
                stage = stage + 1
                RecordBypass = False
                print 'registered pos as ', pos

            '''This is another way to go to the baseline period: the recordbypass variable is called upon when you give the X Y coordinates manually.  This function is nearly identical to the 'NEXT' 
            set of variables.  Candidly, I should have made them both into a singular function that could be called upon, but there are fundamental structural reasons (due to building on a faulty 
            origin point) I cannot do that without rewriting things.  You're welcome to do that dirty work, if you wish.  I regret not doing it myself.  -SP'''
        else:
            # Inelegant; make a module for this later so as to encompass keypresses
            if stage == 0 and RecordBypass == True:
                print('outputfilename is ' + OutputFilename)
                f = open(OutputFilename, 'w')  # This should have the custom name plugged in later;

                pausetime = False
                RecordBypass = False  # Can't have the recordbypass triggering prematurely for the second recording.

                ontime = 0  # This sets the beginning period of time to zero
                countdown = time.time() + BlocInterval  # This is the number of seconds in a Glider game block; set to 300 when done debugging
                FirstSuccessTimer = time.time()
                score = 0
                recordtick = time.time() + .25  # Collecting values at a 250 ms interval; decrease to up sampling rate
                consolidatedoutput = []
                consolidatedhi = []
                consolidatedlo = []
                consolidatedoutputNext = []
                consolidatedhiNext = []
                consolidatedloNext = []
                VoltMedianArray = []
                ControlCountdown = time.time()
                ControlTimer = time.time()
                Phos.rect.center = pos
                NoPhos.rect.center = pos
                # This is for the baselining stages at the beginning and end
                if stage == 0:
                    Record = True
                    countdown = time.time() + FixationInterval  # Number of seconds for Baseline block

                stage = stage + 1  # time to go to the next stage

        # This is what happens when you hit the invisible ball button.  It moves the y coordinate of the orb far out of the screen.
        if invisibleflag == True:
            b.rect.y = 10000


            # needed to exit the program gracefully
        if quittingtime == True:
            break

        # If the game is at a pausing point, such as the beginning screen
        if pausetime == True:
            Pausepoint(stage, score)
            pygame.display.update()
            FPSCLOCK.tick(FPS)
            continue

        if stage == 0:
            drawArena()
            fixation(TEXTCOLOR)
            DISPLAYSURF.blit(Phos.image, Phos.rect)
            pygame.display.flip()  # needed to draw the >< ~STARS~ ><
            pygame.display.update()  # Refresh all the details that do not fall under the "flip" method. SP NOTE: I don't understand the difference very well.
            FPSCLOCK.tick(FPS)
            continue

        NEXT = False  # This prevents a multi-pressing problem
        '''Every quarter of a second, the voltage and spectral values are recorded for a control file.  this is a legacy function that could be used again for controls, though in the 
        context of the BIAV, it makes no sense to have controls.  It's hard enough to get people to perform the task correctly when training them under optimal conditions.  -SP'''
        if time.time() >= recordtick:
            recordtick = time.time() + .25  # This collects data every 250 ms.  Lower this number for higher resolution
            if stage == 1 or stage == 6 or (
                            VoltBaseline < VoltMin + 400 and VoltBaseline > VoltMax - 400 and HighNoiseFlag == False and LowNoiseFlag == False):
                # print('Voltmin', VoltMin, 'Voltmax', VoltMax, 'VoltBaseline', VoltBaseline)
                consolidatedoutputNext.append(TargetVal)

                # else:
                # if alpha == True:
                #    TargetVal = np.mean(densityA[Alphamax-2:Alphamax+3])

            consolidatedhiNext.append(HiNoise)
            consolidatedloNext.append(LoNoise)
            VoltMedianArrayNext.append(VoltMedian)

        if stage == 2 and len(resultarray) == trialnumber:
            pygame.quit()
            f.write('\ntrials:,')
            for i in resultarray:
                f.write(str(i))
                f.write(',')
            f.close()
            quittingtime = True
            break

        '''If the countdown timer reaches zero (in other words, if the duration of the stage is completed)
        this should only happen during the baseline.'''
        if time.time() > countdown:
            Record = False

            # if stage == 2 or stage == 3 or stage == 4 or stage == 5:

            ControlIndex = 0

            consolidatedoutput = consolidatedoutputNext
            consolidatedhi = consolidatedhiNext
            consolidatedlo = consolidatedloNext
            VoltMedianArray = VoltMedianArrayNext

            # What follows is a series of print statements that tell the administrator about previous sessions.
            # These values are also written to a text file for future examination.

            '''Take note of the fact that this is only ever seen after the baseline in this particular NFT paradigm.
            The specific features of Alpha, because we use individual alpha, are spelled out in great detail if Alpha
            is true.  For Mu, this felt less necessary.  All of these things are written into the metadata file. -SP'''
            print 'position is ', pos
            f.write('Position: ,' + str(pos[0]) + ',' + str(pos[1]) + '\n')
            f.write('LR Sequence 21 forward:,')
            for i in LRValues:
                f.write(str(i) + ',')
            f.write('\n')
            print("STAGE " + str(stage))  # Just printing the stage

            output = sum(consolidatedoutput) / len(consolidatedoutput)
            f.write(str(output) + ',')
            print 'before alpha'
            if alpha == True and stage == 1:
                print 'after alpha'
                # print Alphas
                Alphas = np.mean(Alphas, axis=0)  # from mean
                # Alphas = np.median(Alphas, axis=0)#From Median

                print 'median ', np.median(Alphas, axis=0), ' mean is ', np.mean(Alphas, axis=0)
                # print 'probalo?'
                AlphasTrue = Alphas[2:-2]
                print 'alphas are ', Alphas
                Alphamax = np.argmax(AlphasTrue)
                Alphamax = Alphamax + 2
                print 'Alpha max index is ', Alphamax, ' and alpha range is ', Alphamax - 2, ' ', Alphamax + 3
                AlphaDensity = np.mean(
                    Alphas[Alphamax - 2:Alphamax + 3])  # the range is -2 from the true value to +2 from the true value
                Alphamax = Alphamax + 6

                print "alpha maximum is ", str(Alphamax), ' Hz'
                f.write('\nmax alpha:,' + str(Alphamax) + '\n')

                print 'Alphas are ', Alphamax - 2, ' to ', Alphamax + 2

                # print 'Alpha powers are ',
                # print 'true Alpha density is ', AlphaDensity
                output = AlphaDensity
                f.write('Alpha Power Avg:,' + str(AlphaDensity) + '\n')
                print 'Alpha Power: ', AlphaDensity
                Threshold = AlphaDensity

                '''If Alpha is true, we want the 'output' and 'Threshold' to contain the spectral values for alpha.'''
            elif alpha == True:
                output = AlphaDensity
                Threshold = AlphaDensity

            '''Note that output is defined as the mu output earlier in the script if alpha is false.'''
            if alpha == False:
                Threshold = output
                print 'Alpha is false'
            print("Data Baseline is: " + str(output))

            '''These outputs are all both printed to the terminal and also written into the metadata file.'''
            deviance = np.std(consolidatedoutput)
            f.write(str(deviance) + ',')
            print("Data baseline STDEV:" + str(deviance))

            HiOutput = sum(consolidatedhi) / len(consolidatedhi)
            f.write(str(HiOutput) + ',')
            print("High Freq. Noise Baseline: " + str(HiOutput))

            HiDev = np.std(consolidatedhi)
            f.write(str(HiDev) + ',')
            print("High Freq. Noise STDEV: " + str(HiDev))

            LoOutput = sum(consolidatedlo) / len(consolidatedlo)
            f.write(str(LoOutput) + ',')
            print("Low Freq. Noise Baseline is: " + str(LoOutput))

            LoDev = np.std(consolidatedlo)
            f.write(str(LoDev) + ',\n')
            print("Low Freq. Noise STDev is: " + str(LoDev))

            pausetime = True

            f.write('\n')  # New line
            f.close()
            f = open(OutputFilename, 'a')
            b.rect.y = WINDOWHEIGHT / 2

            # This is for the voltage values
            VoltBaseline = np.mean(VoltMedianArray)
            print(
            str(round(np.mean(VoltMedianArray), 2)) + ' v is the average of the Median Voltages.')  # falseflag

            continue

        # baselining at stages 1 and 6
        if stage == 1:
            fixation(recordtick)
            # displayDEBUG(round(TargetVal,3))
            pygame.display.update()

            FPSCLOCK.tick(FPS)
            continue

        # This refreshes the arena
        drawArena()
        if alpha == True:
            TargetVal = np.mean(densityA[Alphamax - 2:Alphamax + 3])

        ''' Debug mode allows you to see the EEG trace.  It is the one utility it serves.  This can be useful for making sure you are 
        truly measuring what you think you are measuring. after all, if you tap the correct electrode and you see no changes, odds are
        something is wrong with how you have ID'd the target electrode.  -SP '''
        if DebugFlag == True:

            EEGTimeSeries = SMRTimeSeries
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0  # This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1  # We go through each point.
                numpairs.append([500 + timeseriesindex, x * .75 + 725])
            pygame.draw.lines(DISPLAYSURF, CYAN, False, numpairs, 1)

            EEGTimeSeries = SMRTimeSeries2
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0  # This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1  # We go through each point.
                numpairs.append([500 + timeseriesindex, x * 0.75 + 825])
            pygame.draw.lines(DISPLAYSURF, YELLOW, False, numpairs, 1)

            EEGTimeSeries = AlphaSeries
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0  # This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1  # We go through each point.
                numpairs.append([500 + timeseriesindex, x * 0.75 + 925])
            pygame.draw.lines(DISPLAYSURF, WHITE, False, numpairs, 1)

            if alpha == False:
                EEGTimeSeries = SMRDens
                timeseriesindex = 0  # This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1  # We go through each point.
                    yval = 925 - (x) * 3
                    if yval < 700:
                        yval = 700
                    numpairs.append([1100 + timeseriesindex * 50, yval])
                pygame.draw.lines(DISPLAYSURF, CYAN, False, numpairs, 1)

                EEGTimeSeries = SMRDens2
                timeseriesindex = 0  # This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1  # We go through each point.
                    yval = 925 - (x) * 3
                    if yval < 700:
                        yval = 700
                    numpairs.append([1100 + timeseriesindex * 50, yval])
                pygame.draw.lines(DISPLAYSURF, YELLOW, False, numpairs, 1)

            if alpha == True:
                EEGTimeSeries = densityA[Alphamax - 2:Alphamax + 3]
                timeseriesindex = 0  # This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1  # We go through each point.
                    yval = 925 - (x) * 3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100 + timeseriesindex * 50, yval])
                pygame.draw.lines(DISPLAYSURF, WHITE, False, numpairs, 1)

                EEGTimeSeries = densityA[Alphamax - 2:Alphamax + 3]
                timeseriesindex = 0  # This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1  # We go through each point.
                    yval = 925 - (Threshold) * 3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100 + timeseriesindex * 50, yval])
                pygame.draw.lines(DISPLAYSURF, RED, False, numpairs, 1)

                EEGTimeSeries = densityA[Alphamax - 2:Alphamax + 3]
                timeseriesindex = 0  # This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1  # We go through each point.
                    yval = 925 - (np.mean(densityA[Alphamax - 2:Alphamax + 3])) * 3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100 + timeseriesindex * 50, yval])
                pygame.draw.lines(DISPLAYSURF, CYAN, False, numpairs, 1)

        ''' The moveflag is a condition that is met during the periods that the cross is blue.  it should respond to whether you are above or below the target NFT threshold.
        whether that is a good thing or a bad thing is contingent on what kind of round it is.  -SP'''
        if moveflag == True:
            if TargetVal < Threshold:  # This is a success state.
                b.rect.x = b.rect.x + 3  # It is counterintuitive, but lower numbers means higher on the screen.
                b.image = pygame.image.load("images/orb.png").convert_alpha()
                # successflag = True
            else:  # The only other possibility is that there are no noise flags, but the signal band isn't high enough to pass threshold. This is the second of 2 failure states.
                b.image = pygame.image.load("images/orb.png").convert_alpha()
                b.rect.x = b.rect.x - 3

        ''' "Those who do not move, do not feel their chains."  -Rosa Luxemburg  
        Also, if the time is wrong for that ball to move, we want to make sure that it doesn't keep moving.  From here on out, we see that this is the portion of the code 
        that governs the stages within the NFT: is it time for the stimulation?  is it time for the blue cross, response time?  is it somewhere in between?  
        This chunk of code is what governs that process.  -SP '''
        moveflag = False
        color = TEXTCOLOR
        if LeftRightTimer < time.time():
            if LRPauseFlag == True:
                print 'pause is over'
                Record = True
                if len(resultarray) < 19:
                    LeftFlag = not LeftFlag  # The first 20 rounds alternate between left and right
                else:
                    LeftFlag = not LRValues[(len(
                        resultarray) - 20)]  # The remaining rounds are pulled from the random list defined in the beginning.

                LRPauseFlag = False  # this is the transitional pausing between types of rounds.

                if LeftFlag == True:
                    LeftTag = True
                else:
                    RightTag = True
                LeftRightTimer = time.time() + ResponsePeriod  # Remember responseperiod?  it's defined near the top of the file.  It is how long a person has to respond to NFT.
            else:
                print 'pause'
                # Record = False
                LRPauseFlag = True
                LeftRightTimer = time.time() + DelayPeriod  # This is how much time there is between types of rounds.
                if LeftFlag == True:
                    if b.rect.centerx < WINDOWWIDTH / 2:
                        score = score + 1
                        coin.play()  # This sound means the person did the right thing.  b.rect.centerx is the x position.  If the leftflag is true, the person wants the ball to be on the left side.
                        resultarray.append(1)
                        grandresultarray.append(1)
                    else:
                        '''#Take note of the fact that in the first 20 rounds, this Threshold can be adjusted.  It is shifted in the opposite direction of failure, 
                        making it harder to repeat the same mistake, but easier to make the opposite type.  The increment of this change gets smaller with each 
                        succesive round.  The goal is to converge on the optimal middle point of a subject's performance.'''
                        if len(resultarray) < 20:
                            Threshold = Threshold - float(20 - (len(resultarray))) / 20
                            print 'Threshold is now lower: ', Threshold
                        resultarray.append(0)
                        grandresultarray.append(0)
                if LeftFlag == False:  # This all is the mirror image of the leftflag case.  Notice that the next line is opposite of the b.rect.centerx comparison statement above.
                    if b.rect.centerx > WINDOWWIDTH / 2:
                        score = score + 1
                        coin.play()
                        resultarray.append(1)
                        grandresultarray.append(1)
                    else:
                        if len(resultarray) < 20:
                            Threshold = Threshold + float(20 - (len(resultarray))) / 20
                            print 'Threshold is now higher: ', Threshold
                        resultarray.append(0)
                        grandresultarray.append(0)
                percent = np.mean(resultarray)
                print(resultarray)
                print '%s TOTAL PERCENT', (percent), ' of ', len(resultarray)
                print 'Threshold is: ', Threshold



        else:
            if LRPauseFlag == True:
                b.rect.centerx = WINDOWWIDTH / 2

            '''This governs this display of the stim, and the blue cross for response time.'''

            if LRPauseFlag == False:
                if LeftRightTimer < time.time() + 26 and LeftRightTimer > time.time() + 25:
                    color = RED
                    b.rect.centerx = WINDOWWIDTH / 2
                    if LeftRightTimer < time.time() + 25.1 and LeftRightTimer > time.time() + 25:
                        if LeftFlag == True:
                            if TMSFlag:
                                tms.tms_fire(i=LOW_INTENSITY)
                            else:
                                print 'No phos'
                                # DISPLAYSURF.blit(NoPhos.image, NoPhos.rect)
                        else:
                            if TMSFlag:
                                tms.tms_fire(i=HIGH_INTENSITY)
                            else:
                                DISPLAYSURF.blit(NoPhos.image, Phos.rect)  # was Phos
                                # DISPLAYSURF.blit(resultSurf, resultRect)
                if LeftRightTimer > time.time() + 15:
                    b.rect.centerx = WINDOWWIDTH / 2
                else:
                    color = BLUE
                    moveflag = True
                    # LRPauseFlag = True

        '''This is where the sprite and reticle actually change as a consequence of things declared above.'''
        drawSprite(b)
        reticle(color)

        # Displays the score
        displayScore(score)

        # Displays debug information
        if DebugFlag == True:
            displayDEBUG()

        pygame.display.flip()  # needed to draw the >< ~STARS~ ><
        pygame.display.update()  # Refresh all the details that do not fall under the "flip" method. SP NOTE: I don't understand the difference very well.

        FPSCLOCK.tick(FPS)  # Tells the game system that it is not untouched by the inexorable march of time


if __name__ == '__main__':
    main()
