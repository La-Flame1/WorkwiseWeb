import db  # This imports your db.py file as a module
import pprint # Used to "pretty-print" the dictionary results
import sqlite3

def test_find_all_jobs():
    """
    Initializes, connects, and fetches all active jobs from the database.
    """
    print("--- 1. Initializing Database (if needed) ---")
    # This function is crucial. It creates tables AND
    # calls _populate_initial_data() if the db is empty.
    db.initDatabase()
    print("Database initialization complete.")
    
    conn = None
    try:
        # --- 2. Get a database connection ---
        print("\n--- 2. Connecting to Database ---")
        conn = db.getDatabase()
        print(f"Successfully connected to: {db.workwiseDatabase}")

        # --- 3. Fetch all active jobs ---
        # Your db.py file provides the getActiveJobs() function.
        # We set a high limit to ensure we get all of them.
        limit = 100 
        offset = 0
        
        print(f"\n--- 3. Fetching Active Jobs (limit={limit}) ---")
        jobs = db.getActiveJobs(conn, limit, offset)
        
        # --- 4. Display the results ---
        if not jobs:
            print("\n[RESULT] No active jobs were found in the database.")
            return

        print(f"\n[RESULT] Successfully found {len(jobs)} active jobs:\n")
        print("=" * 40)
        
        # Loop through each job and print its details
        for job in jobs:
            pprint.pprint(job)
            print("-" * 40)
            
    except sqlite3.Error as e:
        print(f"\n[ERROR] An error occurred: {e}")
    except Exception as e:
        print(f"\n[ERROR] A general error occurred: {e}")
        
    finally:
        # --- 5. Close the connection ---
        if conn:
            conn.close()
            print("\n--- 4. Database connection closed ---")

# This makes the script runnable
if __name__ == "__main__":
    test_find_all_jobs()