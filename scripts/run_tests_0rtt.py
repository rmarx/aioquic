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
quiche_nginx = "https://cloudflare-quic.com"            # only has 1MB.png, 5MB.png
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

# the run with 3k max_initial_data was done by manually changing the values in configuration.py and then running run0 again 
factor0 = True
factor1 = False
factor2 = False
factor10 = False

gvideourlmedium = "https://r4---sn-uxaxoxu-cg0k.googlevideo.com/videoplayback?expire=1588274362&ei=WtCqXpnoE4SR1gK0842oBw&ip=2a02%3A1810%3A9517%3A5100%3A58f9%3A3c65%3A7f1d%3Afb57&id=o-AF8OlT74B3LfUqGaQ0AudG5i9Bv4s3r5DpnFPyHYEQzN&itag=243&aitags=133%2C134%2C135%2C136%2C137%2C160%2C242%2C243%2C244%2C247%2C248%2C278&source=youtube&requiressl=yes&mh=qH&mm=31%2C29&mn=sn-uxaxoxu-cg0k%2Csn-5hne6n7e&ms=au%2Crdu&mv=m&mvi=3&pl=47&initcwndbps=1548750&vprv=1&mime=video%2Fwebm&gir=yes&clen=24982541&dur=738.900&lmt=1546553117541033&mt=1588252653&fvip=4&keepalive=yes&fexp=23882514&beids=23886201&c=WEB&txp=5535432&sparams=expire%2Cei%2Cip%2Cid%2Caitags%2Csource%2Crequiressl%2Cvprv%2Cmime%2Cgir%2Cclen%2Cdur%2Clmt&sig=AJpPlLswRgIhAPfE951_Pwy_1-lonYzkDovdoTVznoTVdKNVmkATFNAzAiEA1VGrxZaY-W6sEG1nydhvMGK68-22e9cGrd9_6Tn1w5o%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Cinitcwndbps&lsig=ALrAebAwRgIhAOy_ofCoulf8zCnQILIodB0xmEITUXSvxod16Iv0ElZNAiEA4yc53bt1jWHhGdPP-gZ7EPE1HSARnw3P2mTNsdb1Uq0%3D&alr=yes&cpn=kwNTXAMegTYVDpPV&cver=2.20200429.03.00&range=440947-1353034&rn=7&rbuf=18583"

# since quicly fails so often, this allows fast re-testing 
# run_single_endpoint( "https://quic.examp1e.net/1000000", 0, "1MB_ampfactor0", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 1, "1MB_ampfactor1", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 2, "1MB_ampfactor2", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 3, "1MB_ampfactor3", "quicly" )
# run_single_endpoint( "https://quic.examp1e.net/1000000", 10, "1MB_ampfactor10", "quicly" )

if factor0: 
    run_single(          1_000_000,                     0,  "1MB_ampfactor0" )
    run_single_endpoint( facebook + "/",                0,  "1MB_ampfactor0", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           0,  "1MB_ampfactor0", "quiche" )
    run_single_endpoint( quiche_nginx + "/1MB.png",     0,  "1MB_ampfactor0", "quicheNginx" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     0,  "1MB_ampfactor0", "fbcdn" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 0,  "1MB_ampfactor0", "fbcdnCachebuster" )
    # run_single_endpoint( akamai + "/1M",                0,  "1MB_ampfactor0", "akamai" )
    # run_single_endpoint( ats + "/en/latest/admin-guide/files/records.config.en.html", 0,  "400KB_ampfactor0", "ats" )
    # run_single_endpoint( f5 +     "/50000",             0,  "500KB_ampfactor0", "f5" ) # closed with an unknown error
    # run_single_endpoint( gvideourlmedium,               0,  "1MB_ampfactor0",   "googlevideo" )
    # run_single_endpoint( msquic  + "/1MBfile.txt",      0,  "1MB_ampfactor0", "msquic" )


if factor1: 
    run_single(          1_000_000,                     1,  "1MB_ampfactor1" )
    run_single_endpoint( facebook + "/",                1,  "1MB_ampfactor1", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           1,  "1MB_ampfactor1", "quiche" )
    run_single_endpoint( quiche_nginx + "/1MB.png",     1,  "1MB_ampfactor1", "quicheNginx" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 1,  "1MB_ampfactor1", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     1,  "1MB_ampfactor1", "fbcdn" )

if factor2: 
    run_single(          1_000_000,                     2,  "1MB_ampfactor2" )
    run_single_endpoint( facebook + "/",                2,  "1MB_ampfactor2", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           2,  "1MB_ampfactor2", "quiche" )
    run_single_endpoint( quiche_nginx + "/1MB.png",     2,  "1MB_ampfactor2", "quicheNginx" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 2,  "1MB_ampfactor2", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     2,  "1MB_ampfactor2", "fbcdn" )

if factor10: 
    run_single(          1_000_000,                     10,  "1MB_ampfactor10" )
    run_single_endpoint( facebook + "/",                10,  "1MB_ampfactor10", "facebook" )
    run_single_endpoint( quiche + "/1MB.png",           10,  "1MB_ampfactor10", "quiche" )
    run_single_endpoint( quiche_nginx + "/1MB.png",     10,  "1MB_ampfactor10", "quicheNginx" )
    run_single_endpoint( fbcdn2  + "/rsrc.php/v3/yi/r/OBaVg52wtTZ.png?buster=" + ''.join(random.choice(string.ascii_lowercase) for i in range(8)), 10,  "1MB_ampfactor10", "fbcdnCachebuster" )
    run_single_endpoint( fbcdn  + "/speedtest-1MB",     10,  "1MB_ampfactor10", "fbcdn" )

# TODO: check the not_valid_before things in the session tickets for the ones that don't seem to work 
# TODO: limit initial_max_data and see if the server follows that 


if len(nozerorttendpoints) > 0:
    print("Some endpoints do not seem to support 0-RTT")
    print( nozerorttendpoints )