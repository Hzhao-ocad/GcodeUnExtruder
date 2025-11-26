import zipfile
import re
import os
import sys


def process_3mf_file(path):
    """Process a single .3mf file"""
    if not os.path.exists(path):
        print(f"Error: File '{path}' not found!")
        return False

    if not path.lower().endswith('.3mf'):
        print(f"Error: '{path}' is not a .3mf file!")
        return False

    print(f"\nProcessing: {path}")

    gcode_path = "Metadata/plate_1.gcode"
    start_tag = "; MACHINE_START_GCODE_END"
    end_tag = "; MACHINE_END_GCODE_START"

    # REGEX: Match any G command with X/Y and E parameters
    pattern = re.compile(
        r"^G\d*\b(?=.*\b[XY]-?\d*\.?\d+)(?=.*\bE-?\d*\.?\d+).*",
        re.MULTILINE
    )

    try:
        # --- Read entire .3mf ---
        with zipfile.ZipFile(path, "r") as zin:
            original_gcode = zin.read(gcode_path).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error reading .3mf file: {e}")
        return False

    # Split entire G-code into lines
    lines = original_gcode.splitlines()

    # Extract block indices
    collect = False
    block_start_idx = None
    block_end_idx = None
    block_lines = []

    for i, line in enumerate(lines):
        if start_tag in line:
            collect = True
            block_start_idx = i + 1
            continue
        if end_tag in line and collect:
            block_end_idx = i
            collect = False
            break
        if collect:
            block_lines.append(line)

    if block_start_idx is None or block_end_idx is None:
        print("Warning: Could not find start/end tags in G-code")
        return False

    # Join and filter
    block_text = "\n".join(block_lines)
    filtered_lines = pattern.findall(block_text)

    if not filtered_lines:
        print("No matching G-code lines found to modify")
        return False

    print(f"Found {len(filtered_lines)} lines to modify")

    # --- Modify filtered lines ---
    modified_lines = []
    line_numbers = []

    # Map filtered lines back to original block lines
    for idx, line in enumerate(block_lines):
        if line in filtered_lines:
            line_numbers.append(block_start_idx + idx)

    # Apply modifications
    for i, line in enumerate(filtered_lines):
        split = line.split("E", 1)
        left = split[0]

        if i == len(filtered_lines) - 2:
            # LAST line → E.01
            new_line = left + "E.01"
        else:
            # All other lines → E0
            new_line = left + "E0"

        modified_lines.append(new_line)

    # --- Print modified lines with line numbers ---
    print("\nModified lines:")
    for ln, new in zip(line_numbers, modified_lines):
        print(f"[Line {ln}] {new}")

    # --- Replace modified lines back into block ---
    modified_block = block_lines.copy()

    fi = 0
    for i, line in enumerate(modified_block):
        if line in filtered_lines:
            modified_block[i] = modified_lines[fi]
            fi += 1

    # Replace block in main file
    new_lines = (
            lines[:block_start_idx] +
            modified_block +
            lines[block_end_idx:]
    )

    new_gcode_text = "\n".join(new_lines)

    # --- Write modified .3mf file (overwrite original) ---
    temp_path = path + ".tmp"

    try:
        # Read all data from original file first
        all_files = {}
        with zipfile.ZipFile(path, "r") as zin:
            for item in zin.infolist():
                if item.filename != gcode_path:
                    all_files[item.filename] = (item, zin.read(item.filename))

        # Now write to temporary file
        with zipfile.ZipFile(temp_path, "w") as zout:
            for filename, (item, data) in all_files.items():
                zout.writestr(item, data)
            # Write modified plate_1.gcode
            zout.writestr(gcode_path, new_gcode_text)

        # Replace original file with modified one
        os.remove(path)
        os.rename(temp_path, path)
        print(f"\n✓ Original file updated successfully: {path}")
        return True

    except Exception as e:
        print(f"Error saving file: {e}")
        if os.path.exists(temp_path):
            print(f"Temporary file saved as: {temp_path}")
        return False


def main():
    print("=" * 60)
    print("GcodeUnExtruder - 3MF G-code Modifier")
    print("=" * 60)

    # Check if file was provided as command line argument (drag & drop)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"\nFile detected via drag & drop: {file_path}")
        process_3mf_file(file_path)
    else:
        # Interactive mode
        print("\nNo file provided. Please enter the file path:")
        print("(You can drag & drop the file into this window, or type the path)")
        print()

        while True:
            file_path = input("Enter .3mf file path (or 'q' to quit): ").strip()

            # Remove quotes if user dragged & dropped
            file_path = file_path.strip('"').strip("'")

            if file_path.lower() == 'q':
                print("Exiting...")
                break

            if file_path:
                success = process_3mf_file(file_path)
                if success:
                    # Ask if user wants to process another file
                    print("\n" + "-" * 60)
                    another = input("\nProcess another file? (y/n): ").strip().lower()
                    if another != 'y':
                        print("Exiting...")
                        break
                else:
                    print("\nPlease try again with a valid file.")
            else:
                print("No file path entered. Please try again.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()