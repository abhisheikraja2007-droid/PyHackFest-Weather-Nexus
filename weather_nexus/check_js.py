import re, subprocess
html = open('d:/hacathons/SEM 2/PyHackFest/weather_nexus/analytics/templates/analytics/dashboard.html', encoding='utf-8').read()
js = re.search(r'<script>(.*?)</script>', html, re.S).group(1)
open('test_js.js', 'w', encoding='utf-8').write(js)
subprocess.run(['node', '-c', 'test_js.js'])
