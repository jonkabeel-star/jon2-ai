"""Jon2 Compute Core: a small, bounded virtual CPU simulator.

This is software emulation, not a physical CPU or a source of extra host compute.
Programs are lists of instructions; arbitrary Python code is never evaluated.
"""
from dataclasses import dataclass, field
from typing import Any

REGISTER_NAMES = tuple(f"R{i}" for i in range(8))
RAM_SIZE = 64 * 1024


class CPUError(Exception):
    """Raised for invalid instructions or memory access."""


@dataclass
class VirtualCPU:
    ram_size: int = RAM_SIZE
    max_steps: int = 100_000
    registers: dict[str, int] = field(
        default_factory=lambda: {name: 0 for name in REGISTER_NAMES}
    )
    ram: bytearray = field(default_factory=lambda: bytearray(RAM_SIZE))
    pc: int = 0
    zero_flag: bool = False
    halted: bool = False
    output: list[int] = field(default_factory=list)
    steps: int = 0

    def __post_init__(self) -> None:
        if self.ram_size <= 0 or self.ram_size > 16 * 1024 * 1024:
            raise CPUError("RAM size must be between 1 byte and 16 MiB")
        if len(self.ram) != self.ram_size:
            self.ram = bytearray(self.ram_size)
        if self.max_steps <= 0:
            raise CPUError("max_steps must be positive")

    def _reg(self, name: Any) -> str:
        if not isinstance(name, str) or name not in self.registers:
            raise CPUError(f"Invalid register: {name!r}")
        return name

    def _address(self, value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise CPUError("Memory address must be an integer")
        if not 0 <= value < self.ram_size:
            raise CPUError(f"Memory address out of range: {value}")
        return value

    @staticmethod
    def _u32(value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise CPUError("Register values must be integers")
        return value & 0xFFFFFFFF

    def step(self, program: list[tuple]) -> None:
        if self.halted:
            return
        if self.steps >= self.max_steps:
            raise CPUError("Instruction limit reached")
        if not 0 <= self.pc < len(program):
            self.halted = True
            return

        instruction = program[self.pc]
        if not isinstance(instruction, (tuple, list)) or not instruction:
            raise CPUError("Malformed instruction")
        op, *args = instruction
        self.pc += 1

        if op == "SET" and len(args) == 2:
            reg = self._reg(args[0])
            self.registers[reg] = self._u32(args[1])
            self.zero_flag = self.registers[reg] == 0
        elif op in ("ADD", "SUB", "MUL") and len(args) == 3:
            dest, left, right = map(self._reg, args)
            a, b = self.registers[left], self.registers[right]
            value = a + b if op == "ADD" else a - b if op == "SUB" else a * b
            self.registers[dest] = self._u32(value)
            self.zero_flag = self.registers[dest] == 0
        elif op == "LOAD" and len(args) == 2:
            dest = self._reg(args[0])
            address = self._address(args[1])
            self.registers[dest] = int.from_bytes(
                self.ram[address:address + 4].ljust(4, b"\x00"), "little"
            )
            self.zero_flag = self.registers[dest] == 0
        elif op == "STORE" and len(args) == 2:
            address = self._address(args[0])
            value = self.registers[self._reg(args[1])]
            if address + 4 > self.ram_size:
                raise CPUError("32-bit store exceeds RAM boundary")
            self.ram[address:address + 4] = value.to_bytes(4, "little")
        elif op == "JMP" and len(args) == 1:
            target = args[0]
            if not isinstance(target, int) or not 0 <= target < len(program):
                raise CPUError("Invalid jump target")
            self.pc = target
        elif op == "JZ" and len(args) == 1:
            target = args[0]
            if not isinstance(target, int) or not 0 <= target < len(program):
                raise CPUError("Invalid jump target")
            if self.zero_flag:
                self.pc = target
        elif op == "OUT" and len(args) == 1:
            self.output.append(self.registers[self._reg(args[0])])
        elif op == "HALT" and not args:
            self.halted = True
        else:
            raise CPUError(f"Unsupported or malformed instruction: {op!r}")

        self.steps += 1

    def run(self, program: list[tuple]) -> list[int]:
        if not isinstance(program, list):
            raise CPUError("Program must be a list of instructions")
        while not self.halted and self.pc < len(program):
            self.step(program)
        if self.steps >= self.max_steps and not self.halted and self.pc < len(program):
            raise CPUError("Instruction limit reached")
        return list(self.output)
