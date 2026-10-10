
import streamlit as st
import pandas as pd
import sqlite3
import random
from datetime import datetime, timedelta

DB_NAME = "fulfillment.db"

st.set_page_config(
    page_title="Fulfillment Hub",
    page_icon="📦",
    layout="wide"
)

def get_connection():
    return sqlite3.connect(DB_NAME)

def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                sku TEXT,
                product TEXT,
                variant TEXT,
                quantity INTEGER,
                priority TEXT,
                status TEXT,
                main_stock INTEGER,
                ship_by TEXT,
                courier TEXT DEFAULT ''
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        if count == 0:
            random.seed(42)

            products = [
                ("SKU001", "Wireless Mouse", "Black"),
                ("SKU002", "Keyboard", "White"),
                ("SKU003", "Laptop Stand", "Silver"),
                ("SKU004", "USB Hub", "Grey"),
                ("SKU005", "Headphones", "Black"),
                ("SKU006", "Webcam", "Black"),
                ("SKU007", "USB Cable", "White"),
                ("SKU008", "Phone Stand", "Blue"),
            ]

            statuses = [
                "Pending", "Picking", "Packed",
                "Awaiting Pickup", "Shipped"
            ]

            now = datetime.now()

            for i in range(1, 251):
                sku, product, variant = random.choice(products)

                conn.execute("""
                    INSERT INTO orders (
                        order_id, sku, product, variant,
                        quantity, priority, status,
                        main_stock, ship_by, courier
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"ORD{i:04d}",
                    sku,
                    product,
                    variant,
                    random.randint(1, 3),
                    "High" if random.random() < 0.2 else "Normal",
                    random.choice(statuses),
                    random.randint(0, 30),
                    (now + timedelta(
                        hours=random.randint(-3, 24)
                    )).isoformat(timespec="seconds"),
                    ""
                ))

def load_orders():
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM orders ORDER BY order_id",
            conn
        )

    df = df.rename(columns={
        "order_id": "Order ID",
        "sku": "SKU",
        "product": "Product",
        "variant": "Variant",
        "quantity": "Quantity",
        "priority": "Priority",
        "status": "Status",
        "main_stock": "Main Stock",
        "ship_by": "Ship By",
        "courier": "Courier"
    })

    df["Ship By"] = pd.to_datetime(df["Ship By"])
    df["Deadline Risk"] = df.apply(
        lambda row: "At Risk"
        if row["Status"] != "Shipped"
        and row["Ship By"] < datetime.now()
        else "On Track",
        axis=1
    )

    return df

def update_order(order_id, status=None, courier=None):
    with get_connection() as conn:
        if status is not None and courier is not None:
            conn.execute(
                "UPDATE orders SET status=?, courier=? WHERE order_id=?",
                (status, courier, order_id)
            )
        elif status is not None:
            conn.execute(
                "UPDATE orders SET status=? WHERE order_id=?",
                (status, order_id)
            )
        elif courier is not None:
            conn.execute(
                "UPDATE orders SET courier=? WHERE order_id=?",
                (courier, order_id)
            )

initialize_database()

# Create a separate inventory table for Warehouse 2
with get_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS secondary_inventory (
            sku TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            variant TEXT,
            available_stock INTEGER NOT NULL DEFAULT 0
        )
    """)

st.title("📦 Fulfillment Hub")
st.caption("XYZ E-commerce | Order Fulfillment Management")

orders = load_orders()


# Dashboard KPIs
total_orders = len(orders)

completed_orders = int(
    (orders["Status"] == "Shipped").sum()
)

pending_orders = int(
    (orders["Status"] == "Pending").sum()
)

