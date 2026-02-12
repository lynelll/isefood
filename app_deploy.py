import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="이세푸드", layout="wide")
st.title("🛒 이세푸드 공동구매 관리")

# -----------------------------------
# 세션 초기화
# -----------------------------------
if "items" not in st.session_state:
    st.session_state.items = {}

# -----------------------------------
# 7일 지난 품목 자동 삭제
# -----------------------------------
def clean_old_items():
    now = datetime.now()
    expired = []
    for item, data in st.session_state.items.items():
        if now - data["created_at"] > timedelta(days=7):
            expired.append(item)
    for item in expired:
        del st.session_state.items[item]

clean_old_items()

# ===================================
# 1️⃣ 품목 추가
# ===================================
st.header("📦 품목 추가")

col1, col2 = st.columns([3,1])

with col1:
    new_item = st.text_input("품목 이름")

with col2:
    if st.button("추가"):
        if new_item and new_item not in st.session_state.items:
            st.session_state.items[new_item] = {
                "created_at": datetime.now(),
                "orders": pd.DataFrame(
                    columns=["이름", "핸드폰번호", "수량"]
                )
            }
            st.success(f"{new_item} 추가 완료")

st.markdown("---")

# ===================================
# 2️⃣ 주문자 추가
# ===================================
st.header("🧾 주문자 추가")

if st.session_state.items:

    item_list = list(st.session_state.items.keys())

    selected_item = st.selectbox("품목 선택", item_list)

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
                new_row = pd.DataFrame(
                    [[name, phone, qty]],
                    columns=["이름", "핸드폰번호", "수량"]
                )
                st.session_state.items[selected_item]["orders"] = pd.concat(
                    [
                        st.session_state.items[selected_item]["orders"],
                        new_row
                    ],
                    ignore_index=True
                )
                st.success("주문 추가 완료")

    st.markdown("---")

    # ===================================
    # 3️⃣ 주문 테이블 표시
    # ===================================
    st.subheader(f"📋 {selected_item} 주문 목록")

    order_df = st.session_state.items[selected_item]["orders"]

    st.dataframe(order_df, use_container_width=True)

    if not order_df.empty:
        total_qty = order_df["수량"].sum()
        st.info(f"총 주문 수량: {total_qty}개")

else:
    st.warning("먼저 품목을 추가해주세요.")
