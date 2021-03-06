#!/usr/bin/env python3
#
#   Copyright 2016 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest


class ActsImportTestUtilsTest(unittest.TestCase):
    """This test class has unit tests for the implementation of everything
    under acts_contrib.test_utils.*
    """

    def test_import_successful(self):
        """ Test to return true if all imports were successful.

        This test will fail if any import was unsuccessful.
        """
        try:
            from acts import utils

            from acts_contrib.test_utils.bt import BleEnum
            from acts_contrib.test_utils.bt import BluetoothBaseTest
            from acts_contrib.test_utils.bt import BluetoothCarHfpBaseTest
            from acts_contrib.test_utils.bt import BtEnum
            from acts_contrib.test_utils.bt import GattConnectedBaseTest
            from acts_contrib.test_utils.bt import GattEnum
            from acts_contrib.test_utils.bt import bt_contacts_utils
            from acts_contrib.test_utils.bt import bt_gatt_utils
            from acts_contrib.test_utils.bt import bt_test_utils
            from acts_contrib.test_utils.bt import native_bt_test_utils

            from acts_contrib.test_utils.car import car_bt_utils
            from acts_contrib.test_utils.car import car_media_utils
            from acts_contrib.test_utils.car import car_telecom_utils
            from acts_contrib.test_utils.car import tel_telecom_utils

            from acts_contrib.test_utils.net import connectivity_const
            from acts_contrib.test_utils.net import connectivity_const

            from acts_contrib.test_utils.tel import TelephonyBaseTest
            from acts_contrib.test_utils.tel import tel_atten_utils
            from acts_contrib.test_utils.tel import tel_data_utils
            from acts_contrib.test_utils.tel import tel_defines
            from acts_contrib.test_utils.tel import tel_lookup_tables
            from acts_contrib.test_utils.tel import tel_subscription_utils
            from acts_contrib.test_utils.tel import tel_test_utils
            from acts_contrib.test_utils.tel import tel_video_utils
            from acts_contrib.test_utils.tel import tel_voice_utils

            from acts_contrib.test_utils.wifi import wifi_constants
            from acts_contrib.test_utils.wifi import wifi_test_utils

        except Exception:
            self.fail('Unable to import all supported test_utils')


if __name__ == '__main__':
    unittest.main()
