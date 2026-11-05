// Jon2 Compute Hardware - RV32I integer register file
// RTL design source only. Not tested on physical FPGA hardware.
// x0 is hardwired to zero. x1-x31 are writable 32-bit registers.
module jon2_register_file (
    input  logic        clk,
    input  logic        write_enable,
    input  logic [4:0]  read_addr_a,
    input  logic [4:0]  read_addr_b,
    input  logic [4:0]  write_addr,
    input  logic [31:0] write_data,
    output logic [31:0] read_data_a,
    output logic [31:0] read_data_b
);

    logic [31:0] registers [1:31];

    always_ff @(posedge clk) begin
        if (write_enable && (write_addr != 5'd0))
            registers[write_addr] <= write_data;
    end

    always_comb begin
        if (read_addr_a == 5'd0)
            read_data_a = 32'h00000000;
        else
            read_data_a = registers[read_addr_a];

        if (read_addr_b == 5'd0)
            read_data_b = 32'h00000000;
        else
            read_data_b = registers[read_addr_b];
    end

endmodule
