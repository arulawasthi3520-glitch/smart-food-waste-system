import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta
import pandas as pd
import os

# ============================================================
# CONFIGURATION
# ============================================================

DB_NAME = "food_waste.db"

st.set_page_config(
    page_title="Smart Food Waste System",
    page_icon="🍎",
    layout="wide"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# DATABASE SETUP
# ============================================================

def prepare_database():

    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    """)

    # Food table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity REAL,
            unit TEXT,
            purchase_date TEXT,
            expiry_date TEXT,
            storage TEXT,
            waste_recorded INTEGER DEFAULT 0,
            user_id INTEGER
        )
    """)

    # Waste table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER,
            food_name TEXT,
            quantity REAL,
            unit TEXT,
            waste_date TEXT,
            reason TEXT,
            user_id INTEGER
        )
    """)

    # Add missing columns if an older database is being used

    try:
        cursor.execute("ALTER TABLE food ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE waste ADD COLUMN food_id INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE food ADD COLUMN waste_recorded INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE waste ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


prepare_database()


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = ""

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except:
        return None


def days_until_expiry(expiry_date):
    expiry = parse_date(expiry_date)

    if expiry is None:
        return None

    return (expiry - date.today()).days


def get_user_food():
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            name,
            category,
            quantity,
            unit,
            purchase_date,
            expiry_date,
            storage,
            waste_recorded
        FROM food
        WHERE user_id = ?
        ORDER BY expiry_date ASC
        """,
        conn,
        params=(st.session_state.user_id,)
    )

    conn.close()
    return df


