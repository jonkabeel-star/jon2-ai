`timescale 1ns/1ps
module tb_jon2_core_jumps;
    logic clk=0;
    logic reset_n=1;
    logic [31:0] debug_pc, debug_instruction, debug_writeback_data;
    logic halted, debug_reg_write;
    logic [4:0] debug_rd;

    always #5 clk=~clk;

    jon2_core #(
        .INSTRUCTION_WORDS(9),
        .DATA_WORDS(8),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_jump_program.hex")
    ) dut (
        .clk(clk), .reset_n(reset_n),
        .debug_pc(debug_pc), .debug_instruction(debug_instruction),
        .halted(halted), .debug_reg_write(debug_reg_write),
        .debug_rd(debug_rd), .debug_writeback_data(debug_writeback_data)
    );

    initial begin
        #1 reset_n=0;
        #1;
        reset_n=1;
        repeat(6) begin
            @(posedge clk); #1;
            $display("JUMP TRACE pc=%h insn=%h halted=%b x1=%h x2=%h x3=%h x4=%h x5=%h x6=%h x7=%h",
                debug_pc, debug_instruction, halted,
                dut.registers.registers[1], dut.registers.registers[2],
                dut.registers.registers[3], dut.registers.registers[4],
                dut.registers.registers[5], dut.registers.registers[6],
                dut.registers.registers[7]);
        end

        if (dut.registers.registers[1] !== 32'h0000_101c)
            $fatal(1, "JALR base register setup failed");
        if (dut.registers.registers[2] !== 32'h0000_100c)
            $fatal(1, "JAL link register incorrect: %h", dut.registers.registers[2]);
        if (dut.registers.registers[3] === 32'd99)
            $fatal(1, "JAL failed to skip wrong-path instruction");
        if (dut.registers.registers[4] !== 32'd7)
            $fatal(1, "JAL target instruction did not execute");
        if (dut.registers.registers[5] !== 32'h0000_1018)
            $fatal(1, "JALR link register incorrect: %h", dut.registers.registers[5]);
        if (dut.registers.registers[6] === 32'd99)
            $fatal(1, "JALR failed to skip wrong-path instruction");
        if (dut.registers.registers[7] !== 32'd42)
            $fatal(1, "JALR target instruction did not execute");
        if (halted)
            $fatal(1, "core halted unexpectedly during jump test");

        $display("PASS: integrated JAL/JALR targets, link addresses, and wrong-path skipping");
        $finish;
    end
endmodule
