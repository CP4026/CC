import boto3
import logging
import base64
import os
import time
from botocore.exceptions import ClientError

def initializeAws() :
    regionName = 'us-east-1'
    awsAccessKeyId ='AKIAW3MEECIEVV73MZHY'
    awsSecretAccessKey = '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'
    endpoint = 'https://sqs.us-east-1.amazonaws.com'
    requestQueue = 'https://sqs.us-east-1.amazonaws.com/471112880649/1229143775-req-queue'
    responseQueue = 'https://sqs.us-east-1.amazonaws.com/471112880649/1229143775-resp-queue'
    s3InputBucket = "1229143775-in-bucket"
    s3OutputBucket = "1229143775-out-bucket"
    sqs = boto3.client('sqs', aws_access_key_id=awsAccessKeyId, aws_secret_access_key=awsSecretAccessKey, endpoint_url=endpoint, region_name=regionName)
    s3_client = boto3.client('s3', aws_access_key_id=awsAccessKeyId, aws_secret_access_key=awsSecretAccessKey, region_name=regionName)
    s3 = boto3.resource('s3',region_name=regionName,aws_access_key_id=awsAccessKeyId,aws_secret_access_key=awsSecretAccessKey)

    return sqs, s3_client, s3, requestQueue, responseQueue, s3InputBucket, s3OutputBucket

def deleteFromQueue(receipt) :
    sqs.delete_message( QueueUrl = requestQueue, ReceiptHandle = receipt )

def sendToQueue(firstName, message) :
    sqs.send_message( QueueUrl = responseQueue, MessageBody= firstName + ":" + message )

def polling() :

    print("Polling for messages:")
    timestamp = 'SentTimestamp'
    maxMessages = 10
    timeout = 30
    all = 'All'

    try:
        response = sqs.receive_message(
                QueueUrl=requestQueue,
                AttributeNames=[timestamp],
                VisibilityTimeout=timeout,
                MessageAttributeNames=[all],
                MaxNumberOfMessages=maxMessages,
            )

    except Exception:
        return "Error!"

    if 'Messages' in response :
        msg = response['Messages']
        reciept = response['Messages'][0]['ReceiptHandle']
        print(msg)
        deleteFromQueue(reciept)
        return msg
    else :
        time.sleep(1)
        return polling()

def uploadToInputBucket(bucket, file, object) :
    try:
        s3_client.upload_fileobj(file, bucket, object)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def uploadToOutputBucket(s3, image, res) :
    s3.Object(s3OutputBucket, image).put(Body=res)

def start(s3, s3InputBucket):
    value = polling()
    if(value == None or len(value) == 0):
        print('Error!')
        return
    message = value[0]
    firstName , encodedMessage = message['Body'].split()
    firstNameFile = firstName + ".jpg"
    print('file name : ' + firstNameFile)
    decodedVal = base64.b64decode(bytes(encodedMessage, 'ascii'))
    print(decodedVal)

    with open(firstNameFile, "wb") as file:
        file.write(decodedVal)

    with open(firstNameFile, 'rb') as f:
        if uploadToInputBucket(s3InputBucket, f, firstNameFile):
            print("image uploaded")

    # current_dir = os.path.dirname(os.path.abspath(_file_))
    # model_folder_path = os.path.join(current_dir, "model")
    # face_recognition_path = os.path.join(model_folder_path, "face_recognition.py")
    # data_path = os.path.join(model_folder_path, "data.pt")
    stdout = os.popen(f'python3 /Users/chaitanya/Documents/"Project Stuff"/"CC Phase 2"/CSE546-Cloud-Computing/model/face_recognition.py {firstNameFile}')
    result = stdout.read().strip()
    logging.info('result : ' + result)
    print("result " + result)

    with open(firstNameFile, 'rb') as f:
        uploadToOutputBucket(s3, firstName, result)
        sendToQueue(firstName, result)

    print(result)    


if __name__ == "__main__":
    sqs, s3_client, s3, requestQueue, responseQueue, s3InputBucket, s3OutputBucket = initializeAws()
    while True:
        start( s3, s3InputBucket)