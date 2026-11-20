
def load(filename):
    data = {}
    current_section = data
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Section
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip()
                data[section_name] = {}
                current_section = data[section_name]
                continue
            
            # Key-Value pair
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove inline comments (naive)
                # Check for comment start not inside quotes
                in_quote = False
                quote_char = ''
                comment_idx = -1
                for i, char in enumerate(value):
                    if char in ["'", '"']:
                        if not in_quote:
                            in_quote = True
                            quote_char = char
                        elif char == quote_char:
                            in_quote = False
                    elif char == '#' and not in_quote:
                        comment_idx = i
                        break
                
                if comment_idx != -1:
                    value = value[:comment_idx].strip()
                
                # Parse types
                current_section[key] = _parse_value(value)
                
    return data

def _parse_value(value):
    # Boolean
    if value == 'true':
        return True
    if value == 'false':
        return False
    
    # Strings
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
        
    # Numbers
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value # Return as string if nothing else matches
