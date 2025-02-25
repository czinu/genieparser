''' show_arp.py

IOSXE parsers for the following show commands:
    * show arp
    * show arp <WORD>
    * show arp vrf <vrf>
    * show arp vrf <vrf> <WORD>
    * show ip arp
    * show ip arp vrf <vrf>
    * show ip arp summary
    * show ip traffic
    * show arp application
    * show arp summary
'''

# Python
from ast import Or
import re

# Metaparser
from genie.metaparser import MetaParser
from genie.metaparser.util.schemaengine import Schema, Any, Optional

# parser utils
from genie.libs.parser.utils.common import Common


# =============================================
# Parser for 'show arp [vrf <WORD>] <WORD>'
# =============================================

class ShowArpSchema(MetaParser):
    """Schema for show arp
                  show arp <WORD>
                  show arp vrf <vrf>
                  show arp vrf <vrf> <WORD>
    """

    schema = {
        Optional('global_static_table'): {
            Any(): {
                'ip_address': str,
                'mac_address': str,
                'encap_type': str,
                'age': str,
                'protocol': str,
            },
        },
        Optional('interfaces'): {
            Any(): {
                'ipv4': {
                    'neighbors': {     
                        Any(): {
                            'ip': str,
                            'link_layer_address': str,
                            'origin': str,
                            'age': str,
                            'type': str,
                            'protocol': str,
                            Optional('private_vlan'): int
                        },
                    }
                }
            },
        }
    }


class ShowArp(ShowArpSchema):
    """ Parser for show arp
                  show arp <WROD>
                  show arp vrf <vrf>
                  show arp vrf <vrf> <WROD> """

    cli_command = ['show arp','show arp vrf {vrf}','show arp vrf {vrf} {intf_or_ip}','show arp {intf_or_ip}']
    exclude = ['age']

    def cli(self, vrf='', intf_or_ip='', cmd=None, output=None):
        if output is None:
            if not cmd:
                cmd = self.cli_command[0]
                if vrf and not intf_or_ip:
                    cmd = self.cli_command[1].format(vrf=vrf)
                if vrf and intf_or_ip:
                    cmd = self.cli_command[2].format(vrf=vrf,intf_or_ip=intf_or_ip)
                if not vrf and intf_or_ip:
                    cmd = self.cli_command[3].format(intf_or_ip=intf_or_ip)

            out = self.device.execute(cmd)
        else:
            out = output

        # Internet  192.168.234.1           -   58bf.eaff.e508  ARPA   Vlan100
        # Internet  10.169.197.93          -   fa16.3eff.b7ad  ARPA
        # Internet  192.168.111.111         0   aabb.0111.0111  802.1Q Vlan111
        # Internet 192.168.1.203 3 0015.0100.0001 ARPA Vlan201 pv 203
        p1 = re.compile(r'^(?P<protocol>\w+) +(?P<address>[\d\.\:]+) +(?P<age>[\d\-]+) +'
                         r'(?P<mac>[\w\.]+) +(?P<type>[\w\.]+)'
                         r'( +(?P<interface>[\w\.\/\-]+)(\s+pv\s+(?P<private_vlan>\d+))?)?$')
        # initial variables
        ret_dict = {}

        for line in out.splitlines():
            line = line.strip()

            # Internet  192.168.234.1           -   58bf.eaff.e508  ARPA   Vlan100
            # Internet  10.169.197.93          -   fa16.3eff.b7ad  ARPA
            # Internet  192.168.111.111         0   aabb.0111.0111  802.1Q Vlan111
            # Internet 192.168.1.203 3 0015.0100.0001 ARPA Vlan201 pv 203
            m = p1.match(line)
            if m:
                group = m.groupdict()
                address = group['address']
                interface = group['interface']
                if interface:
                    final_dict = ret_dict.setdefault('interfaces', {}).setdefault(
                        interface, {}).setdefault('ipv4', {}).setdefault(
                        'neighbors', {}).setdefault(address, {})
                    
                    final_dict['ip'] = address
                    final_dict['link_layer_address'] = group['mac']
                    final_dict['type'] = group['type']
                    if group['age'] == '-':
                        final_dict['origin'] = 'static'
                    else:
                        final_dict['origin'] = 'dynamic'
                    if group['private_vlan']:
                        final_dict['private_vlan'] = int(group['private_vlan'])
                else:
                    final_dict = ret_dict.setdefault(
                        'global_static_table', {}).setdefault(address, {})
                    final_dict['ip_address'] = address
                    final_dict['mac_address'] = group['mac']
                    final_dict['encap_type'] = group['type']

                final_dict['age'] = group['age']
                final_dict['protocol'] = group['protocol']
                continue

        return ret_dict

# =====================================
# Parser for 'show ip arp, show ip arp vrf <vrf>'
# =====================================
class ShowIpArp(ShowArp):
    """Parser for 'show ip arp,  show ip arp vrf <vrf>"""
    cli_command = ['show ip arp', 'show ip arp vrf {vrf}']

    def cli(self, vrf='', output=None):
        if output is None:
            if vrf:
                cmd = self.cli_command[1].format(vrf=vrf)
            else:
                cmd = self.cli_command[0]
            out = self.device.execute(cmd)
        else:
            out = output
        return super().cli(output=out)
# =====================================
# Schema for 'show ip arp summary'
# =====================================
class ShowIpArpSummarySchema(MetaParser):
    """Schema for show ip arp summary"""

    schema = {
        'total_entries': int,
        'incomp_entries': int,
        }

# =====================================
# Parser for 'show ip arp summary'
# =====================================
class ShowIpArpSummary(ShowIpArpSummarySchema):
    """Parser for:
        show ip arp summary
        parser class - implements detail parsing mechanisms for cli,xml and yang output.
    """
    cli_command = 'show ip arp summary'
    def cli(self,output=None):
        if output is None:
            # excute command to get output
            out = self.device.execute(self.cli_command)
        else:
            out = output

        # 40 IP ARP entries, with 0 of them incomplete
        p1 = re.compile(r'^(?P<total_entries>\w+) +IP +ARP +entries, +with '
            r'+(?P<incomp_entries>\w+) +of +them +incomplete$')

        # initial variables
        ret_dict = {}

        for line in out.splitlines():
            line = line.strip()

            m = p1.match(line)
            if m:
                ret_dict['total_entries'] = int(m.groupdict()['total_entries'])
                ret_dict['incomp_entries'] = int(m.groupdict()['incomp_entries'])
                continue

        return ret_dict

