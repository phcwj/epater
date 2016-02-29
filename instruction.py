import struct
import math
from collections import defaultdict
from functools import lru_cache
from enum import Enum

from settings import getSetting

class InstrType(Enum):
    undefined = -1
    dataop = 0
    memop = 1
    multiplememop = 2
    branch = 3
    multiply = 4
    swap = 5
    softinterrupt = 6
    declareOp = 100

    @staticmethod
    def getEncodeFunction(inType):
        return {InstrType.dataop: DataInstructionToBytecode,
                InstrType.memop: MemInstructionToBytecode,
                InstrType.multiplememop: MultipleMemInstructionToBytecode,
                InstrType.branch: BranchInstructionToBytecode,
                InstrType.multiply: MultiplyInstructionToBytecode,
                InstrType.swap: SwapInstructionToBytecode,
                InstrType.softinterrupt: SoftinterruptInstructionToBytecode,
                InstrType.declareOp: DeclareInstructionToBytecode}[inType]

exportInstrInfo = {# DATA OPERATIONS
                   'AND': InstrType.dataop,
                   'EOR': InstrType.dataop,
                   'SUB': InstrType.dataop,
                   'RSB': InstrType.dataop,
                   'ADD': InstrType.dataop,
                   'ADC': InstrType.dataop,
                   'SBC': InstrType.dataop,
                   'RSC': InstrType.dataop,
                   'TST': InstrType.dataop,
                   'TEQ': InstrType.dataop,
                   'CMP': InstrType.dataop,
                   'CMN': InstrType.dataop,
                   'ORR': InstrType.dataop,
                   'MOV': InstrType.dataop,
                   'BIC': InstrType.dataop,
                   'MVN': InstrType.dataop,
                    # MEMORY OPERATIONS
                   'LDR': InstrType.memop,
                   'STR': InstrType.memop,
                    # MULTIPLE MEMORY OPERATIONS
                   'LDM': InstrType.multiplememop,
                   'STM': InstrType.multiplememop,
                   'PUSH': InstrType.multiplememop,
                   'POP': InstrType.multiplememop,
                    # BRANCH OPERATIONS
                   'B'  : InstrType.branch,
                   'BX' : InstrType.branch,
                   'BL' : InstrType.branch,
                   'BLX': InstrType.branch,
                    # MULTIPLY OPERATIONS
                   'MUL': InstrType.multiply,
                   'MLA': InstrType.multiply,
                    # SWAP OPERATIONS
                   'SWP': InstrType.swap,
                    # SOFTWARE INTERRUPT OPERATIONS
                   'SWI': InstrType.softinterrupt,
                   }

globalInstrInfo = dict(exportInstrInfo)
globalInstrInfo.update({# DECLARATION STATEMENTS
                   'DC' : InstrType.declareOp,
                   'DS' : InstrType.declareOp,
                    })

conditionMapping = {'EQ': 0,
                    'NE': 1,
                    'CS': 2,
                    'CC': 3,
                    'MI': 4,
                    'PL': 5,
                    'VS': 6,
                    'VC': 7,
                    'HI': 8,
                    'LS': 9,
                    'GE': 10,
                    'LT': 11,
                    'GT': 12,
                    'LE': 13,
                    'AL': 14}

conditionMappingR = {v: k for k,v in conditionMapping.items()}

shiftMapping = {'LSL': 0,
                'LSR': 1,
                'ASR': 2,
                'ROR': 3}
# TODO Add RRX rotate mode (special case of ROR)

shiftMappingR = {v: k for k,v in shiftMapping.items()}

updateModeLDMMapping = {'ED': 3, 'IB': 3,
                        'FD': 1, 'IA': 1,
                        'EA': 2, 'DB': 2,
                        'FA': 0, 'DA': 0}
updateModeSTMMapping = {'FA': 3, 'IB': 3,
                        'EA': 1, 'IA': 1,
                        'FD': 2, 'DB': 2,
                        'ED': 0, 'DA': 0}

dataOpcodeMapping = {'AND': 0,
                     'EOR': 1,
                     'SUB': 2,
                     'RSB': 3,
                     'ADD': 4,
                     'ADC': 5,
                     'SBC': 6,
                     'RSC': 7,
                     'TST': 8,
                     'TEQ': 9,
                     'CMP': 10,
                     'CMN': 11,
                     'ORR': 12,
                     'MOV': 13,
                     'BIC': 14,
                     'MVN': 15}

dataOpcodeMappingR = {v: k for k,v in dataOpcodeMapping.items()}

