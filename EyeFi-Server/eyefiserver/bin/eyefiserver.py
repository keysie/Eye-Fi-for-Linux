#!/usr/bin/env python

"""
* Copyright (c) 2009, Jeffrey Tchang
* Additional *pike
* All rights reserved.
*
*
* THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY
* EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


import string
import cgi
import time

import sys
import os
import socket
import thread
import StringIO

import hashlib
import binascii
import select 
import tarfile

import xml.sax
from xml.sax.handler import ContentHandler 
import xml.dom.minidom

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import BaseHTTPServer

import SocketServer

import logging

#pike
from datetime import datetime
import ConfigParser


"""
General architecture notes


This is a standalone Eye-Fi Server that is designed to take the place of the Eye-Fi Manager.


Starting this server creates a listener on port 59278. I use the BaseHTTPServer class included
with Python. I look for specific POST/GET request URLs and execute functions based on those
URLs. 




"""




# Create the main logger
eyeFiLogger = logging.Logger("eyeFiLogger",logging.DEBUG)

# Create two handlers. One to print to the log and one to print to the console
consoleHandler = logging.StreamHandler(sys.stdout)

# Set how both handlers will print the pretty log events
eyeFiLoggingFormat = logging.Formatter("[%(asctime)s][%(funcName)s] - %(message)s",'%m/%d/%y %I:%M%p')
consoleHandler.setFormatter(eyeFiLoggingFormat)

# Append both handlers to the main Eye Fi Server logger
eyeFiLogger.addHandler(consoleHandler)

 


# Eye Fi XML SAX ContentHandler
class EyeFiContentHandler(ContentHandler):

  # These are the element names that I want to parse out of the XML    
  elementNamesToExtract = ["macaddress","cnonce","transfermode","transfermodetimestamp","fileid","filename","filesize","filesignature"]  

  # For each of the element names I create a dictionary with the value to False
  elementsToExtract = {}

  # Where to put the extracted values
  extractedElements = {}


  def __init__(self):
    self.extractedElements = {}
    
    for elementName in self.elementNamesToExtract:
        self.elementsToExtract[elementName] = False
  
  def startElement(self, name, attributes):
  
    # If the name of the element is a key in the dictionary elementsToExtract
    # set the value to True
    if name in self.elementsToExtract:
      self.elementsToExtract[name] = True

  def endElement(self, name):

    # If the name of the element is a key in the dictionary elementsToExtract
    # set the value to False
    if name in self.elementsToExtract:
      self.elementsToExtract[name] = False


  def characters(self, content):
  
    for elementName in self.elementsToExtract:
      if self.elementsToExtract[elementName] == True:
        self.extractedElements[elementName] = content

# Implements an EyeFi server
class EyeFiServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):

  
  def server_bind(self):

    BaseHTTPServer.HTTPServer.server_bind(self)    
    self.socket.settimeout(None)
    self.run = True

  def get_request(self):  
    while self.run:
      try:
        connection, address = self.socket.accept()
        eyeFiLogger.debug("Incoming connection from client %s" % address[0])

        connection.settimeout(None)
        return (connection, address)
        
      except socket.timeout:
        pass

  #def stop(self):
  #  self.run = False

  # alt serve_forever method for python <2.6
  # because we want a shutdown mech ..
  #def serve(self):
  #  while self.run:
  #    self.handle_request()
  #  self.socket.close()



# This class is responsible for handling HTTP requests passed to it.
# It implements the two most common HTTP methods, do_GET() and do_POST()

class EyeFiRequestHandler(BaseHTTPRequestHandler):

  # pike: these seem unused ?
  protocol_version = 'HTTP/1.1'
  sys_version = ""
  server_version = "Eye-Fi Agent/2.0.4.0 (Windows XP SP2)"    

  
  def do_GET(self):

    eyeFiLogger.debug(self.command + " " + self.path + " " + self.request_version)
    
    SOAPAction = ""
    eyeFiLogger.debug("Headers received in GET request:")
    for headerName in self.headers.keys():
      for headerValue in self.headers.getheaders(headerName):
        eyeFiLogger.debug(headerName + ": " + headerValue)
        if( headerName == "soapaction"):
          SOAPAction = headerValue
          
    # couldnt get this to work ..
    #if((self.client_address == "localhost") and (self.path == "/api/soap/eyefilm/v1x") and (SOAPAction == "\"urn:StopServer\"")):
    #  eyeFiLogger.debug("Got StopServer request .. stopping server")
    #  self.server.stop()
    # or, for python 2.6>
    #  self.server.shutdown()
      
    self.send_response(200)
    self.send_header('Content-type','text/html')
    # I should be sending a Content-Length header with HTTP/1.1 but I am being lazy
    # self.send_header('Content-length', '123')
    self.end_headers()
    self.wfile.write(self.client_address)
    self.wfile.write(self.headers)
    self.close_connection = 0
    

  def do_POST(self):
    eyeFiLogger.debug(self.command + " " + self.path + " " + self.request_version)

    SOAPAction = ""
    contentLength = ""

    # Loop through all the request headers and pick out ones that are relevant    
    
    eyeFiLogger.debug("Headers received in POST request:")
    for headerName in self.headers.keys():
      for headerValue in self.headers.getheaders(headerName):

        if( headerName == "soapaction"):
          SOAPAction = headerValue
        
        if( headerName == "content-length"):
          contentLength = int(headerValue)

        eyeFiLogger.debug(headerName + ": " + headerValue)

    
    # Read contentLength bytes worth of data
    eyeFiLogger.debug("Attempting to read " + str(contentLength) + " bytes of data")
    postData = self.rfile.read(contentLength)
    eyeFiLogger.debug("Finished reading " + str(contentLength) + " bytes of data")

    # TODO: Implement some kind of visual progress bar
    # bytesRead = 0
    # postData = ""
    
    # while(bytesRead < contentLength):
    #  postData = postData + self.rfile.read(1)
    #   bytesRead = bytesRead + 1
      
    #  if(bytesRead % 10000 == 0):
    #    print "#",    


    # Perform action based on path and SOAPAction
    # A SOAPAction of StartSession indicates the beginning of an EyeFi
    # authentication request
    if((self.path == "/api/soap/eyefilm/v1") and (SOAPAction == "\"urn:StartSession\"")):
      eyeFiLogger.debug("Got StartSession request")
      response = self.startSession(postData)
      contentLength = len(response)

      eyeFiLogger.debug("StartSession response: " + response)
            
      self.send_response(200)
      self.send_header('Date', self.date_time_string())      
      self.send_header('Pragma','no-cache')
      self.send_header('Server','Eye-Fi Agent/2.0.4.0 (Windows XP SP2)')
      self.send_header('Content-Type','text/xml; charset="utf-8"') 
      self.send_header('Content-Length', contentLength)
      self.end_headers()
      
      self.wfile.write(response)
      self.wfile.flush()
      self.handle_one_request()
    
    # GetPhotoStatus allows the card to query if a photo has been uploaded
    # to the server yet
    if((self.path == "/api/soap/eyefilm/v1") and (SOAPAction == "\"urn:GetPhotoStatus\"")):
      eyeFiLogger.debug("Got GetPhotoStatus request")

      response = self.getPhotoStatus(postData)
      contentLength = len(response)

      eyeFiLogger.debug("GetPhotoStatus response: " + response)
      
      self.send_response(200)
      self.send_header('Date', self.date_time_string())      
      self.send_header('Pragma','no-cache')
      self.send_header('Server','Eye-Fi Agent/2.0.4.0 (Windows XP SP2)')
      self.send_header('Content-Type','text/xml; charset="utf-8"') 
      self.send_header('Content-Length', contentLength)
      self.end_headers()
      
      self.wfile.write(response)
      self.wfile.flush()

      
    # If the URL is upload and there is no SOAPAction the card is ready to send a picture to me  
    if((self.path == "/api/soap/eyefilm/v1/upload") and (SOAPAction == "")):
      eyeFiLogger.debug("Got upload request")      
      response = self.uploadPhoto(postData)
      contentLength = len(response)

      eyeFiLogger.debug("Upload response: " + response)

      self.send_response(200)
      self.send_header('Date', self.date_time_string())      
      self.send_header('Pragma','no-cache')
      self.send_header('Server','Eye-Fi Agent/2.0.4.0 (Windows XP SP2)')
      self.send_header('Content-Type','text/xml; charset="utf-8"') 
      self.send_header('Content-Length', contentLength)
      self.end_headers()
      
      self.wfile.write(response)
      self.wfile.flush()

    # If the URL is upload and SOAPAction is MarkLastPhotoInRoll
    if((self.path == "/api/soap/eyefilm/v1") and (SOAPAction == "\"urn:MarkLastPhotoInRoll\"")):
      eyeFiLogger.debug("Got MarkLastPhotoInRoll request")      
      response = self.markLastPhotoInRoll(postData)
      contentLength = len(response)
      
      eyeFiLogger.debug("MarkLastPhotoInRoll response: " + response)
      self.send_response(200)
      self.send_header('Date', self.date_time_string())      
      self.send_header('Pragma','no-cache')
      self.send_header('Server','Eye-Fi Agent/2.0.4.0 (Windows XP SP2)')
      self.send_header('Content-Type','text/xml; charset="utf-8"') 
      self.send_header('Content-Length', contentLength)
      self.send_header('Connection', 'Close')      
      self.end_headers()
      
      self.wfile.write(response)
      self.wfile.flush()
      
      eyeFiLogger.debug("Connection closed.")


  # Handles MarkLastPhotoInRoll action
  def markLastPhotoInRoll(self,postData):
    # Create the XML document to send back
    doc = xml.dom.minidom.Document()

    SOAPElement = doc.createElementNS("http://schemas.xmlsoap.org/soap/envelope/","SOAP-ENV:Envelope")
    SOAPElement.setAttribute("xmlns:SOAP-ENV","http://schemas.xmlsoap.org/soap/envelope/")    
    SOAPBodyElement = doc.createElement("SOAP-ENV:Body")

    markLastPhotoInRollResponseElement = doc.createElement("MarkLastPhotoInRollResponse")
    
    SOAPBodyElement.appendChild(markLastPhotoInRollResponseElement)
    SOAPElement.appendChild(SOAPBodyElement)
    doc.appendChild(SOAPElement)

    return doc.toxml(encoding="UTF-8")


  # Handles receiving the actual photograph from the card.
  # postData will most likely contain multipart binary post data that needs to be parsed 
  def uploadPhoto(self,postData):
    
    # Take the postData string and work with it as if it were a file object
    postDataInMemoryFile = StringIO.StringIO(postData)
    
    # Get the content-type header which looks something like this
    # content-type: multipart/form-data; boundary=---------------------------02468ace13579bdfcafebabef00d    
    contentTypeHeader = self.headers.getheaders('content-type').pop()
    eyeFiLogger.debug(contentTypeHeader)
    
    # Extract the boundary parameter in the content-type header
    headerParameters = contentTypeHeader.split(";")
    eyeFiLogger.debug(headerParameters)      
    
    boundary = headerParameters[1].split("=")
    boundary = boundary[1].strip()
    eyeFiLogger.debug("Extracted boundary: " + boundary)          
    
    # eyeFiLogger.debug("uploadPhoto postData: " + postData)
    
    # Parse the multipart/form-data
    form = cgi.parse_multipart(postDataInMemoryFile, {"boundary":boundary,"content-disposition":self.headers.getheaders('content-disposition')})
    eyeFiLogger.debug("Available multipart/form-data: " + str(form.keys()))
    
    # Parse the SOAPENVELOPE using the EyeFiContentHandler()
    soapEnvelope = form['SOAPENVELOPE'][0]
    eyeFiLogger.debug("SOAPENVELOPE: " + soapEnvelope)
    handler = EyeFiContentHandler()
    parser = xml.sax.parseString(soapEnvelope,handler)

    eyeFiLogger.debug("Extracted elements: " + str(handler.extractedElements))
   
    
    imageTarfileName = handler.extractedElements["filename"]

    #pike
    #uid = self.server.config.getint('EyeFiServer','upload_uid')
    #gid = self.server.config.getint('EyeFiServer','upload_gid')
    #mode = self.server.config.get('EyeFiServer','upload_mode')
    #eyeFiLogger.debug("Using uid/gid %d/%d"%(uid,gid))
    #eyeFiLogger.debug("Using mode " + mode)
    
    now = datetime.now()
    uploadDir = now.strftime(self.server.config.get('EyeFiServer','upload_dir'))
    if not os.path.isdir(uploadDir):
      os.makedirs(uploadDir)
      #if uid!=0 and gid!=0:
      #  os.chown(uploadDir,uid,gid)
      #if mode!="":
      #  os.chmod(uploadDir,string.atoi(mode))
         
    imageTarPath = os.path.join(uploadDir,imageTarfileName)
    eyeFiLogger.debug("Generated path " + imageTarPath)
    

    fileHandle = open(imageTarPath, 'wb')
    eyeFiLogger.debug("Opened file " + imageTarPath + " for binary writing")

    fileHandle.write(form['FILENAME'][0])
    eyeFiLogger.debug("Wrote file " + imageTarPath)

    fileHandle.close()
    eyeFiLogger.debug("Closed file " + imageTarPath)
        
    #if uid!=0 and gid!=0:
    #  os.chown(imageTarPath,uid,gid)
    #if mode!="":
    #  os.chmod(imageTarPath,string.atoi(mode))
         
    eyeFiLogger.debug("Extracting TAR file " + imageTarPath)
    imageTarfile = tarfile.open(imageTarPath)
    imageTarfile.extractall(path=uploadDir)

    eyeFiLogger.debug("Closing TAR file " + imageTarPath)
    imageTarfile.close()

    eyeFiLogger.debug("Deleting TAR file " + imageTarPath)
	
	#remove .log Files after extracting the tarfile (patched by swiffer)
    logFiles = os.listdir(uploadDir)
    for f in logFiles:
	  if not os.path.isdir(f) and ".log" in f:
	    os.remove(os.path.join(uploadDir,f))
	
    os.remove(imageTarPath)

    # Create the XML document to send back
    doc = xml.dom.minidom.Document()

    SOAPElement = doc.createElementNS("http://schemas.xmlsoap.org/soap/envelope/","SOAP-ENV:Envelope")
    SOAPElement.setAttribute("xmlns:SOAP-ENV","http://schemas.xmlsoap.org/soap/envelope/")    
    SOAPBodyElement = doc.createElement("SOAP-ENV:Body")
    
    uploadPhotoResponseElement = doc.createElement("UploadPhotoResponse")
    successElement = doc.createElement("success")
    successElementText = doc.createTextNode("true")

    successElement.appendChild(successElementText)
    uploadPhotoResponseElement.appendChild(successElement)
    
    SOAPBodyElement.appendChild(uploadPhotoResponseElement)
    SOAPElement.appendChild(SOAPBodyElement)
    doc.appendChild(SOAPElement)

    return doc.toxml(encoding="UTF-8")
  
    
  def getPhotoStatus(self,postData):
    handler = EyeFiContentHandler()
    parser = xml.sax.parseString(postData,handler)

    # Create the XML document to send back
    doc = xml.dom.minidom.Document()

    SOAPElement = doc.createElementNS("http://schemas.xmlsoap.org/soap/envelope/","SOAP-ENV:Envelope")
    SOAPElement.setAttribute("xmlns:SOAP-ENV","http://schemas.xmlsoap.org/soap/envelope/")    
    SOAPBodyElement = doc.createElement("SOAP-ENV:Body")
    
    getPhotoStatusResponseElement = doc.createElement("GetPhotoStatusResponse")
    getPhotoStatusResponseElement.setAttribute("xmlns","http://localhost/api/soap/eyefilm")

    fileidElement = doc.createElement("fileid")
    fileidElementText = doc.createTextNode("1")
    fileidElement.appendChild(fileidElementText)
    
    offsetElement = doc.createElement("offset")
    offsetElementText = doc.createTextNode("0")
    offsetElement.appendChild(offsetElementText)
    
    getPhotoStatusResponseElement.appendChild(fileidElement)
    getPhotoStatusResponseElement.appendChild(offsetElement)
    
    SOAPBodyElement.appendChild(getPhotoStatusResponseElement)
    
    SOAPElement.appendChild(SOAPBodyElement)
    doc.appendChild(SOAPElement)

    return doc.toxml(encoding="UTF-8")
    
     
  def startSession(self, postData):  
    eyeFiLogger.debug("Delegating the XML parsing of startSession postData to EyeFiContentHandler()")
    handler = EyeFiContentHandler()
    parser = xml.sax.parseString(postData,handler)
    
    eyeFiLogger.debug("Extracted elements: " + str(handler.extractedElements))
    
    # Retrieve it from C:\Documents and Settings\<User>\Application Data\Eye-Fi\Settings.xml
    
    eyeFiLogger.debug("Setting Eye-Fi upload key to " + self.server.config.get('EyeFiServer','upload_key'))
    
    credentialString = handler.extractedElements["macaddress"] + handler.extractedElements["cnonce"] + self.server.config.get('EyeFiServer','upload_key');
    eyeFiLogger.debug("Concatenated credential string (pre MD5): " + credentialString)

    # Return the binary data represented by the hexadecimal string
    # resulting in something that looks like "\x00\x18V\x03\x04..."
    binaryCredentialString = binascii.unhexlify(credentialString)
    
    # Now MD5 hash the binary string    
    m = hashlib.md5()
    m.update(binaryCredentialString)
    
    # Hex encode the hash to obtain the final credential string
    credential = m.hexdigest()

    # Create the XML document to send back
    doc = xml.dom.minidom.Document()
    
    SOAPElement = doc.createElementNS("http://schemas.xmlsoap.org/soap/envelope/","SOAP-ENV:Envelope")
    SOAPElement.setAttribute("xmlns:SOAP-ENV","http://schemas.xmlsoap.org/soap/envelope/")    
    SOAPBodyElement = doc.createElement("SOAP-ENV:Body")
    

    startSessionResponseElement = doc.createElement("StartSessionResponse")
    startSessionResponseElement.setAttribute("xmlns","http://localhost/api/soap/eyefilm")

    credentialElement = doc.createElement("credential")
    credentialElementText = doc.createTextNode(credential)
    credentialElement.appendChild(credentialElementText)
    
    snonceElement = doc.createElement("snonce")
    snonceElementText = doc.createTextNode("99208c155fc1883579cf0812ec0fe6d2")
    snonceElement.appendChild(snonceElementText)
    
    transfermodeElement = doc.createElement("transfermode")
    transfermodeElementText = doc.createTextNode("2")
    transfermodeElement.appendChild(transfermodeElementText)

    transfermodetimestampElement = doc.createElement("transfermodetimestamp")
    transfermodetimestampElementText = doc.createTextNode("1230268824")
    transfermodetimestampElement.appendChild(transfermodetimestampElementText)

    upsyncallowedElement = doc.createElement("upsyncallowed")
    upsyncallowedElementText = doc.createTextNode("false")
    upsyncallowedElement.appendChild(upsyncallowedElementText)


    startSessionResponseElement.appendChild(credentialElement)
    startSessionResponseElement.appendChild(snonceElement)
    startSessionResponseElement.appendChild(transfermodeElement)
    startSessionResponseElement.appendChild(transfermodetimestampElement)
    startSessionResponseElement.appendChild(upsyncallowedElement)

    SOAPBodyElement.appendChild(startSessionResponseElement)
    
    SOAPElement.appendChild(SOAPBodyElement)
    doc.appendChild(SOAPElement)


    return doc.toxml(encoding="UTF-8")


def main():
  
  if len(sys.argv) < 2:
        print "usage: %s configfile logfile" % os.path.basename(sys.argv[0])
        sys.exit(2)

  configfile = sys.argv[1]
  eyeFiLogger.info("Reading config " + configfile)

  config = ConfigParser.SafeConfigParser()
  config.read(configfile)
  
  # open file logging
  logfile = sys.argv[2]
  fileHandler = logging.FileHandler(logfile,"w",encoding=None)
  fileHandler.setFormatter(eyeFiLoggingFormat)
  eyeFiLogger.addHandler(fileHandler)

  
  server_address = (config.get('EyeFiServer','host_name'), config.getint('EyeFiServer','host_port'))
  
  # run webserver as www-data - cant get it working
  #if config.get('EyeFiServer','user_id')!='':
  #  os.setuid(config.getint('EyeFiServer','user_id'))
    
  try:
    # Create an instance of an HTTP server. Requests will be handled
    # by the class EyeFiRequestHandler
    eyeFiServer = EyeFiServer(server_address, EyeFiRequestHandler)
    eyeFiServer.config = config
    
    # Spawn a new thread for the server    
    # thread.start_new_thread(eyeFiServer.serve, ())
    # eyeFiLogger.info("Eye-Fi server started listening on port " + str(server_address[1]))

    eyeFiLogger.info("Eye-Fi server started listening on port " + str(server_address[1]))
    eyeFiServer.serve_forever() 
         
    #raw_input("\nPress <RETURN> to stop server\n")    
    #eyeFiServer.stop()
    #eyeFiLogger.info("Eye-Fi server stopped")
    #eyeFiServer.socket.close()
    
  except KeyboardInterrupt:
    eyeFiServer.socket.close()
    #eyeFiServer.shutdown()

  #eyeFiLogger.info("Eye-Fi server stopped")

if __name__ == '__main__':
    main()

