# Plug-in data
masterName = ""                                 # Name of master MQTT server
masterMqttClient = None                         # Master MQTT client object
masterMqttHost = ""                             # Master MQTT server address
masterMqttPort = ""                             # Master MQTT server port
masterMqttUser = ""                             # Master MQTT username
masterMqttPassword = ""                         # Master MQTT password
masterSequence = ""                             # Master sequence id
slaveName = ""                                  # Name of slave MQTT server
slaveMqttClient = None                          # Slave MQTT client object
slaveMqttHost = ""                              # Slave MQTT server address
slaveMqttPort = ""                              # Slave MQTT server port
slaveMqttUser = ""                              # Slave MQTT username
slaveMqttPassword = ""                          # Slave MQTT password
slaveSequence = ""                              # Slave sequence id
slaveDevicePrefix = ""                          # Prefix to add to device names on Slave
slaveUpdateAllowed = {}                         # Slave local devices idx update allowed on master
domoticzUrl = ""                                # Domoticz URL
domoticzOutTopic = ""                           # Domoticz Out topic
domoticzUsername = ""                           # Domoticz IP username
domoticzPassword = ""                           # Domoticz IP password
domoticzAddress = ""                            # Domoticz IP address
domoticzPort = ""                               # Domoticz port
domoticzHttps = False                           # Is Domoticz using https scheme?
httpClient = None                               # HTTP client object
initDone = False                                # Clear init flag
settings = None                                 # Configuration settings
mapping = None                                  # Configuration mapping
debugging = "Normal"                            # Debug level
name2IdxConnection = "name2idx"                 # name2Idx HTTP connection name
backupDatabaseConnection = "backupDatabase"     # Device list HTTP connection name
sendSlaveUpdateConnection = "sendSlaveUpdate"   # Send slave update
masterConnection = "Master"                     # MQTT master connection name
slaveConnection = "Slave"                       # MQTT master connection name
syncDevices = {}                                # Synchronized devices values dictionary
syncParameters = {}                             # Synchronized devices parameters
name2Idx = {}                                   # Name to IDX dictionary
idxList = []                                    # List of known idxes
rootTopic = ""                                  # Root Mqttsync topic
masterValues = "masterValues"                   # Master values sub-topic
masterParameters = "masterParameters"           # Master parameters sub-topic
slaveValues = "slaveValues"                     # Slave values sub-topic
databaseCopyFileName = ""                       # Name of database copy file
databaseConnecion = None                        # Database connection
pluginVersion = "1.0.0"                         # That's written on it ;-)
areWeOnMaster = True                            # Are we running on master (else on slave)?
runMode = "Master"                              # Run mode (Master or Slave)
sendApiUpdateList = []                          # List of device update to send to master Domoticz