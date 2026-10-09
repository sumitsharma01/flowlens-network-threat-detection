# Dataset Features (UNSW-NB15 Training Set)
Available at : https://unsw-my.sharepoint.com/personal/z5025758_ad_unsw_edu_au/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fz5025758%5Fad%5Funsw%5Fedu%5Fau%2FDocuments%2FUNSW%2DNB15%20dataset%2FCSV%20Files%2FTraining%20and%20Testing%20Sets&ga=1

The selected train/test CSVs contain 45 columns: 42 input features plus `id`, `attack_cat`, and `label`. The raw dataset has a different schema. Below is a description of the most important columns:

| **Column**               | **Description**                                                                 |
|--------------------------|---------------------------------------------------------------------------------|
| id                       | Record identifier (unique row index).                                           |
| dur                      | Duration of the flow (seconds).                                                 |
| proto                    | Protocol type (e.g., TCP, UDP, ICMP).                                           |
| service                  | Application service on the destination (e.g., http, ftp, dns).                  |
| state                    | State of the connection (e.g., FIN, CON, INT).                                  |
| spkts / dpkts            | Number of packets sent (source/destination).                                    |
| sbytes / dbytes          | Number of bytes transferred (source/destination).                               |
| rate                     | Transaction rate (packets per second).                                          |
| sttl / dttl              | Source/Destination time-to-live values.                                         |
| sload / dload            | Source/Destination bits per second.                                             |
| sloss / dloss            | Source/Destination packet loss.                                                 |
| sinpkt / dinpkt          | Source/Destination inter-packet arrival time (ms).                              |
| sjit / djit              | Source/Destination jitter (ms).                                                 |
| swin / dwin              | Source/Destination TCP window advertisement.                                    |
| stcpb / dtcpb            | Source/Destination TCP base sequence number.                                    |
| tcprtt                   | TCP round trip time.                                                           |
| synack                   | TCP connection setup time (SYN → ACK).                                          |
| ackdat                   | TCP acknowledgment time (ACK → DATA).                                          |
| smean / dmean            | Mean packet size for source/destination.                                        |
| trans_depth              | Number of pipelined commands (FTP/HTTP).                                       |
| response_body_len        | Length of the response body (e.g., HTTP).                                       |
| ct_srv_src               | Count of connections to the same service from source IP.                        |
| ct_state_ttl             | Count of connections with the same state & TTL.                                 |
| ct_dst_ltm               | Count of connections to the same destination host in the last 100 connections.  |
| ct_src_dport_ltm         | Count of connections from same source to same destination port in last 100 connections. |
| ct_dst_sport_ltm         | Count of connections to same destination from same source port.                 |
| ct_dst_src_ltm           | Count of connections to the same destination and source IP.                     |
| is_ftp_login             | 1 if FTP login successful, else 0.                                              |
| ct_ftp_cmd               | Number of FTP commands.                                                        |
| ct_flw_http_mthd         | Number of HTTP methods used.                                                   |
| ct_src_ltm / ct_srv_dst  | Counts for repeated source or destination connections.                          |
| is_sm_ips_ports          | Binary flag for same source & destination IP and port.                          |
| attack_cat               | Attack category (e.g., DoS, Exploits, Fuzzers, Reconnaissance).                 |
| label                    | Binary class label → 0 = Normal, 1 = Attack.                                    |


## Reproducible download
Run `python scripts/download_data.py` from the repository root. This obtains the complete predefined train/test CSVs from a revision-pinned public mirror with expected SHA-256 checksums. Source and attribution: https://research.unsw.edu.au/projects/unsw-nb15-dataset. See `data/raw/manifest.json` after download.
