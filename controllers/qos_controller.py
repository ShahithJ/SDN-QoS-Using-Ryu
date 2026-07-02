from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls

from ryu.ofproto import ofproto_v1_3

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
from ryu.lib.packet import tcp
from ryu.lib.packet import udp


class QoSSwitch(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):

        super(QoSSwitch, self).__init__(*args, **kwargs)

        self.mac_to_port = {}

        print()
        print("======================================")
        print(" SDN QoS Controller Started")
        print(" OpenFlow Version : 1.3")
        print("======================================")
        print()


    def add_flow(self,
                 datapath,
                 priority,
                 match,
                 actions,
                 meter_id=None):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = []

        if meter_id is not None:
            instructions.append(
                parser.OFPInstructionMeter(
                    meter_id,
                    ofproto.OFPIT_METER
                )
            )

        instructions.append(
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        )

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions
        )

        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        print("--------------------------------------")
        print("Switch Connected")
        print("Datapath ID :", datapath.id)
        print("--------------------------------------")

        #
        # Table-Miss Flow
        #
        match = parser.OFPMatch()

        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )
        ]

        self.add_flow(
            datapath,
            0,
            match,
            actions
        )

        print("Installing QoS Meters...")

        #
        # Meter 1 : ICMP (High Priority)
        #
        bands = [
            parser.OFPMeterBandDrop(rate=100000, burst_size=1000)
        ]

        req = parser.OFPMeterMod(
            datapath=datapath,
            command=ofproto.OFPMC_ADD,
            flags=ofproto.OFPMF_KBPS,
            meter_id=1,
            bands=bands
        )

        datapath.send_msg(req)
        print("Meter 1 Installed (ICMP)")

        #
        # Meter 2 : UDP (10 Mbps)
        #
        bands = [
            parser.OFPMeterBandDrop(rate=10000, burst_size=1000)
        ]

        req = parser.OFPMeterMod(
            datapath=datapath,
            command=ofproto.OFPMC_ADD,
            flags=ofproto.OFPMF_KBPS,
            meter_id=2,
            bands=bands
        )

        datapath.send_msg(req)
        print("Meter 2 Installed (UDP 10 Mbps)")

        #
        # Meter 3 : TCP (3 Mbps)
        #
        bands = [
            parser.OFPMeterBandDrop(rate=3000, burst_size=1000)
        ]

        req = parser.OFPMeterMod(
            datapath=datapath,
            command=ofproto.OFPMC_ADD,
            flags=ofproto.OFPMF_KBPS,
            meter_id=3,
            bands=bands
        )

        datapath.send_msg(req)

        print("Meter 3 Installed (TCP 3 Mbps)")
        print("QoS Initialization Completed")
        print()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):

        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        dpid = datapath.id

        # -----------------------------
        # MAC Learning
        # -----------------------------

        self.mac_to_port.setdefault(dpid, {})

        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [
            parser.OFPActionOutput(out_port)
        ]

        priority = 1
        meter_id = None

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        arp_pkt = pkt.get_protocol(arp.arp)

        # -----------------------------
        # ARP
        # -----------------------------

        if arp_pkt:

            match = parser.OFPMatch(
                eth_type=0x0806,
                in_port=in_port,
                eth_src=src,
                eth_dst=dst
            )

        # -----------------------------
        # IPv4 Traffic
        # -----------------------------

        elif ip_pkt:

            # ICMP
            if pkt.get_protocol(icmp.icmp):

                priority = 30
                meter_id = 1

                match = parser.OFPMatch(
                    eth_type=0x0800,
                    ip_proto=1,
                    in_port=in_port,
                    eth_src=src,
                    eth_dst=dst
                )

                self.logger.info(
                    "ICMP Packet | %s -> %s",
                    src,
                    dst
                )

            # UDP
            elif pkt.get_protocol(udp.udp):

                priority = 20
                meter_id = 2

                match = parser.OFPMatch(
                    eth_type=0x0800,
                    ip_proto=17,
                    in_port=in_port,
                    eth_src=src,
                    eth_dst=dst
                )

                self.logger.info(
                    "UDP Packet | 10 Mbps | %s -> %s",
                    src,
                    dst
                )

            # TCP
            elif pkt.get_protocol(tcp.tcp):

                priority = 10
                meter_id = 3

                match = parser.OFPMatch(
                    eth_type=0x0800,
                    ip_proto=6,
                    in_port=in_port,
                    eth_src=src,
                    eth_dst=dst
                )

                self.logger.info(
                    "TCP Packet | 3 Mbps | %s -> %s",
                    src,
                    dst
                )

            else:

                match = parser.OFPMatch(
                    eth_type=0x0800,
                    in_port=in_port,
                    eth_src=src,
                    eth_dst=dst
                )

        # -----------------------------
        # Other Ethernet Traffic
        # -----------------------------

        else:

            match = parser.OFPMatch(
                in_port=in_port,
                eth_src=src,
                eth_dst=dst
            )
                # --------------------------------------------------
        # Install Flow
        # --------------------------------------------------

        if out_port != ofproto.OFPP_FLOOD:

            if meter_id is not None:

                self.add_flow(
                    datapath=datapath,
                    priority=priority,
                    match=match,
                    actions=actions,
                    meter_id=meter_id
                )

            else:

                self.add_flow(
                    datapath=datapath,
                    priority=priority,
                    match=match,
                    actions=actions
                )

        # --------------------------------------------------
        # Send Packet
        # --------------------------------------------------

        data = None

        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )

        datapath.send_msg(out)