in_progress_orders = int(
    orders["Status"].isin(
        ["Picking", "Packed", "Awaiting Pickup"]
    ).sum()
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Orders", total_orders)
c2.metric("Completed Orders", completed_orders)
c3.metric("Pending Orders", pending_orders)
c4.metric("Orders In Progress", in_progress_orders)

st.caption(
    "Completed = Shipped | In Progress = Picking, Packed or Awaiting Pickup"
)


st.divider()
st.subheader("📋 Order Management")

f1, f2, f3 = st.columns(3)

with f1:
    priority_filter = st.selectbox(
        "Priority", ["All", "High", "Normal"]
    )

with f2:
    status_filter = st.selectbox(
        "Status",
        ["All", "Pending", "Picking", "Packed",
         "Awaiting Pickup", "Shipped"]
    )

with f3:
    search = st.text_input("Search Order ID or Product")

filtered = orders.copy()

if priority_filter != "All":
    filtered = filtered[filtered["Priority"] == priority_filter]

if status_filter != "All":
    filtered = filtered[filtered["Status"] == status_filter]

if search:
    filtered = filtered[
        filtered["Order ID"].str.contains(search, case=False)
        | filtered["Product"].str.contains(search, case=False)
    ]

st.dataframe(filtered, use_container_width=True, hide_index=True)

st.divider()
st.subheader("⚠️ Orders Requiring Attention")
at_risk = orders[orders["Deadline Risk"] == "At Risk"]

if not at_risk.empty:
    st.dataframe(
        at_risk.head(20),
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("No orders are currently at risk.")

st.divider()
st.subheader("📦 Inventory & Stock Validation")

stock_order = st.selectbox(
    "Select Order for Stock Check",
    orders["Order ID"].tolist(),
    key="stock_order"
)

stock_row = orders[orders["Order ID"] == stock_order].iloc[0]
available = int(stock_row["Main Stock"])
required = int(stock_row["Quantity"])

s1, s2 = st.columns(2)
s1.metric("Available Main Stock", available)
s2.metric("Required Quantity", required)

if available >= required:
    st.success("Stock available for this order.")
else:
    st.error("Insufficient stock for this order.")

if st.button("Validate Stock"):
    if available >= required:
        st.success("Stock validation successful.")
    else:
        st.warning("Check secondary warehouse or replenish stock.")

st.divider()
st.subheader("🔄 Picking & Packing Workflow")

workflow_order = st.selectbox(
    "Select Order to Process",
    orders["Order ID"].tolist(),
    key="workflow_order"
)

row = orders[orders["Order ID"] == workflow_order].iloc[0]

st.write(f"**Product:** {row['Product']}")
st.write(f"**Quantity:** {row['Quantity']}")
st.write(f"**Current Status:** {row['Status']}")

if row["Status"] == "Pending":
    if st.button("Start Picking"):
        quantity = int(row["Quantity"])
        conn = get_connection()

        try:
            stock_row = conn.execute(
                """
                SELECT available_stock
                FROM inventory
                WHERE product = ? AND variant = ?
                """,
                (row["Product"], row["Variant"])
            ).fetchone()

            if stock_row is None:
                st.error("Product not found in inventory.")

            elif stock_row[0] < quantity:
                st.error("Insufficient inventory stock. Picking cannot start.")

            else:
                cursor = conn.execute(
                    """
                    UPDATE inventory
                    SET available_stock = available_stock - ?
                    WHERE product = ?
                    AND variant = ?
                    AND available_stock >= ?
                    """,
                    (
                        quantity,
                        row["Product"],
                        row["Variant"],
                        quantity
                    )
                )

                if cursor.rowcount == 1:
                    conn.execute(
                        "UPDATE orders SET status = ? WHERE order_id = ?",
                        ("Picking", workflow_order)
                    )
                    conn.commit()
                    st.success(
                        f"Picking started. {quantity} unit(s) deducted from inventory."
                    )
                    st.rerun()
                else:
                    conn.rollback()
                    st.error("Stock could not be updated. Please try again.")

        except sqlite3.Error as e:
            conn.rollback()
            st.error(f"Database error: {e}")

        finally:
            conn.close()

elif row["Status"] == "Picking":
    st.write(f"**Expected SKU:** {row['SKU']}")
    st.write(f"**Expected Variant:** {row['Variant']}")

    picked_sku = st.text_input(
        "Enter picked SKU",
        key=f"picked_sku_{workflow_order}"
    )

    picked_variant = st.text_input(
        "Enter picked variant",
        key=f"picked_variant_{workflow_order}"
    )

    if st.button("Mark as Packed"):
        if picked_sku.strip().casefold() != str(row["SKU"]).strip().casefold():
            st.error("Wrong SKU! Please verify the product.")

        elif picked_variant.strip().casefold() != str(row["Variant"]).strip().casefold():
            st.error("Wrong variant! Please verify the variant.")

        else:
            update_order(workflow_order, status="Packed")
            st.success("SKU and variant verified. Order packed successfully.")
            st.rerun()

elif row["Status"] == "Packed":
    st.info("Order is packed and waiting for courier handover.")

elif row["Status"] == "Awaiting Pickup":
    st.info("Order is awaiting courier pickup.")

elif row["Status"] == "Shipped":
    st.success("Order is shipped.")

st.divider()
st.subheader("🚚 Courier Pickup Management")

packed_orders = orders[
    orders["Status"] == "Packed"
]["Order ID"].tolist()

if packed_orders:
    courier_order = st.selectbox(
        "Select Packed Order",
        packed_orders,
        key="courier_order"
    )

    courier_name = st.selectbox(
        "Courier Partner",
        ["Blue Dart", "Delhivery", "DTDC", "Ecom Express"],
        key="courier_name"
    )

    if st.button("Confirm Courier Handover"):
        update_order(
            courier_order,
            status="Awaiting Pickup",
            courier=courier_name
        )
        st.success(
            f"{courier_order} assigned to {courier_name}. "
            "Status saved as Awaiting Pickup."
        )
        st.rerun()
else:
    st.info("No packed orders are currently available for handover.")

pickup_orders = orders[
    orders["Status"] == "Awaiting Pickup"
]["Order ID"].tolist()

if pickup_orders:
    pickup_order = st.selectbox(
        "Select Order Collected by Courier",
        pickup_orders,
        key="pickup_order"
    )

    if st.button("Confirm Courier Pickup"):
        update_order(pickup_order, status="Shipped")
        st.success("Courier pickup confirmed and saved.")
        st.rerun()

st.caption("Order status and courier assignments are stored in SQLite.")

st.divider()
st.divider()
st.subheader("🔄 Transfer Stock to Main Warehouse")

with get_connection() as conn:
    transfer_df = pd.read_sql_query(
        """
        SELECT sku, product, variant, available_stock
        FROM secondary_inventory
        WHERE available_stock > 0
        ORDER BY sku
        """,
        conn
    )

if transfer_df.empty:
    st.info("Warehouse 2 has no stock available to transfer.")
else:
    with st.form("transfer_stock_form"):
        transfer_sku = st.selectbox(
            "Select product to transfer",
            transfer_df["sku"].tolist(),
            format_func=lambda sku: (
                f"{sku} - "
                f"{transfer_df.loc[transfer_df['sku'] == sku, 'product'].iloc[0]} "
                f"({transfer_df.loc[transfer_df['sku'] == sku, 'variant'].iloc[0]})"
            )
        )

        selected_stock = int(
            transfer_df.loc[
                transfer_df["sku"] == transfer_sku,
                "available_stock"
            ].iloc[0]
        )

        st.write(f"Available in Warehouse 2: {selected_stock}")

        transfer_qty = st.number_input(
            "Quantity to transfer",
            min_value=1,
            max_value=selected_stock,
            value=1,
            step=1
        )

        if st.form_submit_button("Transfer to Main Warehouse"):
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE secondary_inventory
                    SET available_stock = available_stock - ?
                    WHERE sku = ? AND available_stock >= ?
                    """,
                    (int(transfer_qty), transfer_sku, int(transfer_qty))
                )

                if cursor.rowcount == 1:
                    main_cursor = conn.execute(
                        """
                        UPDATE inventory
                        SET available_stock = available_stock + ?
                        WHERE sku = ?
                        """,
                        (int(transfer_qty), transfer_sku)
                    )

                    if main_cursor.rowcount == 1:
                        conn.commit()
                        st.success(
                            f"Transferred {int(transfer_qty)} unit(s) to Main Warehouse."
                        )
                        st.rerun()
                    else:
                        conn.rollback()
                        st.error("Product not found in Main Warehouse.")
                else:
                    conn.rollback()
                    st.error("Transfer failed. Please check available stock.")

st.subheader("📦 Inventory Management")

st.divider()
st.subheader("🏬 Warehouse 2 — Secondary Stock")


with get_connection() as conn:

    secondary_df = pd.read_sql_query(
        """
        SELECT sku AS SKU, product AS Product,
               variant AS Variant,
               available_stock AS 'Available Stock'
        FROM secondary_inventory
        ORDER BY sku
        """,
        conn
    )

st.dataframe(secondary_df, use_container_width=True, hide_index=True)

st.write("Add stock to Warehouse 2")

with st.form("add_secondary_stock_form"):
    with get_connection() as conn:
        products_df = pd.read_sql_query(
            "SELECT sku, product, variant FROM inventory ORDER BY sku",
            conn
        )

    selected_sku = st.selectbox(
        "Select Product",
        products_df["sku"].tolist(),
        format_func=lambda sku: (
            f"{sku} - "
            f"{products_df.loc[products_df['sku'] == sku, 'product'].iloc[0]} "
            f"({products_df.loc[products_df['sku'] == sku, 'variant'].iloc[0]})"
        )
    )

    stock_to_add = st.number_input(
        "Quantity to Add",
        min_value=1,
        step=1
    )

    add_stock = st.form_submit_button("Add Stock to Warehouse 2")

    if add_stock:
        product_row = products_df[products_df["sku"] == selected_sku].iloc[0]

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO secondary_inventory
                    (sku, product, variant, available_stock)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    available_stock = available_stock + excluded.available_stock
                """,
                (
                    product_row["sku"],
                    product_row["product"],
                    product_row["variant"],
                    int(stock_to_add)
                )
            )

        st.success(f"Added {int(stock_to_add)} unit(s) to Warehouse 2.")
        st.rerun()


with sqlite3.connect("fulfillment.db") as conn:
    inventory_df = pd.read_sql_query(
        """
        SELECT
            sku AS 'SKU',
            product AS 'Product',
            variant AS 'Variant',
            available_stock AS 'Available Stock',
            reorder_level AS 'Reorder Level'
        FROM inventory
        ORDER BY sku
        """,
        conn
    )

inventory_df["Stock Status"] = inventory_df.apply(
    lambda row: "Low Stock"
    if row["Available Stock"] <= row["Reorder Level"]
    else "In Stock",
    axis=1
)

total_products = len(inventory_df)
low_stock_count = int(
    (inventory_df["Stock Status"] == "Low Stock").sum()
)

inv1, inv2 = st.columns(2)
inv1.metric("Total Products", total_products)
inv2.metric("Low Stock Products", low_stock_count)

st.dataframe(
    inventory_df,
    use_container_width=True,
    hide_index=True
)

low_stock_products = inventory_df[
    inventory_df["Stock Status"] == "Low Stock"
]

if not low_stock_products.empty:
    st.warning("Some products have low stock. Replenishment may be needed.")
    st.dataframe(
        low_stock_products,
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("All products have sufficient stock.")
   