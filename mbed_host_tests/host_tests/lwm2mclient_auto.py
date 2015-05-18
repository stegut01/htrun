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

import urllib2
import base64
import json
import re
from sys import stdout
import time

class TestConfiguration():
    OWN_PC_ADDRESS = "10.45.2.27"
    #BOOTSTRAP_SERVER = "10.45.3.10"
    BOOTSTRAP_SERVER = OWN_PC_ADDRESS
    BOOTSTRAP_PORT = "5693"
    #MDS_SERVER = "10.45.3.10"
    MDS_SERVER = OWN_PC_ADDRESS
    MDS_PORT = "5683"
    BOOTSTRAP_SERVER_NAME = "test" #todo rename this to 
    BOOTSTRAP_ADDRESS = "coap://%s:%s" % (BOOTSTRAP_SERVER, BOOTSTRAP_PORT)
    MDS_ADDRESS = "coap://%s:%s" % (MDS_SERVER, MDS_PORT)
    BOOTSTRAP_USER = "admin"
    BOOTSTRAP_PASS = "admin"

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
        #puukko
        #selftest.notify("Host: servers: %s" % servers)
        
        return servers
    
    def GetOMAClients(self):
        request = self.CreateAuthRequest("http://%s:8090/rest-api/oma-clients" % self.config.BOOTSTRAP_SERVER)
        result = urllib2.urlopen(request)
        clients = json.loads(result.read())
        return clients
    
    def GetOMAServerId(self, server_name):
        server_id = None
        
        # Get OMA server id
        servers = self.GetOMAServers()
        for oma_server in servers:
            if oma_server["name"] == server_name:
                server_id = oma_server["id"]
                break
        
        return server_id
    
    def ClientMappingExists(self, endpointName):
        clients = self.GetOMAClients()
        for client in clients:
            if client["name"] == endpointName:
                return True
        return False
    
    def AddClientMapping(self, endpointName):
        """ Adds new client with endpointName as name to domain in OMA server.
        """
        
        if not endpointName:
            endpointName = "lwm2m-client-tester"
           
        server_id = self.GetOMAServerId(self.config.BOOTSTRAP_SERVER_NAME)
        
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
        config_str = "<%s><%s><%s>\r\n" % (self.testconfig.BOOTSTRAP_ADDRESS, self.testconfig.MDS_ADDRESS, self.testconfig.BOOTSTRAP_SERVER_NAME)
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
    
    def suite_result_check(self, ser, selftest):
        m = re.search("Suite: result (success|failure)", ser)
        if not m:
            return selftest.RESULT_FAILURE
        
        if m.group(1) == "success":
            return selftest.RESULT_SUCCESS
        
        return selftest.RESULT_FAILURE

# This is not in use, saved for future development.
#    
#     def detect_local_bootstrap_server(self):
#         (hostname, aliaslist, ipaddresslist) = socket.gethostbyname_ex(socket.gethostname())
#         
#         conf = TestConfiguration()
#         #ipaddresslist = ['10.45.2.11', 'localhost']
#         for ip in ipaddresslist:
#             #print "IP:" + ip
#             try:
#                 conf.BOOTSTRAP_SERVER = ip
#                 adapter = BootstrapServerAdapter(conf)
#                 servers = adapter.GetOMAServers()
#                 print "Servers for %s: %s" % (ip, servers)
#             except:
#                 print "exception"
                
    def test(self, selftest):
        result = selftest.RESULT_PASSIVE
        testoutput = ""
        
        # Send test configuration to MUT
        self.send_configuration(selftest)
        
        # Read unique endpoint name from MUT
        self.testconfig.EP_NAME = self.read_endpointname(selftest)        
            
        # Add endpoint name as a client to OMA bootstrap server if it doesn't already exist
        bootstrap_server = BootstrapServerAdapter(self.testconfig)
        if not bootstrap_server.ClientMappingExists(self.testconfig.EP_NAME):
            selftest.notify("Host: Adding OMA bootstrap client mapping for %s" % self.testconfig.EP_NAME)
            bootstrap_server.AddClientMapping(self.testconfig.EP_NAME)
        
        start_time = time.time()
        try:
            while True:
                c = selftest.mbed.serial_read(512)
                if c is None:
                    result = selftest.RESULT_IO_SERIAL
                stdout.write(c)
                stdout.flush()
                testoutput += c
                # Check for suite result
                if "Suite: result" in testoutput:
                    result = self.suite_result_check(testoutput, selftest)
                    break
                    
        except KeyboardInterrupt, _:
            selftest.notify("\r\n[CTRL+C] exit")
            result = selftest.RESULT_ERROR
        
        selftest.notify("Host: Deleting OMA bootstrap client mapping for %s" % self.testconfig.EP_NAME)
        
        bootstrap_server.DeleteClientMapping(self.testconfig.EP_NAME)

        elapsedTime = time.time() - start_time
        selftest.notify("Host:Test completed in %.0f seconds\n" % elapsedTime)
        
        return result
