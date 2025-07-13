#!/usr/bin/env python3
"""
Utility to retrieve the Windows host's private IP address from WSL.
This script retrieves the Windows host's private IP address from WSL using the `ip route` command.
It checks if the IP is a private address (10.x.x.x, 172.16.x.x - 172.31.x.x, or 192.168.x.x)
and returns it.
In WSL, the windows host IP is typically the default gateway.
"""

import subprocess
import re


def get_windows_host_ip() -> str | None:
    """
    Retrieves the Windows host's private IP address from within WSL.

    This function executes the `ip route` command in the WSL environment,
    parses its output to find the default gateway's IP address, and then
    validates if this IP address falls within the private IP address ranges.

    Returns:
        str | None: The private IP address of the Windows host if found and
                    valid, otherwise None.
    """
    try:
        # Run `ip route` and get output, using text=True for automatic decoding.
        result = subprocess.check_output(["ip", "route"], text=True, stderr=subprocess.DEVNULL)

        # Look for the 'default via' line, which usually contains the host IP in WSL.
        for line in result.splitlines():
            if line.startswith("default via"):
                parts = line.split()
                if len(parts) >= 3:
                    ip = parts[2]
                    # Check if the found IP is a private address.
                    is_private = (
                        # Manual regex-based private IP check
                        # Check for 10.0.0.0/8
                        # Check for 172.16.0.0/12
                        # Check for 192.168.0.0/16
                        re.match(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)
                        or re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}$", ip)
                        or re.match(r"^192\.168\.\d{1,3}\.\d{1,3}$", ip)
                    )
                    if is_private:
                        return ip  # Found a valid private IP for the default route.
    except (FileNotFoundError, subprocess.CalledProcessError):
        # This can happen if 'ip' command is not available or fails.
        # Silently fail and return None, as the caller should handle the absence of an IP.
        return None

    # If no 'default via' line with a private IP was found.
    return None


if __name__ == "__main__":
    # Example usage when the script is run directly.
    windows_ip = get_windows_host_ip()
    if windows_ip:
        print(f"Windows Host IP: {windows_ip}")
    else:
        print("Failed to find a valid private IP for the Windows host.")
