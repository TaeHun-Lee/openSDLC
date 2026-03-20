import random

def generate_lotto_numbers():
    """
    Generates 6 unique random numbers between 1 and 45 (inclusive).
    Ensures:
    - Exactly 6 numbers.
    - Numbers are unique.
    - Numbers are within the range [1, 45].
    """
    numbers = set()
    while len(numbers) < 6:
        numbers.add(random.randint(1, 45))
    
    # Convert to list and sort for consistent output, though not strictly required by AC.
    return sorted(list(numbers))

def main():
    """
    Main entry point for the Simple Lotto App.
    Generates and displays a set of lotto numbers.
    """
    print("Welcome to the Simple Lotto App!")
    print("------------------------------")
    
    lotto_numbers = generate_lotto_numbers()
    
    print("\nYour lucky lotto numbers are:")
    # Display format for clarity, matching "명확하게 표시"
    print(f"[{', '.join(map(str, lotto_numbers))}]")
    print("\nGood luck!")

if __name__ == "__main__":
    main()