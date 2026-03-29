import socket
import struct
import os
import time

LISTEN_IP = "127.0.0.1"
LISTEN_PORT = 5005
TIMEOUT = 2.0  

def create_packet(conn_id, seq_num, msg_type, payload):
    header = struct.pack('!IIBH', conn_id, seq_num, msg_type, len(payload))
    return header + payload

def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    print(f"Server listening on {LISTEN_IP}:{LISTEN_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)
        conn_id, seq_num, msg_type, p_len = struct.unpack('!IIBH', data[:11])
        filename = data[11:].decode()

        if msg_type == 1: 
            print(f"Request received for: {filename} (ConnID: {conn_id})")
            if not os.path.exists(filename):
                err_pkt = create_packet(conn_id, 0, 4, b"File Not Found")
                sock.sendto(err_pkt, addr)
                continue

            with open(filename, 'rb') as f:
                current_seq = 0
                while True:
                    chunk = f.read(512) 
                    transmit_packet = create_packet(conn_id, current_seq, 2, chunk)
                    
                    while True:
                        sock.sendto(transmit_packet, addr)
                        sock.settimeout(TIMEOUT)
                        try:
                            ack_data, _ = sock.recvfrom(1024)
                            a_id, a_seq, a_type, _ = struct.unpack('!IIBH', ack_data[:11])
                            
                            if a_type == 3 and a_seq == current_seq:
                                print(f"ACK {current_seq} received.")
                                break 
                        except socket.timeout:
                            print(f"Timeout! Retransmitting Seq {current_seq}...")

                    current_seq += 1
                    if len(chunk) < 512: 
                        print("Transfer complete.")
                        break
            sock.settimeout(None)

if __name__ == "__main__":
    run_server()