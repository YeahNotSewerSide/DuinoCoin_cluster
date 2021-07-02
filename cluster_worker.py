import hashlib
import xxhash
import socket
import threading
import time
import struct
import traceback
import logging
import json
import types

logger = logging.getLogger('Cluster_Client')
logger.setLevel(logging.DEBUG)
#fh = logging.FileHandler('Cluster_Client.log')
#fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
#logger.addHandler(fh)
logger.addHandler(ch)

WORKER_NAME = 'TEST'
CLUSTER_SERVER_ADDRESS = ('127.0.0.1',9090)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
client_socket.setblocking(False)

END_JOB = True

calculation_result = [None,0,0,0,None]
calculation_thread = None

EXPECTED_HASH = None
START_END = None
JOB_WAS_TERMINATED = False

ping_delay = 30
last_ping = 0

def update_last_ping():
    global last_ping
    last_ping = time.time()

def to_ping():
    global ping_delay
    global last_ping
    return time.time()-last_ping>ping_delay

def ducos1(
        lastBlockHash,
        expectedHash,
        start,
        end):
    global END_JOB,calculation_result
    hashcount = 0
    base_hash = hashlib.sha1(str(lastBlockHash).encode('ascii'))
    temp_hash = None
    for ducos1xxres in range(int(start),int(end)):
        if END_JOB:
            logger.info('JOB TERMINATED')
            calculation_result = [None,0,0,0,None]
            return None
        temp_hash = base_hash.copy()
        temp_hash.update(str(ducos1xxres).encode('ascii'))
        ducos1xx = temp_hash.hexdigest()
        # Increment hash counter for hashrate calculator
        hashcount += 1
        # Check if result was found
        if ducos1xx == expectedHash:
            END_JOB = True
            logger.debug('LEFT '+str(ducos1xxres))
            calculation_result = [ducos1xxres, hashcount,start,end,expectedHash]
            return None
    logger.info('Empty block')
    END_JOB = True
    calculation_result = [None,hashcount,start,end,expectedHash]

def ducos1xxh(
        lastBlockHash,
        expectedHash,
        start,
        end):
    global END_JOB,calculation_result
    hashcount = 0
    base_hash = xxhash.xxh64(str(lastBlockHash),seed=2811)
    temp_hash = None
    for ducos1xxres in range(int(start),int(end)):
        if END_JOB:
            logger.info('JOB TERMINATED')
            calculation_result = [None,0,0,0,None]
            return None

        temp_hash = base_hash.copy()
        temp_hash.update(str(ducos1xxres))
        ducos1xx = temp_hash.hexdigest()
        # Increment hash counter for hashrate calculator
        hashcount += 1
        # Check if result was found
        if ducos1xx == expectedHash:
            END_JOB = True
            logger.debug('LEFT '+str(ducos1xxres))
            calculation_result = [ducos1xxres, hashcount,start,end,expectedHash]
            return None
    logger.info('Empty block')
    END_JOB = True
    calculation_result = [None,hashcount,start,end,expectedHash]
    
def get_job():
    global client_socket
    global CLUSTER_SERVER_ADDRESS
    global END_JOB

    END_JOB = False

    data = json.dumps({'t':'e',
                        'event':'get_job'}).encode('ascii')
    client_socket.sendto(data,CLUSTER_SERVER_ADDRESS)


def ping(dispatcher,event):
    '''
    event - {'t':'e',
            'event':'ping',
            'address':(1,1)}
    '''
    global client_socket
    update_last_ping()
    logger.info('Pinging master server')
    data = b'{"t":"e","event":"ping"}'
    client_socket.sendto(data,event.address)

def register(dispatcher,event):
    '''
    event = {'t':'e',
            'event':'register',
            'address':(127.0.0.1,1234),
            'callback':socket}
    '''
    global WORKER_NAME

    dispatcher.clear_queue()
    logger.info('Registering worker')
    END_JOB = False
    calculation_result = [None,0,0,0,None]
    message = {'t':'e',
            'event':'register',
            'name':WORKER_NAME}
    data = json.dumps(message).encode('ascii')
    event.callback.sendto(data,event.address)
    get_job()

