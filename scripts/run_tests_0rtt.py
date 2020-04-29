import subprocess

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

basecommand = "python3 /srv/"+directoryName+"/examples/http3_client_0rtt.py --insecure -v"

class Endpoint:
    def __init__(self, url, name):
        self.url = url
        self.name = name

runname = ""

proper_endpoints = [
    # Endpoint("https://quic.aiortc.org/{}", "aioquic"),
    # Endpoint("https://mew.org:4433/{}", "haskell"),
    # Endpoint("https://quicgo:4122/{}", "quicgo"),
    # Endpoint("https://neqo:4123/{}", "neqo"),
    # # Endpoint("https://quic.seemann.io/{}", "quicgo"), # not online
    Endpoint("https://test.privateoctopus.com:4433/{}", "picoquic"), 
    # Endpoint("https://http3-test.litespeedtech.com:4433/{}", "lsquic"),
    # # Endpoint("https://fb.mvfst.net:443/{}", "mvfst"), # // this endpoint was not reachable when we did these tests
    # Endpoint("https://nghttp2.org:4433/{}", "ngtcp2"),
    # Endpoint("https://quic.examp1e.net/{}", "quicly"),
    # Endpoint("https://quic.rocks:4433/{}", "google"),
    # Endpoint("https://h3.stammw.eu:4433/{}", "quinn"), # is proper, but bugs out when requesting many files at once... put it at the back of the runs manually to prevent it from holding up everything
]

f5          = "https://f5quic.com:4433"                 # only has 50000, 5000000, 10000000 (50KB, 5MB , 10MB)
msquic      = "https://quic.westus.cloudapp.azure.com"  # only has 5000000.txt, 10000000.txt, 1MBfile.txt, index.html (1MB, 5MB, 10MB, 1KB)
quiche      = "https://quic.tech:8443"                  # only has 1MB.png, 5MB.png
quiche_nginx = "https://cloudflare-quic.com"            # only has 1MB.png, 5MB.png
facebook    = "https://www.facebook.com"                # "rsrc.php/v3iXG34/y_/l/en_GB/ppT9gy-P_lf.js?_nc_x=Ij3Wp8lg5Kz"
fbcdn       = "https://scontent.xx.fbcdn.net"           # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB
fbcdn_india = "https://xx-fbcdn-shv-01-bom1.fbcdn.net"  # only has /speedtest-1MB, /speedtest-5MB, /speedtest-10MB
ats         = "https://quic.ogre.com:4433"              # en/latest/admin-guide/files/records.config.en.html
akamai      = "https://ietf.akaquic.com"                # /10k, /100k, /1M # based on google's implementation # can't deal with multiple requests at the same time
quinn       = "https://h3.stammw.eu:4433"               # proper, any integer after / goes
gvideo      = "googlevideo.com"

def run_single(size, testname):

    for endpoint in proper_endpoints:
        url = endpoint.url.format(str(size))
        cmd = basecommand + " " + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_" + endpoint.name + ".qlog " + url
        print ("Executing ", cmd)
        run_command ( cmd )

def run_single_endpoint(url, testname, endpointName):

    cmd = basecommand + " " + "--quic-log /srv/"+logDirectoryName+"/qlog/run"+ runname + "_" + testname + "_" + endpointName + ".qlog \"" + url + "\""
    print ("Executing ", cmd)
    run_command ( cmd )

def run_command(cmd):
    process = subprocess.run("{}".format(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if ( len(process.stdout) > 0 ):
        print ( process.stdout )

    if len(process.stderr) is not 0 or process.returncode is not 0:
        # print ("Potential ERROR in process: ", process.returncode, " != 0?")
        print ( process.stderr )

runname = "0rtttest"

run_single(                    1000,        "0rtt_1file_1KB_0ms" )
# run_single_endpoint( msquic  + "/1MBfile.txt",  "big_1file_1MB_0ms", "msquic" )