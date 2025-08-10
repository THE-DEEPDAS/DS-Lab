import os
import pandas as pd

# Folder containing your CSV files
input_folder = "archive"
output_file = "merged.csv"

# List all CSV files in the folder
csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]

# Merge all CSVs
merged_df = pd.concat(
    [pd.read_csv(os.path.join(input_folder, f)) for f in csv_files],
    ignore_index=True
)

# Save merged CSV
merged_df.to_csv(output_file, index=False)

print(f"Merged {len(csv_files)} CSV files into '{output_file}'")
