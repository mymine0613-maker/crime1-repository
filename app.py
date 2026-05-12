import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

DB_PATH = "crime.db"

st.set_page_config(page_title="범죄 공공데이터 대시보드", layout="wide")
st.title("범죄 공공데이터 시각화 대시보드")

if not os.path.exists(DB_PATH):
    st.error("crime.db 파일이 없습니다. app.py와 같은 폴더에 crime.db를 업로드해주세요.")
    st.stop()

conn = sqlite3.connect(DB_PATH)

def query(sql):
    return pd.read_sql_query(sql, conn)

time_cols = [
    "00:00-02:59", "03:00-05:59", "06:00-08:59", "09:00-11:59",
    "12:00-14:59", "15:00-17:59", "18:00-20:59", "21:00-23:59"
]

# -------------------------------------------------
# 1. 죄종(대)별 범죄발생시간 MAX
# -------------------------------------------------
st.header("1. 죄종(대)와 범죄발생시간대의 상관관계")

sql1 = """
SELECT
    "죄종(대)",
    SUM("00:00-02:59") AS "00:00-02:59",
    SUM("03:00-05:59") AS "03:00-05:59",
    SUM("06:00-08:59") AS "06:00-08:59",
    SUM("09:00-11:59") AS "09:00-11:59",
    SUM("12:00-14:59") AS "12:00-14:59",
    SUM("15:00-17:59") AS "15:00-17:59",
    SUM("18:00-20:59") AS "18:00-20:59",
    SUM("21:00-23:59") AS "21:00-23:59"
FROM "범죄발생시간대 및 요일"
GROUP BY "죄종(대)";
"""

df1 = query(sql1)

df1_long = df1.melt(
    id_vars="죄종(대)",
    value_vars=time_cols,
    var_name="범죄발생시간대",
    value_name="발생건수"
)

max_time = df1_long.loc[df1_long.groupby("죄종(대)")["발생건수"].idxmax()]

fig1 = px.line(
    df1_long,
    x="범죄발생시간대",
    y="발생건수",
    color="죄종(대)",
    markers=True,
    title="죄종(대)별 범죄발생시간대 발생건수"
)

st.plotly_chart(fig1, use_container_width=True)

st.subheader("죄종(대)별 범죄발생시간 MAX")
st.dataframe(max_time, use_container_width=True)

with st.expander("사용한 SQL"):
    st.code(sql1, language="sql")

top_row = max_time.sort_values("발생건수", ascending=False).iloc[0]
st.write(f"""
**인사이트**  
전체적으로 `{top_row["죄종(대)"]}` 범죄는 `{top_row["범죄발생시간대"]}` 시간대에 가장 많이 발생했다.  
죄종별로 집중되는 시간대가 다르기 때문에, 범죄 예방 정책은 단순 전체 건수가 아니라 시간대별 위험도를 기준으로 세우는 것이 효과적이다.
""")


# -------------------------------------------------
# 2. 검거성별과 범죄발생시간대의 상관관계
# -------------------------------------------------
st.header("2. 검거성별과 범죄발생시간대의 상관관계")

sql2 = """
SELECT
    t."죄종(대)",
    t."죄종(중)",
    t."00:00-02:59",
    t."03:00-05:59",
    t."06:00-08:59",
    t."09:00-11:59",
    t."12:00-14:59",
    t."15:00-17:59",
    t."18:00-20:59",
    t."21:00-23:59",
    c."검거인원(남)",
    c."검거인원(여)",
    c."검거인원(불상)"
FROM "범죄발생시간대 및 요일" t
JOIN "범죄발생 및 검거현황" c
ON t."죄종(대)" = c."죄종(대)"
AND t."죄종(중)" = c."죄종(중)";
"""

df2 = query(sql2)

df2["총검거인원"] = (
    df2["검거인원(남)"] +
    df2["검거인원(여)"] +
    df2["검거인원(불상)"]
)

time_long = df2.melt(
    id_vars=["죄종(대)", "죄종(중)", "검거인원(남)", "검거인원(여)", "검거인원(불상)", "총검거인원"],
    value_vars=time_cols,
    var_name="범죄발생시간대",
    value_name="시간대발생건수"
)

gender_long = time_long.melt(
    id_vars=["죄종(대)", "죄종(중)", "범죄발생시간대", "시간대발생건수", "총검거인원"],
    value_vars=["검거인원(남)", "검거인원(여)", "검거인원(불상)"],
    var_name="검거성별",
    value_name="검거인원"
)

gender_long["성별_시간대_추정값"] = gender_long["시간대발생건수"] * (
    gender_long["검거인원"] / gender_long["총검거인원"].replace(0, pd.NA)
)

chart2_df = gender_long.groupby(
    ["범죄발생시간대", "검거성별"],
    as_index=False
)["성별_시간대_추정값"].sum()

fig2 = px.bar(
    chart2_df,
    x="범죄발생시간대",
    y="성별_시간대_추정값",
    color="검거성별",
    barmode="group",
    title="범죄발생시간대별 검거성별 추정 분포"
)

