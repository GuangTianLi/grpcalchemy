class BaseField:
    # TODO Use descriptors
    name = ""
    type_name = ""

    def __str__(self) -> str:
        return f"{self.type_name} {self.name}"


class StringField(BaseField):
    type_name = "string"


class Int32Field(BaseField):
    type_name = "int32"


class Int64Field(BaseField):
    type_name = "int64"


class BooleanField(BaseField):
    type_name = "bool"


class BytesField(BaseField):
    type_name = "bytes"


class EmptyFile:
    pass


class ReferenceField(BaseField):
    def __init__(self, key_type, value_type=None):
        self.key_type = key_type
        self.type_name = self.get_type_name(key_type)

        if value_type:
            self.value_type = value_type
            self.value_type_name = self.get_type_name(value_type)
        else:
            self.value_type = EmptyFile

    def get_type_name(self, field):
        if issubclass(field, BaseField):
            return field.type_name
        else:
            return field.__name__


class ListField(ReferenceField):
    def __str__(self) -> str:
        return f"repeated {super().__str__()}"


class MapField(ReferenceField):
    def __str__(self) -> str:
        return f"map<{self.type_name}, {self.value_type_name}> {self.name}"
