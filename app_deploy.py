import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="이세푸드", layout="wide")
st.title("🛒 이세푸드 공동구매 관리")

# -----------------------------------
# 파일 경로
# -----------------------------------
ITEM_FILE = "items.csv"
ORDER_FILE = "orders.csv"

# -----------------------------------
# 파일 없으면 생성
# -----------------------------------
if not os.path.exists(ITEM_FILE):
    pd.DataFrame(columns=["item_name", "created_at"]).to_csv(ITEM_FILE, index=False)

if not os.path.exists(ORDER_FILE):
    pd.DataFrame(
        columns=["item_name", "name", "phone", "qty", "received", "created_at"]
    ).to_csv(ORDER_FILE, index=False)

# -----------------------------------
# 데이터 로드 (phone 문자열 유지)
# -----------------------------------
items_df = pd.read_csv(
    ITEM_FILE,
    dtype={"item_name": str, "created_at": str}
)

orders_df = pd.read_csv(
    ORDER_FILE,
    dtype={
        "item_name": str,
        "name": str,
        "phone": str,   # 앞자리 0 유지
        "qty": int,
        "received": bool,
        "created_at": str,
    },
)

# ===================================
# 1️⃣ 품목 추가
# ===================================
st.header("📦 품목 추가")

col1, col2 = st.columns([3, 1])

with col1:
    new_item = st.text_input("품목 이름")

with col2:
    if st.button("추가"):
        if new_item and new_item not in items_df["item_name"].values:
            new_row = pd.DataFrame(
                [[new_item, datetime.now().strftime("%Y-%m-%d")]],
                columns=["item_name", "created_at"]
            )

            items_df = pd.concat([items_df, new_row], ignore_index=True)
            items_df.to_csv(ITEM_FILE, index=False)

            st.success(f"{new_item} 추가 완료")
            st.rerun()

st.markdown("---")

# ===================================
# 2️⃣ 주문자 추가
# ===================================
st.header("🧾 주문자 추가")

if not items_df.empty:

    selected_item = st.selectbox("품목 선택", items_df["item_name"].tolist())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        name = st.text_input("이름")

    with col2:
        phone = st.text_input("핸드폰번호")

    with col3:
        qty = st.number_input("수량", min_value=1, step=1)

    with col4:
        if st.button("주문 추가"):
            if name and phone:

                new_order = pd.DataFrame(
                    [[
                        selected_item,
                        name,
                        str(phone),  # 문자열 강제
                        qty,
                        False,
                        datetime.now().strftime("%Y-%m-%d")
                    ]],
                    columns=[
                        "item_name",
                        "name",
                        "phone",
                        "qty",
                        "received",
                        "created_at",
                    ],
                )

                orders_df = pd.concat([orders_df, new_order], ignore_index=True)
                orders_df.to_csv(ORDER_FILE, index=False)

                st.success("주문 추가 완료")
                st.rerun()

    st.markdown("---")

    # ===================================
    # 3️⃣ 주문 테이블 표시
    # ===================================
    st.subheader(f"📋 {selected_item} 주문 목록")

    filtered_orders = orders_df[orders_df["item_name"] == selected_item]

    st.dataframe(filtered_orders, use_container_width=True)

    if not filtered_orders.empty:
        total_qty = filtered_orders["qty"].sum()
        st.info(f"총 주문 수량: {total_qty}개")

else:
    st.warning("먼저 품목을 추가해주세요.")
