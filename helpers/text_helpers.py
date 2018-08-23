def always_str(txt):
    return txt if isinstance(txt, str) else txt.encode('utf-8')