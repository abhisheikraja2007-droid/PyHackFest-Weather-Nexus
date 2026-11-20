import requests
import traceback


try:
    r = requests.get('http://localhost:8000/api/aqi/?city=Delhi&y1=2015&y2=2024')
    if r.status_code == 200:
        print("Success:", r.json())
    else:
        text = r.text
        start = text.find('exception_value">')
        if start != -1:
            end = text.find('</pre>', start)
            print("EXCEPTION VALUE:\n", text[start+17:end])
        else:
            print("No exception_value tag found. First 500 chars:\n", text[:500])

except Exception as e:
    traceback.print_exc()
