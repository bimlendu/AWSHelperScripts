# How to use

## Required arguments
* Server Role :: Chef role of the instance.
* Environment :: Chef environment of the instance.
* Product tag :: Product tag to attach to the instance.
* Project tag :: Project tag to attach to the instance.
* Placement / Availability Zone :: Availability zone to launch the instance in.

## Optional arguments. Defaults are in *italics*.
* Name tag :: Name tag to attach to the instance.
* Instance type :: Type of the instance *[t2.medium]*
* AMI :: AMI ID to use. *[ami-60b6c60a : Amazon Linux AMI 2015.09.1 (HVM), SSD Volume Type]*
* SSH keypair :: Keypair to use. *[_vpc]*
* IAM role :: IAM role to attach with the the instance. *[bootstrap]*
* Root Volume Size :: Root volume size in GB. *[50 GB]*
* EBS Size :: Size (GB) of EBS volume to attach to the instance. Specify non-zero value to attach an EBS.
* Security Group :: Security Group for the instance. *[base-global-private, ec2-web-private]*
* Chef version to use :: Chef client version to install. *[12.5.1]*

## How tags work.

The script *needs* three files, in the same directory where the script is, respectively for each tag type to attach.
* environment.tags
* product.tags
* project.tags

To add a new project/product/environment just add the new item in the file.

All tags added are forced lower case.

```
usage: instance.py [-h] -r ROLE -e ENV -z {us-east-1a,us-east-1b} -p PRODUCT
                   -j PROJECT [-n NAME] [--type TYPE] [--ami AMI]
                   [--keypair KEYPAIR] [--iamrole IAMROLE]
                   [--rootsize ROOTSIZE] [--ebs EBS]
                   [--securitygroup SECURITYGROUP] [--chefversion CHEFVERSION]
                   [-v]

Creates an EC2 instanc.

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


optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Name tag to be atached to the instance.
  --type TYPE           instance type. [t2.medium]
  --ami AMI             AMI ID to use. [ami-60b6c60a : Amazon Linux AMI
                        2015.09.1 (HVM), SSD Volume Type]
  --keypair KEYPAIR     Keypair to use. [_vpc]
  --iamrole IAMROLE     IAM role to attach with the the instance. [bootstrap]
  --rootsize ROOTSIZE   Root volume size in GB. [50 GB]
  --ebs EBS             Size (GB) of EBS volume to attach to the instance.
                        Specify non-zero value to attach an EBS.
  --securitygroup SECURITYGROUP
                        Security Group for the instance. Group base-global-
                        private, which opens SSH access is already added by
                        default). [ec2-web-private]
  --chefversion CHEFVERSION
                        Chef client version to install.
  -v, --version         show program's version number and exit

required arguments:
  -r ROLE, --role ROLE  Instance Chef role. Role format is <service>-<stack> ,
                        eg. webc-bys, etc.
  -e ENV, --env ENV     Instance Chef environment.
  -z {us-east-1a,us-east-1b}, --placement {us-east-1a,us-east-1b}
                        Availability Zone to launch the instance in.
  -p PRODUCT, --product PRODUCT
                        Product tag to attach to the instance.
  -j PROJECT, --project PROJECT
                        Project tag to attach to the instance.

EBS volume created and attached will have to be made usable.
```
