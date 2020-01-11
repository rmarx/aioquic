import subprocess

# need to run setup.py first to make sure all our changes are compiled before running
# need to run this from inside the root dir
# so do python3 scripts/run_tests.py

print("Compiling...")
process = subprocess.run("{}".format("python3 /srv/aioquic_live/setup.py install"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

# if ( len(process.stdout) > 0 ):
#     print ( process.stdout )


if process.returncode is not 0:
    print ("ERROR in compilation: ", process.returncode, " != 0?")
    print ( process.stderr )

print("Compilation done!")

basecommand = "python3 /srv/aioquic_live/examples/http3_client.py --insecure"

class Endpoint:
    def __init__(self, url, name):
        self.url = url
        self.name = name

proper_endpoints = [
    Endpoint("https://quic.aiortc.org/{}", "aioquic"),
    Endpoint("https://test.privateoctopus.com:4433/{}", "picoquic"), 
    Endpoint("https://http3-test.litespeedtech.com:4433/{}", "lsquic"),
    Endpoint("https://fb.mvfst.net:4433/{}", "mvfst"),
    Endpoint("https://nghttp2.org:4433/{}", "ngtcp2"),
    Endpoint("https://quic.examp1e.net/{}", "quicly")
]

hacky_endpoints = [
    Endpoint("https://f5quic.com:4433", "f5"), # only has 50000, 5000000, 10000000 (50KB, 5MB , 10MB)
    Endpoint("https://quic.westus.cloudapp.azure.com/1MBfile.txt", "msquic"), # only has 5000000.txt, 10000000.txt, 1MBfile.txt (1MB, 5MB, 10MB)
    Endpoint("https://quic.tech:8443/1MB.png","quiche"),
    Endpoint("https://www.facebook.com/rsrc.php/v3iXG34/y_/l/en_GB/ppT9gy-P_lf.js?_nc_x=Ij3Wp8lg5Kz", "mvfst-facebook"),
    Endpoint("https://scontent-bru2-1.xx.fbcdn.net/v/t31.0-8/11333999_10206053543551446_142142577509361396_o.jpg?_nc_cat=105&_nc_ohc=Ydfgv65b-1wAQlHich3zGFlggP_28Kct-L9A4ks99FSLaEK7oLNPMiFtQ&_nc_ht=scontent-bru2-1.xx&oh=11dbe11236cf4df32e3f3518d2f91a16&oe=5E7E764A", "mvfst-fbcdn")
]

singlefile_endpoints = [
    Endpoint("https://quic.ogre.com:4433/en/latest/admin-guide/files/records.config.en.html", "ats"), # doesn't really have any large files
]

def run_single(size, testname):

    for endpoint in proper_endpoints:
        url = endpoint.url.format(str(size))
        cmd = basecommand + " " + "--quic-log /srv/aioquic/qlog/results/single/single_" + testname + "_" + endpoint.name + ".qlog " + url
        print ("Executing ", cmd)
        run_command ( cmd )

    # print( list(map( lambda endpoint : endpoint.name + " " + endpoint.url, proper_endpoints )) )
    # print( list(map( lambda endpoint : endpoint.name + " " + endpoint.url, hacky_endpoints )) )


def run_single_fbcdn(url, testname, endpointName = "fbcdn"):

    for endpoint in proper_endpoints:
        cmd = basecommand + " " + "--quic-log /srv/aioquic/qlog/results/single/single_" + testname + "_" + endpointName + ".qlog \"" + url + "\""
        print ("Executing ", cmd)
        run_command ( cmd )

def run_parallel(size, amount, delay, testname):
    for endpoint in proper_endpoints:
        url = endpoint.url.format(str(size))
        delaystr = ""
        if delay > 0:
            delaystr = " --delay-parallel " + str(delay) + " " # delay is in SECONDS

        cmd = basecommand + " " + "--parallel " + str(amount) + delaystr + " --quic-log /srv/aioquic/qlog/results/parallel/parallel_" + testname + "_" + endpoint.name + ".qlog " + url
        print ("Executing ", cmd)
        run_command ( cmd )



def run_command(cmd):
    process = subprocess.run("{}".format(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if ( len(process.stdout) > 0 ):
        print ( process.stdout )

    if len(process.stderr) is not 0 or process.returncode is not 0:
        print ("Potential ERROR in process: ", process.returncode, " != 0?")
        print ( process.stderr )

# debugging
# run_single(5000, "1file_5000B_0ms")
# run_single(1_000_000, "1file_1MB_0ms")
# run_single(5_000_000, "1file_5MB_0ms")

# run_single_fbcdn("https://scontent.xx.fbcdn.net/speedtest-10MB", "1file_10MB_0ms")
# run_single_fbcdn("https://scontent.xx.fbcdn.net/speedtest-100MB", "1file_100MB_0ms")
# run_single_fbcdn("https://xx-fbcdn-shv-01-bom1.fbcdn.net/speedtest-10MB", "1file_10MB_0ms", "fbcdn-india")

# run_single_fbcdn("https://scontent-bru2-1.xx.fbcdn.net/v/t31.0-8/11333999_10206053543551446_142142577509361396_o.jpg?_nc_cat=105&_nc_ohc=Ydfgv65b-1wAQlHich3zGFlggP_28Kct-L9A4ks99FSLaEK7oLNPMiFtQ&_nc_ht=scontent-bru2-1.xx&oh=11dbe11236cf4df32e3f3518d2f91a16&oe=5E7E764A",
#    "1file_400KB_0ms")

# probe for default buffer size (min packet size is 1280, so work in increments of that)
# run_parallel(1200,  10, 0, "10files_1200B_0ms") # 1 packet
# run_parallel(2400,  10, 0, "10files_2400B_0ms") # 2 packets
# run_parallel(3600,  10, 0, "10files_3600B_0ms") # 3 packets
# run_parallel(7200,  10, 0, "10files_7200B_0ms") # 6 packets
# run_parallel(12000, 10, 0, "10files_12KB_0ms") # 10 packets

# initial tests: 10x xMB, see global multiplexing behaviour appear
# run_parallel(1_000_000, 10, 0, "10files_1MB_0ms")
# run_parallel(5_000_000, 10, 0, "10files_5MB_0ms")
# run_parallel(10_000_000, 10, 0, "10files_10MB_0ms")

# 2nd tests: slight delay between files, see how that affects things (when does e.g., RR kick in)
# run_parallel(1_000_000, 10, 0.1,    "10files_1MB_100ms")
# run_parallel(1_000_000, 10, 0.5,    "10files_1MB_500ms")
# run_parallel(1_000_000, 10, 1,      "10files_1MB_1000ms")