def get_user_waste():
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            food_id,
            food_name,
            quantity,
            unit,
            waste_date,
            reason
        FROM waste
        WHERE user_id = ?
        ORDER BY waste_date DESC, id DESC
        """,
        conn,
        params=(st.session_state.user_id,)
    )

    conn.close()
    return df


# ============================================================
# AUTOMATIC EXPIRED FOOD → WASTE
# ============================================================

def move_expired_food_to_waste():

    user_id = st.session_state.user_id

    if user_id is None:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            quantity,
            unit,
            expiry_date
        FROM food
        WHERE user_id = ?
        AND waste_recorded = 0
        """,
        (user_id,)
    )

    foods = cursor.fetchall()

    moved = 0

    for food in foods:

        expiry = parse_date(food["expiry_date"])

        if expiry is None:
            continue

        if expiry < date.today():

            cursor.execute(
                """
                INSERT INTO waste
                (
                    food_id,
                    food_name,
                    quantity,
                    unit,
                    waste_date,
                    reason,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    food["id"],
                    food["name"],
                    food["quantity"],
                    food["unit"],
                    date.today().isoformat(),
                    "Expired",
                    user_id
                )
            )

            cursor.execute(
                """
                UPDATE food
                SET waste_recorded = 1
                WHERE id = ?
                AND user_id = ?
                """,
                (
                    food["id"],
                    user_id
                )
            )

            moved += 1

    conn.commit()
    conn.close()

    return moved


# ============================================================
# LOGIN / PROFILE
# ============================================================

if not st.session_state.logged_in:

    st.title("🍎 Smart Food Waste System")

    st.markdown(
        """
        ### Prevent • Track • Reduce Food Waste

        Create your own profile to manage your food inventory,
        expiry dates, waste and recommendations.
        """
    )

    st.divider()

    tab1, tab2 = st.tabs(
        [
            "🔐 Login",
            "➕ Create Profile"
        ]
    )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    with tab1:

        st.subheader("Login")

        username = st.text_input(
            "Enter your username",
            key="login_username"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            username = username.strip()

            if username == "":
                st.error("Please enter a username.")

            else:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, username
                    FROM users
                    WHERE username = ?
                    """,
                    (username,)
                )

                user = cursor.fetchone()

                conn.close()

                if user:

                    st.session_state.logged_in = True
                    st.session_state.user_id = user["id"]
                    st.session_state.username = user["username"]

                    st.success("Login successful!")
                    st.rerun()

                else:

                    st.error(
                        "Username not found. Please create a profile first."
                    )

    # --------------------------------------------------------
    # CREATE PROFILE
    # --------------------------------------------------------

    with tab2:

        st.subheader("Create New Profile")

        new_username = st.text_input(
            "Choose a username",
            key="new_username"
        )

        if st.button(
            "Create Profile",
            use_container_width=True
        ):

            new_username = new_username.strip()

            if new_username == "":
                st.error("Username cannot be empty.")

            elif len(new_username) < 3:
                st.error("Username must contain at least 3 characters.")

            else:

                conn = get_connection()
                cursor = conn.cursor()

                try:

                    cursor.execute(
                        """
                        INSERT INTO users (username)
                        VALUES (?)
                        """,
                        (new_username,)
                    )

                    conn.commit()

                    user_id = cursor.lastrowid

                    conn.close()

                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = new_username

                    st.success(
                        "Profile created successfully!"
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    conn.close()

                    st.error(
                        "This username is already claimed. "
                        "Please choose another username."
                    )

    st.stop()


# ============================================================
# AUTOMATIC EXPIRY CHECK
# ============================================================

moved = move_expired_food_to_waste()

if moved > 0:
    st.toast(
        f"{moved} expired food item(s) moved to Waste Management.",
        icon="⚠️"
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.title("🍎 Smart Food")

    st.caption(
        f"Logged in as: **{st.session_state.username}**"
    )

    st.divider()

    navigation_options = [
        "🏠 Dashboard",
        "🍎 Food Inventory",
        "➕ Add Food",
        "🗑 Waste Management",
        "📊 Analytics",
        "🧠 Smart Recommendations"
    ]

    # Make sure the saved page is valid
    if st.session_state.page not in navigation_options:
        st.session_state.page = "🏠 Dashboard"

    page = st.radio(
        "Navigation",
        navigation_options,
        index=navigation_options.index(
            st.session_state.page
        )
    )

    st.session_state.page = page

    st.divider()

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = ""
        st.session_state.page = "🏠 Dashboard"

        st.rerun()
# ============================================================
# COMMON DATA
# ============================================================

food_df = get_user_food()
waste_df = get_user_waste()


# ============================================================
# DASHBOARD
# ============================================================

if st.session_state.page == "🏠 Dashboard":

    st.title("🏠 Dashboard")

    st.subheader(
        f"Welcome, {st.session_state.username}! 👋"
    )

    today = date.today()

    total_food = len(food_df)

    total_quantity = (
        food_df["quantity"].sum()
        if not food_df.empty
        else 0
    )

    expiring_soon = 0
    urgent = 0
    expired = 0

    if not food_df.empty:

        for _, row in food_df.iterrows():

            days = days_until_expiry(
                row["expiry_date"]
            )

            if days is None:
                continue

            if days < 0:
                expired += 1

            elif days <= 7:
                expiring_soon += 1

            if 0 <= days <= 2:
                urgent += 1

    waste_records = len(waste_df)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🍎 Total Food",
        total_food
    )

    col2.metric(
        "📦 Total Quantity",
        round(total_quantity, 2)
    )

    col3.metric(
        "⏰ Expiring Soon",
        expiring_soon
    )

    col4.metric(
        "🗑 Waste Records",
        waste_records
    )

    st.divider()

    # --------------------------------------------------------
    # EXPIRY ALERTS
    # --------------------------------------------------------

    st.subheader("⚠️ Expiry Alerts")

    if food_df.empty:

        st.info(
            "No food items added yet."
        )

    else:

        alerts = []

        for _, row in food_df.iterrows():

            days = days_until_expiry(
                row["expiry_date"]
            )

            if days is None:
                continue

            if days < 0:

                alerts.append(
                    {
                        "Food": row["name"],
                        "Expiry Date": row["expiry_date"],
                        "Status": "❌ Expired",
                        "Days": abs(days)
                    }
                )

            elif days == 0:

                alerts.append(
                    {
                        "Food": row["name"],
                        "Expiry Date": row["expiry_date"],
                        "Status": "🚨 Expires Today",
                        "Days": 0
                    }
                )

            elif days <= 7:

                alerts.append(
                    {
                        "Food": row["name"],
                        "Expiry Date": row["expiry_date"],
                        "Status": "⚠️ Expiring Soon",
                        "Days": days
                    }
                )

        if alerts:

            alert_df = pd.DataFrame(alerts)

            st.dataframe(
                alert_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "✅ No food is expiring within the next 7 days."
            )

    st.divider()

    # --------------------------------------------------------
    # QUICK SUMMARY
    # --------------------------------------------------------

    st.subheader("📋 Quick Summary")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            **Food Management**

            • Add new food items  
            • Track purchase dates  
            • Track expiry dates  
            • Monitor storage  
            • Edit or delete food
            """
        )

    with col2:

        st.markdown(
            """
            **Waste Management**

            • Automatically detect expired food  
            • Record wasted food  
            • Track waste reasons  
            • View waste history  
            • Analyse waste patterns
            """
        )


# ============================================================
# FOOD INVENTORY
# ============================================================

elif st.session_state.page == "🍎 Food Inventory":

    st.title("🍎 Food Inventory")

    if food_df.empty:

        st.info(
            "Your food inventory is empty."
        )

        st.write(
            "Go to **➕ Add Food** to add your first item."
        )

    else:

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        search = st.text_input(
            "🔎 Search food"
        )

        display_df = food_df.copy()

        if search.strip():

            display_df = display_df[
                display_df["name"]
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        statuses = []

        for _, row in display_df.iterrows():

            days = days_until_expiry(
                row["expiry_date"]
            )

            if days is None:

                status = "Unknown"

            elif days < 0:

                status = "❌ Expired"

            elif days == 0:

                status = "🚨 Today"

            elif days <= 2:

                status = "🔴 Urgent"

            elif days <= 7:

                status = "🟠 Soon"

            else:

                status = "🟢 Fresh"

            statuses.append(status)

        display_df["Status"] = statuses

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        show_df = display_df[
            [
                "id",
                "name",
                "category",
                "quantity",
                "unit",
                "purchase_date",
                "expiry_date",
                "storage",
                "Status"
            ]
        ].copy()

        show_df.columns = [
            "ID",
            "Food",
            "Category",
            "Quantity",
            "Unit",
            "Purchase Date",
            "Expiry Date",
            "Storage",
            "Status"
        ]

        st.dataframe(
            show_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------------------------------
        # EDIT FOOD
        # ----------------------------------------------------

        st.subheader("✏️ Edit Food")

        selected_id = st.number_input(
            "Enter Food ID to edit",
            min_value=0,
            step=1,
            value=0
        )

        if selected_id > 0:

            selected = food_df[
                food_df["id"] == selected_id
            ]

            if selected.empty:

                st.error(
                    "Food ID not found."
                )

            else:

                item = selected.iloc[0]

                with st.form(
                    "edit_food_form"
                ):

                    edit_name = st.text_input(
                        "Food Name",
                        value=str(item["name"])
                    )

                    edit_category = st.text_input(
                        "Category",
                        value=str(item["category"] or "")
                    )

                    edit_quantity = st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=float(item["quantity"]),
                        step=0.1
                    )

                    edit_unit = st.text_input(
                        "Unit",
                        value=str(item["unit"] or "")
                    )

                    edit_purchase = st.date_input(
                        "Purchase Date",
                        value=parse_date(
                            item["purchase_date"]
                        ) or date.today()
                    )

                    edit_expiry = st.date_input(
                        "Expiry Date",
                        value=parse_date(
                            item["expiry_date"]
                        ) or date.today()
                    )

                    edit_storage = st.selectbox(
                        "Storage",
                        [
                            "Room Temperature",
                            "Refrigerator",
                            "Freezer",
                            "Other"
                        ],
                        index=[
                            "Room Temperature",
                            "Refrigerator",
                            "Freezer",
                            "Other"
                        ].index(
                            item["storage"]
                            if item["storage"]
                            in [
                                "Room Temperature",
                                "Refrigerator",
                                "Freezer",
                                "Other"
                            ]
                            else "Other"
                        )
                    )

                    save_edit = st.form_submit_button(
                        "💾 Save Changes",
                        use_container_width=True
                    )

                    if save_edit:

                        if edit_name.strip() == "":
                            st.error(
                                "Food name cannot be empty."
                            )

                        elif edit_expiry < edit_purchase:

                            st.error(
                                "Expiry date cannot be before purchase date."
                            )

                        else:

                            conn = get_connection()
                            cursor = conn.cursor()

                            cursor.execute(
                                """
                                UPDATE food
                                SET
                                    name = ?,
                                    category = ?,
                                    quantity = ?,
                                    unit = ?,
                                    purchase_date = ?,
                                    expiry_date = ?,
                                    storage = ?
                                WHERE id = ?
                                AND user_id = ?
                                """,
                                (
                                    edit_name.strip(),
                                    edit_category.strip(),
                                    edit_quantity,
                                    edit_unit.strip(),
                                    edit_purchase.isoformat(),
                                    edit_expiry.isoformat(),
                                    edit_storage,
                                    selected_id,
                                    st.session_state.user_id
                                )
                            )

                            conn.commit()
                            conn.close()

                            st.success(
                                "Food updated successfully!"
                            )

                            st.rerun()

        st.divider()

        # ----------------------------------------------------
        # DELETE FOOD
        # ----------------------------------------------------

        st.subheader("🗑 Delete Food")

        delete_id = st.number_input(
            "Enter Food ID to delete",
            min_value=0,
            step=1,
            value=0,
            key="delete_food_id"
        )

        if st.button(
            "Delete Food",
            type="secondary"
        ):

            if delete_id <= 0:

                st.error(
                    "Enter a valid Food ID."
                )

            else:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM food
                    WHERE id = ?
                    AND user_id = ?
                    """,
                    (
                        delete_id,
                        st.session_state.user_id
                    )
                )

                deleted = cursor.rowcount

                conn.commit()
                conn.close()

                if deleted:

                    st.success(
                        "Food deleted successfully."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Food ID not found."
                    )


