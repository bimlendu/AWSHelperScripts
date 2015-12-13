#!/usr/bin/env python
# __version__ = 1.0
# __author__ = 'Bimlendu Mishra'

import os
import sys
import time

try:
  from colorama import init, Fore
  init(autoreset=True)
except ImportError:
  print "ERROR: Please install 'colorama' using 'sudo pip install colorama' or 'sudo easy_install colorama'"
  sys.exit(2)

try:
  import argparse
except ImportError:
  print Fore.RED + "ERROR: Please install 'argparse' using 'sudo pip install argparse' or 'sudo easy_install argparse'"
  sys.exit(2)

try:
  import boto.ec2
  from boto.ec2.blockdevicemapping import BlockDeviceType
  from boto.ec2.blockdevicemapping import BlockDeviceMapping
except ImportError:
  print Fore.RED + "ERROR: Please install 'boto' using 'sudo pip install boto' or 'sudo easy_install boto'"
  sys.exit(2)


def valid_role(role):
  if '-' not in role:
    msg = 'Not a valid role: ' + role + '. Should be of format <service>-<stack>, eg. webc-bys'
    raise argparse.ArgumentTypeError(msg)
  return role


def valid_tag(tag_key, tag_value):
  if tag_value.lower() not in open(tag_key + '.tags').read():
    raise argparse.ArgumentTypeError('Not a valid ' + tag_key + ' tag.')
  return tag_value


def valid_product_tag(tag):
  return valid_tag('product', tag)


def valid_project_tag(tag):
  return valid_tag('project', tag)


def valid_environment(env):
  return valid_tag('environment', env)


def getSecurityGroupID(conn, name):
    '''Get security group id from security group name, returns the id as string.'''
    groups = conn.get_all_security_groups()
    for group in groups:
        if group.name == name:
            id = group.id
    return id


def connectEC2(region):
    '''Connects to EC2, returns a connection object'''
    try:
        conn = boto.ec2.connect_to_region(region)
    except Exception, e:
        sys.stderr.write('Could not connect to region: %s. Exception: %s\n' % (region, e))
        conn = None
    return conn


def genUserData(role, env, chef_version):
    '''Generates user data script based on chef role and environment, returns user_data script as string object.'''
    data = """#!/bin/bash -xe
ROLE=%s
ENV=%s
yum update -y
echo $(/sbin/ifconfig eth0 | grep "inet addr:" | cut -d: -f2 | cut -d" " -f1) $(hostname) >> /etc/hosts
true && curl -L https://www.opscode.com/chef/install.sh | bash -s -- -v %s
mkdir /etc/chef
mkdir /var/log/chef
aws s3 cp s3://bootstrap/bootstrap.tar.gz /tmp/bootstrap.tar.gz
tar -zxf /tmp/bootstrap.tar.gz -C /tmp
cd /tmp/bootstrap
cat > roles/$ROLE.json << EOL
{
  "name": "$ROLE",
  "json_class": "Chef::Role",
  "chef_type": "role",
  "run_list": [
    "recipe[ec2-ohai]",
    "recipe[hostname]",
    "recipe[chef-client]"
    ]
}
EOL
cat > environments/$ENV.json << EOL
{
  "name": "$ENV",
  "json_class": "Chef::Environment",
  "chef_type": "environment"
}
EOL
chef-client --local-mode -E $ENV -r "role[$ROLE]"
aws s3 cp s3://bootstrap/corp-validator.pem /etc/chef/corp-validator.pem
aws s3 cp s3://bootstrap/corp-client.rb /etc/chef/client.rb
cd ~
rm -rf /tmp/bootstrap
rm -f /etc/chef/client.pem
service chef-client start
    """ % (role, env, chef_version)
    return data


def attachEBS(conn, instance, size):
    '''Attaches an EBS volume to that instance'''
    print Fore.YELLOW + 'Trying to create an EBS volume.'
    # Create a volume in the same availability zone as the instance
    volume = conn.create_volume(size, instance.placement)
    status = ''
    while status != 'available':
        status = conn.get_all_volumes([volume.id])[0].status
        print Fore.GREEN + "Volume created. Status: %s" % status
        time.sleep(5)
    # Attach once EBS becomes available
    volume.attach(instance.id, '/dev/sdh')
    print Fore.GREEN + 'Volume ' + volume.id + ' attached.'


def getSubnetID(placement, env):
    '''Gets subnets ID based on the placement zone and env of the instance, returns a subnet id string.'''
    subnets_map = {'us-east-1a': {'dev': 'subnet-********',
                                  'qe': 'subnet-********',
                                  'uat': 'subnet-********',
                                  'prod': 'subnet-********'},
                   'us-east-1b': {'corp': 'subnet-********',
                                  'dev2': 'subnet-********',
                                  'test': 'subnet-********',
                                  'uat': 'subnet-********'}
                   }
    return subnets_map[placement][env]


