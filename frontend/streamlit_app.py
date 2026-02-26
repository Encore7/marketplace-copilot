from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_BASE_URL_DEFAULT = os.getenv("COPILOT_API_BASE_URL", "http://localhost:8000/api/v1")


def _get_api_base_url() -> str:
    return st.session_state.get("api_base_url", API_BASE_URL_DEFAULT).rstrip("/")


def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{_get_api_base_url()}{path}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{_get_api_base_url()}{path}"
    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()


def _load_sessions(seller_id: Optional[str]) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"limit": 100}
    if seller_id:
        params["seller_id"] = seller_id
    return _api_get("/chat/sessions", params=params)


def _create_session(
    seller_id: Optional[str],
    seller_name: Optional[str],
    title: Optional[str],
) -> Dict[str, Any]:
    return _api_post(
        "/chat/sessions",
        {
            "seller_id": seller_id,
            "seller_name": seller_name,
            "title": title,
        },
    )


def _load_session_detail(session_id: str) -> Dict[str, Any]:
    return _api_get(f"/chat/sessions/{session_id}", params={"limit": 300})


def _send_analyze(
    query: str,
    marketplaces: List[str],
    session_id: str,
    seller_id: Optional[str],
    seller_name: Optional[str],
) -> Dict[str, Any]:
    return _api_post(
        "/analyze",
        {
            "query": query,
            "marketplaces": marketplaces,
            "session_id": session_id,
            "seller_id": seller_id,
            "seller_name": seller_name,
        },
    )


def _render_trust_block(metadata: Dict[str, Any]) -> None:
    used_tools = metadata.get("used_tools") or []
    used_rag_evidence = metadata.get("used_rag_evidence") or []
    rag_debug = metadata.get("rag_debug") or {}
    execution_trace = metadata.get("execution_trace") or []
    routing_debug = metadata.get("routing_debug") or {}
    citations = metadata.get("citations") or []
    request_id = metadata.get("request_id")

    st.caption("Trust and Evidence")
    if request_id:
        st.code(f"request_id: {request_id}")
    cols = st.columns(4)
    cols[0].metric("Tools used", len(used_tools))
    cols[1].metric("RAG evidence", len(used_rag_evidence))
    cols[2].metric("Trace steps", len(execution_trace))
    cols[3].metric("Citations", len(citations))

    if rag_debug:
        st.write("`rag_debug`")
        st.json(rag_debug)
    if routing_debug:
        st.write("`routing_debug`")
        st.json(routing_debug)
    if used_tools:
        st.write("`used_tools`")
        st.json(used_tools)
    if used_rag_evidence:
        st.write("`used_rag_evidence`")
        st.json(used_rag_evidence)
    if citations:
        st.write("`citations`")
        st.json(citations)
    if execution_trace:
        st.write("`execution_trace`")
        st.json(execution_trace)


def _render_sidebar() -> Optional[str]:
    st.sidebar.title("Seller Copilot")
    st.sidebar.caption("Multi-turn, session-based chat")

    st.session_state["api_base_url"] = st.sidebar.text_input(
        "Backend API base URL",
        value=st.session_state.get("api_base_url", API_BASE_URL_DEFAULT),
    )
    seller_id_default = st.session_state.get("seller_id") or "seller_demo"
    seller_id = st.sidebar.text_input(
        "Seller ID",
        value=str(seller_id_default),
    ).strip() or None
    seller_name_default = st.session_state.get("seller_name") or ""
    seller_name = st.sidebar.text_input(
        "Seller Name",
        value=str(seller_name_default),
    ).strip() or None
    st.session_state["seller_id"] = seller_id
    st.session_state["seller_name"] = seller_name

    marketplaces = st.sidebar.multiselect(
        "Marketplaces",
        ["amazon", "flipkart", "myntra", "meesho"],
        default=st.session_state.get("marketplaces", ["amazon"]),
    )
    st.session_state["marketplaces"] = marketplaces or ["amazon"]

    try:
        sessions = _load_sessions(seller_id=seller_id)
    except Exception as exc:
        st.sidebar.error(f"Failed to load sessions: {exc}")
        return None

    if st.sidebar.button("New Session", use_container_width=True):
        try:
            created = _create_session(
                seller_id=seller_id,
                seller_name=seller_name,
                title="Seller chat",
            )
            st.session_state["active_session_id"] = created["session_id"]
            st.rerun()
        except Exception as exc:
            st.sidebar.error(f"Failed to create session: {exc}")

    if not sessions:
        st.sidebar.info("No sessions yet. Create one.")
        return None

    labels = [
        f"{s.get('title', 'Seller chat')} · {s['session_id'][:8]} · {s.get('updated_at', '')}"
        for s in sessions
    ]
    selected_idx = 0
    active_session_id = st.session_state.get("active_session_id")
    if active_session_id:
        for idx, s in enumerate(sessions):
            if s["session_id"] == active_session_id:
                selected_idx = idx
                break

    selected_label = st.sidebar.selectbox(
        "Sessions",
        options=labels,
        index=selected_idx,
    )
    selected_index = labels.index(selected_label)
    selected_session_id = sessions[selected_index]["session_id"]
    st.session_state["active_session_id"] = selected_session_id
    return selected_session_id


def _render_chat(session_id: str) -> None:
    try:
        session_detail = _load_session_detail(session_id)
    except Exception as exc:
        st.error(f"Failed to load chat session: {exc}")
        return

    session_meta = session_detail["session"]
    memory_facts = session_detail.get("memory_facts", {})
    messages = session_detail.get("messages", [])

    st.title("Marketplace Seller Copilot")
    st.caption(
        f"Session `{session_meta['session_id']}` · Updated {session_meta.get('updated_at', 'n/a')}"
    )

    if memory_facts:
        with st.expander("Remembered Seller Facts", expanded=False):
            for key, value in memory_facts.items():
                st.write(f"- `{key}`: {value}")

    for message in messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(message["content"])
            if role == "assistant":
                metadata = message.get("metadata") or {}
                if metadata:
                    _render_trust_block(metadata)

    user_prompt = st.chat_input("Ask about pricing, compliance, inventory, SEO...")
    if not user_prompt:
        return

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = _send_analyze(
                    query=user_prompt,
                    marketplaces=st.session_state.get("marketplaces", ["amazon"]),
                    session_id=session_id,
                    seller_id=st.session_state.get("seller_id"),
                    seller_name=st.session_state.get("seller_name"),
                )
            except Exception as exc:
                st.error(f"Analyze failed: {exc}")
                return

        answer = response["final_answer"]["answer_markdown"]
        st.markdown(answer)
        _render_trust_block(
            {
                "used_tools": response.get("used_tools", []),
                "used_rag_evidence": response.get("used_rag_evidence", []),
                "rag_debug": response.get("rag_debug", {}),
                "routing_debug": response.get("routing_debug", {}),
                "execution_trace": response.get("execution_trace", []),
                "citations": (
                    response.get("final_answer", {}).get("citations", [])
                    if isinstance(response.get("final_answer"), dict)
                    else []
                ),
                "session_id": response.get("session_id"),
                "request_id": response.get("request_id"),
            }
        )
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Marketplace Seller Copilot",
        layout="wide",
    )
    selected_session_id = _render_sidebar()
    if not selected_session_id:
        st.title("Marketplace Seller Copilot")
        st.info("Create a session from the sidebar to start chatting.")
        return
    _render_chat(selected_session_id)


if __name__ == "__main__":
    main()
