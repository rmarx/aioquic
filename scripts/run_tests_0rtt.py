import subprocess
import random
import string 

# need to run setup.py first to make sure all our changes are compiled before running
# if you didn't make changes to aioquic, you can comment this step out
# need to run this from inside the root dir
# so do python3 scripts/run_tests.py

directoryName = "aioquic_live"
logDirectoryName = "aioquic"

print("Compiling...")
process = subprocess.run("{}".format("python3 /srv/"+directoryName+"/setup.py install"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


if process.returncode is not 0:
    print ("ERROR in compilation: ", process.returncode, " != 0?")
    print ( process.stderr )

print("Compilation done!")

nozerorttendpoints = []

basecommand = "python3 /srv/"+directoryName+"/examples/http3_client_0rtt.py --insecure -v"

class Endpoint:
    def __init__(self, url, name):
        self.url = url
        self.name = name

runname = ""
ticketNumber = 0
storeTicket = False
readTicket = False

proper_endpoints = [
    Endpoint("https://quic.aiortc.org/{}", "aioquic"),
    # Endpoint("https://mew.org:4433/{}", "haskell"), # no HTTP/3
    # Endpoint("https://quicgo:4122/{}", "quicgo"), # local docker
    # Endpoint("https://neqo:4123/{}", "neqo"), # local docker
    Endpoint("https://test.privateoctopus.com:4433/{}", "picoquic"), 
    Endpoint("https://http3-test.litespeedtech.com:4433/{}", "lsquic"),
    Endpoint("https://nghttp2.org:4433/{}", "ngtcp2"),
    Endpoint("https://quic.examp1e.net/{}", "quicly"), # sometimes does 0-RTT correctly, sometimes doesn't... might take a few tries 
    Endpoint("https://h3.stammw.eu:4433/{}", "quinn"), # is proper, but bugs out when requesting many files at once... put it at the back of the runs manually to prevent it from holding up everything
    # Endpoint("https://fb.mvfst.net:443/{}", "mvfst"), # // this endpoint was not reachable from belgium when we did these tests. fbcdn is the same codebase though
    # Endpoint("https://quic.rocks:4433/{}", "google"), # doesn't seem to have 0-RTT support a this time
]

# f5          = "https://f5quic.com:4433"                 # only has 50000, 5000000, 10000000 (50KB, 5MB , 10MB) # no 0-RTT at this time
# msquic      = "https://quic.westus.cloudapp.azure.com"  # only has 5000000.txt, 10000000.txt, 1MBfile.txt, index.html (1MB, 5MB, 10MB, 1KB) # no 0-RTT at this time
quiche      = "https://quic.tech:8443"                  # only has 1MB.png, 5MB.png
# quiche_nginx = "https://cloudflare-quic.com"            # only has 1MB.png, 5MB.png  # no 0-RTT at this time, endpoint not updated
facebook    = "https://www.facebook.com"                # "rsrc.php/v3iXG34/y_/l/en_GB/ppT9gy-P_lf.js?_nc_x=Ij3Wp8lg5Kz"
fbcdn       = "https://scontent.xx.fbcdn.net"           # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB
fbcdn2      = "https://static.xx.fbcdn.net"             # /rsrc.php/v3/yl/r/tjt2pkny7ku.png?buster=$RANDOM$RANDOM
# fbcdn_india = "https://xx-fbcdn-shv-01-bom1.fbcdn.net"  # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB # same as normal fbcdn, not tested separately
# ats         = "https://quic.ogre.com:4433"              # en/latest/admin-guide/files/records.config.en.html # no 0-RTT at this time
# akamai      = "https://ietf.akaquic.com"                # /10k, /100k, /1M # based on google's implementation # can't deal with multiple requests at the same time  # no 0-RTT at this time
# gvideo      = "googlevideo.com"                          # no 0-RTT at this time

def run_single(size, amplification_factor, testname):

    for endpoint in proper_endpoints:
        url = endpoint.url.format(str(size))

        ticket = ""
        ticketFileName = ""
        if storeTicket:
            ticket = " --session-ticket-write /srv/" + directoryName + "/tickets/" + endpoint.name + str(ticketNumber) + ".ticket "
            ticketFileName = "1RTT_"
        elif readTicket:
            ticket = " --session-ticket-read /srv/" + directoryName + "/tickets/" + endpoint.name + str(ticketNumber) + ".ticket "
            ticketFileName = "0RTT_"


        cmd = basecommand + " " + ticket + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_"  + ticketFileName + endpoint.name + ".qlog " + "--amplification-factor " + str(amplification_factor) + " " + url
        print ("Executing ", cmd)
        run_command ( cmd )

def run_single_endpoint(url, amplification_factor, testname, endpointName):

    ticket = ""
    ticketFileName = ""
    if storeTicket:
        ticket = " --session-ticket-write /srv/" + directoryName + "/tickets/" + endpointName + str(ticketNumber) + ".ticket "
        ticketFileName = "1RTT_"
    elif readTicket:
        ticket = " --session-ticket-read /srv/" + directoryName + "/tickets/" + endpointName + str(ticketNumber) + ".ticket "
        ticketFileName = "0RTT_"

    cmd = basecommand + " " + ticket + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_" + ticketFileName + endpointName + ".qlog " + "--amplification-factor " + str(amplification_factor) + " \"" + url + "\""
    print ("Executing ", cmd)
    run_command ( cmd )

def run_command(cmd):
    process = subprocess.run("{}".format(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if ( len(process.stdout) > 0 ):
        if process.stdout.find("EARLY_DATA NOT ACCEPTED") >= 0:
            nozerorttendpoints.append( cmd )
        elif process.stdout.find("so not doing 0rtt") >= 0:
            nozerorttendpoints.append( cmd )

        print ( process.stdout )

    if len(process.stderr) is not 0 or process.returncode is not 0:
        if process.stderr.find("EARLY_DATA NOT ACCEPTED") >= 0:
            nozerorttendpoints.append( cmd )
        elif process.stderr.find("so not doing 0rtt") >= 0:
            nozerorttendpoints.append( cmd )

        # print ("Potential ERROR in process: ", process.returncode, " != 0?")
        print ( process.stderr )
        # print( "stderr length was %d", len(process.stderr) )

ticketNumber = 1 # so tickets don't get overridden if we want to prep all ampfactor tests at once
# set both to False for addressFixed mode (run 1rtt and 0rtt back-to-back)
# set first storeTicket = True, then readTicket = True for addressChange mode 
# (change network in between of course. We used a VPN, but you could also copy over the tickets)
storeTicket = False
readTicket = False

if storeTicket:
    runname = "1_storedWifiWrite"
elif readTicket:
    runname = "1_storedCableRead"
else:
    runname = "1"

# the run with 6k max_initial_data was done by manually changing the values in configuration.py and then running factor1 again 
# firstflightOnly was done by first running normally with storeTicket=True. 
# # Then manually changing srv/aioquic/quic/connection.py datagrams_to_send to not send anything after first flight,
# # also set firstFlightOnly to True in the http3_client_0rtt.py
# # then ran with readTicket=True
factor0 = False
factor1 = False
factor2 = False
factor10 = False

# run_single_endpoint( "https://h3.stammw.eu:4433/1000000",  0,  "1MB_ampfactor0", "quinn" )

# run_single_endpoint( "https://http3-test.litespeedtech.com:4433/1000000", 0, "1MB_ampfactor0", "lsquic" )
# run_single_endpoint( "https://nghttp2.org:4433/1000000", 0, "1MB_ampfactor0", "ngtcp2" )

# run_single_endpoint( facebook + "/",                2,  "1MB_ampfactor2", "facebook" )

run_single_endpoint( "https://quic.examp1e.net/1000000", 0, "1MB_ampfactor0", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 1, "1MB_ampfactor1", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 2, "1MB_ampfactor2", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 3, "1MB_ampfactor3", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 10, "1MB_ampfactor10", "quicly" )


# run_single_endpoint( "https://h3.stammw.eu:4433/1000000", 0, "1MB_ampfactor0", "quinn" )
# run_single_endpoint( "https://h3.stammw.eu:4433/1000000", 1, "1MB_ampfactor1", "quinn" )
# run_single_endpoint( "https://h3.stammw.eu:4433/1000000", 2, "1MB_ampfactor2", "quinn" )
# run_single_endpoint( "https://h3.stammw.eu:4433/1000000", 10, "1MB_ampfactor10", "quinn" )

# run_single_endpoint( "https://test.privateoctopus.com:4433/1000000", 0, "1MB_ampfactor0", "picoquic" )
# run_single_endpoint( "https://test.privateoctopus.com:4433/1000000", 1, "1MB_ampfactor1", "picoquic" )
# run_single_endpoint( "https://test.privateoctopus.com:4433/1000000", 2, "1MB_ampfactor2", "picoquic" )
# run_single_endpoint( "https://test.privateoctopus.com:4433/1000000", 10, "1MB_ampfactor10", "picoquic" )

# run_single_endpoint( quiche + "/1MB.png",           0,  "1MB_ampfactor0", "quiche" )
# run_single_endpoint( quiche + "/1MB.png",           1,  "1MB_ampfactor1", "quiche" )
# run_single_endpoint( quiche + "/1MB.png",           2,  "1MB_ampfactor2", "quiche" )
# run_single_endpoint( quiche + "/1MB.png",           10,  "1MB_ampfactor10", "quiche" )


# run_single_endpoint( facebook  + "/",     0,  "1MB_ampfactor0", "facebook" )

# run_single_endpoint( fbcdn  + "/speedtest-1MB",     0,  "1MB_ampfactor0", "fbcdn" )
# run_single_endpoint( fbcdn  + "/speedtest-1MB",     1,  "1MB_ampfactor1", "fbcdn" )
# run_single_endpoint( fbcdn  + "/speedtest-1MB",     2,  "1MB_ampfactor2", "fbcdn" )
# run_single_endpoint( fbcdn  + "/speedtest-1MB",     10,  "1MB_ampfactor10", "fbcdn" )

# run_single_endpoint( f5 +     "/50000",             0,  "500KB_ampfactor0", "f5" )
# run_single_endpoint( f5 +     "/50000",             1,  "500KB_ampfactor1", "f5" )
# run_single_endpoint( f5 +     "/50000",             2,  "500KB_ampfactor2", "f5" )
# run_single_endpoint( f5 +     "/50000",             10,  "500KB_ampfactor10", "f5" )

if factor0: 
    run_single(          1_000_000,                     0,  "1MB_ampfactor0" )
    run_single_endpoint( facebook + "/",                0,  "1MB_ampfactor0", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           0,  "1MB_ampfactor0", "quiche" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 0,  "1MB_ampfactor0", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     0,  "1MB_ampfactor0", "fbcdn" )
    # run_single_endpoint( quiche_nginx + "/1MB.png",     0,  "1MB_ampfactor0", "quicheNginx" ) # no 0.5RTT data actually sent at this time
    # run_single_endpoint( akamai + "/1M",                0,  "1MB_ampfactor0", "akamai" )
    # run_single_endpoint( ats + "/en/latest/admin-guide/files/records.config.en.html", 0,  "400KB_ampfactor0", "ats" )
    # run_single_endpoint( f5 +     "/50000",             0,  "500KB_ampfactor0", "f5" ) # doesn't work with stateless retry
    # run_single_endpoint( gvideourlmedium,               0,  "1MB_ampfactor0",   "googlevideo" )
    # run_single_endpoint( msquic  + "/1MBfile.txt",      0,  "1MB_ampfactor0", "msquic" )


if factor1: 
    run_single(          1_000_000,                     1,  "1MB_ampfactor1" )
    run_single_endpoint( facebook + "/",                1,  "1MB_ampfactor1", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           1,  "1MB_ampfactor1", "quiche" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 1,  "1MB_ampfactor1", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     1,  "1MB_ampfactor1", "fbcdn" )

if factor2: 
    run_single(          1_000_000,                     2,  "1MB_ampfactor2" )
    run_single_endpoint( facebook + "/",                2,  "1MB_ampfactor2", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           2,  "1MB_ampfactor2", "quiche" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 2,  "1MB_ampfactor2", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     2,  "1MB_ampfactor2", "fbcdn" )

if factor10: 
    run_single(          1_000_000,                     10,  "1MB_ampfactor10" )
    run_single_endpoint( facebook + "/",                10,  "1MB_ampfactor10", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           10,  "1MB_ampfactor10", "quiche" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 10,  "1MB_ampfactor10", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     10,  "1MB_ampfactor10", "fbcdn" )


if len(nozerorttendpoints) > 0:
    print("Some endpoints do not seem to support 0-RTT")
    print( nozerorttendpoints )