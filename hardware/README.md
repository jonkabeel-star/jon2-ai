# Jon2 Compute Hardware

## Project status (truthful)
- Physical hardware available: none.
- FPGA board programmed: no.
- ASIC fabricated: no.
- CPU running on physical silicon: no.
- RTL source files committed: yes (design artifacts only).
- Synthesis, place-and-route, bitstream generation, and physical board tests: not confirmed/performed.

This directory is the hardware-design track for Jon2 AI. It is separate from the Python software compute utilities. RTL source describes circuits; it does not create physical CPU, RAM, storage, or GPU resources by itself.

## Initial target
- Architecture: RISC-V, RV32I base integer ISA.
- Implementation path: SystemVerilog RTL -> synthesis/place-and-route -> FPGA bitstream -> program a compatible physical FPGA board.
- First source milestone: implement and review individual datapath/control blocks, then integrate a top-level core.

## Current RTL source files
- `rtl/jon2_pc.sv` — 32-bit program counter with reset, hold, and redirect.
- `rtl/jon2_alu.sv` — 32-bit arithmetic/logic operations.
- `rtl/jon2_register_file.sv` — integer register file with x0 hardwired to zero.
- `rtl/jon2_decoder.sv` — instruction decoding.
- `rtl/jon2_immediate_gen.sv` — immediate-value generation.

These are source files only. Their presence does not establish that the modules compile, pass tests, synthesize, or run on hardware. No such verification is claimed here.

## Next engineering milestones
1. Review interfaces and operation encodings across the existing RTL modules.
2. Add a control unit and define shared control-signal encodings.
3. Integrate the datapath into a top-level RV32I core.
4. Add a documented verification plan and run RTL checks when a suitable tool environment is available.
5. Synthesize and generate a bitstream for a selected FPGA family.
6. Program and test on an actual compatible FPGA development board.

## Hardware boundary
A physical FPGA development board is required before claiming the design has been loaded onto hardware. A separate real compute board or computer will be required for a useful Jon2 AI host. A small FPGA soft CPU is an embedded control processor, not a substitute for a GPU or a powerful AI inference server.

## No-simulation / no-claim policy
- Do not describe RTL as a working physical CPU.
- Do not report clock speed, RAM, storage, GPU, benchmark, or board status unless measured on actual hardware.
- Software verification or simulation, if later used, must be clearly labelled and never represented as physical execution.
- No external paid AI inference service is part of this hardware design.
