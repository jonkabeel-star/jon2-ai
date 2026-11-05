# Jon2 Compute Hardware

## Project status (truthful)
- Physical hardware available: none.
- FPGA board programmed: no.
- ASIC fabricated: no.
- CPU running on physical silicon: no.
- Current work: hardware description source (RTL) only.

This directory is the hardware-design track for Jon2 AI. It is separate from the Python software compute utilities. RTL source describes circuits; it does not create physical CPU, RAM, storage, or GPU resources by itself.

## Initial target
- Architecture: RISC-V, RV32I base integer ISA.
- Implementation path: SystemVerilog RTL -> synthesis/place-and-route -> FPGA bitstream -> program a compatible physical FPGA board.
- First milestone: build and verify small synthesizable hardware blocks, beginning with the program counter.
- Later milestones: register file, instruction decoder, ALU, load/store interface, control-flow logic, integration, and board bring-up.

## Hardware boundary
A physical FPGA development board is required before claiming the design has been loaded onto hardware. A separate real compute board or computer will be required for a useful Jon2 AI host. A small FPGA soft CPU is an embedded control processor, not a substitute for a GPU or a powerful AI inference server.

## No-simulation / no-claim policy
- Do not describe RTL as a working physical CPU.
- Do not report clock speed, RAM, storage, GPU, benchmark, or board status unless measured on actual hardware.
- Simulation may be used later as a software verification aid, but must never be represented as physical execution.
- No external paid AI inference service is part of this hardware design.

## First RTL block
`rtl/jon2_pc.sv` is a resettable 32-bit program-counter register with a selectable sequential or redirected next address. It is a design artifact only until synthesized and programmed onto a physical FPGA.
