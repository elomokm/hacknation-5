import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.title("Hack-Nation Demo")

user_input = st.text_area("Input", placeholder="Type something...")

if st.button("Run"):
    if not user_input.strip():
        st.warning("Please enter some input.")
    else:
        with st.spinner("Calling backend..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/predict",
                    json={"input": user_input},
                    timeout=30,
                )
                resp.raise_for_status()
                result = resp.json()
                st.success("Done")
                st.write(result["output"])
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach backend. Is it running? (`make backend`)")
            except Exception as e:
                st.error(f"Error: {e}")
