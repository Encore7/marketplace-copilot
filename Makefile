PYTHON ?= python

.PHONY: init-warehouse build-rag-index os-up os-seed api-run ui-run smoke-analyze eval-custom

init-warehouse:
	$(PYTHON) -m backend.app.db.init_seller_warehouse

build-rag-index:
	$(PYTHON) -m backend.app.rag.index_builder

os-up:
	docker compose up -d opensearch

os-seed:
	$(PYTHON) -m backend.app.rag.opensearch_indexer

api-run:
	$(PYTHON) -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

ui-run:
	streamlit run frontend/streamlit_app.py

smoke-analyze:
	curl -sS -X POST "http://localhost:8000/api/v1/analyze" \
		-H "Content-Type: application/json" \
		-d '{"query":"Give me a weekly plan to improve my margins on amazon and avoid compliance issues","marketplaces":["amazon"]}'

eval-custom:
	$(PYTHON) -m eval.run_custom_evals
