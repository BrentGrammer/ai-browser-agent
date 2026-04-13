import re
import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to reach projectroot/
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")

sensitive_data = [LOGIN_PASSWORD, LOGIN_USERNAME]

def sanitize_sensitive_text(text: str) -> str:
    """Mask common secrets like passwords, API keys, etc."""
    if not text:
        return text
    
    # Mask passwords
    text = re.sub(r'(password|passwd|pwd)\s*[:=]\s*["\']?([^"\']+)["\']?', 
                  r'\1: [REDACTED]', text, flags=re.IGNORECASE)
    
    # Mask email + password combinations in one go
    text = re.sub(r'password[:=]\s*["\']?[^"\']+["\']?', '[REDACTED]', text, flags=re.IGNORECASE)
    
    # Optional: mask any long string that looks like a password (8+ chars with mixed types)
    text = re.sub(r'(?i)(password|pass|pw)\s*[:=]\s*\S{8,}', r'\1: [REDACTED]', text)

    for sensitive_str in sensitive_data:
        if not sensitive_str:
            raise Exception("A environment var or sensitive string was not found")
        text = re.sub(f"{re.escape(sensitive_str)}", "[REDACTED]", text)
    
    return text