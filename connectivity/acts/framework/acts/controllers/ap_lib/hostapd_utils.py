#   Copyright 2019 - The Android Open Source Project
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

from acts import utils
from acts.controllers.ap_lib import hostapd_config
from acts.controllers.ap_lib import hostapd_constants


def generate_random_password(security_mode=None, length=None, hex=None):
    """Generates a random password. Defaults to an 8 character ASCII password.

    Args:
        security_mode: optional string, security type. Used to determine if
            length should be WEP compatible (useful for generated tests to simply
            pass in security mode)
        length: optional int, length of password to generate. Defaults to 8,
            unless security_mode is WEP, then 13
        hex: optional int, if True, generates a hex string, else ascii
    """
    if hex:
        generator_func = utils.rand_hex_str
    else:
        generator_func = utils.rand_ascii_str

    if length:
        return generator_func(length)
    if security_mode and security_mode.lower() == hostapd_constants.WEP_STRING:
        return generator_func(hostapd_constants.WEP_DEFAULT_STR_LENGTH)
    else:
        return generator_func(hostapd_constants.MIN_WPA_PSK_LENGTH)


def verify_interface(interface, valid_interfaces):
    """Raises error if interface is missing or invalid
    Args:
        interface: string of interface name
        valid_interfaces: list of valid interface names
    """
    if not interface:
        raise ValueError('Required wlan interface is missing.')
    if interface not in valid_interfaces:
        raise ValueError('Invalid interface name was passed: %s' % interface)


def verify_security_mode(security_profile, valid_security_modes):
    """Raises error if security mode is not in list of valid security modes.

    Args:
        security_profile: a hostapd_security.Security object.
        valid_security_modes: a list of valid security modes for a profile. Must
            include None if open security is valid.
    """
    if security_profile is None:
        if None not in valid_security_modes:
            raise ValueError('Open security is not allowed for this profile.')
    elif security_profile.security_mode not in valid_security_modes:
        raise ValueError(
            'Invalid Security Mode: %s. '
            'Valid Security Modes for this profile: %s.' %
            (security_profile.security_mode, valid_security_modes))


def verify_cipher(security_profile, valid_ciphers):
    """Raise error if cipher is not in list of valid ciphers.

    Args:
        security_profile: a hostapd_security.Security object.
        valid_ciphers: a list of valid ciphers for a profile.
    """
    if security_profile is None:
        raise ValueError('Security mode is open.')
    elif security_profile.security_mode == hostapd_constants.WPA1:
        if security_profile.wpa_cipher not in valid_ciphers:
            raise ValueError('Invalid WPA Cipher: %s. '
                             'Valid WPA Ciphers for this profile: %s' %
                             (security_profile.wpa_cipher, valid_ciphers))
    elif security_profile.security_mode == hostapd_constants.WPA2:
        if security_profile.wpa2_cipher not in valid_ciphers:
            raise ValueError('Invalid WPA2 Cipher: %s. '
                             'Valid WPA2 Ciphers for this profile: %s' %
                             (security_profile.wpa2_cipher, valid_ciphers))
    else:
        raise ValueError('Invalid Security Mode: %s' %
                         security_profile.security_mode)