def immediateToBytecode(imm):
    """
    The immediate operand rotate field is a 4 bit unsigned integer which specifies a shift
    operation on the 8 bit immediate value. This value is zero extended to 32 bits, and then
    subject to a rotate right by twice the value in the rotate field. (ARM datasheet, 4.5.3)
    :param imm:
    :return:
    """
    if imm == 0:
        return 0, 0, False
    if imm < 0:
        val, rot, _ = immediateToBytecode(~imm)
        return val, rot, True

    mostSignificantOne = int(math.log2(imm))
    leastSignificantOne = int(math.log2((1 + (imm ^ (imm-1))) >> 1))
    if mostSignificantOne < 8:
        # Are we already able to fit the value in the immediate field?
        return imm & 0xFF, 0, False
    elif mostSignificantOne - leastSignificantOne < 8:
        # Does it fit in 8 bits?
        # If so, we want to put the MSB to the utmost left possible in 8 bits
        # Remember that we can only do an EVEN number of right rotations
        if mostSignificantOne % 2 == 0:
            val = imm >> (mostSignificantOne - 6)
            rot = (32 - (mostSignificantOne - 6)) // 2
        else:
            val = imm >> (mostSignificantOne - 7)
            rot = (32 - (mostSignificantOne - 7)) // 2
        return val & 0xFF, rot, False
    else:
        # It is impossible to generate the requested value
        return None

# TEST CODE
def _immShiftTestCases():
    # Asserted with IAR
    tcases = [(0, 0x000),
              (1, 0x001),
              (255, 0x0ff),
              (256, 0xf40),
              (260, 0xf41),
              (1024, 0xe40),
              (4096, 0xd40),
              (8192, 0xd80),
              (65536, 0xb40),
              (0x80000000, 0x480)]
    negtcases = [(-1, 0x000),
                 (-2, 0x001),
                 (-255, 0x0fe)]

    for case in tcases:
        print("Testing case {}... ".format(case[0]), end="")
        val, rot, inv = immediateToBytecode(case[0])
        assert 0 <= val <= 255, "Echec cas {} (pas entre 0 et 255) : {}".format(case[0], val)
        cmpval = val & 0xFF | ((rot & 0xF) << 8)
        assert case[1] == cmpval, "Echec cas {} (invalide) : {} vs {}".format(case[0], hex(cmpval), hex(case[1]))
        print("OK")
    for case in negtcases:
        print("Testing case {}... ".format(case[0]), end="")
        val, rot, inv = immediateToBytecode(case[0])
        assert 0 <= val <= 255, "Echec cas {} (pas entre 0 et 255) : {}".format(case[0], val)
        cmpval = val & 0xFF | ((rot & 0xF) << 8)
        assert case[1] == cmpval, "Echec cas {} (invalide) : {} vs {}".format(case[0], hex(cmpval), hex(case[1]))
        print("OK")
# END TEST CODE


def checkTokensCount(tokensDict):
    # Not a comprehensive check
    assert tokensDict['COND'] <= 1
    assert tokensDict['SETFLAGS'] <= 1
    assert tokensDict['SHIFTREG'] + tokensDict['SHIFTIMM'] <= 1
    assert tokensDict['CONSTANT'] <= 1
    assert tokensDict['BYTEONLY'] <= 1
    assert tokensDict['MEMACCESSPRE'] + tokensDict['MEMACCESSPOST'] <= 1
    assert tokensDict['WRITEBACK'] <= 1
    assert tokensDict['UPDATEMODE'] <= 1


def DataInstructionToBytecode(asmtokens):
    mnemonic = asmtokens[0].value
    b = dataOpcodeMapping[mnemonic] << 21

    countReg = 0
    dictSeen = defaultdict(int)
    for tok in asmtokens[1:]:
        # "TEQ, TST, CMP and CMN do not write the result of their operation but do set
        # flags in the CPSR. An assembler should always set the S flag for these instructions
        # even if this is not specified in the mnemonic" (4-15, ARM7TDMI-S Data Sheet)
        if tok.type == 'SETFLAGS' or mnemonic in ('TEQ', 'TST', 'CMP', 'CMN'):
            b |= 1 << 20
        elif tok.type == 'COND':
            b |= conditionMapping[tok.value] << 28
        elif tok.type == 'REGISTER':
            if dictSeen['REGISTER'] == 0:
                b |= tok.value << 12
            elif dictSeen['REGISTER'] == 2 or mnemonic in ('MOV', 'MVN'):
                b |= tok.value
            else:
                b |= tok.value << 16
        elif tok.type == 'CONSTANT':
            b |= 1 << 25
            immval, immrot, inverse = immediateToBytecode(tok.value)
            if inverse:
                # We can fit the constant, but we have to swap MOV<->MVN in order to do so
                if mnemonic == 'MOV':
                    b |= dataOpcodeMapping['MVN'] << 21     # MVN is 1111 opcode
                elif mnemonic == 'MVN':
                    b ^= 1 << 22
            b |= immval
            b |= immrot << 8
        elif tok.type == 'SHIFTREG':
            b |= 1 << 4
            b |= shiftMapping[tok.value[0]] << 5
            b |= tok.value[1] << 8
        elif tok.type == 'SHIFTIMM':
            b |= shiftMapping[tok.value[0]] << 5
            b |= tok.value[1] << 7
        dictSeen[tok.type] += 1

    if dictSeen['COND'] == 0:
        b |= conditionMapping['AL'] << 28

    checkTokensCount(dictSeen)
    return struct.pack("<I", b)


