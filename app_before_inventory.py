
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

st.title("📦 Fulfillment Hub")
st.caption("XYZ E-commerce | Order Fulfillment Management")

orders = load_orders()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Orders", len(orders))
c2.metric("Priority Orders", int((orders["Priority"] == "High").sum()))
c3.metric("Orders At Risk", int((orders["Deadline Risk"] == "At Risk").sum()))
c4.metric("Awaiting Pickup", int((orders["Status"] == "Awaiting Pickup").sum()))

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
        if int(row["Main Stock"]) >= int(row["Quantity"]):
            update_order(workflow_order, status="Picking")
            st.success("Picking started and saved to database.")
            st.rerun()
        else:
            st.error("Insufficient stock. Picking cannot start.")

elif row["Status"] == "Picking":
    if st.button("Mark as Packed"):
        update_order(workflow_order, status="Packed")
        st.success("Packed status saved to database.")
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
