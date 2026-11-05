`timescale 1ns/1ps
module tb_jon2_core;
    logic clk=0;
    logic reset_n=1;
    logic [31:0] debug_pc, debug_instruction, debug_writeback_data;
    logic halted, debug_reg_write;
    logic [4:0] debug_rd;

    always #5 clk=~clk;

    jon2_core #(
        .INSTRUCTION_WORDS(11),
        .DATA_WORDS(16),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_core_program.hex")
    ) dut (
        .clk(clk), .reset_n(reset_n),
        .debug_pc(debug_pc), .debug_instruction(debug_instruction),
        .halted(halted), .debug_reg_write(debug_reg_write),
        .debug_rd(debug_rd), .debug_writeback_data(debug_writeback_data)
    );

    initial begin
        #1 reset_n=0;
        #1;
        if (debug_pc !== 32'h0000_1000) $fatal(1,"core reset PC failed");
        reset_n=1;
        repeat(9) begin
            @(posedge clk); #1;
            $display("CORE TRACE pc=%h insn=%h halted=%b legal=%b memerr=%b x1=%h x2=%h x3=%h x4=%h x5=%h x6=%h x7=%h", debug_pc, debug_instruction, halted, dut.legal, dut.memory_error, dut.registers.registers[1], dut.registers.registers[2], dut.registers.registers[3], dut.registers.registers[4], dut.registers.registers[5], dut.registers.registers[6], dut.registers.registers[7]);
        end
        if (dut.registers.registers[1] !== 32'd5)
            $fatal(1,"ADDI x1 failed: %h",dut.registers.registers[1]);
        if (dut.registers.registers[2] !== 32'd12)
            $fatal(1,"ADDI x2 failed: %h",dut.registers.registers[2]);
        if (dut.registers.registers[3] !== 32'd17)
            $fatal(1,"ADD x3 failed: %h",dut.registers.registers[3]);
        if (dut.registers.registers[5] !== 32'd17) $fatal(1,"LW x5 failed: %h",dut.registers.registers[5]);
        if (dut.data_memory.memory[0] !== 32'd17) $fatal(1,"SW memory write failed: %h",dut.data_memory.memory[0]);
        if (dut.registers.registers[6] !== 32'd1) $fatal(1,"BEQ did not skip wrong path: %h",dut.registers.registers[6]);
        if (dut.registers.registers[7] !== 32'd42) $fatal(1,"branch target ADDI failed: %h",dut.registers.registers[7]);
        if (halted) $fatal(1,"core halted unexpectedly");
        $display("PASS: Jon2 core executed ADDI, ADDI, ADD program");
        $finish;
    end
endmodule
