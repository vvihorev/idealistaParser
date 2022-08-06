import requests


def generate_url(numPage=1):
    base_idealista_url = "https://api.idealista.com/3.5/it/search"
    search_parameters = {
        "center": "45.469,9.182",
        "distance": "5500",
        "propertyType": "homes",
        "operation": "rent",
        "locale": "en",
        "locationId": "0-EU-IT-MI-01-001-135",
        "sinceDate": "T",
        "maxPrice": "1300",
        "bedroom": "2",
        "maxItems": "50",
        "numPage": f"{numPage}",
        "order": "price",
        "sort": "desc"
    }
    response = requests.post(base_idealista_url, data=search_parameters)
    return base_idealista_url + '?' + response.request.body.replace("%2C", ",")


def generate_command(url, write_to_file=False):
    """Generates the query command for the pydealista API"""
    command = "python3 pydealista.py " + f'{url}'
    if write_to_file:
        with open('sample_command', 'w') as file:
            file.write("#!/usr/bin/bash\n")
            file.write(command)
    return command


if __name__ == "__main__":
    res = generate_command(generate_url())
    print(res)
