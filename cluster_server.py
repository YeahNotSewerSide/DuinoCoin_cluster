import socket
import time
import configparser
import json
import requests
import threading
import struct
import select
import traceback
import logging
import types

# https://github.com/DoctorEenot/DuinoCoin_android_cluster
'''
For more details go to projects page:
https://github.com/DoctorEenot/DuinoCoin_android_cluster
'''

'''
GLOBALS:
'''
username = ''
requestedDiff= ''
rigIdentifier= ''
algorithm= ''
MIN_DIFFICULTY = 300000 #real difficulty to start dividing jobs
INC_COEF = 0
TIME_FOR_DEVICE = 90 #Time for device to update it's aliveness
DISABLE_LOGGING = True
PING_MASTER_SERVER = 40 # Seconds to ping master server

config = configparser.ConfigParser()
serveripfile = ("https://raw.githubusercontent.com/"
    + "revoxhere/"
    + "duino-coin/gh-pages/"
    + "serverip.txt")  # Serverip file
masterServer_address = ''
masterServer_port = 0


'''
LOGGER:
'''
logger = logging.getLogger('Cluster_Server')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
if not DISABLE_LOGGING:
    fh = logging.FileHandler('Cluster_Server.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_master_server_info():
    global masterServer_address
    global masterServer_port

    logger.info('Getting Master server info')
    while True:
        try:
            res = requests.get(serveripfile, data=None)
            break
        except:
            pass
        logger.info('getting data again')
        time.sleep(10)

    if res.status_code == 200:
        logger.info('Master server info accepted')
        # Read content and split into lines
        content = (res.content.decode().splitlines())
        masterServer_address = content[0]  # Line 1 = pool address
        masterServer_port = content[1]  # Line 2 = pool port
    else:
        raise Exception('CANT GET MASTER SERVER ADDRESS')

# Config loading section
def loadConfig():
    global username
    global requestedDiff
    global rigIdentifier
    global algorithm
    global MIN_DIFFICULTY
    global INC_COEF
    global TIME_FOR_DEVICE
    global DISABLE_LOGGING

    logger.info('Loading config')
    config.read('Cluster_Config.cfg')
    username = config["cluster"]["username"]
    requestedDiff = config["cluster"]["difficulty"] # LOW/MEDIUM/NET
    algorithm = config["cluster"]["algorithm"] # XXHASH/DUCO-S1
    rigIdentifier = config["cluster"]["identifier"]
    MIN_DIFFICULTY = int(config['cluster']['MIN_DIFFICULTY'])
    INC_COEF = int(config['cluster']['INC_COEF'])
    TIME_FOR_DEVICE = int(config['cluster']['TIME_FOR_DEVICE'])
    DISABLE_LOGGING = bool(config['cluster']['DISABLE_LOGGING'])



class Device:
    def __init__(self,name,address):
        self.name = name
        self.last_updated = time.time()
        self.busy = False
        self.address = address

    def is_alive(self):
        return (time.time()-self.last_updated)<TIME_FOR_DEVICE
    def update_time(self):
        self.last_updated = time.time()
    def isbusy(self):
        return self.busy
    def job_stopped(self):
        self.busy = False
    def job_started(self):
        self.busy = True

    def __str__(self):
        return self.name+' '+str(self.address)
    def __repr__(self):
        return str(self)



devices = {}


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
server_socket.setblocking(False)
SERVER_ADDRESS = ('0.0.0.0',9090)
server_socket.bind(SERVER_ADDRESS)

master_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
master_server_socket.settimeout(15)
master_server_timeout = 15
master_server_is_connected = False
master_server_last_pinged = 0

def connect_to_master(dispatcher,event):
    '''
    event - {'t':'e',
             'event':'connect_to_master'}
    '''
    logger.info('CONNECTING TO MASTER')
    global master_server_socket
    global masterServer_address
    global masterServer_port
    global master_server_timeout
    global master_server_is_connected

    try:
        event.dict_representation['address']
        return
    except:
        pass

    master_server_is_connected = False

    get_master_server_info()
    while True:
        master_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        master_server_socket.settimeout(15)
        # Establish socket connection to the server
        try:
            master_server_socket.connect((str(masterServer_address),
                                        int(masterServer_port)))
        except Exception as e:
            yield
            continue
        master_server_socket.settimeout(0)
        serverVersion = None
        timeout_start = time.time()
        while time.time()-timeout_start<master_server_timeout:
            try:
                serverVersion = master_server_socket.recv(3).decode().rstrip("\n")  # Get server version
                master_server_is_connected = True
                break
            except Exception as e:
                yield
        if serverVersion != None\
           and serverVersion != '':      
            break



def register(dispatcher,event):
    '''
    event = {'t':'e',
              'event':'register',
              'name':'Test',
              'address':('127.0.0.1',1234),
              'callback':socket}
    '''
    global devices
    
    logger.info('Register')
    device = devices.get(event.address,None)
    if device != None:
        event.callback.sendto(b'{"t":"a",\
                                "status":"ok",\
                                "message":"already exists"}',
                                event.address)
        device.update_time()
        return None


    devices[event.address] = Device(event.name,event.address)
    devices[event.address].update_time()
    event.callback.sendto(b'{"t":"a",\
                             "status":"ok",\
                             "message":"device added"}',
                             event.address)
    
    event_ = Event({'t':'e',
                   'event':'get_job',
                   'address':event.address,
                   'callback':event.callback})
    dispatcher.add_to_queue(event_)

    return None

def ping(dispatcher,event):
    '''
    event = {'t':'e',
             'event':'ping',
             'address':('127.0.0.1',1234),
              'callback':socket}
    '''
    global devices

    logger.debug('Ping')
    device = devices.get(event.address,None)
    if device == None:
        event.callback.sendto(b'{"t":"e",\
                             "event":"register",\
                             "message":"You must register in cluster"}',
                              event.address)
        return None
    
    device.update_time()
    data = b'{"t":"a","status":"ok","message":"server is running"}'
    event.callback.sendto(data,event.address)
    return None

JOB = None
JOB_START_SECRET = 'ejnejkfnhiuhwefiy87usdf'
JOBS_TO_PROCESS = {}
HASH_COUNTER = 0
JOB_STARTED_TIME = 0


class Job:
    def __init__(self,devices = []):
        self.devices = devices
        self.done = False
    def set_device(self,device):
        self.devices.append(device)
    def get_devices(self):
        return self.devices
    def is_done(self):
        return self.done
    def set_done(self):
        self.done = True
    def is_claimed(self):
        return len(self.devices)>0
    def unclaim(self):
        self.devices = []
    def number_of_devices(self):
        return len(self.devices)



def job_start(dispatcher,event):
    '''
    event = {'t':'e',
             'event':'job_start',
             'secret':'',
             'callback':socket}
    '''
    global JOB
    global JOB_START_SECRET
    global algorithm
    global JOBS_TO_PROCESS
    global JOB_STARTED_TIME

    if event.secret != JOB_START_SECRET:
        logger.warning('bad secret')
        return

    logger.info('Job is starting')
    JOB_STARTED_TIME = time.time()
    
    counter = 0   
    jobs = list(JOBS_TO_PROCESS.items())

    sent = True
    for addr,device in devices.items():
        if device.isbusy():
            continue
        start_end,job = jobs[counter]
        data = json.dumps({'t':'e',
                          'event':'start_job',
                          'lastBlockHash':JOB[0],
                          'expectedHash':JOB[1],
                          'start':start_end[0],
                          'end':start_end[1],
                          'algorithm':algorithm})
        device.job_started()
        event.callback.sendto(data.encode('ascii'),addr)
        job.set_device(device)
        counter += 1
        if counter == len(jobs):
            return
        yield

        
            

def send_results(dispatcher,result):
    global algorithm
    global minerVersion
    global rigIdentifier
    global HASH_COUNTER
    global devices
    global master_server_timeout

    logger.info('Sending results')
    logger.debug(str(result))
    logger.info('Hashes were checked: '+str(HASH_COUNTER))
    if HASH_COUNTER<result[0]:
        HASH_COUNTER = result[0]

    master_server_socket.settimeout(master_server_timeout)
    while True:
        
        try:
            master_server_socket.send(bytes(
                                    str(result[0])
                                    + ","
                                    + str(HASH_COUNTER)#HASHCOUNTER
                                    + ","
                                    + "YeahNot Cluster("
                                    + str(algorithm)
                                    + f") Devices:{len(devices)}"
                                    + ","
                                    + str(rigIdentifier),
                                    encoding="utf8"))
            feedback = master_server_socket.recv(8).decode().rstrip("\n")
            
        except Exception as e:
            event = {'t':'e',
                     'event':'connect_to_master'}
            event = Event(event)
            dispatcher.add_to_queue(event)
            logger.warning('Giving up on that hash')
            break

        if feedback == 'GOOD':
            logger.info('Hash accepted')
            
        elif feedback == 'BLOCK':
            logger.info('Hash blocked')
            
        elif feedback == '':
            logger.debug('Connection with master is lost')
            #connect_to_master()
            continue
        else:
            logger.info('Hash rejected')
        break
    HASH_COUNTER = 0

def get_job(dispatcher,event):
    '''
    event - {'t':'e',
            'event':'get_job',
            'address':'address',
            'callback':'callback'}
    '''
    global JOB
    global algorithm
    global JOBS_TO_PROCESS
    job_to_send = None

    logger.info('Get job packet')

    device = devices.get(event.address,None)
    if device == None:
        logger.warning('device is not registered')
        event.callback.sendto(b'{"t":"e",\
                             "event":"register",\
                             "message":"You must register in cluster"}',
                              event.address)
        return None
    if not device.is_alive():
        logger.warning('Device '+device.name+' '+str(event.address)+' is dead')
        data = json.dumps({'t':'e',
                           'event':'ping'})
        event.callback.sendto(data.encode('ascii'),event.address)
        return None

    # searching for unclaimed jobs
    for start_end,job in JOBS_TO_PROCESS.items():
        if not job.is_claimed() and not job.is_done():
            job.set_device(device)
            job_to_send = start_end
            break
        yield
    # searching for claimed by 1 device undone jobs
    if job_to_send == None:
        for start_end,job in JOBS_TO_PROCESS.items():
            if not job.is_done():
                job_to_send = start_end
                if not job.number_of_devices()<2:
                    job.set_device(device)
                    job_to_send = start_end
                    break
            yield
              
    if job_to_send == None:
        device.job_stopped()
        logger.warning('CANT FIND FREE JOB')
        return None


    data = json.dumps({'t':'e',
                      'event':'start_job',
                      'lastBlockHash':JOB[0],
                      'expectedHash':JOB[1],
                      'start':job_to_send[0],
                      'end':job_to_send[1],
                      'algorithm':algorithm})
    logger.debug('Sending job: '+data)
    device.job_started()

    event.callback.sendto(data.encode('ascii'),event.address)


def job_done(dispatcher,event):
    '''
    event = {'t':'e',
            'event':'job_done',
            'result':[1,1] | ['None',1],
            'start_end':[1,1],
            'expected_hash':'',
            'address':('127.0.0.1',1234),
            'callback':socket}
    '''
    global JOB
    global algorithm
    global JOBS_TO_PROCESS
    global HASH_COUNTER
    global JOB_STARTED_TIME

    logger.info('job done packet')
    if (event.result[0] == 'None' \
        or event.result[0] == None):
        logger.info('Empty block')
        device = devices.get(event.address,None)
        if device == None:
            logger.warning('device is not registered')
            event.callback.sendto(b'{"t":"e",\
                             "event":"register",\
                             "message":"You must register in cluster"}',
                              event.address)
            return None
        if not device.is_alive():
            logger.warning('Device '+device.name+' '+str(event.address)+' is dead')
            data = json.dumps({'t':'e',
                                'event':'ping'})
            event.callback.sendto(data.encode('ascii'),event.address)
            return None

        device.job_stopped()

        if JOB == None:
            logger.debug('Job is already over')
            data = b'{"t":"a",\
                    "status":"ok",\
                    "message":"No job to send"}'
            event.callback.sendto(data,event.address)
            return

        

        recieved_start_end = tuple(event.start_end)
        if event.expected_hash == None:
            logger.debug('redirect from register')
        else:
            if event.expected_hash == JOB[1]:
                logger.debug('currently running job')
                CURRENT_JOB = None
                try:
                    CURRENT_JOB = JOBS_TO_PROCESS[recieved_start_end]

                except:
                    logger.error('CANT FIND BLOCK: '+str(recieved_start_end))
                if CURRENT_JOB != None:
                    HASH_COUNTER += event.result[1]
                    logger.debug('terminating linked devices')
                    data_dict = {'t':'e',
                                'event':'stop_job',
                                'expected_hash':JOB[1],
                                'start_end':event.start_end,
                                'message':'another device already solved hash'}
                    data = json.dumps(data_dict).encode('ascii')
                    CURRENT_JOB.set_done()
                    
                    for device in CURRENT_JOB.get_devices():
                        if device.address != event.address\
                            and device.isbusy():
                            device.job_stopped()
                            event.callback.sendto(data,device.address)
                        yield
            else:
                logger.debug('Old packet')
        
    
    else:
        logger.info('accepted result')
        recieved_start_end = tuple(event.start_end)
        CURRENT_JOB = JOBS_TO_PROCESS.get(recieved_start_end,None)
        if event.expected_hash != JOB[1]\
           or CURRENT_JOB == None:
            logger.warning('STOP JOB ON WRONG JOB')
            return
        HASH_COUNTER += event.result[1]
        logger.info('HASHRATE: '+str(HASH_COUNTER//(time.time()-JOB_STARTED_TIME))+' H/s')
        send_results(dispatcher,event.result)
        JOBS_TO_PROCESS = {}
        data_dict = {'t':'e',
                     'event':'stop_job',
                     'expected_hash':JOB[1],
                     'start_end':event.start_end,
                     'message':'another device already solved hash'}
        data = json.dumps(data_dict).encode('ascii')
        logger.debug('stopping workers')
        for addr,device in devices.items():
            device.job_stopped()
            if addr != event.address:
                event.callback.sendto(data,addr)
            yield
        JOB = None


def request_job(dispatcher,event):
    '''
    event = {'t':'e',
             'event':'requets_job',
             'secret':'',
             'parts':10}
    '''
    global JOB
    global JOB_START_SECRET
    global algorithm
    global username
    global requestedDiff
    global master_server_socket
    global JOBS_TO_PROCESS
    global INC_COEF
    global master_server_timeout
    global master_server_is_connected

    logger.info('requesting job')
    if event.secret != JOB_START_SECRET:
        logger.warning('bad secret')
        return
    job = None
    while job == None or job == '':
        try:
            if algorithm == "XXHASH":
                master_server_socket.send(bytes(
                    "JOBXX,"
                    + str(username)
                    + ","
                    + str(requestedDiff),
                    encoding="utf8"))
            else:
                master_server_socket.send(bytes(
                    "JOB,"
                    + str(username)
                    + ","
                    + str(requestedDiff),
                    encoding="utf8"))
        except Exception as e:
            master_server_is_connected = False
            logger.error('asking for job error accured')
            event = {'t':'e',
                     'event':'connect_to_master'}
            event = Event(event)
            dispatcher.add_to_queue(event)
            break

        # make socket non-blocking
        master_server_socket.settimeout(0)
        timeout_start = time.time()
        master_server_is_connected = False

        # pure implementation of timeout for socket, but with yielding back to main event loop
        while time.time()-timeout_start<master_server_timeout:
            try:
                job = master_server_socket.recv(128).decode().rstrip("\n")
                master_server_is_connected = True
                break
            except:
                yield
                continue

        # server didn't respond in <master_server_timeout> seconds
        if job == None:
            master_server_is_connected = False
            logger.warning('Couldnt recieve job from server')
            event = {'t':'e',
                     'event':'connect_to_master'}
            event = Event(event)
            dispatcher.add_to_queue(event)
            yield
            continue

        # if server sent job
        job = job.split(",")
        if job[0] == 'BAD':
            logger.warning('GOT "BAD" PACKET IN RESPONSE')
            return
        elif job[0] == '':
            logger.warning('CONNECTION WITH MASTER SERVER WAS BROKEN')
            #connect_to_master()
            continue
        logger.info('job accepted')
        logger.info('Difficulty: '+str(job[2]))
        logger.debug(str(job))

        event = Event({'t':'e',
                       'event':'job_start',
                       'secret':JOB_START_SECRET,
                       'callback':server_socket})
        dispatcher.add_to_queue(event)

        JOBS_TO_PROCESS = {}
        parts = len(devices)+INC_COEF

        JOB = job[:2]
        real_difficulty = (100*int(job[2]))

        if real_difficulty <= MIN_DIFFICULTY:
            job_part = real_difficulty
        else:
            job_part = (real_difficulty//parts)

        start = 0
        if job_part == real_difficulty:
            end = job_part+1
        else:
            end = job_part
        while start<real_difficulty:
            job_object = Job()
            JOBS_TO_PROCESS[(start,end)] = job_object
            start = end
            if real_difficulty<=end+job_part:
                end = real_difficulty+1
            else:
                end += job_part
        logger.debug('JOB: '+str(JOBS_TO_PROCESS))

        break

def clean_up_devices(dispatcher,event):
    try:
        # if event was recieved by server
        event.dict_representation['address']
        return None
    except:
        pass

    counter = 0
    items = list(devices.items())
    while counter<len(devices):
        address,device = items[counter]
        if not device.is_alive():
            del devices[address]
            del items[counter]
            continue
        counter += 1
        yield



class Event(object):
    def __init__(self,input:dict):
        self.dict_representation = input
    def __dict__(self):
        return super(Event, self).__getattribute__('dict_representation')
    #def event_name(self) -> str:
    #    return self.dict_representation['event']
    def __getattribute__(self, item):
        # Calling the super class to avoid recursion
        return super(Event, self).__getattribute__(item)
    def __getattr__(self, item):
        
        try:
            return super(Event, self).__getattribute__('dict_representation')[item]
        except:
            logger.warning('NO SUCH ELEMENT AS '+str(item))
            pass
    def __str__(self):
        return str(self.dict_representation)

class Dispatcher:
    def __init__(self):
        self.actions = {}
        self.queue = []
        self.active_loop = []

    def register(self,event_name,action):
        self.actions[event_name] = action
    
    def add_to_queue(self,event:Event):
        logger.debug('added event')
        logger.debug(str(event.dict_representation))
        self.queue.append(event)

    def clear_queue(self):
        self.queue = []

    def iter_through_active_list(self):
        counter = 0
        while counter<len(self.active_loop):
            try:
                next(self.active_loop[counter])
            except StopIteration:
                self.active_loop.pop(counter)
                continue
            counter += 1

    def dispatch_event(self,count=1):
        for i in range(count):
            try:
                event = self.queue.pop(0)
            except:
                return None
            logger.debug('dispatching event')
            func = self.actions.get(event.event,None)
            if func == None:
                logger.warning('NO SUCH ACTION '+event.event)
                return None
            activity = self.actions[event.event](self,event)
            if isinstance(activity,types.GeneratorType):
                self.active_loop.append(activity)



def ping_master(dispatcher,event):
    '''
    event - {'t':'e',
             'event':'ping_master'}
    '''
    global master_server_socket
    global master_server_last_pinged
    global master_server_is_connected
    global master_server_timeout

    return None

    logger.info('Pinging master server')
    ping_packet = b'PING'
    master_server_last_pinged = time.time()
    try:
        master_server_socket.send(ping_packet)
    except Exception as e:
        master_server_is_connected = False
        
    master_server_socket.settimeout(master_server_timeout)
    try:
        data = master_server_socket.recv(5)
    except Exception as e:
        master_server_is_connected = False
        new_event = Event({'t':'e',
                           'event':'connect_to_master'})
        dispatcher.add_to_queue(new_event)
    master_server_socket.settimeout(0)




def server():
    global server_socket
    global devices
    global MIN_PARTS
    global INC_COEF
    global TIME_FOR_DEVICE
    global master_server_last_pinged
    global PING_MASTER_SERVER

    logger.debug('Initializing dispatcher')
    event_dispatcher = Dispatcher()
    event_dispatcher.register('register',register)
    event_dispatcher.register('ping',ping)
    event_dispatcher.register('job_start',job_start)
    event_dispatcher.register('job_done',job_done)
    event_dispatcher.register('request_job',request_job)
    event_dispatcher.register('clean_up_devices',clean_up_devices)
    event_dispatcher.register('connect_to_master',connect_to_master)
    event_dispatcher.register('get_job',get_job)
    event_dispatcher.register('ping_master',ping_master)
    logger.debug('Dispatcher initialized')

    event = {'t':'e',
             'event':'connect_to_master'}
    event = Event(event)
    event_dispatcher.add_to_queue(event)
    event_dispatcher.dispatch_event()
    event_dispatcher.iter_through_active_list()


    last_devices_cleenup = time.time()
    last_ping_master = time.time()

    while True:
        # recieving events
        data = None
        try:
            data, address = server_socket.recvfrom(1024)
        except:
            pass

        # parsing events and registering events
        if data != None:
            data_is_ok = False
            try:
                message = json.loads(data.decode('ascii'))
                data_is_ok = True
            except:
                logger.warning("can't parse packet")
                logger.debug(str(data))
            if data_is_ok:
                logger.debug('accepted packet')
                logger.debug(str(message))
                if message['t'] == 'e':
                    message['address'] = address
                    message['callback'] = server_socket
                    event = Event(message)
                    event_dispatcher.add_to_queue(event)
                else:
                    device = devices.get(address,None)
                    if device == None:
                        server_socket.sendto(b'{"t":"e",\
                                                "event":"register",\
                                                "message":"You must register in cluster"}',
                                                address)
                    else:
                        device.update_time()
        
        # dispatching events
        try:
            event_dispatcher.dispatch_event(3)
        except Exception as e:
            logger.error('CANT DISPATCH EVENT')
            logger.debug('Traceback',exc_info=e)
        try:
            event_dispatcher.iter_through_active_list()
        except Exception as e:
            logger.error('CANT EXECUTE')
            logger.debug('Traceback',exc_info=e)



        # request job and start it
        if len(devices)>0 and master_server_is_connected:
            # Well new server doesn't like that
            #if time.time()-master_server_last_pinged>PING_MASTER_SERVER:
            #    event = Event({'t':'e',
            #                   'event':'ping_master'})
            #    event_dispatcher.add_to_queue(event)
            if JOB == None:
                event_dispatcher.clear_queue()
                event = Event({'t':'e',
                               'event':'request_job',
                               'secret':JOB_START_SECRET,
                               'parts':20})
                event_dispatcher.add_to_queue(event)

        

        # cleenup devices
        if time.time()-last_devices_cleenup>TIME_FOR_DEVICE:
            last_devices_cleenup = time.time()
            logger.debug('Cleaning up devices')
            event = {'t':'e',
                     'event':'clean_up_devices'}
            event = Event(event)
            event_dispatcher.add_to_queue(event)
        
        time.sleep(0.1)



if __name__ == '__main__':
    logger.info('STARTING SERVER')
    loadConfig()

    #connect_to_master()
    try:
        server()
    except Exception as e:
        logger.error('ERROR ACCURED',exc_info=e)

    input()

    
