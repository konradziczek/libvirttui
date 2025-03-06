Each Windows image should have its own template with UUID generated only for this image. For example:

<domain type='kvm'>
  <uuid>1b01438c-fab4-11ef-9cd2-0242ac120003</uuid>
  .....
  <sysinfo type='smbios'>
    .....
    <system>
      .....
      <entry name='uuid'>1b01438c-fab4-11ef-9cd2-0242ac120003</entry>