def launchInstance(region, rootsize, role, env, ami, key_name, instance_type, placement, sec_group, iamrole, ebs, product, project, name, chefversion):
    '''Launch a single instance of the provided ami'''

    conn = connectEC2(region)

    mapping = BlockDeviceMapping()
    root = BlockDeviceType()
    root.size = rootsize
    mapping['/dev/xvda'] = root

    user_data = genUserData(role, env, chefversion)

    sec_group_id = getSecurityGroupID(conn, sec_group)

    subnet_id = getSubnetID(placement, env)

    print Fore.YELLOW + 'Instance will be launched with following parameters.\n'
    print Fore.GREEN + 'Region :\t\t' + region
    print Fore.GREEN + 'Chef Role :\t\t' + role
    print Fore.GREEN + 'Chef Env :\t\t' + env
    print Fore.GREEN + 'AMI ID :\t\t' + ami
    print Fore.GREEN + 'Keypair :\t\t' + key_name
    print Fore.GREEN + 'Instance Type :\t\t' + instance_type
    print Fore.GREEN + 'Placement :\t\t' + placement
    print Fore.GREEN + 'Security Group :\t' + sec_group + ' (' + sec_group_id + ')'
    print Fore.GREEN + 'Subnet ID :\t\t' + subnet_id
    print Fore.GREEN + 'IAM Role :\t\t' + iamrole
    if ebs:
        print Fore.GREEN + 'EBS Volume Size: ' + str(ebs) + ' GB'
    print Fore.YELLOW + '\nFollowing tags will be attached to the instance.\n'
    if name:
      print Fore.GREEN + 'Name :\t\t\t' + name.lower()
    print Fore.GREEN + 'Product :\t\t' + product.lower()
    print Fore.GREEN + 'Project :\t\t' + project.lower()
    print Fore.GREEN + 'Environment :\t\t' + env.lower()

    print Fore.YELLOW + '\nTrying to launch an EC2 instance ...'
    reservation = conn.run_instances(ami,
                                     key_name=key_name,
                                     user_data=user_data,
                                     instance_type=instance_type,
                                     placement=placement,
                                     subnet_id=subnet_id,
                                     block_device_map=mapping,
                                     instance_initiated_shutdown_behavior='stop',
                                     security_group_ids=['sg-********', sec_group_id],
                                     instance_profile_name=iamrole,
                                     dry_run=False)

    print(Fore.YELLOW + '\nWaiting for instance to start ...')
    instance = reservation.instances[0]
    status = instance.update()
    while status == 'pending':
        time.sleep(5)
        status = instance.update()
    if status == 'running':
        print(Fore.GREEN + 'New instance "' + instance.id + '" accessible at ' + instance.private_ip_address)
        print(Fore.YELLOW + 'Adding tags.')
        if name:
          instance.add_tag('Name',name.lower())
        instance.add_tag('Product', product.lower())
        instance.add_tag('Project', project.lower())
        instance.add_tag('Environment', env.lower())
    else:
        print(Fore.YELLOW + 'Instance status: ' + status)
        return
    # If we got through the launching successfully, go ahead and create and attach a volume.
    if ebs:
        attachEBS(conn, instance, ebs)

    print Fore.GREEN + '\nInstance ' + instance.id + ' launched successfuly.'
    #print Fore.GREEN + '\n\nInstance Status :\n\n'
    #pprint.pprint(instance.__dict__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''Creates an EC2 instance, with our setup.

This script uses `boto` python module. you need to have a ~/.boto file with your aws credentials.

#########################
[Credentials]
aws_access_key_id = <your access key>
aws_secret_access_key = <your secret key>
#########################

More details on boto credentials setup here: http://boto.readthedocs.org/en/latest/boto_config_tut.html

Required arguments:

1. Server role, -r/--role
2. Environment, -e/--env
3. Product Tag, -p/--product
4. Project Tag, -j/--project
5. Availability Zone, -z/--placement

Rest all are optional with appropriate defaults. Default values are shown in square brackets [].
        ''',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='EBS volume created and attached will have to be made usable.')
    required = parser.add_argument_group('required arguments')
    
    required.add_argument('-r', '--role',
      required=True,
      type=valid_role,
      help='Instance Chef role. Role format is <service>-<stack> , eg. webc-bys, etc.')
    
    required.add_argument('-e', '--env',
      required=True,
      type=valid_environment,
      help='Instance Chef environment.')

    required.add_argument('-z', '--placement',
      required=True,
      choices=['us-east-1a', 'us-east-1b'],
      help='Availability Zone to launch the instance in.')

    required.add_argument('-p', '--product',
      required=True,
      type=valid_product_tag,
      help='Product tag to attach to the instance.')

    required.add_argument('-j', '--project',
      required=True,
      type=valid_project_tag,
      help='Project tag to attach to the instance.')

    parser.add_argument('-n', '--name',
      help='Name tag to be atached to the instance.')
    
    parser.add_argument('--type',
      default='t2.medium',
      help='instance type. [t2.medium]')
    
    parser.add_argument('--ami',
      default='ami-60b6c60a',
      help='AMI ID to use. [ami-60b6c60a : Amazon Linux AMI 2015.09.1 (HVM), SSD Volume Type]')
    
    parser.add_argument('--keypair',
      default='_default',
      help='Keypair to use. [_default]')
    
    parser.add_argument('--iamrole',
      default='bootstrap',
      help='IAM role to attach with the the instance. [bootstrap]')
    
    parser.add_argument('--rootsize',
      default=50,
      type=int,
      help='Root volume size in GB. [50 GB]')
    
    parser.add_argument('--ebs',
      type=int,
      help='Size (GB) of EBS volume to attach to the instance. Specify non-zero value to attach an EBS.')
    
    parser.add_argument('--securitygroup',
      default='default-security-group',
      help='Security Group for the instance. Group base-global-private, which opens SSH access is already added by default). [default-security-group]')

    parser.add_argument('--chefversion',
      default='12.5.1',
      help='Chef client version to install.')

    parser.add_argument('-v', '--version',
      action='version',
      version='%(prog)s 1.0')
    
    args = parser.parse_args()

    launchInstance('us-east-1',
      args.rootsize,
      args.role,
      args.env,
      args.ami,
      args.keypair,
      args.type,
      args.placement,
      args.securitygroup,
      args.iamrole,
      args.ebs,
      args.product,
      args.project,
      args.name,
      args.chefversion)
