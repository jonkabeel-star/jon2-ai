`timescale 1ns/1ps
module tb_jon2_instruction_memory;
    logic read_enable;
    logic [31:0] address;
    logic [31:0] instruction;
    logic access_valid;
    logic access_error;

    jon2_instruction_memory #(
        .WORDS(4),
        .BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_instruction_memory.hex")
    ) dut (
        .read_enable(read_enable),
        .address(address),
        .instruction(instruction),
        .access_valid(access_valid),
        .access_error(access_error)
    );

    initial begin
        read_enable = 1'b0;
        address = 32'h0000_1000;
        #1;
        if (access_valid || access_error) $fatal(1, "disabled read should be idle");

        read_enable = 1'b1;
        address = 32'h0000_1000;
        #1;
        if (!access_valid || access_error || instruction !== 32'h00500093)
            $fatal(1, "first instruction read failed");

        address = 32'h0000_1004;
        #1;
        if (!access_valid || access_error || instruction !== 32'h00700113)
            $fatal(1, "second instruction read failed");

        address = 32'h0000_1002;
        #1;
        if (access_valid || !access_error)
            $fatal(1, "misaligned address was not rejected");

        address = 32'h0000_1010;
        #1;
        if (access_valid || !access_error)
            $fatal(1, "out-of-range address was not rejected");

        address = 32'h0000_0FFC;
        #1;
        if (access_valid || !access_error)
            $fatal(1, "address below base was not rejected");

        $display("PASS: Jon2 instruction memory smoke tests");
        $finish;
    end
endmodule
