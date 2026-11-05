module jon2_pc (
    input logic clk,
    input logic reset_n,
    input logic hold,
    input logic redirect,
    input logic [31:0] redirect_addr,
    output logic [31:0] pc
);
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            pc <= 32'h00000000;
        else if (!hold) begin
            if (redirect)
                pc <= redirect_addr;
            else
                pc <= pc + 32'd4;
        end
    end
endmodule
