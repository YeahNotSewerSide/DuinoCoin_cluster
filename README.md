# DuinoCoin miner optimized for phones under OS android or any piece of junk that can run python

To start it you can use any python ide, I suggest pydroid 3 or you can also use termux

in folder PCMiner_2.4_resources in file Miner_config.cfg write your username from duinocoin site: "username = username"

and I will suggest you NOT to change anything else in that file.

File Android_Miner.py - is a miner for android, that file along can mine you some coins.(Just a port of official miner for PC with some optimization tweaks)

File cluster_server.py - is a server for your cluster, it must have folder "PCMiner_2.4_resources" next to it to parse info, it also must have file "Miner_config.cfg" inside, "langs.json" is not used by server(default port is 9090)

File Android_cluster.py - is a miner for cluster, don't forget to change server address and worker name right in the script(WORKER_NAME and CLUSTER_SERVER_ADDRESS). It doesn't need folder PCMiner_2.4_resources

# Some questions:

How many devices can I connect? - As many as you want.

What devices can use that scripts? - Any devices that can run python.

Should devices be the same for mining? - No, I tested it and optimized to mine on devices with different speed efficiently.

Does it has tips for creator? - No, it mines only for your account, if you want to support me, buy me a coffee:                https://buymeacoffee.com/ENotSewerSide.

What happens if one devices shuts down and stops responding? - Nothing, server will send job of that device to other devices, and if device cant respond to server in 90 seconds, server will forget that device.

What if I connect new device to the server rigth in the middle of calculating hash? - server will send to that device some job, it depends on what jobs have been done and what are been processed right now.

What are those jobs that server sends to devices? - When server receives new job wrom Duino-coin master server, it divides it on different blocks(jobs), by default it will divide on the number of connected device, to change that you can change variable in the file "cluster_server.py" "INC_COEF", so jobs from master server will be divided by len(devices)+INC_COEF.

Will slow devices make cluster work slower? - No, actually they will make it work faster, so the speed depends on the number of devices connected, more=faster.

IS IT SAFE TO USE OVER THE INTERNET? - Not right now, it has some vulnerabilities, which I will fix later.

I don't have a lot of storage memmory on my phone, will Android_cluster.py store something? - Nope it wouldn't.

I want to change difficulty for cluster, what do I do? - "./PCMiner_2.4_resources/Miner_config.cfg" in that file change "requesteddiff" = NET|MEDIUM|LOW (NET is the hardest difficulty, at least that's what I have read in official PC miner)

Do I start server or workers first? - Doesn't matter.

When I connect my PC to cluster of phones produced in 2005 it seems, that only my PC calculating hashes. - That's because of the servers algorithm, it tries to keep cluster always busy with different jobs, so when phone and PC are calculatiing the same block, PC will calculate it faster and server will stop phone's job, so all devices are calculating something, but the fastest interupts slower devices, because there is no need to continue that job on slower devices.

How many devices will calculate the same block? - It depends, can be one, can be all devices in the same time, but that's ok.

# before you start program download some python libraries:

  py-cpuinfo (only Android_Miner.py)

  colorama (only Android_Miner.py)
  
  pypresence (only Android_Miner.py)
  
  requests
  
  xxhash
  
