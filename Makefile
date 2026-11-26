.PHONY: data test baseline replay record dbt verify demo

data:
	python customer/generate_data.py

test:
	python -m pytest -q

baseline: data
	python -m migrator.run --translator baseline

replay: data          ## agent run from saved responses (no API key)
	python -m migrator.run --translator llm --mode replay --write-models

record: data          ## real agent run; needs ANTHROPIC_API_KEY; saves responses
	python -m migrator.run --translator llm --mode record --write-models

dbt:
	cd dbt_project && dbt build --profiles-dir .

verify: dbt
	python scripts/verify_dbt.py

demo: test baseline replay verify
