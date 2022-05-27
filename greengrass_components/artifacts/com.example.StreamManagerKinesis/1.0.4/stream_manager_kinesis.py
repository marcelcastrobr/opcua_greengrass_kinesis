"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""


import asyncio
import logging
import random
import time
import sys
import datetime

from stream_manager import (
    ExportDefinition,
    KinesisConfig,
    MessageStreamDefinition,
    ReadMessagesOptions,
    ResourceNotFoundException,
    StrategyOnFull,
    StreamManagerClient,
)

# This example will create a Greengrass StreamManager stream called "SomeStream".
# It will then start writing data into that stream and StreamManager will
# automatically export the written data to a Kinesis Data Stream called "MyKinesisStream".
# This example will run forever, until the program is killed.

# The size of the StreamManager stream on disk will not exceed the default (which is 256 MB).
# Any data appended after the stream reaches the size limit, will continue to be appended, and
# StreamManager will delete the oldest data until the total stream size is back under 256MB.
# The Kinesis Data Stream in the cloud has no such bound, so all the data from this script
# will be uploaded to Kinesis and you will be charged for that usage.


def main(logger):
    try:
        stream_name = "SomeStream1"
        kinesis_stream_name = "Foo1"

        # Create a client for the StreamManager
        client = StreamManagerClient()

        message = f"StreamManagerKinesis: able to instantiate client!"
        logger.info(message)

        # Try deleting the stream (if it exists) so that we have a fresh start
        try:
            client.delete_message_stream(stream_name=stream_name)
        except ResourceNotFoundException:
            pass
        except Exception as e:
            logger.error(f"General exception error while trying to execute delete_message_stream: {e}")
            pass

        exports = ExportDefinition(
            kinesis=[
                KinesisConfig(
                    identifier="KinesisExport" + stream_name, 
                    kinesis_stream_name=kinesis_stream_name,
                    batch_size =2
                    )]
        )
        try:
            logger.info("Creating stream: " + stream_name)
            client.create_message_stream(
                MessageStreamDefinition(
                    name=stream_name, 
                    strategy_on_full=StrategyOnFull.OverwriteOldestData, 
                    export_definition=exports
                )
            )
            logger.info("Stream created: " + stream_name)
        except StreamManagerException as e:
            logger.error(f"Error creating message stream: {e}")
            pass
        except Exception as e:
            logger.error(f"General exception error: {e}")
            pass


    except asyncio.TimeoutError:
        logger.exception("Timed out while executing")
    except Exception:
        logger.exception("Exception while running")
    finally:
        # Always close the client to avoid resource leaks
        if client:
            client.close()


logging.basicConfig(level=logging.INFO)
# Start up this sample code
main(logger=logging.getLogger())
