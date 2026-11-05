// Jon2 Compute Hardware - single-cycle RV32I subset core
// RTL simulation/design artifact only; not physical hardware.
module jon2_core #(
    parameter integer INSTRUCTION_WORDS = 256,
    parameter integer DATA_WORDS = 256,
    parameter logic [31:0] RESET_PC = 32'h0000_1000,
    parameter logic [31:0] INSTRUCTION_BASE_ADDR = 32'h0000_1000,
    parameter logic [31:0] DATA_BASE_ADDR = 32'h1000_0000,
    parameter INIT_FILE = ""
) (
    input  logic clk,
    input  logic reset_n,
    output logic [31:0] debug_pc,
    output logic [31:0] debug_instruction,
    output logic        halted,
    output logic        debug_reg_write,
    output logic [4:0]  debug_rd,
    output logic [31:0] debug_writeback_data
);
    logic [31:0] pc, instruction, pc_plus4;
    logic instruction_valid, instruction_error;
    logic legal, reg_write, alu_src_imm, alu_a_pc;
    logic mem_read, mem_write;
    logic [1:0] writeback_sel, pc_sel;
    logic [3:0] alu_ctrl;
    logic [2:0] imm_type;
    logic [31:0] immediate;
    logic imm_valid, branch_taken;
    logic [31:0] rs1_value, rs2_value;
    logic [31:0] alu_a, alu_b, alu_result;
    logic alu_zero;
    logic [31:0] memory_read_data;
    logic memory_valid, memory_error;
    logic [31:0] writeback_data, next_pc;
    logic fault;

    assign pc_plus4 = pc + 32'd4;
    assign debug_pc = pc;
    assign debug_instruction = instruction;
    assign debug_reg_write = reg_write && !fault;
    assign debug_rd = instruction[11:7];
    assign debug_writeback_data = writeback_data;
    assign fault = reset_n && (!instruction_valid || instruction_error ||
                               !legal || !imm_valid || memory_error);
    assign halted = fault;

    jon2_fetch_unit #(
        .INSTRUCTION_WORDS(INSTRUCTION_WORDS),
        .RESET_PC(RESET_PC),
        .INSTRUCTION_BASE_ADDR(INSTRUCTION_BASE_ADDR),
        .INIT_FILE(INIT_FILE)
    ) fetch (
        .clk(clk), .reset_n(reset_n), .hold(fault),
        .redirect(!fault && (pc_sel != 2'd0)),
        .redirect_addr(next_pc),
        .pc(pc), .instruction(instruction),
        .instruction_valid(instruction_valid),
        .instruction_error(instruction_error)
    );

    jon2_register_file registers (
        .clk(clk), .write_enable(reg_write && !fault),
        .read_addr_a(instruction[19:15]),
        .read_addr_b(instruction[24:20]),
        .write_addr(instruction[11:7]),
        .write_data(writeback_data),
        .read_data_a(rs1_value), .read_data_b(rs2_value)
    );

    jon2_control_unit control (
        .instruction(instruction),
        .rs1_value(rs1_value), .rs2_value(rs2_value),
        .legal(legal), .reg_write(reg_write),
        .alu_src_imm(alu_src_imm), .alu_a_pc(alu_a_pc),
        .mem_read(mem_read), .mem_write(mem_write),
        .writeback_sel(writeback_sel), .alu_ctrl(alu_ctrl),
        .imm_type(imm_type), .immediate(immediate),
        .imm_valid(imm_valid), .branch_taken(branch_taken),
        .pc_sel(pc_sel)
    );

    assign alu_a = alu_a_pc ? pc : rs1_value;
    assign alu_b = alu_src_imm ? immediate : rs2_value;

    jon2_alu alu (
        .a(alu_a), .b(alu_b), .alu_ctrl(alu_ctrl),
        .result(alu_result), .zero(alu_zero)
    );

    jon2_data_memory #(
        .WORDS(DATA_WORDS), .BASE_ADDR(DATA_BASE_ADDR)
    ) data_memory (
        .clk(clk),
        .read_enable(mem_read && legal),
        .write_enable(mem_write && legal),
        .address(alu_result), .write_data(rs2_value),
        .read_data(memory_read_data),
        .access_valid(memory_valid), .access_error(memory_error)
    );

    always_comb begin
        case (writeback_sel)
            2'd1: writeback_data = memory_read_data;
            2'd2: writeback_data = pc_plus4;
            2'd3: writeback_data = immediate;
            default: writeback_data = alu_result;
        endcase

        case (pc_sel)
            2'd1: next_pc = pc + immediate;
            2'd2: next_pc = pc + immediate;
            2'd3: next_pc = {alu_result[31:1], 1'b0};
            default: next_pc = pc_plus4;
        endcase
    end
endmodule
