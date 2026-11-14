"""Generate XML safely without shell interpolation, then exec Icecast."""
import os
import xml.etree.ElementTree as ET

root = ET.fromstring('''<icecast>
  <location>Local VPS</location><admin>admin@localhost</admin>
  <limits><clients>100</clients><sources>2</sources><queue-size>524288</queue-size>
    <client-timeout>30</client-timeout><header-timeout>15</header-timeout><source-timeout>10</source-timeout>
    <burst-on-connect>1</burst-on-connect><burst-size>65535</burst-size></limits>
  <authentication><source-password/><relay-password/><admin-user>admin</admin-user><admin-password/></authentication>
  <hostname>localhost</hostname><listen-socket><port>8000</port></listen-socket>
  <fileserve>1</fileserve>
  <paths><basedir>/usr/share/icecast2</basedir><logdir>/tmp</logdir>
    <webroot>/usr/share/icecast2/web</webroot><adminroot>/usr/share/icecast2/admin</adminroot></paths>
  <logging><accesslog>-</accesslog><errorlog>-</errorlog><loglevel>2</loglevel></logging>
  <security><chroot>0</chroot></security>
</icecast>''')
root.find("authentication/source-password").text = os.environ["ICECAST_SOURCE_PASSWORD"]
root.find("authentication/relay-password").text = os.environ["ICECAST_SOURCE_PASSWORD"]
root.find("authentication/admin-password").text = os.environ["ICECAST_ADMIN_PASSWORD"]
ET.ElementTree(root).write("/tmp/icecast.xml", encoding="unicode")
os.execvp("icecast2", ["icecast2", "-c", "/tmp/icecast.xml"])
