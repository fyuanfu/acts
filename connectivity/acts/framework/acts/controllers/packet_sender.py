#!/usr/bin/env python3.4
#
#   Copyright 2017 - The Android Open Source Project
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
"""Collection of utility functions to generate and send custom packets.

"""
import logging
import multiprocessing
import socket
import time

import acts.signals

# http://www.secdev.org/projects/scapy/
# On ubuntu, sudo pip3 install scapy
import scapy.all as scapy

MOBLY_CONTROLLER_CONFIG_NAME = 'PacketSender'
ACTS_CONTROLLER_REFERENCE_NAME = 'packet_senders'

GET_FROM_LOCAL_INTERFACE = 'get_local'
MAC_BROADCAST = 'ff:ff:ff:ff:ff:ff'
IPV4_BROADCAST = '255.255.255.255'
ARP_DST = '00:00:00:00:00:00'
RA_MAC = '33:33:00:00:00:01'
RA_IP = 'ff02::1'
RA_PREFIX = 'd00d::'
RA_PREFIX_LEN = 64
DHCP_OFFER_OP = 2
DHCP_OFFER_SRC_PORT = 67
DHCP_OFFER_DST_PORT = 68
DHCP_TRANS_ID = 0x01020304
DNS_LEN = 3
PING6_DATA = 'BEST PING6 EVER'
PING4_TYPE = 8
MDNS_TTL = 255
MDNS_QTYPE = 'PTR'
MDNS_UDP_PORT = 5353
MDNS_V4_IP_DST = '224.0.0.251'
MDNS_V4_MAC_DST = '01:00:5E:00:00:FB'
MDNS_RECURSIVE = 1
MDNS_V6_IP_DST = 'FF02::FB'
MDNS_V6_MAC_DST = '33:33:00:00:00:FB'
ETH_TYPE_IP = 2048
SAP_SPANNING_TREE = 0x42
SNAP_OUI = 12
SNAP_SSAP = 170
SNAP_DSAP = 170
SNAP_CTRL = 3
LLC_XID_CONTROL = 191
PAD_LEN_BYTES = 128


def create(configs):
    """Creates PacketSender controllers from a json config.

    Args:
        The json configs that represent this controller

    Returns:
        A new PacketSender
    """
    return [PacketSender(c) for c in configs]


def destroy(objs):
    """Destroys a list of PacketSenders and stops sending (if active).

    Args:
        objs: A list of PacketSenders
    """
    for pkt_sender in objs:
        pkt_sender.stop_sending(True)
    return


def get_info(objs):
    """Get information on a list of packet senders.

    Args:
        objs: A list of PacketSenders

    Returns:
        Network interface name that is being used by each packet sender
    """
    return [pkt_sender.interface for pkt_sender in objs]


class ThreadSendPacket(multiprocessing.Process):
    """Creates a thread that keeps sending the same packet until a stop signal.

    Attributes:
        stop_signal: signal to stop the thread execution
        packet: desired packet to keep sending
        interval: interval between consecutive packets (s)
        interface: network interface name (e.g., 'eth0')
        log: object used for logging
    """

    def __init__(self, signal, packet, interval, interface, log):
        multiprocessing.Process.__init__(self)
        self.stop_signal = signal
        self.packet = packet
        self.interval = interval
        self.interface = interface
        self.log = log

    def run(self):
        self.log.info('Packet Sending Started.')
        while True:
            if self.stop_signal.is_set():
                # Poison pill means shutdown
                self.log.info('Packet Sending Stopped.')
                break

            try:
                scapy.sendp(self.packet, iface=self.interface, verbose=0)
                time.sleep(self.interval)
            except Exception:
                self.log.exception('Exception when trying to send packet')
                return

        return


class PacketSenderError(acts.signals.ControllerError):
    """Raises exceptions encountered in packet sender lib."""


