`timescale 1ns/1ps
module tb_jon2_data_memory;
    logic clk = 1'b0;
    logic read_enable = 1'b0;
    logic write_enable = 1'b0;
    logic [31:0] address = 32'h1000_0000;
    logic [31:0] write_data = 32'h0;
    logic [31:0] read_data;
    logic access_valid, access_error;

    logic single_read_enable = 1'b0;
    logic single_write_enable = 1'b0;
    logic [31:0] single_address = 32'h2000_0000;
    logic [31:0] single_write_data = 32'h0;
    logic [31:0] single_read_data;
    logic single_access_valid, single_access_error;

    logic three_read_enable = 1'b0;
    logic three_write_enable = 1'b0;
    logic [31:0] three_address = 32'h3000_0000;
    logic [31:0] three_write_data = 32'h0;
    logic [31:0] three_read_data;
    logic three_access_valid, three_access_error;

    always #5 clk = ~clk;

    // A one-word memory catches zero-width index declarations.
    jon2_data_memory #(.WORDS(1), .BASE_ADDR(32'h2000_0000)) single_word_dut (
        .clk(clk), .read_enable(single_read_enable), .write_enable(single_write_enable),
        .address(single_address), .write_data(single_write_data),
        .read_data(single_read_data), .access_valid(single_access_valid),
        .access_error(single_access_error)
    );

    // A non-power-of-two depth checks index sizing and the final valid word.
    jon2_data_memory #(.WORDS(3), .BASE_ADDR(32'h3000_0000)) three_word_dut (
        .clk(clk), .read_enable(three_read_enable), .write_enable(three_write_enable),
        .address(three_address), .write_data(three_write_data),
        .read_data(three_read_data), .access_valid(three_access_valid),
        .access_error(three_access_error)
    );

    jon2_data_memory #(.WORDS(4), .BASE_ADDR(32'h1000_0000)) dut (
        .clk(clk), .read_enable(read_enable), .write_enable(write_enable),
        .address(address), .write_data(write_data), .read_data(read_data),
        .access_valid(access_valid), .access_error(access_error)
    );

    initial begin
        // Write/read the first word.
        address = 32'h1000_0000;
        write_data = 32'hA55A_1234;
        write_enable = 1'b1;
        #1;
        if (!access_valid || access_error) $fatal(1, "valid write rejected");
        @(posedge clk);
        #1;
        write_enable = 1'b0;
        read_enable = 1'b1;
        #1;
        if (read_data !== 32'hA55A_1234) $fatal(1, "readback mismatch");

        // Misaligned accesses must be rejected.
        address = 32'h1000_0001;
        #1;
        if (access_valid || !access_error) $fatal(1, "misaligned access accepted");

        // Address immediately beyond configured memory must be rejected.
        address = 32'h1000_0010;
        #1;
        if (access_valid || !access_error) $fatal(1, "out-of-range access accepted");

        // WORDS=1 must accept its only word and reject the next word.
        single_address = 32'h2000_0000;
        single_write_data = 32'h1234_ABCD;
        single_write_enable = 1'b1;
        #1;
        if (!single_access_valid || single_access_error)
            $fatal(1, "single-word memory rejected its only address");
        @(posedge clk);
        #1;
        single_write_enable = 1'b0;
        single_read_enable = 1'b1;
        #1;
        if (single_read_data !== 32'h1234_ABCD)
            $fatal(1, "single-word memory readback mismatch");
        single_address = 32'h2000_0004;
        #1;
        if (single_access_valid || !single_access_error)
            $fatal(1, "single-word memory accepted address beyond its range");
        single_read_enable = 1'b0;

        // WORDS=3 must correctly address word 2 and reject word 3.
        three_address = 32'h3000_0008;
        three_write_data = 32'h3A3A_C0DE;
        three_write_enable = 1'b1;
        #1;
        if (!three_access_valid || three_access_error)
            $fatal(1, "three-word memory rejected its final valid word");
        @(posedge clk);
        #1;
        three_write_enable = 1'b0;
        three_read_enable = 1'b1;
        #1;
        if (three_read_data !== 32'h3A3A_C0DE)
            $fatal(1, "three-word memory final-word readback mismatch");
        three_address = 32'h3000_000C;
        #1;
        if (three_access_valid || !three_access_error)
            $fatal(1, "three-word memory accepted address beyond its range");
        three_read_enable = 1'b0;

        $display("PASS: data memory read/write, alignment, bounds, WORDS=1 and WORDS=3");
        $finish;
    end
endmodule
