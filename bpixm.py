#!/usr/bin/env python

import os
import sys
import ConfigParser
import shutil
import glob
import datetime
import traceback

from BpixLayer import BpixLayer
import BpixUI.BpixUI
from BpixUI.BpixUI import *

class BpixMountTool():

    def __init__(self):

        self.globalConfig = ConfigParser.ConfigParser()
        self.globalConfig.read('config.ini')
        self.dataDirectoryBase = 'data/'
        self.FillDirection = self.globalConfig.get('System', 'fill')
        self.revisionTag = ''
        self.Autosave = False

        useColors = False
        try:
            useColors = (int(self.globalConfig.get('System','colors')) > 0)
        except:
            pass

        self.UI = BPixUi(useColors)

        try:
            self.DisplayWidth = int(self.globalConfig.get('System', 'DisplayWidth'))
        except:
            self.DisplayWidth = 80

        self.UnsavedChanges = False
        self.StorageLocations = {}
        self.InitializeStorageData()
        self.InitializeModuleData()

        self.Operator = self.globalConfig.get('System', 'Operator')
        self.Log("-"*80, Category='START')
        self.Log("started, operator: %s"%self.Operator, Category='START')
        self.Log("-"*80, Category='START')

        try:
            self.Autosave = True if self.globalConfig.get('System', 'Autosave').lower().strip() == 'true' else False
        except:
            pass


    def GetDataDirectory(self):
        return self.dataDirectoryBase + self.globalConfig.get('System', 'DataRevision') + '/'


    def InitializeStorageData(self):
        dataDirectory = self.GetDataDirectory()
        self.StorageLocations = {}
        storageLocationFileName = dataDirectory + 'storage_locations.txt'
        if os.path.isfile(storageLocationFileName):
            with open(storageLocationFileName, 'r') as storageLocationFile:
                for line in storageLocationFile:
                    lineParts = line.strip().replace(',',';').replace('\t',';').split(';')
                    if len(lineParts) > 1:
                        self.StorageLocations[lineParts[0]] = lineParts[1].strip()
        else:
            self.ShowWarning("can't find storage location file in '$data/storage_locations.txt'")


    def GetStorageLocation(self, ModuleID):
        location = 'unknown'
        if ModuleID in self.StorageLocations:
            location = self.StorageLocations[ModuleID]
            if len(location) < 1:
                location = 'empty'
        return location


    def InitializeModuleData(self):
        self.dataDirectory = self.GetDataDirectory()
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
        self.SectorsFileName = self.config.get('Layers', 'SectorsFileName')
        self.HubIDsFileName = self.config.get('Layers', 'HubIDsFileName')

        # initialize layers
        self.Layers = {}
        self.LayersMounted = {}
        self.Sectors = {}

        for LayerName in self.LayerNames:
            layerLadders = int(self.config.get('Layer_%s'%LayerName, 'Ladders'))
            layerZpositions = int(self.config.get('Layer_%s'%LayerName, 'ZPositions'))
            layerTbms = int(self.config.get('Layer_%s'%LayerName, 'Tbms'))
            self.Layers[LayerName] = BpixLayer(LayerName, Ladders=layerLadders, ZPositions=layerZpositions, Tbms=layerTbms)
            self.LayersMounted[LayerName] = BpixLayer(LayerName+'(mounted)', Ladders=layerLadders, ZPositions=layerZpositions, Tbms=layerTbms)

            # initialize planned module positions
            layerPlanFileName =  self.GetDataDirectory() + self.LayerPlanFileName.format(Layer=LayerName)
            if os.path.isfile(layerPlanFileName):
                print "initialize ",LayerName
                self.Layers[LayerName].LoadFromFile(layerPlanFileName)
            else:
                print "config file for",LayerName," does not exist!!"

            # initialize already mounted module positions
            layerMountFileName =  self.GetDataDirectory() + self.LayerMountFileName.format(Layer=LayerName)
            if os.path.isfile(layerMountFileName):
                print "initialize mounted modules for ", LayerName
                self.LayersMounted[LayerName].LoadFromFile(layerMountFileName)
            else:
                print "mount file for", LayerName, " does not exist!!"

            # initialize HUB IDs
            hubIDsFileName =  self.GetDataDirectory() + self.HubIDsFileName.format(Layer=LayerName)
            if os.path.isfile(hubIDsFileName):
                print "initialize HUB IDs for ", LayerName
                self.Layers[LayerName].LoadHubIDsFromFile(hubIDsFileName)
                self.LayersMounted[LayerName].LoadHubIDsFromFile(hubIDsFileName)
            else:
                print "HUB IDs file for", LayerName, " does not exist!!"

            # initialize sectors <-> ladders configuration
            sectorsFileName =  self.GetDataDirectory() + self.SectorsFileName.format(Layer=LayerName)
            if os.path.isfile(sectorsFileName):
                self.Sectors[LayerName] = {}
                with open(sectorsFileName, 'r') as sectorsFile:
                    try:
                        for sectorLine in sectorsFile:
                            sectorID = int(sectorLine.split(':')[0].strip(' '))
                            ladders = [int(x) for x in sectorLine.split(':')[1].strip(' ').split(',')]
                            self.Sectors[LayerName][sectorID] = ladders
                    except:
                        print sectorsFileName,": bad formatted line:", sectorLine
        self.ActiveLayer = self.config.get('Layers', 'ActiveLayer')
        print "SECTORS:", self.Sectors

        try:
            self.revisionTag = self.config.get('Revision', 'Tag')
        except:
            self.revisionTag = ""


    def FlagUnsaved(self):
        self.UnsavedChanges = True

        if self.Autosave:
            self.SaveConfiguration(False)


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
        logFileName =  self.GetDataDirectory() + 'bpixm.log'
        with open(logFileName, "a") as logFile:
            logFile.write(logString)


    def WriteGlobalConfig(self):
        if self.Autosave:
            self.globalConfig.set('System', 'Autosave', 'true')
        else:
            self.globalConfig.set('System', 'Autosave', 'false')

        self.globalConfig.set('System', 'fill', self.FillDirection)
        with open('config.ini', 'wb') as configfile:
            self.globalConfig.write(configfile)
        self.globalConfig.read('config.ini')


    def SaveLocalConfiguration(self):
        with open( self.GetDataDirectory() + 'config.ini', 'wb') as configfile:
            self.config.write(configfile)

        self.config.read(self.GetDataDirectory() + 'config.ini')


    def SaveConfiguration(self, PrintOutput = True):
        Success = True
        for LayerName in self.LayerNames:
            layerMountFileName =  self.GetDataDirectory() + self.LayerMountFileName.format(Layer=LayerName)
            if self.LayersMounted[LayerName].SaveAs(layerMountFileName):
                if PrintOutput:
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
            dataDirectories = [x.replace('\\','/').strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
            nextRevision = 1 + max([int(x) for x in dataDirectories if x.isdigit()])
            dataDirectoryNew = self.dataDirectoryBase + '%d/'%nextRevision
        except:
            print "can't determine data revision!!!"
            Success = False

        if Success:
            try:
                shutil.copytree( self.GetDataDirectory(), dataDirectoryNew)
            except:
                print "can't copy to new location:", dataDirectoryNew
                Success = False

        if Success:
            self.dataDirectory = dataDirectoryNew
            self.globalConfig.set('System', 'DataRevision', nextRevision)
            self.WriteGlobalConfig()

            self.Log("CREATED REV {newRev} out of REVISION {oldRev}".format(newRev = nextRevision, oldRev=oldRevision), Category="CONFIG")

        return Success

    def EnterSearchMenu(self):
        print "############################################################"
        print " ENTER/SCAN MODULE ID"
        print "############################################################"
        moduleID = self.ReadModuleBarcode()
        self.Log("Search for module: %s"%moduleID, 'SEARCH')
        StorageLocationScannedID = self.GetStorageLocation(moduleID)
        print "############################################################"
        print " SEARCH RESULTS"
        print "############################################################"
        print " MODULE:        %s" % moduleID
        print " STORAGE:       %s" % StorageLocationScannedID
        if StorageLocationScannedID in ['unknown', 'empty']:
            self.ShowWarning(
                'Storage location for module {ModuleID} is unknown, this module ID might not exist, please check!'.format(
                    ModuleID=moduleID))

        plannedPositions = []
        if len(moduleID) > 0:
            for layerName, layer in self.Layers.items():
                for ladderNumber, ladder in enumerate(layer.Modules, start=1):
                    for planModuleID in ladder:
                        if planModuleID == moduleID:
                            plannedPositions.append("{Layer} LADDER {Ladder}".format(Layer=layerName, Ladder=ladderNumber))
        print " PLAN POSITION: %s" % (', '.join(plannedPositions) if len(plannedPositions) > 0 else '-')

        mountedPositions = []
        if len(moduleID) > 0:
            for layerName, layer in self.LayersMounted.items():
                for ladderNumber, ladder in enumerate(layer.Modules, start=1):
                    for planModuleID in ladder:
                        if planModuleID == moduleID:
                            mountedPositions.append("{Layer} LADDER {Ladder}".format(Layer=layerName, Ladder=ladderNumber))
        print " MOUNTED AT:    %s" % (', '.join(mountedPositions) if len(mountedPositions) > 0 else '-')
        print "############################################################"
        print "press any key to continue to main menu"
        raw_input()
        return True

    def EnterMainMenu(self):
        while True:

            revisionInfo = ''
            try:
                dataDirectories = [x.replace('\\','/').strip('/').split('/')[-1] for x in glob.glob(self.dataDirectoryBase + '*/')]
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
            elif self.Autosave:
                unsavedInfo = "Autosave is on! Changes are saved immediately!"


            ret = self.UI.AskUser(['Main menu',revisionInfo,unsavedInfo],
                          [
                            ['mount','_Mount modules on half ladder'],
                            ['replace','_Replace single module'],
                            ['view','View _detector status'],
                            ['plan','View mounting _plan'],
                            ['hubids', 'View _hub IDs'],
                            ['search', 'Search module ID'],
                            ['log','Add _log entry'],
                            ['mlog', 'Add log entry to specific module'],
                            ['save', 'Sa_ve configuration'],
                            ['step','Save configuration as new revision'],
                            ['revs','Sho_w revisions'],
                            ['selectrevs','Select revision'],
                            ['tagrevs','Set tag for this revision'],
                            ['select', '_Select Layer (active: %s)' % self.ActiveLayer],
                            ['settings', 'Sett_ings'],
                            ['quit','_Quit']
                          ], DisplayWidth=self.DisplayWidth)
            if ret == 'plan':
                self.EnterViewPlanMenu()
            elif ret == 'hubids':
                self.EnterViewHubIDsMenu()
            elif ret == 'view':
                self.EnterViewStatusMenu()
            elif ret == 'select':
                self.EnterSelectLayerMenu()
            elif ret == 'search':
                self.EnterSearchMenu()
            elif ret == 'mount':
                self.EnterMountMenu()
            elif ret == 'replace':
                self.EnterReplaceMenu()
            elif ret == 'log':
                self.EnterLogMenu()
            elif ret == 'mlog':
                self.EnterModuleLogMenu()
            elif ret == 'revs':
                self.EnterRevsMenu()
            elif ret == 'selectrevs':
                self.EnterSelectRevsMenu()
            elif ret == 'tagrevs':
                self.EnterTagRevsMenu()
            elif ret == 'save':
                self.EnterSaveConfigurationMenu()
            elif ret == 'settings':
                self.EnterSettingsMenu()
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
                    ret = self.UI.AskUser("do you really want to quit?",
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


    def SelectSingleModule(self, selectTitle='select a module'):
        self.UI.Clear()

        # header
        self.PrintBox(selectTitle)

        ModuleChoices = []
        MountingLayer = self.GetActiveMountingLayer()
        for Ladder in MountingLayer.Modules:
            LadderModules = []
            for ModuleId in Ladder:
                LadderModules.append(self.GetActiveMountingLayer().FormatModuleName(ModuleId))
            ModuleChoices.append(LadderModules)

        # Z positions
        ZPositionsString = ' '*9
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition).ljust(9)
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions, 2*self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition).ljust(9)
        print ZPositionsString

        # half ladders
        HalfLadderChoices = []
        HeaderColumn = []

        LadderIndex = 1
        for Ladder in MountingLayer.Modules:
            HeaderColumn.append(("L%d"%LadderIndex).ljust(5))
            LadderIndex += 1

        # ask user to pick a half ladder
        selectedModuleIndex = self.UI.AskUser2D('', ModuleChoices, HeaderColumn=HeaderColumn)

        # [0] = ladderIndex = Ladder Number from 0...#-1
        # [1] = zIndex = 0...7 from minus side to plus side
        return selectedModuleIndex


    def EnterModuleLogMenu(self):
        modulePosition = self.SelectSingleModule("select module to add comment")
        commentLayer = self.ActiveLayer
        commentLadder = self.GetActiveMountingLayer().GetLadderName(modulePosition[0])
        commentZPosition = self.GetActiveMountingLayer().GetZPositionNameRaw(modulePosition[1])
        try:
            commentModule = self.GetActiveMountingLayer().Modules[modulePosition[0]][modulePosition[1]]
        except:
            commentModule = '----'
        print " LAYER:    %s"%commentLayer
        print " LADDER:   %s"%commentLadder
        print " Z:        %s"%commentZPosition
        print " MODULE:   %s"%commentModule
        self.PrintBox("enter lines to write to log file, empty line to stop")
        logComments = []
        logString = raw_input()
        while len(logString.strip()) > 0:
            logComments.append(logString)
            logString = raw_input()

        logComment = ', '.join(logComments)
        logLine = '{Layer}/{Ladder}/{ZPosition}/{ModuleID}: {Comment}'.format(Layer=commentLayer, Ladder=commentLadder, ZPosition=commentZPosition, ModuleID=commentModule, Comment=logComment)
        self.Log(logLine, 'MODULE-COMMENT')

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

        ret = self.UI.AskUser("Select revision to return to", revs, DisplayWidth=self.DisplayWidth)
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
            ret = self.UI.AskUser("do you really want to switch to another parameters revision?",
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
                textLine = textWord + ' '
        if len(textLine) > 0:
            textLines.append(textLine)

        for textLine in textLines:
            print "| %s|" % textLine.ljust(self.DisplayWidth-3)

        print "+%s+" % ('-' * (self.DisplayWidth-2))


    def EnterSaveConfigurationMenu(self):
        ret = self.UI.AskUser("Save list of mounted modules for all layers?",
                      [
                          ['yes', '_yes'],
                          ['no', '_no']
                      ], DisplayWidth=self.DisplayWidth)

        if ret == 'yes':
            self.SaveConfiguration()


    def EnterViewPlanMenu(self):
        self.UI.Clear()

        PlannedLayer = self.Layers[self.ActiveLayer]
        self.PrintBox("mounting plan for %s"%self.ActiveLayer)

        ZPositionsString = '               '

        for ZPosition in range(PlannedLayer.ZPositions):
            ZPositionsString += ("Z%d-"%(PlannedLayer.ZPositions - ZPosition)).ljust(7)
        ZPositionsString += '  '
        for ZPosition in range(PlannedLayer.ZPositions):
            ZPositionsString += ("Z%d+"%(ZPosition+1)).ljust(7)

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
        self.UI.Clear()

        MountingLayer = self.LayersMounted[self.ActiveLayer]
        PlannedLayer = self.Layers[self.ActiveLayer]

        self.PrintBox("status of %s"%self.ActiveLayer)

        ZPositionsString = ' '*15

        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d-"%(MountingLayer.ZPositions - ZPosition)).ljust(7)
        ZPositionsString += '  '
        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d+"%(ZPosition+1)).ljust(7)

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


    def EnterViewHubIDsMenu(self):
        self.UI.Clear()

        MountingLayer = self.LayersMounted[self.ActiveLayer]
        PlannedLayer = self.Layers[self.ActiveLayer]

        self.PrintBox("status of %s"%self.ActiveLayer)

        ZPositionsString = ' '*15

        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d-"%(MountingLayer.ZPositions - ZPosition )).ljust(7)
        ZPositionsString += '     '
        for ZPosition in range(MountingLayer.ZPositions):
            ZPositionsString += ("Z%d+"%(ZPosition+1)).ljust(7)

        print "|%s|"%(ZPositionsString.ljust((self.DisplayWidth-2)))

        for LadderIndex in range(len(MountingLayer.Modules)):

            LadderName = "L%d" %(LadderIndex+1)
            LadderName = "\x1b[32m%s\x1b[0m   " % (LadderName.ljust(10))

            # compare all mounted modules in the ladder with mounting plan
            LadderString = '   ' + LadderName
            for i in range(0, 2*MountingLayer.ZPositions):
                if i == MountingLayer.ZPositions:
                    LadderString += '   '

                hubIDmounted = MountingLayer.FormatHubIDTuple(MountingLayer.HubIDs[LadderIndex][i])
                hubIDplanned = PlannedLayer.FormatHubIDTuple(PlannedLayer.HubIDs[LadderIndex][i])

                if (hubIDmounted == hubIDplanned) or len(hubIDmounted) < 1:
                    LadderString += hubIDplanned.ljust(7)
                else:
                    LadderString += hubIDmounted.ljust(7)

            print "|%s|"%(LadderString.ljust((self.DisplayWidth+7)))
            LadderIndex += 1

        print "+%s+\n" % ('-' * (self.DisplayWidth-2))


    def GetFormattedHalfLadder(self, HalfLadderModules, LadderZIndex = 0):

        if LadderZIndex == 0 and (self.FillDirection == 'inwards' or self.FillDirection == 'lefttoright'):
            ret = ' > '
        elif LadderZIndex == 1 and (self.FillDirection == 'outwards' or self.FillDirection == 'lefttoright'):
            ret = ' > '
        else:
            ret = ''

        ModuleNameLength = 5
        EmptyModulePlaceholder = '-----'
        for HalfLadderModule in HalfLadderModules:
            if len(HalfLadderModule.strip()) > 0:
                ret = ret + HalfLadderModule.ljust(ModuleNameLength+1)
            else:
                ret = ret + EmptyModulePlaceholder.ljust(ModuleNameLength+1)
        if LadderZIndex == 1 and (self.FillDirection == 'inwards' or self.FillDirection == 'righttoleft'):
            ret += ' < '
        if LadderZIndex == 0 and (self.FillDirection == 'outwards' or self.FillDirection == 'righttoleft'):
            ret += ' < '

        return ret


    def GetActiveMountingLayer(self):
        return self.LayersMounted[self.ActiveLayer]

    def GetActivePlanLayer(self):
        return self.Layers[self.ActiveLayer]

    def EnterMountMenu(self):
        while True:
            self.UI.Clear()

            # header
            self.PrintBox("mounting plan for %s: select half ladder" % self.ActiveLayer)

            # Z positions
            ZPositionsString = ' '*12
            for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions):
                ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition)
            ZPositionsString += ' '*7
            for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions, 2*self.Layers[self.ActiveLayer].ZPositions):
                ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition)
            print ZPositionsString

            # half ladders
            HalfLadderChoices = []
            HeaderColumn = []

            LadderIndex = 1
            for Ladder in self.LayersMounted[self.ActiveLayer].Modules:
                HalfLadderChoices.append([
                    self.GetFormattedHalfLadder(Ladder[:self.Layers[self.ActiveLayer].ZPositions], 0),
                    self.GetFormattedHalfLadder(Ladder[self.Layers[self.ActiveLayer].ZPositions:], 1)
                ])
                HeaderColumn.append(("L%d"%LadderIndex).ljust(5))
                LadderIndex += 1

            HalfLadderChoices.append(["Go back to main menu",""])

            # ask user to pick a half ladder
            selectedHalfLadderIndex = self.UI.AskUser2D('', HalfLadderChoices, HeaderColumn=HeaderColumn)

            if selectedHalfLadderIndex[0] >= len(HalfLadderChoices)-1:
                return False

            # check for modules already mounted on that half ladder
            selectedHalfLadderModules = self.GetActiveMountingLayer().GetHalfLadderModulesFromIndex(selectedHalfLadderIndex)
            selectedHalfLadderString = self.GetFormattedHalfLadder(selectedHalfLadderModules, selectedHalfLadderIndex[1])

            # check modules planned to be mounted on that half ladder
            toBeMountedHalfLadderModules = self.GetActivePlanLayer().GetHalfLadderModulesFromIndex(selectedHalfLadderIndex)
            toBeMountedHalfLadderString = self.GetFormattedHalfLadder(toBeMountedHalfLadderModules, selectedHalfLadderIndex[1])

            # display hub IDs
            hubIDsList = self.GetActivePlanLayer().GetHalfLadderHubIDsFromIndex(selectedHalfLadderIndex)
            hubIDsString = ', '.join(hubIDsList)

            # display modules list and ask user how to continue
            ret = self.UI.AskUser(["SELECTED HALF-LADDER: %s:"%selectedHalfLadderString,
                           "MOUNTING PLAN:        %s"%toBeMountedHalfLadderString,
                           "HUB IDs:              %s" %hubIDsString,
                           ],
                          [
                              ['scan', '_Scan modules...'],
                              ['clear', '_Clear'],
                              ['mountmenu', 'Go _back'],
                              ['back', 'Main menu (_q)'],
                          ], DisplayWidth=self.DisplayWidth)

            if ret == 'scan':
                self.Log("Layer: " + self.ActiveLayer + ", Ladder: " + self.Layers[self.ActiveLayer].GetHalfLadderName(selectedHalfLadderIndex), 'MOUNT')
                self.Log("Currently installed modules: " + selectedHalfLadderString, 'MOUNT')
                self.EnterScanHalfLadderMenu(selectedHalfLadderIndex)
            elif ret == 'clear':
                self.Log("Layer: " + self.ActiveLayer + ", Ladder: " + self.Layers[self.ActiveLayer].GetHalfLadderName(
                    selectedHalfLadderIndex), 'MOUNT-CLEAR')
                self.Log("Currently installed modules: " + selectedHalfLadderString, 'MOUNT-CLEAR')
                self.ClearHalfLadder(selectedHalfLadderIndex)

            elif ret == 'back':
                return False


    def EnterReplaceMenu(self):
        self.UI.Clear()

        # header
        self.PrintBox("mounting plan for %s: select half ladder" % self.ActiveLayer)

        ModuleChoices = []
        MountingLayer = self.GetActiveMountingLayer()
        for Ladder in MountingLayer.Modules:
            LadderModules = []
            for ModuleId in Ladder:
                LadderModules.append(self.GetActiveMountingLayer().FormatModuleName(ModuleId))
            ModuleChoices.append(LadderModules)

        # Z positions
        ZPositionsString = ' '*9
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition).ljust(9)
        for ZPosition in range(self.Layers[self.ActiveLayer].ZPositions, 2*self.Layers[self.ActiveLayer].ZPositions):
            ZPositionsString += self.Layers[self.ActiveLayer].GetZPositionName(ZPosition).ljust(9)
        print ZPositionsString

        # half ladders
        HalfLadderChoices = []
        HeaderColumn = []

        LadderIndex = 1
        for Ladder in MountingLayer.Modules:
            HeaderColumn.append(("L%d"%LadderIndex).ljust(5))
            LadderIndex += 1

        # ask user to pick a half ladder
        selectedModuleIndex = self.UI.AskUser2D('', ModuleChoices, HeaderColumn=HeaderColumn)
        self.Log("Layer: " + self.ActiveLayer + ", Ladder: %d"%selectedModuleIndex[0] + " Z: %d"%selectedModuleIndex[1], 'MOUNT-REPLACE')

        return self.EnterMountSingleModuleMenu(MountingLayer, selectedModuleIndex[0], selectedModuleIndex[1], PlannedLayer=self.GetActivePlanLayer())


    def VerifyModuleID(self, ModuleID, CheckLadderIndex, CheckZIndex):
        #print "VERIFY:", ModuleID, "/", CheckLadderIndex, "/", CheckZIndex

        if len(ModuleID.strip()) < 1:
            return True

        alreadyMountedPositions = []
        for LadderIndex, Ladder in enumerate(self.GetActiveMountingLayer().Modules):
            for ZIndex, MountedModuleID in enumerate(Ladder):
                if MountedModuleID == ModuleID:
                    if CheckLadderIndex==LadderIndex and CheckZIndex==ZIndex:
                        print "Module {Module} already mounted here! => continue!".format(Module=ModuleID)
                    else:
                        alreadyMountedPositions.append("Ladder {Ladder}, Z {ZIndex}".format(Ladder=LadderIndex, ZIndex=ZIndex))

        if len(alreadyMountedPositions)>0:
            self.ShowWarning(
                "The module {ModuleID} is already mounted in another position ({Position}), can't use it a second time!".format(
                    ModuleID=ModuleID, Position="; ".join(alreadyMountedPositions)))
            return False

        if len(ModuleID) > 6:
            self.ShowWarning("Module-ID is too long, max. length of 6 allowed")
            return False


        return True


    def MountModule(self, MountingLayer, LadderIndex, ZPosition, newModuleID, PlannedLayer = None):

        success = False
        try:
            if ZPosition < MountingLayer.ZPositions:
                ZPositionFormatted = "-%d"%(MountingLayer.ZPositions - ZPosition)
            else:
                ZPositionFormatted = "+%d"%(ZPosition - MountingLayer.ZPositions)

            if len(MountingLayer.Modules[LadderIndex][ZPosition]) < 1:
                logString = "DONE: mount module  -> " + newModuleID
            else:
                logString = "DONE: replace module " + MountingLayer.Modules[LadderIndex][ZPosition] + ' -> ' + newModuleID

            logString = logString + " at ladder %d"%(LadderIndex+1) + " Z =" + ZPositionFormatted

            if PlannedLayer:
                plannedModule = PlannedLayer.Modules[LadderIndex][ZPosition]
                logString += ' plan: ' + plannedModule

            logString = logString + " operator: " + self.Operator
            try:
                MountingLayer.Modules[LadderIndex][ZPosition] = newModuleID
                success = True
            except:
                logString = "FAILED: mount module  -> " + newModuleID
        except:
            logString = "ERROR IN CREATING LOG"

        self.Log(logString, 'MOUNT-MODULE')
        return success

    def ReadModuleBarcode(self):
        moduleID = raw_input()
        # correct barcodes
        if moduleID.startswith('D'):
            moduleID = 'M' + moduleID[1:]

        return moduleID

    def EnterMountSingleModuleMenu(self, MountingLayer, LadderIndex, ZPosition, PlannedLayer = None):
        oldModuleID = MountingLayer.FormatModuleName(MountingLayer.Modules[LadderIndex][ZPosition])

        plannedModuleIDraw = PlannedLayer.Modules[LadderIndex][ZPosition].strip()
        plannedModuleFound = len(plannedModuleIDraw) > 1
        try:
            plannedModuleID = PlannedLayer.FormatModuleName(plannedModuleIDraw)
        except:
            plannedModuleID = 'M????'

        ModuleMountComplete = False
        hubIDs = MountingLayer.HubIDs[LadderIndex][ZPosition]
        while not ModuleMountComplete:

            selectedLadderID = 1+LadderIndex
            hubIDOffset = 0
            sectorID = 0

            halfLadderZPosition = 3-ZPosition if ZPosition < 4 else ZPosition-4

            # ask user for module ID
            ModuleStorageLocation = self.GetStorageLocation(plannedModuleID)
            print " LADDER:           %d"%(1+LadderIndex)
            print " PLANNED MODULE:   %s"%plannedModuleID
            print " STORAGE LOCATION: %s"%ModuleStorageLocation
            if oldModuleID.startswith('-'):
                if plannedModuleFound:
                    question = "Scan module ID to mount here, plan: {plan} (\x1b[31mq\x1b[0m to quit): ".format(plan=plannedModuleID)
                else:
                    question = "Scan module ID to mount here (\x1b[31mq\x1b[0m to quit): "
            else:
                question = "Scan module ID to replace '{old}', plan: {plan} (\x1b[31mq\x1b[0m to quit): ".format(old=oldModuleID, plan=plannedModuleID)
            print question

            newModuleID = self.ReadModuleBarcode()

            if newModuleID == 'q':
                logMessage = "CANCEL: no module scanned, action was cancelled by user!"
                self.Log(logMessage, Category="MOUNT-MODULE")
                print logMessage
                return False

            self.Log("L: {Ladder}, Z: {Z}, Plan: {Plan} (in {Box}), Scanned: {Scanned}".format(Ladder=LadderIndex+1, Z=ZPosition, Plan=plannedModuleID, Scanned=newModuleID, Box=ModuleStorageLocation), Category="MOUNT-MODULE")
            # check if module is mountable _here_
            isMountable = self.VerifyModuleID(newModuleID, LadderIndex, ZPosition)

            if isMountable:
                self.Log("OK: The module {ModuleID} can be mounted here.".format(ModuleID=newModuleID), Category="MOUNT-MODULE")
                # check if it was _planned_ to mount the module here
                if plannedModuleFound and newModuleID != plannedModuleID:
                    warningMessage = "planning to mount module '%s' instead of '%s' at position z=%s" % (
                        newModuleID, plannedModuleID, MountingLayer.GetZPositionName(ZPosition))
                    self.ShowWarning(warningMessage)
                    ret = self.UI.AskUser("continue",
                                  [
                                      ['no', '_no'],
                                      ['yes', '_yes']
                                  ], DisplayWidth=self.DisplayWidth)
                    if ret != 'yes':
                        self.Log("CANCEL: action was cancelled by user!", Category="MOUNT-MODULE")
                        isMountable = False
            else:
                pass

            if isMountable:

                HubIDString = ('/'.join(['%d'%x for x in hubIDs]))
                StorageLocationScannedID = self.GetStorageLocation(newModuleID)
                print "############################################################"
                print " VERIFY MODULE AND CHANGE HUB ID"
                print "############################################################"
                print " MODULE:      %s" % newModuleID
                print " STORAGE:     %s" % StorageLocationScannedID
                if StorageLocationScannedID in ['unknown', 'empty']:
                    self.ShowWarning('Storage location for module {ModuleID} is unknown, this module ID might not exist, please check!'.format(ModuleID=newModuleID))
                print " LADDER:      %d" % selectedLadderID
                print " LADDER ZPOS: %d" % ZPosition
                print " HUB-IDs:     %s" % HubIDString
                print "------------------------------------------------------------"
                for tbmID, hubID in enumerate(hubIDs, start=1):
                    print "TBM", tbmID, " of", len(hubIDs), " => HUB ID = ", hubID
                    print "least significant bit"
                    for hubIDbit in range(5):
                        if ((hubID >> hubIDbit) % 2) == 1:
                            print "%d   O------O    " % hubIDbit
                        else:
                            print "%d   O      O  <<" % hubIDbit
                    print "most significant bit"
                print "------------------------------------------------------------"

                self.Log("HUB-IDS: {HubIDs}".format(HubIDs=HubIDString), Category="MOUNT-MODULE")

                ret = self.UI.AskUser("continue",
                              [
                                  ['yes', '_Yes'],
                                  ['no', '_no']
                              ], DisplayWidth=self.DisplayWidth)
                if ret == 'yes':
                    # mount module
                    if self.MountModule(MountingLayer=self.GetActiveMountingLayer(),
                                        LadderIndex=LadderIndex,
                                        ZPosition=ZPosition,
                                        newModuleID=newModuleID,
                                        PlannedLayer=self.GetActivePlanLayer()
                                        ):
                        print "->mounted"
                        self.FlagUnsaved()
                        ModuleMountComplete = True
                    else:
                        self.ShowWarning("Could not mount the module here! Enter Module ID again!")

            else:
                print "Enter Module ID again! (q to quit)"
        return True


    def EnterFillDirectionMenu(self):
        ret = self.UI.AskUser("Set fill direction (used in 'Mount' menu) currently: %s" % self.FillDirection,
                      [
                          ['inwards', '_Inwards -> <-'],
                          ['outwards', '_Outwards <- ->'],
                          ['lefttoright', '_Left to right -> ->'],
                          ['righttoleft', '_Right to left <- <-'],
                          ['q', 'Back to settings (_q)']
                      ], DisplayWidth=self.DisplayWidth)
        if ret in ['inwards', 'outwards', 'lefttoright', 'righttoleft']:
            self.FillDirection = ret
            self.WriteGlobalConfig()
            return True
        elif ret == 'q':
            return False
        else:
            print "invalid option selected"


    def EnterSettingsMenu(self):
        while True:
            ret = self.UI.AskUser("Settings",
                          [
                              ['select', '_Select Layer (active: %s)' % self.ActiveLayer],
                              ['operator', 'Set _operator (currently: %s)' % self.Operator],
                              ['fill', 'Set _fill direction (currently: %s)' % self.FillDirection],
                              ['autosave', 'Toggle _autosave (currently: %s)' % ('on' if self.Autosave else 'off')],
                              ['q', 'Back to main menu (_q)']
                          ], DisplayWidth=self.DisplayWidth)

            if ret == 'autosave':
                self.Autosave = not self.Autosave
                self.WriteGlobalConfig()
            elif ret == 'operator':
                self.EnterSetOperatorMenu()
            elif ret == 'select':
                self.EnterSelectLayerMenu()
            elif ret == 'fill':
                self.EnterFillDirectionMenu()
            elif ret == 'q':
                return True

    def EnterScanHalfLadderMenu(self, HalfLadderIndex):

        # pick active layer for mounting
        MountingLayer = self.GetActiveMountingLayer()
        PlannedLayer = self.GetActivePlanLayer()

        ModuleZPositions = []

        if self.FillDirection == 'lefttoright':
            print "filling modules from left to right"
            ModuleZPositions = range(HalfLadderIndex[1] * MountingLayer.ZPositions,
                                   (HalfLadderIndex[1] + 1) * MountingLayer.ZPositions)

        elif self.FillDirection == 'righttoleft':
            print "filling modules from right to left"
            ModuleZPositions = list(reversed(range(HalfLadderIndex[1] * MountingLayer.ZPositions,
                                   (HalfLadderIndex[1] + 1) * MountingLayer.ZPositions)))

        elif self.FillDirection == 'outwards':
            print "filling modules from inside (Z0) to outside (Z3)"
            if HalfLadderIndex[1] == 0:
                ModuleZPositions = list(reversed(range(HalfLadderIndex[1] * MountingLayer.ZPositions,
                                       (HalfLadderIndex[1] + 1) * MountingLayer.ZPositions)))
            else:
                # scan through all module slots in half-ladder in reverse order
                ModuleZPositions = list(reversed(range((HalfLadderIndex[1] + 1) * MountingLayer.ZPositions - 1,
                                       HalfLadderIndex[1] * MountingLayer.ZPositions - 1, -1)))
        else:
            print "filling modules from outside (Z3) to inside (Z0)"
            if HalfLadderIndex[1] == 0:
                ModuleZPositions = range(HalfLadderIndex[1] * MountingLayer.ZPositions,
                                       (HalfLadderIndex[1] + 1) * MountingLayer.ZPositions)
            else:
                # scan through all module slots in half-ladder in reverse order
                ModuleZPositions = range((HalfLadderIndex[1] + 1) * MountingLayer.ZPositions - 1,
                                       HalfLadderIndex[1] * MountingLayer.ZPositions - 1, -1)

        # mount individual modules
        for ZPosition in ModuleZPositions:
            self.EnterMountSingleModuleMenu(MountingLayer, HalfLadderIndex[0], ZPosition, PlannedLayer=PlannedLayer)


    def ClearHalfLadder(self, HalfLadderIndex):

        ret = self.UI.AskUser("clear half ladder?",
                      [
                          ['no', '_No'],
                          ['yes', '_yes']
                      ], DisplayWidth=self.DisplayWidth)

        if ret == 'yes':
            for ZPosition in range(HalfLadderIndex[1]*self.LayersMounted[self.ActiveLayer].ZPositions, (HalfLadderIndex[1]+1)*self.LayersMounted[self.ActiveLayer].ZPositions):
                print "%s ----> %s"%(self.LayersMounted[self.ActiveLayer].FormatModuleName(self.LayersMounted[self.ActiveLayer].Modules[HalfLadderIndex[0]][ZPosition]), self.LayersMounted[self.ActiveLayer].FormatModuleName(''))
                self.LayersMounted[self.ActiveLayer].Modules[HalfLadderIndex[0]][ZPosition] = ''
            print "cleared!"
            self.Log("DONE: half-ladder cleared!", 'MOUNT-CLEAR')

            self.FlagUnsaved()
        else:
            self.Log("CANCEL: clear cancelled.", 'MOUNT-CLEAR')


    def EnterSelectLayerMenu(self):
        layerMenu = []
        LayerIndex = 1
        for LayerName in self.LayerNames:
            layerMenu.append([LayerName,'_%d %s'%(LayerIndex, LayerName)])
            LayerIndex += 1
        selectedLayer = self.UI.AskUser('Select Layer', layerMenu, DisplayWidth=self.DisplayWidth)
        if selectedLayer:
            try:
                if selectedLayer in self.LayerNames:
                    self.ActiveLayer = selectedLayer
                    self.Log("SELECT layer: %s"%selectedLayer, Category='LAYER')
                    self.config.set('Layers', 'ActiveLayer', selectedLayer)
                    self.SaveLocalConfiguration()

            except:
                selectedLayer = ''

        return selectedLayer



try:
    bmt = BpixMountTool()
    bmt.EnterMainMenu()
except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    # Start red color
    sys.stdout.write("\x1b[31m")
    sys.stdout.flush()
    # Print error message
    print 'An exception occurred!'
    # Print traceback
    traceback.print_exception(exc_type, exc_obj, exc_tb)
    # Stop red color
    sys.stdout.write("\x1b[0m")
    sys.stdout.flush()
