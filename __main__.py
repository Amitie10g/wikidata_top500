#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOP500 importer main script

Copyright (c) 2019 Davod (Amitie 10g)

Licensed under the MIT license. See LICENSE for details
"""

# :: Prepare
try:
    try:
        # :: Import standard libraries
        try:
            import sys
            import getopt
        except ModuleNotFoundError as e:
            sys.stderr.write(str(e) + '\n')
            sys.exit(1)

        # Import local library
        from library import Top500Importer

        # :: Check Python version (3.5 or above)
        if sys.version_info < (3, 5):
            sys.stderr.write("You need python 3.5 or later to run this script\n")
            sys.exit(0)

        # :: Check if configuration has been properly set at config.py
        try:
            import config as cfg

            wiki_site = cfg.config['site']
            wiki_lang = cfg.config['lang']
            instance_of = cfg.config['instance_of']
            top500url = cfg.config['top500url']
            log_page = cfg.config['log_page']
            status_page = cfg.config['status_page']
            redis_server = cfg.config['redis_server']
            redis_port = cfg.config['redis_port']
        except (NameError, IndexError, ModuleNotFoundError) as e:
            sys.stderr.write(str(e) + '\n')
            sys.exit(1)

        # :: Get args
        argv = sys.argv[1:]
        usage = 'Usage: python3 pywikibot/pwb.py main.py [-i <Wikidata item> -t <TOP500 id> | --mass] num\n'

        # :: Parse args
        if argv == []:
            print(usage)
            sys.exit(0)

        try:
            opts, args = getopt.getopt(argv, "i:t:", "mass")
            args2 = []
            for opt, arg in opts:
                if opt in ("-i", "-t"):
                    args2.append(arg)
                elif opt in "--mass":
                    try:
                        args2 = ['mass', argv[1]]
                    except (ValueError, IndexError):
                        args2 = ['mass', 0]

        except getopt.GetoptError:
            print(usage)
            sys.exit(0)

        if args2 == []:
            print(usage)
            sys.exit(0)

        try:
            # :: Call the Top500Importer object
            top500importer = Top500Importer(
                wiki_site, wiki_lang,
                redis_server,
                redis_port,
                instance_of,
                top500url,
                log_page,
                status_page)
        except TypeError as e:
            sys.stderr.write(str(e) + '\n')

        try:
            print(top500importer.error)
            sys.exit(1)
        except (NameError, AttributeError):
            pass

    except KeyboardInterrupt as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(1)

except SystemExit as e:
    sys.exit(0) # This, to avoid restart the task

# :: Begin
try:
    try:
        # :: Mass import
        if args2[0] == 'mass':
            top500importer.updateStatus(0)

            if top500importer.mass(args2[1]):
                print('Everything OK\n')

            try:
                system_status = top500importer.qstat()
                if system_status.returncode == 0:
                    sys.exit(128)

                else:
                    sys.exit(2)

            except FileNotFoundError:
                sys.exit(2)

        # :: One-file import
        else:
            if len(args2) == 2:
                top500importer.updateStatus(0)

                if top500importer.main(args2[1], args2[0]):
                    print('Everything OK\n')

                    try:
                        system_status = top500importer.qstat()
                        if system_status.returncode == 0:
                            sys.exit(128)

                        else:
                            sys.exit(2)

                    except FileNotFoundError:
                        sys.exit(2)

                else:
                    sys.exit(1)

            else:
                print(usage)
                sys.exit(3)

    except KeyboardInterrupt:
        try:
            system_status = top500importer.qstat()
            if system_status.returncode == 0:
                sys.exit(128)
            else:
                sys.exit(2)

        except FileNotFoundError:
            sys.exit(2)

except SystemExit as e:
    top500importer.updateStatus(e.code)
    sys.exit(0) # This, to avoid restart the task
