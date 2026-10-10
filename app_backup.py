
import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Fulfillment Hub",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Fulfillment Hub")
st.caption("XYZ E-commerce | Order Fulfillment Management")

# Generate 250 sample orders
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
    "Pending",
    "Picking",
    "Packed",
    "Awaiting Pickup",
    "Shipped"
]

orders_list = []
now = datetime.now()

for i in range(1, 251):
    sku, product, variant = random.choice(products)

    priority = "High" if random.random() < 0.2 else "Normal"
    status = random.choice(statuses)
    main_stock = random.randint(0, 30)
    quantity = random.randint(1, 3)

    deadline = now + timedelta(
        hours=random.randint(-3, 24)
    )

    orders_list.append({
        "Order ID": f"ORD{i:04d}",
        "SKU": sku,
        "Product": product,
        "Variant": variant,
        "Quantity": quantity,
        "Priority": priority,
        "Status": status,
        "Main Stock": main_stock,
        "Ship By": deadline,
    })

orders = pd.DataFrame(orders_list)

# Identify orders that may miss their deadline
orders["Deadline Risk"] = orders.apply(
    lambda row: "At Risk"
    if row["Status"] != "Shipped"
    and row["Ship By"] < datetime.now()
    else "On Track",
    axis=1
)

# Dashboard metrics
total_orders = len(orders)
priority_orders = int(
    (orders["Priority"] == "High").sum()
)
at_risk_count = int(
    (orders["Deadline Risk"] == "At Risk").sum()
)
awaiting_pickup = int(
    (orders["Status"] == "Awaiting Pickup").sum()
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Orders", total_orders)
col2.metric("Priority Orders", priority_orders)
col3.metric("Orders At Risk", at_risk_count)
col4.metric("Awaiting Pickup", awaiting_pickup)

st.divider()

# Order management
st.subheader("📋 Order Management")

col1, col2, col3 = st.columns(3)

with col1:
    priority_filter = st.selectbox(
        "Filter by Priority",
        ["All", "High", "Normal"]
    )

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All"] + statuses
    )

with col3:
    search = st.text_input(
        "Search Order ID or Product"
    )

filtered = orders.copy()

if priority_filter != "All":
    filtered = filtered[
        filtered["Priority"] == priority_filter
    ]

if status_filter != "All":
    filtered = filtered[
        filtered["Status"] == status_filter
    ]

if search:
    filtered = filtered[
        filtered["Order ID"].str.contains(
            search, case=False
        )
        | filtered["Product"].str.contains(
            search, case=False
        )
    ]

st.write(f"Showing {len(filtered)} order(s)")

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True
)

# Orders requiring attention
st.subheader("⚠️ Orders Requiring Attention")

at_risk = orders[
    orders["Deadline Risk"] == "At Risk"
].copy()

if len(at_risk) > 0:
    st.warning(
        f"{len(at_risk)} order(s) may miss their shipping deadline."
    )
    st.dataframe(
        at_risk.head(20),
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("No orders are currently at risk.")

st.success("Fulfillment Hub is running successfully!")

st.divider()

st.subheader("🔄 Update Order Status")

order_ids = orders["Order ID"].tolist()

selected_order = st.selectbox(
    "Select Order ID",
    order_ids,
    key="update_order_id"
)

current_status = orders.loc[
    orders["Order ID"] == selected_order,
    "Status"
].iloc[0]

st.write(f"Current Status: **{current_status}**")

new_status = st.selectbox(
    "Choose New Status",
    statuses,
    index=statuses.index(current_status),
    key="new_order_status"
)

if st.button("Update Order Status"):
    orders.loc[
        orders["Order ID"] == selected_order,
        "Status"
    ] = new_status

    st.success(
        f"{selected_order} status updated to {new_status}!"
    )
    
st.divider()

st.subheader("📦 Inventory & Stock Validation")

selected_stock_order = st.selectbox(
    "Select Order for Stock Check",
    orders["Order ID"].tolist(),
    key="stock_check_order"
)

stock_row = orders[
    orders["Order ID"] == selected_stock_order
].iloc[0]

available_stock = int(stock_row["Main Stock"])
required_quantity = int(stock_row["Quantity"])

col1, col2 = st.columns(2)

col1.metric("Available Main Stock", available_stock)
col2.metric("Required Quantity", required_quantity)

if available_stock >= required_quantity:
    st.success("Stock Available — order can proceed to picking.")
else:
    st.error("Insufficient Stock — order cannot proceed to picking.")

if st.button("Validate Stock", key="validate_stock"):
    if available_stock >= required_quantity:
        st.success(
            f"Stock validated for {selected_stock_order}."
        )
    else:
        st.warning(
            f"{selected_stock_order} needs more stock before picking."
        )

st.divider()

st.subheader("📦 Picking & Packing Workflow")

workflow_order_id = st.selectbox(
    "Select Order to Process",
    orders["Order ID"].tolist(),
    key="workflow_order"
)

order_index = orders.index[
    orders["Order ID"] == workflow_order_id
][0]

workflow_order = orders.loc[order_index]
workflow_status = workflow_order["Status"]

st.write(f"**Product:** {workflow_order['Product']}")
st.write(f"**Quantity Required:** {workflow_order['Quantity']}")
st.write(f"**Current Status:** {workflow_status}")

if workflow_status == "Shipped":
    st.success("This order has already been shipped.")

elif workflow_status == "Awaiting Pickup":
    st.info("Order is packed and waiting for courier pickup.")

elif workflow_status == "Packed":
    st.info("Order is packed and ready for courier pickup.")

elif workflow_status == "Picking":
    if st.button("Mark as Packed", key="mark_packed"):
        orders.loc[order_index, "Status"] = "Packed"
        st.success("Order packed successfully!")
        st.rerun()

elif workflow_status == "Pending":
    if st.button("Start Picking", key="start_picking"):
        available = int(workflow_order["Main Stock"])
        required = int(workflow_order["Quantity"])

        if available >= required:
            orders.loc[order_index, "Status"] = "Picking"
            st.success("Picking started successfully!")
            st.rerun()
        else:
            st.error(
                "Insufficient stock. Picking cannot start."
            )

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
        "Select Courier Partner",
        ["Blue Dart", "Delhivery", "DTDC", "Ecom Express"],
        key="courier_partner"
    )

    st.write(f"**Selected Order:** {courier_order}")
    st.write(f"**Courier Partner:** {courier_name}")

    if st.button("Confirm Courier Handover"):
        orders.loc[
            orders["Order ID"] == courier_order,
            "Status"
        ] = "Shipped"

        st.success(
            f"{courier_order} handed over to {courier_name}!"
        )
        st.rerun()

else:
    st.info(
        "No packed orders are currently waiting for courier pickup."
    )




