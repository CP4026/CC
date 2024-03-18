from flask import Flask, request
import threading
import os
import boto3
import base64
import time

app = Flask(__name__)
res = dict()
amiId = 'ami-031291c88603471ae'
awsAccessKeyId = 'AKIAW3MEECIEVV73MZHY'
awsSecretAccessKey = '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'
region = 'us-east-1'
inputQueue = 'https://sqs.us-east-1.amazonaws.com/471112880649/1229143775-req-queue'
outputQueue = 'https://sqs.us-east-1.amazonaws.com/471112880649/1229143775-resp-queue'
ec2Client = boto3.client('ec2', region_name=region, aws_access_key_id=awsAccessKeyId, aws_secret_access_key=awsSecretAccessKey)
sqsClient = boto3.client('sqs', region_name=region, aws_access_key_id=awsAccessKeyId, aws_secret_access_key=awsSecretAccessKey)
autoscalingClient = boto3.client('autoscaling', region_name='us-east-1', aws_access_key_id=awsAccessKeyId, aws_secret_access_key=awsSecretAccessKey)


@app.route("/",methods=["POST"])
def sendToRequestQueue():
    output = None
    print(request.files)
    if 'inputFile' in request.files:
        img = request.files['inputFile']
        firstName = str(img).split(" ")[1][1:][:-1]
        print(firstName)
        if firstName != '':
            extension = os.path.splitext(firstName)[1]
            print(extension)
            byteform=base64.b64encode(img.read())
            value = str(byteform, 'ascii')
            body=firstName.split('.')[0] + " " + value
            print(body)
            response = sqsClient.send_message(QueueUrl=inputQueue, MessageBody=body)
            print(response)
            print(firstName.split('.')[0])
            try:
                output  = getResponse(firstName.split('.')[0])
                print("OUTPUT")
                print(output)
                return output

            except Exception:
                return "Error!"
        else :
            return "Error!"
    else:
        return "Error! No file found"

def getResponse(image) :
    while True:
        maxMessages = 10
        all = 'All'
        if image in res.keys():
            return res[image]
        response = sqsClient.receive_message(
            QueueUrl=outputQueue,
            MaxNumberOfMessages=maxMessages,
            MessageAttributeNames=[all],
        )
        if 'Messages' in response:
            message = response['Messages']
            for msg in message:
                body = msg['Body']
                print(body)
                res_image = body.split(":")[0]
                print("result image: ")
                print(res_image.split(".")[0])
                print(res_image)
                res[res_image] = body
                sqsClient.delete_message(QueueUrl = outputQueue, ReceiptHandle = msg['ReceiptHandle'])
                if res_image.split(".")[0] == image :
                    return res[res_image]

def getTotalMessages(url):
    response = sqsClient.get_queue_attributes(QueueUrl=url, AttributeNames=['ApproximateNumberOfMessages'])
    return int(response['Attributes']['ApproximateNumberOfMessages'])

def scaling():
    while True:
        numberOfMessages = getTotalMessages(inputQueue)
        if numberOfMessages > 0:
            capacity = min(numberOfMessages, 19) 
        else:
            capacity = 0

        runningInstances = ec2Client.describe_instances(
            Filters=[
                {'Name': 'image-id', 'Values': [amiId]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )['Reservations']
        totalRunningInstances = sum(len(reservation['Instances']) for reservation in runningInstances)

        numberOfInstancesToLaunch = max(0,capacity - totalRunningInstances)
        user_data_script = """#!/bin/bash
        # Add commands to install dependencies and run app.py here
        sudo pip3 install boto3
        sudo pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        cd /home/ubuntu/CC
        python3 app.py 
        """
        instanceIds = []
        for _ in range(numberOfInstancesToLaunch):
            response = ec2Client.run_instances(
                ImageId=amiId,
                InstanceType='t2.micro',
                MinCount=1,
                MaxCount=1,
                UserData=user_data_script,
                TagSpecifications=[
                {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'app-tier-instance-'+str(_+totalRunningInstances+1)
                    },
                ]
                }
                ]       
            )
            instance_id = response['Instances'][0]['InstanceId']
            instanceIds.append(instance_id)
            print("Launched instance - " + str(_+totalRunningInstances+1) )
        
        if numberOfInstancesToLaunch>0:  
            waiter = ec2Client.get_waiter('instance_running')
            waiter.wait(InstanceIds=instanceIds)
            print("Currently all instances are running")
        
        numberOfInstancesToTerminate = max(totalRunningInstances - capacity, 0)
        for reservation in runningInstances:
            for instance in reservation['Instances']:
                if numberOfInstancesToTerminate > 0:
                    ec2Client.terminate_instances(InstanceIds=[instance['InstanceId']])
                    print(f"Terminated instance - {instance['InstanceId']}")
                    numberOfInstancesToTerminate -= 1

        print("... auto scaling ...")
        time.sleep(5)

scale_thread = threading.Thread(target=scaling)
scale_thread.daemon = True
scale_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
    