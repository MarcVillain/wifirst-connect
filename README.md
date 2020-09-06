Wifirst Connect
===
This script allows for automatic login on the [Captive Portal](https://www.wifirst.com/en/captive-portal) of the [Wifirst](https://www.wifirst.com/en/) WiFi provider.

This is a rework of this [ConnectToWiFirst](https://github.com/JoseIgnacioTamayo/ConnectToWiFirst) python script.

# How to install

### Global install
```
pip3 install --user -r requirements.txt
```

### Virtualenv install
```
pip3 install virtualenv
python3 -m venv venv
source ./venv/bin/activate
pip3 install -r requirements.txt
```

# How to use

The configuration is done by editting the full caps variables at the top of the
`connect.py` file.

```
python3 ./connect.py --help
```

# Run it as a background service

Having to run the tool manually can be fun at first but it gets really annoying
over time. Here is how to add it as a **systemd** service.

Before doing anything, make sure you have installed all the python requirements
by following the instructions in **How to install > Global Install**.

Make sure the python file is accessible and executable by the system:
```
sudo cp connect.py /root/wifirst_connect.py
sudo chmod u+x /root/wifirst_connect.py
```

Edit the service file at `/etc/systemd/system/wifirstconnect.service`:
```
[Unit]
Description = Login through Wifirst network
Wants = network-online.target
After = network.target network-online.target

[Service]
ExecStart = /usr/bin/python3 /root/wifirst_connect.py --output /var/log/wifirst_connect.log

[Install]
WantedBy = multi-user.target
```

Enable the service to make it start upon startup and start it:
```
sudo systemctl enable wifirstconnect.service
sudo systemctl start wifirstconnect.service
```

Check that everything went well:
```
sudo systemctl status wifirstconnect.service
```

# Authors

* Marc Villain (marc.villain@epita.fr)
