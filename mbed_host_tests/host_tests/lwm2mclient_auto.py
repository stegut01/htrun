"""
mbed SDK
Copyright (c) 2011-2013 ARM Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import uuid
import urllib
import urllib2
import base64
import json
import re
from sys import stdout

class TestConfiguration():
    BOOTSTRAP_SERVER = ""
    BOOTSTRAP_PORT = ""
    MDS_SERVER = ""
    MDS_PORT = ""
    DOMAIN = ""
    BOOTSTRAP_ADDRESS = "coap://%s:%s" % (BOOTSTRAP_SERVER, BOOTSTRAP_PORT)
    MDS_ADDRESS = "coap://%s:%s" % (MDS_SERVER, MDS_PORT)
    BOOTSTRAP_USER = ""
    BOOTSTRAP_PASS = ""

class BootstrapServerAdapter():
    def __init__(self, configuration):
        self.config = configuration
    
    def CreateAuthRequest(self, address):
        request = urllib2.Request(address)
        auth = base64.encodestring("%s:%s" % (self.config.BOOTSTRAP_USER, self.config.BOOTSTRAP_PASS)).strip()
        request.add_header("Authorization", "Basic %s" % auth)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        return request
    
    def GetOMAServers(self):
        request = self.CreateAuthRequest("http://%s:8090/rest-api/oma-servers" % self.config.BOOTSTRAP_SERVER)
        result = urllib2.urlopen(request)
        servers = json.loads(result.read())
        return servers
    
    def AddClientMapping(self, endpointName):
        """ Adds new client with endpointName as name to domain in OMA server.
        """     
        server_id = None
        
        if not endpointName:
            endpointName = "lwm2m-client-tester"
           
        # Get OMA server id
        servers = self.GetOMAServers()
        for oma_server in servers:
            if oma_server["name"] == self.config.DOMAIN:
                server_id = oma_server["id"]
                break
        
        if not server_id:
            return
        
        mapping = {"name" : endpointName, "omaServerId" : server_id}
        
        request = self.CreateAuthRequest("http://%s:8090/rest-api/oma-clients/%s" % (self.config.BOOTSTRAP_SERVER, endpointName))
        request.add_data(json.dumps(mapping))
        result = urllib2.urlopen(request)
        
    def DeleteClientMapping(self, endpointName):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = self.CreateAuthRequest("http://%s:8090/rest-api/oma-clients/%s" % (self.config.BOOTSTRAP_SERVER, endpointName))
        request.get_method = lambda: "DELETE"
        result = opener.open(request)

class LWM2MClientAutoTest():
    """ A simple LWM2M client test that sends bootstrap and mds server information to 
        DUT and waits for test result print from DUT.
    """
    
    testconfig = TestConfiguration()
        
    """ Function for configuring test parameters of DUT.
    """
    def send_configuration(self, selftest):
        selftest.notify("HOST: Waiting for DUT to start...")
        
        c = selftest.mbed.serial_readline()
        if c is None:
            selftest.print_result(selftest.RESULT_IO_SERIAL)
            return
        selftest.notify(c.strip())

        selftest.notify("HOST: Sending test configuration to DUT...")
        config_str = "<%s><%s><%s>\r\n" % (self.testconfig.BOOTSTRAP_ADDRESS, self.testconfig.MDS_ADDRESS, self.testconfig.DOMAIN)
        selftest.notify("HOST: Sending configuration: %s" % config_str)
        selftest.mbed.serial_write(config_str)

    def read_endpointname(self, selftest):
        epname = None
        read = ""
        while True:
            inp = selftest.mbed.serial_readline(64)
            if inp:
                read += inp
            if "endpoint_name=" in read:
                break
            
        name = re.search("endpoint_name=([\w:-]+)", inp)
        if name:
            epname = name.group(1)
            selftest.notify("HOST: Using endpoint name: %s" % epname)
            
        return epname
    
    def test(self, selftest):
        result = selftest.RESULT_PASSIVE
        testoutput = ""
        
        # Send test configuration to MUT
        self.send_configuration(selftest)
        
        # Read unique endpoint name from MUT
        self.testconfig.EP_NAME = self.read_endpointname(selftest)        
            
        # Add endpoint name as a client to OMA bootstrap server
        bootstrap_server = BootstrapServerAdapter(self.testconfig)
        bootstrap_server.AddClientMapping(self.testconfig.EP_NAME)
        
        try:
            while True:
                c = selftest.mbed.serial_read(512)
                if c is None:
                    result = selftest.RESULT_IO_SERIAL
                stdout.write(c)
                stdout.flush()     
        except KeyboardInterrupt, _:
            selftest.notify("\r\n[CTRL+C] exit")
            result = selftest.RESULT_ERROR
        
        bootstrap_server.DeleteClientMapping(self.testconfig.EP_NAME)
        
        return result
