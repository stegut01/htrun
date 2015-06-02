#!/usr/bin/env python

import re
import socket, base64
import threading
import hashlib
import io

def unmask(masking_key, msg):
    b = io.BytesIO(msg)
    b.seek(0)
    i = 0
    buf = b.read(1)
    while buf != '':
        mask = ( masking_key >> (i%4 *8) ) & 0xff
        buf = ord(buf) ^ mask
        print "unmasked buf", buf, unichr(buf)
        buf = b.read(1)
        i += 1

    return buf


class client_thread (threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.sock.setblocking(1)

    def run(self):
        chunk = self.sock.recv(2048)
        if chunk == '':
            raise RuntimeError("socket connection broken")
        #chunks.append(chunk)
        print repr(chunk)

        headers = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", chunk))

        response = {}
        response["Upgrade"] = "websocket"
        response["Connection"] = "Upgrade"
        rsp_code = headers['Sec-WebSocket-Key'] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        rsp_code = hashlib.sha1(rsp_code).digest()
        rsp_code = base64.b64encode(rsp_code)
        response["Sec-WebSocket-Accept"] = rsp_code

        r_str = "\r\n".join( [ str(x[0]) + ": " + x[1] for x in response.items() ] ) + "\r\n\r\n"
        r_str = "HTTP/1.1 101 Switching Protocols\r\n" + r_str
        print repr(r_str)

        self.sock.send(r_str)

        while True:
            try:
                dat = self.sock.recv(2048)
            except Exception as e:
                print str(e)
                break
            if not dat: break

            #dat =  binascii.a2b_uu(dat)
            dat = io.BytesIO(dat)
            frame = {}

            buf = ord(dat.read(1))
            frame['FIN'] = buf >> 7
            frame['RSV1'] = buf & 0b01000000 << 1 >> 7
            frame['RSV2'] = buf & 0b00100000 << 2 >> 7
            frame['RSV3'] = buf & 0b00010000 << 3 >> 7
            frame['opcode'] = buf & 0b00001111
            buf = ord(dat.read(1))
            frame['MASK'] = buf >> 7
            frame['Payload len'] = buf & 0b01111111
            frame['Masking-key'] =  (
                ( ord(dat.read(1)) <<  0 ) |
                ( ord(dat.read(1)) <<  8 ) |
                ( ord(dat.read(1)) << 16 ) |
                ( ord(dat.read(1)) << 24 )
            )
            frame['Application Message'] = dat.read()

            key = frame['Masking-key']
            masked_msg = frame['Application Message']
            msg = unmask(key, masked_msg)
            if msg == "Can you hear me?":
                resp = chr(0b10000010) + chr(0b00000101) + "roger"
                self.sock.sendall(resp)
                print repr(resp)


class WSCliendtTest():
    def test(self, selftest):
        test_result = True

        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        # reuse previously exited socket.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        SERVER_PORT = 2312
        s.bind(("localhost", SERVER_PORT))
        SERVER_IP = str(socket.gethostbyname(socket.getfqdn()))
        selftest.mbed.serial_write("{}:{}\n".format(SERVER_IP, SERVER_PORT))
        selftest.mbed.flush()
        s.listen(5)

        selftest.dump_serial()

        try:
            while 1:
                # accept connections from outside
                (clientsocket, address) = s.accept()
                # threaded server
                print clientsocket, address
                ct = client_thread(clientsocket)
                ct.run()
        finally:
            s.close()

        selftest.dump_serial_end()
        return selftest.RESULT_SUCCESS if test_result else selftest.RESULT_FAILURE