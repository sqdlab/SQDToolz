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
Tabor-Electronics Proteus API.

Control Proteus PXI hardware-modules directly.

This Python module can be used only from Python code running on the PC that is
physically connected to the PXI chassis. It wraps the `TEProteus.dll` which is
a native C DLL (located under `C:/Windows/System32`), and therefore it gives
a fast way to control the hardware-modules.

There are two classes in this Python module:
:class:`TEProteusAdmin` and :class:`TEProteusInst`.

:class:`TEProteusAdmin` (the *instruments-administrator*) is used for finding
the PXI slots which are the connection-slots of the hardware modules, and for
opening instances of :class:`TEProteusInst`, where each instance of that class
represents a single *instrument*.

:class:`TEProteusInst` represents a single *instrument* that controls
one or more hardware-modules. In case of multiple hardware-modules the modules
must be located in contiguous PXI slots. After opening *instrument*, the user
can send SCP-Commands download waveform-data etc. using the methods from
:class:`TEProteusInst`.

**Example of use**

.. code-block:: python

    from teproteus import TEProteusAdmin, TEProteusInst
    import numpy as np

    with TEProteusAdmin() as admin:

        # Get list of available PXI slots
        slot_ids = admin.get_slot_ids()

        # Assume that at least one slot was found
        sid = slot_ids[0]

        # Open a single-slot instrument:
        with admin.open_instrument(slot_id=sid) as inst

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

import os
import gc
import numpy as np
import ctypes as ct
import warnings
from ctypes.util import find_library
from numpy.ctypeslib import ndpointer

__version__ = '1.0.1'
__docformat__ = 'reStructuredText'

__all__ = [
    'TEProteusAdmin',
    'TEProteusInst']


