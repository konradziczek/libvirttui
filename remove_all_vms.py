#!/opt/libvirttui/venv/bin/python

import os
import time
import libvirt
from shutil import rmtree


VIRT_DATA_DIR_PATH = "/opt/virt_data"

def libvirt_temp_callback(userdata, err):
        pass

libvirt_conn = libvirt.open("qemu:///system")
if not libvirt_conn:
    print("ERROR: Failed to open connection to qemu.")
    exit(1)

libvirt.registerErrorHandler(f=libvirt_temp_callback, ctx=None)


print("Stopping old vms...")

domains = libvirt_conn.listAllDomains(0)
for domain in domains:
    if domain.name().startswith("libvirttui_"):
        try:
            domain.destroy()
        except libvirt.libvirtError:
            pass
        print(f"{domain.name()} stopped")

print("Done.\n")


print("Deleting old vm disks...")

for dir_name in os.listdir(os.path.join(VIRT_DATA_DIR_PATH, 'vm')):
    if os.path.isdir(os.path.join(VIRT_DATA_DIR_PATH, 'vm', dir_name)):
        rmtree(os.path.join(VIRT_DATA_DIR_PATH, 'vm', dir_name))
        print(f"User {dir_name} vm disks have been deleted.")

print("Done.\n")


print("Deleting vms...")

time.sleep(1)

domains = libvirt_conn.listAllDomains(0)
for domain in domains:
    if domain.name().startswith("libvirttui_"):
        domain.undefine()
        print(f"{domain.name()} deleted")

print("Done.\n")


print("Deleting temporary data...")

for dir_name in os.listdir('/tmp'):
    if os.path.isdir(os.path.join('/tmp', dir_name)) and dir_name.startswith("libvirttui_"):
        rmtree(os.path.join('/tmp', dir_name))
        print(f"{dir_name} deleted")

print("Done.\n")

libvirt.registerErrorHandler(f=None, ctx=None)  # restore default handler

