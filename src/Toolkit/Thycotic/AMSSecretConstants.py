_store = [
    {'type': 'secret_type', 'name': 'TYPE_PGP', 'id': 6052, 'value': 'PGP'},
    {'type': 'secret_type', 'name': 'TYPE_PASSWORD', 'id': 2, 'value': 'password'},
    {'type': 'secret_type', 'name': 'TYPE_UNIX_ACCOUNT_SSH', 'id': 6007, 'value': 'Unix_Account_SSH'},
    {'type': 'folder', 'name': 'AMS_Global', 'id': 5184, 'value': 'AMS_Global'},
    {'type': 'folder', 'name': 'AMS_USOnly', 'id': 5185, 'value': 'AMS_USOnly'}
]

# _test_store = [
#     {'type': 'folder', 'name': 'TEST_Global', 'id': 23357, 'value': 'TEST_Global'},
#     {'type': 'folder', 'name': 'TEST_USOnly', 'id': 23358, 'value': 'TEST_USOnly'}
# ]
#
# _store.extend(_test_store)


def name_to_id(name):
    """find id based on name"""
    for obj in _store:
        if obj['name'] == str(name):
            return obj['id']


def id_to_name(thyco_id):
    """find name based on id"""
    for obj in _store:
        if obj['id'] == int(thyco_id):
            return obj['name']


def id_to_value(thyco_id):
    """find display name based on id"""
    for obj in _store:
        if obj['id'] == int(thyco_id):
            return obj['value']


def name_to_value(name):
    """find string display value for a name"""
    for obj in _store:
        if obj['name'] == str(name):
            return obj['value']


def value_to_name(value):
    """find name from a display value"""
    for obj in _store:
        if obj['value'] == str(value):
            return obj['name']


def value_to_id(value):
    """ find id from value"""
    for obj in _store:
        if obj['value'] == str(value):
            return obj['id']


def all_folder_names():
    """list all folder names"""
    all_folders = filter(lambda obj: obj['type'] == 'folder', _store)
    return list(map(lambda folder: folder['name'], all_folders))


def all_secret_types():
    """list all secret types"""
    secret_types = filter(lambda obj: obj['type'] == 'secret_type', _store)
    return list(map(lambda secret_type: secret_type['value'], secret_types))


TYPE_PGP = name_to_value("TYPE_PGP")
TYPE_PASSWORD = name_to_value("TYPE_PASSWORD")
TYPE_UNIX_ACCOUNT_SSH = name_to_value("TYPE_UNIX_ACCOUNT_SSH")

SECRET_SEVER_ROOT = 'https://securevault.sas.com/secretserver'
SECRET_SERVER_API = SECRET_SEVER_ROOT + '/api/v1'
