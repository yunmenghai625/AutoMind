import getpass

from apps.api.auth.service import hash_admin_password


def main() -> int:
    password = getpass.getpass("New administrator password: ")
    confirmation = getpass.getpass("Confirm administrator password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    print(hash_admin_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
