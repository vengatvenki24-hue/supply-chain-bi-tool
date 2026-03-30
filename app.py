import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="On-Time Delivery Performance Index", layout="wide")

st.title("Supply Chain On-Time Delivery Performance Index")
st.write(
    "Upload a supply chain CSV file to measure on-time delivery performance by product category and region."
)

# STUDENT NOTE: define the standardized column names the metric needs after mapping
STANDARD_COLUMNS = {
    "order_id": "order_id",
    "days_for_shipment_scheduled": "days_for_shipment_scheduled",
    "days_for_shipping_real": "days_for_shipping_real",
    "category_name": "category_name",
    "order_region": "order_region",
    "order_item_quantity": "order_item_quantity",
}

uploaded_file = st.file_uploader("Upload your dataset (CSV)", type="csv")

if uploaded_file is not None:
    # STUDENT NOTE: load the uploaded CSV into a DataFrame for validation and analysis
    df = pd.read_csv(uploaded_file, encoding="latin1")

    # STUDENT NOTE: remove extra spaces from column names to reduce upload errors
    df.columns = df.columns.str.strip()

    st.subheader("Raw Data Preview")
    st.dataframe(df.head(10))

    st.subheader("Column Mapping")
    st.write("Map your uploaded columns to the fields required for this metric.")

    all_columns = df.columns.tolist()

    # STUDENT NOTE: let the user map their dataset columns so the app works on equivalent files
    order_id_col = st.selectbox("Select the shipment/order ID column", all_columns)
    scheduled_col = st.selectbox("Select the scheduled delivery days column", all_columns)
    actual_col = st.selectbox("Select the actual delivery days column", all_columns)
    category_col = st.selectbox("Select the product category column", all_columns)
    region_col = st.selectbox("Select the shipping region column", all_columns)
    quantity_col = st.selectbox("Select the order quantity column", all_columns)

    selected_columns = [
        order_id_col,
        scheduled_col,
        actual_col,
        category_col,
        region_col,
        quantity_col,
    ]

    # STUDENT NOTE: check whether the user selected the same column more than once
    if len(set(selected_columns)) < len(selected_columns):
        st.error("Each required field must be mapped to a different column.")
        st.stop()

    # STUDENT NOTE: create a clean working DataFrame with standardized column names
    df_clean = df[selected_columns].copy()
    df_clean.columns = list(STANDARD_COLUMNS.values())

    # STUDENT NOTE: remove rows with missing values so delay and rate calculations are valid
    df_clean = df_clean.dropna()

    # STUDENT NOTE: convert delivery day columns to numeric values to avoid calculation errors
    df_clean["days_for_shipment_scheduled"] = pd.to_numeric(
        df_clean["days_for_shipment_scheduled"], errors="coerce"
    )
    df_clean["days_for_shipping_real"] = pd.to_numeric(
        df_clean["days_for_shipping_real"], errors="coerce"
    )
    df_clean["order_item_quantity"] = pd.to_numeric(
        df_clean["order_item_quantity"], errors="coerce"
    )

    # STUDENT NOTE: remove rows that became invalid after numeric conversion
    df_clean = df_clean.dropna()

    if df_clean.empty:
        st.error("No valid rows remain after cleaning. Please check your column mapping and data types.")
        st.stop()

    st.subheader("Cleaned Data Preview")
    st.dataframe(df_clean.head(10))

    st.subheader("Interactive Filters")

    # STUDENT NOTE: let the user filter regions so KPI values and charts update dynamically
    available_regions = sorted(df_clean["order_region"].astype(str).unique().tolist())
    selected_regions = st.multiselect(
        "Filter by shipping region",
        options=available_regions,
        default=available_regions
    )

    # STUDENT NOTE: let the user choose how many categories to show in ranking charts
    top_n = st.slider(
        "Number of categories to show in category charts",
        min_value=5,
        max_value=20,
        value=10
    )

    # STUDENT NOTE: apply the selected region filter so all outputs respond to user input
    filtered_df = df_clean[df_clean["order_region"].astype(str).isin(selected_regions)].copy()

    if filtered_df.empty:
        st.error("The selected filter returned no rows. Please choose at least one region with data.")
        st.stop()

    # STUDENT NOTE: calculate shipment delay in days by comparing actual and scheduled delivery times
    filtered_df["delay_days"] = (
        filtered_df["days_for_shipping_real"] - filtered_df["days_for_shipment_scheduled"]
    )

    # STUDENT NOTE: create an on-time flag where early or exactly on-schedule shipments count as on time
    filtered_df["on_time"] = filtered_df["delay_days"].apply(lambda x: 1 if x <= 0 else 0)

    # STUDENT NOTE: summarize delivery performance by category for ranking and charting
    performance = (
        filtered_df.groupby("category_name")
        .agg(
            total_shipments=("order_id", "count"),
            on_time_rate=("on_time", "mean"),
            average_delay=("delay_days", "mean"),
        )
        .reset_index()
    )

    # STUDENT NOTE: convert the on-time rate to a percentage for business reporting
    performance["on_time_rate"] = performance["on_time_rate"] * 100

    # STUDENT NOTE: calculate the average delay using only late shipments for a more meaningful KPI
    late_shipments = filtered_df[filtered_df["delay_days"] > 0].copy()
    average_days_late = late_shipments["delay_days"].mean() if not late_shipments.empty else 0.0

    # STUDENT NOTE: calculate the overall on-time delivery rate for the filtered dataset
    overall_on_time_rate = filtered_df["on_time"].mean() * 100

    # STUDENT NOTE: identify the worst-performing category based on the lowest on-time rate
    worst_category_row = performance.sort_values("on_time_rate", ascending=True).iloc[0]
    worst_category_name = str(worst_category_row["category_name"])

    st.subheader("Headline KPIs")
    col1, col2, col3 = st.columns(3)

    # STUDENT NOTE: display the primary KPI showing how often shipments arrive on time
    col1.metric("Overall On-Time Rate", f"{overall_on_time_rate:.2f}%")

    # STUDENT NOTE: display the weakest category so managers can focus intervention efforts
    col2.metric("Worst-Performing Category", worst_category_name)

    # STUDENT NOTE: display the average number of days late for delayed shipments only
    col3.metric("Average Days Late", f"{average_days_late:.2f}")

    st.subheader("Performance Table")

    # STUDENT NOTE: rank categories from weakest to strongest on-time performance for easy review
    performance_display = performance.sort_values("on_time_rate", ascending=True).copy()
    st.dataframe(performance_display)

    st.subheader("Chart 1: On-Time Delivery Rate by Category")

    # STUDENT NOTE: limit the chart to the weakest categories selected by the user for clearer display
    bottom_categories = (
        performance.sort_values("on_time_rate", ascending=True)
        .head(top_n)
        .copy()
    )

    fig_bar = px.bar(
        bottom_categories,
        x="on_time_rate",
        y="category_name",
        orientation="h",
        title=f"Bottom {top_n} Categories by On-Time Delivery Rate",
        labels={
            "on_time_rate": "On-Time Delivery Rate (%)",
            "category_name": "Product Category",
        },
    )
    fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Chart 2: Late Delivery Heatmap")

    # STUDENT NOTE: keep the highest-delay categories and most common regions so the heatmap remains readable
    top_categories_delay = (
        filtered_df.groupby("category_name")["delay_days"]
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
        .index
    )

    top_regions_volume = (
        filtered_df["order_region"]
        .value_counts()
        .head(10)
        .index
    )

    # STUDENT NOTE: filter the dataset to the most relevant region-category combinations for the heatmap
    heatmap_df = filtered_df[
        (filtered_df["category_name"].isin(top_categories_delay)) &
        (filtered_df["order_region"].isin(top_regions_volume))
    ].copy()

    # STUDENT NOTE: compute average delay for each region-category combination
    heatmap_data = heatmap_df.pivot_table(
        index="order_region",
        columns="category_name",
        values="delay_days",
        aggfunc="mean"
    )

    fig_heatmap = px.imshow(
        heatmap_data,
        title="Average Delay Heatmap (Top Regions vs Highest-Delay Categories)",
        labels=dict(x="Product Category", y="Shipping Region", color="Avg Delay"),
        aspect="auto"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.subheader("Interpretation")

    # STUDENT NOTE: provide a fixed business explanation so the app communicates insight without using AI
    st.info(
        "This tool measures how reliably shipments are delivered on time across product categories and regions. "
        "A higher on-time rate means a category is performing more consistently against its promised delivery window. "
        "The weakest category highlights where delivery performance is under the most pressure, while the heatmap shows "
        "which region-category combinations are creating the biggest delay problems. Business users should focus first "
        "on categories with low on-time rates and routes with persistent positive delay values, because those areas are "
        "most likely to reduce customer satisfaction and create operational inefficiency."
    )

else:
    st.warning("Upload a CSV file to begin.")