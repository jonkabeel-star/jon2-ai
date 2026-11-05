// Jon2 Compute Hardware - RV32I immediate generator
// RTL design source only. Not tested on physical FPGA hardware.
// imm_type: 0=I, 1=S, 2=B, 3=U, 4=J.
module jon2_immediate_gen (
    input  logic [31:0] instruction,
    input  logic [2:0]  imm_type,
    output logic [31:0] immediate,
    output logic        valid_type
);

    always_comb begin
        immediate = 32'h00000000;
        valid_type = 1'b1;

        case (imm_type)
            3'd0: immediate = {{20{instruction[31]}}, instruction[31:20]};
            3'd1: immediate = {{20{instruction[31]}}, instruction[31:25], instruction[11:7]};
            3'd2: immediate = {{19{instruction[31]}}, instruction[31], instruction[7],
                               instruction[30:25], instruction[11:8], 1'b0};
            3'd3: immediate = {instruction[31:12], 12'b0};
            3'd4: immediate = {{11{instruction[31]}}, instruction[31], instruction[19:12],
                               instruction[20], instruction[30:21], 1'b0};
            default: begin
                immediate = 32'h00000000;
                valid_type = 1'b0;
            end
        endcase
    end

endmodule
