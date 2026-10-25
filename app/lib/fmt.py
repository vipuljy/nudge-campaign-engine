"""Number formatting for Indian readers: ₹2,43,600 and ₹2.44 lakh, plus percentages and points.
Negative numbers use a real minus sign (−), not a hyphen."""

MINUS = '−'


def _group_indian(n: int) -> str:
    # 243600 -> "2,43,600": last three digits, then groups of two
    s = str(abs(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    if head:
        parts.insert(0, head)
    return ','.join(parts) + ',' + tail


def inr(x: float, decimals: int = 0) -> str:
    """Full rupee amount with Indian grouping: ₹2,43,600 / −₹0.47."""
    sign = MINUS if x < 0 else ''
    if decimals:
        whole, frac = f'{abs(x):.{decimals}f}'.split('.')
        return f'{sign}₹{_group_indian(int(whole))}.{frac}'
    return f'{sign}₹{_group_indian(int(round(abs(x))))}'


def rs(x: float) -> str:
    """Short rupee amount for headlines: ₹2.44 lakh, ₹1.2 crore, ₹3,300 below one lakh."""
    sign, a = (MINUS if x < 0 else ''), abs(x)
    if a >= 1e7:
        return f'{sign}₹{a / 1e7:.2f} crore'
    if a >= 1e5:
        return f'{sign}₹{a / 1e5:.2f} lakh'
    if a >= 100:
        return f'{sign}₹{_group_indian(int(round(a)))}'
    if a >= 10:
        return f'{sign}₹{a:.0f}'                           # whole rupees, like the larger amounts
    return f'{sign}₹{a:.2f}'.replace('.00', '')          # paise only for small amounts (₹1.02 per message, −₹0.47)


def count(n: float) -> str:
    """Whole count with Indian grouping: 1,00,000."""
    return (MINUS if n < 0 else '') + _group_indian(int(round(abs(n))))


def pct(x: float, decimals: int = 0) -> str:
    return f'{100 * x:.{decimals}f}%'


def pts(x: float, decimals: int = 1, sign: bool = True) -> str:
    """A change in a buy rate, in percentage points: 0.033 -> +3.3 pts."""
    return f'{100 * x:{"+" if sign else ""}.{decimals}f} pts'.replace('-', MINUS)


def cost(x: float) -> str:
    """Cost per contact: ₹0.01, ₹0.10, ₹1.02, ₹5 (paise always shown below ₹10, whole rupees when exact)."""
    return f'₹{x:g}' if float(x).is_integer() else f'₹{x:.2f}'


def signed(x: float, decimals: int = 1, unit: str = '') -> str:
    """+10.7% / −6.5%: explicit sign with a real minus."""
    return f'{"+" if x >= 0 else MINUS}{abs(x):.{decimals}f}{unit}'
