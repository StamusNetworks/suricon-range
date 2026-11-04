def domain_principals(groups: list, netbios: str) -> list:
    return [f"{netbios}\\{group}" for group in groups]


class FilterModule(object):
    def filters(self):
        return {
            "domain_principals": domain_principals,
        }