def MemInstructionToBytecode(asmtokens):
    mnemonic = asmtokens[0].value

    b = 1 << 26
    b |= (1 << 20 if mnemonic == "LDR" else 0)
    dictSeen = defaultdict(int)
    for tok in asmtokens[1:]:
        if tok.type == 'COND':
            b |= conditionMapping[tok.value] << 28
        elif tok.type == 'BYTEONLY':
            b |= 1 << 22
        elif tok.type == 'REGISTER':
            b |= tok.value << 12
        elif tok.type == 'MEMACCESSPRE':
            b |= 1 << 24
            b |= tok.value.base << 16
            if tok.value.direction > 0:
                b |= 1 << 23
            if tok.value.offsettype == "imm":
                b |= tok.value.offset
            elif tok.value.offsettype == "reg":
                b |= 1 << 25
                b |= tok.value.offset
                b |= shiftMapping[tok.value.shift.type] << 5
                b |= tok.value.shift.count << 7
        elif tok.type == 'MEMACCESSPOST':
            b |= tok.value.base << 16
            if tok.value.direction > 0:
                b |= 1 << 23
            if tok.value.offsettype == "imm":
                b |= tok.value.offset
            elif tok.value.offsettype == "reg":
                b |= 1 << 25
                b |= tok.value.offset
        elif tok.type == 'SHIFTIMM':
            # Should be post increment
            b |= shiftMapping[tok.value.type] << 5
            b |= tok.value.count << 7
        elif tok.type == 'WRITEBACK':
            b |= 1 << 21
        dictSeen[tok.type] += 1

    if dictSeen['COND'] == 0:
        b |= conditionMapping['AL'] << 28

    checkTokensCount(dictSeen)
    return struct.pack("<I", b)


def MultipleMemInstructionToBytecode(asmtokens):
    mnemonic = asmtokens[0].value
    b = 0b100 << 25

    b |= (1 << 20 if mnemonic == "LDM" else 0)
    dictSeen = defaultdict(int)
    for tok in asmtokens[1:]:
        if tok.type == 'COND':
            b |= conditionMapping[tok.value] << 28
        elif tok.type == 'WRITEBACK':
            b |= 1 << 21
        elif tok.type == 'REGISTER':
            if dictSeen['REGISTER'] == 0:
                b |= tok.value << 16
            elif dictSeen['REGISTER'] == 1:
                assert dictSeen['LISTREGS'] == 0
                b |= 1 << tok.value     # Not the real encoding when only one reg is present. Is this an actual issue?
        elif tok.type == 'LISTREGS':
            for i in range(tok.value):
                b |= tok.value[i] << i
        elif tok.type == 'UPDATEMODE':
            if mnemonic in ('LDM', 'POP'):
                b |= updateModeLDMMapping[tok.value] << 23
            elif mnemonic in ('STM', 'PUSH'):
                b |= updateModeSTMMapping[tok.value] << 23
        dictSeen[tok.type] += 1

    if dictSeen['COND'] == 0:
        b |= conditionMapping['AL'] << 28

    checkTokensCount(dictSeen)
    return struct.pack("<I", b)

