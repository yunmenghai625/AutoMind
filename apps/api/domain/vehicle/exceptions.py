from uuid import UUID


class VehicleDomainError(Exception):
    pass


class VehicleNotFoundError(VehicleDomainError):
    def __init__(self, vehicle_id: UUID) -> None:
        super().__init__(f"Vehicle {vehicle_id} was not found")
        self.vehicle_id = vehicle_id


class VehicleValidationError(VehicleDomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class VehicleVersionConflictError(VehicleDomainError):
    def __init__(self, expected_version: int, current_version: int) -> None:
        super().__init__(
            "Vehicle state version conflict: "
            f"expected {expected_version}, current {current_version}"
        )
        self.expected_version = expected_version
        self.current_version = current_version


class VehicleStorageError(VehicleDomainError):
    pass
