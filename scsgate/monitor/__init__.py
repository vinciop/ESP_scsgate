""" This module implements the scs-monitor cli tool """
import argparse
import logging
import pathlib
import signal
import sys
import yaml

import scsgate.messages as messages
from scsgate.connection import Connection


def cli_opts():
    """ Handle the command line options """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--homeassistant-config",
        type=str,
        required=False,
        dest="config",
        help="Create configuration section for home assistant",)
    parser.add_argument(
        "-f",
        "--filter",
        type=str,
        required=False,
        dest="filter",
        help="Ignore events related with these devices",)
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        dest="output",
        help="Send output to file",)
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        dest="verbose",
        help="Verbose output",)
    parser.add_argument('device')
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        required=False,
        dest="port",
        help="port used for the connection",)

    return parser.parse_args()


class Monitor:
    """ Class monitoring bus event """

    def __init__(self, options):
        self._options = options

        # A dict with scs_id as key and another dict as value.
        # The latter dict has 'ha_id' and 'name' as keys.
        self._devices = {}

        log_level = logging.WARNING

        if options.output:
            logging.basicConfig(
                format='%(asctime)s : %(message)s',
                level=logging.DEBUG,
                filename=options.output,
                filemode="a")
        else:
            logging.basicConfig(
                format='%(asctime)s : %(message)s',
                level=logging.DEBUG)

        if options.verbose:
            log_level = logging.DEBUG
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s: %(message)s',
            level=log_level)

        if self._options.filter:
            self._load_filter(self._options.filter)

        self._connection = Connection(device=options.device, logger=logging, port=options.port)

        self._setup_signal_handler()

    def _setup_signal_handler(self):
        """ Register signal handlers """
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGQUIT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """ Method called when handling signals """
        if self._options.config:
            with open(self._options.config, "w") as cfg:
                yaml.dump(self._home_assistant_config(self._options), cfg, sort_keys=False)
                print(
                    "Dumped home assistant configuration at",
                    self._options.config)
        self._connection.close
        sys.exit(0)

    def start(self):
        """ Monitor the bus for events and handle them """
        print("Entering monitoring mode, press CTRL-C to quit")
        socket = self._connection._socket

        while True:
            self._connection.send(b"@R")
            raw = self._connection.receive()
            if not ((raw == b'k') or (raw is None)):
                length = int(raw[:1], 16)
                if length == 0:
                    return
                data = raw[1:]
                message = data
                if not self._options.config or \
                    int(message.decode("utf-8")[2:4]) is None or \
                    int(message.decode("utf-8")[2:4]) in self._devices or \
                    message.decode("utf-8")[0:2] == '16':
                    continue

                print("New device found")
                #print(message)
                ha_id = message.decode("utf-8")[2:4]
                name = input("Enter name: ")
                type = input("Enter type(1=light, 2=cover, 3=switch): ")
                self._add_device(scs_id=int(message.decode("utf-8")[2:4]), ha_id=ha_id, name=name, type=type)

    def _add_device(self, scs_id, ha_id, name, type):
        """ Add device to the list of known ones """
        if scs_id in self._devices:
            return

        self._devices[scs_id] = {
            'name': name,
            'ha_id': ha_id,
            'type': type
        }

    def _home_assistant_config(self, options):
        """ Creates home assistant configuration for the known devices """
        devices = {}
        light = {}
        cover = {}
        switch = {}
        for scs_id, dev in self._devices.items():
            if dev['type'] == '1':
                light[dev['ha_id']] = {
                    'name': dev['name'],
                    'scs_id': scs_id}
            if dev['type'] == '2':
                cover[dev['ha_id']] = {
                    'name': dev['name'],
                    'scs_id': scs_id}
            if dev['type'] == '3':
                switch[dev['ha_id']] = {
                    'name': dev['name'],
                    'scs_id': scs_id}

        return {'scsgate': {'device': options.device, 'port': options.port}, 'light':{'platform':'scsgate', 'devices': light}, 'cover':{'platform':'scsgate', 'devices': cover}, 'switch':{'platform':'scsgate', 'devices': switch}}

    def _load_filter(self, config):
        """ Load the filter file and populates self._devices accordingly """
        path = pathlib.Path(config)
        if not path.is_file():
            return

        with open(config, 'r') as conf:
            devices = yaml.load(conf)['devices']
            for ha_id, dev in devices.items():
                self._devices[dev['scs_id']] = {
                    ha_id: dev,
                    'name': dev['name']}


def main():
    """ Entry point of the scs-monitor cli tool """

    options = cli_opts()
    monitor = Monitor(options)
    monitor.start()