# =====================================
# Schema for 'show ip traffic'
# =====================================
class ShowIpTrafficSchema(MetaParser):
    """Schema for show ip traffic"""

    schema = {
        'arp_statistics': {
            'arp_in_requests': int,
            'arp_in_replies': int,
            'arp_in_reverse': int,
            'arp_in_other': int,
            'arp_out_requests': int,
            'arp_out_replies': int,
            'arp_out_proxy': int,
            'arp_out_reverse': int,
            Optional('arp_drops_input_full'): int,
        },
        'ip_statistics': {
            'ip_rcvd_total': int,
            'ip_rcvd_local_destination': int,
            'ip_rcvd_format_errors': int,
            'ip_rcvd_checksum_errors': int,
            'ip_rcvd_bad_hop': int,
            'ip_rcvd_unknwn_protocol': int,
            'ip_rcvd_not_gateway': int,
            'ip_rcvd_sec_failures': int,
            'ip_rcvd_bad_optns': int,
            'ip_rcvd_with_optns': int,
            'ip_opts_end': int,
            'ip_opts_nop': int,
            'ip_opts_basic_security': int,
            'ip_opts_loose_src_route': int,
            'ip_opts_timestamp': int,
            'ip_opts_extended_security': int,
            'ip_opts_record_route': int,
            'ip_opts_strm_id': int,
            'ip_opts_strct_src_route': int,
            'ip_opts_alert': int,
            'ip_opts_cipso': int,
            'ip_opts_ump': int,
            'ip_opts_other': int,
            Optional('ip_opts_ignored'): int,
            'ip_frags_reassembled': int,
            'ip_frags_timeouts': int,
            'ip_frags_no_reassembled': int,
            'ip_frags_fragmented': int,
            Optional('ip_frags_fragments'): int,
            'ip_frags_no_fragmented': int,
            Optional('ip_frags_invalid_hole'): int,
            'ip_bcast_received': int,
            'ip_bcast_sent': int,
            'ip_mcast_received': int,
            'ip_mcast_sent': int,
            'ip_sent_generated': int,
            'ip_sent_forwarded': int,
            'ip_drop_encap_failed': int,
            'ip_drop_unresolved': int,
            'ip_drop_no_adj': int,
            'ip_drop_no_route': int,
            'ip_drop_unicast_rpf': int,
            'ip_drop_forced_drop': int,
            Optional('ip_drop_unsupp_address'): int,
            'ip_drop_opts_denied': int,
            Optional('ip_drop_src_ip'): int,
        },
        'icmp_statistics': {
            'icmp_received_format_errors': int,
            'icmp_received_checksum_errors': int,
            'icmp_received_redirects': int,
            'icmp_received_unreachable': int,
            'icmp_received_echo': int,
            'icmp_received_echo_reply': int,
            'icmp_received_mask_requests': int,
            'icmp_received_mask_replies': int,
            'icmp_received_quench': int,
            'icmp_received_parameter': int,
            'icmp_received_timestamp': int,
            Optional('icmp_received_timestamp_replies'): int,
            'icmp_received_info_request': int,
            'icmp_received_other': int,
            'icmp_received_irdp_solicitations': int,
            'icmp_received_irdp_advertisements': int,
            Optional('icmp_received_time_exceeded'): int,
            Optional('icmp_received_info_replies'): int,
            'icmp_sent_redirects': int,
            'icmp_sent_unreachable': int,
            'icmp_sent_echo': int,
            'icmp_sent_echo_reply': int,
            'icmp_sent_mask_requests': int,
            'icmp_sent_mask_replies': int,
            'icmp_sent_quench': int,
            'icmp_sent_timestamp': int,
            Optional('icmp_sent_timestamp_replies'): int,
            Optional('icmp_sent_info_reply'): int,
            Optional('icmp_sent_time_exceeded'): int,
            'icmp_sent_parameter_problem': int,
            'icmp_sent_irdp_solicitations': int,
            'icmp_sent_irdp_advertisements': int,
        },
        'udp_statistics': {
            'udp_received_total': int,
            'udp_received_udp_checksum_errors': int,
            'udp_received_no_port': int,
            Optional('udp_received_finput'): int,
            'udp_sent_total': int,
            'udp_sent_fwd_broadcasts': int,
        },
        'ospf_statistics': {
            Optional('ospf_traffic_cntrs_clear'): str,
            'ospf_received_total': int,
            'ospf_received_checksum_errors': int,
            'ospf_received_hello': int,
            'ospf_received_database_desc': int,
            'ospf_received_link_state_req': int,
            'ospf_received_lnk_st_updates': int,
            'ospf_received_lnk_st_acks': int,
            'ospf_sent_total': int,
            'ospf_sent_hello': int,
            'ospf_sent_database_desc': int,
            'ospf_sent_lnk_st_acks': int,
            'ospf_sent_lnk_st_updates': int,
            'ospf_sent_lnk_st_acks': int,
        },
        'pimv2_statistics': {
            'pimv2_total': str,
            'pimv2_checksum_errors': int,
            'pimv2_format_errors': int,
            'pimv2_registers': str,
            'pimv2_non_rp': int,
            'pimv2_non_sm_group': int,
            'pimv2_registers_stops': str,
            'pimv2_hellos': str,
            'pimv2_join_prunes': str,
            'pimv2_asserts': str,
            'pimv2_grafts': str,
            'pimv2_bootstraps': str,
            'pimv2_candidate_rp_advs': str,
            Optional('pimv2_queue_drops'): int,
            'pimv2_state_refresh': str,
        },
        'igmp_statistics': {
            'igmp_total': str,
            'igmp_format_errors': str,
            'igmp_checksum_errors': str,
            'igmp_host_queries': str,
            'igmp_host_reports': str,
            'igmp_host_leaves': str,
            'igmp_dvmrp': str,
            'igmp_pim': str,
            Optional('igmp_queue_drops'): int,
        },
        'tcp_statistics': {
            'tcp_received_total': int,
            'tcp_received_checksum_errors': int,
            'tcp_received_no_port': int,
            'tcp_sent_total': int,
        },
        'eigrp_ipv4_statistics': {
            'eigrp_ipv4_received_total': int,
            'eigrp_ipv4_sent_total': int,
        },
        Optional('bgp_statistics'): {
            'bgp_received_total': int,
            'bgp_received_opens': int,
            'bgp_received_notifications': int,
            'bgp_received_updates': int,
            'bgp_received_keepalives': int,
            'bgp_received_route_refresh': int,
            'bgp_received_unrecognized': int,
            'bgp_sent_total': int,
            'bgp_sent_opens': int,
            'bgp_sent_notifications': int,
            'bgp_sent_updates': int,
            'bgp_sent_keepalives': int,
            'bgp_sent_route_refresh': int,
        },
    }