# ============================================================
# ADD FOOD
# ============================================================

elif st.session_state.page == "➕ Add Food":

    st.title("➕ Add Food")

    st.write(
        "Enter the details of the food item."
    )

    with st.form(
        "add_food_form"
    ):

        name = st.text_input(
            "Food Name *",
            placeholder="Example: Milk"
        )

        category = st.selectbox(
            "Category",
            [
                "Dairy",
                "Fruits",
                "Vegetables",
                "Grains",
                "Meat",
                "Fish",
                "Frozen Food",
                "Beverages",
                "Snacks",
                "Other"
            ]
        )

        col1, col2 = st.columns(2)

        with col1:

            quantity = st.number_input(
                "Quantity",
                min_value=0.0,
                value=1.0,
                step=0.1
            )

        with col2:

            unit = st.selectbox(
                "Unit",
                [
                    "kg",
                    "g",
                    "litre",
                    "ml",
                    "packet",
                    "piece",
                    "box",
                    "bottle",
                    "other"
                ]
            )

        purchase_date = st.date_input(
            "Purchase Date",
            value=date.today()
        )

        expiry_date = st.date_input(
            "Expiry Date",
            value=date.today() + timedelta(days=7)
        )

        storage = st.selectbox(
            "Storage",
            [
                "Room Temperature",
                "Refrigerator",
                "Freezer",
                "Other"
            ]
        )

        submit = st.form_submit_button(
            "➕ Add Food",
            use_container_width=True
        )

        if submit:

            if name.strip() == "":

                st.error(
                    "Please enter a food name."
                )

            elif quantity <= 0:

                st.error(
                    "Quantity must be greater than 0."
                )

            elif expiry_date < purchase_date:

                st.error(
                    "Expiry date cannot be before purchase date."
                )

            else:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO food
                    (
                        name,
                        category,
                        quantity,
                        unit,
                        purchase_date,
                        expiry_date,
                        storage,
                        waste_recorded,
                        user_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        name.strip(),
                        category,
                        quantity,
                        unit,
                        purchase_date.isoformat(),
                        expiry_date.isoformat(),
                        storage,
                        st.session_state.user_id
                    )
                )

                conn.commit()
                conn.close()

                st.success(
                    f"{name} added successfully! 🎉"
                )

                st.info(
                    "Go to Food Inventory or Dashboard to see it."
                )


