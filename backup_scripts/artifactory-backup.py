#!/usr/bin/env python
import logging
import math
import mimetypes
import os
import time
import requests
import json
import socket
import datetime
from multiprocessing import Pool,cpu_count

try:
    import argparse
except ImportError:
    print "ERROR: Please install 'argparse' using 'pip install argparse' or 'easy_install argparse'"
    sys.exit(2)

try:
    import boto
    from boto.s3.connection import S3Connection
except ImportError:
    print "ERROR: Please install 'boto' using 'pip install boto' or 'easy_install boto'"
    sys.exit(2)

try:
    from filechunkio import FileChunkIO
except ImportError:
    print "ERROR: Please install 'FileChunkIO' using 'pip install FileChunkIO' or 'easy_install FileChunkIO'"
    sys.exit(2)

try:
    from daemonize import Daemonize
except ImportError:
    print "ERROR: Please install 'daemonize' using 'pip install daemonize' or 'easy_install daemonize'"
    sys.exit(2)


def valid_module(module):
    try:
        import module
    except ImportError:
        print 'ERROR: Please install ' + module + ' using pip or easy_install.'
        sys.exit(2)


slack_webhook_url = 'https://hooks.slack.com/services/CCCCCCCC/HHHHHHHHH/HHHHJJJJJHHHH'
channel = '#testnotifs'
username = 'The Backup Man'
application = 'Artifactory'
icon_url = 'https://s3.amazonaws.com/backup.jpg'
pid = '/var/log/artifactory.s3-backup.pid'


def slack(color, status):
    '''
    Notifies slack.
    '''
    message = 'Application Name :: ' + application
    payload = { 'channel': channel,
    'username': username,
                'text': 'Backup status :: ' + status ,
                'icon_url': icon_url,
                'attachments': [ {
                  'fallback': event_title,
                  'color': color,
                  'fields': [
                    {
                        'title': event_title,
                        'value': event_value,
                        'short': 'false'
                    }
                  ]
                } ]
               }
    r = requests.post(slack_webhook_url, data=json.dumps(payload))


suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
def humansize(nbytes):
    '''
    Converts bytes to human readable values.
    '''
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def valid_file(filepath):
    '''
    Checks if input file is present or not.
    '''
    if not os.path.isfile(filepath):
      msg = 'Input file ' + filepath + ' not present.'
      raise argparse.ArgumentTypeError(msg)
    return filepath


def _upload_part(bucketname, aws_key, aws_secret, multipart_id, part_num,
    source_path, offset, bytes, amount_of_retries=10):
    '''
    Uploads a part with retries.
    '''
    def _upload(retries_left=amount_of_retries):
        try:
            logging.info('Start uploading part #%d ...' % part_num)
            conn = S3Connection(aws_key, aws_secret)
            bucket = conn.get_bucket(bucketname)
            for mp in bucket.get_all_multipart_uploads():
                if mp.id == multipart_id:
                    with FileChunkIO(source_path, 'r', offset=offset,
                        bytes=bytes) as fp:
                        mp.upload_part_from_file(fp=fp, part_num=part_num)
                    break
        except Exception, exc:
            if retries_left:
                _upload(retries_left=retries_left - 1)
            else:
                logging.info('... Failed uploading part #%d' % part_num)
                raise exc
        else:
            logging.info('... Uploaded part #%d' % part_num)

    _upload()


