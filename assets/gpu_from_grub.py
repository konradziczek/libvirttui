import os
import sys
import re
import json
import pwd
import grp

with open('/etc/default/grub', 'r') as f:
    content = f.read()

match = re.search(r'pci-stub\.ids=([^\s"]+)', content)
if not match:
    print("Parameter pci-stub.ids not found in /etc/default/grub.")
    sys.exit(1)

pci_ids_str = match.group(1)
pci_ids = pci_ids_str.split(',')

print(f"Found: {pci_ids}")

if not os.path.exists('/opt/libvirttui/gpu.json'):
    with open('/opt/libvirttui/gpu.json', 'w') as json_file:
        json.dump(pci_ids, json_file, indent=2)
        print("File saved.")
    if os.geteuid() == 0:
        print("Changing owner and group to libvirttui.")
        uid = pwd.getpwnam('libvirttui').pw_uid
        gid = grp.getgrnam('libvirttui').gr_gid
        os.chown('/opt/libvirttui/gpu.json', uid, gid)
else:
    print("File /opt/libvirttui/gpu.json already exists - it will not be replaced.")
    sys.exit(1)
