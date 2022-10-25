import requests
import base64

url = "https://rm12filereader.rentmanager.com/files/get/?EID=bobai&FKey=K0xtSmxCZ2pJTW89N3h2VThhYUREQ0lDdC9DT295Y05pZz09VjRpUTVQSWVNOGFpZ21rUVg5dlhhL3ZadG5yVC9jUEU1RG55aWJGcERVSkNwNkdRM0M2cHNVRUd2c0xXYkNZeUNiOUtvUUd5bFBYdmd3RzFZcm1qRlBseDhzTjhqNnhrSUNCcDdhTE45bk9lS0IvaWNJMkQrR25wWUo3ck9TQkJDZndyQzY2Mm9SdFUvdHk5dHpvdTdXdjBLU2hBSlFpRGhKcHlDSnNLUSt3TGlsQlkxdmI5R2hlL2x6c2xuZnd5TmlrN0ZZSlhsa0RoNjJlVFMwQWpoSTVDSlRHQXRYT2o2TUd5ckxRYXlZUT0="

payload={}
headers = {}

r = requests.request("GET", url, headers=headers, stream=True, data=payload)

content_size = int(r.headers['content-length'])

bytes_downloaded = 0

with open('abc.png', 'wb') as file_handle:
    for chunk in r.iter_content(chunk_size=content_size):
        if chunk:
            bytes_downloaded += len(chunk)
            file_handle.write(chunk)
            file_handle.flush()

with open("abc.png", "rb") as f:
    im_bytes = f.read()        
    im_b64 = base64.b64encode(im_bytes).decode("utf8")

print(im_b64)