# Domoticz Mqtt Sync plug-in for Domoticz / Plug-in Mqtt Sync pour Domoticz 
#
#   This plug-in synchronizes (part of) devices of a master instance to a slave one
#
#   Functions:
#    	- Allow synchronization of (part of) Domoticz devices on a master instance to a slave one
#   	- Creation/modification/deletion and update of slave devices is automatic
#   	- Changes from slave can be reflected on master, if authorized in device configuration
#
#   More details on README.md
#
#   Flying Domotic -  https://github.com/FlyingDomotic/domoticz-mqtt-sync-plugin.git

"""
<plugin key="domoticz-mqtt-sync" name="MQTT Sync with LAN interface" author="Flying Domotic" version="1.0.0" externallink="https://github.com/FlyingDomoticz/domoticz-mqtt-sync-plugin">
    <description>
      Mqtt Sync plug-in<br/><br/>
      Synchronizes (part of) devices from a master instance to a slave one<br/>
    </description>
    <params>
        <param field="Mode1" label="JSON mapping file to use" width="300px" required="true" default="mqttSync.json"/>
        <param field="Mode5" label="Role" width="100px">
            <options>
                <option label="Master" value="Master" default="true"/>
                <option label="Slave" value="Slave"/>
            </options>
        </param>
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="Extra verbose" value="Verbose+"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug" value="Debug"/>
                <option label="Normal" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
# This line is used by VsCodium when running outside Domoticz environment
try:
    from Domoticz import *
except:
    pass

from urllib.parse import urlparse
import json
import sqlite3
import base64
import variables
from datetime import datetime
import os

# Local MQTT client class
class MqttClient:
    name = ""                       # Name of this client
    address = ""                    # IP address of MQTT server
    port = ""                       # Port of MQTT server
    username = ""                   # Associated username
    password = ""                   # Associated password
    lwtTopic = ""                   # Last Will Topic
    lwtData = ""                    # Last Will data
    lastSubscribedTopics = ""       # Last subscribed topic(s)
    connection = None               # MQTT connection object

    # Class initialization: save parameters and open connection
    def __init__(self, name, address, port, username = None, password = None, lwtTopic = None, lwtData = None):
        marker = makeMarker("__init__", "MqttClient", name, F"{address}, {port}, {username}, {password}, {lwtTopic}, {lwtData}")
        self.name = name
        self.address = address
        self.port = port
        self.username = username
        self.password = password
        self.lwtTopic = lwtTopic
        self.lwtData = lwtData

    # Class default string
    def __str__(self):
        marker = makeMarker("__str__", "MqttClient", self.name)
        if (self.connection != None):
            return str(self.name)
        else:
            return "None"

    # Open MQTT connection at TCP level
    def Open(self):
        marker = makeMarker("Open", "MqttClient", self.name, F"{self.address}:{self.port}")
        if (self.connection != None):
            if self.connection.Connected():
                self.connection.Disconnect()
        Parameters['Username'] = str(self.username)
        Parameters['Password'] = str(self.password)
        if self.username != "":
            Domoticz.Debug(F"{marker} Using {Parameters['Username']}/{Parameters['Password']}")
        self.connection = Domoticz.Connection(Name=self.name, Transport="TCP/IP", Protocol="MQTT", Address=self.address, Port=self.port)
        self.connection.Connect()

    # Connect to MQTT server (or open connction if not active)
    def SendId(self):
        marker = makeMarker("SendId", "MqttClient", self.name)
        if self.connection != None:
            ID = F"Domoticz_{Parameters['Key']}_{Parameters['HardwareID']}_{self.name}_{variables.masterSequence}"
            if self.lwtTopic:
                Domoticz.Log(F"{marker} ID: {ID}, lwtTopic: {self.lwtTopic}, lwtData: {self.lwtData}")
                self.connection.Send({'Verb': 'CONNECT', 'ID': ID, 'WillTopic': self.lwtTopic, 'WillQoS': 0, 'WillRetain': 1, 'WillPayload': self.lwtData})
            else:
                Domoticz.Log(F"{marker} ID: {ID}")
                self.connection.Send({'Verb': 'CONNECT', 'ID': ID})
        else:
            Domoticz.Error(F"{marker} Not initialized, ignoring!!")

    # Send a MQTT Ping message
    def Ping(self):
        marker = makeMarker("Connect", "MqttClient", self.name, ignore=True)
        if self.connection == None:
            Domoticz.Error(F"{marker} Not initialized, Ignoring")
            return
        # Reconnect if master connection has dropped
        if self.connection.Connected():
                self.connection.Send({'Verb': 'PING'})
        elif self.connection.Connecting():
            Domoticz.Debug(F"{marker} Still trying to reconnect to MQTT")
        else:
            Domoticz.Debug(F"{marker} Reconnecting to MQTT")
            self.Open()

    #  Publish a payload on a given topic (and retain flag)
    def Publish(self, topic, payload, retain = 0):
        marker = makeMarker("Publish", "MqttClient", self.name, F"{topic} ({payload})")
        if self.connection == None:
            Domoticz.Error(F"{marker} Not initialized, Ignoring")
            return
        self.connection.Send({'Verb': 'PUBLISH', 'Topic': topic, 'Payload': bytearray(payload, 'utf-8'), 'Retain': retain})

    # Subscribe to topic(s)
    def Subscribe(self, topics):
        marker = makeMarker("Subscribe", "MqttClient", self.name, F"{topics}")
        if self.connection == None:
            Domoticz.Error(F"{marker} Not initialized, Ignoring")
            return
        subscriptionlist = []
        if type(topics).__name__ == "list":
            for topic in topics:
                subscriptionlist.append({'Topic':topic, 'QoS':0})
        else:
                subscriptionlist.append({'Topic':topics, 'QoS':0})
        self.lastSubscribedTopics = topics
        self.connection.Send({'Verb': 'SUBSCRIBE', 'Topics': subscriptionlist})

    # Close MQTT connection
    def Close(self):
        marker = makeMarker("Close", "MqttClient", self.name)
        if self.connection != None:
            if self.connection.Connected():
                self.connection.Disconnect()

# Local HTTP client class
class HttpClient:
    name = ""                       # TCP client name
    address = ""                    # IP address of HTTP server
    port = ""                       # Port of HTTP server
    isHttps = False                 # Is connection using https?
    connection = None               # HTTP connection object

    # Class initialization: save parameters and open connection
    def __init__(self, name, address, port, isHttps):
        marker = makeMarker("__init__", "HttpClient", name, F"{address}, {port}, {isHttps}")
        self.name = name
        self.address = address
        self.port = port
        self.isHttps = isHttps

    # Class default string
    def __str__(self):
        marker = makeMarker("__str__", "HttpClient", self.name)
        if (self.connection != None):
            return str(self.name)
        else:
            return "None"

    # Open HTTP connection at TCP level
    def Open(self):
        marker = makeMarker("Open", "HttpClient", self.name, F"{self.address}:{self.port}")
        if (self.connection != None):
            if self.connection.Connected():
                self.connection.Disconnect()
        if self.isHttps:
            self.connection = Domoticz.Connection(Name=self.name, Transport="TCP/IP", Protocol="HTTPS", Address=self.address, Port=self.port)
        else:
            self.connection = Domoticz.Connection(Name=self.name, Transport="TCP/IP", Protocol="HTTP", Address=self.address, Port=self.port)
        self.connection.Connect()

    # Close HTTP connection
    def Close(self):
        marker = makeMarker("Close", "HttpClient", self.name)

####    Plug-in code    ####

# Compose a marker to display in front of each message
#   Optionally, add a debug line, still optionally with parameters)
def makeMarker(function, module="", instance="", parameters="", ignore=False):
    # Start with module
    marker = module
    # Add instance if not empty
    if instance !="":
        # Add "/" separator if module not empty
        if marker != "":
            marker += "/"
        # Add instance
        marker += instance
    # If module and/or instance given, add "::"
    if marker != "":
        marker += "::"
    # Terminate by function and ":"
    marker += function + ":"
    # Send a debug message if not marked to be ingored
    if not ignore:
        # Add marker and paramaters
        Domoticz.Debug((marker+" "+parameters).strip())
    return marker

# Returns a dictionary value giving a key or default value if not existing
def getValue(dict, key, default=''):
    if dict == None:
        return default
    else:
        if key in dict:
            if dict[key] == None:
                return default
            else:
                return dict[key]
        else:
            return default

# Load name -> IDX correspondance table from list of devices
def loadName2Idx(listOfDevices):
    marker = makeMarker("loadName2Idx")
    variables.name2Idx = {}
    variables.idxList = []
    for device in listOfDevices:
        variables.name2Idx[getValue(device,"Name")] = getValue(device, "idx", "-1")
        variables.idxList.append(getValue(device, "idx", "-1"))
    Domoticz.Log(F"{marker} {len(variables.idxList)} idx and {len(variables.name2Idx)} names loaded")

# Read mapping data and create synchronized devices dictionary
def loadMapping(mappingData):
    marker = makeMarker("loadMapping")
    # Clear dictionary
    variables.syncDevices = {}
    # Read all lines
    for item in mappingData:
        Domoticz.Debug(F"{marker} Analyzing {item}")
        # Load item IDX
        itemIdx = str(getValue(item, "idx"))
        # Does item have a name element?
        itemName = getValue(item,"name")
        if itemName != "":
            # Find idx from name
            itemIdx2 = str(getValue(variables.name2Idx, itemName))
            # Idx corresponding to name found
            if itemIdx2 != "":
                # Do we also have idx specified in item?
                if itemIdx != "":
                    if itemIdx != itemIdx2:
                        Domoticz.Error(F"{marker} {itemName} idx is {itemIdx2} but {itemIdx} also specified in {str(item)} - Keeping idx {itemIdx}")
                else:
                    # Set idx from name
                    itemIdx = itemIdx2
            else:
                # Do we have an idx from item?
                if itemIdx !="":
                    Domoticz.Error(F"{marker} Can't find >{itemName}< for {str(item)} - Using idx {itemIdx}")
                else:
                    Domoticz.Error(F"{marker} Can't find >{itemName}< for {str(item)} - Line ignored!!")
        if itemIdx != "":
            if itemIdx in variables.idxList:
                deviceParams = {}
                deviceParams['allowSlaveUpdate'] = bool(getValue(item, 'allowSlaveUpdate', 'False'))
                variables.syncDevices[itemIdx] = deviceParams
            else:
                Domoticz.Debug(F"{marker} idxList: {variables.idxList}")
                Domoticz.Error(F"{marker} Device idx {itemIdx} is not known for {str(item)} - Line ignored!!")
        else:
            Domoticz.Error(F"{marker} No idx found for {str(item)} - Line ignored!!")
    for line in variables.syncDevices:
        Domoticz.Debug(F"{marker} Result: {line} {variables.syncDevices[line]}")

# Dump plug-in configuration to log
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Log( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Log(F"Device count: {len(Devices)}")
    for x in Devices:
        Domoticz.Log(F"Device: {str(x)} - {str(Devices[x])}")

# Dump MQTT message to log
def DumpMqttMessageToLog(topic, rawmessage, prefix=''):
    message = rawmessage
    Domoticz.Log(prefix+topic+":"+message)

# Dump an HTTP response to log
def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug(F"HTTP Details ({len(httpResp)}):")
    indentStr = ""
    for i in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(F"{indentStr}> '{str(x)}': '{str(httpResp[x])}'")
            else:
                Domoticz.Debug(F"{indentStr}> '{str(x)}':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(F"{indentStr}> {str(x)}")
    else:
        for x in httpResp:
            Domoticz.Debug(F"{indentStr}> '{str(x)}': '{str(httpResp[x])}'")
        
# Replace CR and LF by \r and \n in order to keep log lines structured
def replaceCrLf(message):
    return str(message).replace("\r","\\r").replace("\n","\\n")

# Find a device by key in devices table
def getDevice(deviceKey):
    for device in Devices:
        if (str(Devices[device].DeviceID) == str(deviceKey)) :
            # Return device
            return Devices[device]
    # Return None if not found
    return None

# Get device name
def deviceStr(unit):
    name = "<UNKNOWN>"
    if unit in Devices:
        name = Devices[unit].Name
    return name

# Get next free device Id
def getNextDeviceId():
    nextDeviceId = 1
    while True:
        exists = False
        for device in Devices:
            if (device == nextDeviceId) :
                exists = True
                break
        if (not exists):
            break;
        nextDeviceId = nextDeviceId + 1
    return nextDeviceId

# Decode options fields (as some fields are base64 encoded)
def decodeOptions(options):
    marker = makeMarker("decodedOptions", parameters=F"{options}")
    # Create options dictionary
    decodedOptions = {}
    # If they're some options
    if options != "":
        # Split options separated by ";"
        elements = options.split(";")
        # Analyze each option
        for element in elements:
            # Key and value are separated by a ":"
            parts = element.split(":")
            # Key is first element
            key = parts[0]
            # Value is second, base64 encoded
            value = base64.b64decode(parts[1]).decode("UTF-8")
            decodedOptions[key] = value
    Domoticz.Debug(F"{marker} Decoded {str(decodedOptions)}")
    return decodedOptions

# Load settings
def loadSettings():
    marker = makeMarker("loadSettings")
    # Parse options
    variables.debugging = Parameters["Mode6"]        # Debug mode from plug-in parameters
    DumpConfigToLog()
    if variables.debugging == "Verbose+":
        Domoticz.Debugging(1+2+4+8+16+32+64+128)
    elif variables.debugging == "Verbose":
        Domoticz.Debugging(2+4+8+16)
    elif variables.debugging == "Debug":
        Domoticz.Debugging(2)
    elif variables.debugging == "None":
        Domoticz.Debugging(0)

    variables.runMode = Parameters["Mode5"]
    # Copy run mode to address to have a view of mode in hardware list
    Parameters["Address"] = variables.runMode
    # Are we on master?
    variables.areWeOnMaster = (variables.runMode.lower() !="slave")
    # Json file name (at root of plug-in folder)
    jsonFile = Parameters['HomeFolder'] + Parameters["Mode1"]

    # Load JSON settings
    with open(jsonFile, encoding = 'UTF-8') as configStream:
        try:
            jsonData = json.load(configStream)
        except Exception as e:
            Domoticz.Error(F"{marker} {e} when loading {jsonFile}")
            return
        # Get settings part
        variables.settings = getValue(jsonData, 'settings')
        if not variables.settings:
            # No settings found, exit
            Domoticz.Error(F"{marker} Can't find 'settings' in {jsonFile}")
            return

        inError = False
        # Get settings for Domoticz HTTP
        if variables.areWeOnMaster:
            variables.domoticzOutTopic = getValue(variables.settings, 'masterDomoticzOutTopic', "domoticz/out")
            variables.domoticzUrl = getValue(variables.settings, 'masterDomoticzUrl', "http://127.0.0.1:8080")
            variables.masterMqttHost = getValue(variables.settings, "masterMqttHost")
            if not variables.masterMqttHost:
                Domoticz.Error(F"{marker} Can't find 'settings/masterMqttHost' in {jsonFile}")
                inError = True
            variables.masterMqttPort = getValue(variables.settings, "masterMqttPort")
            if not variables.masterMqttPort:
                Domoticz.Error(F"{marker} Can't find 'settings/masterMqttPort' in {jsonFile}")
                inError = True
            variables.masterMqttUser = getValue(variables.settings, "masterMqttUser")
            variables.masterMqttPassword = getValue(variables.settings, "masterMqttPassword")
            # Get mapping part
            variables.mapping = getValue(jsonData, "mapping")
            if not variables.mapping:
                # No mapping found, exit
                Domoticz.Error(F"{marker} Can't find 'mapping' in {jsonFile}")
                return
        else:
            variables.domoticzUrl = getValue(variables.settings, 'slaveDomoticzUrl', "http://127.0.0.1:8080")
            variables.slaveDevicePrefix = getValue(variables.settings, "slaveDevicePrefix")

        # Get settings used on both instances
        variables.masterName = getValue(variables.settings, "masterName")
        if not variables.masterName:
            Domoticz.Error(F"{marker} Can't find 'settings/masterName' in {jsonFile}")
            inError = True

        variables.slaveName = getValue(variables.settings, "slaveName")
        if not variables.slaveName:
            Domoticz.Error(F"{marker} Can't find 'settings/slaveName' in {jsonFile}")
            inError = True

        # Get settings for Slave MQTT
        variables.slaveMqttHost = getValue(variables.settings, "slaveMqttHost")
        if not variables.slaveMqttHost:
            Domoticz.Error(F"{marker} Can't find 'settings/slaveMqttHost' in {jsonFile}")
            inError = True
        variables.slaveMqttPort = getValue(variables.settings, "slaveMqttPort")
        if not variables.slaveMqttPort:
            Domoticz.Error(F"{marker} Can't find 'settings/slaveMqttPort' in {jsonFile}")
            inError = True

        variables.slaveMqttUser = getValue(variables.settings, "slaveMqttUser")
        variables.slaveMqttPassword = getValue(variables.settings, "slaveMqttPassword")

        # Exit if something not found
        if inError :
            return

        # Parse Domoticz URL
        urlParts = urlparse(variables.domoticzUrl)
        variables.domoticzUsername = urlParts.username
        variables.domoticzPassword = urlParts.password
        variables.domoticzAddress = urlParts.hostname
        variables.domoticzPort = str(urlParts.port)
        variables.domoticzHttps = urlParts.scheme.lower() == "https"

        # Compose other variables
        variables.rootTopic = F"mqttSync/{variables.masterName}2{variables.slaveName}"
        variables.databaseCopyFileName = os.path.join(Parameters['HomeFolder'], "databaseCopy.db")
        variables.masterSequence = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        variables.slaveSequence = variables.masterSequence

    variables.initDone = True

# Connect to MQTT master
def connectToMqttMaster():
    marker = makeMarker("connectToMqttMaster")
    # Connect to master MQTT server
    lwtTopic = F"{variables.rootTopic}/lwt/masterOnMaster"
    lwtData = {}
    lwtData["state"] = "down"
    lwtData["version"] =  variables.pluginVersion
    variables.masterMqttClient = MqttClient(variables.masterConnection, variables.masterMqttHost, variables.masterMqttPort, \
        variables.masterMqttUser, variables.masterMqttPassword, lwtTopic, json.dumps(lwtData))
    variables.masterMqttClient.Open()

# Connect to MQTT slave from Master
def connectToMqttSlaveOnMaster():
    marker = makeMarker("connectToMqttSlaveOnMaster")
    # Connect to slave MQTT server
    lwtTopic = F"{variables.rootTopic}/lwt/slaveOnMaster"
    lwtData = {}
    lwtData["state"] = "down"
    lwtData["version"] =  variables.pluginVersion
    variables.slaveMqttClient = MqttClient(variables.slaveConnection, variables.slaveMqttHost, variables.slaveMqttPort, \
        variables.slaveMqttUser, variables.slaveMqttPassword, lwtTopic, json.dumps(lwtData))
    variables.slaveMqttClient.Open()

# Connect to MQTT slave from Slave
def connectToMqttSlaveOnSlave():
    marker = makeMarker("connectToMqttSlaveOnSlave")
    # Connect to slave MQTT server
    lwtTopic = F"{variables.rootTopic}/lwt/slaveOnSlave"
    lwtData = {}
    lwtData["state"] = "down"
    lwtData["version"] =  variables.pluginVersion
    variables.slaveMqttClient = MqttClient(variables.slaveConnection, variables.slaveMqttHost, variables.slaveMqttPort, \
        variables.slaveMqttUser, variables.slaveMqttPassword, lwtTopic, json.dumps(lwtData))
    variables.slaveMqttClient.Open()

# Load device definition from database copy
def loadDefinitionsFromDb():
    marker = makeMarker("loadDefinitionsFromDb")
    if variables.databaseConnecion != None:
        cursor = variables.databaseConnecion.cursor()
        result = cursor.execute('select ID, Type, SubType, SwitchType, nValue, sValue, Options, LastUpdate, Color, Name from DeviceStatus')
        #          Field #:              0    1      2         3          4       5       6          7         8     9
        for row in result.fetchall():
            idx = str(row[0])
            if idx in variables.syncDevices.keys():
                # Load parameters topics
                fields = {}
                fields["Name"] = row[9]
                fields['Type'] = row[1]
                fields['SubType'] = row[2]
                fields['SwitchType'] = row[3]
                if row[6] != None:
                    fields['Options'] = row[6]
                fields['Sequence'] = variables.masterSequence
                # Save parameters
                variables.syncParameters[idx] = fields
                Domoticz.Debug(F"{marker} syncParameters={idx}:{fields}")
                # Load/update values topics
                fields = variables.syncDevices[idx]
                if "nValue" not in fields:
                    fields['nValue'] = row[4]
                if "sValue" not in fields:
                    fields['sValue'] = row[5]
                if "LastUpdate" not in fields:
                    fields['LastUpdate'] = row[7]
                if "Color" not in fields and row[8] != None and row[8] != "":
                    fields["Color"] = row[8]
                fields['Sequence'] = variables.masterSequence
                # Save last values
                variables.syncDevices[idx] = fields
                Domoticz.Debug(F"{marker} syncDevices={idx}:{fields}")
                # Send updates if slave mqtt connected
                if variables.slaveMqttClient != None:
                    variables.slaveMqttClient.Publish(F"{variables.rootTopic}/{variables.masterValues}/{idx}", json.dumps(fields), retain=1)
        connectToMqttSlaveOnMaster()

# Send next slave update
def sendNextSlaveUpdate():
    marker = makeMarker("sendNextSlaveUpdate", parameters=F"Queue length={len(variables.sendApiUpdateList)}")
    # Is queue empty?
    if len(variables.sendApiUpdateList) == 0:
        # Yes, close connection
        variables.httpClient = None
    else:
        # No, check for client
        if variables.httpClient != None:
            # Client exists, is it connected?
            if variables.httpClient.connection.Connected():
                # Send next slave update 
                sendSlaveUpdate(variables.httpClient.connection)
            else:
                # Client exists, not connected
                prepareSendingSlaveUpdate()
        else:
            # Client don't exists, create it
            prepareSendingSlaveUpdate()
        
# Send parameters and values to MQTT slave after (re)connection
def sendParametersAndValuesToSlave():
    marker = makeMarker("sendParametersAndValuesToSlave")
    for idx in variables.syncParameters.keys():
        if variables.slaveMqttClient != None:
            if variables.slaveMqttClient.connection.Connected():
                variables.slaveMqttClient.Publish(F"{variables.rootTopic}/{variables.masterParameters}/{idx}", \
                    json.dumps(variables.syncParameters[idx]), retain=1)
    for idx in variables.syncDevices.keys():
        if variables.slaveMqttClient != None:
            if variables.slaveMqttClient.connection.Connected():
                variables.slaveMqttClient.Publish(F"{variables.rootTopic}/{variables.masterValues}/{idx}", \
                    json.dumps(variables.syncDevices[idx]), retain=1)

# Subscribe for slave values changes from Master
def subscribeSlaveValuesFromMaster():
    marker = makeMarker("subscribeSlaveValuesFromMaster")
    if variables.slaveMqttClient != None:
        if variables.slaveMqttClient.connection.Connected:
            variables.slaveMqttClient.Subscribe(F"{variables.rootTopic}/{variables.slaveValues}/#")

# Subscribe for master changes on parameters from slave
def subscribeMasterParametersFromSlave():
    marker = makeMarker("subscribeMasterParametersFromSlave")
    if variables.slaveMqttClient != None:
        if variables.slaveMqttClient.connection.Connected:
            variables.slaveMqttClient.Subscribe(F"{variables.rootTopic}/{variables.masterParameters}/#")

# Subscribe for master changes on values from slave
def subscribeMasterValuesFromSlave(idx):
    marker = makeMarker("subscribeMasterValuesFromSlave")
    if variables.slaveMqttClient != None:
        if variables.slaveMqttClient.connection.Connected:
            variables.slaveMqttClient.Subscribe(F"{variables.rootTopic}/{variables.masterValues}/{idx}")

# Request name2idx data (list of devices)
def requestName2IdxData():
    marker = makeMarker("requestName2IdxData")
    if variables.httpClient != None:
        variables.httpClient = None
    # Create HTTP clients for requests
    variables.httpClient = HttpClient(variables.name2IdxConnection, \
        variables.domoticzAddress, variables.domoticzPort, variables.domoticzHttps)
    # Open connection for name2idx request
    variables.httpClient.Open()

# Request a database backup
def requestBackupDatabaseData():
    marker = makeMarker("requestBackupDatabaseData")
    if variables.httpClient != None:
        variables.httpClient = None
    variables.httpClient = HttpClient(variables.backupDatabaseConnection, \
        variables.domoticzAddress, variables.domoticzPort, variables.domoticzHttps)
    # Open connection for database backup request
    variables.httpClient.Open()

# Prepare sending slave update
def prepareSendingSlaveUpdate():
    marker = makeMarker("prepareSendingSlaveUpdate")
    if variables.httpClient != None:
        if variables.httpClient.connection.Connected():
            variables.httpClient = None
    variables.httpClient = HttpClient(variables.sendSlaveUpdateConnection, \
        variables.domoticzAddress, variables.domoticzPort, variables.domoticzHttps)
    # Open connection for database backup request
    variables.httpClient.Open()

# Ask master for getting domoticz/out changes
def askForDomoticzChanges(Connection):
    marker = makeMarker("askForDomoticzChanges")
    # Ask for domoticz/out changes
    if variables.masterMqttClient != None:
        variables.masterMqttClient.Subscribe(variables.domoticzOutTopic)

# Ask Domoticz for device list
def askForDeviceList(Connection):
    marker = makeMarker("askForDeviceList")
    # HTTP API changed since 2023.2, so check for version used
    domVersion = str(Parameters["DomoticzVersion"])
    if (domVersion[:2] == "20" and domVersion >= "2023.2"):
        apiParams = "?type=command&param=getdevices&used=true"
    else:
        apiParams = "?type=devices&used=true"
    if variables.domoticzUsername != "":
        authorizationText = variables.domoticzUsername
        if variables.domoticzPassword != "":
            authorizationText += ":" + variables.domoticzPassword
        authorization = base64.b64encode(authorizationText.encode('ascii')).decode("UTF_8")
        sendData = { 'Verb':'GET',
                        'URL':'/json.htm'+apiParams,
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'Authorization': 'Basic '+authorization, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    else:
        sendData = { 'Verb':'GET',
                        'URL':'/json.htm'+apiParams,
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    Connection.Send(sendData, 0)
    Domoticz.Debug(F"{marker} Send {str(sendData)}")

# Ask Domoticz for Domoticz database copy
def askForBackupDatabase(Connection):
    marker = makeMarker("askForBackupDatabase")
    if variables.domoticzUsername != "":
        authorizationText = variables.domoticzUsername
        if variables.domoticzPassword != "":
            authorizationText += ":" + variables.domoticzPassword
        authorization = base64.b64encode(authorizationText.encode('ascii')).decode("UTF_8")
        sendData = { 'Verb':'GET',
                        'URL': '/backupdatabase.php',
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: */*', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'Authorization': 'Basic '+authorization, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    else:
        sendData = { 'Verb':'GET',
                        'URL': '/backupdatabase.php',
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: */*', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    Connection.Send(sendData, 0)
    Domoticz.Debug(F"{marker} Send {str(sendData)}")

# Send an update command received from slave
def sendSlaveUpdate(Connection):
    # Get next update to send
    apiParams = variables.sendApiUpdateList.pop(0)
    marker = makeMarker("sendSlaveUpdate", parameters=F"Parameters={apiParams}")
    if variables.domoticzUsername != "":
        authorizationText = variables.domoticzUsername
        if variables.domoticzPassword != "":
            authorizationText += ":" + variables.domoticzPassword
        authorization = base64.b64encode(authorizationText.encode('ascii')).decode("UTF_8")
        sendData = { 'Verb':'GET',
                        'URL':'/json.htm'+apiParams,
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'Authorization': 'Basic '+authorization, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    else:
        sendData = { 'Verb':'GET',
                        'URL':'/json.htm'+apiParams,
                        'Headers':{'Content-Type': 'application/json; charset=utf-8', \
                                'Connection': 'keep-alive', \
                                'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                'Host': variables.domoticzAddress+":"+variables.domoticzPort, \
                                'User-Agent':'Domoticz/1.0' }
                    }
    Connection.Send(sendData, 0)
    Domoticz.Debug(F"{marker} Send {str(sendData)}")

# Decode a (remote) command and prepare fields to send to Domoticz API
def decodeOnCommand(Unit, Command, Level, Color, Idx, Type, SubType, SwitchType):
    marker = makeMarker("decodeOnCommand", parameters=F"{Unit}, {Command}, {Level}, {Color}", ignore=True)
    pTypeSetpoint = 0xF2
    fields = {}
    if Command == "On" or Command == "Off" or Command == "Toggle" or Command == "Stop" or Command == "Open" or Command == "Close":
        fields["type"] = "command"
        fields["param"] = "switchlight"
        fields["idx"] = Idx
        fields["switchcmd"] = Command
    elif Command == "Set Level":
        # SetPoint device special case
        if Type == pTypeSetpoint:
            fields["type"] = "command"
            fields["param"] = "setsetpoint"
            fields["idx"] = Idx
            fields["setpoint"] = Level
        else:
            fields["type"] = "command"
            fields["param"] = "switchlight"
            fields["idx"] = Idx
            fields["switchcmd"] = "Set%20Level"
            fields["level"] = Level
    elif Command == "Set Color":
        fields["type"] = "command"
        fields["param"] = "setcolbrightnessvalue"
        fields["idx"] = Idx
        fields["color"] = Color
        fields["brightness"] = Level
    else:
        Domoticz.Error(F"{marker} Command {Command} not recognized. Please open GitHub issue to ask for support!")
    return fields

# Called after master subscription acknoledgment
def onMasterMqttSubAck(Connection, topics):
    marker = makeMarker("onMasterMqttSubAck", parameters=F"{topics}")
    if topics == variables.domoticzOutTopic:
        requestBackupDatabaseData()
    else:
        Domoticz.Error(F"{marker} Unexpected topics {topics}")

# Called after HTTP connection
def onHttpConnected(Connection):
    marker = makeMarker("onHttpConnected", instance=Connection.Name)
    if Connection.Name == variables.name2IdxConnection:
        askForDeviceList(Connection)
    if Connection.Name == variables.backupDatabaseConnection:
        askForBackupDatabase(Connection)
    if Connection.Name == variables.sendSlaveUpdateConnection:
        sendNextSlaveUpdate()

# Called after master MQTT connection
def onMasterConnected(Connection):
    marker = makeMarker("onMasterConnected")
    if variables.masterMqttClient != None:
        variables.masterMqttClient.SendId()

# Called after slave MQTT connection
def onSlaveConnected(Connection):
    marker = makeMarker("onSlaveConnected")
    if variables.slaveMqttClient != None:
        variables.slaveMqttClient.SendId()

# Called after master MQTT connection acknoledgment (Connect ID received ok)
def onMasterMqttConAck(Connection):
    marker = makeMarker("onMasterMqttConAck", instance=Connection.Name)
    # Send LWT data
    if variables.masterMqttClient != None:
        if variables.masterMqttClient.lwtTopic != "":
            lwtData = {}
            lwtData["state"] = "up"
            lwtData["version"] =  variables.pluginVersion
            lwtData["since"] = variables.masterSequence
            variables.masterMqttClient.Publish(variables.masterMqttClient.lwtTopic, json.dumps(lwtData), retain=1)
    askForDomoticzChanges(Connection)

# Called after slave MQTT connection acknoledgment (Connect ID received ok)
def onSlaveMqttConAck(Connection):
    marker = makeMarker("onSlaveMqttConAck", instance=Connection.Name)
    # Send LWT data
    if variables.slaveMqttClient != None:
        if variables.slaveMqttClient.lwtTopic != "":
            lwtData = {}
            lwtData["state"] = "up"
            lwtData["version"] =  variables.pluginVersion
            lwtData["since"] = variables.masterSequence
            variables.slaveMqttClient.Publish(variables.slaveMqttClient.lwtTopic, json.dumps(lwtData), retain=1)
        if variables.areWeOnMaster:
            sendParametersAndValuesToSlave()
            subscribeSlaveValuesFromMaster()
        else:
            subscribeMasterParametersFromSlave()

# Called after a message has been received on master MQTT
def onMasterReceived(Connection, topic, payload):
    marker = makeMarker("onMasterReceived")
    # Is this a message from domoticz/out topic on master MQTT?
    if topic == variables.domoticzOutTopic:
        jsonPayload = json.loads(payload)
        idx = str(getValue(jsonPayload, "idx"))
        Domoticz.Debug(F"{marker} idx {idx}, payload {json.dumps(jsonPayload)}")
        # Is idx in device to synchronize list?
        if idx in variables.syncDevices.keys():
            # Update syncDevices with nValue and sValue
            deviceParams = variables.syncDevices[idx]
            nValue = getValue(jsonPayload,"nvalue")
            if nValue != "":
                deviceParams["nValue"] = nValue
            sValue = getValue(jsonPayload,"svalue")
            if sValue == "":
                for i in range(10):
                    if "svalue"+str(i) in jsonPayload:
                        sValue += (";" if sValue != "" else "") + jsonPayload["svalue"+str(i)]
            if sValue != "":
                deviceParams["sValue"] = sValue
            lastUpdate = getValue(jsonPayload,"LastUpdate")
            if lastUpdate != "":
                deviceParams["LastUpdate"] = lastUpdate
            color = getValue(jsonPayload,"Color")
            if color != "":
                deviceParams["Color"] = color
            variables.syncDevices[idx] = deviceParams
            # Should we send updates to slave?
            if variables.slaveMqttClient != None:
                if variables.slaveMqttClient.connection.Connected:
                    variables.slaveMqttClient.Publish(F"{variables.rootTopic}/{variables.masterValues}/{idx}", \
                        json.dumps(variables.syncDevices[idx]), retain=1)
            Domoticz.Debug(F"{marker} Updating idx {idx} with {variables.syncDevices[idx]}")
    else:
        Domoticz.Error("{marker} Unexpected topic {topic}, payload {payload}")

# Called after a message has been received on slave MQTT connection on master
def onSlaveReceived(Connection, topic, payload):
    marker = makeMarker("onSlaveReceived")
    if variables.areWeOnMaster:
        # Is this a message from slaveValues topic on slave MQTT?
        prefix = F"{variables.rootTopic}/{variables.slaveValues}/"
        if topic.startswith(prefix):
            idx = topic[len(prefix):]
            jsonPayload = json.loads(payload)
            Domoticz.Debug(F"{marker} idx {idx}, payload {json.dumps(jsonPayload)}")
            # Is idx in device to synchronize list?
            if idx in variables.syncDevices.keys():
                # Get device characteristics
                device = variables.syncDevices[idx]
                Domoticz.Debug(F"{marker} Device={device}")
                if variables.syncDevices[idx]['allowSlaveUpdate']:
                    # Update master device with command received from slave
                    device = variables.syncParameters[idx]
                    fields = decodeOnCommand(Unit=None, Command=jsonPayload["Command"], \
                                Level=jsonPayload["Level"], Color=jsonPayload["Color"], Idx=idx, \
                                Type=device["Type"], SubType=device["SubType"], SwitchType=device["SwitchType"])
                    # Send message to master Domoticz server
                    if fields != None and fields != {}:
                        apiParameters = ""
                        for field in fields:
                            apiParameters += "&"+field+"="+str(fields[field])
                        apiParameters = "?" + apiParameters[1:]
                        Domoticz.Debug(F"{marker} Update parameters={apiParameters}")
                        # Add command to update list
                        variables.sendApiUpdateList.append(apiParameters)
                        sendNextSlaveUpdate()
                else:
                    Domoticz.Error("{marker} Remote changes not allowed for idx {idx}")
            else:
                Domoticz.Error(F"{marker} Can't find idx {idx} in {variables.syncDevices.keys()}")
        else:
            Domoticz.Error("{marker} Unexpected topic {topic}, payload {payload}")
    else:
        # Is this a message from masterParameters or matsreValues topics on slave MQTT?
        prefix1 = F"{variables.rootTopic}/{variables.masterParameters}/"
        prefix2 = F"{variables.rootTopic}/{variables.masterValues}/"
        jsonPayload = json.loads(payload)
        if topic.startswith(prefix1):
            # Here, we receive a parameters values message from master (either at startup as retained, or dynamically)
            idx = topic[len(prefix1):]
            deviceName = F"{variables.slaveDevicePrefix}{jsonPayload['Name']}"
            deviceType = jsonPayload['Type']
            deviceSubType = jsonPayload['SubType']
            deviceSwitchType = jsonPayload['SwitchType']
            options = decodeOptions(getValue(jsonPayload, "Options"))
            # Does device already exists?
            device = getDevice(idx)
            deviceUnit = getNextDeviceId()
            # If device type or subtype changed, delete device first, and recreate it with same device id
            if device != None:
                if device.Type != deviceType or device.SubType != deviceSubType:
                    deviceUnit = device.DeviceID
                    device.Delete()
                    device = None
            if device == None:
                # Create a new device
                Domoticz.Log(F"{marker} Creating " \
                    +F"Name='{deviceName}', Unit='{deviceUnit}', " \
                    +F"Type='{deviceType}', Subtype='{deviceSubType}', " \
                    +F"Switchtype='{deviceSwitchType}', Options='{options}', " \
                    +F"DeviceID='{idx}', Used='True'")
                device = Domoticz.Device(Name=deviceName, Unit=deviceUnit, \
                    Type=deviceType, Subtype=deviceSubType, \
                    Switchtype=deviceSwitchType, Options=options, \
                    DeviceID=idx, Used=True)
                device.Create()
            # Update existing device (at each startup and after creation, as plugin name is added by default)
            nValueToSet = device.nValue
            sValueToSet = device.sValue
            deviceUnit = device.DeviceID
            Domoticz.Log(F"{marker} Updating key '{idx}' " \
                +F"Name='{deviceName}', Unit='{deviceUnit}', " \
                +F"Type='{deviceType}', Subtype='{deviceSubType}', " \
                +F"Switchtype='{deviceSwitchType}', Options='{options}', " \
                +F"nValue='{nValueToSet}', sValue='{sValueToSet}', SuppressTriggers='True'")
            device.Update(Name=deviceName, \
                Type=deviceType, Subtype=deviceSubType, \
                Switchtype=deviceSwitchType, Options=options, \
                sValue=sValueToSet, nValue=nValueToSet, SuppressTriggers=True)
            # Ask for value changes
            subscribeMasterValuesFromSlave(idx)
        elif topic.startswith(prefix2):
            idx = topic[len(prefix2):]
            device = getDevice(idx)
            if device != None:
                nValueToSet = jsonPayload["nValue"]
                sValueToSet = jsonPayload["sValue"]
                colorToSet = getValue(jsonPayload, "Color")
                if colorToSet != "":
                    colorToSetStr = json.dumps(colorToSet)
                    if nValueToSet != device.nValue or sValueToSet != device.sValue or colorToSet != device.Color:
                        Domoticz.Log(F"{marker} Updating key {idx} " \
                            +F"Name={device.Name}, "\
                            +F"nValue={nValueToSet}, sValue={sValueToSet}, Color={colorToSetStr}")
                        device.Update(nValue=nValueToSet, sValue=sValueToSet, Color=colorToSetStr)
                else:
                    if nValueToSet != device.nValue or sValueToSet != device.sValue:
                        Domoticz.Log(F"{marker} Updating key {idx} " \
                            +F"Name={device.Name}, "\
                            +F"nValue={nValueToSet}, sValue={sValueToSet}")
                        device.Update(nValue=nValueToSet, sValue=sValueToSet)
                # Save update allowed flag
                variables.slaveUpdateAllowed[device.ID] = jsonPayload["allowSlaveUpdate"]
            else:
                Domoticz.Error(F"{marker} Can't find device matching idx {idx}")
        else:
            Domoticz.Error(F"{marker} Unexpected topic {topic}, payload {payload}")

# Called after name2idx request data received
def onHttpName2idx(Connection, result):
    marker = makeMarker("onHttpName2idx")
    if variables.httpClient != None:
        variables.httpClient.Close()
    # We got device list, load idx list and name to idx dictionnary
    loadName2Idx(result)
    loadMapping(variables.mapping)
    connectToMqttMaster()
    
# Called after backup database received
def onHttpBackupDatabase(Connection, data):
    marker = makeMarker("onHttpBackupDatabase")
    # Write database copy
    with open(variables.databaseCopyFileName, "wb") as dbStream:
        dbStream.write(data)
    # Open database copy
    variables.databaseConnecion = sqlite3.connect(variables.databaseCopyFileName)
    loadDefinitionsFromDb()
    variables.databaseConnecion = None
    try:
        os.remove(variables.databaseCopyFileName)
    except:
        pass

# Called on plug-in statup
def onStart():
    marker = makeMarker("onStart")
    # Load settings
    loadSettings()

    # Exit if error during loading settings
    if not variables.initDone:
        return

    # First operation depends on run mode
    if variables.areWeOnMaster:
        # Ask for name to idx data
        requestName2IdxData()
    else:
        # Connect to slave MQTT (from slave)
        connectToMqttSlaveOnSlave()

    # Enable heartbeat
    Domoticz.Heartbeat(30)

# Called when user change a device state
def onCommand(Unit, Command, Level, sColor):
    # Exit if init not properly done
    if not variables.initDone:
        return
    marker = makeMarker("onCommand", ignore=True)
    device = Devices[Unit]
    Domoticz.Log(F"{marker} {deviceStr(Unit)}, {device.DeviceID}: Command: '{Command}', Level: {Level}, Color: {sColor}")
    id = device.ID
    # Is update allowed on this device?
    if id in variables.slaveUpdateAllowed and variables.slaveUpdateAllowed[id]:
        fields = {}
        fields["Command"] = Command
        fields["Level"] = Level
        fields["Color"] = sColor
        fields["LastUpdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        idx = device.DeviceID
        # Publish change *WITHOUT* retain flag
        if variables.slaveMqttClient != None:
            if variables.slaveMqttClient.connection.Connected():
                Domoticz.Log(F"{marker} Sending idx {idx} to master with payload {str(fields)}")
                variables.slaveMqttClient.Publish(F"{variables.rootTopic}/{variables.slaveValues}/{idx}", json.dumps(fields), retain=False)
    else:
        Domoticz.Log(F"{marker} Update from {device.Name} (master idx {device.DeviceID}) forbidden")

# Called when a new device is added
def onDeviceAdded(Unit):
    # Exit if init not properly done
    if not variables.initDone:
        return
    marker = makeMarker("onDeviceAdded", ignore=True)
    Domoticz.Log(F"{marker} {deviceStr(Unit)}")

# Called when a device is modified by script
def onDeviceModified(self, Unit):
    # Exit if init not properly done
    if not variables.initDone:
        return
    marker = makeMarker("onDeviceModified", ignore=True)
    Domoticz.Log(F"{marker} {deviceStr(Unit)}")

# Called when a device is deleted
def onDeviceRemoved(Unit):
    # Exit if init not properly done
    if not variables.initDone:
        return
    marker = makeMarker("onDeviceRemoved", ignore=True)
    Domoticz.Log(F"{marker} {deviceStr(Unit)}")

# Called when a connection is opened
def onConnect(Connection, Status, Description):
    marker = makeMarker("onConnect", instance=F"{Connection.Name}", parameters=F"Status {str(Status)}, Description {str(Description)}")
    if Connection.Name == variables.name2IdxConnection \
            or Connection.Name == variables.backupDatabaseConnection \
            or Connection.Name == variables.sendSlaveUpdateConnection:
        onHttpConnected(Connection)
    elif Connection.Name == variables.masterConnection:
        onMasterConnected(Connection)
    elif Connection.Name == variables.slaveConnection:
        onSlaveConnected(Connection)
    else:
        Domoticz.Error(F"{marker} Unexpected Status {Status}, Description {Description}")
    
# Called when a conection is disconnected
def onDisconnect(Connection):
    marker = makeMarker("onDisconnect", instance=F"{Connection.Name}")
    # Delete slave MQTT client if disconnected
    if Connection.Name == variables.slaveConnection:
        variables.slaveMqttClient = None

# Called when a message is received on a connection
def onMessage(Connection, Data):
    if Connection.Name == variables.name2IdxConnection:
        marker = makeMarker("onMessage", instance=F"{Connection.Name}")
        Status = int(Data["Status"])
        if Status == 200:
            strData = Data["Data"].decode("utf-8", "ignore")
            if Connection.Connected():
                Connection.Disconnect()
            try:
                jsonData = json.loads(strData)
            except ValueError as e:
                Domoticz.Error(F"Error {e} decoding json data")
                return
            result = getValue(jsonData, "result")
            onHttpName2idx(Connection, result)
        else:
            Domoticz.Error(F"{marker} Error {Status} returned by HTTP")
    elif Connection.Name == variables.backupDatabaseConnection:
        marker = makeMarker("onMessage", instance=F"{Connection.Name}")
        Status = int(Data["Status"])
        if Status == 200:
            strData = Data["Data"]
            if Connection.Connected():
                Connection.Disconnect()
            onHttpBackupDatabase(Connection, strData)
        else:
            Domoticz.Error(F"{marker} Error {Status} returned by HTTP")
    elif Connection.Name == variables.sendSlaveUpdateConnection:
        marker = makeMarker("onMessage", instance=F"{Connection.Name}")
        Status = int(Data["Status"])
        if Status == 200:
            sendNextSlaveUpdate()
        else:
            Domoticz.Error(F"{marker} Error {Status} returned by HTTP - Data {Data['Data']}")
    elif Connection.Name == variables.masterConnection or Connection.Name == variables.slaveConnection:
        marker = makeMarker("onMessage", instance=F"{Connection.Name}", parameters=F"Data: {Data}", ignore=True)
        # Extract data and topic of MQTT message
        topic = Data['Topic'] if 'Topic' in Data else ""
        payload = Data['Payload'] if 'Payload' in Data else ""

        # Is this a connection ACK?
        if Data['Verb'] == "CONNACK":
            Domoticz.Log(F"{marker} Connection established")
            if Connection.Name == variables.masterConnection:
                onMasterMqttConAck(Connection)
            elif Connection.Name == variables.slaveConnection:
                onSlaveMqttConAck(Connection)
            else:
                Domoticz.Error(F"{marker} Unexpected Data {str(Data)}")
        # Is this a subcription ACK?
        elif Data['Verb'] == "SUBACK":
            # Is this an acknoledgment of domoticz/out topic on master MQTT?
            if Connection.Name == variables.masterConnection:
                if variables.masterMqttClient != None:
                    topics = variables.masterMqttClient.lastSubscribedTopics
                else:
                    topics = "???"
                Domoticz.Log(F"{marker} Topics {topics} subscribed")
                onMasterMqttSubAck(Connection, topics)
            elif Connection.Name == variables.slaveConnection:
                pass    # Don't care about subscription ack for slave on slave and on master
            else:
                Domoticz.Error(F"{marker} Unexpected Data {str(Data)}")
        # Is this a publish message (after subscription)?
        elif Data['Verb'] == "PUBLISH":
            Domoticz.Log(F"{marker} Topic {str(topic)}, payload >{payload}<")
            # Is this a message from domoticz/out topic on master MQTT?
            if Connection.Name == variables.masterConnection:
                onMasterReceived(Connection, topic, payload)
            elif Connection.Name == variables.slaveConnection:
                onSlaveReceived(Connection, topic, payload)
            else:
                Domoticz.Error(F"{marker} Unexpected Data {str(Data)}")
        elif Data['Verb'] == "PINGRESP":
            pass
        else:
            Domoticz.Error(F"{marker} Unexpected Data {str(Data)}")
    else:
        marker = makeMarker("onMessage", instance=F"{Connection.Name}", ignore=True)
        Domoticz.Error(F"{marker} Unexpected Data {str(Data)}")

# Called at regular interval by plug-in
def onHeartbeat():
    # Exit if init not properly done
    if not variables.initDone:
        return
    marker = makeMarker("onHeartbeat", ignore=(variables.debugging != "Verbose+"))

    # Send ping or (try to) reconnect master MQTT
    if variables.masterMqttClient != None:
        if variables.masterMqttClient.connection.Connected():
            variables.masterMqttClient.Ping()
        else:
            variables.masterMqttClient.Open()

    # Send ping or (try to) reconnect slave MQTT
    if variables.slaveMqttClient != None:
        if variables.slaveMqttClient.connection.Connected():
            variables.slaveMqttClient.Ping()
        else:
            variables.slaveMqttClient.Open()