from adb import get_device
import os
import secrets
device = get_device()[0]

print(device.shell("su -c \'mount --all -o remount,rw -t vfat\'"))
allcfgfiles = [
    ".propfile",
    ".abipropfile",
    ".bluestacks.prop",
    ".def.prop",
    ".vendor.prop",
    ".dfprop",
    ".bstconf.prop",
]

try:
    os.makedirs("tmp")
except:
    pass

for file in allcfgfiles:
    inputf = f"/data/{file}"
    outputf = f"tmp/{file}"
    tmpf = f"/sdcard/" + secrets.token_hex(8)

    device.pull(inputf, outputf)

    print(file)

    with open(outputf, 'r') as file:
        meow = file.read()

    with open(outputf, 'w') as file:
        file.write(meow.replace('samsung/beyond1ltexx/beyond1:11/RD2A.211001.002/1884:user/release-keys', 'samsung/beyond1ltexx/beyond1:12/RD2A.211001.002/1884:user/release-keys'))

    print(device.push(outputf, tmpf))
    print(device.shell(f"su -c 'mv {tmpf} {inputf}'"))