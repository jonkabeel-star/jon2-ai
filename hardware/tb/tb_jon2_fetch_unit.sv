`timescale 1ns/1ps
module tb_jon2_fetch_unit;
    logic clk = 1'b0;
    logic reset_n = 1'b1;
    logic hold = 1'b0;
    logic redirect = 1'b0;
    logic [31:0] redirect_addr = 32'h0;
    logic [31:0] pc;
    logic [31:0] instruction;
    logic instruction_valid;
    logic instruction_error;

    always #5 clk = ~clk;

    jon2_fetch_unit #(
        .INSTRUCTION_WORDS(4),
        .RESET_PC(32'h0000_1000),
        .INSTRUCTION_BASE_ADDR(32'h0000_1000),
        .INIT_FILE("hardware/tb/fixtures/jon2_instruction_memory.hex")
    ) dut (
        .clk(clk), .reset_n(reset_n), .hold(hold),
        .redirect(redirect), .redirect_addr(redirect_addr),
        .pc(pc), .instruction(instruction),
        .instruction_valid(instruction_valid),
        .instruction_error(instruction_error)
    );

    initial begin
        #1 reset_n = 1'b0;
        #1;
        if (pc !== 32'h0000_1000) $fatal(1, "configured PC reset failed");
        reset_n = 1'b1;
        #1;
        if (!instruction_valid || instruction_error ||
            instruction !== 32'h00500093)
            $fatal(1, "reset-address instruction fetch failed");

        @(posedge clk); #1;
        if (pc !== 32'h0000_1004 || !instruction_valid ||
            instruction !== 32'h00700113)
            $fatal(1, "sequential fetch failed");

        hold = 1'b1;
        @(posedge clk); #1;
        if (pc !== 32'h0000_1004)
            $fatal(1, "hold did not preserve PC");

        hold = 1'b0;
        redirect = 1'b1;
        redirect_addr = 32'h0000_1008;
        @(posedge clk); #1;
        redirect = 1'b0;
        if (pc !== 32'h0000_1008 || !instruction_valid ||
            instruction !== 32'h002081B3)
            $fatal(1, "redirected fetch failed");

        $display("PASS: Jon2 fetch unit smoke tests");
        $finish;
    end
endmodule
