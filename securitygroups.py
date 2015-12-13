#!/usr/bin/env python
'''
'''

import collections
import boto.ec2
import pprint

SecurityGroupRule = collections.namedtuple('SecurityGroupRule', ['ip_protocol', 'from_port', 'to_port', 'cidr_ip', 'src_group_name'])

BASE_GLOBAL_PRIVATE_RULES = [
  SecurityGroupRule('tcp', '22', '22', '10.0.0.0/8', None),
  SecurityGroupRule('tcp', '22', '22', '172.16.0.0/12', None),
  SecurityGroupRule('tcp', '22', '22', '192.168.0.0/16', None)
]

ELB_WEB_PUBLIC_RULES = [
  SecurityGroupRule('tcp', '80', '80', '0.0.0.0/0', None),
  SecurityGroupRule('tcp', '443', '443', '0.0.0.0/0', None),
]

SECURITY_GROUPS = [('base-global-private', BASE_GLOBAL_PRIVATE_RULES),
                   ('elb-web-public', ELB_WEB_PUBLIC_RULES)]


def get_or_create_security_group(c, group_name, description=''):
    print 'Getting groups list...'
    groups = [g for g in c.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
        print 'Creating group %s ...' % (group_name,)
        group = c.create_security_group(group_name, group_name, vpc_id='vpc-********')
    else:
        print 'Group %s already present.' % (group_name,)
    return group


def modify_sg(c, group, rule, authorize=False, revoke=False):
    src_group = None
    if rule.src_group_name:
        src_group = c.get_all_security_groups([rule.src_group_name, ])[0]

    if authorize and not revoke:
        print 'Adding missing rule %s ...' % (rule,)
        group.authorize(ip_protocol=rule.ip_protocol,
                        from_port=rule.from_port,
                        to_port=rule.to_port,
                        cidr_ip=rule.cidr_ip,
                        src_group=src_group)
    elif not authorize and revoke:
        print 'Revoking unexpected rule %s ...' % (rule,)
        group.revoke(ip_protocol=rule.ip_protocol,
                     from_port=rule.from_port,
                     to_port=rule.to_port,
                     cidr_ip=rule.cidr_ip,
                     src_group=src_group)


def authorize(c, group, rule):
    return modify_sg(c, group, rule, authorize=True)


def revoke(c, group, rule):
    return modify_sg(c, group, rule, revoke=True)


def update_security_group(c, group, expected_rules):
    print 'Updating group %s ...' % (group.name,)
    print 'Expected Rules: '
    pprint.pprint(expected_rules)
    current_rules = []
    for rule in group.rules:
        for grant in rule.grants:
            if not grant.cidr_ip:
                current_rule = SecurityGroupRule(rule.ip_protocol,
                                                 rule.from_port,
                                                 rule.to_port,
                                                 '0.0.0.0/0',
                                                 grant.name)
            else:
                current_rule = SecurityGroupRule(rule.ip_protocol,
                                                 rule.from_port,
                                                 rule.to_port,
                                                 grant.cidr_ip,
                                                 None)
            if current_rule not in expected_rules:
                revoke(c, group, current_rule)
            else:
                current_rules.append(current_rule)

    print 'Current Rules: '
    pprint.pprint(current_rules)

    for rule in expected_rules:
        if rule not in current_rules:
            authorize(c, group, rule)


def create_security_groups():
    c = boto.connect_ec2()
    for group_name, rules in SECURITY_GROUPS:
        print '*** %s ***' % (group_name,)
        group = get_or_create_security_group(c, group_name)
        update_security_group(c, group, rules)
        print '-----------------------------------------------'

if __name__ == '__main__':
    create_security_groups()
