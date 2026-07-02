"""
qos_controller.py

Advanced Routing using SDN for Network QoS
Version 1.0
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from qos_statistics import Statistics
from qos_logger import QoSLogger


class QoSController(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)

        self.stats = Statistics()
        self.log = QoSLogger()

        self.mac_to_port = {}

        self.log.info("===================================")
        self.log.info(" SDN QoS Controller Started")
        self.log.info(" OpenFlow Version : 1.3")
        self.log.info(" Waiting for switches...")
        self.log.info("===================================")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath

        self.stats.switch()

        self.log.info("-----------------------------------")
        self.log.info("Switch Connected")
        self.log.info(f"Datapath ID : {datapath.id}")
        self.log.info("-----------------------------------")

        self.install_default_flow(datapath)

        self.install_qos_meters(datapath)

    def install_default_flow(self, datapath):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )
        ]

        inst = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=0,
            match=match,
            instructions=inst
        )

        datapath.send_msg(mod)

        self.log.info("Default flow installed")

    def install_qos_meters(self, datapath):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.log.info("Installing QoS meters...")

        # Meter 1 (ICMP)
        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=1,
                bands=[]
            )
        )

        self.log.info("Meter 1 : ICMP")

        # Meter 2 (UDP)
        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=2,
                bands=[
                    parser.OFPMeterBandDrop(
                        rate=10000,
                        burst_size=1000
                    )
                ]
            )
        )

        self.log.info("Meter 2 : UDP (10 Mbps)")

        # Meter 3 (TCP)
        datapath.send_msg(
            parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=3,
                bands=[
                    parser.OFPMeterBandDrop(
                        rate=3000,
                        burst_size=500
                    )
                ]
            )
        )

        self.log.info("Meter 3 : TCP (3 Mbps)")
        self.log.info("QoS initialization completed")