def start_job(dispatcher,event):
    '''
    event = {'t':'e',
             'event':'start_job',
             'lastBlockHash':JOB[0],
             'expectedHash':JOB[1],
             'start':JOB_START,
             'end':JOB_END,
             'algorithm':algorithm,
             'address':(),
             'callback':socket}
    '''
    global calculation_thread
    global END_JOB
    global calculation_result
    global EXPECTED_HASH
    global START_END

    logger.info('Starting job')

    arguments = (event.lastBlockHash,
                 event.expectedHash,
                 event.start,
                 event.end)
    func = None
    if event.algorithm == 'XXHASH':
        logger.info('Using XXHASH algorithm')
        func = ducos1xxh
    elif event.algorithm == 'DUCO-S1':
        logger.info('Using DUCO-S1 algorithm')
        func = ducos1
    else:
        logger.warning('Algorithm not implemented')
        logger.debug(str(event.algorithm))
        return

    END_JOB = True

    #yield

    try:
        calculation_thread.join()
    except:
        pass

    EXPECTED_HASH = event.expectedHash
    START_END = (event.start,event.end)

    if func == None:
        return None

    END_JOB = False
    calculation_result = [None,0,0,0,None]

    calculation_thread = threading.Thread(target=func,args=arguments,name='calculation thread')
    calculation_thread.start()

    data = json.dumps({'t':'a',
                        'status':'ok',
                        'message':'Job accepted'})
    event.callback.sendto(data.encode('ascii'),event.address)
    update_last_ping()

def stop_job(dispatcher,event):
    '''
    event = {'t':'e',
            'event':'stop_job',
            'expected_hash':JOB[1],
            'start_end':event.start_end,
            'message':'another device already solved hash'}
    '''
    global END_JOB
    global calculation_result
    global calculation_thread
    global EXPECTED_HASH
    global START_END
    global JOB_WAS_TERMINATED

    if EXPECTED_HASH != event.expected_hash\
        or event.start_end[0] != START_END[0]\
        or event.start_end[1] != START_END[1]:
        logger.warning('Trying to stop wrong job')
        return

    JOB_WAS_TERMINATED = True
    
    logger.info('Terminating job')

    END_JOB = True

    try:
        calculation_thread.join()
    except:
        pass
    END_JOB = False

    #calculation_result = [None,0,0,0]
    #calculation_thread = None

    data = json.dumps({'t':'a',
                        'status':'ok',
                        'message':'Job terminated'})
    event.callback.sendto(data.encode('ascii'),event.address)
    update_last_ping()


def send_result():
    global calculation_result
    global calculation_thread
    global END_JOB
    global client_socket
    global CLUSTER_SERVER_ADDRESS
    global JOB_WAS_TERMINATED


    logger.info('Sending result')
    logger.debug(str(calculation_result))

    data = json.dumps({'t':'e',
                        'event':'job_done',
                        'result':calculation_result[:2],
                        'start_end':calculation_result[2:4],
                        'expected_hash':calculation_result[4]})

    client_socket.sendto(data.encode('ascii'),CLUSTER_SERVER_ADDRESS)

    calculation_result = [None,0,0,0,None]
    calculation_thread = None
    END_JOB = False
    

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




def client():
    global client_socket
    global END_JOB
    global calculation_thread
    global JOB_WAS_TERMINATED

    logger.debug('Initializing dispatcher')
    event_dispatcher = Dispatcher()
    event_dispatcher.register('register',register)
    event_dispatcher.register('stop_job',stop_job)
    event_dispatcher.register('start_job',start_job)
    event_dispatcher.register('ping',ping)
    logger.debug('Dispatcher initialized')


    END_JOB = True

    while True:
        data = None
        try:
            data, address = client_socket.recvfrom(1024)
        except:
            pass
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
                    message['callback'] = client_socket
                    event = Event(message)
                    event_dispatcher.add_to_queue(event)
                else:
                    pass
        
        try:
            event_dispatcher.dispatch_event()
        except Exception as e:
            logger.error('CANT DISPATCH EVENT')
            logger.debug('Traceback',exc_info=e)

        try:
            event_dispatcher.iter_through_active_list()
        except Exception as e:
            logger.error('CANT EXECUTE')
            logger.debug('Traceback',exc_info=e)
                    
        if to_ping():
            event = Event({'t':'e',
                           'event':'ping',
                           'address':CLUSTER_SERVER_ADDRESS})
            event_dispatcher.add_to_queue(event)


        if END_JOB:
            if calculation_result[4] != None:
                send_result()
                get_job()



        time.sleep(0.5)




if __name__ == '__main__':
    try:
        client()
    except Exception as e:
        #tr = traceback.format_exc()
        logger.warning('ERROR ACCURED',exc_info=e)

    input()