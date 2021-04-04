#!/usr/bin/env python3
##########################################
# Duino-Coin Python PC Miner (v2.4)
# https://github.com/revoxhere/duino-coin
# Distributed under MIT license
# © Duino-Coin Community 2019-2021
##########################################
# Import libraries
import socket
import threading
import time
import hashlib
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
from signal import signal, SIGINT
import random

# Install pip package automatically
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    os.execl(sys.executable, sys.executable, *sys.argv)

# Return datetime object
def now():
    return datetime.datetime.now()


# Check if cpuinfo is installed
try:
    import cpuinfo
except:
    print(
        now().strftime("%H:%M:%S ")
        + 'Cpuinfo is not installed. '
        + 'Miner will try to install it. '
        + 'If it fails, please manually install "py-cpuinfo" python3 package.'
        + '\nIf you can\'t install it, use the Minimal-PC_Miner.')
    install("py-cpuinfo")

# Check if colorama is installed
try:
    from colorama import init, Fore, Back, Style
except:
    print(
        now().strftime("%H:%M:%S ")
        + 'Colorama is not installed. '
        + 'Miner will try to install it. '
        + 'If it fails, please manually install "colorama" python3 package.'
        + '\nIf you can\'t install it, use the Minimal-PC_Miner.')
    install("colorama")

# Check if requests is installed
try:
    import requests
except:
    print(
        now().strftime("%H:%M:%S ")
        + 'Requests is not installed. '
        + 'Miner will try to install it. '
        + 'If it fails, please manually install "requests" python3 package.'
        + '\nIf you can\'t install it, use the Minimal-PC_Miner.')
    install("requests")

# Check if pypresence is installed
try:
    from pypresence import Presence
except:
    print(
        now().strftime("%H:%M:%S ")
        + 'Pypresence is not installed. '
        + 'Miner will try to install it. '
        + 'If it fails, please manually install "pypresence" python3 package.'
        + '\nIf you can\'t install it, use the Minimal-PC_Miner.')
    install("pypresence")

# Check if xxhash is installed
try:
    import xxhash
    xxhash_enabled = True
except:
    print(
        now().strftime("%H:%M:%S ")
        + 'Xxhash is not installed. '
        + 'Continuing without xxhash support.')
    xxhash_enabled = False


# Global variables
minerVersion = "2.4"  # Version number
timeout = 15  # Socket timeout
resourcesFolder = "PCMiner_" + str(minerVersion) + "_resources"
hash_mean = []
donatorrunning = False
debug = "n"
rigIdentifier = "None"
requestedDiff = "NET"
algorithm = "DUCO-S1"
serveripfile = ("https://raw.githubusercontent.com/"
    + "revoxhere/"
    + "duino-coin/gh-pages/"
    + "serverip.txt")  # Serverip file
config = configparser.ConfigParser()
donationlevel = 0
thread = []

# Create resources folder if it doesn't exist
if not os.path.exists(resourcesFolder):
    os.mkdir(resourcesFolder)

# Check if languages file exists
if not Path(resourcesFolder + "/langs.json").is_file():
    url = ("https://raw.githubusercontent.com/"
    + "revoxhere/"
    + "duino-coin/master/Resources/"
    + "PC_Miner_langs.json")
    r = requests.get(url)
    with open(resourcesFolder + "/langs.json", "wb") as f:
        f.write(r.content)

# Load language file
with open(f"{resourcesFolder}/langs.json", "r", encoding="utf8") as lang_file:
    lang_file = json.load(lang_file)

# OS X invalid locale hack
if platform.system() == 'Darwin':
    if locale.getlocale()[0] is None:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Check if miner is configured, if it isn't, autodetect language
if not Path(resourcesFolder + "/Miner_config.cfg").is_file():
    locale = locale.getdefaultlocale()[0]
    if locale.startswith("es"):
        lang = "spanish"
    elif locale.startswith("pl"):
        lang = "polish"
    elif locale.startswith("fr"):
        lang = "french"
    elif locale.startswith("ru"):
        lang = "russian"
    elif locale.startswith("de"):
        lang = "german"
    else:
        lang = "english"
else:
    # Read language variable from configfile
    try:
        config.read(resourcesFolder + "/Miner_config.cfg")
        lang = config["miner"]["language"]
    except:
        # If it fails, fallback to english
        lang = "english"

