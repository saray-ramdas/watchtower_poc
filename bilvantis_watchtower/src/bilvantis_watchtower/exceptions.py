class WatchtowerError(RuntimeError):
    pass


class SecurityResponseError(WatchtowerError):
    pass


class PIIDetectionError(WatchtowerError):
    pass
