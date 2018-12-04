<p align="center">
  <img src="./imgs/logo.png">
</p>

# Introduction
We develop a novel network application to support large file transfer between two computers in the Internet, which is  our LFTP should use UDP as the transport layer protocol.
(5) LFTP must realize 100% reliability as TCP;
(6) LFTP must implement flow control function similar as TCP;
(7) LFTP must implement congestion control function similar as TCP;
(8) LFTP server side must be able to support multiple clients at the same time; (9) LFTP should provide meaningful debug information when programs are executed.
# Related Work
## Standard Reliable Data Transfer
- **MSS (maximum segment size)** is the maximum amount of application-layer data in the segment.
- MSS is typically set by first determining the length of the largest link-layer frame that can be sent by the local sending host, the so-called, **MTU(maximum transmission unit)**.
- When sends a large file, it typically breaks the file into chunks of size MSS.
- The **sequence number** for a segment is therefore the byte-stream number of the first byte in the segment.
- It randomly choose an initial sequence number.
- The **acknowledgment number** that receiver puts in its segment is the sequence number of the next byte expected from sender.
- Only acknowledges bytes up to the first missing byte in the stream, which is said to provide **cumulative acknowledgments**.
- **Selective acknowledgment**, allows receiver to acknowledge out-of-order segments selectively rather than just cumulatively acknowledging the last correctly received, inorder segment.
- **RTT** (round-trip time), which is the time it takes for a small packet to travel from sender to receiver and then back to the sender.
- **SampleRTT**, for a segment is the amount of time between when the segment is sent (that is, passed to IP) and when an acknowledgment for the segment is received. The SampleRTT is being estimated for only one of the transmitted (except a segment that has been retransmitted) but currently unacknowledged segments, leading to a new value of SampleRTT approximately once every RTT.
- **EWMA (exponential weighted moving average)** of EstimatedRTT:  
```EstimatedRTT = 0.875 • EstimatedRTT + 0.125 • SampleRTT```
- RTT variation, **DevRTT**:  
```DevRTT = 0.75 • DevRTT + 0.25 • | SampleRTT – EstimatedRTT |```
- Determines the retransmission **timeout interval**:  
```TimeoutInterval = EstimatedRTT + 4 • DevRTT```
- An initial TimeoutInterval value of 1 second is recommended.
- Each time TCP retransmits, it sets the next timeout interval to twice the previous value.
- Simplified TCP sender:
    ```c
    /* Assume sender is not constrained by TCP flow or congestion control, that data from above is less
    than MSS in size, and that data transfer is in one direction only. */

    NextSeqNum=InitialSeqNumber
    SendBase=InitialSeqNumber

    loop (forever) {
        switch(event)

            event: data received from application above
                create TCP segment with sequence number NextSeqNum
                if (timer currently not running)
                    start timer
                pass segment to IP
                NextSeqNum=NextSeqNum+length(data)
                break;
                
            event: timer timeout
                retransmit not-yet-acknowledged segment with
                    smallest sequence number
                start timer
                break;
            
            event: ACK received, with ACK field value of y
                if (y > SendBase) {
                    SendBase=y
                    if (there are currently any not yet
                        acknowledged segments)
                        start timer
                }
                else { /* a duplicate ACK for already ACKed
                    segment */
                    increment number of duplicate ACKs
                        received for y
                    if (number of duplicate ACKS received
                        for y==3)
                        /* TCP fast retransmit */
                        resend segment with sequence number y
                }
                break;
        
    } /* end of loop forever */
    ```