def BranchInstructionToBytecode(asmtokens):
    mnemonic = asmtokens[0].value

    if mnemonic == 'BX':
        b = 0b000100101111111111110001 << 4
    else:
        b = 5 << 25
        if mnemonic == 'BL':
            b |= 1 << 24

    dictSeen = defaultdict(int)
    for tok in asmtokens[1:]:
        if tok.type == 'COND':
            b |= conditionMapping[tok.value] << 28
        elif tok.type == 'REGISTER':
            # Only for BX
            b |= tok.value
        elif tok.type == 'MEMACCESSPRE':
            # When we find a label in the previous parsing stage,
            # we replace it with a MEMACCESSPRE token, even if this
            # token cannot appear in actual code
            b |= tok.value.offset if tok.value.direction >= 0 else (~tok.value.offset + 1) & 0xFFFFFF
        elif tok.type == 'CONSTANT':
            b |= tok.value
        dictSeen[tok.type] += 1

    if dictSeen['COND'] == 0:
        b += conditionMapping['AL'] << 28

    checkTokensCount(dictSeen)
    return struct.pack("<I", b)


def MultiplyInstructionToBytecode(asmtokens):
    mnemonic = asmtokens[0].value

    b = 9 << 4
    if mnemonic == 'MLA':
        b |= 1 << 21

    countReg = 0
    dictSeen = defaultdict(int)
    for tok in asmtokens[1:]:
        if tok.type == 'SETFLAGS':
            b |= 1 << 20
        elif tok.type == 'COND':
            b |= conditionMapping[tok.value] << 28
        elif tok.type == 'REGISTER':
            if dictSeen['REGISTER'] == 0:
                b |= tok.value << 16
            elif dictSeen['REGISTER'] == 1:
                b |= tok.value
            elif dictSeen['REGISTER'] == 2:
                b |= tok.value << 8
            else:
                b |= tok.value << 12
        dictSeen[tok.type] += 1

    if dictSeen['COND'] == 0:
        b |= conditionMapping['AL'] << 28

    checkTokensCount(dictSeen)
    return struct.pack("<I", b)


def SwapInstructionToBytecode(asmtokens):
    # Todo
    raise NotImplementedError()


def SoftinterruptInstructionToBytecode(asmtokens):
    # TODO
    raise NotImplementedError()


def DeclareInstructionToBytecode(asmtokens):
    assert asmtokens[0].type == 'DECLARATION', str((asmtokens[0].type, asmtokens[0].value))
    info = asmtokens[0].value

    formatletter = "B" if info.nbits == 8 else "H" if info.nbits == 16 else "I" # 32
    return struct.pack("<"+formatletter*info.dim, *([0]*info.dim if len(info.vals) == 0 else info.vals))



def InstructionToBytecode(asmtokens):
    assert asmtokens[0].type in ('INSTR', 'DECLARATION')
    #print(asmtokens)
    tp = globalInstrInfo[asmtokens[0].value if asmtokens[0].type == 'INSTR' else asmtokens[0].value.type]
    return InstrType.getEncodeFunction(tp)(asmtokens)


def checkMask(data, posOnes, posZeros):
    v = 0
    for p1 in posOnes:
        v |= 1 << p1
    if data & v != v:
        return False
    v = 0
    for p0 in posZeros:
        v |= 1 << p0
    if data & v != 0:
        return False
    return True


