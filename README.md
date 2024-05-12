# App preview
<img src="assets/app_preview.png" width="50%" height="50%">


# Installation
```
yum install git g++ cargo libvirt-devel libcap-ng-devel libseccomp-devel

git -C /opt clone https://github.com/konradziczek/libvirttui.git

python3.11 -m venv /opt/libvirttui/venv

source /opt/libvirttui/venv/bin/activate

pip3 install -r /opt/libvirttui/requirements.txt

/opt/libvirttui/setup.sh
```


# Updating
```
git -C /opt/libvirttui pull

source /opt/libvirttui/venv/bin/activate

pip3 install -r /opt/libvirttui/requirements.txt

/opt/libvirttui/setup.sh
```

# Sample /opt/virt_data/images.json file

```
{
  "fedora_template": {
    "name": "Fedora Template",
    "description": "Sample description.",
    "cpu_count": 2,
    "memory": 4096,
    "image_file": "fedora_template.qcow2",
    "template_file": "domain_linux.xml",
    "mounts": {
        "data": "/mnt/abc/<username_short>"
    }
  },
  "rocky_linux_template": {
    "name": "Rocky Linux Template",
    "description": "Sample description.",
    "cpu_count": 2,
    "memory": 4096,
    "image_file": "fedora_template.qcow2",
    "template_file": "domain_linux.xml",
    "mounts": {
        "data": "/mnt/abc/<username_long>"
    }
  }
}
```
