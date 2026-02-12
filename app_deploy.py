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

# ===================================================
# 🔹 상단 한 행 (3컬럼)
# ===================================================
col_item, col_order, col_search = st.columns(3)

# ----------------------------
# 📦 품목 추가
# ----------------------------
with col_item:
    st.subheader("📦 품목 추가")

    new_item = st.text_input("품목 이름", key="new_item")

    if st.button("품목 추가"):
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

# ----------------------------
# 🧾 주문자 추가
# ----------------------------
with col_order:
    st.subheader("🧾 주문자 추가")

    if not items_df.empty:

        selected_item = st.selectbox(
            "품목 선택",
            items_df["item_name"].tolist(),
            key="select_item"
        )

        name = st.text_input("이름", key="order_name")
        phone = st.text_input("핸드폰번호", key="order_phone")
        qty = st.number_input("수량", min_value=1, step=1, key="order_qty")

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

# ----------------------------
# 🔍 주문 검색
# ----------------------------
with col_search:
    st.subheader("🔍 주문 검색")

    search_name = st.text_input("이름 검색", key="search_name")
    search_phone_last4 = st.text_input("전화번호 뒤 4자리", key="search_phone")

# ===================================================
# 🔹 아래 전체 주문 목록
# ===================================================
st.markdown("---")
st.header("📋 전체 주문 목록 (이름 기준)")

if not orders_df.empty:

    orders_df["qty"] = orders_df["qty"].astype(int)
    orders_df["received"] = orders_df["received"].astype(str) == "True"

    filtered_df = orders_df.copy()

    if search_name:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search_name, na=False)
        ]

    if search_phone_last4 and len(search_phone_last4) == 4:
        filtered_df = filtered_df[
            filtered_df["phone"].str[-4:] == search_phone_last4
        ]

    # 🔥 사람 기준 pivot
    pivot_df = filtered_df.pivot_table(
        index=["name", "phone"],
        columns="item_name",
        values="qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # 🔥 모든 품목 컬럼 강제 생성
    all_items = items_df["item_name"].tolist()

    for item in all_items:
        if item not in pivot_df.columns:
            pivot_df[item] = 0

    # 컬럼 정렬
    pivot_df = pivot_df[["name", "phone"] + all_items]

    # 🔥 사람 기준 수령 여부
    received_map = (
        filtered_df.groupby(["name", "phone"])["received"]
        .all()
        .reset_index()
        .rename(columns={"received": "수령"})
    )

    pivot_df = pivot_df.merge(received_map, on=["name", "phone"], how="left")
    pivot_df["수령"] = pivot_df["수령"].fillna(False)

    # 🔥 수령 체크박스 표시
    edited_df = st.data_editor(
        pivot_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "수령": st.column_config.CheckboxColumn("수령")
        },
        key="pivot_editor"
    )

    # 🔥 수령 저장
    if st.button("💾 수령 상태 저장"):

        for _, row in edited_df.iterrows():
            name = row["name"]
            phone = row["phone"]
            received_value = str(row["수령"])

            mask = (
                (orders_df["name"] == name) &
                (orders_df["phone"] == phone)
            )

            orders_df.loc[mask, "received"] = received_value

        if save_csv_to_github(orders_df, ORDER_PATH, "update received status"):
            st.success("수령 상태 저장 완료")
            st.rerun()
        else:
            st.error("저장 실패")

else:
    st.info("아직 주문이 없습니다.")
