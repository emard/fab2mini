#!/usr/bin/python

# Copyright (c) 2013, Jake
# All rights reserved.
# Modified by EMARD for Fabrikator ][ mini
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import urllib, urllib2, os, sys, time, curses
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import getopt, datetime

# Class used to display a progress bar in the console.
# Probably good only on Mac or Unix style OS's.
# From StackOverflow 5925028, 6169217, et al.
class Progress(object):
    def __init__(self, title):
        # Some initialization of variables
        self._seen=0.0;
        self._title = title;
        self._progress = 0.0;
        self._numberOfBars = 40
        self._numberOfBarsDisplayed = 0
        
        #print the initial progress meter
        sys.stdout.write(self._title + " [" + "-"* self._numberOfBars +"] %.2f%%" % (self._progress * 100.0))
        sys.stdout.flush();

    def update(self, total, size, args = 0):
        # Calculate the current progress
        self._seen += size;
        newProgress = self._seen/total;
        newBars = int(newProgress * self._numberOfBars)
        
        # Check to see if we need to add another hashmark to the progress meter
        if (self._numberOfBarsDisplayed < newBars):
            #If so, move the cursor back to the begninning of the meter and print it.
            lenOfCurrentProgress = len("%.2f%%" % (self._progress * 100.0))
            sys.stdout.write("\x1b[%dD" % lenOfCurrentProgress) #move back by the # of chars in %            
            sys.stdout.write("\x1b[%dD" % (2 + self._numberOfBars))
            sys.stdout.write("#" * newBars)
            
            #Move the cursor forward to the end of the progress meter and print the percentage
            sys.stdout.write("\x1b[%dC" % ((self._numberOfBars - newBars) + 2))
            newProgressLabel = "%.2f%%" % (newProgress * 100.0)
            sys.stdout.write(newProgressLabel)
            
            #Upadate the state for the next time
            self._progress = newProgress
            self._numberOfBarsDisplayed = newBars
            
        # Check to see if only the percentage has changed
        elif (newProgress > self._progress):
            #If so, move the cursor back to the beginning of the percentage area and print
            sys.stdout.write("\x1b[%dD" % len("%.2f%%" % (self._progress*100))) #move back by the # of chars in %
            sys.stdout.write("%.2f%%" % (newProgress * 100.0))
            self._progress = newProgress
        sys.stdout.flush();
            
# A file class to track the progress of the read
class file_with_callback(file):
    def __init__(self, path, mode, callback, *args):
        file.__init__(self, path, mode)
        self.seek (0, os.SEEK_END);
        self._total = self.tell();
        self.seek(0);
        self._callback = callback
        self._args = args
        
    def __len__(self):
        return self._total
        
    def read(self, size):
        data = file.read(self, size);
        self._callback(self._total, len(data), *self._args)
        return data
    
# This function uploads the file to 
def upload(path, sdCardIP, directory="/"):
    # Get the filename from the path and create the progress indicator
    filename = os.path.basename(path)
    thetime=os.path.getctime(path);
    cdate = datetime.datetime.fromtimestamp(thetime)
    year = cdate.year
    month = cdate.month
    day = cdate.day
    packedDate = (day & 0b11111) + ((month & 0b1111) << 5) + (((year - 1980) & 0b1111111) << 9)    
        
    progress = Progress(filename)
    
    # Open the file,  and set the callback to the progress indicator
    file = file_with_callback(path, 'rb', progress.update, path)

    # Upload the file using "poster" module
    register_openers()
    url = "http://%s/upload" % (sdCardIP)
    # those throw some error:
    # url = "http://%s/upload.cgi?UPDIR=%s" % (sdCardIP, directory)
    # url = "http://%s/upload.cgi?FTIME=%08x" % (sdCardIP, packedDate)
    values = {'file':file, 'submit':"submit" }
    data, headers = multipart_encode(values)
    headers['User-Agent'] = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    request = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(request)
    the_page = response.read();