class TEProteusAdmin(object):
    '''Instruments Administrator (single instance per process).'''

    def _load_te_proteus_library(self, lib_dir_path=None):
        '''Loads the `TEProteus.dll`.'''

        if lib_dir_path is None:
            script_dir = os.path.realpath(__file__)
            script_dir = os.path.dirname(script_dir)
            lib_path = os.path.join(script_dir, 'TEProteus.dll')
            if os.path.exists(lib_path):
                lib_dir_path = script_dir
        
        if lib_dir_path is not None:
            libpath = os.path.join(lib_dir_path, 'TEProteus.dll')
        else:
            libpath = find_library('TEProteus.dll')
            if not libpath:
                sys32path = str('C:/Windows/System32/TEProteus.dll')
                if os.path.exists(sys32path):
                    libpath = sys32path	
                else:
                    print('TEProteus.dll is not present at : C:/Windows/System32')
        
        print('Load TEProteus.dll from : {0}'.format(libpath))
        teplib = ct.cdll.LoadLibrary(libpath)

        if teplib is None:
            raise Exception('failed to load TEProteus.dll')

        self._libpath = libpath
        self._teplib = teplib

        self._tep_open_inst_admin = teplib.tep_open_inst_admin
        self._tep_open_inst_admin.restype = ct.c_int
        self._tep_open_inst_admin.argtypes = None

        self._tep_close_inst_admin = teplib.tep_close_inst_admin
        self._tep_close_inst_admin.restype = ct.c_int
        self._tep_close_inst_admin.argtypes = None

        self._tep_is_inst_admin_open = teplib.tep_is_inst_admin_open
        self._tep_is_inst_admin_open.restype = ct.c_int
        self._tep_is_inst_admin_open.argtypes = None

        self._tep_get_slot_ids = teplib.tep_get_slot_ids
        self._tep_get_slot_ids.restype = ct.c_uint32
        self._tep_get_slot_ids.argtypes = [
            ndpointer(ct.c_uint32, flags="C_CONTIGUOUS"), ct.c_uint32]

        self._tep_get_slot_info = teplib.tep_get_slot_info
        self._tep_get_slot_info.restype = ct.c_int64
        self._tep_get_slot_info.argtypes = [ct.c_uint32, ]

        self._tep_get_slot_number = teplib.tep_get_slot_number
        self._tep_get_slot_number.restype = ct.c_uint16
        self._tep_get_slot_number.argtypes = [ct.c_int64, ]

        self._tep_get_slot_chassis_index = teplib.tep_get_slot_chassis_index
        self._tep_get_slot_chassis_index.restype = ct.c_uint16
        self._tep_get_slot_chassis_index.argtypes = [ct.c_int64, ]

        self._tep_get_slot_is_dummy = teplib.tep_get_slot_is_dummy
        self._tep_get_slot_is_dummy.restype = ct.c_int32
        self._tep_get_slot_is_dummy.argtypes = [ct.c_int64, ]

        self._tep_get_slot_is_in_use = teplib.tep_get_slot_is_in_use
        self._tep_get_slot_is_in_use.restype = ct.c_int32
        self._tep_get_slot_is_in_use.argtypes = [ct.c_int64, ]

        self._tep_get_slot_parent_instr_id = \
            teplib.tep_get_slot_parent_instr_id
        self._tep_get_slot_parent_instr_id.restype = ct.c_uint16
        self._tep_get_slot_parent_instr_id.argtypes = [ct.c_int64, ]

        self._tep_get_slot_fpga_version = teplib.tep_get_slot_fpga_version
        self._tep_get_slot_fpga_version.restype = ct.c_uint32
        self._tep_get_slot_fpga_version.argtypes = [ct.c_int64, ]

        self._tep_get_slot_fpga_svn = teplib.tep_get_slot_fpga_svn
        self._tep_get_slot_fpga_svn.restype = ct.c_uint32
        self._tep_get_slot_fpga_svn.argtypes = [ct.c_int64, ]

        self._tep_get_slot_fpga_date = teplib.tep_get_slot_fpga_date
        self._tep_get_slot_fpga_date.restype = ct.c_int32
        self._tep_get_slot_fpga_date.argtypes = [
            ct.c_int64,
            ct.c_char_p,
            ct.POINTER(ct.c_char),
            ct.c_uint32]

        self._tep_get_slot_idn_str = teplib.tep_get_slot_idn_str
        self._tep_get_slot_idn_str.restype = ct.c_int32
        self._tep_get_slot_idn_str.argtypes = [
            ct.c_int64,
            ct.c_char_p,
            ct.POINTER(ct.c_char),
            ct.c_uint32]

        self._tep_get_slot_fw_options = teplib.tep_get_slot_fw_options
        self._tep_get_slot_fw_options.restype = ct.c_uint32
        self._tep_get_slot_fw_options.argtypes = [ct.c_int64, ]

        self._tep_get_slot_hw_options = teplib.tep_get_slot_hw_options
        self._tep_get_slot_hw_options.restype = ct.c_uint32
        self._tep_get_slot_hw_options.argtypes = [ct.c_int64, ]

        self._tep_get_slot_installed_memory = \
            teplib.tep_get_slot_installed_memory
        self._tep_get_slot_installed_memory.restype = ct.c_uint32
        self._tep_get_slot_installed_memory.argtypes = [ct.c_int64, ]

        self._tep_open_instrument = teplib.tep_open_instrument
        self._tep_open_instrument.restype = ct.c_int64
        self._tep_open_instrument.argtypes = [ct.c_uint32, ct.c_int]

        self._tep_open_multi_slots_instrument = \
            teplib.tep_open_multi_slots_instrument
        self._tep_open_multi_slots_instrument.restype = ct.c_int64
        self._tep_open_multi_slots_instrument.argtypes = [
            ndpointer(ct.c_uint32, flags="C_CONTIGUOUS"),
            ct.c_uint32,
            ct.c_int]

        self._tep_close_instrument = teplib.tep_close_instrument
        self._tep_close_instrument.restype = ct.c_int
        self._tep_close_instrument.argtypes = [ct.c_int64, ]

        self._tep_close_all_instruments = teplib.tep_close_all_instruments
        self._tep_close_all_instruments.restype = ct.c_int
        self._tep_close_all_instruments.argtypes = None

        self._tep_get_instrument_id = teplib.tep_get_instrument_id
        self._tep_get_instrument_id.restype = ct.c_uint16
        self._tep_get_instrument_id.argtypes = [ct.c_int64, ]

        self._tep_open_comm_intf = teplib.tep_open_comm_intf
        self._tep_open_comm_intf.restype = ct.c_int64
        self._tep_open_comm_intf.argtypes = [ct.c_int64, ]

        self._tep_close_comm_intf = teplib.tep_close_comm_intf
        self._tep_close_comm_intf.restype = ct.c_int
        self._tep_close_comm_intf.argtypes = [ct.c_int64, ct.c_int64]

        self._tep_send_scpi = teplib.tep_send_scpi
        self._tep_send_scpi.restype = ct.c_int
        self._tep_send_scpi.argtypes = [
            ct.c_int64,
            ct.c_char_p,
            ct.POINTER(ct.c_char),
            ct.c_uint32]

        self._tep_write_binary_data = teplib.tep_write_binary_data
        self._tep_write_binary_data.restype = ct.c_int
        self._tep_write_binary_data.argtypes = [
            ct.c_int64,
            ct.c_char_p,
            ct.POINTER(ct.c_uint8),
            ct.c_uint64]

        self._tep_read_binary_data = teplib.tep_read_binary_data
        self._tep_read_binary_data.restype = ct.c_int
        self._tep_read_binary_data.argtypes = [
            ct.c_int64,
            ct.c_char_p,
            ct.POINTER(ct.c_uint8),
            ct.c_uint64]

        self._tep_get_write_stream_intf = teplib.tep_get_write_stream_intf
        self._tep_get_write_stream_intf.restype = ct.c_int64
        self._tep_get_write_stream_intf.argtypes = [ct.c_int64, ct.c_int]

        self._tep_get_stream_packet_size = teplib.tep_get_stream_packet_size
        self._tep_get_stream_packet_size.restype = ct.c_uint32
        self._tep_get_stream_packet_size.argtypes = None

        self._tep_is_write_stream_active = teplib.tep_is_write_stream_active
        self._tep_is_write_stream_active.restype = ct.c_int
        self._tep_is_write_stream_active.argtypes = [ct.c_int64, ]

        self._tep_get_stream_empty_buff = teplib.tep_get_stream_empty_buff
        self._tep_get_stream_empty_buff.restype = ct.POINTER(ct.c_uint8)
        self._tep_get_stream_empty_buff.argtypes = [ct.c_int64, ]

        self._tep_put_stream_full_buff = teplib.tep_put_stream_full_buff
        self._tep_put_stream_full_buff.restype = ct.c_int
        self._tep_put_stream_full_buff.argtypes = [
            ct.c_int64, ct.POINTER(ct.c_uint8), ct.c_int]

        self._tep_put_stream_empty_buff = teplib.tep_put_stream_empty_buff
        self._tep_put_stream_empty_buff.restype = ct.c_int
        self._tep_put_stream_empty_buff.argtypes = [
            ct.c_int64, ct.POINTER(ct.c_uint8)]

        self._tep_push_stream_packet = teplib.tep_push_stream_packet
        self._tep_push_stream_packet.restype = ct.c_int
        self._tep_push_stream_packet.argtypes = [
            ct.c_int64, ct.POINTER(ct.c_uint8), ct.c_int64, ct.c_int]

    def _unload_te_proteus_library(self):

        teplib = self._teplib

        self._teplib = None

        self._libpath = None

        self._tep_open_inst_admin = None

        self._tep_close_inst_admin = None

        self._tep_is_inst_admin_open = None

        self._tep_get_slot_ids = None

        self._tep_get_slot_info = None

        self._tep_get_slot_number = None

        self._tep_get_slot_chassis_index = None

        self._tep_get_slot_is_dummy = None

        self._tep_get_slot_is_in_use = None

        self._tep_get_slot_parent_instr_id = None

        self._tep_get_slot_fpga_version = None

        self._tep_get_slot_fpga_svn = None

        self._tep_get_slot_fpga_date = None

        self._tep_get_slot_idn_str = None

        self._tep_get_slot_fw_options = None

        self._tep_get_slot_hw_options = None

        self._tep_get_slot_installed_memory = None

        self._tep_open_instrument = None

        self._tep_open_multi_slots_instrument = None

        self._tep_close_instrument = None

        self._tep_close_all_instruments = None

        self._tep_get_instrument_id = None

        self._tep_open_comm_intf = None

        self._tep_close_comm_intf = None

        self._tep_send_scpi = None

        self._tep_write_binary_data = None

        self._tep_read_binary_data = None

        self._tep_get_write_stream_intf = None

        self._tep_get_stream_packet_size = None

        self._tep_is_write_stream_active = None

        self._tep_get_stream_empty_buff = None

        self._tep_put_stream_full_buff = None

        self._tep_put_stream_empty_buff = None

        self._tep_push_stream_packet = None

        if teplib is not None:
            libHandle = teplib._handle  # pylint: disable=W0212
            del teplib
            if libHandle is not None:
                try:
                    kernel32 = ct.windll.kernel32
                    kernel32.FreeLibrary(libHandle)  # @UndefinedVariable
                except Exception:  # pylint: disable=broad-except
                    pass

        gc.collect()

    def __init__(self, lib_dir_path=None):

        self._libpath = None

        self._teplib = None

        self._inst_dict = dict()

        self._tep_open_inst_admin = None

        self._tep_close_inst_admin = None

        self._tep_is_inst_admin_open = None

        self._tep_get_slot_ids = None

        self._tep_get_slot_info = None

        self._tep_get_slot_number = None

        self._tep_get_slot_chassis_index = None

        self._tep_get_slot_is_dummy = None

        self._tep_get_slot_is_in_use = None

        self._tep_get_slot_parent_instr_id = None

        self._tep_get_slot_fpga_version = None

        self._tep_get_slot_fpga_svn = None

        self._tep_get_slot_fpga_date = None

        self._tep_get_slot_idn_str = None

        self._tep_get_slot_fw_options = None

        self._tep_get_slot_hw_options = None

        self._tep_get_slot_installed_memory = None

        self._tep_open_instrument = None

        self._tep_open_multi_slots_instrument = None

        self._tep_close_instrument = None

        self._tep_close_all_instruments = None

        self._tep_get_instrument_id = None

        self._tep_open_comm_intf = None

        self._tep_close_comm_intf = None

        self._tep_send_scpi = None

        self._tep_write_binary_data = None

        self._tep_read_binary_data = None

        self._tep_get_write_stream_intf = None

        self._tep_get_stream_packet_size = None

        self._tep_is_write_stream_active = None

        self._tep_get_stream_empty_buff = None

        self._tep_put_stream_full_buff = None

        self._tep_put_stream_empty_buff = None

        self._tep_push_stream_packet = None

        self._load_te_proteus_library(lib_dir_path)

        self._tep_close_inst_admin()

        self._tep_open_inst_admin()

        if not self._tep_is_inst_admin_open():
            raise Exception('failed to open InstAdmin')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        self.close_inst_admin()
        self._unload_te_proteus_library()

    def open_inst_admin(self):
        '''Opens the *single* instruments-administrator.
        :returns: zero if succeeded; otherwise, error code.
        '''
        return self._tep_open_inst_admin()

    def close_inst_admin(self):
        '''Closes the *single* instruments-administrator.
        :returns: zero if succeeded; otherwise, error code.
        '''
        self.close_all_instruments()
        return self._tep_close_inst_admin()

    def is_inst_admin_open(self):
        '''Checks if the instruments-administrator is open.
        :returns: True if the administrator is open; otherwise, False.
        '''
        ret_code = self._tep_is_inst_admin_open()
        return False if 0 == ret_code else True

    def get_slot_ids(self):
        '''Gets the slot-identifiers of the PXI slots with Proteus boards.
        :returns: array of slot-identifiers.
        '''
        slotIds = np.zeros(256, dtype=np.uint32)
        numSlots = self._tep_get_slot_ids(slotIds, np.uint32(256))
        return slotIds[0:numSlots]

    def get_slot_number_in_chassis(self, slot_id):
        '''Gets the slot-number inside the chassis of the specified slot.
        :param slot_id: the slot identifier.
        :returns: the slot-number inside the chassis (zero is none)
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_number(slotInfPtr)
        return 0

    def get_slot_chassis_index(self, slot_id):
        '''Gets the zero-based index of the chassis of the specified slot.
        :param slot_id: the slot identifier.
        :returns: the zero-based index of the chassis.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_chassis_index(slotInfPtr)
        return -1

    def get_slot_is_dummy(self, slot_id):
        '''Checks whether the specified slot is a dummy slot.
        :param slot_id: the slot identifier.
        :returns: `True` if the slot is dummy; otherwise, `False`.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            if self._tep_get_slot_is_dummy(slotInfPtr):
                return True
        return False

    def get_slot_is_in_use(self, slot_id):
        '''Checks whether the specified slot is in use (by instrument).
        :param slot_id: the slot identifier.
        :returns: `True` if the slot is in use; otherwise, `False`.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            if self._tep_get_slot_is_in_use(slotInfPtr):
                return True
        return False

    def get_slot_parent_instr_id(self, slot_id):
        '''Get the instrument-id of the parent-instrument of the specified slot.
        :param slot_id: the slot identifier.
        :returns: the instrument-id of the parent-instrument (zero if none)
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_parent_instr_id(slotInfPtr)
        return 0

    def get_slot_fpga_version(self, slot_id):
        '''Gets the FPGA version of the module in the specified slot.
        :param slot_id: the slot identifier.
        :returns: the FPGA version number.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_fpga_version(slotInfPtr)
        return 0

    def get_slot_fpga_svn_rev(self, slot_id):
        '''Gets the SVN rev. of the FPGA of the module in the specified slot.
        :param slot_id: the slot identifier.
        :returns: the SVN revision of the FPGA.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_fpga_svn(slotInfPtr)
        return 0

    def get_slot_fpga_build_date(self, slot_id):
        '''Gets the build-date of the FPGA of the module in the specified slot.
        :param slot_id: the slot identifier.
        :returns: the build-date (string).
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            max_resp_len = int(256)
            resp_buf = ct.create_string_buffer(max_resp_len)

            max_resp_len = np.uint32(max_resp_len)
            ret_code = self._tep_get_slot_fpga_date(
                slotInfPtr, resp_buf, max_resp_len)
            if 0 < ret_code < 256:
                return str(resp_buf.value, 'utf-8').strip()
        return str('')

    def get_slot_idn_str(self, slot_id):
        '''Gets the `*IDN` string of the module in the specified slot.
        :param slot_id: the slot identifier.
        :returns: the `*IDN` string
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            max_resp_len = int(256)
            resp_buf = ct.create_string_buffer(max_resp_len)

            max_resp_len = np.uint32(max_resp_len)
            ret_code = self._tep_get_slot_idn_str(
                slotInfPtr, resp_buf, max_resp_len)
            if 0 < ret_code < 256:
                return str(resp_buf.value, 'utf-8').strip()
        return str('')

    def get_slot_fw_options(self, slot_id):
        '''Gets the FW Options in the flash of the module in of the specified slot.
        :param slot_id: the slot identifier.
        :return: the firmware-options (a combination of 32 bit-flags).
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_fw_options(slotInfPtr)
        return 0

    def get_slot_hw_options(self, slot_id):
        '''Gets the HW Options in the flash of the module in of the specified slot.
        :param slot_id: the slot identifier.
        :return: the hardware-options (a combination of 32 bit-flags).
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_hw_options(slotInfPtr)
        return 0

    def get_slot_installed_memory(self, slot_id):
        '''Gets the installed-memory size of the module in of the specified slot.
        :param slot_id: the slot identifier.
        :return: the size of the installed memory in GB per DDR.
        '''
        slotInfPtr = self._tep_get_slot_info(np.uint32(slot_id))
        if slotInfPtr:
            return self._tep_get_slot_installed_memory(slotInfPtr)
        return 0

    def open_instrument(self, slot_id, reset_hot_flag=True):
        '''Opens instrument that operates a single slot.
        :param slot_id: the slot identifier.
        :param reset_hot_flag: should reset the system-hot flag?
        :returns: a `TEProteusInst` instance (`None` upon failure).
        '''
        reset_hot_flag = 1 if reset_hot_flag else 0
        slot_id = np.uint32(slot_id)
        instptr = self._tep_open_instrument(slot_id, reset_hot_flag)
        if instptr:
            slot_list = (slot_id,)
            inst = TEProteusInst(self, instptr, slot_list)
            if inst is not None:
                # pylint: disable=protected-access
                instid = inst._instr_id
                self._inst_dict[instid] = inst
                return inst
        print('unable to connect to instrument')
        return None

    def open_multi_slots_instrument(self, slot_ids, reset_hot_flag=True):
        '''Opens instrument that operates a single slot.
        :param slot_ids: array of slot identifiers (uint32 values).
        :param reset_hot_flag: should reset the system-hot flag?
        :returns: pointer to the instrument's interface (zero upon failure).
        '''
        reset_hot_flag = 1 if reset_hot_flag else 0

        slotids = np.array(slot_ids).astype(np.uint32)
        numslots = np.uint32(len(slotids))
        instptr = self._tep_open_multi_slots_instrument(
            slotids,
            numslots,
            reset_hot_flag)
        if instptr:
            slot_list = tuple(slotids)
            inst = TEProteusInst(self, instptr, slot_list)
            if inst is not None:
                # pylint: disable=protected-access
                instid = inst._instr_id
                self._inst_dict[instid] = inst
                return inst
        return None

    def close_all_instruments(self):
        '''Closes all instruments.
        :returns: zero if succeeded; otherwise, error code.
        '''
        inst_dict = self._inst_dict
        self._inst_dict = dict()
        for _, inst in inst_dict.items():
            if inst is not None:
                inst.close_instrument()
                del inst

        gc.collect()

        return self._tep_close_all_instruments()


class TEProteusInst(object):
    '''Proteus Instrument.

    This class manages one or more hardware-modules as single instrument.
    '''

    def __init__(self, te_proteus_admin, inst_ptr, slot_list):
        '''
        Constructor.

        User should not call this method directly, but use the methods

          - :meth:`TEProteusAdmin.open_instrument`
          - :meth:`TEProteusAdmin.open_multi_slots_instrument`

        In order to create instances of :class:`TEProteusInst`.

        :param te_proteus_admin: the parent :class:`TEProteusAdmin`.
        :param inst_ptr: pointer to the relevant native C instrument object.
        :param slot_list: list of slotIds of the relevant PXI slots.
        '''
        self._slots = slot_list
        self._admin = te_proteus_admin
        self._instptr = inst_ptr
        self._commptr = self._admin._tep_open_comm_intf(inst_ptr)
        self._streamptr = None
        self._instr_id = self._admin._tep_get_instrument_id(inst_ptr)
        self._default_paranoia_level = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        self.close_instrument()

    @property
    def default_paranoia_level(self):
        '''The default paranoia level (0, 1, or 2).

        It is used as default value for the `paranoia_level`
        argument of the method :meth:`TEProteusInst.send_scpi_cmd`.

        The supported levels are 0, 1 or 2,  where
         - 0: send bare SCPI command
         - 1: append `*OPC?` and send as query
         - 2: append `:SYST:ERR?` and print warning if the response is not 0.

        :getter: Gets the default paranoia level (0, 1, or 2).
        :setter: Sets the default paranoia level (0, 1, or 2).
        :type: int.
        '''
        return self._default_paranoia_level

    @default_paranoia_level.setter
    def default_paranoia_level(self, value):

        value = max(0, min(int(value), 2))
        self._default_paranoia_level = value

    def close_instrument(self):
        '''Closes this instrument.'''
        if self._admin is not None:
            # pylint: disable=protected-access
            self._admin._tep_close_comm_intf(self._instptr, self._commptr)
            self._admin._inst_dict.pop(self._instr_id, None)
            self._admin._tep_close_instrument(self._instptr)
            self._commptr = None
            self._instptr = None
            self._streamptr = None
            self._instptr = None
            self._slots = ()
            self._instr_id = 0
            gc.collect()

    def send_scpi_query(self, scpi_str, max_resp_len=256):
        '''Sends SCPI query to instrument.
        :param scpi_str: the SCPI string (a null-terminated string).
        :param max_resp_len: the maximal length of the response string.
        :returns: response-string
        '''
        scpi_str = str(scpi_str).encode()
        str_ptr = ct.c_char_p(scpi_str)
        max_resp_len = int(max_resp_len)
        resp_buf = ct.create_string_buffer(max_resp_len)
        max_resp_len = np.uint32(max_resp_len)

        # pylint: disable=protected-access
        ret_code = self._admin._tep_send_scpi(
            self._commptr, str_ptr, resp_buf, max_resp_len)

        if 0 != ret_code:
            wmsg = '\"{0}\" failed with error {1}'.format(scpi_str, ret_code)
            warnings.warn(wmsg)

        resp_str = str(resp_buf.value, 'utf-8').strip()
        return resp_str

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

        scpi_str = str(scpi_str).strip()
        if 1 == paranoia_level:
            if scpi_str:
                cmd = str(scpi_str + '; *OPC?').encode()
            else:
                cmd = str('*OPC?').encode()
        elif paranoia_level > 1:
            if scpi_str:
                cmd = str(scpi_str + '; :SYST:ERR?').encode()
            else:
                cmd = str(':SYST:ERR?').encode()
        else:
            cmd = scpi_str.encode()

        str_ptr = ct.c_char_p(cmd)
        max_resp_len = int(64)
        resp_buf = ct.create_string_buffer(max_resp_len)
        max_resp_len = np.uint32(max_resp_len)

        # pylint: disable=protected-access
        ret_code = self._admin._tep_send_scpi(
            self._commptr, str_ptr, resp_buf, max_resp_len)

        if paranoia_level > 1:
            resp_str = str(resp_buf.value, 'utf-8').strip()
            if not resp_str.startswith('0'):
                wrnmsg = 'CMD: "{0}", SYST:ERR: {1}'.format(scpi_str, resp_str)
                warnings.warn(wrnmsg)
                cmd = str('*CLS').encode()
                str_ptr = ct.c_char_p(cmd)
                self._admin._tep_send_scpi(
                    self._commptr, str_ptr, resp_buf, max_resp_len)

        return ret_code

    def write_binary_data(self, scpi_pref, bin_dat):
        '''Sends block of binary-data to instrument.
        :param scpi_pref: a SCPI string that defines the data (can be None).
        :param bin_dat: a `numpy` array with the binary data.
        :returns: zero if succeeded; otherwise, error code.
        '''
        scpi_pref = str(scpi_pref).encode()
        str_ptr = ct.c_char_p(scpi_pref)

        size_in_bytes = bin_dat.nbytes
        p_dat = bin_dat.ctypes.data_as(ct.POINTER(ct.c_uint8))

        # pylint: disable=protected-access
        return self._admin._tep_write_binary_data(
            self._commptr, str_ptr, p_dat, np.uint64(size_in_bytes))

    def read_binary_data(self, scpi_pref, out_array, num_bytes):
        '''Reads block of binary-data from instrument.
        :param scpi_pref: a SCPI string that defines the data (can be None).
        :param out_array: a `numpy` array for the data.
        :param num_bytes: the data size in bytes.
        :returns: error-code (zero for success).
        '''
        scpi_pref = str(scpi_pref).encode()
        str_ptr = ct.c_char_p(scpi_pref)

        p_buff = out_array.ctypes.data_as(ct.POINTER(ct.c_uint8))

        # pylint: disable=protected-access
        ret_code = self._admin._tep_read_binary_data(
            self._commptr, str_ptr, p_buff, np.uint64(num_bytes))

        return ret_code

    def acquire_stream_intf(self, chan_num):
        '''Acquire the stream-writing interface of the specified channel.
        :param chan_num: the channel-number.
        :returns: None.
        '''
        chan_num = int32(chan_num)
        # pylint: disable=protected-access
        self._streamptr = \
            self._admin._tep_get_write_stream_intf(self._instptr, chan_num)

    def get_stream_packet_size(self):
        '''Gets the size in bytes of a single packet of streaming data.
        :returns: the size in bytes of a single packet of streaming data.
        '''
        # pylint: disable=protected-access
        return self._admin._tep_get_stream_packet_size()

    def is_write_stream_active(self):
        '''Checks if the given stream-writing interface is active.
        :returns: True if the interface is active; otherwise, False.
        '''
        if self._streamptr is not None:
            # pylint: disable=protected-access
            if self._admin._tep_is_write_stream_active(self._streamptr):
                return True
        return False

    def get_stream_empty_buff(self):
        '''Gets empty-buffer from the given stream-writing interface.

        The caller should fill the buffer with packet of streaming-data,
        and then return the ownership of the buffer by calling either
        `put_stream_full_buff` or `tep_put_stream_empty_buff`.

        :returns: pointer to empty-buffer.
        '''
        # pylint: disable=protected-access
        return self._admin._tep_get_stream_empty_buff(self._streamptr)

    def put_stream_full_buff(self, full_buff, usec_wait):
        '''Puts back a full buffer.

        The buffer should be a buffer that was obtained from the given
        stream-writing interface (and filled with data by the caller).
        This method blocks the calling thread (up to the given timeout)
        till the previous packet is transmitted.
        If it doesn't succeed (because of failure or timeout) then caller
        still own the buffer, and must return ownership by calling either
        `put_stream_empty_buff` or `put_stream_full_buff`.

        :param full_buff: buffer that was obtained from the interface.
        :param usec_wait: timeout in microseconds (-1: infinite timeout).
        :returns: 0: success; 1: timeout expired; -1: error.
        '''
        # pylint: disable=protected-access
        return self._admin.\
            _tep_put_stream_full_buff(self._streamptr, full_buff, usec_wait)

    def put_stream_empty_buff(self, empty_buff):
        '''Puts back empty buffer.

        The buffer should be a buffer that was obtained from the given
        stream-writing interface. This method does not blocks the calling
        thread but the buffer is not going to be transmitted.

        :param empty_buff: buffer that was obtained from the interface.
        :returns: 0: success; -1: error.
        '''
        # pylint: disable=protected-access
        return self._admin.\
            _tep_put_stream_empty_buff(self._streamptr, empty_buff)

    def push_stream_packet(self, bin_dat, bytes_offs, usec_wait):
        '''Pushes a packet of streaming-data from block of uint8 wave-samples.

        It is equivalent to get empty-buffer, fill it with data from the
        specified offset in the given wave-data, and then put back the full
        buffer and if it fails, put back empty buffer.

        :param bin_dat: `numpy` array with data.
        :param bytes_offs: offset in bytes inside the `bin_dat` array.
        :param usec_wait: timeout in microseconds (-1: infinite timeout).
        :returns: 0: success; 1: timeout expired; -1: error.
        '''

        p_dat = bin_dat.ctypes.data_as(ct.POINTER(ct.c_ubyte))
        offs = int64(bytes_offs)
        tmo = int32(usec_wait)

        # pylint: disable=protected-access
        return self._admin.\
            _tep_push_stream_packet(self._streamptr, p_dat, offs, tmo)
