# Domoticz-MqttSync-Plugin

Domoticz Mqtt Sync plug-in for Domoticz / Plug-in Mqtt Sync pour Domoticz 

[English version and French version in the same document]
[Versions françaises et anglaises dans le même document]

## What's for? / CéKoi ?

* This plug-in synchronizes (part of) devices of a master instance to a slave one:
   	- Allow synchronization of (part of) Domoticz devices on a master instance to a slave one,
   	- Creation/modification/deletion and update of slave devices is automatic,
   	- Changes from slave can be reflected on master, if authorized in device configuration.

* Ce plugin synchronise (une partie) des dispositifs d'une instance maître sur une esclave :
    - Permet la synchronisation (d'une partie) des dispositifs d'une instance maître sur une esclave
    - Creation/modification/destruction et mise à jour des dispositifs esclaves automatiques,
    - Les mises à jour de l'esclave peuvent être envoyées sur le maître, si elles sont autorisés dans la configuration.


## Plugin Installation / Installation du plug-in

- Tested on Python version 3.7 & Domoticz version 2020.2
- Make sure that your Domoticz supports Python plugins (https://www.domoticz.com/wiki/Using_Python_plugins).


Follow these steps on both master and slave instances:

1. Clone repository into your Domoticz plugins folder:
```
cd domoticz/plugins
git clone https://github.com/FlyingDomotic/domoticz-mqtt-sync-plugin.git MqttSync
```
2. Restart Domoticz,
3. Go to "Hardware" page and add new item with type "MQTT Sync with LAN interface",
4. Select "Master" or "Slave" depending on machine,
5. Define configuration file on both machines (see later on this document).

- Testé avec Python version 3.7 & Domoticz version 2020.2
- Vérifiez que votre version de Domoticz supporte les plugins Python (https://www.domoticz.com/wiki/Using_Python_plugins).

Suivez ces étapes sur les iinstances ma^tre et esclave :

1. Clonez le dépôt GitHub dans le répertoire plugins de Domoticz:
```
cd domoticz/plugins
git clone https://github.com/FlyingDomotic/domoticz-mqtt-sync-plugin.git MqttSync
```
2. Redémarrer Domoticz,
3. Allez dans la page "Matériel" du bouton "configuration" et ajouter une entrée de type "MQTT Sync with LAN interface",
5. Sélectionnez "Master" ou "Slave" selon la machine,
5. Définissez le fichier de configuration sur chaque machine (voir plus bas dans ce document).

## Plugin update / Mise à jour du plugin

1. Go to plugin folder and pull new version:
```
cd domoticz/plugins/MqttSync
git pull
```
2. Restart Domoticz.

Note: if you did any changes to plugin files and `git pull` command doesn't work for you anymore, you could stash all local changes using
```
git stash
```
or
```
git checkout <modified file>
```

1. Allez dans le répertoire du plugin et charger la nouvelle version :
```
cd domoticz/plugins/MqttSync
git pull
```
2. Relancez Domoticz.

Note : si vous avez fait des modifs dans les fichiers du plugin et que la commande `git pull` ne fonctionne pas, vous pouvez écraser les modifications locales avec la commande
```
git stash
```
ou
```
git checkout <fichier modifié>
```

## Domotic versions/Versions de Domoticz
More or less, any versions of Domoticz can be used on master and slave (tested for example with a master on 2020.2 and a slave on 2024.7).

One thing that may being problematic is having to sync a master device with new incompatible option on slave. If this occurs, please open an issue, for me to filter the offending option item.

A peu près n'importe quelles versions de Domoticz peuvent être utilisées sur le maître et l'esclave (j'ai testé, par exemple un maître en 2020.2 et un esclave en 2024.7).

Une chose qui pourrait poser un problème serait d'avoir à synchroniser un dispositis maître avec une option incompatible avec l'esclave. Si celà arrive, merci d'ouvrir une issue, afin que je puisse filtrer l'option fautive.

## Configuration file/Fichier de configuration
Configuration is done through a JSON file, (defaut MqttSync.json, but you may name it as you want, for example based on master/slave names). An example is given in /examples folder. It looks like:

La configuration est réalisé grace à un fichier JSON (par défaut MqttSync.json, mais vous pouvez le nommer comme vous le souhaitez, par exemple en se basant sur les noms du maître et de l'esclave). Un exemple est donné dans le répertoire /examples. Il ressemble à :
```
{
	"settings": {
		"configVersion": "V1.0.2",
		"masterName": "master",
		"masterMqttHost": "masterHost",
		"masterMqttPort": "1883",
		"masterMqttUser": "masterMqttUser",
		"masterMqttPassword": "masterMqttPassword",
		"masterDomoticzOutTopic": "domoticz/out",
        "masterDomoticzUrl": "http://masterHost:8080",
		"slaveName": "slave",
		"slaveMqttHost": "slaveHost",
		"slaveMqttPort": "1883",
		"slaveMqttUser": "slaveMqttUser",
		"slaveMqttPassword": "slaveMqttPassword",
        "slaveDomoticzUrl": "http://slave:8080",
        "slaveDevicePrefix": "MqttSync - "
	},
	"mapping": [
		{"idx": 123, "allowSlaveUpdate": true},
		{"idx": 456},
		{"idx": 789, "name": "My device name", "allowSlaveUpdate": true},
		{"name": "My other device name", "allowSlaveUpdate": false}
	]
}
```
Change it as follow:
    - "settings": contains list of plugin settings,
        - "configVersion": Keep given value here, update it when it changes in example folder (a message in plugin will tell you if you're using a too old version),
        - "masterName"/"slaveName": give names of master and slave Domoticz instances. This allows a master to feed multiple slaves, and a slave to connect to multiple masters,
        - "masterMqttHost"/"slaveMqttHost": give IP address/name of master/slave MQTT instances. Warning: on master instance, don't specify here "127.0.0.1" for "slaveMqttHost", as it should refers to slave remote instance, not local master one!
        - "masterMqttPort"/slaveMqttPort": give port number of MQTT master/slave instances (commonly 1883),
        - "masterMqttUser"/"slaveMqttUser": give username of MQTT master/slave instances (if needed),
        - "masterMqttPassword"/"slaveMqttPassword": give password of MQTT master/slave instances (if needed),
        - "masterDomoticzOutTopic": give Domoticz out topic of master instance (commonly "domoticz/out"),
        - "masterDomoticzUrl"/"slaveDomoticzUrl": give Domotcz URL of master/slave instances. Often "http://127.0.0.1:8080". You may speficy "https" if needed, change IP address and/or add username/password,
        - "slaveDevicePrefix": give prefix that will be added in front of master device names on slave instance. This is useful when devices have same name on both master and slave, when running master and slave on same machine (at least for me to test), or when a slave manages multiple masters with same devices names.Optional, set empty if not given,
    - "mapping": contains list of devices to be synchronized from master to slave,
        - "idx": give idx of master device to synchonize. Optional if "name" given,
        - "name" : give name of master device to synchonize. Optional if "idx" given. If both given, "idx" will be used, and a message displayed if "name" is not those of given "idx",
        - "allowSlaveUpdate" : set it to "true" to allow slave to send changes to master. Optional, set to "false" if not given. This value is part of parameter data sent by master on slave, allowing slave to only send required changes. On master side, an additional check is made when receiving data to discard illegal changes sent by slave.

    You may have the same configuration file on master and slave. In this case, take care NOT giving "127.0.0.1" as "slaveMqttHost" on master, but real slave IP or name. This real IP or name can also be given on slave, keeping configuration files identical on both instances.

    Items used on both instances are "configVersion", "masterName", "slaveName", "slaveMqttHost",  "slaveMqttPort", "slaveMqttUser" and "slaveMqttPassword".

    Items used on master only are "masterMqttHost", "masterMqttPort", "masterMqttUser", "masterMqttPassword", "masterDomoticzOutTopic", "masterDomoticzUrl" and all "mapping" items.

    Items used on slave only are "slaveDomoticzUrl" and "slaveDevicePrefix".

    Items not used on an instance are just ignored.

Modifiez le comme suit :
    - "settings": contient la liste des paramètres du plugin,
        - "configVersion": Conservez la valeur trouvé ici, mettez-la à jour lorsqu'elle change dans le répertoire examples (un message du plugin vous indiquera si vous utilisez une version trop ancienne),
        - "masterName"/"slaveName": donnez le nom des instances Domoticz maître et esclave. Permet à un maître de contrôler plusieurs esclaves, et à un esclave de se connecter sur plusieurs maîtres,
        - "masterMqttHost"/"slaveMqttHost": donnez l'adress IP ou le nom des serveurs MQTT maître et esclave. Attention: sur l'instance maître, ne PAS spécifier "127.0.0.1" pour "slaveMqttHost", car on doit donner une référence à l'instance MQTT esclave distante, pas le maître (local) !
        - "masterMqttPort"/slaveMqttPort": donnez le numéro de port du serveur MQTT maître ou esclave (habituellement 1883),
        - "masterMqttUser"/"slaveMqttUser": donnez le nom d'utilisateur du serveur MQTT maître ou esclave (si besoin),
        - "masterMqttPassword"/"slaveMqttPassword": donnez le mot de passe du serveur MQTT maître ou esclave (si besoin),
        - "masterDomoticzOutTopic": donnez le topic Domotiz "out" de l'instance maître (généralement "domoticz/out"),
        - "masterDomoticzUrl"/"slaveDomoticzUrl": donnez l'URL des serveurs Domotcz maître et esclave. Souvent "http://127.0.0.1:8080". Vous pouvez indiquer "https" si besoin, changer l'adresse IP et/ou ajouter un nom d'utilisateur et un mot de passe,
        - "slaveDevicePrefix": donnez un préfixe qui sera ajoué devant le nom du dispositif maître sur l'esclave. C'est utile lorsque des dispositfs ont le même nom sur le maître et l'esclave, lorsque maître et esclave tournent sur la même machine (à minima pour mes tests), ou lorsqu'un esclave gère plusieurs maîtres avec des noms de dispositif identiques. Optionel, vide si non spécifié,
    - "mapping": contient la liste des dispositifs à synchroniser du maître vers l'esclave,
        - "idx": donnez le numéro d'idx du dispositif maître à synchroniser. Optionel si "name" est spécifié,
        - "name" : donnez le nom du dispositif maître à synchroniser. Optionel si "idx" est spécifié. Si les deux sont donnés, "idx" sera utilisé et un message affiché si "name" n'est pas celui du dispositif "idx" specifié,
        - "allowSlaveUpdate" : mettez le à "true" pour autoriser les changements de l'esclave à être répercutés sur le maître. Optionel, mis à "false" si omis. Cet item fait partie des paramètres envoyés du maître vers l'esclave, afin qu'il n'envoie des modifications que sur les dispositifs autorisés. De son côté, le maître vérifie les données reçues et ignore celles qui ne sont pas autorisées.

    Vous pouvez utiliser le même fichier de configuration sur le maître et sur l'esclave. Dans ce cas, faites attention à ne PAS indiquer "127.0.0.1" dans "slaveMqttHost" sur le maître, mais l'adresse ou le nom IP réel de l'esclave. Ce nom ou cette adresse peuvent aussi être donnés sur l'esclave, afin de conserver des fichiers identiques sur les deux instances.

    Les items utilisés sur les 2 instances sont "configVersion", "masterName", "slaveName", "slaveMqttHost",  "slaveMqttPort", "slaveMqttUser" et "slaveMqttPassword".

    Les items utilisés uniquement sur le maître sont "masterMqttHost", "masterMqttPort", "masterMqttUser", "masterMqttPassword", "masterDomoticzOutTopic", "masterDomoticzUrl" et l'ensemble des items "mapping".

    LEs items utilisés uniquement sur l'esclave sont "slaveDomoticzUrl" et "slaveDevicePrefix".

    Les items non utilisés par une instance sont simplement ignorés.

## MQTT Topics/Topics MQTT

mqttSync: Main root topic
    - <master name>2<slave name>: master/slave identifier
        - lwt: Last Will Testament (status)
            MasterOnMaster: MQTT master on master/Connexion du maître au serveur MQTT maître
            SlaveOnMaster: MQTT slave on master/Connexion du maître au serveur MQTT esclave
            SlaveOnSlave: MQTT slave on slave/Connexion de l'esclave au serveur MQTT esclave
        - masterParameters: Synchronized devices parameters written by master, read on slave
            - idx ...
        - masterValues: Synchronized devices values written by master, read on slave
            - idx ...
        - slaveValues: Slave authorized device command values written by slave, read on master
            - idx ...

Note: All idx(es) are those of master device

mqttSync : Topic racine principal
    - <nom maître>2<nom esclave> : Identificateu maître/esclave
        - lwt : Dernières volontées (statut)
            MasterOnMaster : Connexion du maître au serveur MQTT maître
            SlaveOnMaster : Connexion du maître au serveur MQTT esclave
            SlaveOnSlave : Connexion de l'esclave au serveur MQTT esclave
        - masterParameters : Paramètres des dispositifs synchronisés écrits par le maître, lus par l'esclave
            - idx ...
        - masterValues : Valeurs des dispositifs synchronisés écrits par le maître, lus par l'esclave
            - idx ...
        - slaveValues : Commandes des dispositifs esclave autorisés écrits par l'esclave, lues par le maître
            - idx ...

Note: Tous les idx sont ceux des dispositifs du maître

## Technical implementation/Mise en oeuvre technique

[En Anglais seulement, le code étant écrit dans cette langue]

Basics:
	- For each synchronized device, slave (remote) MQTT contains 3 topics based on master device's idx:
		* one topic containing device parameters (all useful parameters to create/update device)
			. written by master/read by slave
		* one topic containing device value (nValue/sValue/Color)
			. written by master/read by slave
		* one topic containing slave device command (Command/Level/Color)
			. written by slave/read by master (if authorized)
	- Master instance:
		* updates devices parameters each time it starts (ToDo: deleting those not used anymore)
		* updates device value:
			. when (re)connected to master MQTT
			. when (re)connected to slave MQTT
			. when master device changes
		* subscribes to authorized slave device changes:
			. it updates master value with slave change if authorized. As topic is not marked "retained", change is lost if master not listening. However, slave won't receive feedback of its change.
	- Slave instance:
		* create/updates devices each time it (re)connects to slave MQTT as topics are marked "retained". They will also be updated each time master restarts. (ToDo: deleting those not used anymore)
		* subscribes to master device changes:
			. it updates its value when master changes (and at startup as marked "retained")
		* send (allowed) device changes to master:
			. device update will come from master as nothing is propagated to local slace instance by plugin.
	- In addition, one topic for each site is created, containing plug-in version and last heartbeat time

Master implementation:
	- At startup (onStart):
		* Load settings (loadSettings)
		* Request list of device IDX through Domoticz API (requestName2IdxData, which opens HTTP connection)
	- When HTTP connection is opened (onConnect-> onHttpConnect), request for API device list(askForDeviceList)
	- When Domoticz device list if received from  API (onMessage):
		* Create internal device list from JSON configuration file (loadName2Idx), don't set nValue, sValue nor color.
		* Connect to master MQTT (connectToMqttMaster)
	- When connected to master MQTT (onConnect->onMasterConnected):
		* Send connection ID
	- When connection id acknowledgment is received (onMessage->onMasterConnected)
		* Set Last Will Testament
		* Subscribe to domoticz/out changes (askForDomoticzChanges)
	- When domoticz/out subscription is received (onMessage->onMasterMqttSubAck)
		* Request database backup (requestBackupDatabaseData, which opens HTTP connection)
	- When HTTP connection is opened (onConnect-> onHttpConnect), request database copy (askForBackupDatabase)
	- When receiving database copy is received (onMessage->onHttpBackupDatabase):
		* Save database to disk
		* Open database
		* Load device definition from database (loadDefinitionsFromDb)
		* Close database and (try to) delete it
		* Connect to slave MQTT (connectToMqttSlaveOnMaster)
	- When slave MQTT connects (onConnect->onSlaveConnected)
		* Send connection ID (acknowledged will be ignored)
	- When connection ID is acknowledged (onConnect->onSlaveMqttConAck):
		* Send Last Will Testament
		* Send device parameters and values to slave (sendParametersAndValuesToSlave)
		* Subscribe to slave values change (subscribeSlaveValuesFromMaster), acknowledgment will be ignored
	- When receiving a device change from Domoticz (onMessage->onMasterReceived):
		* Update internal values and send them if connected to slave MQTT
	- When receiving a device change from slave (onMessage->onSlaveReceived)
		* Read command set by slave
		* Check that master change is allowed for this device
		* Updating master device if value changed
	- On heartbeat:
		* Reconnect master and/or slave MQTT if disconnected

Slave implementation:
	- At startup (onStart):
		* Load settings (loadSettings)
		* Connect to slave MQTT (connectToMqttSlaveOnSlave)
	- When slave MQTT connects (onConnect->onSlaveConnected)
		* Send connection ID (acknowledged will be ignored)
	- When connection ID is acknowledged (onConnect->onSlaveMqttConAck):
		* Send Last Will Testament
		* Subscribe to master parameters changes, and initial values as "retained" flag is set (subscribeMasterParametersFromSlave), acknowledgment will be ignored
	- When master parameters are received (onMessage->onSlaveReceived):
		* Extract device parameters
		* If (slave local) device exists and type or subtype changes:
			- Delete it, and save Device ID to recreate a new one with same device ID
		* If device don't exists (or has just been deleted)
			- Create device with right parameters, with first unused device ID unless just deleted
		* Any way modify device parameters (useful just after creation as Domoticz adds plugin name in front of device name)
		* Subscribe to master value change for this device (subscribeMasterValuesFromSlave)
	- When master values are received (onMessage->onSlaveReceived):
		* Updates (slave local) device with master values
	- When a slave (MqttSync) device changes (onCommand):
		* Check that device is allowed to send data to master:
			- Discard change if not
		* Sends command to master 

## Security aspects/Aspects de sécurité

Master instance is connected to Master MQTT, Slave MQTT and Master Domoticz, running on Master.

Slave instance is connected to Slave MQTT, Slave Domoticz, running on Slave.

In both cases, plugin runs on local Domoticz instances.

Slave can be running in an unsafe environment, hosting slave MQTT. In this case, Master Domoticz has only outgoing connections (to slave MQTT), which is often seen as safer than accepting incomming connection.

Changes are allowed from master (inside) configuration file. Change allowed flag is sent by Master to Slave in parameters. This is tested in slave, which sends only change request for authorized devices. If slave plugin is compromized (or changes intercepted and mimiked), and sends unauthorized changes to master, master will discard these unauthorized changes.

In addition, you may add another level of restriction, creating a dedicated user on Master, and allowing it to read (an optionaly write) only some devices on Master. Give this user (and password) on Domoticz master URL in master configuration file.

Note that people that can access Domoticz slave instance are able to send device changes for allowed devices. You must protect this instance to avoid "unexpected" changes.

L'instance maître est connectée au serveur MQTT maître, au serveur MQTT esclave, et à l'instance maître Domoticz, et tourne sur le maître.

L'instance esclave est connectée au serveur MQTT esclave, à l'instance esclave Domoticz, et tourne sur l'esclave.

L'esclave peut tourner dans un environnement non sûr, hébergeant le serveur MQTT esclave. Dans ce cas, l'instance Domoticz maître aura seulement une connexion sortante (vers le serveur MQTT esclave), qui est souvent considéré comme plus sûr que d'accepter des connexions entrantes.

Les modifications sont acceptées depuis le fichier de configuration (interne) maître. L'indicateur de modification possible est envoyé par le maître à l'eclave dans les paramètres. L'eclave le teste avant d'envoyer une modification, et bloque les changements non autorisés. Si le plugin esclave est compromis (ou des modifications interceptées et rejouées), et envoye des modifications non autorisées, le maître ignorera ces changements.

De plus, vous pouvez ajouter un niveau supplémentaire de protection en créant un utilisateur dédié sur le maître, et ne l'autoriser à lire (et écrire si souhaité) que certains dispositifs. Donnez ce nom d'utilisateur (et son mot de passe) dans l'URL Domoticz maître dans le fichier de configuration sur le maître.

Noter que les personnes qui peuvent accéder à l'instance Domoticz esclave peuvent envoyer des modifications sur les dispositifs autorisés. Vous vevez protéger cette instance pour éviter des modification non désirées.