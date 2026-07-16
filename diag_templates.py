import os
p = r'C:\PROJECT\AIProject'
print('CWD exists:', os.path.exists(p))
print('List root:')
print(os.listdir(p))
pt = os.path.join(p, 'templates')
print('templates exists:', os.path.exists(pt))
if os.path.exists(pt):
    print('templates listing:', os.listdir(pt))
else:
    print('templates missing')
