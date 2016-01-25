#!/usr/bin/env python
"""
mbed SDK
Copyright (c) 2011-2015 ARM Limited

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

import unittest

from mock import patch
from mbed_host_tests.host_tests_registry import HostRegistry
from mbed_host_tests import mbedhtrun


def detect_test_config_mock():
    return {'test_id': 'MBED_1', 
            'host_test_name': 'host_test_mock', 
            'description': 'Test mbedhtrun', 
            'timeout': '5'}

            
class HostTestClassMock:
    def setup(self):
        global setup_called_flag
        setup_called_flag = True

    def test(self, selftest):
        global test_called_flag
        test_called_flag = True
        return "{{success}}"
        
    def teardown(self):
        global teardown_called_flag
        tearDown_called_flag = True

        
class MbedMock:
    def __init__(self, options):
        self.options = options
        
    def init_serial(self):
        return True
        
    def reset(self):
        return True
        
    def copy_image(self):
        return True

        
class HtOptions:
    def __init__(self,
                micro=None,
                port=None,
                disk=None,
                image_path=None,
                copy_method=None,
                forced_reset_type=None,
                program_cycle_s=None,
                forced_reset_timeout=None,
                enum_host_tests=None,
                list_reg_hts=False,
                list_plugins=False,
                run_binary=False,
                skip_flashing=False,
                skip_reset=False,
                send_break_cmd=False,
                verbose=False,
                version=False):
        
        self.micro=micro
        self.port=port
        self.disk=disk
        self.image_path=image_path
        self.copy_method=copy_method
        self.forced_reset_type=forced_reset_type
        self.program_cycle_s=program_cycle_s
        self.forced_reset_timeout=forced_reset_timeout
        self.enum_host_tests=enum_host_tests
        self.list_reg_hts=list_reg_hts
        self.list_plugins=list_plugins
        self.run_binary=run_binary
        self.skip_flashing=skip_flashing
        self.skip_reset=skip_reset
        self.send_break_cmd=send_break_cmd
        self.verbose=verbose
        self.version=version
 

class OptionParserMock:
    static_options = {}

    def __init__(self):
        pass

    def add_option(self, *args, **kwargs):
        pass

    def parse_args(self):
        return (OptionParserMock.static_options, [])
 

class BaseHostTestTestCase(unittest.TestCase):

    def setUp(self):
        self.HOSTREGISTRY = HostRegistry()

    def tearDown(self):
        pass

    def test_host_test_has_setup_teardown_attribute(self):
        for ht_name in self.HOSTREGISTRY.HOST_TESTS:
            ht = self.HOSTREGISTRY.HOST_TESTS[ht_name]
            self.assertTrue(hasattr(ht, 'setup'))
            self.assertTrue(hasattr(ht, 'teardown'))

    def test_host_test_has_no_rampUpDown_attribute(self):
        for ht_name in self.HOSTREGISTRY.HOST_TESTS:
            ht = self.HOSTREGISTRY.HOST_TESTS[ht_name]
            self.assertFalse(hasattr(ht, 'rampUp'))
            self.assertFalse(hasattr(ht, 'rampDown'))
    
    @patch('mbed_host_tests.OptionParser')
    @patch('mbed_host_tests.DefaultTestSelector.detect_test_config')
    @patch('mbed_host_tests.host_tests_runner.host_test.Mbed')
    def test_run_test(self, mbed_mock, detectTestConfig_mock, optionParser_mock):
        self.HOSTREGISTRY.register_host_test('host_test_mock', HostTestClassMock())  
        mbed_mock.side_effect = MbedMock
        detectTestConfig_mock.return_value = detect_test_config_mock()
        
        my_ht_opts = HtOptions(verbose=True)
        OptionParserMock.static_options = my_ht_opts
        optionParser_mock.side_effect = OptionParserMock
        
        global setup_called_flag  
        global test_called_flag 
        global teardown_called_flag 
        setup_called_flag = False
        test_called_flag = False
        teardown_called_flag = False
        
        mbedhtrun.main()
        
        self.assertTrue(True, setup_called_flag)
        self.assertTrue(True, test_called_flag)
        self.assertTrue(True, teardown_called_flag)
    
if __name__ == '__main__':
    unittest.main()
