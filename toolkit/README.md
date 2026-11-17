# 🛠 Toolkit

This folder provides a lightweight visualization and utility toolkit for the UAHSF artifact.

---

## Run the standalone UI demo

Open the following file directly in a browser:

```text
Toolkit/uahsf_ui_demo.html
```

or, from this folder:

```text
uahsf_ui_demo.html
```

This version does not require Python or external packages.

---

## Run the Streamlit UI demo

Install Streamlit:

```bash
pip install streamlit
```

Run the demo from the repository root:

```bash
streamlit run toolkit/uahsf_ui_demo.py
```

---

## Run the prompt payload demo

From the repository root:

```bash
python toolkit/demo_prompt_payload.py
```

This prints a JSON payload showing how UAHSF uncertainty signals can be packaged for the prompt template.
