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

proper_endpoints = [
    Endpoint("https://quic.aiortc.org/{}", "aioquic"),
    # Endpoint("https://mew.org:4433/{}", "haskell"), # no HTTP/3
    # Endpoint("https://quicgo:4122/{}", "quicgo"), # local docker
    # Endpoint("https://neqo:4123/{}", "neqo"), # local docker
    # Endpoint("https://quic.seemann.io/{}", "quicgo"), # not online
    Endpoint("https://test.privateoctopus.com:4433/{}", "picoquic"), 
    Endpoint("https://http3-test.litespeedtech.com:4433/{}", "lsquic"),
    # Endpoint("https://fb.mvfst.net:443/{}", "mvfst"), # // this endpoint was not reachable when we did these tests
    Endpoint("https://nghttp2.org:4433/{}", "ngtcp2"),
    Endpoint("https://quic.examp1e.net/{}", "quicly"),
    Endpoint("https://quic.rocks:4433/{}", "google"),
    # Endpoint("https://h3.stammw.eu:4433/{}", "quinn"), # is proper, but bugs out when requesting many files at once... put it at the back of the runs manually to prevent it from holding up everything
]

f5          = "https://f5quic.com:4433"                 # only has 50000, 5000000, 10000000 (50KB, 5MB , 10MB)
msquic      = "https://quic.westus.cloudapp.azure.com"  # only has 5000000.txt, 10000000.txt, 1MBfile.txt, index.html (1MB, 5MB, 10MB, 1KB)
quiche      = "https://quic.tech:8443"                  # only has 1MB.png, 5MB.png
quiche_nginx = "https://cloudflare-quic.com"            # only has 1MB.png, 5MB.png
facebook    = "https://www.facebook.com"                # "rsrc.php/v3iXG34/y_/l/en_GB/ppT9gy-P_lf.js?_nc_x=Ij3Wp8lg5Kz"
fbcdn       = "https://scontent.xx.fbcdn.net"           # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB
fbcdn2      = "https://static.xx.fbcdn.net"             # /rsrc.php/v3/yl/r/tjt2pkny7ku.png?buster=$RANDOM$RANDOM
fbcdn_india = "https://xx-fbcdn-shv-01-bom1.fbcdn.net"  # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB
ats         = "https://quic.ogre.com:4433"              # en/latest/admin-guide/files/records.config.en.html
akamai      = "https://ietf.akaquic.com"                # /10k, /100k, /1M # based on google's implementation # can't deal with multiple requests at the same time
# quinn       = "https://h3.stammw.eu:4433"               # proper, any integer after / goes
gvideo      = "googlevideo.com"

def run_single(size, amplification_factor, testname):

    for endpoint in proper_endpoints:
        url = endpoint.url.format(str(size))
        cmd = basecommand + " " + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_" + endpoint.name + ".qlog " + "--amplification-factor " + str(amplification_factor) + " " + url
        print ("Executing ", cmd)
        run_command ( cmd )

def run_single_endpoint(url, amplification_factor, testname, endpointName):

    cmd = basecommand + " " + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_" + endpointName + ".qlog " + "--amplification-factor " + str(amplification_factor) + " \"" + url + "\""
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

runname = "1"

run0 = False
run1 = True
run2 = False

if run0: 
    # run_single( 1_000_000, 0, "1MB_ampfactor0" )
    # run_single_endpoint( facebook + "/", 0, "1MB_ampfactor0", "facebook" )
    # run_single_endpoint( msquic  + "/1MBfile.txt",  0,  "1MB_ampfactor0", "msquic" )
    # run_single_endpoint( quiche + "/1MB.png",       0,  "1MB_ampfactor0", "quiche" )
    # run_single_endpoint( quiche_nginx + "/1MB.png", 0,  "1MB_ampfactor0", "quicheNginx" )
    # run_single_endpoint( fbcdn  + "/speedtest-1MB", 0,  "1MB_ampfactor0", "fbcdn" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 0,  "1MB_ampfactor0", "fbcdnCachebuster" )
    # run_single_endpoint( akamai + "/1M",            0,  "1MB_ampfactor0", "akamai" )
    # run_single_endpoint( ats + "/en/latest/admin-guide/files/records.config.en.html", 0,  "400KB_ampfactor0", "ats" )

    # run_single_endpoint( f5 +     "/50000",       0,  "500KB_ampfactor0", "f5" )
    # run_single_endpoint( quinn + "/500000",        0,  "500KB_ampfactor0", "quinn" )


if run1: 
    # run_single( 1_000_000, 1, "1MB_ampfactor1" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?busterv2=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 1,  "1MB_ampfactor1", "fbcdnCachebuster" )

if run2: 
    run_single( 1_000_000, 2, "1MB_ampfactor2" )

# TODO: check the not_valid_before things in the session tickets for the ones that don't seem to work 
# TODO: add youtube


if len(nozerorttendpoints) > 0:
    print("Some endpoints do not seem to support 0-RTT")
    print( nozerorttendpoints )