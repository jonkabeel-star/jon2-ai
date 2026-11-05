# Jon2 Compute Hardware

## Project status (truthful)
- Physical hardware available: none.
- FPGA board programmed: no.
- ASIC fabricated: no.
- CPU running on physical silicon: no.
- RTL source files committed: yes (design artifacts only).
- Automated compile workflow: configured; latest run result must be checked separately.
- Synthesis, place-and-route, bitstream generation, and physical board tests: not confirmed/performed.

This directory is the hardware-design track for Jon2 AI. RTL source describes circuits; it does not create physical CPU, RAM, storage, or GPU resources by itself.

## Initial target
- Architecture: RISC-V, RV32I base integer ISA subset.
- Implementation path: SystemVerilog RTL -> compile/lint -> verification -> synthesis/place-and-route -> FPGA bitstream -> program a compatible physical FPGA board.
- First source milestone: implement and review datapath/control blocks, then integrate a top-level core.

## Current RTL source files
- `rtl/jon2_pc.sv` — 32-bit program counter with configurable reset, hold, and redirect.
- `rtl/jon2_fetch_unit.sv` — connects the program counter to instruction memory.
- `rtl/jon2_core.sv` — initial single-cycle RV32I subset integration of fetch, decode, register file, ALU, and word data memory.
- `rtl/jon2_alu.sv` — 32-bit arithmetic/logic operations.
- `rtl/jon2_register_file.sv` — integer register file with x0 hardwired to zero.
- `rtl/jon2_decoder.sv` — implemented instruction decoding, including six branch encodings.
- `rtl/jon2_immediate_gen.sv` — I/S/B/U/J immediate-value generation.
- `rtl/jon2_control_unit.sv` — control signals, branch decisions, immediate selection, and writeback/PC selection.
- `rtl/jon2_data_memory.sv` — parameterized 32-bit word memory for aligned accesses in a configurable address window.
- `rtl/jon2_instruction_memory.sv` — parameterized read-only instruction store with optional `$readmemh` initialization and address validation.
- `tb/tb_jon2_data_memory.sv` — tests write/read, alignment and bounds rejection, plus `WORDS=1` and non-power-of-two `WORDS=3` memory configurations.
- `tb/tb_jon2_instruction_memory.sv` and `tb/fixtures/jon2_instruction_memory.hex` — deterministic instruction-memory read and bounds tests.
- `tb/tb_jon2_fetch_unit.sv` — reset, sequential fetch, hold, and redirect smoke tests.
- `tb/tb_jon2_core.sv` and `tb/fixtures/jon2_core_program.hex` — end-to-end core program test covering ADDI, ADD, LUI, SW, LW, and a taken BEQ with wrong-path skipping.
- `tb/tb_jon2_control_unit.sv` — tests all six branch conditions, signed/unsigned comparisons, JAL/JALR control signals, and rejection of an unsupported branch encoding.
- `tb/tb_jon2_core_jumps.sv` and `tb/fixtures/jon2_jump_program.hex` — end-to-end JAL/JALR target, link-address, and wrong-path tests.
- `tb/tb_jon2_core_faults.sv`, `tb/fixtures/jon2_unaligned_store.hex`, `tb/fixtures/jon2_illegal_instruction.hex`, and `tb/fixtures/jon2_out_of_range_store.hex` plus `tb/fixtures/jon2_out_of_range_load.hex` — verify halt, fault reporting, PC hold, and disabled register writes for unaligned stores, illegal instructions, and out-of-range loads/stores.

These are source files and simulation testbenches only. The GitHub Actions RTL workflow completed successfully in run `42031802710`, including integrated core execution, branch/jump control tests, JAL/JALR execution, fault-halt tests for unaligned stores, illegal instructions, and out-of-range loads/stores. The data-memory test also covers one-word and non-power-of-two three-word configurations. This verifies the tested simulations and compilation only; it does not establish synthesis or physical hardware operation. The data memory is an RTL memory array and is not physical RAM.

## Implemented subset and limitations
- Integer ALU operations: ADD, SUB, AND, OR, XOR, SLT, SLTU, SLL, SRL, SRA.
- Immediate ALU operations supported by the decoder.
- LW and SW word accesses only; byte/halfword loads and stores are not implemented.
- BEQ, BNE, BLT, BGE, BLTU, and BGEU branch comparisons.
- JAL, JALR, LUI, and AUIPC control encodings.
- An initial single-cycle integrated core is present in RTL. Its end-to-end simulation test passed for ADDI, ADD, LUI, SW, LW, and a taken BEQ branch (including wrong-path skipping). Separate tests passed all six branch conditions, signed/unsigned comparison cases, JAL/JALR control selection, integrated JAL/JALR execution with link-address checks, and halt/PC-hold behavior for unaligned memory access, illegal instructions, and out-of-range loads/stores in GitHub Actions run 42023004276. This is an early RV32I subset, not a complete or production-ready CPU.
- Byte/halfword memory operations, robust exception/trap handling, privilege modes, interrupts, caches, pipelining, and broad ISA compliance remain unimplemented and require further verification.

## Next engineering milestones
1. Review interfaces and operation encodings across all RTL modules.
2. Expand end-to-end tests for reset behavior after faults and broader instruction sequencing.
3. Review synthesis compatibility and remove simulation-only constructs where needed.
4. Run broader RTL lint, simulation, and ISA compliance tests.
5. Synthesize and generate a bitstream for a selected FPGA family.
6. Program and test on an actual compatible FPGA development board.

## Hardware boundary
A physical FPGA development board is required before claiming the design has been loaded onto hardware. A separate real compute board or computer will be required for a useful Jon2 AI host. A small FPGA soft CPU is an embedded control processor, not a substitute for a GPU or a powerful AI inference server.

## No-claim policy
- Do not describe RTL as a working physical CPU.
- Do not report clock speed, RAM, storage, GPU, benchmark, or board status unless measured on actual hardware.
- Software compilation or simulation, if performed, must be clearly labelled and never represented as physical execution.
- No external paid AI inference service is part of this hardware design.