@lru_cache(maxsize=256)
def BytecodeToInstrInfos(bc):
    """
    :param bc: The current instruction, in a bytes object
    :return: A tuple containing four elements. The first is a *InstrType* value
    that corresponds to the type of the current instruction. The second is a
    tuple containing the registers indices that see their value modified by
    this instruction. The third is a decoding of the condition code.
    Finally, the fourth element is not globally defined, and is used by
    the decoder to put informations relevant to the current instruction. For
    instance, when decoding a data processing instruction, this fourth element
    will, amongst other things, contain the opcode of the request operation.
    """
    assert len(bc) == 4 # 32 bits
    instrInt = struct.unpack("<I", bc)[0]      # It's easier to work with integer objects when it comes to bit manipulation

    affectedRegs = ()
    condition = conditionMappingR[instrInt >> 28]
    miscInfo = None

    if checkMask(instrInt, (24, 25, 26, 27), ()): # Software interrupt
        category = InstrType.softinterrupt
        miscInfo = instrInt & (0xFF << 24)

    elif checkMask(instrInt, (4, 25, 26), (27,)):    # Undefined instruction
        category = InstrType.undefined

    elif checkMask(instrInt, (27, 25), (26,)):       # Branch
        category = InstrType.branch
        setlr = bool(instrInt & (1 << 24))
        if setlr:
            affectedRegs = (14,)
        offset = instrInt & 0xFFFFFF
        if offset & 0x800000:   # Negative offset
            offset = -2**24 + offset
        miscInfo = {'mode': 'imm',
                    'L': setlr,
                    'offset': offset}

    elif checkMask(instrInt, (27,), (26, 25)):       # Block data transfer
        category = InstrType.multiplememop
        pre = bool(instrInt & (1 << 24))
        sign = 1 if instrInt & (1 << 22) else -1
        writeback = bool(instrInt & (1 << 23))
        mode = "LDR" if instrInt & (1 << 20) else "STR"

        basereg = (instrInt >> 16) & 0xF
        reglist = instrInt & 0xFFFF
        affectedRegs = []
        for i in range(16):
            if reglist & (1 << i):
                affectedRegs.append(i)
        affectedRegs = tuple(affectedRegs)

        miscInfo = {'base': basereg,
                    'reglist': reglist,
                    'pre': pre,
                    'sign': sign,
                    'writeback': writeback,
                    'mode': mode}

    elif checkMask(instrInt, (26, 25), (4, 27)) or checkMask(instrInt, (26,), (25, 27)):    # Single data transfer
        category = InstrType.memop

        imm = not bool(instrInt & (1 << 25))   # For LDR/STR, imm is 0 if offset IS an immediate value (4-26 datasheet)
        pre = bool(instrInt & (1 << 24))
        sign = 1 if instrInt & (1 << 23) else -1
        byte = bool(instrInt & (1 << 22))
        writeback = bool(instrInt & (1 << 21))
        mode = "LDR" if instrInt & (1 << 20) else "STR"

        basereg = (instrInt >> 16) & 0xF
        destreg = (instrInt >> 12) & 0xF
        if imm:
            offset = instrInt & 0xFFF
        else:
            rm = instrInt & 0xF
            if instrInt & (1 << 4):
                shift = (shiftMappingR[(instrInt >> 5) & 0x3], "reg", (instrInt >> 8) & 0xF)
            else:
                shift = (shiftMappingR[(instrInt >> 5) & 0x3] , "imm", (instrInt >> 7) & 0x1F)
            offset = (rm, shift)

        affectedRegs = (destreg,) if not writeback else (destreg, basereg)
        miscInfo = {'base': basereg,
                    'rd': destreg,
                    'offset': offset,
                    'imm': imm,
                    'pre': pre,
                    'sign': sign,
                    'byte': byte,
                    'writeback': writeback,
                    'mode': mode}

    elif checkMask(instrInt, (24, 21, 4) + tuple(range(8, 20)), (27, 26, 25, 23, 22, 20, 7, 6, 5)): # BX
        category = InstrType.branch
        miscInfo = {'mode': 'reg',
                    'L': False,
                    'offset': instrInt & 0xF}

    elif checkMask(instrInt, (7, 4), tuple(range(22, 28)) + (5, 6)):    # MUL or MLA
        category = InstrType.multiply
        rd = (instrInt >> 16) & 0xF
        rn = (instrInt >> 12) & 0xF
        rs = (instrInt >> 8) & 0xF
        rm = instrInt & 0xF
        affectedRegs = (rd,)

        flags = bool(instrInt & (1 << 20))
        accumulate = bool(instrInt & (1 << 21))

        miscInfo = {'accumulate':accumulate,
                    'setflags': flags,
                    'rd': rd,
                    'operandsmul': (rm, rs),
                    'operandadd': rd}

    elif checkMask(instrInt, (7, 4, 24), (27, 26, 25, 23, 21, 20, 11, 10, 9, 8, 6, 5)): # Swap
        category = InstrType.swap
        # TODO

    elif checkMask(instrInt, (), (27, 26)):     # Data processing
        category = InstrType.dataop
        opcodeNum = (instrInt >> 21) & 0xF
        opcode = dataOpcodeMappingR[opcodeNum]

        imm = bool(instrInt & (1 << 25))
        flags = bool(instrInt & (1 << 20))

        rd = (instrInt >> 12) & 0xF
        rn = (instrInt >> 16) & 0xF

        if imm:
            val = instrInt & 0xFF
            shift = ("ROR", "imm", ((instrInt >> 8) & 0xF) * 2)       # see 4.5.3 of ARM doc to understand the * 2
        else:
            val = instrInt & 0xF
            if instrInt & (1 << 4):
                shift = (shiftMappingR[(instrInt >> 5) & 0x3], "reg", (instrInt >> 8) & 0xF)
            else:
                shift = (shiftMappingR[(instrInt >> 5) & 0x3] , "imm", (instrInt >> 7) & 0x1F)
        op2 = (val, shift)

        if not 7 < opcodeNum < 12:
            affectedRegs = (rd,)

        miscInfo = {'opcode': opcode,
                'rd': rd,
                'setflags': flags,
                'imm': imm,
                'rn': rn,
                'op2': op2}

    else:
        assert False, "Unknown instruction!"

    return category, affectedRegs, condition, miscInfo

