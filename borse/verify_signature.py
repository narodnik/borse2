import ed25519

class PublicKey:

    def __init__(self, public_key):
        self._key = ed25519.VerifyingKey(public_key)

    def verify(self, message, signature):
        assert isinstance(message, str)
        assert isinstance(signature, str)

        try:
            self._key.verify(signature, message.encode(),
                             encoding='base64')
        except (ed25519.BadSignatureError, AssertionError):
            return False

        return True

