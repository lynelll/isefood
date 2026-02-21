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

ITEM_PATH  = "./data/items.csv"
ORDER_PATH = "./data/orders.csv"

headers = {"Authorization": f"token {GITHUB_TOKEN}"}

# ---------------------------------------------------
# GitHub CSV 불러오기
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
# GitHub CSV 저장
# ---------------------------------------------------
def save_csv_to_github(df, path, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    get_url = f"{url}?ref={GITHUB_BRANCH}"

    old = requests.get(get_url, headers=headers)
    sha = old.json().get("sha") if old.status_code == 200 else None

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
    ["item_name", "name", "phone", "qty", "received", "created_at", "person_id"]
)

if not orders_df.empty:
    orders_df["phone"] = orders_df["phone"].str.replace("-", "").str.strip()

    if "person_id" not in orders_df.columns:
        orders_df["person_id"] = orders_df["name"] + "_" + orders_df["phone"]

# ===================================================
# 🔀 모드 선택
# ===================================================
mode = st.radio(
    "모드 선택",
    ["🧾 주문 입력 모드", "📦 수령 확인 모드"],
    horizontal=True
)

# ===================================================
# 🧾 주문 입력 모드
# ===================================================
if mode == "🧾 주문 입력 모드":

    col_item, col_order = st.columns(2)

    with col_item:
        st.subheader("📦 품목 추가")
        new_item = st.text_input("품목 이름")

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

    with col_order:
        st.subheader("🧾 주문자 추가")

        if not items_df.empty:
            selected_item = st.selectbox("품목 선택", items_df["item_name"].tolist())
            name = st.text_input("이름")
            phone = st.text_input("핸드폰번호")
            qty = st.number_input("수량", min_value=1, step=1)

            if st.button("주문 추가"):
                if name and phone:
                    phone = phone.replace("-", "").strip()
                    person_id = name + "_" + phone

                    new_order = pd.DataFrame(
                        [[
                            selected_item,
                            name,
                            phone,
                            qty,
                            "False",
                            datetime.now().strftime("%Y-%m-%d"),
                            person_id
                        ]],
                        columns=[
                            "item_name", "name", "phone",
                            "qty", "received", "created_at",
                            "person_id"
                        ],
                    )

                    orders_df = pd.concat([orders_df, new_order], ignore_index=True)

                    if save_csv_to_github(orders_df, ORDER_PATH, "update orders"):
                        st.success("주문 저장 완료")
                        st.rerun()

    # ----------------------------
    # 📋 수정 가능한 주문 목록
    # ----------------------------
    st.markdown("---")
    st.subheader("📋 현재 주문 목록 (수정 가능)")

    if not orders_df.empty:

        orders_df["qty"] = orders_df["qty"].astype(int)

        pivot_df = orders_df.pivot_table(
            index=["person_id", "name", "phone"],
            columns="item_name",
            values="qty",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        all_items = items_df["item_name"].tolist()

        for item in all_items:
            if item not in pivot_df.columns:
                pivot_df[item] = 0

        pivot_df = pivot_df[["person_id", "name", "phone"] + all_items]

        edited_df = st.data_editor(
            pivot_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "person_id": None  # 🔥 완전 숨김
            }
        )

        if st.button("💾 주문자 정보 저장"):

            for _, row in edited_df.iterrows():

                old_person_id = row["person_id"]
                new_name = row["name"]
                new_phone = row["phone"].replace("-", "").strip()
                new_person_id = new_name + "_" + new_phone

                mask = orders_df["person_id"] == old_person_id

                orders_df.loc[mask, "name"] = new_name
                orders_df.loc[mask, "phone"] = new_phone
                orders_df.loc[mask, "person_id"] = new_person_id

            if save_csv_to_github(orders_df, ORDER_PATH, "update order info"):
                st.success("주문자 정보 수정 완료")
                st.rerun()

    else:
        st.info("아직 주문이 없습니다.")