st.plotly_chart(fig2, use_container_width=True)

with st.expander("사용한 SQL"):
    st.code(sql2, language="sql")

max_gender_row = chart2_df.sort_values("성별_시간대_추정값", ascending=False).iloc[0]

st.write(f"""
**인사이트**  
그래프상 `{max_gender_row["검거성별"]}`은 `{max_gender_row["범죄발생시간대"]}` 시간대에서 가장 높은 검거 분포를 보인다.  
즉, 해당 시간대에 발생량이 많고 검거 인원 비중도 높게 나타나므로, 이 시간대가 검거 활동과 범죄 발생이 동시에 집중되는 구간으로 해석할 수 있다.  
단, 원자료에는 성별별 시간대 검거건수가 직접 존재하지 않기 때문에, 이 값은 발생시간대와 검거성별 비율을 결합한 추정값이다.
""")


# -------------------------------------------------
# 3. 검거율 지역 TOP 5
# -------------------------------------------------
st.header("3. 검거율 지역 TOP 5")

region_cols = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기 고양", "경기 과천", "경기 광명", "경기 광주", "경기 구리",
    "경기 군포", "경기 김포", "경기 남양주", "경기 동두천", "경기 부천",
    "경기 성남", "경기 수원", "경기 시흥", "경기 안산", "경기 안성",
    "경기 안양", "경기 양주", "경기 여주", "경기 오산", "경기 용인",
    "경기 의왕", "경기 의정부", "경기 이천", "경기 파주", "경기 평택",
    "경기 포천", "경기 하남", "경기 화성", "강원 강릉", "강원 동해",
    "강원 삼척", "강원 속초", "강원 원주", "강원 춘천", "강원 태백",
    "충북 제천", "충북 청주", "충북 충주", "충남 계룡", "충남 공주",
    "충남 논산", "충남 당진", "충남 보령", "충남 서산", "충남 아산",
    "충남 천안", "전북 군산", "전북 김제", "전북 남원", "전북 익산",
    "전북 전주", "전북 정읍", "전남 광양", "전남 나주", "전남 목포",
    "전남 순천", "전남 여수", "경북 경산", "경북 경주", "경북 구미",
    "경북 김천", "경북 문경", "경북 상주", "경북 안동", "경북 영주",
    "경북 영천", "경북 포항", "경남 거제", "경남 김해", "경남 밀양",
    "경남 사천", "경남 양산", "경남 진주", "경남 창원", "경남 통영",
    "제주 서귀포", "제주 제주", "기타도시", "도시이외"
]

union_sql = "\nUNION ALL\n".join([
    f"""
    SELECT
        '{col}' AS 지역,
        SUM(r."{col}") AS 발생건수,
        SUM(c."검거") AS 검거건수
    FROM "범죄 발생 지역" r
    JOIN "범죄발생 및 검거현황" c
    ON r."죄종(대)" = c."죄종(대)"
    AND r."죄종(중)" = c."죄종(중)"
    """
    for col in region_cols
])

sql3 = f"""
SELECT
    지역,
    발생건수,
    검거건수,
    ROUND(검거건수 / 10.0, 1) AS "검거건수_단위10",
    ROUND(CAST(검거건수 AS REAL) / 발생건수 * 100, 2) AS 검거율
FROM (
    {union_sql}
)
WHERE 발생건수 > 0
ORDER BY 검거율 DESC
LIMIT 5;
"""

df3 = query(sql3)

fig3 = px.bar(
    df3,
    x="검거건수_단위10",
    y="지역",
    orientation="h",
    text="검거율",
    title="검거율 높은 지역 TOP 5"
)

fig3.update_layout(
    xaxis_title="검거건수 / 10",
    yaxis_title="지역",
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(fig3, use_container_width=True)

st.dataframe(df3, use_container_width=True)

with st.expander("사용한 SQL"):
    st.code(sql3, language="sql")

top_region = df3.iloc[0]

st.write(f"""
**인사이트**  
검거율이 가장 높은 지역은 `{top_region["지역"]}`이며, 검거율은 약 `{top_region["검거율"]}%`로 나타났다.  
그래프에서는 검거건수를 10으로 나누어 표시했기 때문에 지역 간 차이를 더 보기 쉽게 비교할 수 있다.  
검거건수만 보면 인구나 사건 수가 많은 지역이 유리하므로, 검거율 기준으로 보는 것이 더 의미 있다.
""")


# -------------------------------------------------
# 배포 안내
# -------------------------------------------------
st.header("GitHub 업로드 및 Streamlit 배포 방법")

st.write("""
1. GitHub 저장소에 `app.py`, `requirements.txt`, `crime.db`를 같은 위치에 업로드합니다.  
2. Streamlit Community Cloud에서 GitHub 저장소를 연결합니다.  
3. 실행 파일 경로를 `app.py`로 설정한 뒤 Deploy를 누릅니다.  
4. 오류가 나면 `Manage app → Reboot app` 또는 `Redeploy`를 눌러 다시 실행합니다.
""")

conn.close()
