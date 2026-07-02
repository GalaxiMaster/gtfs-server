import sqlite3
import pandas as pd

def csv_to_db(path:str = 'assets'):
    # Define file paths
    files = [f"{path}/trips", f"{path}/stops", f"{path}/stop_times", f"{path}/routes", f"{path}/calendar", f"{path}/calendar_dates"]
    for csv_file in files:
        db_file = f"{csv_file}.db"
        table_name = csv_file.split('/')[-1]

        # Read CSV into a pandas DataFrame
        df = pd.read_csv(f'{csv_file}.txt')

        # Establish connection to SQLite database
        conn = sqlite3.connect(db_file)

        # Write records stored in DataFrame to a SQLite table
        df.to_sql(table_name, conn, if_exists="replace", index=False)

        # Close the database connection
        conn.close()