class PacketSender(object):
    """Send any custom packet over a desired interface.

    Attributes:
        log: class logging object
        thread_active: indicates whether or not the send thread is active
        thread_send: thread object for the concurrent packet transmissions
        stop_signal: event to stop the thread
        interface: network interface name (e.g., 'eth0')
    """

    def __init__(self, ifname):
        """Initiallize the PacketGenerator class.

        Args:
            ifname: network interface name that will be used packet generator
        """
        self.log = logging.getLogger()
        self.packet = None
        self.thread_active = False
        self.thread_send = None
        self.stop_signal = multiprocessing.Event()
        self.interface = ifname

    def send_ntimes(self, packet, ntimes, interval):
        """Sends a packet ntimes at a given interval.

        Args:
            packet: custom built packet from Layer 2 up to Application layer
            ntimes: number of packets to send
            interval: interval between consecutive packet transmissions (s)
        """
        if packet is None:
            raise PacketSenderError(
                'There is no packet to send. Create a packet first.')

        for _ in range(ntimes):
            try:
                scapy.sendp(packet, iface=self.interface, verbose=0)
                time.sleep(interval)
            except socket.error as excpt:
                self.log.exception('Caught socket exception : %s' % excpt)
                return

    def send_receive_ntimes(self, packet, ntimes, interval):
        """Sends a packet and receives the reply ntimes at a given interval.

        Args:
            packet: custom built packet from Layer 2 up to Application layer
            ntimes: number of packets to send
            interval: interval between consecutive packet transmissions and
                      the corresponding reply (s)
        """
        if packet is None:
            raise PacketSenderError(
                'There is no packet to send. Create a packet first.')

        for _ in range(ntimes):
            try:
                scapy.srp1(
                    packet, iface=self.interface, timeout=interval, verbose=0)
                time.sleep(interval)
            except socket.error as excpt:
                self.log.exception('Caught socket exception : %s' % excpt)
                return

    def start_sending(self, packet, interval):
        """Sends packets in parallel with the main process.

        Creates a thread and keeps sending the same packet at a given interval
        until a stop signal is received

        Args:
            packet: custom built packet from Layer 2 up to Application layer
            interval: interval between consecutive packets (s)
        """
        if packet is None:
            raise PacketSenderError(
                'There is no packet to send. Create a packet first.')

        if self.thread_active:
            raise PacketSenderError(
                ('There is already an active thread. Stop it'
                 'before starting another transmission.'))

        self.thread_send = ThreadSendPacket(self.stop_signal, packet, interval,
                                            self.interface, self.log)
        self.thread_send.start()
        self.thread_active = True

    def stop_sending(self, ignore_status=False):
        """Stops the concurrent thread that is continuously sending packets.

       """
        if not self.thread_active:
            if ignore_status:
                return
            else:
                raise PacketSenderError(
                    'Error: There is no acive thread running to stop.')

        # Stop thread
        self.stop_signal.set()
        self.thread_send.join()

        # Just as precaution
        if self.thread_send.is_alive():
            self.thread_send.terminate()
            self.log.warning('Packet Sending forced to terminate')

        self.stop_signal.clear()
        self.thread_send = None
        self.thread_active = False


class ArpGenerator(object):
    """Creates a custom ARP packet

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv4: IPv4 address (Layer 3) of the source node
        dst_ipv4: IPv4 address (Layer 3) of the destination node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: a dictionary with all the necessary packet fields.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.dst_ipv4 = config_params['dst_ipv4']
        if config_params['src_ipv4'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv4 = scapy.get_if_addr(interf)
        else:
            self.src_ipv4 = config_params['src_ipv4']

    def generate(self,
                 op='who-has',
                 ip_dst=None,
                 ip_src=None,
                 hwsrc=None,
                 hwdst=None,
                 eth_dst=None):
        """Generates a custom ARP packet.

        Args:
            op: ARP type (request or reply)
            ip_dst: ARP ipv4 destination (Optional)
            ip_src: ARP ipv4 source address (Optional)
            hwsrc: ARP hardware source address (Optional)
            hwdst: ARP hardware destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Create IP layer
        hw_src = (hwsrc if hwsrc is not None else self.src_mac)
        hw_dst = (hwdst if hwdst is not None else ARP_DST)
        ipv4_dst = (ip_dst if ip_dst is not None else self.dst_ipv4)
        ipv4_src = (ip_src if ip_src is not None else self.src_ipv4)
        ip4 = scapy.ARP(
            op=op, pdst=ipv4_dst, psrc=ipv4_src, hwdst=hw_dst, hwsrc=hw_src)

        # Create Ethernet layer
        mac_dst = (eth_dst if eth_dst is not None else MAC_BROADCAST)
        ethernet = scapy.Ether(src=self.src_mac, dst=mac_dst)

        self.packet = ethernet / ip4
        return self.packet


