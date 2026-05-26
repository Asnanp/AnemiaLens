import urllib.request, json
url = 'https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=eyelid%20pull%20down%20OR%20lower%20eyelid&srnamespace=6&format=json&srlimit=50'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    urls = []
    for item in data['query']['search']:
        title = item['title']
        if not title.lower().endswith(('.jpg', '.jpeg', '.png')): continue
        
        # Get image URL
        title_url = title.replace(' ', '_')
        image_url_req = urllib.request.Request(f'https://en.wikipedia.org/w/api.php?action=query&titles={title_url}&prop=imageinfo&iiprop=url&format=json', headers={'User-Agent': 'Mozilla/5.0'})
        image_response = urllib.request.urlopen(image_url_req)
        image_data = json.loads(image_response.read())
        pages = image_data['query']['pages']
        for page_id in pages:
            if 'imageinfo' in pages[page_id]:
                urls.append(pages[page_id]['imageinfo'][0]['url'])
                print(pages[page_id]['imageinfo'][0]['url'])
except Exception as e:
    print(e)
