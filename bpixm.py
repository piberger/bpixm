#!/usr/bin/env python

import os
import termios
import sys
import tty
import ConfigParser
import shutil
import glob
import datetime

from BpixLayer import BpixLayer
import BpixUI.BpixUI
from BpixUI.BpixUI import *

class BpixMountTool():

    def __init__(self):

        self.globalConfig = ConfigParser.ConfigParser()
        self.globalConfig.read('config.ini')
        self.dataDirectoryBase = 'data/'
        self.revisionTag = ''

        try:
            self.DisplayWidth = int(self.globalConfig.get('System', 'DisplayWidth'))
        except:
            self.DisplayWidth = 80

        self.InitializeModuleData()

        self.Operator = self.globalConfig.get('System', 'Operator')
        self.Log("-"*80, Category='START')
        self.Log("started, operator: %s"%self.Operator, Category='START')
        self.Log("-"*80, Category='START')


    def InitializeModuleData(self):
        self.UnsavedChanges = False
        self.dataDirectory = self.dataDirectoryBase + self.globalConfig.get('System', 'DataRevision') + '/'
        if not os.path.isfile(self.dataDirectory + 'config.ini'):

            dataDirectories = [x.strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
            if len(dataDirectories) > 0:
                headRevision = max([int(x) for x in dataDirectories if x.isdigit()])
                self.globalConfig.set('System', 'DataRevision', headRevision)
                self.dataDirectory = self.dataDirectoryBase + '%d/'%headRevision

                self.ShowWarning('could not load config REV, use %d (HEAD) instead'%(headRevision))
                self.WriteGlobalConfig()
            else:
                self.ShowWarning('no data directories existing!')

        self.config = ConfigParser.ConfigParser()
        self.config.read(self.dataDirectory + 'config.ini')

        self.LayerNames = [x.strip() for x in self.config.get('Layers', 'LayerNames').split(',')]
        self.LayerPlanFileName = self.config.get('Layers', 'LayerPlanFileName')
        self.LayerMountFileName = self.config.get('Layers', 'LayerMountFileName')
        self.Layers = {}
        self.LayersMounted = {}

        for LayerName in self.LayerNames:
            self.Layers[LayerName] = BpixLayer(LayerName, Ladders=int(self.config.get('Layer_%s'%LayerName, 'Ladders')), ZPositions=int(self.config.get('Layer_%s'%LayerName, 'ZPositions')))
            self.LayersMounted[LayerName] = BpixLayer(LayerName+'(mounted)', Ladders=int(self.config.get('Layer_%s'%LayerName, 'Ladders')), ZPositions=int(self.config.get('Layer_%s'%LayerName, 'ZPositions')))

            layerPlanFileName = self.dataDirectory + self.LayerPlanFileName.format(Layer=LayerName)
            if os.path.isfile(layerPlanFileName):
                print "initialize ",LayerName
                self.Layers[LayerName].LoadFromFile(layerPlanFileName)
            else:
                print "config file for",LayerName," does not exist!!"

            layerMountFileName = self.dataDirectory + self.LayerMountFileName.format(Layer=LayerName)
            if os.path.isfile(layerMountFileName):
                print "initialize mounted modules for ", LayerName
                self.LayersMounted[LayerName].LoadFromFile(layerMountFileName)
            else:
                print "mount file for", LayerName, " does not exist!!"

        self.ActiveLayer = self.config.get('Layers', 'ActiveLayer')

        try:
            self.revisionTag = self.config.get('Revision', 'Tag')
        except:
            self.revisionTag = ""


    def FlagUnsaved(self):
        self.UnsavedChanges = True


    def ShowError(self, Message):
        sys.stdout.write('\x1b[31m')
        self.PrintBox("ERROR: " + Message)
        sys.stdout.write('\x1b[0m')
        self.Log(Message=Message, Category='ERROR')


    def ShowWarning(self, Message):
        sys.stdout.write('\x1b[31m')
        self.PrintBox("WARNING: " + Message)
        sys.stdout.write('\x1b[0m')
        self.Log(Message=Message, Category='WARNING')


    def Log(self, Message, Category = 'LOG'):
        logString = "{Date} [{Category}] {Message}\n".format(Date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), Category=Category, Message=Message)
        logFileName = self.dataDirectory + 'bpixm.log'
        with open(logFileName, "a") as logFile:
            logFile.write(logString)


    def WriteGlobalConfig(self):

        with open('config.ini', 'wb') as configfile:
            self.globalConfig.write(configfile)
        self.globalConfig.read('config.ini')


    def SaveLocalConfiguration(self):
        with open(self.dataDirectory + 'config.ini', 'wb') as configfile:
            self.config.write(configfile)

        self.config.read(self.dataDirectory + 'config.ini')


    def SaveConfiguration(self):
        Success = True
        for LayerName in self.LayerNames:
            layerMountFileName = self.dataDirectory + self.LayerMountFileName.format(Layer=LayerName)
            if self.LayersMounted[LayerName].SaveAs(layerMountFileName):
                print "saved configuration for ", LayerName
                self.Log("saved configuration for %s"%LayerName, "CONFIG")
            else:
                self.ShowError("could not save configuration for %s"%LayerName)
                Success = False

        try:
            self.config.set('Layers', 'ActiveLayer', self.ActiveLayer)
            self.SaveLocalConfiguration()
        except:
            Success = False

        if Success:
            self.UnsavedChanges = False
        return Success


    def CreateNewRevision(self):
        self.SaveConfiguration()
        Success = True
        oldRevision = self.globalConfig.get('System', 'DataRevision')

        try:
            dataDirectories = [x.strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
            nextRevision = 1 + max([int(x) for x in dataDirectories if x.isdigit()])
            dataDirectoryNew = self.dataDirectoryBase + '%d/'%nextRevision
        except:
            print "can't determine data revision!!!"
            Success = False

        if Success:
            try:
                shutil.copytree(self.dataDirectory, dataDirectoryNew)
            except:
                print "can't copy to new location:", dataDirectoryNew
                Success = False

        if Success:
            self.dataDirectory = dataDirectoryNew
            self.globalConfig.set('System', 'DataRevision', nextRevision)
            self.WriteGlobalConfig()

            self.Log("CREATED REV {newRev} out of REVISION {oldRev}".format(newRev = nextRevision, oldRev=oldRevision), Category="CONFIG")

        return Success


    def EnterMainMenu(self):
        while True:

            revisionInfo = ''
            try:
                dataDirectories = [x.strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
                headRevision = max([int(x) for x in dataDirectories if x.isdigit()])
                try:
                    if int(headRevision) == int(self.globalConfig.get('System', 'DataRevision', 1)):
                        revStatus = 'HEAD'
                    else:
                        revStatus = 'BEHIND HEAD (%d)'%headRevision
                except:
                    revStatus = '?'
                try:
                    dataRev = self.globalConfig.get('System', 'DataRevision')
                except:
                    dataRev = '?'
                revisionInfo = 'on REV {rev} "{tag}", {status}'.format(rev=dataRev, status=revStatus, tag=self.revisionTag)
            except:
                raise

            unsavedInfo = ''
            if self.UnsavedChanges:
                unsavedInfo = "*****UNSAVED CHANGES!*****"

            ret = AskUser(['Main menu',revisionInfo,unsavedInfo],
                          [
                            ['mount','_Mount'],
                            ['view','View _detector status'],
                            ['plan','View mounting _plan'],
                            ['log','Add _log entry'],
                            ['save', 'Sa_ve configuration'],
                            ['step','Save configuration as new revision'],
                            ['revs','Sho_w revisions'],
                            ['selectrevs','Select _revision'],
                            ['tagrevs','Set tag for this revision'],
                            ['select', '_Select Layer (active: %s)' % self.ActiveLayer],
                            ['operator', 'Set _operator (currently: %s)'%self.Operator],
                            ['quit','_Quit']
                          ], DisplayWidth=self.DisplayWidth)
            if ret == 'plan':
                self.EnterViewPlanMenu()
            elif ret == 'view':
                self.EnterViewStatusMenu()
            elif ret == 'select':
                self.EnterSelectLayerMenu()
            elif ret == 'mount':
                self.EnterMountMenu()
            elif ret == 'log':
                self.EnterLogMenu()
            elif ret == 'revs':
                self.EnterRevsMenu()
            elif ret == 'selectrevs':
                self.EnterSelectRevsMenu()
            elif ret == 'tagrevs':
                self.EnterTagRevsMenu()
            elif ret == 'save':
                self.EnterSaveConfigurationMenu()
            elif ret == 'operator':
                self.EnterSetOperatorMenu()
            elif ret == 'step':
                if self.CreateNewRevision():
                    print "new revision created!"
                else:
                    print "could not create new revision!"
            elif ret == 'quit':
                if self.UnsavedChanges:
                    self.ShowWarning("There are unsaved changes!")
                    ret = AskUser("do you really want to quit?",
                                  [
                                      ['no', '_no'],
                                      ['yes', '_yes']
                                  ], DisplayWidth=self.DisplayWidth)

                    if ret == 'yes':
                        return False
                else:
                    return False


    def EnterSetOperatorMenu(self):
        oldOperator = self.Operator
        self.PrintBox('Set new operator (currently: %s)'%oldOperator)
        self.Operator = raw_input()
        self.globalConfig.set('System', 'Operator', self.Operator)
        self.Log('change operator %s -> %s'%(oldOperator, self.Operator))
        self.WriteGlobalConfig()


    def EnterLogMenu(self):
        self.PrintBox("enter lines to write to log file, empty line to go back")
        logString = raw_input()
        while len(logString.strip()) > 0:
            self.Log(logString, Category='USER')
            logString = raw_input()


    def getLastLine(self, fname, maxLineLength=80):
        fp = file(fname, "rb")
        fp.seek(-maxLineLength - 1, 2)  # 2 means "from the end of the file"
        return fp.readlines()[-1]


    def EnterRevsMenu(self):
        self.PrintBox("configuration/data revisions")

        dataDirectories = [x.strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
        headRevision = 1
        if len(dataDirectories) > 0:
            headRevision = max([int(x) for x in dataDirectories if x.isdigit()])

        dataDirectories.sort(key=lambda x: int(x), reverse=True)
        dataDirectories = dataDirectories[0:10]
        for dataDirectory in dataDirectories:
            DateString = '?'
            try:
                LL = self.getLastLine(self.dataDirectoryBase + dataDirectory + '/bpixm.log',200)
                DateString = LL.split('[')[0]
            except:
                pass

            print " REV {Rev}: {Date} {Status}".format(Rev=dataDirectory,Status='(HEAD)' if int(dataDirectory)==headRevision else '',Date=DateString)


    def EnterTagRevsMenu(self):
        self.PrintBox("input new revision tag (current: %s)"%self.revisionTag)
        self.revisionTag = raw_input()
        self.config.set('Revision', 'Tag', self.revisionTag)
        self.SaveLocalConfiguration()


    def SwitchToRevision(self, newRevNr):
        try:
            dataDirectoryNew = self.dataDirectoryBase + '%d/' % int(newRevNr)

            self.dataDirectory = dataDirectoryNew
            self.globalConfig.set('System', 'DataRevision', int(newRevNr))
            self.WriteGlobalConfig()
            self.InitializeModuleData()
            return True
        except:
            self.ShowError("Can't load REV %r" % newRevNr)
            return False


    def EnterSelectRevsMenu(self):
        self.PrintBox("configuration/data revisions")

        dataDirectories = [x.strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
        headRevision = 1
        if len(dataDirectories) > 0:
            headRevision = max([int(x) for x in dataDirectories if x.isdigit()])

        dataDirectories.sort(key=lambda x: int(x), reverse=True)
        dataDirectories = dataDirectories[0:10]
        revs = [['input', 'input number...']]
        for dataDirectory in dataDirectories:
            DateString = '?'
            try:
                LL = self.getLastLine(self.dataDirectoryBase + dataDirectory + '/bpixm.log',200)
                DateString = LL.split('[')[0]
            except:
                DateString = '?'

            revs.append([dataDirectory, " REV {Rev}: {Date} {Status}".format(Rev=dataDirectory,Status='(HEAD)' if int(dataDirectory)==headRevision else '',Date=DateString)])

        ret = AskUser("Select revision to return to", revs, DisplayWidth=self.DisplayWidth)
        if ret == 'input':
            self.PrintBox('Input revision number')
            newRevNr = raw_input()
        elif ret.isdigit():
            newRevNr = int(ret)
        else:
            print "unable to switch to REV "
            return False

        # check for unsaved changes
        OverwriteConfirmed = False
        if self.UnsavedChanges:
            self.ShowWarning("There are unsaved changes!")
            ret = AskUser("do you really want to switch to another parameters revision?",
                          [
                              ['no', '_no'],
                              ['yes', '_yes']
                          ], DisplayWidth=self.DisplayWidth)

            if ret == 'yes':
                OverwriteConfirmed = True
        else:
            OverwriteConfirmed = True

        if OverwriteConfirmed:
            # switch back to revision
            if self.SwitchToRevision(newRevNr):
                #self.Log("switched back to this REV", Category="REV")
                print "switched back to REV ", newRevNr
            else:
                print "could not switch back to REV ", newRevNr


    def PrintBox(self, text):

        print "+%s+" % ('-' * (self.DisplayWidth-2))

        textLines = []
        textLine = ''
        textWords = text.split(' ')
        for textWord in textWords:
            if len(textLine) + len(textWord) + 1 < self.DisplayWidth-5 and len(textWord) > 0 and textWord[-1] == '\n':
                textLine += textWord
                textLines.append(textLine)
                textLine = ''
            elif len(textLine) + len(textWord) + 1 < self.DisplayWidth-5:
                textLine += textWord + ' '
            else:
                textLines.append(textLine)
                textLine = textWord
        if len(textLine) > 0:
            textLines.append(textLine)

        for textLine in textLines:
            print "| %s|" % textLine.ljust(self.DisplayWidth-3)

        print "+%s+" % ('-' * (self.DisplayWidth-2))


    def EnterSaveConfigurationMenu(self):
        ret = AskUser("Save list of mounted modules for all layers?",
                      [
                          ['yes', '_yes'],
                          ['no', '_no']
                      ], DisplayWidth=self.DisplayWidth)

        if ret == 'yes':
            self.SaveConfiguration()


    def EnterViewPlanMenu(self):
        os.system('clear')

        PlannedLayer = self.Layers[self.ActiveLayer]
        self.PrintBox("mounting plan for %s"%self.ActiveLayer)

        ZPositionsString = '               '

        for ZPosition in range(PlannedLayer.ZPositions):
            ZPositionsString += ("Z%d-"%(PlannedLayer.ZPositions - ZPosition - 1)).ljust(7)
        ZPositionsString += '  '
        for ZPosition in range(PlannedLayer.ZPositions):
            ZPositionsString += ("Z%d+"%(ZPosition)).ljust(7)

        print "|%s|"%(ZPositionsString.ljust((self.DisplayWidth-2)))

        for LadderIndex in range(len(PlannedLayer.Modules)):

            LadderName = "L%d" %(LadderIndex+1)
            LadderName = "\x1b[32m%s\x1b[0m" % (LadderName.ljust(10))

            LadderString = '   ' + LadderName
            for i in range(0, 2 * PlannedLayer.ZPositions):
                if i == PlannedLayer.ZPositions:
                    LadderString += '   '

                LadderString += (PlannedLayer.FormatModuleName(PlannedLayer.Modules[LadderIndex][i])).ljust(7)

            print "|%s|"%(LadderString.ljust((self.DisplayWidth+7)))
            LadderIndex += 1

        print "+%s+" % ('-' * (self.DisplayWidth-2))
        print ""


    def EnterViewStatusMenu(self):
        os.system('clear')

        MountingLayer = self.LayersMounted[self.ActiveLayer]
        PlannedLayer = self.Layers[self.ActiveLayer]

        self.PrintBox("status of %s"%self.ActiveLayer)

        ZPositionsString = ' '*15

        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d-"%(MountingLayer.ZPositions - ZPosition - 1)).ljust(7)
        ZPositionsString += '  '
        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d+"%(ZPosition)).ljust(7)

        print "|%s|"%(ZPositionsString.ljust((self.DisplayWidth-2)))

        for LadderIndex in range(len(MountingLayer.Modules)):

            LadderName = "L%d" %(LadderIndex+1)
            LadderName = "\x1b[32m%s\x1b[0m" % (LadderName.ljust(10))

            # compare all mounted modules in the ladder with mounting plan
            LadderString = '   ' + LadderName
            for i in range(0, 2*MountingLayer.ZPositions):
                if i == MountingLayer.ZPositions:
                    LadderString += '   '

                if (MountingLayer.Modules[LadderIndex][i] == PlannedLayer.Modules[LadderIndex][i]) or len(MountingLayer.Modules[LadderIndex][i]) < 1:
                    LadderString += (MountingLayer.FormatModuleName(MountingLayer.Modules[LadderIndex][i])).ljust(7)
                else:
                    LadderString += (MountingLayer.FormatModuleName(MountingLayer.Modules[LadderIndex][i]) + '!').ljust(7)

            print "|%s|"%(LadderString.ljust((self.DisplayWidth+7)))
            LadderIndex += 1

        print "+%s+\n" % ('-' * (self.DisplayWidth-2))


    def GetFormattedHalfLadder(self, HalfLadderModules):
        ret = ' > '
        ModuleNameLength = 5
        EmptyModulePlaceholder = '-----'
        for HalfLadderModule in HalfLadderModules:
            if len(HalfLadderModule.strip()) > 0:
                ret = ret + HalfLadderModule.ljust(ModuleNameLength+1)
            else:
                ret = ret + EmptyModulePlaceholder.ljust(ModuleNameLength+1)
        return ret


    def EnterMountMenu(self):
        os.system('clear')

        # header
        self.PrintBox("mounting plan for %s: select half ladder" % self.ActiveLayer)

        # Z positions
        ZPositionsString = '           '
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition)
        ZPositionsString += '      '
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions, 2*self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition)
        print ZPositionsString

        # half ladders
        HalfLadderChoices = []
        HeaderColumn = []

        LadderIndex = 1
        for Ladder in self.LayersMounted[self.ActiveLayer].Modules:
            HalfLadderChoices.append([
                self.GetFormattedHalfLadder(Ladder[:self.Layers[self.ActiveLayer].ZPositions]),
                self.GetFormattedHalfLadder(Ladder[self.Layers[self.ActiveLayer].ZPositions:])
            ])
            HeaderColumn.append(("L%d"%LadderIndex).ljust(5))
            LadderIndex += 1


        selectedHalfLadderIndex = AskUser2D('', HalfLadderChoices, HeaderColumn=HeaderColumn)

        selectedHalfLadderString = self.GetFormattedHalfLadder( self.LayersMounted[self.ActiveLayer].Modules[selectedHalfLadderIndex[0]][0+selectedHalfLadderIndex[1]*self.LayersMounted[self.ActiveLayer].ZPositions:(selectedHalfLadderIndex[1]+1)*self.LayersMounted[self.ActiveLayer].ZPositions])
        toBeMountedHalfLadderString = self.GetFormattedHalfLadder( self.Layers[self.ActiveLayer].Modules[selectedHalfLadderIndex[0]][0+selectedHalfLadderIndex[1]*self.Layers[self.ActiveLayer].ZPositions:(selectedHalfLadderIndex[1]+1)*self.Layers[self.ActiveLayer].ZPositions])

        ret = AskUser(["SELECTED HALF-LADDER: %s:"%selectedHalfLadderString,
                       "MOUNTING PLAN:        %s"%toBeMountedHalfLadderString],
                      [
                          ['scan', '_Scan modules...'],
                          ['clear', '_Clear'],
                          ['back', 'Go back (_q)']
                      ], DisplayWidth=self.DisplayWidth)

        if ret == 'scan':
            self.Log("Layer: " + self.ActiveLayer + ", Ladder: " + self.Layers[self.ActiveLayer].GetHalfLadderName(selectedHalfLadderIndex), 'MOUNT')
            self.Log("Currently installed modules: " + selectedHalfLadderString, 'MOUNT')
            self.EnterScanHalfLadderMenu(selectedHalfLadderIndex)
        elif ret == 'clear':
            self.ClearHalfLadder(selectedHalfLadderIndex)

        elif ret == 'back':
            return False


    def EnterScanHalfLadderMenu(self, HalfLadderIndex):

        # pick active layer for mounting
        MountingLayer = self.LayersMounted[self.ActiveLayer]
        PlannedLayer = self.Layers[self.ActiveLayer]


        # scan through all module slots in half-ladder
        for ZPosition in range(HalfLadderIndex[1] * MountingLayer.ZPositions,
                               (HalfLadderIndex[1] + 1) * MountingLayer.ZPositions):
            oldModuleID = MountingLayer.FormatModuleName(MountingLayer.Modules[HalfLadderIndex[0]][ZPosition])
            plannedModuleID = PlannedLayer.FormatModuleName(PlannedLayer.Modules[HalfLadderIndex[0]][ZPosition])
            question = "Scan module ID to replace '{old}' (plan {plan}): ".format(old=oldModuleID, plan=plannedModuleID)
            print question
            newModuleID = raw_input()
            if len(MountingLayer.Modules[HalfLadderIndex[0]][ZPosition]) < 1:
                logString = "mount module  -> " + newModuleID
            else:
                logString = "replace module " + MountingLayer.Modules[HalfLadderIndex[0]][ZPosition] + ' -> ' + newModuleID
            plannedModule = PlannedLayer.Modules[HalfLadderIndex[0]][ZPosition]
            logString += ' plan: ' + plannedModule
            MountingLayer.Modules[HalfLadderIndex[0]][ZPosition] = newModuleID
            self.Log(logString, 'MOUNT-MODULE')

            # check if it was planned to mount the module here
            if newModuleID != plannedModule:
                warningMessage = "mounted module '%s' instead of '%s' at position z=%s" % (
                newModuleID, plannedModule, MountingLayer.GetZPositionName(ZPosition))
                self.ShowWarning(warningMessage)

        self.FlagUnsaved()


    def ClearHalfLadder(self, HalfLadderIndex):

        ret = AskUser("clear half ladder?",
                      [
                          ['yes', '_Yes'],
                          ['no', '_no']
                      ], DisplayWidth=self.DisplayWidth)

        if ret == 'yes':
            for ZPosition in range(HalfLadderIndex[1]*self.LayersMounted[self.ActiveLayer].ZPositions, (HalfLadderIndex[1]+1)*self.LayersMounted[self.ActiveLayer].ZPositions):
                print "%s ----> %s"%(self.LayersMounted[self.ActiveLayer].FormatModuleName(self.LayersMounted[self.ActiveLayer].Modules[HalfLadderIndex[0]][ZPosition]), self.LayersMounted[self.ActiveLayer].FormatModuleName(''))
                self.LayersMounted[self.ActiveLayer].Modules[HalfLadderIndex[0]][ZPosition] = ''
            print "cleared!"
            self.FlagUnsaved()


    def EnterSelectLayerMenu(self):
        layerMenu = []
        LayerIndex = 1
        for LayerName in self.LayerNames:
            layerMenu.append([LayerName,'_%d %s'%(LayerIndex, LayerName)])
            LayerIndex += 1
        selectedLayer = AskUser('Select Layer', layerMenu, DisplayWidth=self.DisplayWidth)
        if selectedLayer:
            try:
                if selectedLayer in self.LayerNames:
                    self.ActiveLayer = selectedLayer
                    self.Log("SELECT layer: %s"%selectedLayer, Category='LAYER')

            except:
                selectedLayer = ''

        return selectedLayer

try:
    os.system('clear')
except:
    pass

try:
    bmt = BpixMountTool()
    bmt.EnterMainMenu()
except:
    print "ERROR: can't initialize BpixMountTool()"
