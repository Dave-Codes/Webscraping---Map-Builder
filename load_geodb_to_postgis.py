import os
import subprocess
import sys #Import sys for exit()

def create_postgis_database(db_name, db_user, db_password, delete_if_exists=False):
    """
    Creates a new PostGIS database and enables the PostGIS extension.

    Args:
        db_name (str): The name of the database to create.
        db_user (str): The PostgreSQL user to use for database creation.
        db_password (str): The password for the PostgreSQL user.
        delete_if_exists (bool): if true, delete the existing database.
    """
    # --- Delete the Database if it exists---
    if delete_if_exists:
        if database_exists(db_name, db_user):
            try:
                subprocess.run(
                    [
                        "dropdb",
                        "-U",
                        db_user,
                        db_name,
                    ],
                    check=True,
                    input=f"{db_password}\n",
                    text=True,
                )
                print(f"Database '{db_name}' dropped successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error dropping database '{db_name}': {e}")
            except FileNotFoundError:
                print("Error: 'dropdb' command not found. Make sure PostgreSQL is installed and in your PATH.")
                sys.exit()
    # ----------------------------------------

    try:
        # Create the database
        subprocess.run(
            [
                "createdb",
                "-U",
                db_user,
                "-E",
                "UTF-8",  # Specify UTF-8 encoding
                db_name,
            ],
            check=True,
            input=f"{db_password}\n",
            text=True,
        )
        print(f"Database '{db_name}' created successfully.")

        # Enable PostGIS extension
        subprocess.run(
            [
                "psql",
                "-U",
                db_user,
                "-d",
                db_name,
                "-c",
                "CREATE EXTENSION postgis;",
            ],
            check=True,
            input=f"{db_password}\n",
            text=True,
        )
        print(f"PostGIS extension enabled in database '{db_name}'.")

    except subprocess.CalledProcessError as e:
        print(f"Error creating database or enabling PostGIS: {e}")
    except FileNotFoundError:
        print("Error: 'createdb' or 'psql' command not found. Make sure PostgreSQL is installed and in your PATH.")
        sys.exit()

def load_gdb_to_postgis(gdb_directory, db_name, db_user, db_password):
    """
    Loads all GDB files from a directory into a PostGIS database.

    Args:
        gdb_directory (str): The path to the directory containing GDB files.
        db_name (str): The name of the PostGIS database.
        db_user (str): The PostgreSQL user.
        db_password (str): The password for the PostgreSQL user.
    """
    if not os.path.exists(gdb_directory):
        print(f"Error: GDB directory '{gdb_directory}' not found.")
        sys.exit()

    for filename in os.listdir(gdb_directory):
        if filename.endswith(".gdb"):
            gdb_path = os.path.join(gdb_directory, filename)
            print(f"Processing: {gdb_path}")

            try:
                # Use ogr2ogr to load the GDB into PostGIS
                subprocess.run(
                    [
                        "ogr2ogr",
                        "-f",
                        "PostgreSQL",
                        f"PG:host=localhost dbname={db_name} user={db_user} password={db_password}",
                        gdb_path,
                    ],
                    check=True,
                )
                print(f"Successfully loaded '{filename}' into PostGIS database '{db_name}'.")
            except subprocess.CalledProcessError as e:
                print(f"Error loading '{filename}' into PostGIS: {e}")
            except FileNotFoundError:
                 print("Error: 'ogr2ogr' command not found. Make sure GDAL is installed and in your PATH.")
                 sys.exit()

def database_exists(db_name, db_user):
    """Check if a database exists."""
    try:
        subprocess.run(
            [
                "psql",
                "-U",
                db_user,
                "-lqt",
                "-d",
                "template1",
            ],
            check=True,
            text=True,
            capture_output=True
        )
        output = subprocess.check_output(
          [
              "psql",
              "-U",
              db_user,
              "-lqt",
              "-d",
              "template1",
          ],
          text=True,
      )

        databases = [line.split("|")[0].strip() for line in output.splitlines()]

        return db_name in databases
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        print("Error: 'psql' command not found. Make sure PostgreSQL is installed and in your PATH.")
        return False

def main():
    # --- Configuration ---
    gdb_directory = "gdb_directory" #Replace with your path
    db_name = "usfs_gdb_db" #Replace with your database name.
    db_user = "dave" #Replace with your user name.
    db_password = "your_password" #Replace with your password.
    delete_existing = True # change this to false if you do not want to delete the existing database.

    # --- Create PostGIS Database ---
    create_postgis_database(db_name, db_user, db_password, delete_if_exists=delete_existing)

    # --- Load GDBs into PostGIS ---
    load_gdb_to_postgis(gdb_directory, db_name, db_user, db_password)

if __name__ == "__main__":
    main()
