import mysql.connector
from container import Container
from ship import Bay

# Change this password to match the root password you set during MySQL setup
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE",
    "database": "cargoopt",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def load_bays_from_db():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT bay_id, bay_row, tier, bay_number, max_weight, is_reefer FROM bays")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    bays = []
    for row in rows:
        bays.append(Bay(
            bay_id=row["bay_id"],
            row=row["bay_row"],
            tier=row["tier"],
            bay_number=row["bay_number"],
            max_weight=row["max_weight"],
            is_reefer=bool(row["is_reefer"]),
        ))
    return bays


def load_containers_from_db():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT container_id, length, width, height, weight, is_fragile, is_hazardous, destination_port FROM containers"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    containers = []
    for row in rows:
        containers.append(Container(
            container_id=row["container_id"],
            length=row["length"],
            width=row["width"],
            height=row["height"],
            weight=row["weight"],
            is_fragile=bool(row["is_fragile"]),
            is_hazardous=bool(row["is_hazardous"]),
            destination_port=row["destination_port"],
        ))
    return containers

def add_container_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM containers WHERE container_id = %s",
        (data["container_id"],),
    )
    (count,) = cursor.fetchone()
    if count > 0:
        cursor.close()
        conn.close()
        raise ValueError(f"Container {data['container_id']} already exists")

    cursor.execute(
        "INSERT INTO containers "
        "(container_id, length, width, height, weight, is_fragile, is_hazardous, destination_port) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            data["container_id"],
            data["length"],
            data["width"],
            data["height"],
            data["weight"],
            data["is_fragile"],
            data["is_hazardous"],
            data["destination_port"],
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_container_in_db(container_id, data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM containers WHERE container_id = %s",
        (container_id,),
    )
    (count,) = cursor.fetchone()
    if count == 0:
        cursor.close()
        conn.close()
        raise LookupError(f"Container {container_id} not found")

    cursor.execute(
        "UPDATE containers SET length = %s, width = %s, height = %s, weight = %s, "
        "is_fragile = %s, is_hazardous = %s, destination_port = %s "
        "WHERE container_id = %s",
        (
            data["length"],
            data["width"],
            data["height"],
            data["weight"],
            data["is_fragile"],
            data["is_hazardous"],
            data["destination_port"],
            container_id,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_container_from_db(container_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM containers WHERE container_id = %s", (container_id,))
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if deleted == 0:
        raise LookupError(f"Container {container_id} not found")

    MAX_SECTIONS = 4


MAX_SECTIONS = 4

def add_bay_section_to_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(MAX(bay_number), 0) FROM bays")
    (current,) = cursor.fetchone()
    new_section = current + 1

    if new_section > MAX_SECTIONS:
        cursor.close()
        conn.close()
        raise ValueError(f"The deck only has room for {MAX_SECTIONS} sections")

    tier_limits = {1: 30000, 2: 25000, 3: 20000}
    for tier, max_weight in tier_limits.items():
        for row in (1, 2):
            cursor.execute(
                "INSERT INTO bays (bay_id, bay_row, tier, bay_number, max_weight, is_reefer) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (f"S{new_section}-R{row}T{tier}", row, tier, new_section, max_weight, False),
            )

    conn.commit()
    cursor.close()
    conn.close()
    return new_section


def remove_last_bay_section_from_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(MAX(bay_number), 0) FROM bays")
    (current,) = cursor.fetchone()

    if current <= 1:
        cursor.close()
        conn.close()
        raise ValueError("The ship must keep at least one section")

    cursor.execute("DELETE FROM bays WHERE bay_number = %s", (current,))
    conn.commit()
    cursor.close()
    conn.close()
    return current