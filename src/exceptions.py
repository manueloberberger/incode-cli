class IncodeError(Exception):
    """
    Base exception for Incode CLI.

    All custom exceptions in this application inherit from this class,
    allowing for broad exception catching when needed while still
    supporting specific exception handling.

    Example:
        try:
            api.login(user, password)
        except IncodeError as e:
            print(f"Incode error occurred: {e}")
    """
    pass


class LoginError(IncodeError):
    """
    Raised when authentication with the Incode system fails.

    Common causes:
        - Invalid username or password
        - Session expired or tokens not found
        - Network connectivity issues during login
        - Server-side authentication errors

    Troubleshooting:
        1. Verify username (Personalnummer) and password are correct
        2. Check network connectivity to dienstplan.k.roteskreuz.at
        3. Try logging in via web browser to verify account status
        4. If using VPN, ensure it's connected

    Example:
        try:
            api.login(username, password)
        except LoginError as e:
            print("Login failed. Please check your credentials.")
    """
    pass


class ApiError(IncodeError):
    """
    Raised when an API request to the Incode system fails.

    This exception indicates that communication with the server succeeded,
    but the request itself failed (e.g., non-200 status code, invalid response).

    Common causes:
        - HTTP error status codes (4xx, 5xx)
        - Invalid or expired session
        - Rate limiting
        - Server-side errors

    Example:
        try:
            duties = api.load_future_duties()
        except ApiError as e:
            print(f"Failed to load duties: {e}")
    """
    pass


class DataError(IncodeError):
    """
    Raised when parsing or data validation fails.

    This exception indicates that data received from the API could not
    be parsed or validated according to expected formats.

    Common causes:
        - Malformed JSON response
        - Missing required fields
        - Unexpected data types
        - Invalid date/time formats

    Example:
        try:
            parsed = parse_duty_response(raw_data)
        except DataError as e:
            print(f"Invalid data format: {e}")
    """
    pass
