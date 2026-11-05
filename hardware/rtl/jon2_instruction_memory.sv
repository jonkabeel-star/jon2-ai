// Jon2 Compute Hardware - RV32I instruction memory
// Parameterized read-only instruction store. RTL source only; not physical RAM.
// INIT_FILE may point to a reviewed hexadecimal instruction image. When empty,
// contents are unspecified until initialized by the implementation/testbench.
module jon2_instruction_memory #(
    parameter integer WORDS = 1024,
    parameter logic [31:0] BASE_ADDR = 32'h0000_0000,
    parameter INIT_FILE = ""
) (
    input  logic        read_enable,
    input  logic [31:0] address,
    output logic [31:0] instruction,
    output logic        access_valid,
    output logic        access_error
);
    logic [31:0] memory [0:WORDS-1];
    integer word_index;

    initial begin
        if (WORDS < 1)
            $error("WORDS must be at least 1");
        if (INIT_FILE != "")
            $readmemh(INIT_FILE, memory);
    end

    always_comb begin
        instruction = 32'h0000_0013; // RISC-V NOP (ADDI x0,x0,0) on invalid reads
        access_valid = 1'b0;
        access_error = 1'b0;
        word_index = 0;

        if (read_enable) begin
            if (address[1:0] != 2'b00) begin
                access_error = 1'b1;
            end else if (address < BASE_ADDR) begin
                access_error = 1'b1;
            end else if (((address - BASE_ADDR) >> 2) >= WORDS) begin
                access_error = 1'b1;
            end else begin
                word_index = (address - BASE_ADDR) >> 2;
                instruction = memory[word_index];
                access_valid = 1'b1;
            end
        end
    end
endmodule