#    url="http://%s/upload.cgi?FTIME=%d" % (sdCardIP, os.path.getctime(path))
#    print(url)
#    print(urllib2.urlopen(url).read())    
        
    return the_page;
    
# This function compares the file to the one on the card
def verify_upload(path, sdCardIP, directory="/"):
    # Parse the filename
    filename = os.path.basename(path)
    filebase = os.path.splitext(filename)[0]
    fileext  = os.path.splitext(filename)[1]
    progress = Progress("Verify")
    
    # Open the file on the card and compare 2048 bytes at a time
    url = "http://%s/%s/%s%s" % (sdCardIP, directory, filebase.upper(), fileext.upper())
    request = urllib2.urlopen(url)
    CHUNK = 2048;

    with open(path, "rb") as localfile:
        localfile.seek (0, os.SEEK_END);
        totalSize = localfile.tell();
        localfile.seek(0);

        while True:
            localchunk = bytes(localfile.read(CHUNK))
            #print (len(localchunk))
            if not localchunk: break;
            remotechunk = bytes(request.read(CHUNK))
            if (localchunk != remotechunk): 
                return False
                break;
            progress.update(totalSize, len(localchunk))
    return True

def delete(file, sdCardIP, directory="/"):
    # delete the file using "poster" module
    register_openers()
    url = "http://%s/upload.cgi?DEL=%s/%s" % (sdCardIP, directory, path)
    response = urllib2.urlopen(url)
    the_page = response.read();

    return the_page;

def gcode(sdCardIP, cmd):
    # delete the file using "poster" module
    register_openers()
    url = "http://%s/set?code=%s" % (sdCardIP, cmd)
    response = urllib2.urlopen(url)
    the_page = response.read();
    return the_page;
            
            
def print_usage():
    print "[-v|--verify] [-c|--cardip] <CardIP> <filename> [-d|--direcoty remote_directory]"
    
#MAIN SECTION

options, remainder = getopt.getopt(sys.argv[1:], 'vc:d:r', ['verify',
                                                           'cardip=',
                                                           'directory=',
                                                           'delete',
                                                         ])

verify = False
# cardip = ""
cardip = "fabrikator.lan"
path = ""
directory = "/UPLOAD"
remove = False

for opt, arg in options:
    if opt in ('-v', '--verify'):
        verify = True
    elif opt in ('-c', '--cardip'):
        cardip = arg
    elif opt in ('-d', '--directory'):
        directory = arg
    elif opt in ('--delete'):
        remove = True

if (cardip == ""):
    print_usage()
    sys.exit(1)

path = remainder[0]    
if(remove):
  result = delete(path, cardip, directory)
  # print(result)
  if ("SUCCESS" in result):
    sys.stdout.write(" DONE\n")
  elif ("NG" in result):
    sys.stdout.write(" FAILED: NG\n")
  else:
    sys.stdout.write(" FAILED\n")
else:
  if (not os.path.exists(path)): 
    print "File not found: " + path;
    sys.exit(1)
  print("steppers off")
  print(gcode(cardip, "M84"))
  print("hotbed to 57'C")
  print(gcode(cardip, "M140 S57"))
  print("enable fast speed upload")
  print(gcode(cardip, "M563 S6"))
  print("pause 9 seconds")
  print(gcode(cardip, "G4 P9000"))
  time.sleep(9)
  result = upload(path, cardip, directory)
  if ("OK" in result):
    sys.stdout.write(" DONE\n")
    if (verify): 
        result = verify_upload(path, cardip, directory)
        if (result):
            sys.stdout.write(" OK\n")
        else:
            sys.stdout.write(" FAILED!\n")
    print("print uploaded file 'cache.gc' from SD card")
    print(gcode(cardip, "M565"))

  elif ("NG" in result):
    sys.stdout.write(" FAILED: NG\n")
  else:
    sys.stdout.write(" FAILED\n")
