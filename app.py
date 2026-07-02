import streamlit as st
import requests

st.set_page_config(page_title="GitHub Repo Explorer", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
.subtitle { color: #888; margin-top: 0; margin-bottom: 1.5rem; }
.source-tag {
  display: inline-block; background:#eef2ff; color:#3730a3; padding:2px 10px;
  border-radius:12px; font-size:0.78rem; margin:2px; font-family: monospace;
}
.stButton>button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🔍 GitHub Repository Explorer</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Ask natural-language questions about any public GitHub repository.</p>', unsafe_allow_html=True)

if "repo_id" not in st.session_state:
    st.session_state.repo_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

with st.sidebar:
    st.header("⚙️ Settings")
    backend_url = st.text_input("Backend URL", "http://localhost:8000").rstrip("/")

    st.header("📦 Load a Repository")
    github_url = st.text_input("GitHub URL", placeholder="https://github.com/owner/repo")
    if st.button("Process Repository", use_container_width=True, type="primary"):
        if not github_url.strip():
            st.warning("Please enter a GitHub URL.")
        else:
            with st.spinner("Cloning repo, extracting content, building index... this can take a minute"):
                try:
                    resp = requests.post(f"{backend_url}/ingest", json={"github_url": github_url}, timeout=600)
                    resp.raise_for_status()
                    data = resp.json()
                    st.session_state.repo_id = data["repo_id"]
                    st.session_state.messages = []
                    st.success(f"Indexed {data['num_chunks']} chunks from {data['owner']}/{data['repo']}")
                except requests.exceptions.RequestException as e:
                    detail = ""
                    if e.response is not None:
                        try:
                            detail = e.response.json().get("detail", "")
                        except Exception:
                            detail = e.response.text
                    st.error(f"Failed to process repository: {detail or e}")

    if st.session_state.repo_id:
        st.info(f"Active repo: **{st.session_state.repo_id}**")
        st.markdown("**Try asking:**")
        for q in [
            "What does this project do?",
            "How do I install it?",
            "Where is the authentication code?",
            "Explain the database connection.",
            "Which file handles user login?",
        ]:
            if st.button(q, use_container_width=True, key=f"suggest_{q}"):
                st.session_state.pending_question = q

# ---- Chat history ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            tags = " ".join(f'<span class="source-tag">{s}</span>' for s in msg["sources"])
            st.markdown(tags, unsafe_allow_html=True)

question = st.chat_input("Ask a question about the repository...")
if st.session_state.pending_question:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

if question:
    if not st.session_state.repo_id:
        st.warning("Please process a repository first (see sidebar).")
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    resp = requests.post(
                        f"{backend_url}/ask",
                        json={"repo_id": st.session_state.repo_id, "question": question},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    st.markdown(data["answer"])
                    if data.get("sources"):
                        tags = " ".join(f'<span class="source-tag">{s}</span>' for s in data["sources"])
                        st.markdown(tags, unsafe_allow_html=True)
                    st.session_state.messages.append({
                        "role": "assistant", "content": data["answer"], "sources": data.get("sources", []),
                    })
                except requests.exceptions.RequestException as e:
                    detail = ""
                    if e.response is not None:
                        try:
                            detail = e.response.json().get("detail", "")
                        except Exception:
                            detail = e.response.text
                    st.error(f"Error: {detail or e}")
