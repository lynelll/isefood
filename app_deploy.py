import streamlit as st
import pandas as pd
import requests
import base64
import json
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="이세푸드", layout="wide")
st.title("🛒 이세푸드 공동구매 관리")

# ---------------------------------------------------
# GitHub 설정
# ---------------------------------------------------
GITHUB_TOKEN  = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO   = st.secrets["GITHUB_REPO"]
GITHUB_BRANCH = st.secrets["GITHUB_BRANCH"]

ITEM_PATH  = "items.csv"
ORDER_PATH = "orders.csv"

headers = {"Authorization": f"token {GITHUB_TOKEN}"}


# ---------------------------------------------------
# GitHub에서 CSV 불러오기
# ---------------------------------------------------
def load_csv_from_github(path, columns):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    res = requests.get(url, headers=headers)

    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode()
        return pd.read_csv(StringIO(content), dtype=str)
    else:
        return pd.DataFrame(columns=columns)


# ---------------------------------------------------
# GitHub에 CSV 저장
# ---------------------------------------------------
def save_csv_to_github(df, path, message):

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    # ⭐ 여기 수정
    get_url = f"{url}?ref={GITHUB_BRANCH}"

    old = requests.get(get_url, headers=headers)

    sha = None
    if old.status_code == 200:
        sha = old.json().get("sha")

    content = base64.b64encode(df.to_csv(index=False).encode()).decode()

    payload = {
        "message": message,
        "content": content,
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha

    res = requests.put(url, headers=headers, data=json.dumps(payload))

    st.write("Status:", res.status_code)
    st.write("Response:", res.text)

    return res.status_code in [200, 201]




# ---------------------------------------------------
# 데이터 로드
# ---------------------------------------------------
items_df = load_csv_from_github(
    ITEM_PATH,
    ["item_name", "created_at"]
)

orders_df = load_csv_from_github(
    ORDER_PATH,
    ["item_name", "name", "phone", "qty", "received", "created_at"]
)

# ===================================
# 1️⃣ 품목 추가
# ===================================
st.header("📦 품목 추가")

col1, col2 = st.columns([3,1])

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

            if save_csv_to_github(items_df, ITEM_PATH, "update items"):
                st.success("품목 저장 완료")
                st.rerun()
            else:
                st.error("저장 실패")

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
                        str(phone),
                        qty,
                        "False",
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

                if save_csv_to_github(orders_df, ORDER_PATH, "update orders"):
                    st.success("주문 저장 완료")
                    st.rerun()
                else:
                    st.error("저장 실패")

    st.markdown("---")

    st.subheader("📋 전체 주문 목록")

    if not orders_df.empty:

        # 타입 정리
        orders_df["qty"] = orders_df["qty"].astype(int)
        orders_df["received"] = orders_df["received"].astype(str) == "True"

        edited_orders = st.data_editor(
            orders_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "received": st.column_config.CheckboxColumn("수령"),
            },
            key="orders_editor"
        )

        if st.button("💾 수령 상태 저장"):
            # 다시 문자열로 변환해서 저장
            edited_orders["received"] = edited_orders["received"].astype(str)

            if save_csv_to_github(edited_orders, ORDER_PATH, "update received status"):
                st.success("수령 상태 저장 완료")
                st.rerun()
            else:
                st.error("저장 실패")

        total_qty = edited_orders["qty"].sum()
        received_qty = edited_orders[edited_orders["received"] == True]["qty"].sum()

        st.info(f"전체 주문 수량: {total_qty}개 / 수령 완료: {received_qty}개")

    else:
        st.info("아직 주문이 없습니다.")


else:
    st.warning("먼저 품목을 추가해주세요.")
