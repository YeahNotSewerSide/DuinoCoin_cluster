import socket
import time
import sys
import os
import statistics
import re
import subprocess
import configparser
import datetime
import locale
import json
import platform
from pathlib import Path
import requests
from colorama import init, Fore, Back, Style
from pypresence import Presence
import threading
import struct
import select

# Return datetime object
def now():
    return datetime.datetime.now()

minerVersion = "2.4"  # Version number
timeout = 30  # Socket timeout
resourcesFolder = "PCMiner_" + str(minerVersion) + "_resources"
username = ''
efficiency= ''
donationlevel= ''
debug= ''
threadcount= ''
requestedDiff= ''
rigIdentifier= ''
lang= ''
algorithm= ''
config = configparser.ConfigParser()
serveripfile = ("https://raw.githubusercontent.com/"
    + "revoxhere/"
    + "duino-coin/gh-pages/"
    + "serverip.txt")  # Serverip file
masterServer_address = ''
masterServer_port = 0


# Config loading section
def loadConfig():
    global username
    global efficiency
    global donationlevel
    global debug
    global threadcount
    global requestedDiff
    global rigIdentifier
    global lang
    global algorithm

    config.read(resourcesFolder + "/Miner_config.cfg")
    username = config["miner"]["username"]
    efficiency = config["miner"]["efficiency"]
    threadcount = config["miner"]["threads"]
    requestedDiff = config["miner"]["requestedDiff"]
    donationlevel = config["miner"]["donate"]
    algorithm = config["miner"]["algorithm"]
    rigIdentifier = config["miner"]["identifier"]
    debug = config["miner"]["debug"]
    # Calulate efficiency for use with sleep function
    efficiency = (100 - float(efficiency)) * 0.01


class Device:
    def __init__(self,name,connection,address):
        self.name = name
        self.connection = connection
        self.address = address

    def send_job(self,
                algorithm:str,
                last_block:str,
                expected_hash:str,
                start,
                end) -> bool:
        data = algorithm\
               + ',' + last_block\
               + ',' + expected_hash\
               + ',' + str(start)\
               + ',' + str(end)

        data_bytes = data.encode('ascii')

        try:
            self.connection.send(data_bytes)
        except:
            return False

        return True
    
    def end_job(self):
        data_bytes = b'END'
        try:
            self.connection.send(data_bytes)
        except:
            return False 
        try:
            data = self.connection.recv(1)
            if data[0] == 0:
                return False
        except:
            return False
        return True


devices = []

new_devices = []
#hashes_to_process = []

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )

soc = socket.socket()
soc.settimeout(30)

def connect_to_master():
    print('CONNECTING TO MASTER')
    global soc
    try:
        soc.close()
    except:
        pass
    while True:
        soc = socket.socket()
        # Establish socket connection to the server
        try:
            soc.connect((str(masterServer_address),
                            int(masterServer_port)))
            serverVersion = soc.recv(3).decode().rstrip("\n")  # Get server version
        except:
            continue
        break

working_with_server = threading.Lock()


