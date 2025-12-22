#!/usr/bin/env python
import sys

from infrapy.database.taskbase.loc import LocInfraPy


def run(config_file):
    pdetect = LocInfraPy(config_file)
    pdetect.database_connecting()
    pdetect.data_processing()


if __name__ == '__main__':
    try:
        config_file = sys.argv[1]
    except Exception:
        print('A configuration file is required to start data processing')
        sys.exit()

    print('Running location methods with configuration param:', config_file)
    run(config_file)
