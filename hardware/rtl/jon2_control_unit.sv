// Jon2 Compute Hardware - RV32I control unit
// RTL source only. Not compiled, simulated, or tested on physical hardware.
// Integrates the existing decoder and immediate generator.
// writeback_sel: 0=ALU, 1=memory, 2=PC+4, 3=immediate (LUI).
// pc_sel: 0=sequential, 1=branch, 2=JAL, 3=JALR.
// alu_a_pc selects PC as ALU operand A (AUIPC).
module jon2_control_unit (
    input  logic [31:0] instruction,
    input  logic [31:0] rs1_value,
    input  logic [31:0] rs2_value,

    output logic        legal,
    output logic        reg_write,
    output logic        alu_src_imm,
    output logic        alu_a_pc,
    output logic        mem_read,
    output logic        mem_write,
    output logic [1:0]  writeback_sel,
    output logic [3:0]  alu_ctrl,
    output logic [2:0]  imm_type,
    output logic        imm_valid,
    output logic        branch_taken,
    output logic [1:0]  pc_sel
);

    logic dec_legal;
    logic dec_reg_write;
    logic dec_alu_src_imm;
    logic dec_mem_read;
    logic dec_mem_write;
    logic dec_mem_to_reg;
    logic dec_branch;
    logic dec_jump;
    logic [2:0] opcode_funct3;

    assign opcode_funct3 = instruction[14:12];

    jon2_decoder decoder (
        .instruction(instruction),
        .legal(dec_legal),
        .reg_write(dec_reg_write),
        .alu_src_imm(dec_alu_src_imm),
        .mem_read(dec_mem_read),
        .mem_write(dec_mem_write),
        .mem_to_reg(dec_mem_to_reg),
        .branch(dec_branch),
        .jump(dec_jump),
        .alu_ctrl(alu_ctrl)
    );

    always_comb begin
        imm_type = 3'd0; // I-type default
        case (instruction[6:0])
            7'b0100011: imm_type = 3'd1; // S
            7'b1100011: imm_type = 3'd2; // B
            7'b0110111,
            7'b0010111: imm_type = 3'd3; // U
            7'b1101111: imm_type = 3'd4; // J
            default:    imm_type = 3'd0; // I
        endcase
    end

    jon2_immediate_gen immediate_generator (
        .instruction(instruction),
        .imm_type(imm_type),
        .immediate(),
        .valid_type(imm_valid)
    );

    always_comb begin
        legal         = dec_legal && imm_valid;
        reg_write     = dec_reg_write && legal;
        alu_src_imm   = dec_alu_src_imm && legal;
        alu_a_pc      = (instruction[6:0] == 7'b0010111) && legal;
        mem_read      = dec_mem_read && legal;
        mem_write     = dec_mem_write && legal;
        writeback_sel = 2'd0;
        branch_taken  = 1'b0;
        pc_sel        = 2'd0;

        if (dec_mem_to_reg && legal)
            writeback_sel = 2'd1;
        else if (dec_jump && legal)
            writeback_sel = 2'd2;
        else if ((instruction[6:0] == 7'b0110111) && legal)
            writeback_sel = 2'd3;

        if (dec_branch && legal) begin
            if (opcode_funct3 == 3'b000)
                branch_taken = (rs1_value == rs2_value); // BEQ
            else if (opcode_funct3 == 3'b001)
                branch_taken = (rs1_value != rs2_value); // BNE
            if (branch_taken)
                pc_sel = 2'd1;
        end

        if (dec_jump && legal) begin
            if (instruction[6:0] == 7'b1100111)
                pc_sel = 2'd3; // JALR
            else
                pc_sel = 2'd2; // JAL
        end

        if (!legal) begin
            reg_write     = 1'b0;
            alu_src_imm   = 1'b0;
            alu_a_pc      = 1'b0;
            mem_read      = 1'b0;
            mem_write     = 1'b0;
            writeback_sel = 2'd0;
            branch_taken  = 1'b0;
            pc_sel        = 2'd0;
        end
    end

endmodule
