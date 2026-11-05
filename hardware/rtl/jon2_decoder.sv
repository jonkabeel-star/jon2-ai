// Jon2 Compute Hardware - RV32I instruction decoder
// RTL design source only. Not tested on physical FPGA hardware.
// Decodes the base integer instruction fields needed by the initial core.
// alu_ctrl encoding matches jon2_alu.sv:
// 0 ADD, 1 SUB, 2 AND, 3 OR, 4 XOR,
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

    logic [6:0] opcode;
    logic [2:0] funct3;
    logic [6:0] funct7;

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
            // Register-register integer operations (R-type)
            7'b0110011: begin
                case (funct3)
                    3'b000: begin
                        if (funct7 == 7'b0000000) begin
                            legal = 1'b1; reg_write = 1'b1; alu_ctrl = 4'd0;
                        end else if (funct7 == 7'b0100000) begin
                            legal = 1'b1; reg_write = 1'b1; alu_ctrl = 4'd1;
                        end
                    end
                    3'b111: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd2; end
                    3'b110: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd3; end
                    3'b100: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd4; end
                    3'b010: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd5; end
                    3'b011: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd6; end
                    3'b001: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd7; end
                    3'b101: begin
                        if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd8; end
                        else if (funct7 == 7'b0100000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd9; end
                    end
                    default: begin end
                endcase
            end

            // Immediate integer operations (I-type ALU)
            7'b0010011: begin
                alu_src_imm = 1'b1;
                case (funct3)
                    3'b000: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd0; end // ADDI
                    3'b111: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd2; end // ANDI
                    3'b110: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd3; end // ORI
                    3'b100: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd4; end // XORI
                    3'b010: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd5; end // SLTI
                    3'b011: begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd6; end // SLTIU
                    3'b001: if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd7; end
                    3'b101: begin
                        if (funct7 == 7'b0000000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd8; end
                        else if (funct7 == 7'b0100000) begin legal=1'b1; reg_write=1'b1; alu_ctrl=4'd9; end
                    end
                    default: begin end
                endcase
                if (!legal) alu_src_imm = 1'b0;
            end

            // Load word (LW)
            7'b0000011: if (funct3 == 3'b010) begin
                legal=1'b1; reg_write=1'b1; alu_src_imm=1'b1;
                mem_read=1'b1; mem_to_reg=1'b1; alu_ctrl=4'd0;
            end

            // Store word (SW)
            7'b0100011: if (funct3 == 3'b010) begin
                legal=1'b1; alu_src_imm=1'b1; mem_write=1'b1; alu_ctrl=4'd0;
            end

            // Conditional branches: BEQ and BNE
            7'b1100011: begin
                if (funct3 == 3'b000 || funct3 == 3'b001) begin
                    legal=1'b1; branch=1'b1; alu_ctrl=4'd1;
                end
            end

            // Jump and link (JAL)
            7'b1101111: begin
                legal=1'b1; reg_write=1'b1; jump=1'b1;
            end

            // Jump and link register (JALR)
            7'b1100111: if (funct3 == 3'b000) begin
                legal=1'b1; reg_write=1'b1; alu_src_imm=1'b1; jump=1'b1; alu_ctrl=4'd0;
            end

            // Load upper immediate (LUI)
            7'b0110111: begin
                legal=1'b1; reg_write=1'b1; alu_src_imm=1'b1;
            end

            // Add upper immediate to PC (AUIPC)
            7'b0010111: begin
                legal=1'b1; reg_write=1'b1; alu_src_imm=1'b1; alu_ctrl=4'd0;
            end

            default: begin end
        endcase
    end

endmodule
