"""psql adapter placeholder."""


class PSQLAdapter:
    def get(self, symbol: str):
        raise NotImplementedError("psql adapter not implemented yet")

    def set(self, symbol: str, value):
        raise NotImplementedError("psql adapter not implemented yet")

    def delete(self, symbol: str):
        raise NotImplementedError("psql adapter not implemented yet")

    def list_symbols(self):
        return []
