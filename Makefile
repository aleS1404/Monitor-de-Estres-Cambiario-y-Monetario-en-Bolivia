.PHONY: install data report notebooks app test
install: ; pip install -r requirements.txt
data: ; python -m bcb_pipeline update
report: ; python -m stress_monitor.report
notebooks: ; python notebooks/build_notebooks.py
app: ; streamlit run app/streamlit_app.py
test: ; python -m pytest -q
