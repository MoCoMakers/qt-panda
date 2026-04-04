import math

def generate_log_table(size=32784):
    log_table = []

    for i in range(1, size + 1):
        # Example logic to generate new log values
        log_value = int(math.log(i) * 10000)
        log_table.append(log_value)

    return log_table

def generate_verilog(log_table):
    verilog_code = [
        "module LogTable #(parameter SIZE = 32784) (",
        "    input  [14:0] addr,",
        "    output reg [19:0] data",
        ");",
        "",
        "    always @* begin",
        "        case (addr)"
    ]

    for i, value in enumerate(log_table):
        verilog_code.append(f"            {i}: data = 20'd{value};")

    verilog_code.append("            default: data = 20'd0;")
    verilog_code.append("        endcase")
    verilog_code.append("    end")
    verilog_code.append("endmodule")

    return "\n".join(verilog_code)

def save_verilog_to_file(verilog_code, file_name="log_table.v"):
    with open(file_name, "w") as f:
        f.write(verilog_code)

def main():
    size = 32784
    log_table = generate_log_table(size)
    verilog_code = generate_verilog(log_table)
    save_verilog_to_file(verilog_code)
    print(f"Verilog code for log table with {size} entries has been generated and saved to 'log_table.v'.")

if __name__ == "__main__":
    main()
