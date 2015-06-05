#!/usr/bin/env python

import re, socket, io
from random import getrandbits

def unmask(masking_key, msg):
    decoded_msg = bytearray()
    b = io.BytesIO(msg)
    b.seek(0)
    i = 0
    buf = b.read(1)
    while buf != '':
        mask = ( masking_key >> (i%4 *8) ) & 0xff
        buf = ord(buf) ^ mask
        decoded_msg.append(buf)
        buf = b.read(1)
        i += 1

    return decoded_msg

class WSServerTest():
    def test(self, selftest):
        self.test_result = False

        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        # reuse previously exited socket.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        line = selftest.mbed.serial_readline()
        selftest.dump_serial()

        SERVER_IP = line.split()[-1].split(":")[0]
        SERVER_PORT = int(line.split()[-1].split(":")[1])
        print SERVER_IP, SERVER_PORT
        s.connect( (SERVER_IP, SERVER_PORT) )

        self.sock = s
        self.sock.setblocking(1)
        self.run()

        s.close()
        selftest.dump_serial_end()

        return selftest.RESULT_SUCCESS if self.test_result else selftest.RESULT_FAILURE

    def run(self):
        # send opening handshake
        openHandshake = "GET %s HTTP/1.1\r\n" + \
                        "Host: %s:%d\r\n" + \
                        "Upgrade: websocket\r\n" + \
                        "Connection: Upgrade\r\n" + \
                        "Sec-WebSocket-Key: L159VM0TWUzyDxwJEIEzjw==\r\n" + \
                        "Sec-WebSocket-Version: 13\r\n\r\n"
        self.sock.sendall(openHandshake);

        # receive the closing handshake
        chunk = self.sock.recv(2048)
        if chunk == '':
            raise RuntimeError("socket connection broken")
        print repr(chunk)

        # get the reply key
        headers = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", chunk))
        rsp_code = headers["Sec-WebSocket-Accept"]

        # compare the reply key
        if rsp_code == "DdLWT/1JcX+nQFHebYP+rqEx5xI=":
            print "HOST: Got correct closing handshake"
            # send a message encoded with websocket
            msg = "Can you hear me?"
            masking_key = getrandbits(32);
            frame = chr(0b10000001) + chr(0b10000000|len(msg)) + \
                    chr( (masking_key >> 0 ) & 0xff ) + \
                    chr( (masking_key >> 8 ) & 0xff ) + \
                    chr( (masking_key >> 16) & 0xff ) + \
                    chr( (masking_key >> 24) & 0xff )
            frame = bytearray(frame) + unmask(masking_key, msg)
            self.sock.sendall(frame)

        while True:
            try:
                dat = self.sock.recv(2048)
            except Exception as e:
                print str(e)
                break
            if not dat:
                break

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
            frame['Application Message'] = dat.read()

            msg = frame['Application Message']
            expected = "roger"
            if expected == msg:
                self.test_result = True
            else:
                print "HOST: Expected {} Got {}".format(expected, msg)
