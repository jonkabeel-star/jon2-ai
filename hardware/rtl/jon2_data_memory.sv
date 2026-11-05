// Jon2 Compute Hardware - simple RV32I word data memory
// RTL source only; no physical RAM or FPGA execution is implied.
// Supports aligned 32-bit LW/SW accesses in a parameterized address window.
// Reads are combinational; writes occur on the rising clock edge.
module jon2_data_memory #(
    parameter integer WORDS = 1024,
    parameter logic [31:0] BASE_ADDR = 32'h1000_0000
) (
    input  logic        clk,
    input  logic        read_enable,
    input  logic        write_enable,
    input  logic [31:0] address,
    input  logic [31:0] write_data,
    output logic [31:0] read_data,
    output logic        access_valid,
    output logic        access_error
);
    localparam integer INDEX_BITS = $clog2(WORDS);
    logic [31:0] memory [0:WORDS-1];
    logic [31:0] byte_offset;
    logic in_range;
    logic aligned;
    logic [INDEX_BITS-1:0] word_index;

    assign byte_offset = address - BASE_ADDR;
    assign in_range = (address >= BASE_ADDR) &&
                      (byte_offset < (WORDS * 4));
    assign aligned = (address[1:0] == 2'b00);
    assign word_index = byte_offset[INDEX_BITS+1:2];

    always_comb begin
        access_valid = (read_enable || write_enable) && in_range && aligned;
        access_error = (read_enable || write_enable) && !(in_range && aligned);
        read_data = 32'h0000_0000;
        if (read_enable && in_range && aligned)
            read_data = memory[word_index];
    end

    always_ff @(posedge clk) begin
        if (write_enable && in_range && aligned)
            memory[word_index] <= write_data;
    end
endmodule
