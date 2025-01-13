# Mapping of trade policy to storefront site name for pulse purposes (not generally used for regular responses)
def storefront_domain_for_trade_policy(trade_policy: str):
    match trade_policy:
        case "2":
            return "menshealth.com"
        case "3":
            return "womenshealthmag.com"
        case "4":
            return "cosmopolitan.com"
        case "5":
            return "harpersbazaar.com"
        case "6":
            return "prevention.com"
        case _:
            return ""
