`timescale 1ns/1ps
module tb_jon2_core_faults;
    logic clk=0, reset_n=1;
    logic [31:0] pc_mem, insn_mem, wb_mem, pc_ill, insn_ill, wb_ill, pc_range, insn_range, wb_range;
    logic halt_mem, wr_mem;
    logic halt_ill, wr_ill, halt_range, wr_range;
    logic [4:0] rd_mem, rd_ill, rd_range;

    always #5 clk=~clk;

    jon2_core #(
        .INSTRUCTION_WORDS(4), .DATA_WORDS(4),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_unaligned_store.hex")
    ) memory_fault_core (
        .clk(clk), .reset_n(reset_n), .debug_pc(pc_mem),
        .debug_instruction(insn_mem), .halted(halt_mem),
        .debug_reg_write(wr_mem), .debug_rd(rd_mem),
        .debug_writeback_data(wb_mem)
    );

    jon2_core #(
        .INSTRUCTION_WORDS(2), .DATA_WORDS(4),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_illegal_instruction.hex")
    ) illegal_core (
        .clk(clk), .reset_n(reset_n), .debug_pc(pc_ill),
        .debug_instruction(insn_ill), .halted(halt_ill),
        .debug_reg_write(wr_ill), .debug_rd(rd_ill),
        .debug_writeback_data(wb_ill)
    );


    jon2_core #(
        .INSTRUCTION_WORDS(4), .DATA_WORDS(4),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_out_of_range_store.hex")
    ) range_fault_core (
        .clk(clk), .reset_n(reset_n), .debug_pc(pc_range),
        .debug_instruction(insn_range), .halted(halt_range),
        .debug_reg_write(wr_range), .debug_rd(rd_range),
        .debug_writeback_data(wb_range)
    );

    initial begin
        #1 reset_n=0;
        #1 reset_n=1;

        repeat(5) begin
            @(posedge clk); #1;
            $display("FAULT TRACE mem pc=%h insn=%h halted=%b memerr=%b | illegal pc=%h insn=%h halted=%b legal=%b",
                pc_mem, insn_mem, halt_mem, memory_fault_core.memory_error,
                pc_ill, insn_ill, halt_ill, illegal_core.legal);
            $display("RANGE TRACE pc=%h insn=%h halted=%b memerr=%b", pc_range, insn_range, halt_range, range_fault_core.memory_error);
        end

        if (!halt_mem || !memory_fault_core.memory_error)
            $fatal(1, "unaligned store did not raise a memory fault");
        if (pc_mem !== 32'h0000_1008)
            $fatal(1, "memory-faulting instruction PC was not held: %h", pc_mem);
        if (wr_mem)
            $fatal(1, "register write remained enabled during memory fault");

        if (!halt_range || !range_fault_core.memory_error)
            $fatal(1, "out-of-range store did not raise a memory fault");
        if (pc_range !== 32'h0000_1008 || wr_range)
            $fatal(1, "out-of-range memory fault did not hold PC and disable writes");

        if (!halt_ill || illegal_core.legal)
            $fatal(1, "illegal instruction did not halt the core");
        if (pc_ill !== 32'h0000_1000)
            $fatal(1, "illegal instruction PC was not held: %h", pc_ill);
        if (wr_ill)
            $fatal(1, "register write remained enabled during illegal instruction fault");

        $display("PASS: unaligned and out-of-range memory accesses plus illegal instruction halt safely");
        $finish;
    end
endmodule
