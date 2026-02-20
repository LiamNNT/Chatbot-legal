# frontend/app.py
"""
Chatbot-UIT  —  Streamlit Frontend

Tabs:
  1. 💬 Chat          – Main chat interface (stream / non-stream)
  2. 🔍 RAG Debug     – Inspect retrieved documents & processing stats
  3. ⚙️  System        – Health check, agent info, conversations management
  4. 📄 Ingestion     – Upload documents for indexing / KG extraction
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime

import streamlit as st

import api_client
from config import DEFAULT_RAG_TOP_K, DEFAULT_SESSION_ID

# ─── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot-UIT",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════
# Session State Initialisation
# ═══════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "session_id": DEFAULT_SESSION_ID,
        "messages": [],          # list[dict] with keys: role, content, metadata
        "last_rag_context": None,
        "last_processing_stats": None,
        "use_rag": True,
        "use_kg": None,          # None = auto, True/False = force
        "rag_top_k": DEFAULT_RAG_TOP_K,
        "stream_mode": True,
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ═══════════════════════════════════════════════════════════
# Sidebar  — settings & session management
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🎓 Chatbot-UIT")
    st.caption("Trợ lý AI cho sinh viên UIT")
    st.divider()

    # ── Session ──
    st.subheader("📋 Phiên hội thoại")
    st.session_state.session_id = st.text_input(
        "Session ID", value=st.session_state.session_id
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 Phiên mới", use_container_width=True):
            st.session_state.session_id = f"st_{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.session_state.last_rag_context = None
            st.session_state.last_processing_stats = None
            st.rerun()
    with col2:
        if st.button("🗑️ Xóa chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_rag_context = None
            st.session_state.last_processing_stats = None
            st.rerun()

    st.divider()

    # ── RAG Settings ──
    st.subheader("⚙️ Cài đặt RAG")
    st.session_state.use_rag = st.toggle("Bật RAG", value=st.session_state.use_rag)
    kg_option = st.selectbox(
        "Knowledge Graph",
        options=["Auto (SmartPlanner)", "Bật", "Tắt"],
        index=0,
    )
    st.session_state.use_kg = (
        None if kg_option.startswith("Auto") else kg_option == "Bật"
    )
    st.session_state.rag_top_k = st.slider(
        "Số tài liệu truy xuất (top_k)", 1, 20, st.session_state.rag_top_k
    )

    st.divider()

    # ── Generation Settings ──
    st.subheader("🤖 Cài đặt sinh câu trả lời")
    st.session_state.stream_mode = st.toggle(
        "Streaming", value=st.session_state.stream_mode
    )
    st.session_state.temperature = st.slider(
        "Temperature", 0.0, 2.0, st.session_state.temperature, 0.1
    )
    st.session_state.max_tokens = st.slider(
        "Max tokens", 256, 4000, st.session_state.max_tokens, 256
    )


# ═══════════════════════════════════════════════════════════
# Tab Layout
# ═══════════════════════════════════════════════════════════
tab_chat, tab_rag, tab_system, tab_ingest = st.tabs(
    ["💬 Chat", "🔍 RAG Debug", "⚙️ Hệ thống", "📄 Nạp tài liệu"]
)


# ───────────────────────────────────────────────────────────
# TAB 1 — Chat
# ───────────────────────────────────────────────────────────
with tab_chat:
    st.header("💬 Chat với Chatbot-UIT")

    # Display existing messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Nhập câu hỏi..."):
        # Append user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant response
        with st.chat_message("assistant"):
            try:
                if st.session_state.stream_mode:
                    # ── Streaming mode ──
                    placeholder = st.empty()
                    full_response = ""
                    status_text = ""

                    for event in api_client.send_chat_stream(
                        query=prompt,
                        session_id=st.session_state.session_id,
                        use_rag=st.session_state.use_rag,
                        use_knowledge_graph=st.session_state.use_kg,
                        rag_top_k=st.session_state.rag_top_k,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                    ):
                        evt_type = event.get("type", "")
                        if evt_type == "token":
                            full_response += event.get("content", "")
                            placeholder.markdown(full_response + "▌")
                        elif evt_type in ("status", "planning"):
                            status_text = event.get("content", "")
                            placeholder.markdown(
                                f"*⏳ {status_text}*\n\n{full_response}▌"
                            )
                        elif evt_type == "rag_context":
                            st.session_state.last_rag_context = event.get("data")
                        elif evt_type == "stats":
                            st.session_state.last_processing_stats = event.get("data")
                        elif evt_type == "complete":
                            full_response = event.get("content", full_response)
                        elif evt_type == "error":
                            full_response = f"❌ Lỗi: {event.get('content', 'Unknown error')}"

                    placeholder.markdown(full_response)
                    assistant_content = full_response

                else:
                    # ── Non-streaming mode ──
                    with st.spinner("Đang xử lý..."):
                        data = api_client.send_chat_message(
                            query=prompt,
                            session_id=st.session_state.session_id,
                            use_rag=st.session_state.use_rag,
                            use_knowledge_graph=st.session_state.use_kg,
                            rag_top_k=st.session_state.rag_top_k,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                        )
                    assistant_content = data.get("response", "Không có phản hồi.")
                    st.markdown(assistant_content)

                    # Save debug info
                    st.session_state.last_rag_context = data.get("rag_context")
                    st.session_state.last_processing_stats = data.get(
                        "processing_stats"
                    )

                # Save assistant message
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_content}
                )

            except Exception as exc:
                error_msg = f"❌ Lỗi kết nối: {exc}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )


# ───────────────────────────────────────────────────────────
# TAB 2 — RAG Debug
# ───────────────────────────────────────────────────────────
with tab_rag:
    st.header("🔍 RAG Debug Panel")

    if st.session_state.last_processing_stats:
        stats = st.session_state.last_processing_stats
        st.subheader("⏱️ Processing Stats")

        cols = st.columns(4)
        cols[0].metric("Tổng thời gian", f"{stats.get('total_time', 0):.2f}s")
        cols[1].metric("RAG time", f"{stats.get('rag_time', 0) or 0:.2f}s")
        cols[2].metric("Agent time", f"{stats.get('agent_time', 0) or 0:.2f}s")
        cols[3].metric("Docs retrieved", stats.get("documents_retrieved", "N/A"))

        extra_cols = st.columns(3)
        extra_cols[0].metric("LLM calls", stats.get("llm_calls", "N/A"))
        extra_cols[1].metric("Pipeline", stats.get("pipeline", "N/A"))
        extra_cols[2].metric(
            "Complexity", stats.get("plan_complexity", "N/A")
        )

        with st.expander("📊 Raw stats JSON"):
            st.json(stats)
    else:
        st.info("Chưa có dữ liệu xử lý. Hãy gửi một câu hỏi ở tab Chat trước.")

    st.divider()

    if st.session_state.last_rag_context:
        ctx = st.session_state.last_rag_context
        st.subheader("📑 Tài liệu truy xuất")

        docs = ctx.get("documents", [])
        if docs:
            for i, doc in enumerate(docs, 1):
                with st.expander(
                    f"📄 [{i}] {doc.get('title', 'Untitled')}  —  score: {doc.get('score', 0):.4f}"
                ):
                    st.markdown(doc.get("content", doc.get("text", "")))
                    if doc.get("metadata"):
                        st.caption(f"Metadata: {json.dumps(doc['metadata'], ensure_ascii=False)}")
        else:
            st.warning("Không có tài liệu nào được truy xuất.")

        meta_cols = st.columns(3)
        meta_cols[0].metric("Search mode", ctx.get("search_mode", "N/A"))
        meta_cols[1].metric("Knowledge Graph", "✅" if ctx.get("use_knowledge_graph") else "❌")
        meta_cols[2].metric("Vector Search", "✅" if ctx.get("use_vector_search", True) else "❌")

        with st.expander("📊 Raw RAG context JSON"):
            st.json(ctx)
    else:
        st.info("Chưa có ngữ cảnh RAG. Hãy gửi câu hỏi với RAG bật.")


# ───────────────────────────────────────────────────────────
# TAB 3 — System
# ───────────────────────────────────────────────────────────
with tab_system:
    st.header("⚙️ Thông tin hệ thống")

    col_health, col_agents = st.columns(2)

    # ── Health Check ──
    with col_health:
        st.subheader("🏥 Health Check")
        if st.button("Kiểm tra sức khỏe", key="health_btn"):
            try:
                with st.spinner("Đang kiểm tra..."):
                    health = api_client.check_health()
                status = health.get("status", "unknown")
                if status == "healthy":
                    st.success(f"Trạng thái: **{status}** ✅")
                else:
                    st.warning(f"Trạng thái: **{status}** ⚠️")
                st.json(health)
            except Exception as exc:
                st.error(f"Không thể kết nối: {exc}")

    # ── Agent Info ──
    with col_agents:
        st.subheader("🤖 Agent Info")
        if st.button("Xem thông tin agents", key="agents_btn"):
            try:
                with st.spinner("Đang tải..."):
                    info = api_client.get_agents_info()
                st.json(info)
            except Exception as exc:
                st.error(f"Lỗi: {exc}")

    st.divider()

    # ── Test Agents ──
    st.subheader("🧪 Test Agents")
    if st.button("Chạy test nhanh", key="test_btn"):
        try:
            with st.spinner("Đang test hệ thống multi-agent..."):
                result = api_client.test_agents()
            if result.get("test_successful"):
                st.success("Test thành công! ✅")
            else:
                st.error("Test thất bại ❌")
            st.json(result)
        except Exception as exc:
            st.error(f"Lỗi: {exc}")

    st.divider()

    # ── Conversations ──
    st.subheader("📋 Quản lý phiên hội thoại")
    if st.button("Tải danh sách phiên", key="conv_btn"):
        try:
            with st.spinner("Đang tải..."):
                data = api_client.get_conversations()
            convs = data.get("conversations", [])
            if convs:
                for c in convs:
                    cols = st.columns([3, 1, 1])
                    cols[0].write(f"🆔 `{c['session_id']}`")
                    cols[1].write(f"💬 {c.get('message_count', '?')} tin nhắn")
                    if cols[2].button("🗑️", key=f"del_{c['session_id']}"):
                        try:
                            api_client.delete_conversation(c["session_id"])
                            st.success(f"Đã xóa phiên {c['session_id']}")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Lỗi xóa: {exc}")
            else:
                st.info("Không có phiên nào.")
        except Exception as exc:
            st.error(f"Lỗi: {exc}")


# ───────────────────────────────────────────────────────────
# TAB 4 — Document Ingestion & KG Extraction
# ───────────────────────────────────────────────────────────
with tab_ingest:
    st.header("📄 Nạp tài liệu & Trích xuất KG")

    ingest_tab, extract_tab = st.tabs(["📥 Nạp tài liệu (Ingest)", "🔬 Trích xuất KG"])

    # ── Ingest ──
    with ingest_tab:
        st.subheader("📥 Upload tài liệu để nạp vào hệ thống")
        uploaded_file = st.file_uploader(
            "Chọn file DOCX / PDF",
            type=["docx", "doc", "pdf"],
            key="ingest_upload",
        )
        if uploaded_file and st.button("🚀 Bắt đầu nạp", key="ingest_start"):
            try:
                with st.spinner("Đang upload và nạp..."):
                    result = api_client.upload_for_ingest(
                        uploaded_file.getvalue(), uploaded_file.name
                    )
                st.success(f"Job ID: `{result.get('job_id', 'N/A')}`")
                st.json(result)
            except Exception as exc:
                st.error(f"Lỗi: {exc}")

        st.divider()
        st.subheader("📊 Kiểm tra trạng thái job")
        job_id = st.text_input("Job ID", key="ingest_job_id")
        if job_id and st.button("Kiểm tra", key="ingest_check"):
            try:
                status = api_client.get_ingest_status(job_id)
                st.json(status)
            except Exception as exc:
                st.error(f"Lỗi: {exc}")

    # ── KG Extraction ──
    with extract_tab:
        st.subheader("🔬 Trích xuất Knowledge Graph từ PDF")
        kg_file = st.file_uploader(
            "Chọn file PDF",
            type=["pdf"],
            key="kg_upload",
        )
        category = st.selectbox(
            "Loại tài liệu",
            ["Quy chế Đào tạo", "Quy định chung", "Khác"],
        )
        push_neo4j = st.checkbox("Đẩy lên Neo4j sau khi trích xuất")

        if kg_file and st.button("🚀 Bắt đầu trích xuất", key="kg_start"):
            try:
                with st.spinner("Đang upload và trích xuất..."):
                    result = api_client.upload_for_extraction(
                        kg_file.getvalue(),
                        kg_file.name,
                        category=category,
                        push_to_neo4j=push_neo4j,
                    )
                st.success(f"Job ID: `{result.get('job_id', 'N/A')}`")
                st.json(result)
            except Exception as exc:
                st.error(f"Lỗi: {exc}")

        st.divider()
        st.subheader("📊 Kiểm tra kết quả trích xuất")
        kg_job_id = st.text_input("Job ID (KG)", key="kg_job_id")
        col_status, col_result = st.columns(2)
        with col_status:
            if kg_job_id and st.button("Xem trạng thái", key="kg_status"):
                try:
                    status = api_client.get_extraction_status(kg_job_id)
                    st.json(status)
                except Exception as exc:
                    st.error(f"Lỗi: {exc}")
        with col_result:
            if kg_job_id and st.button("Xem kết quả", key="kg_result"):
                try:
                    result = api_client.get_extraction_result(kg_job_id)
                    st.json(result)
                except Exception as exc:
                    st.error(f"Lỗi: {exc}")

        st.divider()
        st.subheader("📈 Neo4j Stats")
        if st.button("Xem thống kê Neo4j", key="neo4j_stats"):
            try:
                with st.spinner("Đang tải..."):
                    stats = api_client.get_neo4j_stats()
                st.json(stats)
            except Exception as exc:
                st.error(f"Lỗi: {exc}")
