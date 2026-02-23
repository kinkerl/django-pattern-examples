import attr


@attr.s
class AbstractBackend:
    def call(self):
        raise NotImplementedError


@attr.s
class FirstBackend(AbstractBackend):
    extra = attr.ib(converter=str)

    def call(self):
        return f"First {self.extra}"


@attr.s
class SecondBackend(AbstractBackend):
    other_extra = attr.ib(converter=str)

    def call(self):
        return f"Second {self.other_extra}"
