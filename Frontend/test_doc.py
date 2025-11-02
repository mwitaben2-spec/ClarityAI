import os

class DataProcessor:
    """
    A simple class to process text files.
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = None

    def load_data(self):
        """
        Loads data from the file path provided.
        Returns True on success, False on failure.
        """
        if not os.path.exists(self.filepath):
            print(f"Error: File not found at {self.filepath}")
            return False

        with open(self.filepath, 'r') as f:
            self.data = f.readlines()

        print("Data loaded successfully.")
        return True

    def get_line_count(self):
        """
        Returns the total number of lines loaded.
        """
        if self.data:
            return len(self.data)
        return 0

def calculate_average(numbers):
    """
    Calculates the average of a list of numbers.
    """
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)