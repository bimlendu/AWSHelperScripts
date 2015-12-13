#!/usr/bin/python
'''
Gets data from AWS Trusted Advisor and prints non-ok checks.
'''

import json
import sys
import boto.support
conn = boto.support.connect_to_region('us-east-1')

class bcolors:
    UNK = '\033[94m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    ENDCOLOR = '\033[0m'

# TODO: Add code for calculating potential savings
# potential_monthly_savings = 0

checks = conn.describe_trusted_advisor_checks('en')
checksCount = 1
for check in checks['checks']:
  status = conn.describe_trusted_advisor_check_summaries([check['id']])['summaries'][0]['status']
  if status != 'ok': # and check['category'] == 'cost_optimizing':
    color = bcolors.WARNING if status == 'warning' else bcolors.ERROR if status == 'error' else bcolors.UNK
    print checksCount, '\tName: ' + check['name']
    print '\tCategory: ' + check['category']
    print '\tID : ' + check['id']
    print '\tStatus: ', color + conn.describe_trusted_advisor_check_summaries([check['id']])['summaries'][0]['status'] + bcolors.ENDCOLOR
    print
    print '\tFlagged Resources: '
    print '\t\tSlNo.\tStatus', '\t\t' if status == 'warning' else '\t', [str(md) for md in check['metadata']]
    print '\t\t---------------------------------------------------------'
    flaggedResources = conn.describe_trusted_advisor_check_result(check['id'],language='en')['result']['flaggedResources']
    flaggedResourcesCount = 1
    for resource in flaggedResources:
      if resource['status'] != 'ok': 
        color = bcolors.WARNING if status == 'warning' else bcolors.ERROR if status == 'error' else bcolors.UNK
        print '\t\t', str(flaggedResourcesCount), '\t', color + str(resource['status']), '\t', [str(item) for item in resource['metadata']],  bcolors.ENDCOLOR
        flaggedResourcesCount += 1
    print
    checksCount += 1
