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
    ["item_name", "name", "phone", "qty", "received", "created_at"]
)

if not orders_df.empty:
    orders_df["phone"] = orders_df["phone"].str.replace("-", "").str.strip()

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

    # ----------------------------
    # 📦 품목 추가
    # ----------------------------
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

    # ----------------------------
    # 🧾 주문 추가
    # ----------------------------
    with col_order:
        st.subheader("🧾 주문자 추가")

        if not items_df.empty:

            selected_item = st.selectbox(
                "품목 선택",
                items_df["item_name"].tolist()
            )

            name = st.text_input("이름")
            phone = st.text_input("핸드폰번호")
            qty = st.number_input("수량", min_value=1, step=1)

            if st.button("주문 추가"):
                if name and phone:

                    phone = phone.replace("-", "").strip()

                    new_order = pd.DataFrame(
                        [[
                            selected_item,
                            name,
                            phone,
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

    # ----------------------------
    # 📋 실시간 주문 목록 표시
    # ----------------------------
    st.markdown("---")
    st.subheader("📋 현재 주문 목록")

    if not orders_df.empty:
        display_df = orders_df.copy()
        display_df["qty"] = display_df["qty"].astype(int)
        display_df["received"] = display_df["received"].astype(str).map({
            "True": "✅",
            "False": "❌"
        })

        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("아직 주문이 없습니다.")

# ===================================================
# 📦 수령 확인 모드
# ===================================================
# ===================================================
# 📦 수령 확인 모드
# ===================================================
if mode == "📦 수령 확인 모드":

    left_col, right_col = st.columns([1, 2])

    # ----------------------------
    # 🔍 왼쪽: 전화번호 검색
    # ----------------------------
    with left_col:
        st.subheader("🔍 전화번호 검색 (뒤 4자리)")
        search_phone_last4 = st.text_input("전화번호 뒤 4자리")

    # ----------------------------
    # 📌 오른쪽: 검색 결과 카드
    # ----------------------------
    with right_col:

        if search_phone_last4 and len(search_phone_last4) == 4:

            summary_df = orders_df[
                orders_df["phone"].str[-4:] == search_phone_last4
            ]

            if not summary_df.empty:

                summary_df["qty"] = summary_df["qty"].astype(int)

                grouped = (
                    summary_df
                    .groupby(["name", "phone", "item_name"])["qty"]
                    .sum()
                    .reset_index()
                )

                # 사람 단위로 출력
                for (name, phone) in grouped[["name", "phone"]].drop_duplicates().values:

                    person_df = grouped[
                        (grouped["name"] == name) &
                        (grouped["phone"] == phone)
                    ]

                    received_status = (
                        "✅ 수령완료"
                        if summary_df[
                            (summary_df["name"] == name) &
                            (summary_df["phone"] == phone)
                        ]["received"].astype(str).eq("True").all()
                        else "❌ 미수령"
                    )

                    summary_html = f"""
                    <div style="
                        padding:20px;
                        border-radius:12px;
                        border:2px solid #2E86C1;
                        background-color:#F4F9FF;
                        margin-bottom:15px;
                    ">
                        <h3>{name} ({phone})</h3>
                        <p><b>{received_status}</b></p>
                    """

                    for _, row in person_df.iterrows():
                        summary_html += f"<p>• {row['item_name']} {row['qty']}개</p>"

                    summary_html += "</div>"

                    st.markdown(summary_html, unsafe_allow_html=True)

            else:
                st.warning("검색 결과가 없습니다.")

    # ----------------------------
    # 아래 전체 수령 테이블
    # ----------------------------
    st.markdown("---")
    st.header("📋 전체 수령 관리")

    if not orders_df.empty:

        orders_df["qty"] = orders_df["qty"].astype(int)
        orders_df["received"] = orders_df["received"].astype(str) == "True"

        pivot_df = orders_df.pivot_table(
            index=["name", "phone"],
            columns="item_name",
            values="qty",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        all_items = items_df["item_name"].tolist()

        for item in all_items:
            if item not in pivot_df.columns:
                pivot_df[item] = 0

        pivot_df = pivot_df[["name", "phone"] + all_items]

        received_map = (
            orders_df.groupby(["name", "phone"])["received"]
            .all()
            .reset_index()
            .rename(columns={"received": "수령"})
        )

        pivot_df = pivot_df.merge(received_map, on=["name", "phone"], how="left")
        pivot_df["수령"] = pivot_df["수령"].fillna(False)

        edited_df = st.data_editor(
            pivot_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "수령": st.column_config.CheckboxColumn("수령")
            }
        )

        if st.button("💾 수령 상태 저장"):

            for _, row in edited_df.iterrows():
                mask = (
                    (orders_df["name"] == row["name"]) &
                    (orders_df["phone"] == row["phone"])
                )
                orders_df.loc[mask, "received"] = str(row["수령"])

            if save_csv_to_github(orders_df, ORDER_PATH, "update received status"):
                st.success("수령 상태 저장 완료")
                st.rerun()

    else:
        st.info("아직 주문이 없습니다.")