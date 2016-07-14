class BpixLayer:

    def __init__(self, Name, Ladders, ZPositions):
        self.Name = Name
        self.Ladders = Ladders
        self.ZPositions = ZPositions

        # initialize empty detector
        self.Modules = []
        for i in range(Ladders):
            self.Modules.append(['']*(ZPositions*2))

        self.ZPositionNameLength = 6
        self.LineEndCharacter = '\n'

    def LoadFromFile(self, layerPlanFileName):
        try:
            with open(layerPlanFileName, 'r') as layerPlanFile:
                LadderIndex = 0
                for line in layerPlanFile:
                    modules = [x.split(' ')[0].replace(' ','').replace('\n','').replace('\r','') for x in line.replace('\t',';').split(';')]
                    if len(modules) == self.ZPositions*2:
                        self.Modules[LadderIndex] = modules
                    else:
                        print "bad format: '%r'"%line
                    LadderIndex += 1
        except:
            pass

    def GetZPositionName(self, ZPosition):
        if ZPosition < self.ZPositions:
            return ("Z%d-" % (self.ZPositions - ZPosition - 1)).ljust(self.ZPositionNameLength)
        else:
            return ("Z%d+" % (ZPosition-self.ZPositions)).ljust(self.ZPositionNameLength)


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

    def GetHalfLadderName(self, HalfLadderIndex):
        Name = 'L%d'%(HalfLadderIndex[0]+1)
        if HalfLadderIndex[1] >= self.ZPositions:
            Name += "+"
        else:
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