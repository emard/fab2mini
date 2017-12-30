#!/usr/bin/python3

import sys
import requests

printer="fabrikator.lan"

def gcode(printer, cmd):
  r = requests.get("http://" + printer + "/set?code=" + cmd)
  return r.text

def upload(printer, local_filename):
  url = "http://" + printer + "/upload"
  files = { 'file': open(local_filename, 'rb') }
  r = requests.post(url, files=files)
  return r.text

print("steppers off")
print(gcode(printer, "M84"))
print("hotbed to 57'C")
print(gcode(printer, "M140 S57"))
print("pause 1 second")
print(gcode(printer, "G4 S1"))
print("print uploaded file 'cache.gc' on SD card")
print(gcode(printer, "M565"))
