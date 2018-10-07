from pypresence import Presence, Activity
import time
import psutil


client_id = '64567352374564'  # Fake ID, put your real one here

RPC = Presence(client_id)  # Initialize the client class
RPC.connect() # Start the handshake loop
ac = Activity(RPC)

ac.start = int(time.time())

while True:  # The presence will stay on as long as the program is running
    cpu_per = round(psutil.cpu_percent(),1) # Get CPU Usage
    mem_per = round(psutil.virtual_memory().percent,1) #Get Mem Usage

    ac.details = "RAM: {}%".format(mem_per) # Setting attrs of an activity will auto update the presence
    ac.state = "CPU: {}%".format(cpu_per)

    time.sleep(15) # Can only update rich presence every 15 seconds
