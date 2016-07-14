import sys
import termios
import tty

try:
    from msvcrt import getch
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

def AskUser(question, answers, DisplayWidth=80):
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
            if '_' in AnswerFormatted:
                p1 = AnswerFormatted.find('_')
                AnswerFormatted = AnswerFormatted[0:p1] + '\x1b[31m' + AnswerFormatted[p1+1] + '\x1b[30m' + AnswerFormatted[p1+2:]
            if AnswerIndex == Selection:
                AnswerFormatted = "  \x1b[47m{answer}\x1b[0m".format(answer=AnswerFormatted)
            else:
                AnswerFormatted = "  {answer}".format(answer=AnswerFormatted)

            if '_' in answer[1]:
                padLen = (DisplayWidth-3)
            else:
                padLen = (DisplayWidth-4)
            print "|%s|"%(AnswerFormatted + ' '*(padLen-len(answer[1])))

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

def AskUser2D(question, answers, DisplayWidth=80, HeaderColumn = []):
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
                    AnswerFormatted = "  \x1b[47m{answer}\x1b[0m".format(answer=AnswerFormatted)
                else:
                    AnswerFormatted = "  {answer}".format(answer=AnswerFormatted)

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
