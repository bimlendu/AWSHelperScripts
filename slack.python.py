#!/usr/bin/python
'''
POST msg to Slack.
'''
import sys
import requests
import json
import os
import socket

role = 'webc-paperless'
slack_webhook_url = 'https://hooks.slack.com/services/JHFJDFGSFJ/HHFJHJFFHF/kjhfkjgdsggsdgjg'
channel = '#channelName'
username = 'TheMessenger'

def slack(color, event):
    

    message = 'Deployment status :: ' + os.environ['APPLICATION_NAME']
    payload = { 'channel': channel,
                'username': username,
                'text': message,
                'icon_url': 'http://img.stackshare.io/service/1888/aws-codedeploy.png',
                'attachments': [ {
                  'fallback': os.environ['APPLICATION_NAME'] + ', ' + os.environ['DEPLOYMENT_GROUP_NAME'] + ', ' + os.environ['DEPLOYMENT_ID'] + ', ' + os.environ['LIFECYCLE_EVENT'],
                  'color': color,
                  'fields': [
                    {
                        'title': 'Application Name',
                        'value': os.environ['APPLICATION_NAME'],
                        'short': 'false'
                    },
                    {
                        'title': 'Deployment Group Name',
                        'value': os.environ['DEPLOYMENT_GROUP_NAME'],
                        'short': 'false'
                    },
                    {
                        'title': 'Deployment ID',
                        'value': os.environ['DEPLOYMENT_ID'],
                        'short': 'false'
                    },
                    {
                        'title': 'LifeCycle Event',
                        'value': os.environ['LIFECYCLE_EVENT'],
                        'short': 'false'
                    },
                    {
                        'title': 'Deployment Event',
                        'value': event + ' ' + role,
                        'short': 'false'
                    },
                    {
                        'title': 'Machine Details',
                        'value': socket.gethostname() + ' : ' + socket.gethostbyname(socket.gethostname()),
                        'short': 'false'
                    }
                  ]
                } ]
            }
    r = requests.post(slack_webhook_url, data=json.dumps(payload))

if __name__ == "__main__":
    slack('good', 'tomcat restarted successfully')
