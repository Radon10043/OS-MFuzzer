# The greater the better
DATA1 = []
DATA2 = []

def calculate_a12(la, lb):
    if not la or not lb:
        return 0.5

    len_a = len(la)
    len_b = len(lb)

    wins = 0  # Number of a > b
    ties = 0  # Number of a == b

    for a in la:
        for b in lb:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1

    # A12 = (N(a > b) + 0.5 * N(a == b)) / N(comparisons)
    return (wins + 0.5 * ties) / (len_a * len_b)

# Calculate A12 (Tool1 vs Tool2)
a12 = calculate_a12(DATA1, DATA2)

print(f"A12 = {a12:.4f}")
if a12 > 0.5:
    print(f"({a12:.4f}) > 0.5: Tool1 has a higher probability of achieving better results than Tool2.")
elif a12 < 0.5:
    print(f"({a12:.4f}) < 0.5: Tool2 has a higher probability of achieving better results than Tool1.")
else:
    print(f"({a12:.4f}) == 0.5: No significant difference between Tool1 and Tool2.")

# Note: A12(B vs A) = 1 - A12(A vs B)
a12_ba = calculate_a12(DATA2, DATA1)
print(f"\nA12 (Tool2 vs Tool1) = {a12_ba:.4f}")
print(f"A12(Tool1 vs Tool2) + A12(Tool2 vs Tool1) = {a12 + a12_ba:.1f} (should be 1.0)")
