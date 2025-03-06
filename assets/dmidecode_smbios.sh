#!/bin/bash

cat << EOF
  <sysinfo type="smbios">
    <bios>
      <entry name="vendor">$(dmidecode -s bios-vendor)</entry>
      <entry name="version">$(dmidecode -s bios-version)</entry>
      <entry name="date">$(dmidecode -s bios-release-date)</entry>
      <entry name="release">$(dmidecode -s bios-version)</entry>
    </bios>
    <system>
      <entry name="manufacturer">$(dmidecode -s system-manufacturer)</entry>
      <entry name="product">$(dmidecode -s system-product-name)</entry>
      <entry name="version">$(dmidecode -s system-version)</entry>
      <entry name="serial">$(dmidecode -s system-serial-number)</entry>
      <entry name="uuid">$(dmidecode -s system-uuid)</entry>
      <entry name="sku">$(dmidecode -s system-sku-number)</entry>
      <entry name="family">$(dmidecode -s system-family)</entry>
    </system>
    <baseBoard>
      <entry name="manufacturer">$(dmidecode -s baseboard-manufacturer)</entry>
      <entry name="product">$(dmidecode -s baseboard-product-name)</entry>
      <entry name="version">$(dmidecode -s baseboard-version)</entry>
      <entry name="serial">$(dmidecode -s baseboard-serial-number)</entry>
      <entry name="asset">$(dmidecode -s baseboard-asset-tag)</entry>
    </baseBoard>
    <chassis>
      <entry name='manufacturer'>$(dmidecode -s chassis-manufacturer)</entry>
      <entry name='version'>$(dmidecode -s chassis-version)</entry>
      <entry name='serial'>$(dmidecode -s chassis-serial-number)</entry>
      <entry name='asset'>$(dmidecode -s chassis-asset-tag)</entry>
    </chassis>
  </sysinfo>
EOF
