import logging, logging.config
import argparse
from json import JSONDecodeError
import os
import requests
import sys

# logging
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "basic": {
            "format": "\033[1m\033[92m[%(name)s]\033[0m %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "basic",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {},
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("Crawler")

# Constants
LOGS_URL = "https://interop.seemann.io/logs.json"
RESULTS_URL = "https://interop.seemann.io/{}/result.json"  # Requires formatting: run
QLOG_URL = "https://interop.seemann.io/{}/{}_{}/{}/{}/qlog/"  # Requires formatting: run, server, client, test, server or client

# Argparse
parser = argparse.ArgumentParser(description="QUIC Interop crawler (https://interop.seemann.io/) [last tested: 2020-4-30]")
parser.add_argument("--server", type=str.lower, default=None, help="Server name (case-insensitive)")
parser.add_argument("--client", type=str.lower, default=None, help="Client name (case-insensitive)")
parser.add_argument("--outdir", type=str, default="./output", help="Output directory [default=./output]")
parser.add_argument("-p", action="store_true", default=False, help="Setting this flag allows for selecting older interop runs [default=latest]")
parser.add_argument("-u", action="store_true", default=False, help="Collect all client interop runs for the provided server, --client is ignored")
parser.add_argument("-v", action="store_true", default=False, help="Verbose mode (display debugging information)")
args = parser.parse_args()


def select_input():
    data = int(input("> ")) - 1
    if data < 0:
        raise IndexError
    return data


def select_interop_run():
    try:
        # This will not work good if we have >100 runs in the future ;)
        logs = requests.get(LOGS_URL).json()
        logs_formatted = "\n".join("{}. {}".format(i+1, logs[i]) for i in range(0, len(logs)))
        logging.info("Interup run selector flag set. Pick one of the following interop runs:\n" + logs_formatted)
        selected_run = select_input()

        return logs[selected_run]
    except requests.exceptions.RequestException as e:
        logger.exception("Could not connect to interop website.", e)
    except JSONDecodeError as e:
        logger.exception("Output from interop runner was not valid JSON", e)
    except ValueError as e:
        logger.exception("Input was non integer", e)
    except IndexError as e:
        logger.warning("Selected undefined interop run [{}].".format(str(selected_run+1)))
        return "latest"


def check_selected_implementations():
    try:
        interop_results = requests.get(RESULTS_URL.format(run)).json()
        implementations = interop_results.get('servers')

        server_valid = args.server in implementations
        client_valid = args.client in implementations
        client_implementation_name = args.client
        server_implementation_name = args.server
        if not args.server or not server_valid or ((not args.client or not client_valid) and not args.u):
            implementations_formatted = "\n".join("{}. {}".format(i+1, implementations[i]) for i in range(0, len(implementations)))
            logger.info("List of available QUIC implementations for selected run:\n" + implementations_formatted)
            if (not args.client or not client_valid) and not args.u:
                logger.info("Select a client implementation:" if not args.client else "Invalid client name provided, select a client implementation:")
                client_implementation_name = implementations[select_input()]
            if not args.server or not server_valid:
                logger.info("Select a server implementation:" if not args.server else "Invalid server name provided, select a server implementation:")
                server_implementation_name = implementations[select_input()]
        return server_implementation_name, client_implementation_name, implementations
    except requests.exceptions.RequestException as e:
        logger.exception("Could not connect to interop website.", e)
    except JSONDecodeError as e:
        logger.exception("Output from interop runner was not valid JSON", e)
    except TypeError as e:
        logger.exception("Interop website did not return any servers?", e)


def check_output_dir():
    outdir = args.outdir
    if not os.path.exists(outdir):
        logging.warning("Given output path [{}] does not exist, do you want to create it?".format(outdir))
        create_path = input("y/n? ").strip().lower() == "y"
        if create_path:
            os.makedirs(outdir)
        else:
            logger.error("Cannot continue without output directory, halting script.")
            sys.exit()
    return outdir


def select_interop_test():
    try:
        tests = ["transfer", "http3"]
        logger.info("What interop test results should be crawled for?\n" + "\n".join("{}. {}".format(i+1, tests[i]) for i in range(0, len(tests))))
        selected_test = select_input()
        return tests[selected_test]
    except ValueError as e:
        logger.exception("Input was non integer", e)
    except IndexError:
        logger.warning("Selected undefined interop test [{}]. Cannot continue script.".format(str(selected_test + 1)))
        sys.exit()


def crawl(run, server, client, implementations, interop_test, outdir):
    clients_to_crawl = implementations if args.u else [client]
    perspectives = ["server", "client"]
    custom_headers = {"accept": "application/json"}
    for c in clients_to_crawl:
        for perspective in perspectives:
            try:
                qlog_url = QLOG_URL.format(run, server, c, interop_test, perspective)
                response = requests.get(qlog_url, headers=custom_headers)
                response.raise_for_status()
                directory_listing = response.json()
                for item in directory_listing:
                    if ".qlog" in item.get("name", []):
                        qlog_url = qlog_url + item.get("name")
                        logger.debug("Fetching {}".format(qlog_url))
                        qlog = requests.get(qlog_url, headers=custom_headers, stream=True)
                        out_path = os.path.join(outdir, "test-{}_server-{}_client-{}_perspective-{}.qlog".format(interop_test, server, c, perspective))
                        with open(out_path, "wb") as fp:
                            for chunk in qlog.iter_content(1024):
                                fp.write(chunk)
                        logger.info("QLOG for test [{}] between server [{}] and client [{}] saved to [{}].".format(interop_test, server, c, out_path))
                        break
            except (TypeError, JSONDecodeError, requests.HTTPError, ValueError):
                logger.warning("No QLOG results found for test [{}] between server [{}] and client [{}].".format(interop_test, server, c))


if __name__ == "__main__":
    if args.v:
        logger.setLevel(logging.DEBUG)

    run = "latest"
    if args.p:
        run = select_interop_run()

    logger.info("Collecting information for run [{}].".format(run))
    server, client, implementations = check_selected_implementations()

    if args.u:
        logger.info("Collecting all interop runs for server [{}]".format(server))
    else:
        logger.info("Collecting interop runs between server [{}] and client [{}]".format(server, client))

    outdir = check_output_dir()
    logger.info("Output directory set to [{}]".format(outdir))

    interop_test = select_interop_test()
    logger.info("Results from interop test [{}] will be collected.".format(interop_test))

    logger.info("Starting crawl...")
    crawl(run, server, client, implementations, interop_test, outdir)
    logger.info("Finished crawling, results can now be found in [{}]!".format(outdir))
