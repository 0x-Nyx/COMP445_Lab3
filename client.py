import socket
import struct
import random
import sys

def run_client(server_ip, server_port, filename, seg_size):
    conn_id = random.randint(1000, 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    header = struct.pack('!IIBH', conn_id, 0, 1, len(filename))
    sock.sendto(header + filename.encode(), (server_ip, server_port))
    
    expected_seq = 0
    with open("received_" + filename, 'wb') as f:
        while True:
            try:
                sock.settimeout(5.0)
                data, addr = sock.recvfrom(seg_size + 11)
                c_id, seq, m_type, p_len = struct.unpack('!IIBH', data[:11])
                payload = data[11:]

                if m_type == 4: 
                    print(f"Error from server: {payload.decode()}")
                    break

                if c_id == conn_id and seq == expected_seq:
                    f.write(payload)
                    ack = struct.pack('!IIBH', conn_id, seq, 3, 0)
                    sock.sendto(ack, addr)
                    print(f"Received Seq {seq}, ACK sent.")
                    expected_seq += 1
                    
                    if p_len < seg_size:
                        print("File download finished.")
                        break
                else:
                    ack = struct.pack('!IIBH', conn_id, seq, 3, 0)
                    sock.sendto(ack, addr)

            except socket.timeout:
                print("Server timed out. Exiting.")
                break

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python client.py <IP> <Port> <File> <SegSize>")
    else:
        run_client(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))