#!/usr/bin/env python
#
# nmapdb.py - parse nmap XML output files and insert them into an SQLite database
#
# Copyright (c) 2009 Patroklos Argyroudis <argp at domain census-labs.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The names of the authors and copyright holders may not be used to
#    endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import getopt
import xml.dom.minidom
from pysqlite2 import dbapi2 as sqlite

VERSION = "1.1"
DEFAULT_DATABASE = "./nmapdb.db"

true = 1
false = 0
vflag = false

def myprint(msg):
    global vflag
    if vflag == true:
        print msg

    return

def usage(name):
    print "usage: %s [options] <nmap output XML file(s)>" % name
    print "options:"
    print "     (-h) --help         this message"
    print "     (-v) --verbose      verbose output"
    print "     (-c) --create       specify input SQL file to create SQLite DB"
    print "     (-d) --database     specify output SQLite DB file"
    print "     (-n) --nodb         do not perform any DB operations (i.e. dry run)"
    print "     (-V) --version      output version number and exit"

    return

def main(argv, environ):
    global vflag
    nodb_flag = false
    db_path = DEFAULT_DATABASE
    sql_file = ""
    argc = len(argv)

    if argc == 1:
        usage(argv[0])
        sys.exit(0)
 
    try:
        alist, args = getopt.getopt(argv[1:], "hvd:c:nV",
                ["help", "verbose", "database=", "create=", "nodb", "version"])
    except getopt.GetoptError, msg:
        print "%s: %s\n" % (argv[0], msg)
        usage(argv[0]);
        sys.exit(1)
 
    for(field, val) in alist:
        if field in ("-h", "--help"):
            usage(argv[0])
            sys.exit(0)
        if field in ("-v", "--verbose"):
            vflag = true
        if field in ("-d", "--database"):
            db_path = val
        if field in ("-c", "--create"):
            sql_file = val
        if field in ("-n", "--nodb"):
            nodb_flag = true
        if field in ("-V", "--version"):
            print "nmapdb v%s by Patroklos Argyroudis <argp at domain census-labs.com>" % (VERSION)
            print "parse nmap XML output files and insert them into an SQLite database"
            sys.exit(0)

    if len(args[0]) == 0:
        usage(argv[0])
        sys.exit(1)

    if nodb_flag == false:
        if db_path == DEFAULT_DATABASE:
            print "%s: no output SQLite DB file specified, using \"%s\"\n" % (argv[0], db_path)

        conn = sqlite.connect(db_path)
        cursor = conn.cursor()

        myprint("%s: successfully connected to SQLite DB \"%s\"\n" % (argv[0], db_path))

    if nodb_flag == false:
        if sql_file != "":
            sql_string = open(sql_file, "r").read()
        
            try:
                cursor.executescript(sql_string)
            except sqlite.ProgrammingError, msg:
                print "%s: error: %s\n" % (argv[0], msg)
                sys.exit(1)

            myprint("%s: SQLite DB created using SQL file \"%s\"\n" % (argv[0], sql_file))
    
    for fname in args:
        try:
            doc = xml.dom.minidom.parse(fname)
        except IOError:
            print "%s: error: file \"%s\" doesn't exist\n" % (argv[0], fname)
            continue
        except xml.parsers.expat.ExpatError:
            print "%s: error: file \"%s\" doesn't seem to be XML\n" % (argv[0], fname)
            continue

        for host in doc.getElementsByTagName("host"):
            try:
                address = host.getElementsByTagName("address")[0]
                ip = address.getAttribute("addr")
                protocol = address.getAttribute("addrtype")
            except:
                # move to the next host since the IP is our primary key
                continue

            try:
                mac_address = host.getElementsByTagName("address")[1]
                mac = mac_address.getAttribute("addr")
                mac_vendor = mac_address.getAttribute("vendor")
            except:
                mac = ""
                mac_vendor = ""

            try:
                hname = host.getElementsByTagName("hostname")[0]
                hostname = hname.getAttribute("name")
            except:
                hostname = ""

            try:
                status = host.getElementsByTagName("status")[0]
                state = status.getAttribute("state")
            except:
                state = ""

            try:
                os = host.getElementsByTagName("os")[0]
                os_match = os.getElementsByTagName("osmatch")[0]
                os_name = os_match.getAttribute("name")
                os_accuracy = os_match.getAttribute("accuracy")
                os_class = os.getElementsByTagName("osclass")[0]
                os_family = os_class.getAttribute("osfamily")
                os_gen = os_class.getAttribute("osgen")
            except:
                os_name = ""
                os_accuracy = ""
                os_family = ""
                os_gen = ""

            try:
                timestamp = host.getAttribute("endtime")
            except:
                timestamp = ""

            myprint("================================================================")

            myprint("[hosts] ip:\t\t%s" % (ip))
            myprint("[hosts] mac:\t\t%s" % (mac))
            myprint("[hosts] hostname:\t%s" % (hostname))
            myprint("[hosts] protocol:\t%s" % (protocol))
            myprint("[hosts] os_name:\t%s" % (os_name))
            myprint("[hosts] os_family:\t%s" % (os_family))
            myprint("[hosts] os_accuracy:\t%s" % (os_accuracy))
            myprint("[hosts] os_gen:\t\t%s" % (os_gen))
            myprint("[hosts] last_update:\t%s" % (timestamp))
            myprint("[hosts] state:\t\t%s" % (state))
            myprint("[hosts] mac_vendor\t%s" % (mac_vendor))

            if nodb_flag == false:
                try:
                    cursor.execute("INSERT INTO hosts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (ip, mac, hostname, protocol, os_name, os_family, os_accuracy,
                            os_gen, timestamp, state, mac_vendor))
                except sqlite.IntegrityError, msg:
                    print "%s: warning: %s: table hosts: ip: %s\n" % (argv[0], msg, ip)
                    continue
                except:
                    print "%s: unknown exception during insert into table hosts\n" % (argv[0])
                    continue

            try:
                ports = host.getElementsByTagName("ports")[0]
                ports = ports.getElementsByTagName("port")
            except:
                print "%s: host %s has no open ports\n" % (argv[0], ip)
                continue

            for port in ports:
                pn = port.getAttribute("portid")
                protocol = port.getAttribute("protocol")
                state_el = port.getElementsByTagName("state")[0]
                state = state_el.getAttribute("state")

                try:
                    service = port.getElementsByTagName("service")[0]
                    port_name = service.getAttribute("name")
                except:
                    service = ""
                    port_name = ""

                myprint("\t------------------------------------------------")

                myprint("\t[ports] ip:\t\t%s" % (ip))
                myprint("\t[ports] port:\t\t%s" % (pn))
                myprint("\t[ports] protocol:\t%s" % (protocol))
                myprint("\t[ports] name:\t\t%s" % (port_name))
                myprint("\t[ports] state:\t\t%s" % (state))
                myprint("\t[ports] service:\t")

                if nodb_flag == false:
                    try:
                        cursor.execute("INSERT INTO ports VALUES (?, ?, ?, ?, ?, NULL)",
                                (ip, pn, protocol, port_name, state))
                    except sqlite.IntegrityError, msg:
                        print "%s: warning: %s: table ports: ip: %s\n" % (argv[0], msg, ip)
                        continue
                    except:
                        print "%s: unknown exception during insert into table ports\n" % (argv[0])
                        continue

                myprint("\t------------------------------------------------")

            myprint("================================================================")

    if nodb_flag == false:
        conn.commit()

if __name__ == "__main__":
    main(sys.argv, os.environ)
    sys.exit(0)

# EOF
