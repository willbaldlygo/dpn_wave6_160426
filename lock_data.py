import hashlib
import os
import shutil
import getpass

# Original filenames
MILESTONES_SRC = 'milestone_matrix.csv'
REFLECTIONS_SRC = 'layer2_layer3_clean_matrix.csv'

def lock_dashboard():
    print("\n--- Dashboard Static Locker ---")
    print("This script will protect your data files by renaming them to a hashed version of your password.")
    
    # 1. Get Password
    password = getpass.getpass("Enter a secret password for the dashboard: ")
    confirm = getpass.getpass("Confirm password: ")
    
    if password != confirm:
        print("Error: Passwords do not match.")
        return

    # 2. Generate Hash (SHA-256)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # 3. Define New Names
    # We use a naming pattern the dashboard will replicate
    milestones_dst = f"data_{password_hash}_m.csv"
    reflections_dst = f"data_{password_hash}_r.csv"
    
    # 4. Copy/Rename Files
    print("\nLocking files...")
    try:
        shutil.copy2(MILESTONES_SRC, milestones_dst)
        shutil.copy2(REFLECTIONS_SRC, reflections_dst)
        print(f"DONE: Created obfuscated data files.")
        print(f"HINT: Your password hash starts with: {password_hash[:8]}...")
        
        # 5. Create a flag file so the dashboard knows to show the login screen
        with open('dashboard/lock_active.json', 'w') as f:
            f.write('{"locked": true}')
            
        print("\nSUCCESS: Your dashboard is now locked.")
        print("NEXT STEPS:")
        print("1. Upload EVERYTHING to your GitHub repository.")
        print("2. When you visit the site, you will be prompted for your password.")
        
    except FileNotFoundError:
        print("Error: Source CSV files not found. Make sure you've run your processing scripts first.")

if __name__ == "__main__":
    lock_dashboard()
