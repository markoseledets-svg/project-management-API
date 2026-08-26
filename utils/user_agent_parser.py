from user_agents import parse

def parse_user_agent(ua_data: str) -> dict:
    if ua_data == "Unknown Device":
        return {'device_type': ua_data}
    ua_parsed_str = parse(ua_data)
    if ua_parsed_str.is_mobile:
        device_type = "Mobile"
    elif ua_parsed_str.is_tablet:
        device_type = "Tablet"
    elif ua_parsed_str.is_pc:
        device_type = "PC"
    elif ua_parsed_str.is_bot:
        device_type = "Bot/Crawler"
    else:
        device_type = "Unknown Device"
    browser_data = f'{ua_parsed_str.browser.family} {ua_parsed_str.browser.version_string}'
    os_data = f'{ua_parsed_str.os.family} {ua_parsed_str.os.version_string}'
    device_model = ua_parsed_str.device.family
    return {
        'device_type': device_type,
        'browser_data': browser_data if browser_data != 'Other' else 'Unknown browser',
        'os_data': os_data if os_data != 'Other' else 'Unknown OS',
        'device_model': device_model if device_model != 'Other' else 'Unknown device model'
    }