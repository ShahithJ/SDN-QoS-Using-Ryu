# 🚀 SDN QoS Controller Using Ryu and OpenFlow

![Python](https://img.shields.io/badge/Python-3.10-blue)
![OpenFlow](https://img.shields.io/badge/OpenFlow-1.3-green)
![Ryu](https://img.shields.io/badge/Ryu-Controller-red)
![Mininet](https://img.shields.io/badge/Mininet-Network-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

A Software Defined Networking (SDN) Quality of Service (QoS) controller developed using the Ryu SDN Framework, OpenFlow 1.3, Open vSwitch, and Mininet.

The controller classifies network traffic into ICMP, TCP, and UDP flows and applies different QoS policies using OpenFlow meters.

---

# 📌 Features

- SDN Controller using Ryu Framework
- OpenFlow 1.3 Support
- QoS using OpenFlow Meters
- Traffic Classification
  - ICMP
  - TCP
  - UDP
- MAC Learning Switch
- Dynamic Flow Installation
- Bandwidth Limiting
- Real-time Packet Classification Logs
- Compatible with Open vSwitch and Mininet

---

# 🛠 Technologies Used

- Python 3
- Ryu SDN Framework
- OpenFlow 1.3
- Open vSwitch (OVS)
- Mininet
- Ubuntu Linux

---

# 📂 Project Structure

```
SDN-QoS-Using-Ryu
│
├── controllers/
│   └── qos_controller.py
│
├── config/
├── docs/
├── report/
├── results/
├── screenshots/
├── scripts/
├── topology/
├── traffic/
│
├── README.md
├── requirements.txt
└── LICENSE
```

---

# 🏗 Architecture

```
                +----------------------+
                |    Ryu Controller    |
                +----------+-----------+
                           |
                    OpenFlow 1.3
                           |
          +----------------+----------------+
          |                                 |
     +---------+                     +---------+
     |   h1    |                     |   h2    |
     +---------+                     +---------+
             \                       /
              \                     /
               +-------------------+
               |   Open vSwitch    |
               +-------------------+
```

---

# ⚙ QoS Policy

| Protocol | Meter ID | Priority | Bandwidth |
|----------|----------|----------|-----------|
| ICMP | 1 | High | 100 Mbps |
| UDP | 2 | Medium | 10 Mbps |
| TCP | 3 | Low | 3 Mbps |

---

# 🚀 Installation

Clone the repository

```bash
git clone git@github.com:ShahithJ/SDN-QoS-Using-Ryu.git
```

Go into the project

```bash
cd SDN-QoS-Using-Ryu
```

Install dependencies

```bash
pip3 install -r requirements.txt
```

---

# ▶ Running the Controller

```bash
cd controllers

ryu-manager qos_controller.py
```

---

# 🌐 Creating the Mininet Topology

```bash
sudo mn \
--topo single,2 \
--switch ovs,protocols=OpenFlow13 \
--controller remote,ip=127.0.0.1,port=6653
```

---

# 🧪 Testing

## Connectivity Test

```bash
pingall
```

---

## ICMP Test

```bash
h1 ping h2
```

---

## TCP Test

```bash
iperf
```

Expected Output

```
≈ 3 Mbps
```

---

## UDP Test

```bash
h1 iperf -s -u &
h2 iperf -u -c h1 -b 20M
```

Expected Result

- UDP classified successfully
- Meter 2 applied
- Packet drops visible in meter statistics

---

# 📊 Verification

Check installed flows

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

Check installed meters

```bash
sudo ovs-ofctl -O OpenFlow13 dump-meters s1
```

Check meter statistics

```bash
sudo ovs-ofctl -O OpenFlow13 meter-stats s1
```

---

# 📈 Experimental Results

The implemented QoS controller successfully

- Classified ICMP, TCP and UDP traffic
- Installed protocol-specific OpenFlow rules
- Applied bandwidth limitations using OpenFlow meters
- Achieved TCP bandwidth limitation of approximately 3 Mbps
- Successfully enforced UDP rate limiting with packet drops confirmed through meter statistics

---

# 🔮 Future Enhancements

- Multiple Switch Support
- REST API Integration
- Dynamic QoS Policies
- Machine Learning based Traffic Classification
- Web Dashboard

---

# 👨‍💻 Author

**Shahith J**

Bachelor of Engineering – Cyber Security

---

# 📜 License

This project is licensed under the MIT License.
