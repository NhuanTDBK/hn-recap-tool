export PYTHONPATH=$PYTHONPATH:"$PWD"

python scripts/fetch_hn_posts.py --limit 50
python scripts/crawl_content.py
python scripts/run_summarization.py
python scripts/push_to_telegram.py