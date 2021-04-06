import hashlib
import xxhash
import socket
import threading
import time
import struct

CLUSTER_SERVER_ADDRESS = ('127.0.0.1',9090)
client_socket = socket.socket()

print('CONNECTING TO MASTER SERVER',CLUSTER_SERVER_ADDRESS)
client_socket.connect(CLUSTER_SERVER_ADDRESS)
client_socket.send(b'TEST')

END_JOB = False

working_with_server = threading.Lock()

calculation_result = None

def ducos1xxh(
        lastBlockHash,
        expectedHash,
        start,
        end):
    global END_JOB,calculation_result

    hashcount = 0
    # Loop from 1 too 100*diff
    real_difficulty = end
    parts = 2
    step = (real_difficulty-start)//parts#difficulty
    left_offset = start
    right_offset = real_difficulty + 1
    while not END_JOB and left_offset < end:
    #for ducos1res in range(100 * int(difficulty) + 1):
        for ducos1xxres in range(left_offset,left_offset+step+1):
            if END_JOB:
                print('JOB TERMINATED')
                calculation_result = None
                return None
            ducos1xx = xxhash.xxh64(
            str(lastBlockHash) + str(ducos1xxres), seed=2811)
            ducos1xx = ducos1xx.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1xx == expectedHash:
                END_JOB = True
                print()
                print('LEFT',ducos1xxres)
                print()
                calculation_result = [ducos1xxres, hashcount]
                return None

        for ducos1xxres in range(right_offset,right_offset-step-1,-1):
            if END_JOB:
                print('JOB TERMINATED')
                calculation_result = None
                return None
            # Generate hash
            ducos1xx = xxhash.xxh64(
            str(lastBlockHash) + str(ducos1xxres), seed=2811)
            ducos1xx = ducos1xx.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1xx == expectedHash:
                END_JOB = True
                print()
                print('RIGHT',ducos1xxres)
                print()
                calculation_result = [ducos1xxres, hashcount]
                return None

        left_offset += step
        right_offset -= step
    END_JOB = True
    calculation_result = None
        

def receive_new_job():
    global END_JOB
    global calculation_result
    client_socket.settimeout(0)

    while True:    
        data_bytes = None
        try:
            data_bytes = client_socket.recv(1024)
        except:
            pass

        if data_bytes != None:
            data = data_bytes.decode('ascii')
            job = data.split(',')

            calculating_thread = None
            if job[0] == 'XXHASH':
                print('RECIEVED JOB:',job)
                END_JOB = False
                calculating_thread = threading.Thread(target=ducos1xxh,
                                                      args=(job[1],
                                                            job[2],
                                                            int(job[3]),
                                                            int(job[4])))
                calculating_thread.start()
            elif job[0] == 'END':
                END_JOB = True
                print('GOT AN END PACKET!')
                try:
                    client_socket.send(struct.pack('B',1))
                except:
                    raise Exception('Cant send response to an END packet')
                continue
            else:
                print('NOT IMPLEMENTED',job)
                continue


        result = calculation_result
        if result != None:
            print('CALCULATED RESULT:',result)
            data = str(result[0])+','+str(result[1])
            data_bytes = bytes(data,'ascii')
            data_bytes = client_socket.send(data_bytes)
            calculation_result = None



        



if __name__ == '__main__':
    receive_new_job()

