`timescale 1ns/1ps
module tb_jon2_alu;
    logic [31:0] a, b;
    logic [3:0] alu_ctrl;
    logic [31:0] result;
    logic zero;

    jon2_alu dut(.a(a), .b(b), .alu_ctrl(alu_ctrl), .result(result), .zero(zero));

    task automatic check(input logic [3:0] op, input logic [31:0] x,
                         input logic [31:0] y, input logic [31:0] expected);
        begin
            alu_ctrl=op; a=x; b=y; #1;
            if (result !== expected) begin
                $display("FAIL ALU op=%0d a=%h b=%h got=%h expected=%h",op,x,y,result,expected);
                $fatal(1);
            end
        end
    endtask

    initial begin
        check(4'd0,32'd7,32'd5,32'd12);
        check(4'd1,32'd7,32'd5,32'd2);
        check(4'd2,32'hF0F0,32'h0FF0,32'h00F0);
        check(4'd3,32'hF000,32'h00F0,32'hF0F0);
        check(4'd4,32'hAAAA,32'h0F0F,32'hA5A5);
        check(4'd5,32'hFFFFFFFF,32'd1,32'd1);
        check(4'd6,32'hFFFFFFFF,32'd1,32'd0);
        check(4'd7,32'd3,32'd4,32'd48);
        check(4'd8,32'd48,32'd2,32'd12);
        check(4'd9,32'hFFFFFFF0,32'd2,32'hFFFFFFFC);
        check(4'd0,32'd0,32'd0,32'd0);
        if (zero !== 1'b1) $fatal(1,"ALU zero flag failed");
        $display("PASS: Jon2 ALU smoke tests");
        $finish;
    end
endmodule
