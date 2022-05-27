# Load Python libraries
import json
import os
import csv
from opcua import Client
from opcua import ua
from opcua import Subscription
import opcua.ua.uaerrors as uaerrors
import boto3
import pandas as pd
import logging
import datetime

# Load stream manager library
from stream_manager import (
    ExportDefinition,
    KinesisConfig,
    MessageStreamDefinition,
    ReadMessagesOptions,
    ResourceNotFoundException,
    StrategyOnFull,
    StreamManagerClient,
    StreamManagerException
)

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Controls
PUBLISH_TO_IOTCORE = False
PUBLISH_TO_STREAM = True
STORE_SEQUENCE_NUMBER = False
STORE_TYPE = True

# Greengrass Stream Manager configuration
STREAM_NAME_REAL = "SomeStream1"
STREAM_NAME_ALL = "SomeStream1"
KNS_NAME = "Foo1"

# Create a client for the Greengrass stream manager
while True:
    try:
        streamclient = StreamManagerClient()
    except Exception as e:
            logger.error(f"General exception error: {e}")
    else:
        print('Stream Manager Connected')
        break

current_streams = streamclient.list_streams()

if STREAM_NAME_REAL in current_streams:
    try:
        streamclient.delete_message_stream(stream_name=STREAM_NAME_REAL)
        logger.info("Stream Deleted", STREAM_NAME_REAL)
    except ResourceNotFoundException:
        pass
    except Exception as e:
        logger.error(f"General exception error: {e}")
        pass

if STREAM_NAME_ALL in current_streams:
    try:
        streamclient.delete_message_stream(stream_name=STREAM_NAME_ALL)
        logger.info("Stream Deleted", STREAM_NAME_ALL)
    except ResourceNotFoundException:
        pass
    except Exception as e:
        logger.error(f"General exception error: {e}")
        pass

exports = ExportDefinition(
                    kinesis=[
                        KinesisConfig(
                            identifier="KinesisExport_" + STREAM_NAME_ALL,
                            kinesis_stream_name=KNS_NAME,
                            batch_size =2)
                            ])

try:
    logger.info("Creating stream: " + STREAM_NAME_REAL + ","+ STREAM_NAME_ALL)
    # The LocalDataStream is low priority source for incoming sensor data and
    # aggregator function.
    streamclient.create_message_stream(
            MessageStreamDefinition(
                name=STREAM_NAME_ALL,
                strategy_on_full=StrategyOnFull.OverwriteOldestData,
                export_definition=exports
            )
        )
    logger.info("Stream created: " + STREAM_NAME_ALL)
    print("stream created:" + STREAM_NAME_ALL)

except StreamManagerException as e:
    logger.error(f"Error creating message stream: {e}")
    pass
except Exception as e:
    logger.error(f"General exception error: {e}")
    pass


# Utils
def is_number(x):
    try:
        float(x)
        return True
    except ValueError:
        return False

def is_boolean(x):
    try:
        if x.lower() in ['true', 'false']:
            return True
        else:
            return False
    except:
        return False

# Tells kinesis how to handle changes
def publish_datachange_worker(nodeid, sourcetime, val, tag_list):

    if is_number(val):
        value = float(val)
    elif is_boolean(val):
        if val.lower() == 'true':
            value = float(1.0) # True
        else:
            value = float(0.0) # False
    else:
        logger.error('Received message which cannot be casted to float: ' + val+' node: '+nodeid)

        pass

    target_tag = [item for item in tag_list if item['node']==nodeid][0]
    topic = 'real_time'
    measurement = target_tag['measurements']
    device = target_tag['device']
    unit = target_tag['unit']
    
    if str(val) != 'None':
        message = {
            'node': nodeid, #nodeid.Identifier
            'EVENT_TIME': sourcetime,
            'device': device,
            'topic': topic,
            'measurement': measurement,
            'unit': unit,
            'VAL': value
                    }


        try:
            sequence_number = streamclient.append_message(STREAM_NAME_ALL, data=json.dumps(message).encode("utf-8") )
            print('write to stream manager', sequence_number,message)

        except Exception as e:
            logger.error('Failed to publish data change: ' + nodeid + ': ' + repr(e))

class SubHandler(object):

# Writing the tag values to file - name,value,timestamp
    def datachange_notification(self, node, val, data):
        global tag_list
        publish_datachange_worker( node.nodeid.to_string(), data.monitored_item.Value.SourceTimestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), str(val),tag_list )
        #output_file.write("{},{},{}\n".format(node.nodeid.Identifier, val,data.monitored_item.Value.SourceTimestamp))


def run_writing():

    # connect to OPC UA Server
    try:
        client = Client("opc.tcp://172.22.51.251:4840") #Client("opc.tcp://10.0.143.208:62541") #Client("opc.tcp://10.163.224.24:49320")
        client.connect()
        logger.info("OPCUA Connected")
        print("opc_ua Connected")
    except Exception as e:
        logger.error(f"OPC UA Connection failed on {e}")

    global tag_list

    ##read tag file 
    s3_client = boto3.client('s3')

    bucket_name = "marcel-experiments" 
    key_name = "greengrass/csv/greengrass.csv"
    obj = s3_client.get_object(Bucket = bucket_name, Key = key_name)

    df_tags = pd.read_csv(obj['Body'], index_col=0)
    print(df_tags.shape)
    tag_list = df_tags.to_dict('records')
    
    print("total tags are: ", len(tag_list[:]))
    logger.info(tag_list[:])
    nodes=[item['node'] for item in tag_list]
    
    ##Get the node names from the raw names
    processed_nodes = []
    for node in nodes:
        processed_nodes.append(client.get_node("{}".format(node)))

    print('total processed notes are:', len(processed_nodes))

    ##Defining the subscription - tell OPC UA how frequently to send subcribed messages (10 sec)
    handler = SubHandler()
    sub = client.create_subscription(10000, handler)
    handle = sub.subscribe_data_change(processed_nodes)


# Main loop
run_writing()

# handler is called when a message is received via a subscription
def lambda_handler(event, context):
    logger.error("This lambda is a long-running lambda and will ignore incoming events. Received event: " + str(event))