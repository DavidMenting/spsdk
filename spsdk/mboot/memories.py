#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2016-2018 Martin Olejar
# Copyright 2019-2021 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Various types of memory identifiers used in the MBoot module."""

from typing import List, Optional

from spsdk.image.misc import size_fmt
from spsdk.utils.easy_enum import Enum

########################################################################################################################
# McuBoot External Memory ID
########################################################################################################################


class ExtMemId(Enum):
    """McuBoot External Memory Property Tags."""

    QUAD_SPI0 = (1, "QSPI", "Quad SPI Memory 0")
    IFR0 = (4, "IFR0", "Nonvolatile information register 0 (only used by SB loader)")
    SEMC_NOR = (8, "SEMC-NOR", "SEMC NOR Memory")
    FLEX_SPI_NOR = (9, "FLEX-SPI-NOR", "Flex SPI NOR Memory")
    SPIFI_NOR = (10, "SPIFI-NOR", "SPIFI NOR Memory")
    FLASH_EXEC_ONLY = (16, "FLASH-EXEC", "Execute-Only region on internal Flash")
    SEMC_NAND = (256, "SEMC-NAND", "SEMC NAND Memory")
    SPI_NAND = (257, "SPI-NAND", "SPI NAND Memory")
    SPI_NOR_EEPROM = (272, "SPI-MEM", "SPI NOR/EEPROM Memory")
    I2C_NOR_EEPROM = (273, "I2C-MEM", "I2C NOR/EEPROM Memory")
    SD_CARD = (288, "SD", "eSD/SD/SDHC/SDXC Memory Card")
    MMC_CARD = (289, "MMC", "MMC/eMMC Memory Card")


class MemId(ExtMemId):
    """McuBoot Internal/External Memory Property Tags."""

    INTERNAL_MEMORY = (0, "RAM/FLASH", "Internal RAM/FLASH (Used for the PRINCE configuration)")


########################################################################################################################
# McuBoot External Memory Property Tags
########################################################################################################################


class ExtMemPropTags(Enum):
    """McuBoot External Memory Property Tags."""

    INIT_STATUS = 0x00000000
    START_ADDRESS = 0x00000001
    SIZE_IN_KBYTES = 0x00000002
    PAGE_SIZE = 0x00000004
    SECTOR_SIZE = 0x00000008
    BLOCK_SIZE = 0x00000010


class MemoryRegion:
    """Base class for memory regions."""

    def __init__(self, start: int, end: int) -> None:
        """Initialize the memory region object.

        :param start: start address of region
        :param end: end address of region

        """
        self.start = start
        self.end = end
        self.size = end - start + 1

    def __str__(self) -> str:
        return f"0x{self.start:08X} - 0x{self.end:08X}; Total Size: {size_fmt(self.size)}"


class RamRegion(MemoryRegion):
    """RAM memory regions."""

    def __init__(self, index: int, start: int, size: int) -> None:
        """Initialize the RAM memory region object.

        :param index: number of region
        :param start: start address of region
        :param size: size of region

        """
        super().__init__(start, start + size - 1)
        self.index = index

    def __str__(self) -> str:
        return f"Region {self.index}: {super().__str__()}"


class FlashRegion(MemoryRegion):
    """Flash memory regions."""

    def __init__(self, index: int, start: int, size: int, sector_size: int) -> None:
        """Initialize the Flash memory region object.

        :param index: number of region
        :param start: start address of region
        :param size: size of region
        :param sector_size: size of sector

        """
        super().__init__(start, start + size - 1)
        self.index = index
        self.sector_size = sector_size

    def __str__(self) -> str:
        msg = f"Region {self.index}: {super().__str__()} Sector size: {size_fmt(self.sector_size)}"
        return msg


class ExtMemRegion(MemoryRegion):
    """External memory regions."""

    def __init__(self, mem_id: int, raw_values: Optional[List[int]] = None) -> None:
        """Initialize the external memory region object.

        :param mem_id: ID of the external memory
        :param raw_values: List of integers representing the property

        """
        self.mem_id = mem_id
        if not raw_values:
            self.value = None
            return
        self.start_address = raw_values[1] if raw_values[0] & ExtMemPropTags.START_ADDRESS else None
        self.total_size = (
            raw_values[2] * 1024 if raw_values[0] & ExtMemPropTags.SIZE_IN_KBYTES else None
        )
        self.page_size = raw_values[3] if raw_values[0] & ExtMemPropTags.PAGE_SIZE else None
        self.sector_size = raw_values[4] if raw_values[0] & ExtMemPropTags.SECTOR_SIZE else None
        self.block_size = raw_values[5] if raw_values[0] & ExtMemPropTags.BLOCK_SIZE else None
        self.value = raw_values[0]

    @property
    def name(self) -> str:
        """Get the name of external memory for given memory ID."""
        return ExtMemId.name(self.mem_id)

    def __str__(self) -> str:
        if not self.value:
            return f"Not Configured"
        info = f"Start Address = 0x{self.start_address:08X}  "
        if self.total_size:
            info += f"Total Size = {size_fmt(self.total_size)}  "
        info += f"Page Size = {self.page_size}  "
        info += f"Sector Size = {self.sector_size}  "
        if self.block_size:
            info += f"Block Size = {self.block_size} "
        return info
