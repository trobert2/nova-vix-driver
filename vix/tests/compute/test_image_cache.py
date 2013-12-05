# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import os
import unittest
import sys

if sys.platform == 'win32':
    import _winreg
    import win32api

from vix.compute import image_cache


class VixUtilsTestCase(unittest.TestCase):
    """Unit tests for utility class"""

    def setUp(self):
        self._image_cache = image_cache.ImageCache()
