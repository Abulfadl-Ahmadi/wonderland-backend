import re
from django.core.exceptions import ValidationError

# Persian + Arabic-Indic digits to English digits
_DIGIT_MAP = str.maketrans(
    {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)

# Iranian mobile numbers:
# National: 09xxxxxxxxx (11 digits)
# Local:    9xxxxxxxxx  (10 digits)
# E.164:   +989xxxxxxxxx (13 chars including +)
_IR_MOBILE_LOCAL_RE = re.compile(r"^9\d{9}$")  # 10 digits, starts with 9
_IR_MOBILE_NATIONAL_RE = re.compile(r"^09\d{9}$")  # 11 digits, starts with 09
_IR_MOBILE_E164_RE = re.compile(r"^\+989\d{9}$")  # +98 + 10 digits starting 9


def normalize_iran_mobile(raw: str) -> str:
    """
    Normalize Iranian mobile numbers to national format: 09xxxxxxxxx

    Accepts:
      - +989xxxxxxxxx
      - 989xxxxxxxxx
      - 09xxxxxxxxx
      - 9xxxxxxxxx
      - Persian/Arabic digits
      - With separators like spaces, -, ()
    Returns:
      - 09xxxxxxxxx
    Raises ValidationError if invalid.
    """
    if raw is None:
        raise ValidationError("Phone number is required.")

    s = str(raw).strip()
    if not s:
        raise ValidationError("Phone number is required.")

    # Convert Persian/Arabic digits to English
    s = s.translate(_DIGIT_MAP)

    # Remove separators
    s = re.sub(r"[\s\-_().]+", "", s)

    # Convert 00 prefix to +
    if s.startswith("00"):
        s = "+" + s[2:]

    # Case 1: +989xxxxxxxxx
    if s.startswith("+98"):
        s = s[3:]  # remove +98
        if s.startswith("0"):
            s = s[1:]  # remove accidental extra 0
        if not _IR_MOBILE_LOCAL_RE.fullmatch(s):
            raise ValidationError("Invalid Iranian mobile number.")
        return "0" + s

    # Case 2: 989xxxxxxxxx
    if s.startswith("98"):
        s = s[2:]
        if s.startswith("0"):
            s = s[1:]
        if not _IR_MOBILE_LOCAL_RE.fullmatch(s):
            raise ValidationError("Invalid Iranian mobile number.")
        return "0" + s

    # Case 3: 09xxxxxxxxx
    if _IR_MOBILE_NATIONAL_RE.fullmatch(s):
        return s

    # Case 4: 9xxxxxxxxx
    if _IR_MOBILE_LOCAL_RE.fullmatch(s):
        return "0" + s

    raise ValidationError("Invalid Iranian mobile number.")
