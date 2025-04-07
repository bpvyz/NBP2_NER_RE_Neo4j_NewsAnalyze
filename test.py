from bs4 import BeautifulSoup
soup = BeautifulSoup('<p>test1</p><p>test2</p>', 'html.parser')
for s in soup.find_all('p'):
    print(s.get_text())
