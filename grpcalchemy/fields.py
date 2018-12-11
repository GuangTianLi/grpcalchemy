class BaseField:
    # TODO Use descriptors
    type_name = ""

    def __init__(self, name=None):
        self._name = name

    def __set__(self, instance, value):
        instance.__dict__[self._name] = value

    def __get__(self, instance, owner):
        if not instance:
            return f"{self.type_name} {self._name}"
        else:
            return instance.__dict__.get(self._name)


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

        super().__init__()

    def get_type_name(self, field):
        if issubclass(field, BaseField):
            return field.type_name
        else:
            return field.__name__


class ListField(ReferenceField):
    def __get__(self, instance, owner):
        if not instance:
            return f"repeated {self.type_name} {self._name}"
        else:
            return instance.__dict__.get(self._name)


class MapField(ReferenceField):
    def __get__(self, instance, owner):
        if not instance:
            return f"map<{self.type_name}, {self.value_type_name}> {self._name}"
        else:
            return instance.__dict__.get(self._name)
