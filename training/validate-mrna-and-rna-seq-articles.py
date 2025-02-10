import csv


def find_string(line, keywords):
    """
    Check if any of the keywords are present in the line.

    Args:
        line (iterable): An iterable containing items to be checked.
        keywords (list of str): A list of keywords to search for in the line.

    Returns:
        bool: True if any keyword from the list is found in the line, False otherwise.
    """
    return any(keyword in str(item).lower() for keyword in keywords for item in line)


def main():
    """
    Main function to process a CSV file and check for specific keywords in each line.
    We need RNA-related and non-RNA-related articles that mention "mrna" or "rna-seq".
    """
    try:
        with open("check_abstracts.csv", mode="r", encoding="utf-8") as file:
            read_csv = csv.reader(file)
            keyword = [
                "non-coding", "noncoding", "ncrna", "rrna", "lncrna", "sncrna", "mirna", "trna", "rbp", "snrna", "pirna",
                "lincrna", "scrna", "pre-mirna", "riboswitch"
            ]

            for line_number, line in enumerate(read_csv, start=1):
                if line_number == 1:
                    continue
                elif 2 <= line_number <= 101:
                    if not find_string(line, ["mrna"]):
                        print(f"Line {line_number} does not contain 'mrna': {line}")
                elif 102 <= line_number <= 201:
                    if not find_string(line, ["mrna"]) or find_string(line, keyword):
                        print(f"Please check line {line_number}: {line}")
                elif 202 <= line_number <= 301:
                    if not find_string(line, ["rna-seq"]):
                        print(f"Line {line_number} does not contain 'rna-seq': {line}")
                else:
                    if not find_string(line, ["rna-seq"]) or find_string(line, keyword):
                        print(f"Please check line {line_number}: {line}")

    except Exception as e:
        print(f"Oops! We've had a problem: {e}")


if __name__ == "__main__":
    main()