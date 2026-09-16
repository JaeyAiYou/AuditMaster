import streamlit as st
import pandas as pd
import numpy as np
import io
import pypdf
import google.generativeai as genai
from docx import Document

st.set_page_config(page_title="3개년 감사보고서 재무 & Gemini AI 심사", layout="wide")

# 1. 개별 API Key 입력 (사이드바)
with st.sidebar:
    st.title("⚙️ AI 설정")
    user_api_key = st.text_input("Gemini API Key 입력", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")

st.title("📈 3개년 감사보고서 재무 분석 및 Gemini AI 심사 시스템")

# 2. 최대 3개 파일 업로드 기능
uploaded_files = st.file_uploader(
    "3개년 감사보고서/재무제표 파일 업로드 (PDF, XLSX, CSV / 최대 3개)", 
    type=["pdf", "xlsx", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) > 3:
        st.warning("⚠️ 최대 3개의 파일까지 지원됩니다. 상위 3개 파일만 분석에 사용됩니다.")
        uploaded_files = uploaded_files[:3]

    parsed_tables = []
    combined_text = ""

    st.subheader("📋 업로드된 파일 및 데이터 표 확인")
    
    # 파일별 파싱 및 표 생성
    for idx, file in enumerate(uploaded_files):
        st.markdown(f"**📁 파일 {idx+1}: {file.name}**")
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            st.dataframe(df, use_container_width=True)
            parsed_tables.append((file.name, df))
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
            st.dataframe(df, use_container_width=True)
            parsed_tables.append((file.name, df))
        elif file.name.endswith(".pdf"):
            reader = pypdf.PdfReader(file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            combined_text += f"\n--- [{file.name}] ---\n" + text
            st.info(f"📄 PDF 텍스트 추출 완료 ({len(reader.pages)} 페이지)")

    tab1, tab2 = st.tabs(["🤖 Gemini 3개년 종합 진단", "📑 Word 보고서 다운로드"])

    with tab1:
        if st.button("🚀 3개년 통합 AI 리스크 심사 실행"):
            if not user_api_key:
                st.error("🔑 왼쪽 사이드바에 Gemini API Key를 입력해주세요.")
            else:
                try:
                    genai.configure(api_key=user_api_key)
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    # 데이터 표 내용 요약 텍스트화
                    table_summary = ""
                    for fname, df in parsed_tables:
                        table_summary += f"\n[{fname} 재무 데이터]\n" + df.to_string() + "\n"

                    prompt = f"""
                    당신은 금융기관 수석 여신심사역입니다. 
                    제공된 3개년 감사보고서/재무 자료를 바탕으로 종합 여신심사평을 작성해주세요.

                    [분석 항목]
                    1. 3개년 주요 재무지표 추세 분석 (매출, 영업이익, 부채비율 등)
                    2. 주석 상 우발채무, 지급보증, 소송, 담보제공 등 숨겨진 리스크 진단
                    3. 최종 여신심사 의견 및 종합 대응 방안

                    [재무 데이터 표]
                    {table_summary}

                    [감사보고서 텍스트]
                    {combined_text[:12000]}
                    """
                    
                    with st.spinner("Gemini AI가 3개년 데이터를 정밀 분석 중입니다..."):
                        response = model.generate_content(prompt)
                        st.session_state["ai_result"] = response.text
                        st.markdown(response.text)
                except Exception as e:
                    st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

    # 3. 첨부 파일의 표가 포함된 Word 보고서 생성
    with tab2:
        if "ai_result" in st.session_state:
            doc = Document()
            doc.add_heading('3개년 감사보고서 재무 & Gemini AI 심사 보고서', level=0)
            
            # 업로드된 데이터 표를 Word 문서에 작성
            if parsed_tables:
                doc.add_heading('1. 주요 재무 데이터 표', level=1)
                for fname, df in parsed_tables:
                    doc.add_paragraph(f"■ 데이터 출처: {fname}")
                    t = doc.add_table(rows=df.shape[0]+1, cols=df.shape[1])
                    t.style = 'Table Grid'
                    for c_idx, col in enumerate(df.columns):
                        t.rows[0].cells[c_idx].text = str(col)
                    for r_idx, row in df.iterrows():
                        for c_idx, val in enumerate(row):
                            t.rows[r_idx+1].cells[c_idx].text = str(val)
                    doc.add_paragraph("")

            doc.add_heading('2. Gemini AI 종합 심사평 및 리스크 진단', level=1)
            doc.add_paragraph(st.session_state["ai_result"])

            doc_io = io.BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)

            st.download_button("📥 Word 심사 보고서 다운로드 (.docx)", doc_io, "Audit_3Year_Analysis_Report.docx")
        else:
            st.info("💡 [Gemini 3개년 종합 진단] 탭에서 AI 심사를 먼저 실행해주세요.")
