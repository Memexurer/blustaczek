import requests
import subprocess
import shutil
import psutil
import os
import time
import argparse
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen
from multiprocessing import Process, Value, Event

def get_device(adb_port):
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
    
    return device

def start_frida(device, frida_start_event, frida_bind_ip):
    if 'such' in str(device.shell('ls /data/local/tmp/frida-server')):
        print("no frida server found, downloading!")
        arch = str(device.shell("getprop ro.product.cpu.abi")).split("\n")[0]

        name = f'frida-server-{arch}.xz'
        with open(name, 'wb') as file:
            file.write(requests.get(f"https://github.com/frida/frida/releases/download/16.1.4/frida-server-16.1.4-android-{arch}.xz").content)

        device.push(name, '/data/local/tmp/frida-server.xz')
        device.shell("unxz /data/local/tmp/frida-server.xz")

    print("starting frida")
    frida_start_event.set()
    print(device.shell(f'su -c "./data/local/tmp/frida-server -l {frida_bind_ip} -P -v"', read_timeout_s=9999999, transport_timeout_s=999999))

def launch_shell(command):
    temp_batch_file = "temp_doskey_commands.bat"

    lime_color = "\x1b[32;1m"
    reset_color = "\x1b[0m"

    with open(temp_batch_file, "w") as f:
        command = command.replace(r"\\", r"\\\\")
        f.write('\n'.join([
            f"@prompt {lime_color}[adb]{reset_color} $P$G",
            "@echo off",
            f"DOSKEY adb=\"{command}\" $*",
            f"set ADB_SHELL=true"
            f"echo.",
            f"echo Current adb shell: {command}",
            f"echo Default adb shell: {shutil.which("adb") or "none??"}",
            "@echo on"
        ]))

    shell = os.environ.get("COMSPEC", "cmd.exe") 
    try:
        subprocess.run([shell, "/K", temp_batch_file], shell=True)
    except:
        pass
    os.remove("temp_doskey_commands.bat")

def run_frida_thread(adb_port, ip, is_running, start_lock):
    is_running.value = True
    start_frida(get_device(adb_port), start_lock, ip)
    is_running.value = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Launch Frida on BlueStacks')
    parser.add_argument('--frida_bind_ip', type=str, default="0.0.0.0", help='IP address for Frida to bind to')
    parser.add_argument('--connect_local', type=bool, default=True, help='Connect to local ADB instance')
    parser.add_argument('--frida', default=False, help='Start Frida server', action='store_true')
    parser.add_argument('--shell',default=False, help='Launches a new shell with ADB in path', action='store_true')
    args = parser.parse_args()

    def get_adb_port():
        adb_port = None

        with open(r'C:\ProgramData\BlueStacks_nxt\bluestacks.conf') as file:
            lines = file.readlines()
            for line in lines:
                if 'status.adb_port' in line:
                    try:
                        adb_port = int(line.split('"')[1])
                    except:
                        print("found an invalid adb port :(")
                        continue

        return adb_port
        
    adb_port = get_adb_port()
    if not adb_port:
        print("No adb port available...")
        exit(1)

    def get_current_adb_path():
        for proc in psutil.process_iter(['name', 'exe']):
            if 'adb' in proc.info['name']:
                return proc.info['exe']
        return None

    command = get_current_adb_path()
    if not command: # we dont have any adb server currently running
        command = shutil.which("adb") or r"C:\Program Files\BlueStacks_nxt\HD-ADB.exe"

    if args.connect_local:
        subprocess.call([command, "connect", f"127.0.0.1:{adb_port}"])

    is_running = Value('b', False)  # 'b' for boolean
    start_event  = Event()

    frida_thread = None
    if args.frida:
        frida_thread = Process(target=run_frida_thread, args=(adb_port, args.frida_bind_ip, is_running, start_event))
        frida_thread.start()
        start_event.wait(timeout=10)

    if args.shell:
        if os.environ.get("ADB_SHELL"):
            raise Exception("You're already inside adb shell!")

        launch_shell(command)

    if is_running.value and frida_thread:
        if args.shell:
            print("Frida server is still running, do Ctrl+C if you want to stop it...")
        
        try:
            time.sleep(9999999)
        except KeyboardInterrupt:
            frida_thread.terminate()
            exit(1)
    
    if args.connect_local:
        print("Adb daemon will be running in background...")