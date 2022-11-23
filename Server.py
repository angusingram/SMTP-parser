from ast import Global
from distutils.log import error
from os import mkdir
from os.path import exists
import re, sys, socket, socketserver

#starts to process input, dividing into 4 possible starting subgroups. M, R, D, or invalid 

global connected

def readText():
    try:
        text = input()
        print(text)
        return text
    except EOFError:
        quit()

# state 0 = mailfrom, state 1 = rectto, state 3 = data. 

state = "mailfrom"

buff = []   ##apend good messages here
addy = []
def regEx(buff, state, clientS):
    #print(state)
    input = clientS.recv(4096).decode("utf-8")
    print(input)
    input = input.split(":")
    mailFrom = re.match('MAIL\s+FROM$', input[0])
    rcptTo = re.match('RCPT\s+TO$', input[0])

    if len(input) > 1:
        address = re.match('\s*<(\w+@[a-zA-Z][a-zA-Z0-9-]*(\.[a-zA-Z][a-zA-Z0-9-]*)*)>\s*$', input[1])    ##reg ex
        if (address != None):
            addy.append(address.group(0))
        
    #print(rcptTo)
    data = re.match('DATA\s*$', input[0])
    #print(data)
    if state == "mailfrom":
        if rcptTo != None or data != None:
            clientS.send('503 Bad sequence of commands'.encode())
            print('503 Bad sequence of commands')
            return False
        if (mailFrom == None):
            clientS.send('500 Syntax error: command unrecognized'.encode())
            print('500 Syntax error: command unrecognized')

        elif (mailFrom!=None):
            buff.append(mailFrom.group(0))
            if (address == None):
                clientS.send('501 Syntax error in parameters or arguments'.encode())
                print('501 Syntax error in parameters or arguments')
                return False
            clientS.send("250 OK".encode())
            print("250 OK\r\n")
            return True
        else:
            return False

    if state == "rcptto":
        if mailFrom != None or data != None:
            print('503 Bad sequence of commands')
            clientS.send('503 Bad sequence of commands'.encode())
            return False
        if (rcptTo == None):
            print('500 Syntax error: command unrecognized')
            clientS.send('500 Syntax error: command unrecognized'.encode())
        elif (rcptTo!=None):
            buff.append(rcptTo.group(0))
            if (address == None):
                clientS.send('501 Syntax error in parameters or arguments'.encode())
                print('501 Syntax error in parameters or arguments')
                return False
            clientS.send("250 OK".encode())
            print("250 OK\r\n")
            return True
        else:
            return False

    if state == "data":
        if mailFrom != None or rcptTo != None:
            print('503 Bad sequence of commands')
            return False
        if(data == None):
            clientS.send('500 Syntax error: command unrecognized'.encode())
            print('500 Syntax error: command unrecognized')
        elif (data!=None):
            buff.append(data.group(0))
            clientS.send("354 Start mail input; end with . on a line by itself".encode())
            print("354 Start mail input; end with . on a line by itself",end="\r\n")
            return True
        else:
            return False

def mail(buff, state, clientS):
        #input = readText()
        ismail = regEx(buff, state, clientS)
        return ismail
def rcptTo(buff, state, clientS):# check for RCPT
        #input = readText()
        isrcpt = regEx(buff, state, clientS)
        return isrcpt

def data(buff, state, clientS):
       # input = readText()
        isData = regEx(buff, state, clientS)
        if (isData == True):
            while(True):

                
                    x = clientS.recv(4096).decode("utf-8")
                    print(x)
                    if x[-3:] == "\n.\n":   #check for with new line alone 
                        clientS.send("250 OK".encode())
                        print("250 OK\r\n")
                        clientS.send(f'221 {socket.getfqdn()} closing connection'.encode())
                        print(f'221 {socket.getfqdn()} closing connection\r\n')
                        clientS.close()
                        buff.append(x)
                        return True
                        
                        
                    '''    
                except:
                    clientS.send("250 OK\r\n".encode())
                    print("250 OK\r\n")
                    return True
                buff.append(x)
                '''
        else:
            return False

def openConnection():
    global connected
    #TODO: figure this thang out 
    port = int(sys.argv[1])
    while True:             #loops waiting for a connection
        try:
            serverS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)            #TODO check for errors here later
        except socket.error as error:
            print(error)
        try:
            serverS.bind((socket.getfqdn(), port))
        except socket.error as error:
            print(error)
        serverS.listen(5)
        clientS, addy = serverS.accept()
        connected = True  #we are now connected 
        cont = True
        hostDomain = socket.getfqdn()     #sets host domain
        clientS.send(f"220 {hostDomain}".encode())   #sends first 220 message to the client (remember: server talks first!!)
        # gets message and writes to stdout. if there is a quit, then it sends 221 "host name" closing message 
        print(f"220 {hostDomain}\r\n")
        try:
            message = clientS.recv(4096).decode("utf-8")
        except socket.error as err:
            serverS.close()            #close it if error, disconnected
            connected = False
            cont = False
        if cont:
            #at this point code has established that message is not a QUIT and no errors have been thrown thus far
            #now checking for helo message correctnes 
            m = message[0:4]
            if (message[0:4] == 'HELO'):
                helo = re.match('HELO\s(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$', message)
                if helo:
                    clientS.send(f'250 Hello{helo.group(0)[4:]} pleased to meet you'.encode())
                    print(f'250 Hello{helo.group(0)[4:]} pleased to meet you\r\n')
                    start_mail = True
                else:
                    clientS.send('501 Syntax error in parameters or arguments'.encode())
                    print('501 Syntax error in parameters or arguments\r\n')
                    cont = False
                    start_mail = False
            elif(m == 'MAIL ' or m == 'RCPT '):
                clientS.send('503 Bad sequence of commands'.encode())
                print('503 Bad sequence of commands')
            else:
                clientS.send('500 Syntax error: command unrecognized'.encode())
                print('500 Syntax error: command unrecognized\r\n')
                cont = False
                start_mail = False
        if start_mail:
            main(clientS)

def main(clientS):
    state = "mailfrom"
    flag = True

    while True:
        
        #print(f"Mail {ismail}")
        if state == 'mailfrom':
            ismail = mail(buff, state, clientS)
            if ismail:
                state = "rcptto"

        if state == 'rcptto':
            isrcpt = rcptTo(buff, state, clientS)
            if isrcpt:
                state = "data"

        if state == 'data':
            isData = data(buff, state, clientS)
            state = "mailfrom"
            if (exists("forward") != True):
                mkdir("forward/")
            y = addy[1]
            num = y.find("@")
            fileName = "forward/"+y[num+1:]     #this names the file as the email stored in buff 2 if not done already
            num = fileName.find(">")
            fileName = fileName[:num]
            with open((fileName), "a") as writer:      #opens file          #writes to file
                for i in range(len(addy)):
                # print(buff[i]+ ":"+addy[i]+"\n")
                    writer.write(buff[i]+ ":"+addy[i]+"\n")
                k = len(addy)
                for a in range(len(buff) - k):
                # print(buff[a+k]+ "\n")
                    writer.write(buff[a+k]+ "\n")
                buff.clear()
                addy.clear()


openConnection()






   

