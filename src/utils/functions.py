import toml

def getRconConfig():
    with open ('config.toml') as f:
        config = toml.load(f)
    host = config['minecraft']['rcon']['host']
    port = config['minecraft']['rcon']['port']
    password = config['minecraft']['rcon']['password']

    if host == '0':
        host = config['minecraft']['host']
    
    return {'host':host, 'port':port, 'password':password}

def getSFTPConfig():
    with open ('config.toml') as f:
        config = toml.load(f)
    host = config['minecraft']['sftp']['host']
    port = config['minecraft']['sftp']['port']
    username = config['minecraft']['sftp']['username']
    password = config['minecraft']['sftp']['password']

    return {'host':host, 'port':port, 'username':username, 'password':password}