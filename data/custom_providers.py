from mimesis.providers import BaseProvider


class EmailProvider(BaseProvider):
    class Meta:
        name = "test_email"

    def get_random_value(self) -> str:
        """
        create random email like test_user_rundomNumber@companyhost.local
        """
        return f"test_user_{self.random.randint(1, 100_000)}@companyhost.local"


class PasswordProvider(BaseProvider):
    class Meta:
        name = "test_password"

    _UPPERCASE: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    _LOWERCASE: str = "abcdefghijklmnopqrstuvwxyz"
    _DIGITS: str = "0123456789"
    _SPECIAL: str = "!.,-_@#$%^&"
    _ALL: str = _UPPERCASE + _LOWERCASE + _DIGITS + _SPECIAL

    def _is_valid(self, password: str) -> bool:
        """Проверяет соответствие пароля всем требованиям."""
        return (
            8 <= len(password) <= 40
            and any(c in self._UPPERCASE for c in password)
            and any(c in self._LOWERCASE for c in password)
            and any(c in self._DIGITS for c in password)
            and any(c in self._SPECIAL for c in password)
        )

    def get_random_value(self, min_len: int = 10, max_len: int = 20) -> str:
        """
        Генерирует пароль через mimesis: 8–40 символов, латиница,
        строчные и заглавные, цифры, спецсимволы !.,-_@#$%^&.
        Повторяет генерацию, пока пароль не пройдёт валидацию.
        """
        while True:
            length: int = self.random.randint(min_len, max_len)
            chars: list[str] = [self.random.choice(self._ALL) for _ in range(length)]
            password: str = "".join(chars)
            if self._is_valid(password):
                return password
