`timescale 1ns/1ps
module tb_jon2_control_unit;
    logic [31:0] instruction, rs1_value, rs2_value;
    logic legal, reg_write, alu_src_imm, alu_a_pc;
    logic mem_read, mem_write;
    logic [1:0] writeback_sel, pc_sel;
    logic [3:0] alu_ctrl;
    logic [2:0] imm_type;
    logic [31:0] immediate;
    logic imm_valid, branch_taken;

    jon2_control_unit dut (.*);

    task automatic check_branch(input logic [2:0] funct3,
                                input logic expected_taken,
                                input logic [31:0] a,
                                input logic [31:0] b);
        begin
            instruction = 32'h00208063 | (funct3 << 12); // B-type, rs1=x1, rs2=x2, +0
            rs1_value = a;
            rs2_value = b;
            #1;
            if (!legal) $fatal(1, "branch funct3 %b should be legal", funct3);
            if (branch_taken !== expected_taken)
                $fatal(1, "branch funct3 %b expected %b got %b", funct3, expected_taken, branch_taken);
            if (pc_sel !== (expected_taken ? 2'd1 : 2'd0))
                $fatal(1, "branch PC select incorrect for funct3 %b", funct3);
        end
    endtask

    initial begin
        rs1_value = 0;
        rs2_value = 0;
        instruction = 0;
        #1;

        // Equal operands: BEQ, BGE and BGEU are taken.
        check_branch(3'b000, 1'b1, 32'd5, 32'd5);
        check_branch(3'b001, 1'b0, 32'd5, 32'd5);
        check_branch(3'b100, 1'b0, 32'd5, 32'd5);
        check_branch(3'b101, 1'b1, 32'd5, 32'd5);
        check_branch(3'b110, 1'b0, 32'd5, 32'd5);
        check_branch(3'b111, 1'b1, 32'd5, 32'd5);

        // 3 < 5: BNE, BLT and BLTU are taken.
        check_branch(3'b000, 1'b0, 32'd3, 32'd5);
        check_branch(3'b001, 1'b1, 32'd3, 32'd5);
        check_branch(3'b100, 1'b1, 32'd3, 32'd5);
        check_branch(3'b101, 1'b0, 32'd3, 32'd5);
        check_branch(3'b110, 1'b1, 32'd3, 32'd5);
        check_branch(3'b111, 1'b0, 32'd3, 32'd5);

        // Signed/unsigned distinction: 0xFFFFFFFF is -1 signed, but large unsigned.
        check_branch(3'b100, 1'b1, 32'hffff_ffff, 32'd1);
        check_branch(3'b110, 1'b0, 32'hffff_ffff, 32'd1);

        instruction = 32'h0080_00ef; // JAL x1, +8
        #1;
        if (!legal || pc_sel !== 2'd2 || writeback_sel !== 2'd2 || !reg_write)
            $fatal(1, "JAL control signals incorrect");

        instruction = 32'h0000_80e7; // JALR x1, 0(x1)
        #1;
        if (!legal || pc_sel !== 2'd3 || writeback_sel !== 2'd2 || !reg_write)
            $fatal(1, "JALR control signals incorrect");

        instruction = 32'h0020_a063; // unsupported branch funct3=010
        #1;
        if (legal || reg_write || mem_write || mem_read)
            $fatal(1, "unsupported branch encoding was not rejected");

        $display("PASS: all six branch conditions, signed/unsigned comparisons, JAL/JALR control, illegal branch rejection");
        $finish;
    end
endmodule
