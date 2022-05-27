# Moving industrial IoT data to the cloud

> This repository is a working in progress tutorial.



## Architecture

![image-20220525145903714](README.assets/image-20220525145903714.png)



## Components

### Industrial IoT Data (OPCUA)

**OPC Unified Architecture** (**OPC UA**) is a cross-platform, open-source, IEC62541 standard for data exchange from sensors to cloud applications developed by the [OPC Foundation](https://en.wikipedia.org/wiki/OPC_Foundation).

In this tutorial we use **[node-opcua](https://github.com/node-opcua/node-opcua)**, an implementation of an OPC UA stack fully written in Typescript for NodeJS.

#### OPCUA-server

##### installing node-opcua as a node package

```bash
$ mkdir mytest
$ cd mytest
$ npm init 
$ npm install node-opcua --unsafe-perms
```

##### installing node-opcua samples as a node package

```bash
$ mkdir myopcuaserver
$ cd myopcuaserver
$ npm init
$ npm install node-opcua-samples --unsafe-perms
$ node ./node_modules/.bin/simple_server
$ node sitewise_workshop_server
```



#### OPCUA-client

```bash
$ node ./node_modules/.bin/simple_client -e "opc.tcp://127.0.0.1:26543" -n="ns=1;s=FanSpeed"
```

Using the node-opcua client through the command above you should be able to see the tag *FanSpeed* from the OPCUA-server.

![image-20220525130839948](README.assets/image-20220525130839948.png)



### AWS IoT Greengrass V2



#### 1 - Create IoT Edge Device

Greengrass can be installed in linux and windows platforms such as EC2 instance and raspberry-pi, linux machine.

In this tutorial, we are going to run IoT Greengrass in a docker contains following the instructions [here](https://docs.aws.amazon.com/greengrass/v2/developerguide/build-greengrass-dockerfile.html).

##### **1.1 - create docker image**

```bash
# Download AWS IoT Greengrass dockerfile package from github https://github.com/aws-greengrass/aws-greengrass-docker/releases
$ wget https://github.com/aws-greengrass/aws-greengrass-docker/archive/refs/tags/v2.5.3.tar.gz 

$ tar -xvzf aws-greengrass-docker-2.5.3.tar.gz
$ cd aws-greengrass-docker-2.5.3
$ docker-compose -f docker-compose.yml build

```

2.5.3 is the *nucleus-version* of greengrass.



##### **1.2 run AWS IoT Greengrass in docker with automatic provisioning.**

Create .env in the aws-greengrass-docker-2.5.3:

```bash
GGC_ROOT_PATH=/greengrass/v2
AWS_REGION=eu-west-1
PROVISION=true
THING_NAME=MyGreengrassCore
THING_GROUP_NAME=MyGreengrassCoreGroup
TES_ROLE_NAME=GreengrassV2TokenExchangeRole
TES_ROLE_ALIAS_NAME=GreengrassCoreTokenExchangeRoleAlias
COMPONENT_DEFAULT_USER=ggc_user:ggc_group
DEPLOY_DEV_TOOLS=true
```



Update your docker-compose.yml file with the following data.

```yml
version: '3.7'
 
services:
  greengrass:
    init: true
    container_name: aws-iot-greengrass
    image: amazon/aws-iot-greengrass:latest
    volumes:
      - /Users/castrma/.aws/credentials:/root/.aws/:ro 
    env_file: .env
    ports:
      - "8883:8883"
```

/Users/castrma/.aws/credentials is the location of the AWS credentials files. You should change accordingly.



You could also create the image yourself from a Dockerfile like:

```yaml
version: '3.7'
 
services:
  greengrass:
    init: true
    container_name: aws-iot-greengrass
    #image: amazon/aws-iot-greengrass:2.5.3-0
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - ./greengrass-v2-credentials:/root/.aws/:ro
    env_file: .env
    ports:
      - "8883:8883"
```



In order to run the docker container, you should run the command:

```bash
$ docker-compose -f docker-compose.yml up -d --build
```



Check your container id using *docker ps*, and access the container running:

```bash
$ docker exec -it dd034cd4aaa1 /bin/bash
```



You can also copy the AWS Greengrass log files using the command:

```bash
$ docker cp dab39303b540:/greengrass/v2/logs /tmp/logs
```



Tips to troubleshoot AWS IoT Greengrass in a Docker container can be found [here](https://docs.aws.amazon.com/greengrass/v2/developerguide/docker-troubleshooting.html).

You should now be able to see your greengrass core device with name "MyGreengrassCore" under AWS IoT -> Greengrass-> Core devices, like:

![image-20220525144155119](README.assets/image-20220525144155119.png)



###### 1.2.1 Installing dependencies

The custom made component that ties Stream Manager with Kinesis is written in python and needs the Stream Manager SDK, which can be installed inside the container with the command:

```bash
$ pip3 install stream_manager
```



#### 2- Attached Components to your deployment



In order to receive opcua messages and overlay them to the cloud, the following components are necessary to be deployed in your greengrass deployment:

- [aws.greengrass.StreamManager](https://eu-west-1.console.aws.amazon.com/iot/home?region=eu-west-1#/greengrass/v2/components/all/aws.greengrass.StreamManager/versions/2.0.14)

- [aws.greengrass.Nucleus](https://eu-west-1.console.aws.amazon.com/iot/home?region=eu-west-1#/greengrass/v2/components/all/aws.greengrass.Nucleus/versions/2.5.4)

- [aws.iot.SiteWiseEdgeCollectorOpcua](https://eu-west-1.console.aws.amazon.com/iot/home?region=eu-west-1#/greengrass/v2/components/all/aws.iot.SiteWiseEdgeCollectorOpcua/versions/2.0.3)

- [aws.iot.SiteWiseEdgePublisher](https://eu-west-1.console.aws.amazon.com/iot/home?region=eu-west-1#/greengrass/v2/components/public/aws.iot.SiteWiseEdgePublisher/versions/2.1.4)

  

The steps to deploy the **StreamManager** are:

- From the Component details page, select the **Deploy** button

![image-20220525144421986](README.assets/image-20220525144421986.png)



Select **Add to existing deployment** Select the ‘Deployment for MyGreengrassCoreGroup’ deployment radio button. Select **Next**

![image-20220525144520812](README.assets/image-20220525144520812.png)



Verify that both `aws.greengrass.StreamManager`, and `aws.greengrass.Cli` are selected.

![image-20220525144717464](README.assets/image-20220525144717464.png)

Select **Deploy** if everything looks OK.

![image-20220525145117055](README.assets/image-20220525145117055.png)



You can now add the **aws.greengrass.Nucleus** and **aws.iot.SiteWiseEdgeCollectorOpcua** and **aws.iot.SiteWiseEdgePublisher**.



### AWS SiteWise Gateway

An [AWS IoT SiteWise gateway](https://docs.aws.amazon.com/iot-sitewise/latest/userguide/gateways-ggv2.htmll) connects to data sources to retrieve your industrial data streams, which in our case is the opcua data. The gateway runs on [AWS IoT Greengrass V2](https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html) as Greengrass components.

#### 1- Create a gateway

![image-20220525154115074](README.assets/image-20220525154115074.png)

No need to have data processing package as we are not doing any transformation to the data on the edge for now.

![image-20220525154211278](README.assets/image-20220525154211278.png)



![image-20220525154341223](README.assets/image-20220525154341223.png)



![image-20220525165724304](README.assets/image-20220525165724304.png)



#### 2- Check Opcua messages on StreamManager

Log files for Greengrass and SiteWise components are stored in the directory `/greengrass/v2/logs`

You can check the opcua messages arriving in the StreamManager component at greengrass/v2/work/aws.greengrass.StreamManager/SiteWise_StreamManager1/, like:

```bash
$ tail -f  greengrass/v2/work/aws.greengrass.StreamManager/SomeStream1/0000000000000000000.log
```

A screenshot of the output looks like:

![image-20220525163536394](README.assets/image-20220525163536394.png)



Some other important log files are:

- **greengrass.log**: Logs for AWS IoT Greengrass
- **aws.iot.SiteWiseEdgeCollectorOpcua.log**: Logs for the SiteWise component which collects data from OPC-UA servers
- **aws.iot.SiteWiseEdgeProcessor.log**: Logs for the SiteWise data processing pack. This logs contains mainly information about downloading and spinning up container.
- **aws.iot.SiteWiseEdgePublisher.log**: Logs for the SiteWise component that sends data to the SiteWise data store in the Cloud.

## Docker Extras for Amazon linux image:

```bash
# For ifconfig
$ yum install net-tools

# For ping
$ yum install iputils 

# To ping the host
$ ping host.docker.internal 
```

