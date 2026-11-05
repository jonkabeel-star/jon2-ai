`timescale 1ns/1ps
module tb_jon2_register_file;
    logic clk, write_enable;
    logic [4:0] read_addr_a, read_addr_b, write_addr;
    logic [31:0] write_data, read_data_a, read_data_b;

    jon2_register_file dut(
        .clk(clk), .write_enable(write_enable),
        .read_addr_a(read_addr_a), .read_addr_b(read_addr_b),
        .write_addr(write_addr), .write_data(write_data),
        .read_data_a(read_data_a), .read_data_b(read_data_b)
    );

    always #5 clk=~clk;

    initial begin
        clk=0; write_enable=0; read_addr_a=0; read_addr_b=0;
        write_addr=0; write_data=0;
        #2;
        if (read_data_a !== 32'd0 || read_data_b !== 32'd0)
            $fatal(1,"x0 did not read as zero");
        @(negedge clk);
        write_enable=1; write_addr=5'd5; write_data=32'h1234ABCD;
        @(negedge clk);
        write_enable=0; read_addr_a=5'd5;
        #1;
        if (read_data_a !== 32'h1234ABCD)
            $fatal(1,"register write/read failed: %h",read_data_a);
        write_enable=1; write_addr=5'd0; write_data=32'hFFFFFFFF;
        @(negedge clk);
        write_enable=0; read_addr_a=0;
        #1;
        if (read_data_a !== 32'd0) $fatal(1,"x0 was modified");
        $display("PASS: Jon2 register file smoke tests");
        $finish;
    end
endmodule
