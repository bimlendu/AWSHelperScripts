#!/usr/bin/env python

import boto.ec2
conn = boto.ec2.connect_to_region("us-east-1")
reservations = conn.get_all_instances()
for r in reservations:
    for i in r.instances:
        if i.state == 'stopped':
            if 'Name' in i.tags:
                print "%s\t(%s) [%s] %s" % (i.tags['Name'], i.id, i.state, i.reason)
            else:
                print "(%s) [%s] %s" % (i.id, i.state, i.reason)