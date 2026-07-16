import app
from werkzeug.test import Client

client = Client(app.app)
resp = client.post('/', data={'email': 'a@test.com', 'password': 'x'})
print(resp.status_code)
print(resp.data.decode('utf-8')[:100])
