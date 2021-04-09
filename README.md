# DuinoCoin miner optimized for phones under OS android or any piece of junk that can run python

To start it you can use any python ide, I suggest pydroid 3 or you can also use termux

in folder PCMiner_2.4_resources in file Miner_config.cfg write your username from duinocoin site: "username = username"

and I will suggest you NOT to change anything else in that file.

File Android_Miner.py - is a miner for android, that file along can mine you some coins.(Just a port of official miner for PC with some optimization tweaks)

File cluster_server.py - is a server for your cluster, it must have folder "PCMiner_2.4_resources" next to it to parse info, it also must have file "Miner_config.cfg" inside, "langs.json" is not used by server(default port is 9090)

File Android_cluster.py - is a miner for cluster, don't forget to change server address and worker name right in the script. It doesn't need folder PCMiner_2.4_resources

before you start program download some python libraries:

  py-cpuinfo (only Android_Miner.py)

  colorama (only Android_Miner.py)

  requests
  
  pypresence (only Android_Miner.py)
  
  xxhash
  
