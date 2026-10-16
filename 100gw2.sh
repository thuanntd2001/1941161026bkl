#!/bin/bash
INTERFACE="enp2s0"
NEW_IP="192.168.100.16/24"
GATEWAY="192.168.100.2"

CONNECTION_NAME="Wired connection 1"

nmcli connection modify "$CONNECTION_NAME" \
    ipv4.addresses "$NEW_IP" \
    ipv4.gateway "$GATEWAY" \
    ipv4.method manual

nmcli connection down "$CONNECTION_NAME"
nmcli connection up "$CONNECTION_NAME"
