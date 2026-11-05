// Jon2 Compute Hardware - RV32I instruction fetch path
// Connects the program counter to the read-only instruction memory.
// RTL source only; no physical CPU or memory is implied.
module jon2_fetch_unit #(
    parameter integer INSTRUCTION_WORDS = 1024,
    parameter logic [31:0] RESET_PC = 32'h0000_0000,
    parameter logic [31:0] INSTRUCTION_BASE_ADDR = 32'h0000_0000,
    parameter INIT_FILE = ""
) (
    input  logic        clk,
    input  logic        reset_n,
    input  logic        hold,
    input  logic        redirect,
    input  logic [31:0] redirect_addr,
    output logic [31:0] pc,
    output logic [31:0] instruction,
    output logic        instruction_valid,
    output logic        instruction_error
);
    jon2_pc program_counter (
        .clk(clk),
        .reset_n(reset_n),
        .hold(hold),
        .redirect(redirect),
        .redirect_addr(redirect_addr),
        .pc(pc)
    );

    jon2_instruction_memory #(
        .WORDS(INSTRUCTION_WORDS),
        .BASE_ADDR(INSTRUCTION_BASE_ADDR),
        .INIT_FILE(INIT_FILE)
    ) instruction_store (
        .read_enable(reset_n),
        .address(pc),
        .instruction(instruction),
        .access_valid(instruction_valid),
        .access_error(instruction_error)
    );
endmodule
