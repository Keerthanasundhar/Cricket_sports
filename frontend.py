"""Streamlit frontend for the Cricket Match Analyst."""
import asyncio
import os
import sys

import streamlit as st
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

from cricket_analyst import guardrails
from cricket_analyst.graph import build_graph
from cricket_analyst.observability import configure_tracing, setup_logging


st.set_page_config(
    page_title="Cricket Insight Studio",
    page_icon="🏏",
    layout="centered",
)

load_dotenv()
configure_tracing()
setup_logging()

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #111827 28%, #1e293b 100%);
            color: #e2e8f0;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.9);
            border-right: 1px solid rgba(148, 163, 184, 0.2);
        }
        .stButton > button {
            background: linear-gradient(135deg, #22c55e 0%, #14b8a6 100%);
            color: #031310;
            border: none;
            border-radius: 0.75rem;
            font-weight: 700;
            padding: 0.75rem 1rem;
            box-shadow: 0 8px 20px rgba(20, 184, 166, 0.25);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #4ade80 0%, #2dd4bf 100%);
        }
        .stTextArea textarea,
        .stTextInput input {
            background: rgba(15, 23, 42, 0.75);
            color: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.45);
            border-radius: 0.8rem;
        }
        h1 {
            color: #f8fafc;
            letter-spacing: 0.02em;
        }
        .stSuccess, .stWarning, .stInfo, .stError {
            border-radius: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

SAMPLE_QUESTIONS = [
    "How does umpire's call work in DRS?",
    "Build me a fantasy XI for CSK vs MI at Chepauk within 100 credits",
    "Compare CSK and MI at Chepauk",
]


async def _create_graph():
    client = MultiServerMCPClient(
        {
            "cricket": {
                "command": sys.executable,
                "args": ["-m", "cricket_analyst.mcp_server"],
                "transport": "stdio",
            }
        }
    )
    return build_graph(await client.get_tools())


@st.cache_resource(show_spinner=False)
def get_graph():
    """Create the backend graph once per Streamlit process."""
    return asyncio.run(_create_graph())


def ask_question(graph, question):
    return asyncio.run(graph.ainvoke({"query": question}))["answer"]


def has_groq_key():
    key = os.getenv("GROQ_API_KEY", "").strip()
    return bool(key) and key != "your_groq_api_key_here"


st.title("🏏 Cricket Insight Studio")
st.caption("AI-powered cricket analysis, match context, and fantasy build guidance.")

with st.sidebar:
    st.header("Configuration")
    if has_groq_key():
        st.success("Groq API key configured")
    else:
        st.warning("Groq API key missing")
        st.caption("Copy .env.example to .env and add your own key, then restart Streamlit.")
    st.header("Example questions")
    for sample in SAMPLE_QUESTIONS:
        if st.button(sample, use_container_width=True):
            st.session_state["question"] = sample

question = st.text_area(
    "Your question",
    key="question",
    height=120,
    placeholder="For example: Build me a fantasy XI for CSK vs MI at Chepauk within 100 credits",
)

if st.button("Ask analyst", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Enter a question before submitting.")
    elif guardrails.is_obviously_out_of_scope(question):
        st.info(guardrails.OUT_OF_SCOPE)
    elif not has_groq_key():
        st.error(
            "Add your Groq API key to a local .env file before asking a question. "
            "The key is required to route and answer requests."
        )
    else:
        with st.spinner("Processing your question..."):
            try:
                answer = ask_question(get_graph(), question.strip())
            except TypeError as exc:
                if "authentication" in str(exc).lower() or "api key" in str(exc).lower():
                    st.error(
                        "Groq authentication failed. Check GROQ_API_KEY in "
                        "your local .env file and restart Streamlit."
                    )
                else:
                    raise
            except Exception as exc:
                error_text = str(exc).lower()
                if "credit balance is too low" in error_text or "plans & billing" in error_text:
                    st.error(
                        "Your provider account has no available credits. Add credits "
                        "in the provider billing settings, "
                        "then restart Streamlit and try again."
                    )
                elif "model_not_found" in error_text or "does not exist" in error_text:
                    st.error(
                        "The configured Groq model is unavailable. Update CRICKET_MODEL "
                        "in .env to an active Groq model and restart Streamlit."
                    )
                else:
                    st.error(
                        "The analyst could not process this question. Check the "
                        "backend configuration and try again."
                    )
            else:
                st.subheader("Result")
                st.markdown(answer)
