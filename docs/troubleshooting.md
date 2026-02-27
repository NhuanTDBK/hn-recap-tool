# Troubleshooting Guide

Common issues and solutions for HN Pal.

## Database Issues

### Connection Refused

**Symptom**: `could not connect to server: Connection refused`

**Causes**:
- PostgreSQL not running
- Wrong port/host configuration
- Docker container stopped

**Solutions**:
```bash
# Verify PostgreSQL is running
docker-compose ps

# Check if service is healthy
docker-compose logs postgres

# Restart services
docker-compose down && docker-compose up -d

# Verify connection string in .env
cat backend/.env | grep DATABASE_URL
```

### Permission Denied

**Symptom**: `FATAL: password authentication failed for user`

**Solutions**:
- Verify credentials in `DATABASE_URL` match `docker-compose.yml`
- Ensure no special characters need URL encoding
- Try resetting: `docker-compose down -v && docker-compose up -d`

### Migration Errors

**Symptom**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solutions**:
```bash
# Check current version
python -m alembic current

# View migration history
python -m alembic history

# Apply all pending migrations
python -m alembic upgrade head

# If stuck, rollback and reapply
python -m alembic downgrade -1
python -m alembic upgrade head
```

## OpenAI API Issues

### Rate Limit Exceeded

**Symptom**: `RateLimitError: Rate limit exceeded for requests`

**Solutions**:
- Wait 1-2 minutes before retrying
- Check usage at platform.openai.com
- Verify you're on appropriate tier for your request volume
- Consider implementing request queuing/throttling
- Reduce `HN_MAX_POSTS` to process fewer items

### Authentication Error

**Symptom**: `AuthenticationError: Invalid API key`

**Solutions**:
```bash
# Verify key is correct
cat backend/.env | grep OPENAI_API_KEY

# Check for whitespace
python -c "import os; print(repr(os.getenv('OPENAI_API_KEY')))"

# Regenerate key at platform.openai.com
# Update .env with new key
```

### Model Not Found

**Symptom**: `NotFoundError: The model 'xxx' does not exist`

**Solutions**:
- Verify `OPENAI_MODEL` in `.env`
- Check available models at platform.openai.com
- Common models: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
- Ensure you have access to the model

### High Costs

**Symptom**: Unexpected high API costs

**Investigation**:
```sql
-- Check total token usage per user
SELECT user_id, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
FROM user_token_usage
GROUP BY user_id;

-- Check usage by day
SELECT day, SUM(cost_usd)
FROM user_token_usage
GROUP BY day
ORDER BY day DESC;

-- Check if prompt caching is working
SELECT COUNT(*), AVG(token_count)
FROM summaries
WHERE created_at > NOW() - INTERVAL '1 day';
```

**Solutions**:
- Verify prompt caching is enabled in agent configuration
- Check for duplicate API calls (review logs)
- Reduce `HN_MAX_POSTS` or `OPENAI_DEFAULT_MAX_TOKENS`
- Monitor with Langfuse dashboard
- Consider switching to cheaper model (gpt-4o-mini)

## Telegram Bot Issues

### Bot Not Responding

**Symptom**: Bot doesn't respond to `/start` or other commands

**Solutions**:
```bash
# Check if bot script is running
ps aux | grep run_bot.py

# Test bot token
python -c "
import os
import httpx
token = os.getenv('TELEGRAM_BOT_TOKEN')
response = httpx.get(f'https://api.telegram.org/bot{token}/getMe')
print(response.json())
"

# Check logs
tail -f /var/log/hn_pal.log

# Restart bot
python scripts/run_bot.py
```

### Unauthorized Error

**Symptom**: `telegram.error.Unauthorized: Forbidden: bot was blocked by the user`

**Solutions**:
- Unblock bot in Telegram
- Verify `TELEGRAM_CHANNEL_ID` is correct
- For channels, ensure bot is added as admin

### Invalid Token

**Symptom**: `telegram.error.InvalidToken`

