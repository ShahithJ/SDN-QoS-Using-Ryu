from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls

from ryu.ofproto import ofproto_v1_3

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.lib.packet import icmp
from ryu.lib.packet import ether_types


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
	    # --------------------------------------------------
    # Switch Connected
    # --------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        print("--------------------------------------")
        print("Switch Connected")
        print("Datapath ID :", datapath.id)
        print("--------------------------------------")

        # Install QoS Meters
        self.install_meters(datapath)

        # Table-miss flow entry
        match = parser.OFPMatch()

        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )
        ]

        self.add_flow(
            datapath,
            priority=0,
            match=match,
            actions=actions
        )

        print("Default Flow Installed")


    # --------------------------------------------------
    # Install QoS Meters
    # --------------------------------------------------
    def install_meters(self, datapath):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        print("Installing QoS Meters...")

        # ---------------- Meter 1 ----------------
        # ICMP (Unlimited)

        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=1,
                bands=[]
            )
        )

        print("Meter 1 Installed (ICMP)")


        # ---------------- Meter 2 ----------------
        # UDP -> 10 Mbps

        bands = [
            parser.OFPMeterBandDrop(
                rate=10000,
                burst_size=1000
            )
        ]

        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=2,
                bands=bands
            )
        )

        print("Meter 2 Installed (UDP 10 Mbps)")


        # ---------------- Meter 3 ----------------
        # TCP -> 3 Mbps

        bands = [
            parser.OFPMeterBandDrop(
                rate=3000,
                burst_size=500
            )
        ]

        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=3,
                bands=bands
            )
        )

        print("Meter 3 Installed (TCP 3 Mbps)")
        print("QoS Initialization Completed")


    # --------------------------------------------------
    # Install Flow
    # --------------------------------------------------
    def add_flow(self, datapath, priority, match, actions, meter_id=None):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = []

        if meter_id is not None:
            instructions.append(
                parser.OFPInstructionMeter(meter_id)
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
	    # --------------------------------------------------
    # Packet-In Handler
    # --------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):

        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        dpid = datapath.id

        # ----------------------------
        # MAC Learning
        # ----------------------------

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # Output Port Decision
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

        # ----------------------------
        # Protocol Classification
        # ----------------------------

        if ip_pkt:

            # ICMP
            if pkt.get_protocol(icmp.icmp):

                priority = 30
                meter_id = 1

                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=0x0800,
                    ip_proto=1,
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
                    in_port=in_port,
                    eth_type=0x0800,
                    ip_proto=17,
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
                    in_port=in_port,
                    eth_type=0x0800,
                    ip_proto=6,
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
                    in_port=in_port,
                    eth_type=0x0800,
                    eth_src=src,
                    eth_dst=dst
                )

        else:

            # ARP and other non-IP packets
            match = parser.OFPMatch(
                in_port=in_port,
                eth_src=src,
                eth_dst=dst
            )
                # --------------------------------------------------
        # Install Flow
        # --------------------------------------------------

        if out_port != ofproto.OFPP_FLOOD:

            # Install only ARP / unknown flows
            if meter_id is None:

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