# =====================================
# Parser for 'show ip traffic'
# =====================================
class ShowIpTraffic(ShowIpTrafficSchema):
    """Parser for:
        show ip traffic
        parser class - implements detail parsing mechanisms for cli,xml and yang output.
    """
    cli_command = 'show ip traffic'
    exclude = ['bgp_received_keepalives' , 'bgp_received_total', 'bgp_sent_keepalives', 'bgp_sent_total' ,
                'eigrp_ipv4_received_total' , 'eigrp_ipv4_sent_total', 'icmp_received_echo', 'icmp_sent_echo_reply',
                'igmp_host_queries', 'igmp_host_reports', 'igmp_total', 'ip_bcast_received', 'ip_bcast_sent', 'ip_mcast_received',
                'ip_mcast_sent', 'ip_opts_alert', 'ip_rcvd_format_errors', 'ip_rcvd_local_destination', 'ip_rcvd_total' ,
                'ip_rcvd_with_optns', 'ip_sent_generated', 'ospf_received_hello', 'ospf_received_lnk_st_acks', 'ospf_received_lnk_st_updates'
                'ospf_received_total' , 'ospf_sent_hello' , 'ospf_sent_lnk_st_acks', 'ospf_sent_lnk_st_updates', 'ospf_sent_total', 'pimv2_bootstraps',
                'pimv2_candidate_rp_advs', 'pimv2_hellos', 'pimv2_registers', 'pimv2_registers_stops', 'pimv2_total', 'tcp_received_no_port', 'tcp_received_total', 
                'tcp_sent_total', 'udp_received_no_port', 'udp_received_total', 'udp_sent_total']
    def cli(self,output=None):
        if output is None:
            # excute command to get output
            out = self.device.execute(self.cli_command)
        else:
            out = output

        # ARP statistics:
        p1 = re.compile(r'^ARP +statistics:')

        # Rcvd: 2020 requests, 764 replies, 0 reverse, 0 other
        p2 = re.compile(r'^Rcvd: +(?P<arp_in_requests>\d+) +requests,'
            r' +(?P<arp_in_replies>\d+) +replies, +(?P<arp_in_reverse>\d+)'
            r' +reverse, +(?P<arp_in_other>\d+) +other$')

        # Sent: 29 requests, 126 replies (2 proxy), 0 reverse
        p3 = re.compile(r'^Sent: +(?P<arp_out_requests>\d+) +requests,'
            r' +(?P<arp_out_replies>\d+) +replies +\((?P<arp_out_proxy>[\w]+)'
            r' +proxy\), +(?P<arp_out_reverse>\d+) +reverse$')

        # Drop due to input queue full: 0
        p4 = re.compile(r'^Drop +due +to +input +queue +full:'
            r' +(?P<arp_drops>\w+)$')

        # IP statistics:
        p5 = re.compile(r'^IP +statistics:')

        # Rcvd:  17780 total, 110596 local destination
        p6 = re.compile(r'^Rcvd: +(?P<ip_rcvd_total>\d+) +total,'
            r' +(?P<ip_rcvd_local_destination>\d+)'
            r' +local +destination$')

        # 0 format errors, 0 checksum errors, 0 bad hop count
        p7 = re.compile(r'^(?P<ip_rcvd_format_errors>\d+) +format +errors,'
            r' +(?P<ip_rcvd_checksum_errors>\d+)'
            r' +checksum +errors, +(?P<ip_rcvd_bad_hop>\d+) +bad +hop +count$')

        # 0 unknown protocol, 5 not a gateway
        p8 = re.compile(r'^(?P<ip_rcvd_unknwn_protocol>\d+) +unknown +protocol,'
            r' +(?P<ip_rcvd_not_gateway>\d+)'
            r' +not +a +gateway$')

        # 0 security failures, 0 bad options, 12717 with options
        p9 = re.compile(r'^(?P<ip_rcvd_sec_failures>\d+) +security +failures,'
            r' +(?P<ip_rcvd_bad_optns>\d+)'
            r' +bad options, +(?P<ip_rcvd_with_optns>\d+) +with +options$')

        # Opts:  0 end, 0 nop, 0 basic security, 0 loose source route
        p10 = re.compile(r'^Opts: +(?P<ip_opts_end>\d+) +end,'
            r' +(?P<ip_opts_nop>\d+)'
            r' +nop, +(?P<ip_opts_basic_security>\d+) +basic +security, '
            r'+(?P<ip_opts_loose_src_route>\d+) +loose +source +route$')

        # 0 timestamp, 0 extended security, 0 record route
        p11 = re.compile(r'^(?P<ip_opts_timestamp>\d+) +timestamp,'
            r' +(?P<ip_opts_extended_security>\d+)'
            r' +extended +security, +(?P<ip_opts_record_route>\d+)'
            r' +record +route$')

        # 0 stream ID, 0 strict source route, 12717 alert, 0 cipso, 0 ump
        p12 = re.compile(r'^(?P<ip_opts_strm_id>\d+) +stream +ID,'
            r' +(?P<ip_opts_strct_src_route>\d+)'
            r' +strict +source +route, +(?P<ip_opts_alert>\d+) +alert, '
            r'+(?P<ip_opts_cipso>\d+) +cipso, +(?P<ip_opts_ump>\d+) +ump$')

        # 0 other, 0 ignored
        p13 = re.compile(r'^(?P<ip_opts_other>\d+) +other'
            r'(, +(?P<ip_opts_ignored>\d+) +ignored)?$')

        # Frags: 0 reassembled, 0 timeouts, 0 couldn't reassemble
        p14 = re.compile(r'^Frags: +(?P<ip_frags_reassembled>\d+) +reassembled,'
            r' +(?P<ip_frags_timeouts>\d+)'
            r' +timeouts, +(?P<ip_frags_no_reassembled>\d+)'
            r' +couldn\'t +reassemble$')

        # 1 fragmented, 5 fragments, 0 couldn't fragment
        # 0 fragmented, 0 couldn't fragment
        p15 = re.compile(r'^(?P<ip_frags_fragmented>\d+) +fragmented,'
            r'( +(?P<ip_frags_fragments>\d+) +fragments,)?'
            r' +(?P<ip_frags_no_fragmented>\d+)'
            r' +couldn\'t +fragment$')

        # 0 invalid hole
        p16 = re.compile(r'^(?P<ip_frags_invalid_hole>\d+) +invalid hole$')

        # Bcast: 33324 received, 5 sent
        p17 = re.compile(r'^Bcast: +(?P<ip_bcast_received>\d+) +received,'
            r' +(?P<ip_bcast_sent>\d+) +sent$')

        # Mcast: 144833 received, 66274 sent
        p18 = re.compile(r'^Mcast: +(?P<ip_mcast_received>\d+) +received,'
            r' +(?P<ip_mcast_sent>\d+) +sent$')

        # Sent:  85543 generated, 1654728 forwarded
        p19 = re.compile(r'^Sent: +(?P<ip_sent_generated>\d+) +generated,'
            r' +(?P<ip_sent_forwarded>\d+) +forwarded$')

        # Drop:  8 encapsulation failed, 0 unresolved, 20 no adjacency
        p20 = re.compile(r'^Drop: +(?P<ip_drop_encap_failed>\d+) +encapsulation'
            r' +failed, +(?P<ip_drop_unresolved>\d+)'
            r' +unresolved, +(?P<ip_drop_no_adj>\d+) +no +adjacency$')

        # 19 no route, 0 unicast RPF, 0 forced drop, 0 unsupported-addr
        # 0 no route, 0 unicast RPF, 0 forced drop
        p21 = re.compile(r'^(?P<ip_drop_no_route>\d+) +no +route,'
            r' +(?P<ip_drop_unicast_rpf>\d+)'
            r' +unicast +RPF, +(?P<ip_drop_forced_drop>\d+) +forced +drop'
            r'(, +(?P<ip_drop_unsupp_address>\d+) +unsupported-addr)?$')

        # 0 options denied, 0 source IP address zero
        p22 = re.compile(r'^(?P<ip_drop_opts_denied>\d+) +options +denied(,'
            r' +(?P<ip_drop_src_ip>\d+) +source +IP +address +zero)?$')

        # ICMP statistics:
        p23 = re.compile(r'^ICMP +statistics:')

        # Rcvd: 0 format errors, 0 checksum errors, 0 redirects, 0 unreachable
        p24 = re.compile(r'^Rcvd: +(?P<icmp_received_format_errors>\d+) +format '
            r'+errors, +(?P<icmp_received_checksum_errors>\d+) +checksum +errors, '
            r'+(?P<icmp_received_redirects>\d+) +redirects, '
            r'+(?P<icmp_received_unreachable>\d+) +unreachable$')

        # 284 echo, 9 echo reply, 0 mask requests, 0 mask replies, 0 quench
        # 43838 echo, 713 echo reply, 0 mask requests, 0 mask replies, 0 quench
        p25 = re.compile(r'^(?P<icmp_received_echo>\d+) +echo,'
            r' +(?P<icmp_received_echo_reply>\d+)'
            r' +echo +reply, +(?P<icmp_received_mask_requests>\d+) +mask'
            r' +requests, +(?P<icmp_received_mask_replies>\d+) +mask +replies, '
            r'+(?P<icmp_received_quench>\d+) +quench$')

        # 0 parameter, 0 timestamp, 0 timestamp replies, 0 info request, 0 other
        # 0 parameter, 0 timestamp, 0 info request, 0 other
        p26 = re.compile(r'^(?P<icmp_received_parameter>\d+) +parameter,'
            r' +(?P<icmp_received_timestamp>\d+)'
            r' +timestamp(, +(?P<icmp_received_timestamp_replies>\d+) +timestamp'
            r' +replies)?, +(?P<icmp_received_info_request>\d+) +info +request,'
            r' +(?P<icmp_received_other>\d+) +other$')

        # 0 irdp solicitations, 0 irdp advertisements
        p27 = re.compile(r'^(?P<icmp_received_irdp_solicitations>\d+) '
            r'+irdp +solicitations, +(?P<icmp_received_irdp_advertisements>\d+)'
            r' +irdp +advertisements$')

        # 0 time exceeded, 0 info replies
        p28 = re.compile(r'^(?P<icmp_received_time_exceeded>\d+) '
            r'+time +exceeded, +(?P<icmp_received_info_replies>\d+)'
            r' +info +replies$')

        # Sent: 0 redirects, 14 unreachable, 9 echo, 134 echo reply
        p29 = re.compile(r'^Sent: +(?P<icmp_sent_redirects>\d+) +redirects, '
            r'+(?P<icmp_sent_unreachable>\d+) +unreachable,'
            r' +(?P<icmp_sent_echo>\d+) +echo, +(?P<icmp_sent_echo_reply>\d+) '
            r'+echo +reply$')

        # 0 mask requests, 0 mask replies, 0 quench, 0 timestamp, 0 timestamp replies
        # 0 mask requests, 0 mask replies, 0 quench, 0 timestamp
        p30 = re.compile(r'^(?P<icmp_sent_mask_requests>\d+) +mask +requests, '
            r'+(?P<icmp_sent_mask_replies>\d+)'
            r' +mask +replies, +(?P<icmp_sent_quench>\d+) +quench, '
            r'+(?P<icmp_sent_timestamp>\d+) +timestamp'
            r'(, +(?P<icmp_sent_timestamp_replies>\d+) +timestamp +replies)?$')

        # 0 info reply, 0 time exceeded, 0 parameter problem
        p31 = re.compile(r'^(?P<icmp_sent_info_reply>\d+) +info +reply, '
            r'+(?P<icmp_sent_time_exceeded>\d+) +time +exceeded, '
            r'+(?P<icmp_sent_parameter_problem>\d+) +parameter +problem$')

        # 0 irdp solicitations, 0 irdp advertisements
        p32 = re.compile(r'^(?P<icmp_sent_irdp_solicitations>\d+) +irdp '
            r'+solicitations, +(?P<icmp_sent_irdp_advertisements>\d+)'
            r' +irdp +advertisements$')

        # UDP statistics:
        p33 = re.compile(r'^UDP +statistics:')

        # Rcvd: 62515 total, 0 checksum errors, 15906 no port 0 finput
        # Rcvd: 682217 total, 0 checksum errors, 289579 no port
        p34 = re.compile(r'^Rcvd: +(?P<udp_received_total>\d+) +total,'
            r' +(?P<udp_received_udp_checksum_errors>\d+) +checksum +errors,'
            r' +(?P<udp_received_no_port>\d+) +no port( +(?P<udp_received_finput>\d+) '
            r'+finput)?$')

        # Sent: 41486 total, 0 forwarded broadcasts
        p35 = re.compile(r'^Sent: +(?P<udp_sent_total>\d+) +total, '
            r'+(?P<udp_sent_fwd_broadcasts>\d+) +forwarded +broadcasts$')

        # OSPF statistics:
        p36 = re.compile(r'^OSPF +statistics:')

        # Last clearing of OSPF traffic counters never
        p37 = re.compile(r'^Last +clearing +of +OSPF +traffic +counters '
            r'+(?P<ospf_traffic_cntrs_clear>\w+)$')

        # Rcvd: 16222 total, 0 checksum errors
        p38 = re.compile(r'^Rcvd: +(?P<ospf_received_total>\d+) +total, '
            r'+(?P<ospf_received_checksum_errors>\d+) +checksum errors$')

        # 15153 hello, 20 database desc, 2 link state req
        p39 = re.compile(r'^(?P<ospf_received_hello>\d+) +hello, '
            r'+(?P<ospf_received_database_desc>\d+)'
            r' +database +desc, +(?P<ospf_received_link_state_req>\d+) '
            r'+link +state +req$')

        # 359 link state updates, 688 link state acks
        p40 = re.compile(r'^(?P<ospf_received_lnk_st_updates>\d+) +link '
            r'+state +updates, +(?P<ospf_received_lnk_st_acks>\d+) +link '
            r'+state +acks$')

        # Sent: 9456 total
        p41 = re.compile(r'^Sent: +(?P<sent_total>\d+) +total$')

        # 8887 hello, 30 database desc, 8 link state req
        p42 = re.compile(r'^(?P<ospf_sent_hello>\d+) +hello, '
            r'+(?P<ospf_sent_database_desc>\d+)'
            r' +database +desc, +(?P<ospf_sent_lnk_st_acks>\d+) +link +state '
            r'+req$')

        # 299 link state updates, 239 link state acks
        p43 = re.compile(r'^(?P<ospf_sent_lnk_st_updates>\d+) +link '
            r'+state +updates, +(?P<ospf_sent_lnk_st_acks>\d+) +link '
            r'+state +acks$')

        # PIMv2 statistics: Sent/Received
        p44 = re.compile(r'^PIMv2 +statistics: +Sent/Received')

        # Total: 7458/8859, 0 checksum errors, 0 format errors
        p45 = re.compile(r'^Total: +(?P<pimv2_total>[\d\/]+), '
            r'+(?P<pimv2_checksum_errors>\d+) +checksum +errors, '
            r'+(?P<pimv2_format_errors>\d+) +format +errors$')

        # Registers: 1/1 (0 non-rp, 0 non-sm-group), Register Stops: 1/1,  Hellos: 5011/5008
        p46 = re.compile(r'^Registers: +(?P<pimv2_registers>[\d\/]+) +'
            r'\((?P<pimv2_non_rp>\d+) +non-rp, +(?P<pimv2_non_sm_group>\d+) '
            r'+non-sm-group\), +Register +Stops:'
            r' +(?P<pimv2_registers_stops>[\d\/]+),'
            r' +Hellos: +(?P<pimv2_hellos>[\d\/]+)$')

        # Join/Prunes: 5/712, Asserts: 0/697, grafts: 0/2
        p47 = re.compile(r'^Join/Prunes: +(?P<pimv2_join_prunes>[\d\/]+), '
            r'+Asserts: +(?P<pimv2_asserts>[\d\/]+), +grafts: '
            r'+(?P<pimv2_grafts>[\d\/]+)$')

        # Bootstraps: 2088/2438, Candidate_RP_Advertisements: 350/0
        p48 = re.compile(r'^Bootstraps: +(?P<pimv2_bootstraps>[\d\/]+), '
            r'+Candidate_RP_Advertisements:'
            r' +(?P<pimv2_candidate_rp_advs>[\d\/]+)$')

        # Queue drops: 0
        p49 = re.compile(r'^Queue drops: +(?P<pimv2_queue_drops>[\d]+)$')

        # State-Refresh: 0/0
        p50 = re.compile(r'^State-Refresh: +(?P<pimv2_state_refresh>[\d\/]+)$')

        # IGMP statistics: Sent/Received
        p51 = re.compile(r'^IGMP +statistics: +Sent/Received')

        # Total: 2832/4946, Format errors: 0/0, Checksum errors: 0/0
        p52 = re.compile(r'^Total: +(?P<igmp_total>[\d\/]+),'
            r' +Format +errors: +(?P<igmp_format_errors>[\d\/]+),'
            r' +Checksum +errors: +(?P<igmp_checksum_errors>[\d\/]+)$')

        # Host Queries: 2475/1414, Host Reports: 357/3525, Host Leaves: 0/5
        p53 = re.compile(r'^Host +Queries: +(?P<igmp_host_queries>[\d\/]+),'
            r' +Host +Reports: +(?P<igmp_host_reports>[\d\/]+),'
            r' +Host +Leaves: +(?P<igmp_host_leaves>[\d\/]+)$')

        # DVMRP: 0/0, PIM: 0/0
        p54 = re.compile(r'^DVMRP: +(?P<igmp_dvmrp>[\d\/]+), '
            r'+PIM: +(?P<igmp_pim>[\d\/]+)$')

        # Queue drops: 0
        p55 = re.compile(r'^Queue drops: +(?P<igmp_queue_drops>[\d]+)$')

        # TCP statistics:
        p56 = re.compile(r'^TCP +statistics:')

        # Rcvd: 15396 total, 0 checksum errors, 0 no port
        p57 = re.compile(r'^Rcvd: +(?P<tcp_received_total>\d+) +total,'
            r' +(?P<tcp_received_checksum_errors>\d+) +checksum +errors,'
            r' +(?P<tcp_received_no_port>\d+) +no +port$')

        # Sent: 19552 total
        p58 = re.compile(r'^Sent: +(?P<tcp_sent_total>\d+) +total$')

        # EIGRP-IPv4 statistics:
        p59 = re.compile(r'^EIGRP-IPv4 +statistics:')

        # IP-EIGRP statistics:
        p59_1 = re.compile(r'^IP-EIGRP +statistics:')

        # Rcvd: 4612 total
        p60 = re.compile(r'^Rcvd: +(?P<eigrp_ipv4_received_total>\d+) +total$')

        # Sent: 4611 total
        p61 = re.compile(r'^Sent: +(?P<eigrp_ipv4_sent_total>\d+) +total$')

        # BGP statistics:
        p62 = re.compile(r'^BGP +statistics:')

        # Rcvd: 2185 total, 6 opens, 0 notifications, 12 updates
        p63 = re.compile(r'^Rcvd: +(?P<bgp_received_total>\d+) +total,'
            r' +(?P<bgp_received_opens>\d+) +opens,'
            r' +(?P<bgp_received_notifications>\d+) +notifications,'
            r' +(?P<bgp_received_updates>\d+) +updates$')

        # 2167 keepalives, 0 route-refresh, 0 unrecognized
        p64 = re.compile(r'^(?P<bgp_received_keepalives>\d+) +keepalives, '
            r'+(?P<bgp_received_route_refresh>\d+)'
            r' +route-refresh, +(?P<bgp_received_unrecognized>\d+)'
            r' +unrecognized$')

        # Sent: 2304 total, 6 opens, 2 notifications, 0 updates
        p65 = re.compile(r'^Sent: +(?P<bgp_sent_total>\d+) +total,'
            r' +(?P<bgp_sent_opens>\d+) +opens,'
            r' +(?P<bgp_sent_notifications>\d+) +notifications,'
            r' +(?P<bgp_sent_updates>\d+) +updates$')

        # 2296 keepalives, 0 route-refresh
        p66 = re.compile(r'^(?P<bgp_sent_keepalives>\d+) +keepalives, '
            r'+(?P<bgp_sent_route_refresh>\d+) +route-refresh$')

        # initial variables
        ret_dict = {}
        category = ''
        location = ''

        for line in out.splitlines():
            line = line.strip()

            m = p1.match(line)
            if m:
                ret_dict.setdefault('arp_statistics', {})
                continue

            m = p2.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['arp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p3.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['arp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p4.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['arp_statistics']['arp_drops_input_full'] = int(
                    groups['arp_drops'])
                continue

            m = p5.match(line)
            if m:
                ret_dict.setdefault('ip_statistics', {})
                continue

            m = p6.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p7.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p8.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p9.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p10.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p11.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p12.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p13.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p14.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p15.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p16.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p17.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p18.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p19.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p20.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p21.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p22.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ip_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p23.match(line)
            if m:
                ret_dict.setdefault('icmp_statistics', {})
                category = ''
                continue

            m = p24.match(line)
            if m:
                category = 'rcvd'
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p25.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p26.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p27.match(line)
            if m and category=='rcvd':
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p28.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p29.match(line)
            if m:
                category = 'sent'
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p30.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p31.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p32.match(line)
            if m and category=='sent':
                groups = m.groupdict()
                ret_dict['icmp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p33.match(line)
            if m:
                ret_dict.setdefault('udp_statistics', {})
                location = 'udp_statistics'
                continue

            m = p34.match(line)
            if m and location == 'udp_statistics':
                groups = m.groupdict()
                ret_dict['udp_statistics'].update({k: \
                    int(v) for k, v in groups.items() if v})
                continue

            m = p35.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['udp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                location = ''
                continue

            m = p36.match(line)
            if m:
                ret_dict.setdefault('ospf_statistics', {})
                category = 'rcvd'
                location = 'ospf_statistics'
                continue

            m = p37.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p38.match(line)
            if m and category=='rcvd':
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p39.match(line)
            if m and category=='rcvd':
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p40.match(line)
            if m and category=='rcvd':
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p41.match(line)
            if m:
                groups = m.groupdict()
                if location == 'ospf_statistics':
                    category = 'sent'
                    sdict = ret_dict['ospf_statistics']
                    key = 'ospf_sent_total'
                elif location == 'tcp_statistics':
                    sdict = ret_dict['tcp_statistics']
                    key = 'tcp_sent_total'
                elif location == 'eigrp_ipv4_statistics':
                    sdict = ret_dict['eigrp_ipv4_statistics']
                    key = 'eigrp_ipv4_sent_total'
                else:
                    continue
                sdict[key] = int(groups['sent_total'])
                continue

            m = p42.match(line)
            if m and category=='sent':
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p43.match(line)
            if m and category=='sent':
                groups = m.groupdict()
                ret_dict['ospf_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p44.match(line)
            if m:
                ret_dict.setdefault('pimv2_statistics', {})
                continue

            m = p45.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['pimv2_statistics']['pimv2_total'] = \
                    str(groups['pimv2_total'])
                ret_dict['pimv2_statistics']['pimv2_checksum_errors'] = \
                    int(groups['pimv2_checksum_errors'])
                ret_dict['pimv2_statistics']['pimv2_format_errors'] = \
                    int(groups['pimv2_format_errors'])
                continue

            m = p46.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['pimv2_statistics']['pimv2_registers'] = \
                    str(groups['pimv2_registers'])
                ret_dict['pimv2_statistics']['pimv2_non_rp'] = \
                    int(groups['pimv2_non_rp'])
                ret_dict['pimv2_statistics']['pimv2_non_sm_group'] = \
                    int(groups['pimv2_non_sm_group'])
                ret_dict['pimv2_statistics']['pimv2_registers_stops'] = \
                    str(groups['pimv2_registers_stops'])
                ret_dict['pimv2_statistics']['pimv2_hellos'] = \
                    str(groups['pimv2_hellos'])
                continue

            m = p47.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['pimv2_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p48.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['pimv2_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p49.match(line)
            if m and 'igmp_statistics' not in ret_dict:
                groups = m.groupdict()
                ret_dict['pimv2_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p50.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['pimv2_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p51.match(line)
            if m:
                ret_dict.setdefault('igmp_statistics', {})
                continue

            m = p52.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['igmp_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p53.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['igmp_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p54.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['igmp_statistics'].update({k: \
                    str(v) for k, v in groups.items()})
                continue

            m = p55.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['igmp_statistics']['igmp_queue_drops'] = \
                    int(groups['igmp_queue_drops'])
                continue

            m = p56.match(line)
            if m:
                ret_dict.setdefault('tcp_statistics', {})
                location = 'tcp_statistics'
                continue

            m = p57.match(line)
            if m and location == 'tcp_statistics':
                groups = m.groupdict()
                ret_dict['tcp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p59.match(line)
            if m:
                ret_dict.setdefault('eigrp_ipv4_statistics', {})
                location = 'eigrp_ipv4_statistics'
                continue

            m = p59_1.match(line)
            if m:
                ret_dict.setdefault('eigrp_ipv4_statistics', {})
                location = 'eigrp_ipv4_statistics'
                continue

            m = p60.match(line)
            if m:
                groups = m.groupdict()
                ret_dict['eigrp_ipv4_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p62.match(line)
            if m:
                ret_dict.setdefault('bgp_statistics', {})
                continue

            m = p63.match(line)
            if m:
                category = 'rcvd'
                groups = m.groupdict()
                ret_dict['bgp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p64.match(line)
            if m and category == 'rcvd':
                groups = m.groupdict()
                ret_dict['bgp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p65.match(line)
            if m:
                category = 'sent'
                groups = m.groupdict()
                ret_dict['bgp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

            m = p66.match(line)
            if m and category == 'sent':
                groups = m.groupdict()
                ret_dict['bgp_statistics'].update({k: \
                    int(v) for k, v in groups.items()})
                continue

        return ret_dict


# ===========================================================
# Parser for 'show arp application'
# ===========================================================
class ShowArpApplicationSchema(MetaParser):
    """
    Schema for show arp application
    """
    
    schema = {
        'num_of_clients_registered': int,
        'applications': {
            Any(): {
                'id': int,
                'num_of_subblocks': int
            }
        }
    }

class ShowArpApplication(ShowArpApplicationSchema):
    """
    Parser for show arp application
    """
    
    cli_command = 'show arp application'

    def cli(self, output=None):
        if output is None:
            out = self.device.execute(self.cli_command)
        else:
            out = output
        
        # initial variables
        ret_dict = {}
        
        # Number of clients registered: 16
        p1 = re.compile(r'^\s*Number +of +clients +registered: +' \
                r'(?P<num_of_clients>\d+)$')

        # ASR1000-RP SPA Ether215 10024
        p2 = re.compile(r'^(?P<application_name>[\w\W]{0,20})(?P<id>\d+)\s+(?P<num_of_subblocks>\d+)$')

        for line in out.splitlines():
            line = line.strip()
            # Number of clients registered: 16
            m = p1.match(line)
            if m:
                group = m.groupdict()
                ret_dict.setdefault('num_of_clients_registered', \
                    int(group['num_of_clients']))
                continue
            
            # ASR1000-RP SPA Ether215 10024
            m = p2.match(line)
            if m:
                application = ret_dict.setdefault('applications', {})
                group = m.groupdict()
                application[group['application_name'].rstrip()] = {'id': \
                    int(group['id']), 'num_of_subblocks': \
                    int(group['num_of_subblocks'])}
                continue
        return ret_dict


# ========================================
# Parser for 'show arp summary'
# ========================================
class ShowArpSummarySchema(MetaParser):
    """
    Schema for 'show arp summary'
    """

    schema = {
        'total_num_of_entries':{
            Any(): int
        },
        'interface_entries': {
            Any(): int
        },
        Optional('maximum_entries'): {
            Any(): int
        },
        Optional('arp_entry_threshold'): int,
        Optional('permit_threshold'): int
    }

class ShowArpSummary(ShowArpSummarySchema):
    """ Parser for 'show arp summary'"""
    
    cli_command = "show arp summary"

    def cli(self, output=None):
        if output is None:
            out = self.device.execute(self.cli_command)
        else:
            out = output
        
        # initial variables
        ret_dict = {}

        # Total number of entries in the ARP table: 1233
        p1 = re.compile(r'^Total +number +of +entries +in +the +ARP +table: +' \
                r'(?P<arp_table_entries>\d+)\.$')
        
        # Total number of Dynamic ARP entries: 1123
        p2 = re.compile(r'^Total +number +of +(?P<entry_name>[\S\s]+): +' \
                r'(?P<num_of_entries>\d+)\.$')

        # GigabitEthernet0/0/4  4
        p3 = re.compile(r'^(?P<interface_name>[\w\/\.]+) +(?P<entry_count>\d+)')

        # Learn ARP Entry Threshold is 409600 and Permit Threshold is 486400.
        p4 = re.compile(r'^Learn +ARP +Entry +Threshold +is +' \
            r'(?P<arp_entry_threshold>\d+) +and +Permit +Threshold +is +' \
            r'(?P<permit_threshold>\d+).?$')

        # Maximum limit of Learn ARP entry : 512000.
        p5 = re.compile(r'^(?P<maximum_entries_name>[\w\W]+) +: +' \
            r'(?P<maximum_entries>\d+).$')

        for line in out.splitlines():
            line = line.strip()
            # Total number of entries in the ARP table: 1233
            m = p1.match(line)
            if m:
                group = m.groupdict()
                total_num_of_entries = ret_dict.setdefault( \
                    'total_num_of_entries', {})
                total_num_of_entries.update({'arp_table_entries': 
                    int(group['arp_table_entries'])})
                continue
            
            # Total number of Dynamic ARP entries: 1123
            m = p2.match(line)
            if m:
                group = m.groupdict()
                total_num_of_entries = ret_dict.setdefault( \
                    'total_num_of_entries', {})
                key = group['entry_name'].replace(' ', '_').lower()
                total_num_of_entries.update({key: int(group['num_of_entries'])})
                continue

            # GigabitEthernet0/0/4  4
            m = p3.match(line)
            if m:
                group = m.groupdict()
                interfaces = ret_dict.setdefault('interface_entries', {})
                interfaces.update({Common.convert_intf_name(group['interface_name']) : 
                    int(group['entry_count'])})
                continue

            # Learn ARP Entry Threshold is 409600 and Permit Threshold is 486400.
            m = p4.match(line)
            if m:
                group = m.groupdict()
                ret_dict.update({'arp_entry_threshold' : int(group['arp_entry_threshold'])})
                ret_dict.update({'permit_threshold' : int(group['permit_threshold'])})
                continue

            # Maximum limit of Learn ARP entry : 512000.
            m = p5.match(line)
            if m:
                group = m.groupdict()
                key = group['maximum_entries_name'].replace(' ', '_').lower()
                maximum_entries = ret_dict.setdefault('maximum_entries', {})
                maximum_entries.update({key : int(group['maximum_entries'])})

        return ret_dict


class ShowIpArpInspectionVlanSchema(MetaParser):
    """Schema for show ip arp inspection vlan {num}"""
    schema = {
        'source_mac_validation' : str,
        'destination_mac_validation' : str,
        'ip_address_validation' : str,
        'vlan' : int,
        'configuration' : str,
        'operation' : str,
        'acl_logging' : str,
        'dhcp_logging' : str,
        'probe_logging' : str
    }

class ShowIpArpInspectionVlan(ShowIpArpInspectionVlanSchema):
    """Parser for show ip arp inspection vlan {num}"""
    
    cli_command = 'show ip arp inspection vlan {num}'
    def cli(self, num, output=None):
        if output is None:
            output = self.device.execute(self.cli_command.format(num=num))
        ret_dict = {}
        
        #Source Mac Validation : Disabled
        p1 = re.compile(r'^Source\s+Mac\s+Validation\s+:\s+(?P<src_mac_validation>\S+)')
        
        #Destination Mac Validation : Disabled
        p2 = re.compile(r'^Destination\s+Mac\s+Validation\s+:\s+(?P<dst_mac_validation>\S+)')
        
        #IP Address Validation : Disabled
        p3 = re.compile(r'^IP\s+Address\s+Validation\s+:\s+(?P<ip_address_validation>\S+)')
        
        #Vlan Configuration Operation ACL Match Static ACL
        #10 Enabled Active
        p4 = re.compile(r'^(?P<vlan_num>\d+) +'
                r'(?P<configuration>[a-zA-Z]+) +'
                r'(?P<operation>[a-zA-Z]+$)')

        #Vlan ACL Logging DHCP Logging Probe Logging
        #10 Deny Deny Off        
        p5 = re.compile(r'^(?P<vlan>\d+) +'
                r'(?P<acl_logging>[a-zA-Z-]+) +'
                r'(?P<dhcp_logging>[a-zA-Z]+) +'
                r'(?P<probe_logging>[a-zA-Z]+$)')

        for line in output.splitlines():
            line = line.strip()

            #Source Mac Validation : Disabled
            m1 = p1.match(line)
            if m1:
                group = m1.groupdict()
                ret_dict["source_mac_validation"] = group["src_mac_validation"]
            
            #Destination Mac Validation : Disabled
            m2 = p2.match(line)
            if m2:
                group = m2.groupdict()
                ret_dict["destination_mac_validation"] = group["dst_mac_validation"]

            #IP Address Validation : Disabled 
            m3 = p3.match(line)
            if m3:
                group = m3.groupdict()
                ret_dict["ip_address_validation"] = group["ip_address_validation"]

            #Vlan Configuration Operation ACL Match Static ACL
            #10 Enabled Active
            m4 = p4.match(line)
            if m4:
                group = m4.groupdict()
                ret_dict["vlan"] = int(group["vlan_num"])
                ret_dict["configuration"] = group["configuration"]
                ret_dict["operation"] = group["operation"]
            
            #Vlan ACL Logging DHCP Logging Probe Logging
            #10 Deny Deny Off
            m5 = p5.match(line)
            if m5:
                group = m5.groupdict()
                ret_dict["acl_logging"] = group["acl_logging"]
                ret_dict["dhcp_logging"] = group["dhcp_logging"]
                ret_dict["probe_logging"] = group["probe_logging"]
        
        return ret_dict

class ShowAdjacencySummarySchema(MetaParser):
    """Schema for show adjacency summary"""
    schema = {
        'adjacencies_summary':{
            'complete_adjacencies':int,
            'incomplete_adjacencies':int,
            Optional('complete_adj_linktype'):str,
            Optional('incomplete_adj_linktype'):str,
            'database_epoch':int,
            Optional('epoch_entries'):int,
            'summary_events_epoch':int,
            'summary_events_queue':int,
            'hwm_events':int,
            }
        }

class ShowAdjacencySummary(ShowAdjacencySummarySchema):
    """Parser for show adjacency summary"""
    
    cli_command = 'show adjacency summary'
    def cli(self, output=None):
        if output is None:
            output = self.device.execute(self.cli_command)
        # 60004 complete adjacencies
        p1 = re.compile(r'^(?P<complete_adjacencies>\d+) +complete adjacencies$')
         
        # 0 incomplete adjacencies
        p2 = re.compile(r'^(?P<incomplete_adjacencies>\d+) +incomplete adjacencies$')
         
        # complete adjacencies of linktype IPV6 / Ip
        p3 = re.compile(r'^\d+ complete adjacencies of linktype +(?P<complete_adj_linktype>\S+)$')
        #incomplete adjacencies of linktype IPV6 / IP
        p4 = re.compile(r'^\d+ incomplete adjacencies of linktype +(?P<incomplete_adj_linktype>\S+)$')
         
        #Database epoch:        0 (60004 entries at this epoch)
        p5_1 = re.compile(r'^Database epoch: +(?P<database_epoch>\d+) +\((?P<epoch_entries>\d+) entries at this epoch\)$')
        #Database epoch:        0
        p5_2 = re.compile(r'^Database epoch: +(?P<database_epoch>\d+)$')
        # Summary events epoch is 5
        p6 = re.compile(r'^Summary events epoch is +(?P<summary_events_epoch>\d+)$')
        # Summary events queue contains 0 events (high water mark 389 events)
        p7 = re.compile(r'^Summary\s+events\s+queue\s+contains\s+(?P<summary_events_queue>\d+) events +\(high water mark (?P<hwm_events>\d+) events\)$')
        ret_dict = {}
        for line in output.splitlines():
            line = line.strip()
            
            # 60004 complete adjacencies
            m = p1.match(line)
            if m:
                adjacency_dict = ret_dict.setdefault('adjacencies_summary',{})
                adjacency_dict['complete_adjacencies'] = int(m.groupdict()['complete_adjacencies'])
                continue
        
            # 0 incomplete adjacencies
            m = p2.match(line)
            if m:
                adjacency_dict['incomplete_adjacencies'] = int(m.groupdict()['incomplete_adjacencies'])
                continue
            
            # complete adjacencies of linktype IPV6 / IPV4
            m = p3.match(line)
            if m:
                adjacency_dict['complete_adj_linktype'] = m.groupdict()['complete_adj_linktype']
                continue
            #incomplete adjacencies of linktype IPV6 / IPV4
            m = p4.match(line)
            if m:
                adjacency_dict['incomplete_adj_linktype'] = m.groupdict()['incomplete_adj_linktype']
                continue
            #Database epoch:        0 (60004 entries at this epoch)
            m = p5_1.match(line)
            if m:
                adjacency_dict['database_epoch'] = int(m.groupdict()['database_epoch'])
                adjacency_dict['epoch_entries'] = int(m.groupdict()['epoch_entries'])
                continue
            #Database epoch:        0
            m = p5_2.match(line)
            if m:
                adjacency_dict['database_epoch'] = int(m.groupdict()['database_epoch'])
                continue
            # Summary events epoch is 5
            m = p6.match(line)
            if m:
                adjacency_dict['summary_events_epoch'] = int(m.groupdict()['summary_events_epoch'])
                continue
          # Summary events epoch is 5
            m = p7.match(line)
            if m:
                adjacency_dict['summary_events_queue'] = int(m.groupdict()['summary_events_queue'])
                adjacency_dict['hwm_events'] = int(m.groupdict()['hwm_events'])
                continue
        return ret_dict
class ShowIpArpInspectionStatisticsVlanSchema(MetaParser):
    """Schema for show ip arp inspection statistics vlan {num}"""
    schema = {
        'vlan_id': int,
        'forwarded': int,
        'dropped': int,
        'dhcp_drops': int,
        'acl_drops': int,
        'dhcp_permits': int,
        'acl_permits': int,
        'probe_permits': int,
        'source_mac_failures': int,
        'dest_mac_failures': int,
        'ip_validation_failures': int,
        'invalid_protocol_data': int
    }

class ShowIpArpInspectionStatisticsVlan(ShowIpArpInspectionStatisticsVlanSchema):
    """Parser for show ip arp inspection statistics vlan {num}"""
    
    cli_command = 'show ip arp inspection statistics vlan {num}'

    def cli(self, num, output=None):

        if output is None:
            output = self.device.execute(self.cli_command.format(num=num))
        
        # Initialize the result dictionary
        ret_dict = {}

        # Regular expression for the first two sections of the output
        p1 = re.compile(r"^\s*(?P<var_1>\d+)\s+(?P<var_2>\d+)\s+(?P<var_3>\d+)\s+(?P<var_4>\d+)\s+(?P<var_5>\d+)$")

        # Regular expression for the third section of the output
        p2 = re.compile(r"^\s*(?P<var_6>\d+)\s+(?P<var_7>\d+)\s+(?P<var_8>\d+)\s+(?P<var_9>\d+)$")
        
        # This variable is used to parse the first two sections in the output
        flag = True

        # Iterating the output lines
        for line in output.splitlines():
            line = line.strip()

            # Match the current output line with regular expression p1
            m = p1.match(line)

            # Get the statistics Vlan ID, Forwarded, Dropped, DHCP Drops, ACL Drops
            if m and flag:
                dict_val = m.groupdict()
                ret_dict['vlan_id'] = int(dict_val['var_1'])
                ret_dict['forwarded'] = int(dict_val['var_2'])
                ret_dict['dropped'] = int(dict_val['var_3'])
                ret_dict['dhcp_drops'] = int(dict_val['var_4'])
                ret_dict['acl_drops'] = int(dict_val['var_5'])
                flag = False
                continue
            
            # Get the statistics DHCP Permits, ACL Permits, Probe Permits, Source MAC Failures
            elif m and not flag:
                dict_val = m.groupdict()
                ret_dict['dhcp_permits'] = int(dict_val['var_2'])
                ret_dict['acl_permits'] = int(dict_val['var_3'])
                ret_dict['probe_permits'] = int(dict_val['var_4'])
                ret_dict['source_mac_failures'] = int(dict_val['var_5'])
                continue

            # Match the current output line with regular expression p2
            m = p2.match(line)

            # Get the statistics Dest MAC Failures, IP Validation Failures, Invalid Protocol Data
            if m:
                dict_val = m.groupdict()
                ret_dict['dest_mac_failures'] = int(dict_val['var_7'])
                ret_dict['ip_validation_failures'] = int(dict_val['var_8'])
                ret_dict['invalid_protocol_data'] = int(dict_val['var_9'])
                break
        
        return ret_dict
# ======================================================
# Parser for 'show ip arp inspection interfaces '
# ======================================================

class ShowIpArpInspectionInterfacesSchema(MetaParser):
    """Schema for show ip arp inspection interfaces"""
    schema = {
        'interfaces': {
            Any(): {
                'interface': str,
                'state': str,
                'rate': int,
                'interval': int,
            },
        },
    }
class ShowIpArpInspectionInterfaces(ShowIpArpInspectionInterfacesSchema):

    """Parser for show ip arp inspection interfaces"""

    cli_command = 'show ip arp inspection interfaces {interface}'

    def cli(self, interface=None, output=None):
        if output is None:
            output = self.device.execute(self.cli_command.format(interface=interface))

        #  Gi1/0/1          Untrusted               15                 1
        p1 = re.compile(r"^\s+(?P<interface>\S+)\s+(?P<state>\w+)\s+(?P<rate>\d+)\s+(?P<interval>\d+)$")

        ret_dict = {}
        for line in output.splitlines():
            #  Gi1/0/1          Untrusted               15                 1
            m = p1.match(line)
            if m:
                dict_val = m.groupdict()
                Interface_var = dict_val['interface']
                if 'interfaces' not in ret_dict:
                    Interfaces = ret_dict.setdefault('interfaces', {})
                if Interface_var not in ret_dict['interfaces']:
                    Interface_dict = ret_dict['interfaces'].setdefault(Interface_var, {})
                Interface_dict['interface'] = dict_val['interface']
                Interface_dict['state'] = dict_val['state']
                Interface_dict['rate'] = int(dict_val['rate'])
                Interface_dict['interval'] = int(dict_val['interval'])
                continue

        return ret_dict

# ======================================================
# Parser for 'show ip arp inspection log '
# ====================================================== 
class ShowIpArpInspectionLogSchema(MetaParser):
    """Schema for show ip arp inspection log"""
    schema = {
        'buffer_size': int,
        'syslog_rate': str,
        Optional('interfaces'): {
            Any(): {
                'interface': str,
                'vlan_id': int,
                'send_mac_addr': str,
                'sender_ip': str,
                'no_pkts': int,
                'reason': str,
                'time_range': str,
            },
        },
    }
class ShowIpArpInspectionLog(ShowIpArpInspectionLogSchema):

    """Parser for show ip arp inspection log"""

    cli_command = 'show ip arp inspection log'

    def cli(self, output=None):

        if output is None:
            output = self.device.execute(self.cli_command)

        # Total Log Buffer Size : 100
        p1 = re.compile(r"^Total\s+Log\s+Buffer\s+Size\s+:\s+(?P<buffer_size>\d+)$")

        # Syslog rate : 10 entries per 120 seconds.
        p2 = re.compile(r"^Syslog\s+rate\s+:\s+(?P<syslog_rate>\S+\s+\S+\s+\S+\s+\S+\s+\S+)\.$")

        # Gi1/0/37    10    5006.0484.c213  10.1.1.60                1  DHCP Permit   16:35:37 UTC Fri Aug 26 2022
        p3 = re.compile(
            r"^(?P<interface>\S+)\s+(?P<vlan_id>\d+)\s+(?P<send_mac_addr>\S+)\s+(?P<sender_ip>(\d{1,3}\.){3}\d{1,3})\s+(?P<no_pkts>\d+)\s+(?P<reason>\S+\s+\S+)\s+(?P<time_range>\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+)$")

        ret_dict = {}

        for line in output.splitlines():

            # Total Log Buffer Size : 100
            m = p1.match(line)
            if m:
                dict_val = m.groupdict()
                ret_dict['buffer_size'] = int(dict_val['buffer_size'])
                continue

            # Syslog rate : 10 entries per 120 seconds.
            m = p2.match(line)
            if m:
                dict_val = m.groupdict()
                ret_dict['syslog_rate'] = dict_val['syslog_rate']
                continue

            # Gi1/0/37    10    5006.0484.c213  10.1.1.60                1  DHCP Permit   16:35:37 UTC Fri Aug 26 2022
            m = p3.match(line)
            if m:
                dict_val = m.groupdict()
                Interface_var = dict_val['interface']
                if 'interfaces' not in ret_dict:
                    Interfaces = ret_dict.setdefault('interfaces', {})
                if Interface_var not in ret_dict['interfaces']:
                    Interface_dict = ret_dict['interfaces'].setdefault(Interface_var, {})
                Interface_dict['interface'] = dict_val['interface']
                Interface_dict['vlan_id'] = int(dict_val['vlan_id'])
                Interface_dict['send_mac_addr'] = dict_val['send_mac_addr']
                Interface_dict['sender_ip'] = dict_val['sender_ip']
                Interface_dict['no_pkts'] = int(dict_val['no_pkts'])
                Interface_dict['reason'] = dict_val['reason']
                Interface_dict['time_range'] = dict_val['time_range']
                continue

        return ret_dict