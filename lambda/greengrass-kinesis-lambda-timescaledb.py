import base64
import json
import psycopg2
import psycopg2.extras
import os
import io
import datetime
import boto3
from botocore.exceptions import ClientError

import time
from typing import Iterator, Optional, Any, Dict
import io

DB_DATABASE='YOUR-DATABASE'
DB_HOST='YOUR-HOST'
DB_PORT='YOUR-PORT'

def get_secret():

    # Get secrets from secret manager.
    secret_name = "lambda-timescaledb-dev"
    region_name = "eu-west-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret

    


class StringIteratorIO(io.TextIOBase):
    def __init__(self, iter: Iterator[str]):
        self._iter = iter
        self._buff = ''

    def readable(self) -> bool:
        return True

    def _read1(self, n: Optional[int] = None) -> str:
        while not self._buff:
            try:
                self._buff = next(self._iter)
            except StopIteration:
                break
        ret = self._buff[:n]
        self._buff = self._buff[len(ret):]
        return ret

    def read(self, n: Optional[int] = None) -> str:
        line = []
        if n is None or n < 0:
            while True:
                m = self._read1()
                if not m:
                    break
                line.append(m)
        else:
            while n > 0:
                m = self._read1(n)
                if not m:
                    break
                n -= len(m)
                line.append(m)
        return ''.join(line)

def clean_csv_value(value: Optional[Any]) -> str:
    if value is None:
        return r'\N'
    return str(value).replace('\n', '\\n')

print('Loading function')
#datavalue = '{"propertyAlias":"SM-OpcUaPlcServer1/DeviceSet/PLC/Resources/CPU/GlobalVars/::DD3","propertyValues":[{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711314,"offsetInNanos":577000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711315,"offsetInNanos":578000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711313,"offsetInNanos":575000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711316,"offsetInNanos":78000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711313,"offsetInNanos":75000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711312,"offsetInNanos":574000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711315,"offsetInNanos":77000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711311,"offsetInNanos":573000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711314,"offsetInNanos":76000000},"quality":"GOOD"},{"value":{"stringValue":"TechnipFMC"},"timestamp":{"timeInSeconds":1648711312,"offsetInNanos":73000000},"quality":"GOOD"}]}'
def connect_database(secret_string):
    db_name = DB_DATABASE
    db_host = DB_HOST
    db_port = DB_PORT
    db_user = secret_string['DB_USER']
    db_pass = secret_string['DB_PASS']
    
    print(f"Establish connection with server {db_host} on port {db_port}")

    try:
        conn = psycopg2.connect(
            user=db_user, 
            database=db_name, 
            host=db_host,
            password=db_pass, 
            port=db_port)
        conn.autocommit = True
    except Exception as err:
        print(f"Ops! an error has occured while trying to connect to database on server {host} {err}")
        print(f"Exception TYPE: {type(err)}")
    return conn
    

def get_payload(datavalue):
        
        payload_list = []
        data = json.loads(datavalue)
        data_property = data['propertyAlias'].split('/')
        device_name = data_property[0]
        tag_name = data_property[-1]
        data_payload = data['propertyValues']
        #print(f"Device: {device_name}, tag: {tag_name}, data: {data_payload}")
        #print(type(data_payload))
        print(f"opcuapath: {data['propertyAlias']}")


        for row in data_payload:
            value_dict = row['value']
            for key in value_dict:
                typeValue=key
                value = value_dict[key]
            timestamp= row['timestamp']['timeInSeconds']
            quality= row['quality']
            #print(f"device: {device_name}, tag: {tag_name}, valuetype: {typeValue} value: {value}, timestamp: {timestamp}, quality: {quality}")
            
            # Creating my dictionary
            payload = {}
            payload['device']=device_name
            payload['tag']=tag_name
            payload['typeValue']=typeValue
            payload['value']=value
            payload['quality']=quality
            payload['timestamp']=datetime.datetime.fromtimestamp(timestamp).strftime('%c')
            payload['epoch']=timestamp
            payload_list.append(payload)
            #print(timestamp, device_name, tag_name, typeValue, value, quality)

        return payload_list, typeValue
        

def clean_csv_value(value: Optional[Any]) -> str:
    if value is None:
        return r'\N'
    return str(value).replace('\n', '\\n')


def copy_string_iterator(connection, payload_type, beers: Iterator[Dict[str, Any]]) -> None:
    try:
        with connection.cursor() as cursor:
            beers_string_iterator = StringIteratorIO((
                '|'.join(map(clean_csv_value, (
                    beer['timestamp'],
                    beer['device'],
                    beer['tag'],
                    beer['typeValue'],
                    beer['value'],
                    beer['quality'],
                ))) + '\n'
                for beer in beers
            ))
            columns=('time', 'device', 'tag', 'typevalue', payload_type , 'quality')
            cursor.copy_from(beers_string_iterator, 'metrics', sep='|', columns=columns)
    except Exception as err:
        print(f"Ops! an error has occured while trying to COPY data {err}")
        print(f"Exception TYPE: {type(err)}")

def insert_data(connection, payloads):
    try:
        with connection.cursor() as cursor:
            for payload in payloads:
                print(payload)
                cursor.execute(f"INSERT INTO metrics (time, device, tag, typevalue, {payload['typeValue']}, quality) VALUES (\
                        to_timestamp({payload['epoch']}),\
                        '{payload['device']}',\
                        '{payload['tag']}',\
                        '{payload['typeValue']}',\
                        '{payload['value']}',\
                        '{payload['quality']}');\
                        ")
        cursor.close()
    except Exception as err:
        print(f"Ops! an error has occured while trying to INSERT data {err}")
        print(f"Exception TYPE: {type(err)}")

def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))
    
    # Getting database credentials from secret manager
    secret_string = get_secret()
    
    # Connecting to the database
    conn = connect_database(json.loads(secret_string))

    for record in event['Records']:
        try:
            # Kinesis data is base64 encoded so decode here
            payload = base64.b64decode(
                record['kinesis']['data']).decode('utf-8')
            
            #For test purpose
            #payload = datavalue
            #print(f"Decoded payload type {type(payload)}: {payload}")
    
            # Sending data to timescaledb
            payload, payload_type = get_payload(payload)
            print(payload)

            # Use INSERT command for simplicity
            #insert_data(conn, payload)

            # Use COPY command to improve time and memory usage
            # Ref.https://hakibenita.com/fast-load-data-python-postgresql
            copy_string_iterator(conn, payload_type, payload)
            print(f"Able to write payload to database!!!!")

        except ValueError:
            print(f"Not able to decode {record['kinesis']['data']}")
        except:
            print("Unexpected error")
    return 'Successfully processed {} records.'.format(len(event['Records']))


if __name__ == '__main__':

    # Getting database credentials from secret manager
    secret_string = get_secret()

    # Connecting with database
    conn = connect_database(json.loads(secret_string))
    payload, payload_type = get_payload(datavalue)
    print(payload)

    # Use INSERT command for simplicity
    #insert_data(conn, payload)

    # Use COPY command to improve time and memory usage
    copy_string_iterator(conn, payload_type, payload)



