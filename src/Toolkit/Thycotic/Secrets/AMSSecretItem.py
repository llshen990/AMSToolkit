class AMSSecretItem(dict):
    def __init__(self, field_id, item_value):
        dict.__init__(self, field_id=field_id, item_value=item_value)