# Get string form language file
def getString(string_name):
    if string_name in lang_file[lang]:
        return lang_file[lang][string_name]
    elif string_name in lang_file["english"]:
        return lang_file["english"][string_name]
    else:
        return "String not found: " + string_name

# Debug output
def debugOutput(text):
    if debug == "y":
        print(now().strftime(Style.DIM + "%H:%M:%S.%f ") + "DEBUG: " + text)

# Set window title
def title(title):
    if os.name == "nt":
        os.system("title " + title)
    else:
        print("\33]0;" + title + "\a", end="")
        sys.stdout.flush()

# SIGINT handler
def handler(signal_received, frame):
    if multiprocessing.current_process().name == 'MainProcess':
        print(
            "\n"
            + now().strftime(Style.RESET_ALL + Style.DIM + "%H:%M:%S ")
            + Style.BRIGHT
            + Back.GREEN
            + Fore.WHITE
            + " sys0 "
            + Back.RESET
            + Fore.YELLOW
            + getString("sigint_detected")
            + Style.NORMAL
            + Fore.WHITE
            + getString("goodbye"))
        try:
            soc.close()
        except:
            pass
        os._exit(0)
    else:
        os._exit(0)


# Enable signal handler
signal(SIGINT, handler)


# Greeting message
def Greeting():
    global greeting
    print(Style.RESET_ALL)

    if requestedDiff == "LOW":
        diffName = getString("low_diff_short")
    elif requestedDiff == "MEDIUM":
        diffName = getString("medium_diff_short")
    else:
        diffName = getString("net_diff_short")

    current_hour = time.strptime(time.ctime(time.time())).tm_hour
    if current_hour < 12:
        greeting = getString("greeting_morning")
    elif current_hour == 12:
        greeting = getString("greeting_noon")
    elif current_hour > 12 and current_hour < 18:
        greeting = getString("greeting_afternoon")
    elif current_hour >= 18:
        greeting = getString("greeting_evening")
    else:
        greeting = getString("greeting_back")

    print(
        Style.RESET_ALL
        + " ‖ "
        + Fore.YELLOW
        + Style.BRIGHT
        + getString("banner")
        + Style.RESET_ALL
        + Fore.WHITE
        + " (v"
        + str(minerVersion)
        + ") 2019-2021")
    print(
        Style.RESET_ALL
        + " ‖ "
        + Fore.YELLOW
        + "https://github.com/revoxhere/duino-coin")
    try:
        print(
            Style.RESET_ALL
            + " ‖ "
            + Fore.WHITE
            + "CPU: "
            + Style.BRIGHT
            + Fore.YELLOW
            + str(threadcount)
            + "x "
            + str(cpu["brand_raw"]))
    except:
        if debug == "y":
            raise
    if os.name == "nt" or os.name == "posix":
        print(
            Style.RESET_ALL
            + " ‖ "
            + Fore.WHITE
            + getString("donation_level")
            + Style.BRIGHT
            + Fore.YELLOW
            + str(donationlevel))
    print(
        Style.RESET_ALL
        + " ‖ "
        + Fore.WHITE
        + getString("algorithm")
        + Style.BRIGHT
        + Fore.YELLOW
        + algorithm
        + " @ "
        + diffName)
    print(
        Style.RESET_ALL
        + " ‖ "
        + Fore.WHITE
        + getString("rig_identifier")
        + Style.BRIGHT
        + Fore.YELLOW
        + rigIdentifier)
    print(
        Style.RESET_ALL
        + " ‖ "
        + Fore.WHITE
        + str(greeting)
        + ", "
        + Style.BRIGHT
        + Fore.YELLOW
        + str(username)
        + "!\n")


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

    # Initial configuration
    if not Path(resourcesFolder + "/Miner_config.cfg").is_file():
        print(
            Style.BRIGHT
            + getString("basic_config_tool")
            + resourcesFolder
            + getString("edit_config_file_warning"))
        print(
            Style.RESET_ALL
            + getString("dont_have_account")
            + Fore.YELLOW
            + getString("wallet")
            + Fore.WHITE
            + getString("register_warning"))

        username = input(
            Style.RESET_ALL
            + Fore.YELLOW
            + getString("ask_username")
            + Fore.WHITE
            + Style.BRIGHT)

        if xxhash_enabled:
            print(
                Style.RESET_ALL
                + Style.BRIGHT
                + Fore.WHITE
                + "1"
                + Style.NORMAL
                + " - DUCO-S1")
            print(
                Style.RESET_ALL
                + Style.BRIGHT
                + Fore.WHITE
                + "2"
                + Style.NORMAL
                + " - XXHASH")
            algorithm = input(
                Style.RESET_ALL
                + Fore.YELLOW
                + getString("ask_algorithm")
                + Fore.WHITE
                + Style.BRIGHT)
        else:
            algorithm = "1"

        efficiency = input(
            Style.RESET_ALL
            + Fore.YELLOW
            + getString("ask_intensity")
            + Fore.WHITE
            + Style.BRIGHT)

        threadcount = input(
            Style.RESET_ALL
            + Fore.YELLOW
            + getString("ask_threads")
            + str(multiprocessing.cpu_count())
            + "): "
            + Fore.WHITE
            + Style.BRIGHT)

        print(
            Style.RESET_ALL
            + Style.BRIGHT
            + Fore.WHITE
            + "1"
            + Style.NORMAL
            + " - "
            + getString("low_diff"))
        print(
            Style.RESET_ALL
            + Style.BRIGHT
            + Fore.WHITE
            + "2"
            + Style.NORMAL
            + " - "
            + getString("medium_diff"))
        print(
            Style.RESET_ALL
            + Style.BRIGHT
            + Fore.WHITE
            + "3"
            + Style.NORMAL
            + " - "
            + getString("net_diff"))

        requestedDiff = input(
            Style.RESET_ALL
            + Fore.YELLOW
            + getString("ask_difficulty")
            + Fore.WHITE
            + Style.BRIGHT)

        rigIdentifier = input(
            Style.RESET_ALL
            + Fore.YELLOW
            + getString("ask_rig_identifier")
            + Fore.WHITE
            + Style.BRIGHT)

        if rigIdentifier == "y" or rigIdentifier == "Y":
            rigIdentifier = input(
                Style.RESET_ALL
                + Fore.YELLOW
                + getString("ask_rig_name")
                + Fore.WHITE
                + Style.BRIGHT)
        else:
            rigIdentifier = "None"

        donationlevel = "0"
        if os.name == "nt" or os.name == "posix":
            donationlevel = input(
                Style.RESET_ALL
                + Fore.YELLOW
                + getString("ask_donation_level")
                + Fore.WHITE
                + Style.BRIGHT)

        # Check wheter efficiency is correct
        efficiency = re.sub("\D", "", efficiency)
        if efficiency == '':
            efficiency = 95
        elif float(efficiency) > int(100):
            efficiency = 100
        elif float(efficiency) < int(1):
            efficiency = 1

        # Check wheter threadcount is correct
        threadcount = re.sub("\D", "", threadcount)
        if threadcount == '':
            threadcount = multiprocessing.cpu_count()
        elif int(threadcount) > int(10):
            threadcount = 10
        elif int(threadcount) < int(1):
            threadcount = 1

        # Check wheter algo setting is correct
        if algorithm == "2":
            algorithm = "XXHASH"
        else:
            algorithm = "DUCO-S1"

        # Check wheter diff setting is correct
        if requestedDiff == "1":
            requestedDiff = "LOW"
        elif requestedDiff == "2":
            requestedDiff = "MEDIUM"
        else:
            requestedDiff = "NET"

        # Check wheter donationlevel is correct
        donationlevel = re.sub("\D", "", donationlevel)
        if donationlevel == '':
            donationlevel = 1
        elif float(donationlevel) > int(5):
            donationlevel = 5
        elif float(donationlevel) < int(0):
            donationlevel = 0

        # Format data
        config["miner"] = {
            "username": username,
            "efficiency": efficiency,
            "threads": threadcount,
            "requestedDiff": requestedDiff,
            "donate": donationlevel,
            "identifier": rigIdentifier,
            "algorithm": algorithm,
            "language": lang,
            "debug": "n"}
        # Write data to configfile
        with open(resourcesFolder + "/Miner_config.cfg", "w") as configfile:
            config.write(configfile)

        # Calulate efficiency for use with sleep function
        efficiency = (100 - float(efficiency)) * 0.01

        print(Style.RESET_ALL + getString("config_saved"))

    # If config already exists, load data from it
    else:
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