# ============================================================
# WASTE MANAGEMENT
# ============================================================

elif st.session_state.page == "🗑 Waste Management":

    st.title("🗑 Waste Management")

    st.subheader("➕ Record Food Waste")

    available_food = get_user_food()

    if available_food.empty:

        st.info(
            "No food items available."
        )

    else:

        with st.form(
            "waste_form"
        ):

            food_options = {
                f"{row['id']} - {row['name']}": row["id"]
                for _, row in available_food.iterrows()
                if int(row["waste_recorded"] or 0) == 0
            }

            if not food_options:

                st.info(
                    "All current food items have already been marked as waste."
                )

            else:

                selected_food = st.selectbox(
                    "Select Food",
                    list(food_options.keys())
                )

                selected_food_id = food_options[
                    selected_food
                ]

                selected_row = available_food[
                    available_food["id"] == selected_food_id
                ].iloc[0]

                waste_quantity = st.number_input(
                    "Waste Quantity",
                    min_value=0.1,
                    value=float(
                        selected_row["quantity"]
                    ),
                    step=0.1
                )

                reason = st.selectbox(
                    "Reason",
                    [
                        "Expired",
                        "Spoiled",
                        "Overcooked",
                        "Leftover",
                        "Too Much Purchased",
                        "Other"
                    ]
                )

                waste_date = st.date_input(
                    "Waste Date",
                    value=date.today()
                )

                record_waste = st.form_submit_button(
                    "🗑 Record Waste",
                    use_container_width=True
                )

                if record_waste:

                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO waste
                        (
                            food_id,
                            food_name,
                            quantity,
                            unit,
                            waste_date,
                            reason,
                            user_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            selected_food_id,
                            selected_row["name"],
                            waste_quantity,
                            selected_row["unit"],
                            waste_date.isoformat(),
                            reason,
                            st.session_state.user_id
                        )
                    )

                    cursor.execute(
                        """
                        UPDATE food
                        SET waste_recorded = 1
                        WHERE id = ?
                        AND user_id = ?
                        """,
                        (
                            selected_food_id,
                            st.session_state.user_id
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success(
                        "Waste recorded successfully."
                    )

                    st.rerun()

    st.divider()

    # --------------------------------------------------------
    # WASTE HISTORY
    # --------------------------------------------------------

    st.subheader("📜 Waste History")

    waste_df = get_user_waste()

    if waste_df.empty:

        st.info(
            "No waste records yet."
        )

    else:

        show_waste = waste_df[
            [
                "id",
                "food_name",
                "quantity",
                "unit",
                "waste_date",
                "reason"
            ]
        ].copy()

        show_waste.columns = [
            "ID",
            "Food",
            "Quantity",
            "Unit",
            "Waste Date",
            "Reason"
        ]

        st.dataframe(
            show_waste,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------------------------------
        # EDIT WASTE
        # ----------------------------------------------------

        st.subheader("✏️ Edit Waste Record")

        edit_waste_id = st.number_input(
            "Waste ID",
            min_value=0,
            step=1,
            value=0,
            key="edit_waste_id"
        )

        if edit_waste_id > 0:

            selected_waste = waste_df[
                waste_df["id"] == edit_waste_id
            ]

            if selected_waste.empty:

                st.error(
                    "Waste record not found."
                )

            else:

                waste_item = selected_waste.iloc[0]

                with st.form(
                    "edit_waste_form"
                ):

                    new_quantity = st.number_input(
                        "Quantity",
                        min_value=0.1,
                        value=float(
                            waste_item["quantity"]
                        ),
                        step=0.1
                    )

                    new_reason = st.selectbox(
                        "Reason",
                        [
                            "Expired",
                            "Spoiled",
                            "Overcooked",
                            "Leftover",
                            "Too Much Purchased",
                            "Other"
                        ],
                        index=[
                            "Expired",
                            "Spoiled",
                            "Overcooked",
                            "Leftover",
                            "Too Much Purchased",
                            "Other"
                        ].index(
                            waste_item["reason"]
                            if waste_item["reason"]
                            in [
                                "Expired",
                                "Spoiled",
                                "Overcooked",
                                "Leftover",
                                "Too Much Purchased",
                                "Other"
                            ]
                            else "Other"
                        )
                    )

                    new_date = st.date_input(
                        "Waste Date",
                        value=parse_date(
                            waste_item["waste_date"]
                        ) or date.today()
                    )

                    update_waste = st.form_submit_button(
                        "💾 Update Waste"
                    )

                    if update_waste:

                        conn = get_connection()
                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            UPDATE waste
                            SET
                                quantity = ?,
                                reason = ?,
                                waste_date = ?
                            WHERE id = ?
                            AND user_id = ?
                            """,
                            (
                                new_quantity,
                                new_reason,
                                new_date.isoformat(),
                                edit_waste_id,
                                st.session_state.user_id
                            )
                        )

                        conn.commit()
                        conn.close()

                        st.success(
                            "Waste record updated."
                        )

                        st.rerun()

        st.divider()

        # ----------------------------------------------------
        # DELETE WASTE
        # ----------------------------------------------------

        st.subheader("🗑 Delete Waste Record")

        delete_waste_id = st.number_input(
            "Enter Waste ID",
            min_value=0,
            step=1,
            value=0,
            key="delete_waste_id"
        )

        if st.button(
            "Delete Waste Record"
        ):

            if delete_waste_id <= 0:

                st.error(
                    "Enter a valid Waste ID."
                )

            else:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM waste
                    WHERE id = ?
                    AND user_id = ?
                    """,
                    (
                        delete_waste_id,
                        st.session_state.user_id
                    )
                )

                deleted = cursor.rowcount

                conn.commit()
                conn.close()

                if deleted:

                    st.success(
                        "Waste record deleted."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Waste ID not found."
                    )


# ============================================================
# ANALYTICS
# ============================================================

elif st.session_state.page == "📊 Analytics":

    st.title("📊 Analytics")

    food_df = get_user_food()
    waste_df = get_user_waste()

    # --------------------------------------------------------
    # BASIC METRICS
    # --------------------------------------------------------

    total_food = len(food_df)

    total_waste_records = len(waste_df)

    total_wasted_quantity = (
        waste_df["quantity"].sum()
        if not waste_df.empty
        else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Food Items",
        total_food
    )

    col2.metric(
        "Waste Records",
        total_waste_records
    )

    col3.metric(
        "Total Wasted Quantity",
        round(total_wasted_quantity, 2)
    )

    st.divider()

    # --------------------------------------------------------
    # WASTE BY REASON
    # --------------------------------------------------------

    st.subheader("📌 Waste by Reason")

    if waste_df.empty:

        st.info(
            "No waste data available yet."
        )

    else:

        reason_data = (
            waste_df
            .groupby("reason")["quantity"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        st.bar_chart(
            reason_data
        )

    st.divider()

    # --------------------------------------------------------
    # MOST WASTED FOOD
    # --------------------------------------------------------

    st.subheader("🥇 Most Wasted Food")

    if waste_df.empty:

        st.info(
            "No waste data available."
        )

    else:

        most_wasted = (
            waste_df
            .groupby("food_name")["quantity"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        st.bar_chart(
            most_wasted
        )

        st.dataframe(
            most_wasted.reset_index(
                name="Wasted Quantity"
            ),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # --------------------------------------------------------
    # CATEGORY ANALYSIS
    # --------------------------------------------------------

    st.subheader("📦 Food Category Analysis")

    if food_df.empty:

        st.info(
            "No food inventory data available."
        )

    else:

        category_data = (
            food_df
            .groupby("category")["quantity"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        st.bar_chart(
            category_data
        )

    st.divider()

    # --------------------------------------------------------
    # WASTE RISK PREDICTION
    # --------------------------------------------------------

    st.subheader(
        "🔮 Food Waste Risk Prediction"
    )

    st.caption(
        "Current version uses rule-based prediction. "
        "Machine Learning can be added later."
    )

    if food_df.empty:

        st.info(
            "Add food items to calculate risk."
        )

    else:

        risk_rows = []

        for _, row in food_df.iterrows():

            days = days_until_expiry(
                row["expiry_date"]
            )

            if days is None:

                risk = "Unknown"
                score = 0

            elif days < 0:

                risk = "Very High"
                score = 100

            elif days <= 2:

                risk = "High"
                score = 80

            elif days <= 5:

                risk = "Medium"
                score = 50

            elif days <= 10:

                risk = "Low"
                score = 25

            else:

                risk = "Very Low"
                score = 10

            risk_rows.append(
                {
                    "Food": row["name"],
                    "Expiry Date": row["expiry_date"],
                    "Days Remaining": days,
                    "Risk Score": score,
                    "Risk Level": risk
                }
            )

        risk_df = pd.DataFrame(
            risk_rows
        )

        st.dataframe(
            risk_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SMART RECOMMENDATIONS
# ============================================================

elif st.session_state.page == "🧠 Smart Recommendations":

    st.title(
        "🧠 Smart Recommendations"
    )

    st.write(
        "The system analyses your expiry dates "
        "and recommends which food should be used first."
    )

    food_df = get_user_food()

    if food_df.empty:

        st.info(
            "Add food items to receive recommendations."
        )

    else:

        recommendations = []

        for _, row in food_df.iterrows():

            days = days_until_expiry(
                row["expiry_date"]
            )

            if days is None:
                continue

            if days < 0:

                priority = 1
                message = "❌ Expired — remove from active inventory."

            elif days == 0:

                priority = 1
                message = "🚨 Use immediately."

            elif days <= 2:

                priority = 1
                message = "🔥 Use this first."

            elif days <= 5:

                priority = 2
                message = "⚠️ Plan to use soon."

            elif days <= 7:

                priority = 3
                message = "🟡 Consider using this week."

            else:

                priority = 4
                message = "🟢 Safe for now."

            recommendations.append(
                {
                    "Priority": priority,
                    "Food": row["name"],
                    "Category": row["category"],
                    "Quantity": row["quantity"],
                    "Unit": row["unit"],
                    "Expiry Date": row["expiry_date"],
                    "Days Remaining": days,
                    "Recommendation": message
                }
            )

        recommendation_df = pd.DataFrame(
            recommendations
        )

        recommendation_df = (
            recommendation_df
            .sort_values(
                [
                    "Priority",
                    "Days Remaining"
                ]
            )
        )

        st.subheader(
            "🍽️ Use First List"
        )

        st.dataframe(
            recommendation_df[
                [
                    "Food",
                    "Category",
                    "Quantity",
                    "Unit",
                    "Expiry Date",
                    "Days Remaining",
                    "Recommendation"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------------------------------
        # TOP RECOMMENDATIONS
        # ----------------------------------------------------

        st.subheader(
            "⭐ Top Recommendations"
        )

        top_items = recommendation_df.head(5)

        for _, item in top_items.iterrows():

            days = item["Days Remaining"]

            if days < 0:

                st.error(
                    f"❌ **{item['Food']}** — expired."
                )

            elif days <= 2:

                st.warning(
                    f"🔥 **{item['Food']}** — "
                    f"use within {days} day(s)."
                )

            elif days <= 5:

                st.info(
                    f"⚠️ **{item['Food']}** — "
                    f"use within {days} days."
                )

            else:

                st.success(
                    f"🟢 **{item['Food']}** — "
                    f"{days} days remaining."
                )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🍎 Smart Food Waste System"
)

st.sidebar.caption(
    "Prevent • Track • Reduce Food Waste"
)
