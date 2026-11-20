KBPS_PER_UNIT = {
    "m": 1_000,
    "g": 1_000_000,
    "t": 1_000_000_000,
}


def speed_kbps_from_type(interface_type: str) -> int | None:
    """Return the speed implied by a NetBox Ethernet interface type such as "25gbase-x-sfp28", or None."""
    rate, separator, _ = interface_type.partition("base-")
    if separator == "" or rate == "":
        return None

    if rate[-1] in ("g", "t"):
        unit = rate[-1]
        number = rate[:-1]
    else:
        unit = "m"
        number = rate

    try:
        value = float(number)
    except ValueError:
        return None
    return int(value * KBPS_PER_UNIT[unit])


def interface_speed_kbps(interface) -> int | None:
    """Return the interface speed in kbit/s from its speed field, falling back to its type; None when unknown."""
    if interface.speed:
        return interface.speed
    return speed_kbps_from_type(interface.type)
