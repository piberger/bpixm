import sys
import os

try:
    import termios
    import tty
except:
    pass

try:
    from msvcrt import getch as getch_windows
    def getch():
        char = getch_windows()
        if ord(char) == 224:
            k1 = getch_windows()
            if k1 == 'H':
                k1 = '^'
            elif k1 == 'P':
                k1 = 'V'
            elif k1 == 'M':
                k1 = '>'
            elif k1 == 'K':
                k1 = '<'
            return k1
        else:
            return char
except ImportError:
    def getch():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            k1 = sys.stdin.read(1)
            if ord(k1) == 27:
                k1 = sys.stdin.read(1)
                k1 = sys.stdin.read(1)
                if k1 == 'A':
                    k1 = '^'
                elif k1 == 'B':
                    k1 = 'V'
                elif k1 == 'C':
                    k1 = '>'
                elif k1 == 'D':
                    k1 = '<'
            return k1
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

class BPixUi:

    def __init__(self, useColors = True):
        self.UseColors = useColors

    def UseColors(self, useColors = True):
        self.UseColors = useColors

    def Clear(self):
        try:
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
        except:
            pass

    def AskUser(self, question, answers, DisplayWidth=80):
        Selection=0

        First = True
        print "+%s+"%('-'*(DisplayWidth-2))
        if type(question) == list:
            for line in question:
                print "|  %s|" % line.ljust((DisplayWidth - 4))
        else:
            print "|  %s|"%question.ljust((DisplayWidth-4))
        print "+%s+"%('-'*(DisplayWidth-2))

        while True:
            #os.system('clear')
            AnswerIndex = 0

            if not First:
                for answer in answers:
                    sys.stdout.write("\033[F")
                sys.stdout.write("\033[F")
            First = False
            for answer in answers:
                AnswerFormatted = answer[1]
                extraChars = 0
                if '_' in AnswerFormatted:
                    p1 = AnswerFormatted.find('_')
                    if self.UseColors:
                        AnswerFormatted = AnswerFormatted[0:p1] + '\x1b[31m' + AnswerFormatted[p1+1] + '\x1b[30m' + AnswerFormatted[p1+2:]
                    else:
                        AnswerFormatted = AnswerFormatted[0:p1] + '[' + AnswerFormatted[
                            p1 + 1] + ']' + AnswerFormatted[p1 + 2:]
                        extraChars += 2

                if AnswerIndex == Selection:
                    if self.UseColors:
                        AnswerFormatted = "  \x1b[42m{answer}\x1b[47m\x1b[0m".format(answer=AnswerFormatted)
                    else:
                        AnswerFormatted = "  > {answer}".format(answer=AnswerFormatted)
                        extraChars += 2
                else:
                    AnswerFormatted = "  {answer}".format(answer=AnswerFormatted)

                if '_' in answer[1]:
                    padLen = (DisplayWidth-3)
                else:
                    padLen = (DisplayWidth-4)
                print "|%s|"%(AnswerFormatted + ' '*(padLen-len(answer[1])-extraChars))

                AnswerIndex += 1
            print "+%s+" % ('-' * (DisplayWidth-2))

            ans = getch()
            if ans == '^':
                if Selection > 0:
                    Selection -= 1
                else:
                    Selection = len(answers)-1
            elif ans == 'V':
                if Selection < len(answers)-1:
                    Selection += 1
                else:
                    Selection = 0
            elif ord(ans) == 13:
                return answers[Selection][0]
            else:
                for answer in answers:
                    p1 = answer[1].find('_')
                    if p1>=0:
                        if ans == answer[1][p1+1].lower():
                            return answer[0]

    def AskUser2D(self, question, answers, DisplayWidth=80, HeaderColumn = []):
        Selection=[0,0]
        First = True
        if len(question) > 0:
            print "+%s+"%('-'*(DisplayWidth-2))
            print "|  %s|"%question.ljust((DisplayWidth-4))
            print "+%s+"%('-'*(DisplayWidth-2))
        while True:
            #os.system('clear')
            AnswerIndex = 0

            if not First:
                for answer in answers:
                    sys.stdout.write("\033[F")
                if len(question) > 0:
                    sys.stdout.write("\033[F")

            First = False

            AnswerIndexRow = 0
            for answerLine in answers:
                answerLineString = ''
                AnswerIndexColumn = 0
                for answer in answerLine:

                    AnswerFormatted = answer.replace('\n','')

                    if Selection == [AnswerIndexRow, AnswerIndexColumn]:
                        if self.UseColors:
                            AnswerFormatted = "  \x1b[42m{answer}\x1b[47m\x1b[0m ".format(answer=AnswerFormatted)
                        else:
                            AnswerFormatted = " [{answer}]".format(answer=AnswerFormatted)
                    else:
                        AnswerFormatted = "  {answer} ".format(answer=AnswerFormatted)

                    answerLineString += AnswerFormatted + ' '

                    AnswerIndexColumn += 1
                if AnswerIndexRow < len(HeaderColumn):
                    answerLineString = HeaderColumn[AnswerIndexRow] + ' ' + answerLineString

                print answerLineString
                AnswerIndexRow += 1

            if len(question) > 0:
                print "+%s+" % ('-' * (DisplayWidth-2))

            ans = getch()
            if ans == '^':
                if Selection[0] > 0:
                    Selection[0] -= 1
                else:
                    Selection[0] = len(answers)-1
            elif ans == 'V':
                if Selection[0] < len(answers)-1:
                    Selection[0] += 1
                else:
                    Selection[0] = 0
            elif ans == '<':
                if Selection[1] >0:
                    Selection[1] -= 1
            elif ans == '>':
                if Selection[1] < len(answers[0])-1:
                    Selection[1] += 1
            elif ord(ans) == 13:
                return Selection
