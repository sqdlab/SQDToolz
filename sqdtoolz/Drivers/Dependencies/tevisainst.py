#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# Copyright (c) 2021 Tabor Electronics Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================

'''
Tabor-Electronics VISA Instrument.

The class :class:`TEVisaInst` manages remote instrument
with SCPI commands using VISA based communication.

**Example of use**

.. code-block:: python

    from tevisainst import TEVisaInst
    import numpy as np

    ipaddr = '192.168.0.170'

    with TEVisaInst(ipaddr) as inst:

        # Change the default paranoia-level (0, 1, 2)
        # from normal (1) to high (2). This is good for debugging
        # because SYSTEM:ERROR is checked after each SCPI command.
        inst.default_paranoia_level = 2

        # Send query
        resp = inst.send_scpi_query('*IDN?')
        print('Connected to: ' + resp)

        # Send command
        inst.send_scpi_cmd(':INST:CHAN 1; :OUTP ON')
'''

import gc
import socket
import ctypes
import warnings
import numpy as np
import pyvisa as visa
import pyvisa.constants as vc

__version__ = '1.0.1'
__docformat__ = 'reStructuredText'

__all__ = ['TEVisaInst', ]


class TEVisaInst(object):
    '''
    Manage remote instrument with SCPI commands using VISA based communication.
    '''

    def __init__(self, address=None, port=None, use_ni_visa=True):
        '''
        Constructor.

        :param address: IP address or VISA resource-name (optional).
        :param port: port-number for IP address (optional).
        :param use_ni_visa: indicates whether NI-VISA is installed (optional).
        '''
        self._use_ni_visa = bool(use_ni_visa)
        self._vi = None
        self._visa_resource_name = None
        self._default_paranoia_level = 1
        self._resource_manager = None
        if address is not None:
            self.open_instrument(address, port)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        self.close_instrument()

        rsc_mgr = self._resource_manager
        self._resource_manager = None
        if rsc_mgr is not None:
            del rsc_mgr
            gc.collect()

    @property
    def default_paranoia_level(self):
        '''The default paranoia level (0, 1, or 2).

        It is used as default value for the `paranoia_level`
        argument of the method :meth:`TEVisaInst.send_scpi_cmd`.

        The supported levels are 0, 1 or 2,  where
         - 0, send bare SCPI command
         - 1, append `*OPC?` and send as query
         - 2, append `:SYST:ERR?` and print warning if the response is not 0.

        :getter: Gets the default paranoia level (0, 1, or 2).
        :setter: Sets the default paranoia level (0, 1, or 2).
        :type: `int`.
        '''
        return self._default_paranoia_level

    @default_paranoia_level.setter
    def default_paranoia_level(self, value):
        value = max(0, min(int(value), 2))
        self._default_paranoia_level = value

    @property
    def using_ni_visa(self):
        '''Indicates whether `pyvisa` uses NI-VISA (or its own implementation).

        :getter: Gets the flag that indicates whether `pyvisa` uses NI-VISA.
        :type: `bool`.
        '''
        return self._use_ni_visa

    @property
    def vi(self):
        '''The internal visa-instrument (created by `pyvisa`).

        :getter: Gets the internal visa-instrument (created by `pyvisa`).
        :type: `object`.
        '''
        return self._vi

    @property
    def visa_resource_name(self):
        '''The VISA resource name.

        :getter: Gets VISA resource name.
        :type: `str`.
        '''
        return self._visa_resource_name

    def open_instrument(self, address, port=None, extra_init=True):
        '''
        Open instrument connection (VISA session).

        :param address: either IP address or VISA resource name (mandatory).
        :param port: port number used in case of IP address (default is 5025).
        :param extra_init: should initialize the VISA session attributes?
        '''
        if self._vi is not None:
            self.close_instrument()

        if address is not None:

            address = str(address)

            if port is None:
                port = 5025
            else:
                port = int(port)

            rsc_mgr = self._get_resource_manager()

            rsc_name = address
            try:
                packed_ip = socket.inet_aton(address)
                ip_str = socket.inet_ntoa(packed_ip)
                if address == ip_str:
                    rsc_name = "TCPIP::{0}::{1}::SOCKET".format(ip_str, port)
            except OSError:
                pass

            self._vi = rsc_mgr.open_resource(rsc_name)

            if extra_init:
                self._init_vi_inst()

    def close_instrument(self):
        '''Close the instrument connection (VISA session).'''
        vi, self._vi = self._vi, None
        if vi is not None:
            try:
                vi.close()
                vi = None
            except visa.Error:
                pass
            del vi
        self._visa_resource_name = None
        gc.collect()

    def send_scpi_query(self, scpi_str, max_resp_len=None):
        '''Sends SCPI query to instrument.
        :param scpi_str: the SCPI string (a null-terminated string).
        :param max_resp_len: this argument is ignored.
        :returns: response-string
        '''
        del max_resp_len
        return self._vi.query(scpi_str)

    def send_scpi_cmd(self, scpi_str, paranoia_level=None):
        '''Sends SCPI query to instrument.

        The `paranoia-level` is either:
         - 0: send bare SCPI command
         - 1: append `*OPC?` and send as query
         - 2: append `:SYST:ERR?` and print warning if the response is not 0.

        If the given `paranoia-level` is `None`
        then the `default_paranoia_level` is used.

        :param scpi_str: the SCPI string (a null-terminated string).
        :param paranoia_level: either 0, 1, 2 or None.
        :returns: error-code.
        '''
        if paranoia_level is None:
            paranoia_level = self._default_paranoia_level
        else:
            paranoia_level = int(paranoia_level)

        ret_code = 0

        scpi_str = str(scpi_str).strip()
        if 1 == paranoia_level:
            if scpi_str:
                cmd = str(scpi_str) + '; *OPC?'
            else:
                cmd = '*OPC?'

            self._vi.query(cmd)
        elif paranoia_level > 1:
            if scpi_str:
                cmd = str(scpi_str) + '; :SYST:ERR?'
            else:
                cmd = ':SYST:ERR?'

            resp_str = self._vi.query(cmd)
            resp_str = str(resp_str).strip()

            if not resp_str.startswith('0'):
                wrnmsg = 'CMD: "{0}", SYST:ERR: {1}'.format(scpi_str, resp_str)
                warnings.warn(wrnmsg)
                try:
                    ret_code = int(resp_str.split(',')[0])
                except Exception as ex:  # pylint: disable=broad-except
                    ret_code = -1
                    del ex
                self._vi.query('*CLS; *OPC?')
        else:
            cmd = str(scpi_str)
            self._vi.write(cmd)

        return ret_code

    def write_binary_data(
            self,
            scpi_pref,
            bin_dat,
            dtype=None,
            paranoia_level=None,
            mstmo=30000):
        '''Sends block of binary-data to instrument.
        :param scpi_pref: a SCPI string that defines the data (can be None).
        :param bin_dat: a `numpy` array with the binary data.
        :param dtype: the data-type of the elements (optional).
        :param paranoia_level: either 0, 1, 2 or None.
        :param mstmo: timeout in milliseconds (can be None).
        :returns: zero if succeeded; otherwise, error code.
        '''

        ret_val = -1

        if paranoia_level is None:
            paranoia_level = self._default_paranoia_level
        else:
            paranoia_level = int(paranoia_level)

        if scpi_pref is None:
            scpi_pref = ''
        else:
            scpi_pref = str(scpi_pref).strip()

        if paranoia_level >= 1:
            if scpi_pref:
                scpi_pref = '*OPC?; ' + scpi_pref
            else:
                scpi_pref = '*OPC?'

        orig_tmo = None

        if self._vi is not None:
            if mstmo is not None:
                orig_tmo = self._vi.timeout
                self._vi.timeout = int(mstmo)

            try:

                if dtype is None and isinstance(bin_dat, np.ndarray):
                    dtype = bin_dat.dtype.char

                if dtype is not None:
                    self._vi.write_binary_values(
                        scpi_pref, bin_dat, datatype=dtype)
                else:
                    self._vi.write_binary_values(scpi_pref, bin_dat)

                if paranoia_level >= 1:
                    # read the response to the *OPC?
                    self._vi.read()

            except Exception as ex:
                if orig_tmo is not None:
                    self._vi.timeout = orig_tmo

                raise ex

            ret_val = 0

            if paranoia_level >= 2:
                resp_str = self._vi.query(':SYST:ERR?')
                resp_str = str(resp_str).strip()

                if not resp_str.startswith('0'):
                    wrnmsg = 'CMD: "{0}", SYST:ERR: {1}'
                    wrnmsg = wrnmsg.format(scpi_pref, resp_str)
                    warnings.warn(wrnmsg)
                    try:
                        ret_val = int(resp_str.split(',')[0])
                    except Exception as ex:  # pylint: disable=broad-except
                        ret_val = -1
                        del ex
                    self._vi.query('*CLS; *OPC?')

        return ret_val

    def read_binary_data(
            self,
            scpi_pref,
            out_array,
            num_bytes=None,
            mstmo=30000):
        '''Reads block of binary-data from instrument.
        :param scpi_pref: a SCPI string that defines the data (can be None).
        :param out_array: a `numpy` array for the data.
        :param num_bytes: the data size in bytes (for backward compatibility).
        :returns: error-code (zero for success).
        '''

        ret_val = -1
        del num_bytes
        if self._vi is not None:

            if scpi_pref is None:
                scpi_pref = ''
            else:
                scpi_pref = str(scpi_pref)

            orig_tmo = None
            if mstmo is not None:
                orig_tmo = self._vi.timeout
                self._vi.timeout = int(mstmo)

            orig_read_termination = self._vi.read_termination

            try:

                self._vi.read_termination = None

                ret_count = ctypes.c_uint32(0)
                p_ret_count = ctypes.byref(ret_count)

                if scpi_pref:
                    self._vi.write(scpi_pref)

                ch = self._vi.read_bytes(1)

                if ch == b'#':
                    ch = self._vi.read_bytes(1)
                    if b'0' <= ch <= b'9':
                        numbytes = 0
                        numdigits = np.int32(ch.decode('utf-8'))
                        if numdigits > 0:
                            szstr = self._vi.read_bytes(
                                count=int(numdigits), chunk_size=1)
                            szstr = szstr.decode('utf-8')
                            numbytes = int(szstr)

                        if numbytes > out_array.nbytes:
                            numitems = numbytes // out_array.itemsize
                            out_array.resize(numitems, refcheck=False)

                        p_dat = out_array.ctypes.data_as(
                            ctypes.POINTER(ctypes.c_byte))

                        chunk = self._vi.__dict__.get('read_buff_size', 4096)
                        chunk = int(chunk)

                        offset = 0  # np.uint32(0)
                        while offset < numbytes:
                            chunk = min(chunk, numbytes - offset)

                            ptr = ctypes.cast(
                                ctypes.addressof(p_dat.contents) + offset,
                                ctypes.POINTER(ctypes.c_byte))

                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                err_code = self._vi.visalib.viRead(
                                    self._vi.session, ptr, chunk, p_ret_count)

                            #  print('Read {0} bytes, offset {1}, err_code={2}'
                            #        .format(ret_count, offset, err_code))

                            if err_code < 0:
                                break

                            offset = offset + ret_count.value

                        if offset == numbytes:
                            # read the terminating new-line character
                            ch = self._vi.read_bytes(1)
                            if ch == b'\n':
                                ret_val = 0
            finally:
                self._vi.read_termination = orig_read_termination
                if orig_tmo is not None:
                    self._vi.timeout = orig_tmo

        return ret_val

    def _get_resource_manager(self):
        '''Get the VISA resource manager of `pyvisa`.'''
        if self._resource_manager is None:
            if self._use_ni_visa:
                self._resource_manager = visa.ResourceManager()
            else:
                self._resource_manager = visa.ResourceManager('@py')

        return self._resource_manager

    def _init_vi_inst(
            self,
            timeout_msec=10000,
            read_buff_size_bytes=8192,
            write_buff_size_bytes=8192):
        '''Initialize the internal VISA instrument session.

        :param timeout_msec: VISA-Timeout (in milliseconds)
        :param read_buff_size_bytes: VISA Read-Buffer Size (in bytes)
        :param write_buff_size_bytes: VISA Write-Buffer Size (in bytes)
        '''

        vi = self._vi
        if vi is not None:
            vi.timeout = int(timeout_msec)
            try:
                vi.visalib.set_buffer(
                    vi.session, vc.VI_READ_BUF, int(read_buff_size_bytes))
            except NotImplementedError:
                vi.set_visa_attribute(
                    vc.VI_READ_BUF, int(read_buff_size_bytes))
            vi.__dict__['read_buff_size'] = read_buff_size_bytes
            try:
                vi.visalib.set_buffer(
                    vi.session, vc.VI_WRITE_BUF, int(write_buff_size_bytes))
            except NotImplementedError:
                vi.set_visa_attribute(
                    vc.VI_WRITE_BUF, int(write_buff_size_bytes))
            vi.__dict__['write_buff_size'] = write_buff_size_bytes
            vi.read_termination = '\n'
            vi.write_termination = '\n'
            intf_type = vi.get_visa_attribute(vc.VI_ATTR_INTF_TYPE)
            if intf_type in (vc.VI_INTF_USB,
                             vc.VI_INTF_GPIB,
                             vc.VI_INTF_TCPIP,
                             vc.VI_INTF_ASRL):
                vi.set_visa_attribute(
                    vc.VI_ATTR_WR_BUF_OPER_MODE, vc.VI_FLUSH_ON_ACCESS)
                vi.set_visa_attribute(
                    vc.VI_ATTR_RD_BUF_OPER_MODE, vc.VI_FLUSH_ON_ACCESS)
                if intf_type == vc.VI_INTF_TCPIP:
                    vi.set_visa_attribute(
                        vc.VI_ATTR_TERMCHAR_EN, vc.VI_TRUE)  # vc.VI_FALSE
                elif intf_type == vc.VI_INTF_ASRL:
                    vi.set_visa_attribute(vc.VI_ATTR_ASRL_BAUD, 115200)
                    vi.set_visa_attribute(vc.VI_ATTR_ASRL_END_OUT, 0)
                    vi.set_visa_attribute(vc.VI_ATTR_ASRL_END_IN, 2)
            vi.clear()
