from utilities.choices import ChoiceSet


class MirrorSessionStatusChoices(ChoiceSet):
    PLANNED = "planned"
    ACTIVE = "active"

    CHOICES = [
        (PLANNED, "Planned", "cyan"),
        (ACTIVE, "Active", "green"),
    ]


class DestinationKindChoices(ChoiceSet):
    INTERFACE = "interface"
    GRE = "gre"
    CPU = "cpu"

    CHOICES = [
        (INTERFACE, "Local interface", "blue"),
        (GRE, "GRE tunnel", "purple"),
        (CPU, "CPU", "gray"),
    ]


class MirrorDirectionChoices(ChoiceSet):
    RX = "rx"
    TX = "tx"
    BOTH = "both"

    CHOICES = [
        (RX, "Receive (rx)", "blue"),
        (TX, "Transmit (tx)", "orange"),
        (BOTH, "Both", "purple"),
    ]


class ExpiryWarningChoices(ChoiceSet):
    LONG = "long"
    LONG_HIGH_SPEED = "long-high-speed"

    CHOICES = [
        (LONG, "Long expiry", "yellow"),
        (LONG_HIGH_SPEED, "Long expiry on high-speed source", "red"),
    ]
