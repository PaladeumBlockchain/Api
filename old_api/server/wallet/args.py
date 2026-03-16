from webargs import fields, validate

history_args = {
    "addresses": fields.List(fields.Str, missing=[], validate=validate.Length(min=1, max=20)),
    "count": fields.Int(missing=100, validate=lambda val: val > 0 and val <= 500),
    "before": fields.Str(missing=None),
    "after": fields.Str(missing=None)
}

addresses_args = {
    "addresses": fields.List(fields.Str, missing=[], validate=validate.Length(min=1, max=500))
}

broadcast_args = {
    "raw": fields.Str(required=True)
}

utxo_args = {
    "outputs": fields.List(fields.Dict, missing=[])
}
