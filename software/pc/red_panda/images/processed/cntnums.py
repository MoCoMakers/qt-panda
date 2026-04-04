import sys
import re

def count_numbers(filename):
    with open(filename, "r") as f:
        text = f.read()

    # split on commas or whitespace
    numbers = re.split(r"[,\s]+", text.strip())

    # remove empty entries
    numbers = [n for n in numbers if n]

    return len(numbers)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python count_numbers.py <file>")
        sys.exit(1)

    filename = sys.argv[1]
    count = count_numbers(filename)
    print(f"Number of values: {count}")
