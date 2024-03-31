import os
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen

def get_device():
    with open(r'C:\ProgramData\BlueStacks_nxt\bluestacks.conf') as file:
        lines = file.readlines()
        for line in lines:
            if 'status.adb_port' in line:
                try:
                    adb_port = int(line.split('"')[1])
                except:
                    print("found an invalid adb port :(")
                    continue
        
    name = 'adbkey'

    if not os.path.exists(name):
        keygen(name)

    with open(name) as f:
        priv = f.read()
    with open(name + '.pub') as f:
        pub = f.read()

    signer = PythonRSASigner(pub, priv)

    device = AdbDeviceTcp('127.0.0.1', adb_port, default_transport_timeout_s=9.)
    device.connect(rsa_keys=[signer], auth_timeout_s=0.1)

    return device, adb_port
