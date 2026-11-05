// Jon2 Compute Hardware - RV32I ALU
// RTL design source only. This file has not been run on physical FPGA hardware.
// alu_ctrl encoding:
// 0 ADD, 1 SUB, 2 AND, 3 OR, 4 XOR,
// 5 SLT (signed), 6 SLTU (unsigned),
// 7 SLL, 8 SRL, 9 SRA.
module jon2_alu (
    input  logic [31:0] a,
    input  logic [31:0] b,
    input  logic [3:0]  alu_ctrl,
    output logic [31:0] result,
    output logic        zero
);

    always_comb begin
        result = 32'h00000000;

        case (alu_ctrl)
            4'd0: result = a + b;
            4'd1: result = a - b;
            4'd2: result = a & b;
            4'd3: result = a | b;
            4'd4: result = a ^ b;
            4'd5: result = ($signed(a) < $signed(b)) ? 32'd1 : 32'd0;
            4'd6: result = (a < b) ? 32'd1 : 32'd0;
            4'd7: result = a << b[4:0];
            4'd8: result = a >> b[4:0];
            4'd9: result = $signed(a) >>> b[4:0];
            default: result = 32'h00000000;
        endcase
    end

    assign zero = (result == 32'h00000000);

endmodule
