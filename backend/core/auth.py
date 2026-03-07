import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password using bcrypt.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if the password is correct, False otherwise
    """
    return bcrypt.checkpw(
        bytes(plain_password, encoding="utf-8"),
        bytes(hashed_password, encoding="utf-8"),
    )

def get_password_hash_str(password: str) -> str:
    """Hash a password using bcrypt and return the hashed password as a string.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password as a string
    """
    return bcrypt.hashpw(
        bytes(password, encoding="utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")