# DUCO-S1 algorithm
def ducos1(
        lastBlockHash,
        expectedHash,
        difficulty):
    hashcount = 0
    # Loop from 1 too 100*diff
    real_difficulty = (100 * int(difficulty))
    parts = 200
    step = real_difficulty//parts
    left_offset = 0
    right_offset = real_difficulty + 1
    while True:
    #for ducos1res in range(100 * int(difficulty) + 1):
        for ducos1res in range(left_offset,left_offset+step+1):
            # Generate hash
            ducos1 = hashlib.sha1(
                str(lastBlockHash + str(ducos1res)).encode("utf-8"))
            ducos1 = ducos1.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1 == expectedHash:
                return [ducos1res, hashcount]

        for ducos1res in range(right_offset,right_offset-step-1,-1):
            # Generate hash
            ducos1 = hashlib.sha1(
                str(lastBlockHash + str(ducos1res)).encode("utf-8"))
            ducos1 = ducos1.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1 == expectedHash:
                return [ducos1res, hashcount]
        left_offset += step
        right_offset -= step


def ducos1xxh(
        lastBlockHash,
        expectedHash,
        difficulty):
    hashcount = 0
    # Loop from 1 too 100*diff
    real_difficulty = (100 * int(difficulty))
    parts = 100
    step = real_difficulty//parts
    left_offset = difficulty
    right_offset = real_difficulty + 1
    while True:
    #for ducos1res in range(100 * int(difficulty) + 1):
        for ducos1xxres in range(left_offset,left_offset+step+1):
            ducos1xx = xxhash.xxh64(
            str(lastBlockHash) + str(ducos1xxres), seed=2811)
            ducos1xx = ducos1xx.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1xx == expectedHash:
                print()
                print('LEFT',ducos1xxres)
                print()
                return [ducos1xxres, hashcount]

        for ducos1xxres in range(right_offset,right_offset-step-1,-1):
            # Generate hash
            ducos1xx = xxhash.xxh64(
            str(lastBlockHash) + str(ducos1xxres), seed=2811)
            ducos1xx = ducos1xx.hexdigest()
            # Increment hash counter for hashrate calculator
            hashcount += 1
            # Check if result was found
            if ducos1xx == expectedHash:
                print()
                print('RIGHT',ducos1xxres)
                print()
                return [ducos1xxres, hashcount]
        left_offset += step
        right_offset -= step
        
    for ducos1xxres in range(difficulty,-1,-1):
        
        ducos1xx = xxhash.xxh64(
        str(lastBlockHash) + str(ducos1xxres), seed=2811)
        ducos1xx = ducos1xx.hexdigest()
        # Increment hash counter for hashrate calculator
        hashcount += 1
        # Check if result was found
        if ducos1xx == expectedHash:
            print()
            print('FAR LEFT',ducos1xxres)
            print()
            return [ducos1xxres, hashcount]


