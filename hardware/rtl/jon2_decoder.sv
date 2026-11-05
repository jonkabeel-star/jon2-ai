// Jon2 Compute Hardware - RV32I instruction decoder
// RTL design source only. Not compiled or tested on physical FPGA hardware.
// Supports the implemented RV32I subset; unsupported encodings remain illegal.
// alu_ctrl: 0 ADD, 1 SUB, 2 AND, 3 OR, 4 XOR,
// 5 SLT, 6 SLTU, 7 SLL, 8 SRL, 9 SRA.
module jon2_decoder (
    input  logic [31:0] instruction,
    output logic        legal,
    output logic        reg_write,
    output logic        alu_src_imm,
    output logic        mem_read,
    output logic        mem_write,
    output logic        mem_to_reg,
    output logic        branch,
    output logic        jump,
    output logic [3:0]  alu_ctrl
);
    logic [6:0] opcode, funct7;
    logic [2:0] funct3;

    assign opcode = instruction[6:0];
    assign funct3 = instruction[14:12];
    assign funct7 = instruction[31:25];

    always_comb begin
        legal       = 1'b0;
        reg_write   = 1'b0;
        alu_src_imm = 1'b0;
        mem_read    = 1'b0;
        mem_write   = 1'b0;
        mem_to_reg  = 1'b0;
        branch      = 1'b0;
        jump        = 1'b0;
        alu_ctrl    = 4'd0;

        case (opcode)
            7'b0110011: begin // R-type
                case (funct3)
                    3'b000: begin
                        if (funct7 == 7'b0000000) begin legal=1; reg_write=1; alu_ctrl=0; end
                        else if (funct7 == 7'b0100000) begin legal=1; reg_write=1; alu_ctrl=1; end
                    end
                    3'b111: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=2; end
                    3'b110: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=3; end
                    3'b100: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=4; end
                    3'b010: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=5; end
                    3'b011: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=6; end
                    3'b001: if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=7; end
                    3'b101: begin
                        if (funct7 == 0) begin legal=1; reg_write=1; alu_ctrl=8; end
                        else if (funct7 == 7'b0100000) begin legal=1; reg_write=1; alu_ctrl=9; end
                    end
                    default: begin end
                endcase
            end

            7'b0010011: begin // I-type ALU
                case (funct3)
                    3'b000: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=0; end
                    3'b111: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=2; end
                    3'b110: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=3; end
                    3'b100: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=4; end
                    3'b010: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=5; end
                    3'b011: begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=6; end
                    3'b001: if (funct7 == 0) begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=7; end
                    3'b101: begin
                        if (funct7 == 0) begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=8; end
                        else if (funct7 == 7'b0100000) begin legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=9; end
                    end
                    default: begin end
                endcase
            end

            7'b0000011: if (funct3 == 3'b010) begin // LW
                legal=1; reg_write=1; alu_src_imm=1;
                mem_read=1; mem_to_reg=1; alu_ctrl=0;
            end

            7'b0100011: if (funct3 == 3'b010) begin // SW
                legal=1; alu_src_imm=1; mem_write=1; alu_ctrl=0;
            end

            7'b1100011: begin // All six RV32I branch conditions
                case (funct3)
                    3'b000, 3'b001, 3'b100, 3'b101, 3'b110, 3'b111: begin
                        legal=1; branch=1; alu_ctrl=1;
                    end
                    default: begin end
                endcase
            end

            7'b1101111: begin // JAL
                legal=1; reg_write=1; jump=1;
            end

            7'b1100111: if (funct3 == 3'b000) begin // JALR
                legal=1; reg_write=1; alu_src_imm=1; jump=1; alu_ctrl=0;
            end

            7'b0110111: begin // LUI
                legal=1; reg_write=1; alu_src_imm=1;
            end

            7'b0010111: begin // AUIPC
                legal=1; reg_write=1; alu_src_imm=1; alu_ctrl=0;
            end

            default: begin end
        endcase
    end
endmodule
