with open('.env', 'rb') as f:
    raw = f.read(20)
print('First bytes hex:', raw.hex())
print('Has UTF-8 BOM:', raw[:3] == b'\xef\xbb\xbf')

with open('.env', encoding='utf-8-sig') as f:
    for line in f:
        line = line.strip()
        if line.startswith('LMS_TOKEN='):
            token = line[len('LMS_TOKEN='):].strip()
            print('Token found, length:', len(token))
            print('First 20 chars:', repr(token[:20]))
            break
    else:
        print('LMS_TOKEN not found')
