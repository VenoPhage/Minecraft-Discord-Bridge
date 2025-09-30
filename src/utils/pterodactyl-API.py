import requests

headers = {
    "Authorization": "Bearer ptla_DPtY4MtrLZlP1AohoMK0KG8MOxe2dydIOJswx00bShw",
    "Accept": "Application/vnd.pterodactyl.v1+json",
}

params = {"include": "eggs"}

response = requests.get(
    "https://games.bisecthosting.com/api/application/nests",
    headers=headers,
    params=params,
)
print(response.json())
