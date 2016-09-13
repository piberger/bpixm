class BpixLayer:

    def __init__(self, Name, Ladders, ZPositions, Tbms = 1):
        self.Name = Name
        self.Ladders = Ladders
        self.ZPositions = ZPositions
        self.Tbms = Tbms

        # initialize empty detector
        self.Modules = []
        for i in range(Ladders):
            self.Modules.append(['']*(ZPositions*2))

        self.ZPositionNameLength = 6
        self.LineEndCharacter = '\n'

        self.HubIDs = []
        for i in range(Ladders):
            self.HubIDs.append([[-1]*Tbms]*(ZPositions*2))

    def LoadFromFile(self, layerPlanFileName):
        try:
            with open(layerPlanFileName, 'r') as layerPlanFile:
                LadderIndex = 0
                for line in layerPlanFile:
                    modules = [x.split(' ')[0].replace(' ','').replace('\n','').replace('\r','') for x in line.replace('\t',';').split(';')]
                    if len(modules) == self.ZPositions*2:
                        self.Modules[LadderIndex] = modules
                    else:
                        print "-"*78
                        print "bad format: '%r'"%line
                        print "length: ", len(modules)
                        print "expected: ", self.ZPositions*2
                        print "data: ", modules
                        print "-"*78
                    LadderIndex += 1
        except:
            pass

    def LoadHubIDsFromFile(self, hubIDsFileName):
        try:
            with open(hubIDsFileName, 'r') as hubIDsFile:
                LadderIndex = 0
                for line in hubIDsFile:
                    hubIDs = [x.split(' ')[0].replace(' ','').replace('\n','').replace('\r','') for x in line.replace('\t',';').split(';')]
                    if len(hubIDs) == self.ZPositions*2:
                        # split hubID strings for more than one TBMs
                        self.HubIDs[LadderIndex] = [[int(y) for y in x.split('/')] for x in hubIDs]
                    else:
                        print "-"*78
                        print "bad format: '%r'"%line
                        print "length: ", len(hubIDs)
                        print "expected: ", self.ZPositions*2
                        print "data: ", hubIDs
                        print "-"*78
                    LadderIndex += 1
        except:
            print "ERROR: can't load HUB IDs from file:", hubIDsFileName

    def GetZPositionName(self, ZPosition):
        if ZPosition < self.ZPositions:
            return ("Z%d-" % (self.ZPositions - ZPosition)).ljust(self.ZPositionNameLength)
        else:
            return ("Z%d+" % (ZPosition-self.ZPositions+1)).ljust(self.ZPositionNameLength)


    def CheckModuleName(self, ModuleName):
        if ModuleName[0] != 'M':
            return False
        try:
            ModuleID = int(ModuleName[1:])
        except:
            return False
        return True


    def FormatModuleName(self, ModuleName):
        if len(ModuleName.strip()) < 1:
            return '-----'
        else:
            if self.CheckModuleName(ModuleName.strip()):
                return ModuleName.strip()
            else:
                return "M$$$$"

    def GetHalfLadderModulesFromIndex(self, selectedHalfLadderIndex):
        PhiIndex = selectedHalfLadderIndex[0]
        ZIndexFrom = selectedHalfLadderIndex[1] * self.ZPositions
        ZIndexTo = (selectedHalfLadderIndex[1] + 1) * self.ZPositions
        return self.Modules[PhiIndex][ZIndexFrom:ZIndexTo]

    def FormatHubIDTuple(self, hubIDTuple):
        return '/'.join(['%d'%x for x in hubIDTuple])

    def GetHalfLadderHubIDsFromIndex(self, selectedHalfLadderIndex):
        hubIDTuplesList = self.GetHalfLadderHubIDTuplesFromIndex(selectedHalfLadderIndex)
        return [self.FormatHubIDTuple(x) for x in hubIDTuplesList]

    def GetHalfLadderHubIDTuplesFromIndex(self, selectedHalfLadderIndex):
        PhiIndex = selectedHalfLadderIndex[0]
        ZIndexFrom = selectedHalfLadderIndex[1] * self.ZPositions
        ZIndexTo = (selectedHalfLadderIndex[1] + 1) * self.ZPositions
        hubIDTuplesList = self.HubIDs[PhiIndex][ZIndexFrom:ZIndexTo]
        return hubIDTuplesList

    def GetHalfLadderName(self, HalfLadderIndex):
        Name = 'L%d'%(HalfLadderIndex[0]+1)
        if HalfLadderIndex[1] == 1:
            Name += "+"
        elif HalfLadderIndex[1] == 0:
            Name += "-"
        return Name

    def SaveAs(self, FileName):
        Success = False
        try:
            with open(FileName, 'w') as layerFile:
                LadderIndex = 0
                for i in range(self.Ladders):
                    layerFile.write(';'.join(self.Modules[i]) + self.LineEndCharacter)

            Success = True
        except:
            pass

        return Success