def hash_process(job):
    print()
    real_difficulty = (100 * int(job[2]))
    devices_counter = 0
        
    start = int(job[2])*2
    step = (real_difficulty - start)//len(devices)
    end = start + step
    while devices_counter<len(devices):
        result = devices[devices_counter].send_job(algorithm,
                                                       job[0],
                                                       job[1],
                                                       start,
                                                       end)

        if not result:
            print('Device:',devices[devices_counter].name,'is not responding')
            del devices[devices_counter]
            step = (real_difficulty - start)//len(devices)
            end = start + step
            continue

        start = end
        end = start + step
        devices_counter += 1

    inputs = []
    for device in devices:
        inputs.append(device.connection)

    result = None
    while result == None:
        readable, writable, exceptional = select.select(inputs, [], [])
        for conn in readable:
            try:
                data = conn.recv(1024).decode('ascii')    
            except:
                result = ''
                print('ONE WORKER DOWN!')
                break
            if data != 'None':
                result = data.split(',')
                break
                
    print('ACCEPTED RESULT')
    counter = 0
    print('ENDING JOB')
    while counter < len(devices):
        device = devices[counter]
        res = device.end_job()
        if not res:
            del devices[counter]
            continue
        counter += 1

    if result == '':
        print('giving up on that block')
        return
    print('SENDING RESULT')
    while True:
        try:
            soc.send(bytes(
                        str(result[0])
                        + ","
                        + str(result[1])
                        + ","
                        + "Official PC Miner ("
                        + str(algorithm)
                        + ") v" 
                        + str(minerVersion)
                        + ","
                        + str(rigIdentifier),
                        encoding="utf8"))
            feedback = soc.recv(8).decode().rstrip("\n")
            break
        except:
            print('Net error, reconnecting')
            connect_to_master()       

    print('FEEDBACK:',feedback)
    if feedback == 'GOOD':
        print('HASH ACCEPETED!')
    elif feedback == 'BLOCK':
        print('HASH BLOCK!')
    else:
        print('HASH REJECTED!')


#THREAD
def hashes_reciever():
    
    while True:
        print()
        connect_to_master()

        while True:
            print()
            if len(devices) == 0:
                print('No devices connected!')
                time.sleep(5)
                continue
            print('ASKING FOR JOB')
            try:
                if algorithm == "XXHASH":
                    soc.send(bytes(
                    "JOBXX,"
                    + str(username)
                    + ","
                    + str(requestedDiff),
                    encoding="utf8"))
                else:
                    soc.send(bytes(
                    "JOB,"
                    + str(username)
                    + ","
                    + str(requestedDiff),
                    encoding="utf8"))
            except Exception as e:
                break
            
            job = soc.recv(128).decode().rstrip("\n")
            job = job.split(",")  # Get work from pool
            
            if len(job) < 2:
                print('STRANGE PACKET')
                continue
            if job[1] == "This user doesn't exist":
                raise Exception('User doesnt exist')
            elif job[0] == 'BAD':
                print(job)
                continue
            print('recieved job:',job)

            hash_process(job)
            #hashes_to_process.append(job)
        time.sleep(5)




PORT = 9090
HOST = '0.0.0.0'
def cluster_server():
    global PORT,HOST,server_socket
    global devices,new_devices
    
    server_socket.bind((HOST,PORT))
    server_socket.listen(5)
    
    print('SERVER STARTED!')

    while True:
        device = server_socket.accept()
        new_devices.append(device)
        print('New connection!')

#THREAD
def device_initiator():
    global devices,new_devices

    while True:
        try:
            device_connection = new_devices.pop()
        except:
            time.sleep(3)
            continue

        try:
            data = device_connection[0].recv(1024)
        except:
            continue

        try:
            name = data.decode('ascii')
        except:
            continue
        print(name,'CONNECTED')
        device = Device(name,*device_connection)
        devices.append(device)




if __name__ == '__main__':
    loadConfig()
    while True:
        try:
            res = requests.get(serveripfile, data=None)
            break
        except:
            pass
        print('getting data again')
        time.sleep(10)

    if res.status_code == 200:
        # Read content and split into lines
        content = (res.content.decode().splitlines())
        masterServer_address = content[0]  # Line 1 = pool address
        masterServer_port = content[1]  # Line 2 = pool port
    else:
        raise Exception('CANT GET MASTER SERVER ADDRESS')

    device_initiator_thread = threading.Thread(target=device_initiator,args=[],name='device_initiator')
    #hashes_sender_thread = threading.Thread(target=hashes_sender,args=[])
    hashes_reciever_thread = threading.Thread(target=hashes_reciever,args=[],name='hashes_receiver')

    device_initiator_thread.start()
    hashes_reciever_thread.start()
    cluster_server()
