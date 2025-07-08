# Quick test to understand the string sorting issue

dept1 = "Department of Building and Real Estate"
dept2 = "Department of Building Environment and Energy Engineering"

print(f"dept1: '{dept1}'")
print(f"dept2: '{dept2}'")
print(f"dept1 < dept2: {dept1 < dept2}")
print(f"dept1 > dept2: {dept1 > dept2}")
print(f"dept1 == dept2: {dept1 == dept2}")

# Check the comparison at the specific point where they differ
common_prefix = "Department of Building "
remainder1 = dept1[len(common_prefix):]
remainder2 = dept2[len(common_prefix):]

print(f"\nAfter common prefix '{common_prefix}':")
print(f"remainder1: '{remainder1}'")
print(f"remainder2: '{remainder2}'")
print(f"remainder1 < remainder2: {remainder1 < remainder2}")

# Check character by character
print(f"\nFirst differing characters:")
print(f"remainder1[0]: '{remainder1[0]}' (ord: {ord(remainder1[0])})")
print(f"remainder2[0]: '{remainder2[0]}' (ord: {ord(remainder2[0])})")
print(f"ord('{remainder1[0]}') < ord('{remainder2[0]}'): {ord(remainder1[0]) < ord(remainder2[0])}")

# Test sorting a list
dept_list = [dept1, dept2]
dept_list_sorted = sorted(dept_list)
print(f"\nOriginal list: {dept_list}")
print(f"Sorted list: {dept_list_sorted}")
print(f"Is correctly sorted: {dept_list_sorted[0] == dept2}") 