## Standard Flow Control
- Sender maintains a variable called the **receive window**, denoted **rwnd**. Informally, the receive window is used to give the sender an idea of how much free buffer space is available at the receiver:  
```rwnd = RcvBuffer – [LastByteRcvd – LastByteRead]```
- Receiver places its current value of rwnd in the receive window field of every segment it sends to sender.
- Sender make sure that:  
```LastByteSent – LastByteAcked ≦ rwnd```
- When receiver's receive buffer becomes full so that rwnd = 0, to avoid sender being blocked, it requires sender to continue to send segments with one data byte. These segments will be acknowledged by the receiver. Eventually the buffer will begin to empty and the acknowledgments will contain a nonzero rwnd value.
## Standard Connection Management
- TCP three-way handshake: segment exchange:  
![](https://rjgeek.github.io/images/2016/11/tcp_12.png?t=1%3E)
- Closing a TCP connection:   
![](https://rjgeek.github.io/images/2016/11/tcp_13.png?t=1%3E)
## Our Adapted Connection Close
![](our_adapted_connection_close.svg)
## Standard Congestion Control
- Sender keeps track of an variable, the **congestion window**, denoted **cwnd**, imposes a constraint on the rate at which a TCP sender can send traffic into the network, roughly **cwnd/RTT bytes/sec**.
- FSM description of congestion control:  
![](https://i.stack.imgur.com/cJDMC.png)
## Our implementation of Congestion Control

- In our design, we neatly follow the FSM as above, receiving the events (init, new ACK, duplicate ACK, timeout) as parameters and judging the current status of congestion control. And then calling the `retransmission` function we have implemented when `timeout` or `duplicate ack` event happens.  And we change ssthresh, cwnd, congestion status and duplicateAck according to the FSM, outputing corresponding logs describing the change of congestion status. 
- To listen the events which will trigger these events, we judge some of them related to `ack` in `rcvAckAndRwnd` function which is a thread to deal with receiving packets, and the other related to timeout in `detectTimeout` function which is another thread to running all the time and judge whether the difference between the current time and startTime is more than the timeout interval (controlled by RTT).  
  - When the `ackNum` equals to `NextSeqNum`, `duplicate ack` happens.
  - When `ackNum` is more than `NextSeqNum`, `new ack` happens.
  - When `detectTimeout` thread detects a time out, `time out` event is triggered to switch the Congestion Status.

## Standard Client-Server Application using TCP

![](https://4.bp.blogspot.com/-DvRMFAAWUI8/Vk4EqPpbEvI/AAAAAAAAOWA/RBrpMgP3B50/s640/TCP.PNG)
## Standard TCP Segment Structure
![](https://rjgeek.github.io/images/2016/11/tcp_1.png?t=2%3E)
## Our Adapted Header Structure
<table>
   <tr>
      <td align="center" colspan="4">32 bits</td>
   </tr>
   <tr>
      <td align="center" colspan="4">Sequence number</td>
   </tr>
   <tr>
      <td align="center" colspan="4">Acknowledgement number</td>
   </tr>
   <tr>
      <td align="center" colspan="1">ACK</td>
      <td align="center" colspan="1">SF(SYN=1, FIN=2)</td>
      <td align="center" colspan="2">Receive window</td>
   </tr>
</table>

## Our Design of C-S Model

In the basic implementation of one client and one server model,(`UDPClient.py` and `UDPServer.py`) it satisfies that the client side and transmit a large file to the server side. And in one to one model, C and S can exchange their roles to make sure that the `server` can also transmit to the `client`, which is the process of "downing a file from a server".

And our support to  multiple client at the same time, we encapsulate another layer and add thread of top-layer server(`server.py`) side.

### Top-layer server side

The top-layer server side receives client packet including dealing with 3 handshakes in a while loop. When it receives "HAND SHAKE 3" from a client side, `userCount` adds up one and new thread to serve the client starts. 

> In the while loop, we use `rejudge` variable like a `lock` to wait for 3 HAND SHAKE in case some client only makes one hand shake.  

As for each client thread, we resolves the command to  filename, command(`lget`, `lsend`). 

- Firstly, the server will return a server port back to the client

- Secondly, it will judge the role of the server and call corresponding class. 

  - UDPServer.getFile for `lsend` command 
  - UDPClient.sendFile for `lget` command

- Thirdly, if the command is `lget`, the server will check whether the file exists in the `ROOT_DIR`. 

  > in our experiment, the root directory is `/Test/Server`  relative to the path of `server.py`

### Top-layer client side

In the top-layer client side, the first thing to do is splitting the input to command, dest_ip, dest_port and the name of the large file. 

Because one client runs a client program, there's no need for threads in top-layer client(but there's some in basic-layer client). 

There's four things to do for a client.

- Firstly, it should check whether the file to send exists in the directory. 

  > like in server side, the root directory is  `/Test/Client`  relative to the path of `client.py`

- Secondly, it will send handshake message to server according to the server address and server port assigned in the command line. And wait for 3 hand shake finishing and connection setting up.

- Thirdly, it will get the server port for transferring file instead of setting up connection. And then the client will send the file name to the server. 

- At last, it will judge the command and decide the role of client side, like in server

  - UDPClient.sendFile for `lsend`
  - UDPClient.getFile for `lget`

# Experiments
We conduct the following experiments to observe the behaviors and demonstrate the effectiveness of this program.

## Environment
  -  `Windows Ubuntu 18.04 bash ` (**cannot execute directly in windows 10 CMD**) 
  - Client - `macOS Mojave 10.14.1`  
    Server - `Ubuntu 14.04.1`
## Getting started
Firstly, you should create new directory on both client and server side.
- Client
    ```console
    # mkdir Test 
    # mkdir Test/Client
    ```
- Server
  ```console
  # mkdir Test 
  # mkdir Test/Server
  ```

Then, put the file you would like to send to the server in the `Client` while put those you would like to get from the server in `Server`.   

Now, you could run this program.

- The format of input in the command line of server side is:

  ```console
  # ./server.py
  ```

- That of client side is:

  ```console
  #  ./client.py {lsend, lget}  servername:serverport myLargeFileName
  ```

## Single Machine Example

Run the server at first:

![runningServer](./imgs/runningServer.png)

### `lsend`

#### Client Side

In this test case, we try to transfer the movie, *The Hunger Games*, using the command `./client.py lsend 127.0.0.1:16666 FILENAME`

##### If file does not exist

![fileNotExistInClient](./imgs/fileNotExistInClient.png)

##### File sent normally

In the client side, logs of debugging message of LFTP is as follows, including the process of `establishing connection`, `progress message`, `the change of congestion status`, `the change of RTT`, `the sequence number of the packet retransmitted`. 

![clientDebuggingMsg](./imgs/clientDebuggingMsg.png)

#### Server Side

In the server side, in other words, receiving side, the output message includes the progress messages and average speed in each 5% progress. 

![lsendServer](./imgs/lsendServer.png)

when finishing receiving the file, the file can play. 

<img src="./imgs/normallyPlay.png" width="400"/>

### `lget`

This is a test for **multi-users**.

In `lget` command, two sides act in the same way but their roles exchange. 

To test multi-users, we create 3 directories, each of which includes the sub directory `Test/Client` to receive the file from the server and necessary python programs (`client.py`, `UDPClient.py`, `UDPServer.py`).

![beforeMulti](./imgs/beforeMulti.png)

During the file transferring process, compared with single user mode, 3 client divides the speed averagely. 

![inMulti1](./imgs/inMulti1.png)

![AfterMulti](./imgs/AfterMulti.png)

After they finishing receiving the file, the content in the directories is as follows:

![multiResult](./imgs/multiResult.png)

And all of received file can be executed well, guaranteeing the 100% reliability. 

## Test on the Server