# Mining section for every thread
def Thread(
        threadid,
        hashcount,
        accepted,
        rejected,
        requestedDiff,
        khashcount,
        username,
        efficiency,
        rigIdentifier,
        algorithm):
    while True:
        # Grab server IP and port
        while True:
            try:
                # Use request to grab data from raw github file
                res = requests.get(serveripfile, data=None)
                if res.status_code == 200:
                    # Read content and split into lines
                    content = (res.content.decode().splitlines())
                    masterServer_address = content[0]  # Line 1 = pool address
                    masterServer_port = content[1]  # Line 2 = pool port
                    debugOutput(
                        "Retrieved pool IP: "
                        + masterServer_address
                        + ":"
                        + str(masterServer_port))
                    break
            except:  # If there was an error with grabbing data from GitHub
                print(
                    now().strftime(Style.RESET_ALL + Style.DIM + "%H:%M:%S ")
                    + Style.BRIGHT
                    + Back.BLUE
                    + Fore.WHITE
                    + " net"
                    + str(threadid)
                    + " "
                    + Back.RESET
                    + Fore.RED
                    + getString("data_error"))
                if debug == "y":
                    raise
                time.sleep(10)

        # Connect to the server
        while True:
            try:
                soc = socket.socket()
                # Establish socket connection to the server
                soc.connect((str(masterServer_address),
                             int(masterServer_port)))
                serverVersion = soc.recv(3).decode().rstrip("\n")  # Get server version
                debugOutput("Server version: " + serverVersion)
                if (float(serverVersion) <= float(minerVersion)
                        and len(serverVersion) == 3):
                    # If miner is up-to-date, display a message and continue
                    print(
                        now().strftime(
                            Style.RESET_ALL
                            + Style.DIM
                            + "%H:%M:%S ")
                        + Style.BRIGHT
                        + Back.BLUE
                        + Fore.WHITE
                        + " net"
                        + str(threadid)
                        + " "
                        + Back.RESET
                        + Fore.YELLOW
                        + getString("connected")
                        + Style.RESET_ALL
                        + Fore.WHITE
                        + getString("connected_server")
                        + str(serverVersion)
                        + ")")
                    break

                else:
                    # Miner is outdated
                    print(
                        now().strftime(
                            Style.RESET_ALL
                            + Style.DIM
                            + "%H:%M:%S ")
                        + Style.BRIGHT
                        + Back.GREEN
                        + Fore.WHITE
                        + " sys"
                        + str(threadid)
                        + " "
                        + Back.RESET
                        + Fore.RED
                        + getString("outdated_miner")
                        + minerVersion
                        + "),"
                        + Style.RESET_ALL
                        + Fore.RED
                        + getString("server_is_on_version")
                        + serverVersion
                        + getString("update_warning"))
                    break
            except:
                # Socket connection error
                print(
                    now().strftime(Style.DIM + "%H:%M:%S ")
                    + Style.RESET_ALL
                    + Style.BRIGHT
                    + Back.BLUE
                    + Fore.WHITE
                    + " net"
                    + str(threadid)
                    + " "
                    + Style.RESET_ALL
                    + Style.BRIGHT
                    + Fore.RED
                    + getString("connecting_error")
                    + Style.RESET_ALL)
                if debug == "y":
                    raise
                time.sleep(5)

        if algorithm == "XXHASH":
            using_algo = getString("using_algo_xxh")
        else:
            using_algo = getString("using_algo")
        print(
            # Message about mining thread starting
            now().strftime(Style.DIM + "%H:%M:%S ")
            + Style.RESET_ALL
            + Style.BRIGHT
            + Back.GREEN
            + Fore.WHITE
            + " sys"
            + str(threadid)
            + " "
            + Back.RESET
            + Fore.YELLOW
            + getString("mining_thread")
            + str(threadid)
            + getString("mining_thread_starting")
            + Style.RESET_ALL
            + Fore.WHITE
            + using_algo
            + Fore.YELLOW
            + str(int(100 - efficiency * 100))
            + f"% {getString('efficiency')}")

        # Mining section
        while True:
            try:
                # If efficiency lower than 100...
                if float(100 - efficiency * 100) < 100:
                    # ...sleep some time
                    time.sleep(float(efficiency * 5))
                while True:
                    # Ask the server for job
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

                    job = soc.recv(128).decode().rstrip("\n")
                    job = job.split(",")  # Get work from pool
                    debugOutput("Received: " + str(job))

                    if job[1] == "This user doesn't exist":
                        print(
                            now().strftime(
                                Style.RESET_ALL
                                + Style.DIM
                                + "%H:%M:%S ")
                            + Style.RESET_ALL
                            + Style.BRIGHT
                            + Back.BLUE
                            + Fore.WHITE
                            + " cpu"
                            + str(threadid)
                            + " "
                            + Back.RESET
                            + Fore.RED
                            + getString("mining_user")
                            + Fore.WHITE
                            + str(username)
                            + Fore.RED
                            + getString("mining_not_exist")
                            + getString("mining_not_exist_warning"))
                        time.sleep(10)

                    elif job[0] and job[1] and job[2]:
                        diff = int(job[2])
                        debugOutput(str(threadid) +
                                    "Job received: " 
                                    + str(job))
                        # If job received, continue to hashing algo
                        break

                while True:
                    # Call DUCOS-1 hasher
                    computetimeStart = time.time()
                    if algorithm == "XXHASH":
                        algo_back_color = Back.CYAN
                        result = ducos1xxh(job[0], job[1], diff)
                    else:
                        algo_back_color = Back.YELLOW
                        result = ducos1(job[0], job[1], diff)
                    computetimeStop = time.time()
                    # Measure compute time
                    computetime = computetimeStop - computetimeStart
                    # Convert it to miliseconds
                    computetime = computetime
                    # Read result from ducos1 hasher
                    ducos1res = result[0]
                    debugOutput("Thread "
                                + str(threadid)
                                + ": result found: "
                                + str(ducos1res))

                    threadhashcount = result[1]
                    # Add this thread's hash counter
                    # to the global hashrate counter
                    hashcount += threadhashcount

                    while True:
                        # Send result of hashing algorithm to the server
                        soc.send(bytes(
                            str(ducos1res)
                            + ","
                            + str(threadhashcount)
                            + ","
                            + "Official PC Miner ("
                            + str(algorithm)
                            + ") v" 
                            + str(minerVersion)
                            + ","
                            + str(rigIdentifier),
                            encoding="utf8"))

                        responsetimetart = now()
                        # Get feedback
                        feedback = soc.recv(8).decode().rstrip("\n")
                        responsetimestop = now()
                        # Measure server ping
                        ping = str(int(
                            (responsetimestop - responsetimetart).microseconds
                            / 1000))
                        debugOutput("Thread "
                                    + str(threadid)
                                    + ": Feedback received: "
                                    + str(feedback)
                                    + " Ping: "
                                    + str(ping))

                        if khashcount > 800:
                            # Format hashcount to MH/s
                            formattedhashcount = str(
                                f"%01.2f" % round(khashcount / 1000, 2)
                                + " MH/s")
                        else:
                            # Stay with kH/s
                            formattedhashcount = str(
                                f"%03.0f" % float(khashcount)
                                + " kH/s")

                        if feedback == "GOOD":
                            # If result was correct
                            accepted += 1
                            title(
                                getString("duco_python_miner")
                                + str(minerVersion)
                                + ") - "
                                + str(accepted)
                                + "/"
                                + str(accepted + rejected)
                                + getString("accepted_shares"))
                            print(
                                now().strftime(
                                    Style.RESET_ALL
                                    + Style.DIM
                                    + "%H:%M:%S ")
                                + Style.BRIGHT
                                + algo_back_color
                                + Fore.WHITE
                                + " cpu"
                                + str(threadid)
                                + " "
                                + Back.RESET
                                + Fore.GREEN
                                + " ✓"
                                + getString("accepted")
                                + Fore.WHITE
                                + str(int(accepted))
                                + "/"
                                + str(int(accepted + rejected))
                                + Back.RESET
                                + Fore.YELLOW
                                + " ("
                                + str(int(
                                    (accepted
                                        / (accepted + rejected)
                                     * 100)))
                                + "%)"
                                + Style.NORMAL
                                + Fore.WHITE
                                + " ∙ "
                                + str(f"%01.3f" % float(computetime))
                                + "s"
                                + Style.NORMAL
                                + " ∙ "
                                + Fore.BLUE
                                + Style.BRIGHT
                                + str(formattedhashcount)
                                + Fore.WHITE
                                + Style.NORMAL
                                + " @ diff "
                                + str(diff)
                                + " ∙ "
                                + Fore.CYAN
                                + "ping "
                                + str(f"%02.0f" % int(ping))
                                + "ms")
                            break  # Repeat

                        elif feedback == "BLOCK":
                            # If block was found
                            accepted += 1
                            title(
                                getString("duco_python_miner")
                                + str(minerVersion)
                                + ") - "
                                + str(accepted)
                                + "/"
                                + str(accepted + rejected)
                                + getString("accepted_shares"))
                            print(
                                now().strftime(
                                    Style.RESET_ALL
                                    + Style.DIM
                                    + "%H:%M:%S ")
                                + Style.BRIGHT
                                + algo_back_color
                                + Fore.WHITE
                                + " cpu"
                                + str(threadid)
                                + " "
                                + Back.RESET
                                + Fore.CYAN
                                + " ✓"
                                + getString("block_found")
                                + Fore.WHITE
                                + str(accepted)
                                + "/"
                                + str(accepted + rejected)
                                + Back.RESET
                                + Fore.YELLOW
                                + " ("
                                + str(int(
                                    (accepted
                                        / (accepted + rejected)
                                     * 100)))
                                + "%)"
                                + Style.NORMAL
                                + Fore.WHITE
                                + " ∙ "
                                + str(f"%01.3f" % float(computetime))
                                + "s"
                                + Style.NORMAL
                                + " ∙ "
                                + Fore.BLUE
                                + Style.BRIGHT
                                + str(formattedhashcount)
                                + Fore.WHITE
                                + Style.NORMAL
                                + " @ diff "
                                + str(diff)
                                + " ∙ "
                                + Fore.CYAN
                                + "ping "
                                + str(f"%02.0f" % int(ping))
                                + "ms")
                            break  # Repeat

                        else:
                            # If result was incorrect
                            rejected += 1
                            title(
                                getString("duco_python_miner")
                                + str(minerVersion)
                                + ") - "
                                + str(accepted)
                                + "/"
                                + str(accepted + rejected)
                                + getString("accepted_shares"))
                            print(
                                now().strftime(
                                    Style.RESET_ALL
                                    + Style.DIM
                                    + "%H:%M:%S ")
                                + Style.RESET_ALL
                                + algo_back_color
                                + Back.YELLOW
                                + Fore.WHITE
                                + " cpu"
                                + str(threadid)
                                + " "
                                + Back.RESET
                                + Fore.RED
                                + " ✗"
                                + getString("rejected")
                                + Fore.WHITE
                                + str(accepted)
                                + "/"
                                + str(accepted + rejected)
                                + Back.RESET
                                + Fore.YELLOW
                                + " ("
                                + str(int(
                                    (accepted
                                        / (accepted + rejected)
                                     * 100)))
                                + "%)"
                                + Style.NORMAL
                                + Fore.WHITE
                                + " ∙ "
                                + str(f"%01.3f" % float(computetime))
                                + "s"
                                + Style.NORMAL
                                + " ∙ "
                                + Fore.BLUE
                                + Style.BRIGHT
                                + str(formattedhashcount)
                                + Fore.WHITE
                                + Style.NORMAL
                                + " @ diff "
                                + str(diff)
                                + " ∙ "
                                + Fore.CYAN
                                + "ping "
                                + str(f"%02.0f" % int(ping))
                                + "ms")
                            break  # Repeat
                    break
            except:
                print(
                    now().strftime(Style.DIM + "%H:%M:%S ")
                    + Style.RESET_ALL
                    + Style.BRIGHT
                    + Back.BLUE
                    + Fore.WHITE
                    + " net"
                    + str(threadid)
                    + " "
                    + Style.RESET_ALL
                    + Style.BRIGHT
                    + Fore.MAGENTA
                    + getString("error_while_mining")
                    + Style.RESET_ALL
                )
                if debug == "y":
                    raise
                time.sleep(5)
                break


if __name__ == "__main__":


    cpu = cpuinfo.get_cpu_info()  # Processor info
    init(autoreset=True)  # Colorama
    title(getString("duco_python_miner") + str(minerVersion) + ")")
    # globals
    hashcount = 0
    khashcount = 0
    accepted = 0
    rejected = 0

    try:
        loadConfig()  # Load config file or create new one
        debugOutput("Config file loaded")
    except:
        print(
            now().strftime(Style.DIM + "%H:%M:%S ")
            + Style.RESET_ALL
            + Style.BRIGHT
            + Back.GREEN
            + Fore.WHITE
            + " sys0 "
            + Style.RESET_ALL
            + Style.BRIGHT
            + Fore.RED
            + getString("load_config_error")
            + resourcesFolder
            + getString("load_config_error_warning")
            + Style.RESET_ALL)
        if debug == "y":
            raise
        time.sleep(10)
        os._exit(1)
    try:
        Greeting()  # Display greeting message
        debugOutput("Greeting displayed")
    except:
        if debug == "y":
            raise


    Thread(1,
           hashcount,
           accepted,
           rejected,
           requestedDiff,
           khashcount,
           username,
           efficiency,
           rigIdentifier,
           algorithm)
    