**Solutions**:
- Verify `TELEGRAM_BOT_TOKEN` format (should be like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
- Regenerate token via @BotFather if needed
- Check for extra spaces/newlines in `.env`

### Messages Not Delivered

**Symptom**: Bot runs but no messages appear in Telegram

**Solutions**:
```bash
# Check delivery records
python -c "
from app.infrastructure.database.base import SessionLocal
from app.infrastructure.database.models import Delivery
db = SessionLocal()
deliveries = db.query(Delivery).order_by(Delivery.delivered_at.desc()).limit(5).all()
for d in deliveries:
    print(f'User: {d.user_id}, Post: {d.post_id}, Delivered: {d.delivered_at}')
"

# Verify user exists and is active
# Verify posts have summaries generated
# Check bot has permission to send messages to user/channel
```

## RocksDB Issues

### Permission Denied

**Symptom**: `IO error: Permission denied`

**Solutions**:
```bash
# Fix permissions
chmod -R 755 data/content.rocksdb/

# Change ownership
sudo chown -R $USER:$USER data/

# If on EC2/server, ensure user running app owns directory
```

### Lock File Exists

**Symptom**: `IO error: lock file already exists`

**Solutions**:
```bash
# Kill any running processes
pkill -f run_bot.py
pkill -f uvicorn

# Remove lock (only if no processes are running)
rm -f data/content.rocksdb/LOCK

# Restart application
```

### Database Corruption

**Symptom**: `Corruption: corrupted compressed block contents`

**Solutions**:
```bash
# Backup current database
cp -r data/content.rocksdb data/content.rocksdb.backup

# Delete corrupted database (will need to re-crawl)
rm -rf data/content.rocksdb

# Re-run content extraction
python scripts/trigger_content_crawl.py
```

## Content Extraction Issues

### Extraction Failures

**Symptom**: Many posts have `is_crawl_success=False`

**Investigation**:
```sql
-- Check failure rate
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_crawl_success THEN 1 ELSE 0 END) as successes,
    SUM(CASE WHEN is_crawl_success THEN 0 ELSE 1 END) as failures
FROM posts
WHERE created_at > NOW() - INTERVAL '1 day';
```

**Common Causes**:
- Paywall sites
- Anti-scraping protection
- Timeout (check `CONTENT_EXTRACTION_TIMEOUT`)
- Invalid URLs
- Server blocking requests

**Solutions**:
- Increase `CONTENT_EXTRACTION_TIMEOUT` (default 30s)
- Add retry logic with exponential backoff
- Some sites may not be extractable (expected)
- Check extraction logs for specific error patterns

### Slow Extraction

**Symptom**: Content crawling takes very long

**Solutions**:
- Reduce concurrent requests
- Increase timeout but add better error handling
- Skip problematic domains
- Use caching more aggressively

## Redis Issues

### Connection Refused

**Symptom**: `Error connecting to Redis`

**Solutions**:
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping

# Restart Redis
docker-compose restart redis
```

### Memory Limit

**Symptom**: `OOM command not allowed when used memory > 'maxmemory'`

**Solutions**:
- Increase Redis memory limit in `docker-compose.yml`
- Set eviction policy: `maxmemory-policy allkeys-lru`
- Clear old cache: `redis-cli FLUSHDB`

## Scheduler Issues

### Jobs Not Running

**Symptom**: Hourly post collection not happening

**Investigation**:
```bash
# Check APScheduler logs
tail -f /var/log/hn_pal.log | grep APScheduler

# Verify scheduler is initialized
# Look for "Added job" messages in logs
```

**Solutions**:
- Ensure main application is running
- Check scheduler configuration in `app/infrastructure/jobs/data_collector.py`
- Verify no exceptions during job execution
- Check timezone settings

### Duplicate Jobs

**Symptom**: Posts being collected multiple times

**Solutions**:
- Ensure only one instance of application is running
- Check job IDs in APScheduler
- Add `replace_existing=True` to job configuration

## Performance Issues

### High Memory Usage

**Investigation**:
```bash
# Monitor memory
top -p $(pgrep -f uvicorn)

# Check PostgreSQL connections
docker exec -it postgres psql -U user -d hackernews_digest -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions**:
- Reduce connection pool size
- Implement pagination for large queries
- Clear RocksDB cache if too large
- Monitor with profiling tools

### Slow Queries

**Investigation**:
```sql
-- Enable query logging in PostgreSQL
ALTER DATABASE hackernews_digest SET log_min_duration_statement = 1000;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Solutions**:
- Add database indexes
- Optimize queries with EXPLAIN ANALYZE
- Implement caching for frequent queries
- Use async queries properly

## Logs and Debugging

### Enable Debug Logging

```env
# In .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Log Locations

- Application logs: `/var/log/hn_pal.log` (production)
- Docker logs: `docker-compose logs -f [service]`
- Bot logs: stdout when running `scripts/run_bot.py`

### Useful Debug Commands

```bash
# Check all environment variables
python -c "from app.infrastructure.config.settings import settings; print(settings.dict())"

# Test database connection
python -c "from app.infrastructure.database.base import engine; print(engine.connect())"

# Test OpenAI connection
python -c "from openai import OpenAI; client = OpenAI(); print(client.models.list())"

# Test Telegram connection
python scripts/test_telegram.py
```

## Getting Help

If you're still stuck:

1. Check application logs for stack traces
2. Enable DEBUG mode for more detailed output
3. Search existing GitHub issues
4. Create new issue with:
   - Environment details (OS, Python version)
   - Configuration (sanitized, no secrets)
   - Full error message and stack trace
   - Steps to reproduce
