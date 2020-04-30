# Seemann QUIC Interop crawler

## Use
**Install**
`pip install -r requirements.txt`

**Simple run**
`python crawler.py`
Script will ask for input.

**CLI usage**
```
usage: crawler.py [-h] [--server SERVER] [--client CLIENT] [--outdir OUTDIR] [-p] [-u] [-v]

QUIC Interop crawler (https://interop.seemann.io/) [last tested: 2020-4-30]

optional arguments:
  -h, --help       show this help message and exit
  --server SERVER  Server name (case-insensitive)
  --client CLIENT  Client name (case-insensitive)
  --outdir OUTDIR  Output directory [default=./output]
  -p               Setting this flag allows for selecting older interop runs [default=latest]
  -u               Collect all client interop runs for the provided server, --client is ignored
  -v               Verbose mode (display debugging information)
```

## Notes
- Interop tests are currently hardcoded
- It's quickly coded, many edgecases are not being handled (i.e., if stuff does not work, check if the interop website if online)

## Findings
- Available logs: https://interop.seemann.io/logs.json
- Latest results: https://interop.seemann.io/latest/result.json
- Results are logged at: /{timestamp || "latest"}/<server>_<client>/<testname>/{"server" || "client"}/qlog/<connection_id>.qlog
    - Backend server = caddy; as guessed this supports JSON file listings if we change our accept request header to include JSON (e.g., curl -H "Accept: application/json" https://interop.seemann.io/logs_2020-04-27T20:21:17UTC/quicgo_quicly/transfer/server/qlog/)