def upload(bucketname, aws_key, aws_secret, source_path, keyname, parallel_processes,
    acl='private', headers={}, guess_mimetype=True):
    '''
    Parallel multipart upload.
    '''
    conn = S3Connection(aws_key, aws_secret)
    bucket = conn.get_bucket(bucketname)

    if guess_mimetype:
        mtype = mimetypes.guess_type(keyname)[0] or 'application/octet-stream'
        headers.update({'Content-Type': mtype})

    mp = bucket.initiate_multipart_upload(keyname, headers=headers)

    source_size = os.stat(source_path).st_size
    logging.info('Source Size : %s ...' % humansize(source_size))
    bytes_per_chunk = max(int(math.sqrt(5242880) * math.sqrt(source_size)),
        5242880)
    logging.info('Bytes per chunk : %s...' % humansize(bytes_per_chunk))
    chunk_amount = int(math.ceil(source_size / float(bytes_per_chunk)))
    logging.info('Number of chunks : %d ...' % chunk_amount)

    pool = Pool(processes=parallel_processes)
    for i in range(chunk_amount):
        offset = i * bytes_per_chunk
        remaining_bytes = source_size - offset
        bytes = min([bytes_per_chunk, remaining_bytes])
        part_num = i + 1
        pool.apply_async(_upload_part, [bucketname, aws_key, aws_secret, mp.id,
            part_num, source_path, offset, bytes])
    pool.close()
    pool.join()

    if len(mp.get_all_parts()) == chunk_amount:
        mp.complete_upload()
        key = bucket.get_key(keyname)
        key.set_acl(acl)
    else:
        mp.cancel_upload()


def sha256_file(file_path, chunk_size=65336):
    '''
    Gets the sha 256 checksum of a file.
    '''
    # Read the file in small pieces, so as to prevent failures to read particularly large files.
    # Also ensures memory usage is kept to a minimum. Testing shows default is a pretty good size.
    logging.info('Generating sha256 checksum ...')
    assert isinstance(chunk_size, int) and chunk_size > 0
    import hashlib
    import functools
    digest = hashlib.sha256()
    with open(file_path, 'rb') as f:
        [digest.update(chunk) for chunk in iter(functools.partial(f.read, chunk_size), '')]
    logging.info('Generated sha256 checksum is ' + digest.hexdigest())
    return digest.hexdigest()


def getKey(key):
    '''
    Returns timestampped file name.
    '''
    return key.rsplit('.', 1)[0] + '_' + time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()) + '.' + key.rsplit('.', 1)[1]


def backup():
    '''
    Backs up a file to AWS S3, utilizing python's multiprocessing module.
    '''
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='/var/log/artifactory.s3-backup.log', level=logging.INFO)

    parser = argparse.ArgumentParser(description='''Uploads large files to AWS S3.

Required arguments are -f/--file, file to upload and -k/--key ,object key in s3. Default bucket is set as 'backups'.
Override by using -b/--bucket. Defaults are indicated in [].
        ''',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    required = parser.add_argument_group('required arguments')
    required.add_argument('-f', '--file', required=True, type=valid_file,
        help='location file to upload')
    required.add_argument('-k', '--key', required=True,
        help='bucket subdirectory to upload to.',)
    parser.add_argument('-b', '--bucket', default='backups',
        help='s3 bucket to upload to. [backups]')
    parser.add_argument('-r', '--region', default='us-east-1',
        help='AWS S3 region to connect to. [us-east-1]')
    parser.add_argument('-p', '--parallel', default=cpu_count(), type=int,
        help='Number of parallel upload processes to spawn. [Number of CPU cores on the instance.]')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()

    aws_access_key = '*************************'
    aws_secret_access_key = '*******************************************'
    start = time.time()
    logging.info('*** Starting Remote Backup to S3 ****')
    key_name = getKey(args.key)
    upload(args.bucket, aws_access_key, aws_secret_access_key, args.file, key_name, args.parallel, acl='private', headers={}, guess_mimetype=True)
    f = open(args.file + '.sha256.checksum','w')
    f.write(sha256_file(args.file))
    f.close()
    logging.info('Uploading checksum file.')
    upload(args.bucket, aws_access_key, aws_secret_access_key, args.file + '.sha256.checksum', key_name + '.sha256.checksum', args.parallel, acl='private', headers={}, guess_mimetype=True)
    logging.info('Elapsed Time (HH:MM:SS) :: ' + str(datetime.timedelta(seconds=time.time() - start)))
    logging.info('Removing source file')
    os.remove(args.file)
    logging.info('Removing local checksum file')
    os.remove(args.file + '.sha256.checksum')
    logging.info('*** Backup completed ***')


if __name__ == '__main__':
    '''
    The MAIN function.
    '''
    daemon = Daemonize(app='BackupMan',pid=pid, action=backup)
    daemon.start()