class DhcpOfferGenerator(object):
    """Creates a custom DHCP offer packet

    Attributes:
        packet: desired built custom packet
        subnet_mask: local network subnet mask
        src_mac: MAC address (Layer 2) of the source node
        dst_mac: MAC address (Layer 2) of the destination node
        src_ipv4: IPv4 address (Layer 3) of the source node
        dst_ipv4: IPv4 address (Layer 3) of the destination node
        gw_ipv4: IPv4 address (Layer 3) of the Gateway
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        self.subnet_mask = config_params['subnet_mask']
        self.dst_mac = config_params['dst_mac']
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.dst_ipv4 = config_params['dst_ipv4']
        if config_params['src_ipv4'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv4 = scapy.get_if_addr(interf)
        else:
            self.src_ipv4 = config_params['src_ipv4']

        self.gw_ipv4 = config_params['gw_ipv4']

    def generate(self, cha_mac=None, dst_ip=None):
        """Generates a DHCP offer packet.

        Args:
            cha_mac: hardware target address for DHCP offer (Optional)
            dst_ip: ipv4 address of target host for renewal (Optional)
        """

        # Create DHCP layer
        dhcp = scapy.DHCP(options=[
            ('message-type', 'offer'),
            ('subnet_mask', self.subnet_mask),
            ('server_id', self.src_ipv4),
            ('end'),
        ])

        # Overwrite standard DHCP fields
        sta_hw = (cha_mac if cha_mac is not None else self.dst_mac)
        sta_ip = (dst_ip if dst_ip is not None else self.dst_ipv4)

        # Create Boot
        bootp = scapy.BOOTP(
            op=DHCP_OFFER_OP,
            yiaddr=sta_ip,
            siaddr=self.src_ipv4,
            giaddr=self.gw_ipv4,
            chaddr=scapy.mac2str(sta_hw),
            xid=DHCP_TRANS_ID)

        # Create UDP
        udp = scapy.UDP(sport=DHCP_OFFER_SRC_PORT, dport=DHCP_OFFER_DST_PORT)

        # Create IP layer
        ip4 = scapy.IP(src=self.src_ipv4, dst=IPV4_BROADCAST)

        # Create Ethernet layer
        ethernet = scapy.Ether(dst=MAC_BROADCAST, src=self.src_mac)

        self.packet = ethernet / ip4 / udp / bootp / dhcp
        return self.packet


class NsGenerator(object):
    """Creates a custom Neighbor Solicitation (NS) packet

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv6_type: IPv6 source address type (e.g., Link Local, Global, etc)
        src_ipv6: IPv6 address (Layer 3) of the source node
        dst_ipv6: IPv6 address (Layer 3) of the destination node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.dst_ipv6 = config_params['dst_ipv6']
        self.src_ipv6_type = config_params['src_ipv6_type']
        if config_params['src_ipv6'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv6 = get_if_addr6(interf, self.src_ipv6_type)
        else:
            self.src_ipv6 = config_params['src_ipv6']

    def generate(self, ip_dst=None, eth_dst=None):
        """Generates a Neighbor Solicitation (NS) packet (ICMP over IPv6).

        Args:
            ip_dst: NS ipv6 destination (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Compute IP addresses
        target_ip6 = ip_dst if ip_dst is not None else self.dst_ipv6
        ndst_ip = socket.inet_pton(socket.AF_INET6, target_ip6)
        nnode_mcast = scapy.in6_getnsma(ndst_ip)
        node_mcast = socket.inet_ntop(socket.AF_INET6, nnode_mcast)
        # Compute MAC addresses
        hw_dst = (eth_dst
                  if eth_dst is not None else scapy.in6_getnsmac(nnode_mcast))

        # Create IPv6 layer
        base = scapy.IPv6(dst=node_mcast, src=self.src_ipv6)
        neighbor_solicitation = scapy.ICMPv6ND_NS(tgt=target_ip6)
        src_ll_addr = scapy.ICMPv6NDOptSrcLLAddr(lladdr=self.src_mac)
        ip6 = base / neighbor_solicitation / src_ll_addr

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=hw_dst)

        self.packet = ethernet / ip6
        return self.packet


class RaGenerator(object):
    """Creates a custom Router Advertisement (RA) packet

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv6_type: IPv6 source address type (e.g., Link Local, Global, etc)
        src_ipv6: IPv6 address (Layer 3) of the source node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.src_ipv6_type = config_params['src_ipv6_type']
        if config_params['src_ipv6'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv6 = get_if_addr6(interf, self.src_ipv6_type)
        else:
            self.src_ipv6 = config_params['src_ipv6']

    def generate(self,
                 lifetime,
                 enableDNS=False,
                 dns_lifetime=0,
                 ip_dst=None,
                 eth_dst=None):
        """Generates a Router Advertisement (RA) packet (ICMP over IPv6).

        Args:
            lifetime: RA lifetime
            enableDNS: Add RDNSS option to RA (Optional)
            dns_lifetime: Set DNS server lifetime (Optional)
            ip_dst: IPv6 destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Overwrite standard fields if desired
        ip6_dst = (ip_dst if ip_dst is not None else RA_IP)
        hw_dst = (eth_dst if eth_dst is not None else RA_MAC)

        # Create IPv6 layer
        base = scapy.IPv6(dst=ip6_dst, src=self.src_ipv6)
        router_solicitation = scapy.ICMPv6ND_RA(routerlifetime=lifetime)
        src_ll_addr = scapy.ICMPv6NDOptSrcLLAddr(lladdr=self.src_mac)
        prefix = scapy.ICMPv6NDOptPrefixInfo(
            prefixlen=RA_PREFIX_LEN, prefix=RA_PREFIX)
        if enableDNS:
            rndss = scapy.ICMPv6NDOptRDNSS(
                lifetime=dns_lifetime, dns=[self.src_ipv6], len=DNS_LEN)
            ip6 = base / router_solicitation / src_ll_addr / prefix / rndss
        else:
            ip6 = base / router_solicitation / src_ll_addr / prefix

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=hw_dst)

        self.packet = ethernet / ip6
        return self.packet


class Ping6Generator(object):
    """Creates a custom Ping v6 packet (i.e., ICMP over IPv6)

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        dst_mac: MAC address (Layer 2) of the destination node
        src_ipv6_type: IPv6 source address type (e.g., Link Local, Global, etc)
        src_ipv6: IPv6 address (Layer 3) of the source node
        dst_ipv6: IPv6 address (Layer 3) of the destination node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        self.dst_mac = config_params['dst_mac']
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.dst_ipv6 = config_params['dst_ipv6']
        self.src_ipv6_type = config_params['src_ipv6_type']
        if config_params['src_ipv6'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv6 = get_if_addr6(interf, self.src_ipv6_type)
        else:
            self.src_ipv6 = config_params['src_ipv6']

    def generate(self, ip_dst=None, eth_dst=None):
        """Generates a Ping6 packet (i.e., Echo Request)

        Args:
            ip_dst: IPv6 destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Overwrite standard fields if desired
        ip6_dst = (ip_dst if ip_dst is not None else self.dst_ipv6)
        hw_dst = (eth_dst if eth_dst is not None else self.dst_mac)

        # Create IPv6 layer
        base = scapy.IPv6(dst=ip6_dst, src=self.src_ipv6)
        echo_request = scapy.ICMPv6EchoRequest(data=PING6_DATA)

        ip6 = base / echo_request

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=hw_dst)

        self.packet = ethernet / ip6
        return self.packet


class Ping4Generator(object):
    """Creates a custom Ping v4 packet (i.e., ICMP over IPv4)

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        dst_mac: MAC address (Layer 2) of the destination node
        src_ipv4: IPv4 address (Layer 3) of the source node
        dst_ipv4: IPv4 address (Layer 3) of the destination node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        self.dst_mac = config_params['dst_mac']
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.dst_ipv4 = config_params['dst_ipv4']
        if config_params['src_ipv4'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv4 = scapy.get_if_addr(interf)
        else:
            self.src_ipv4 = config_params['src_ipv4']

    def generate(self, ip_dst=None, eth_dst=None):
        """Generates a Ping4 packet (i.e., Echo Request)

        Args:
            ip_dst: IP destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """

        # Overwrite standard fields if desired
        sta_ip = (ip_dst if ip_dst is not None else self.dst_ipv4)
        sta_hw = (eth_dst if eth_dst is not None else self.dst_mac)

        # Create IPv6 layer
        base = scapy.IP(src=self.src_ipv4, dst=sta_ip)
        echo_request = scapy.ICMP(type=PING4_TYPE)

        ip4 = base / echo_request

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=sta_hw)

        self.packet = ethernet / ip4
        return self.packet


class Mdns6Generator(object):
    """Creates a custom mDNS IPv6 packet

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv6_type: IPv6 source address type (e.g., Link Local, Global, etc)
        src_ipv6: IPv6 address (Layer 3) of the source node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        self.src_ipv6_type = config_params['src_ipv6_type']
        if config_params['src_ipv6'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv6 = get_if_addr6(interf, self.src_ipv6_type)
        else:
            self.src_ipv6 = config_params['src_ipv6']

    def generate(self, ip_dst=None, eth_dst=None):
        """Generates a mDNS v6 packet for multicast DNS config

        Args:
            ip_dst: IPv6 destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """

        # Overwrite standard fields if desired
        sta_ip = (ip_dst if ip_dst is not None else MDNS_V6_IP_DST)
        sta_hw = (eth_dst if eth_dst is not None else MDNS_V6_MAC_DST)

        # Create mDNS layer
        qdServer = scapy.DNSQR(qname=self.src_ipv6, qtype=MDNS_QTYPE)
        mDNS = scapy.DNS(rd=MDNS_RECURSIVE, qd=qdServer)

        # Create UDP
        udp = scapy.UDP(sport=MDNS_UDP_PORT, dport=MDNS_UDP_PORT)

        # Create IP layer
        ip6 = scapy.IPv6(src=self.src_ipv6, dst=sta_ip)

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=sta_hw)

        self.packet = ethernet / ip6 / udp / mDNS
        return self.packet


class Mdns4Generator(object):
    """Creates a custom mDNS v4 packet

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv4: IPv4 address (Layer 3) of the source node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

        if config_params['src_ipv4'] == GET_FROM_LOCAL_INTERFACE:
            self.src_ipv4 = scapy.get_if_addr(interf)
        else:
            self.src_ipv4 = config_params['src_ipv4']

    def generate(self, ip_dst=None, eth_dst=None):
        """Generates a mDNS v4 packet for multicast DNS config

        Args:
            ip_dst: IP destination address (Optional)
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """

        # Overwrite standard fields if desired
        sta_ip = (ip_dst if ip_dst is not None else MDNS_V4_IP_DST)
        sta_hw = (eth_dst if eth_dst is not None else MDNS_V4_MAC_DST)

        # Create mDNS layer
        qdServer = scapy.DNSQR(qname=self.src_ipv4, qtype=MDNS_QTYPE)
        mDNS = scapy.DNS(rd=MDNS_RECURSIVE, qd=qdServer)

        # Create UDP
        udp = scapy.UDP(sport=MDNS_UDP_PORT, dport=MDNS_UDP_PORT)

        # Create IP layer
        ip4 = scapy.IP(src=self.src_ipv4, dst=sta_ip, ttl=255)

        # Create Ethernet layer
        ethernet = scapy.Ether(src=self.src_mac, dst=sta_hw)

        self.packet = ethernet / ip4 / udp / mDNS
        return self.packet


class Dot3Generator(object):
    """Creates a custom 802.3 Ethernet Frame

    Attributes:
        packet: desired built custom packet
        src_mac: MAC address (Layer 2) of the source node
        src_ipv4: IPv4 address (Layer 3) of the source node
    """

    def __init__(self, **config_params):
        """Initialize the class with the required network and packet params.

        Args:
            config_params: contains all the necessary packet parameters.
              Some fields can be generated automatically. For example:
              {'subnet_mask': '255.255.255.0',
               'dst_ipv4': '192.168.1.3',
               'src_ipv4: 'get_local', ...
              The key can also be 'get_local' which means the code will read
              and use the local interface parameters
        """
        interf = config_params['interf']
        self.packet = None
        self.dst_mac = config_params['dst_mac']
        if config_params['src_mac'] == GET_FROM_LOCAL_INTERFACE:
            self.src_mac = scapy.get_if_hwaddr(interf)
        else:
            self.src_mac = config_params['src_mac']

    def _build_ether(self, eth_dst=None):
        """Creates the basic frame for 802.3

        Args:
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Overwrite standard fields if desired
        sta_hw = (eth_dst if eth_dst is not None else self.dst_mac)
        # Create Ethernet layer
        dot3_base = scapy.Dot3(src=self.src_mac, dst=sta_hw)

        return dot3_base

    def _pad_frame(self, frame):
        """Pads the frame with default length and values

        Args:
            frame: Ethernet (layer 2) to be padded
        """
        frame.len = PAD_LEN_BYTES
        pad = scapy.Padding()
        pad.load = '\x00' * PAD_LEN_BYTES
        return frame / pad

    def generate(self, eth_dst=None):
        """Generates the basic 802.3 frame and adds padding

        Args:
            eth_dst: Ethernet (layer 2) destination address (Optional)
        """
        # Create 802.3 Base
        ethernet = self._build_ether(eth_dst)

        self.packet = self._pad_frame(ethernet)
        return self.packet

    def generate_llc(self, eth_dst=None, dsap=2, ssap=3, ctrl=LLC_XID_CONTROL):
        """Generates the 802.3 frame with LLC and adds padding

        Args:
            eth_dst: Ethernet (layer 2) destination address (Optional)
            dsap: Destination Service Access Point (Optional)
            ssap: Source Service Access Point (Optional)
            ctrl: Control (Optional)
        """
        # Create 802.3 Base
        ethernet = self._build_ether(eth_dst)

        # Create LLC layer
        llc = scapy.LLC(dsap=dsap, ssap=ssap, ctrl=ctrl)

        # Append and create packet
        self.packet = self._pad_frame(ethernet / llc)
        return self.packet

    def generate_snap(self,
                      eth_dst=None,
                      dsap=SNAP_DSAP,
                      ssap=SNAP_SSAP,
                      ctrl=SNAP_CTRL,
                      oui=SNAP_OUI,
                      code=ETH_TYPE_IP):
        """Generates the 802.3 frame with LLC and SNAP and adds padding

        Args:
            eth_dst: Ethernet (layer 2) destination address (Optional)
            dsap: Destination Service Access Point (Optional)
            ssap: Source Service Access Point (Optional)
            ctrl: Control (Optional)
            oid: Protocol Id or Org Code (Optional)
            code: EtherType (Optional)
        """
        # Create 802.3 Base
        ethernet = self._build_ether(eth_dst)

        # Create 802.2 LLC header
        llc = scapy.LLC(dsap=dsap, ssap=ssap, ctrl=ctrl)

        # Create 802.3 SNAP header
        snap = scapy.SNAP(OUI=oui, code=code)

        # Append and create packet
        self.packet = self._pad_frame(ethernet / llc / snap)
        return self.packet


def get_if_addr6(intf, address_type):
    """Returns the Ipv6 address from a given local interface.

    Returns the desired IPv6 address from the interface 'intf' in human
    readable form. The address type is indicated by the IPv6 constants like
    IPV6_ADDR_LINKLOCAL, IPV6_ADDR_GLOBAL, etc. If no address is found,
    None is returned.

    Args:
        intf: desired interface name
        address_type: addrees typle like LINKLOCAL or GLOBAL

    Returns:
        Ipv6 address of the specified interface in human readable format
    """
    for if_list in scapy.in6_getifaddr():
        if if_list[2] == intf and if_list[1] == address_type:
            return if_list[0]

    return None

