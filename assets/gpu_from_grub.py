import os
import sys
import re
import json
import pwd
import grp
import subprocess


with open('/etc/default/grub', 'r') as f:
    content = f.read()

match = re.search(r'pci-stub\.ids=([^\s"]+)', content)
if not match:
    print("Parameter pci-stub.ids not found in /etc/default/grub.")
    sys.exit(1)

pci_ids_str = match.group(1)
pci_ids = pci_ids_str.split(',')

print(f"Found PCI ids: {pci_ids}")

lspci = subprocess.check_output(['lspci', '-nn', '-D'], text=True)

found = []
for line in lspci.strip().split('\n'):
    match = re.search(r'^([0-9a-f:.]+)\s+(.*)\s+\[(\w{4}:\w{4})\]', line, re.IGNORECASE)
    if match:
        pci_addr, name, id_pair = match.groups()
        id_pair = id_pair.lower()
        if id_pair in pci_ids:
            domain, bus, rest = pci_addr.split(':')
            slot, function = rest.split('.')
            found.append({
                'id': id_pair,
                'name': name,
                'full_address': pci_addr,
                'domain': f"0x{domain.zfill(4)}",
                'bus': f"0x{bus.zfill(2)}",
                'slot': f"0x{slot.zfill(2)}",
                'function': f"0x{function}"
            })

print(f"Found PCI addresses:")

print(json.dumps(found, indent=4))

if not os.path.exists('/opt/libvirttui/gpu.json'):
    with open('/opt/libvirttui/gpu.json', 'w') as json_file:
        json.dump(found, json_file, indent=4)
        print("File saved.")
    if os.geteuid() == 0:
        print("Changing owner and group to libvirttui.")
        uid = pwd.getpwnam('libvirttui').pw_uid
        gid = grp.getgrnam('libvirttui').gr_gid
        os.chown('/opt/libvirttui/gpu.json', uid, gid)
else:
    print("File /opt/libvirttui/gpu.json already exists - it will not be replaced.")
    sys.exit(1)
