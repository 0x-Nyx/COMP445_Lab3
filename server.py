import socket
import struct
import os
import sys

LISTEN_IP = "0.0.0.0"
TIMEOUT   = 2.0

# Message type constants
MSG_REQUEST = 1
MSG_DATA    = 2
MSG_ACK     = 3
MSG_ERROR   = 4


def create_packet(conn_id, seq_num, msg_type, payload):
    header = struct.pack('!IIBH', conn_id, seq_num, msg_type, len(payload))
    return header + payload


def run_server(listen_port, seg_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, listen_port))
    print(f"Server listening on {LISTEN_IP}:{listen_port} (segment size: {seg_size} bytes)")

    while True:
        # Wait indefinitely for a new REQUEST
        sock.settimeout(None)
        data, addr = sock.recvfrom(65535)

        # --- Parse header ---
        if len(data) < 11:
            print("[WARN] Received malformed packet, ignoring.")
            continue

        conn_id, seq_num, msg_type, p_len = struct.unpack('!IIBH', data[:11])
        payload = data[11:]

        if msg_type != MSG_REQUEST:
            print(f"[WARN] Expected REQUEST (1), got type {msg_type}, ignoring.")
            continue

        filename = payload.decode(errors="replace").strip()
        print(f"Request received for: {filename} (ConnID: {conn_id})")

        # --- Check file exists ---
        if not os.path.exists(filename):
            err_pkt = create_packet(conn_id, 0, MSG_ERROR, b"File Not Found")
            sock.sendto(err_pkt, addr)
            print(f"[ERROR] File not found: {filename}")
            continue

        # --- Segment and send file ---
        with open(filename, 'rb') as f:
            current_seq = 0

            while True:
                chunk = f.read(seg_size)          # runtime-configurable segment size

                if not chunk:
                    # Empty read means file size was exact multiple of seg_size.
                    # Send zero-length DATA packet so the client detects end-of-transfer.
                    chunk = b""

                transmit_packet = create_packet(conn_id, current_seq, MSG_DATA, chunk)
                is_last = (len(chunk) < seg_size)

                # Stop-and-Wait: keep sending until correct ACK received
                while True:
                    sock.sendto(transmit_packet, addr)
                    sock.settimeout(TIMEOUT)

                    try:
                        ack_data, _ = sock.recvfrom(65535)

                        if len(ack_data) < 11:
                            print("[WARN] Malformed ACK, ignoring.")
                            continue

                        a_id, a_seq, a_type, _ = struct.unpack('!IIBH', ack_data[:11])

                        if a_type == MSG_ACK and a_id == conn_id and a_seq == current_seq:
                            print(f"ACK {current_seq} received.")
                            break                 # correct ACK — move to next segment
                        else:
                            print(f"[WARN] Unexpected ACK (id={a_id}, seq={a_seq}, type={a_type}), ignoring.")

                    except socket.timeout:
                        print(f"Timeout! Retransmitting Seq {current_seq}...")

                current_seq += 1

                if is_last:
                    print("Transfer complete.")
                    break

        sock.settimeout(None)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python server.py <port> <segment_size>")
        print("Example: python server.py 5005 512")
        sys.exit(1)

    listen_port = int(sys.argv[1])
    seg_size    = int(sys.argv[2])
    run_server(listen_port, seg_size)
