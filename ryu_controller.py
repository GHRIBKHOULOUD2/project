#!/usr/bin/env python3
# =============================================================
# ryu_controller.py — Ryu SDN Controller
# Handles OpenFlow, VLAN policy, QoS, host tracking
# PC: 192.168.1.100  OVS: 192.168.1.10/br0:192.168.1.11
# =============================================================

import os, sys, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, arp
from ryu.lib import hub

from config import HOST_VLAN, HOST_QOS, VLAN_DEFAULT_POLICY, CONTROLLER_IP
from shared_state import read_state, write_state, add_alert, get_vlan_policy


class NetTwinController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.ip_to_mac   = {}
        self.datapaths   = {}
        self.monitor_thread = hub.spawn(self._monitor)
        print(f"[ryu] NetTwin Controller started — listening on port 6633")

    # ── Switch connect ────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp      = ev.msg.datapath
        ofproto = dp.ofproto
        parser  = dp.ofproto_parser
        dpid    = format(dp.id, 'd')

        self.datapaths[dpid] = dp
        print(f"[ryu] Switch connected: dpid={dpid}")

        # Update shared state
        state = read_state()
        state.setdefault("switches", {})[dpid] = "online"
        write_state(state)

        # Default flow: send to controller
        match  = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions)
        print(f"[ryu] Default flow installed on dpid={dpid}")

    # ── Packet in ─────────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg     = ev.msg
        dp      = msg.datapath
        ofproto = dp.ofproto
        parser  = dp.ofproto_parser
        in_port = msg.match['in_port']
        dpid    = format(dp.id, 'd')

        pkt     = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt is None:
            return

        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port

        # Track IP→MAC
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            self.ip_to_mac[src_ip] = src_mac
            self._update_host_status(src_ip, "online")

            # Check if blocked
            state   = read_state()
            blocked = set(state.get("blocked", []))
            if src_ip in blocked or dst_ip in blocked:
                print(f"[ryu] BLOCKED: {src_ip} -> {dst_ip}")
                return  # Drop packet

            # VLAN policy check
            src_vlan = HOST_VLAN.get(src_ip, 0)
            dst_vlan = HOST_VLAN.get(dst_ip, 0)
            if src_vlan and dst_vlan and src_vlan != dst_vlan:
                policy = get_vlan_policy(state, src_vlan, dst_vlan)
                if policy == "deny":
                    print(f"[ryu] VLAN DENY: {src_ip}(V{src_vlan}) -> {dst_ip}(V{dst_vlan})")
                    return  # Drop

        # ARP tracking
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt and arp_pkt.src_ip:
            self._update_host_status(arp_pkt.src_ip, "online")

        # Forward packet
        if dst_mac in self.mac_to_port.get(dpid, {}):
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rule if known port
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self._add_flow(dp, 1, match, actions)

        # Send packet
        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out  = parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data
        )
        dp.send_msg(out)

    # ── Helper: add flow ──────────────────────────────────────
    def _add_flow(self, dp, priority, match, actions, idle=0, hard=0):
        ofproto = dp.ofproto
        parser  = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod  = parser.OFPFlowMod(
            datapath=dp, priority=priority, match=match,
            instructions=inst, idle_timeout=idle, hard_timeout=hard
        )
        dp.send_msg(mod)

    # ── Helper: update host status ────────────────────────────
    def _update_host_status(self, ip: str, status: str):
        if not ip or ip.startswith("0.") or ip == "255.255.255.255":
            return
        state = read_state()
        hosts = state.setdefault("hosts", {})
        prev  = hosts.get(ip, {}).get("status", "offline")
        hosts[ip] = {
            "status":    status,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if prev == "offline" and status == "online":
            print(f"[ryu] Host online: {ip}")
        write_state(state)

    # ── Monitor loop ──────────────────────────────────────────
    def _monitor(self):
        while True:
            hub.sleep(30)
            try:
                state = read_state()
                hosts = state.get("hosts", {})
                now   = time.time()
                for ip, hdata in list(hosts.items()):
                    if hdata.get("status") == "online":
                        last = hdata.get("last_seen", "")
                        if last:
                            try:
                                t = time.strptime(last, "%Y-%m-%d %H:%M:%S")
                                age = now - time.mktime(t)
                                if age > 120:  # 2 minutes timeout
                                    hosts[ip]["status"] = "offline"
                                    print(f"[ryu] Host timeout: {ip}")
                            except Exception:
                                pass
                write_state(state)
            except Exception as e:
                print(f"[ryu] Monitor error: {e}")
