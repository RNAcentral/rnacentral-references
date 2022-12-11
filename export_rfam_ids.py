import csv
import requests


def main():
    """
    Extracts the ids from a csv file to submit to RNAcentral-references.
    :return: None
    """
    url = 'http://45.88.80.122:8080/api/submit-job'

    with open("Rfam Families and Aliases - Sheet1.csv", "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader)
        for line in csv_reader:
            for item in line[2:]:
                if item:
                    try:
                        data = {'id': item.rstrip()}
                        requests.post(url, json=data)
                    except Exception as e:
                        print(e)


if __name__ == "__main__":
    main()
