# Health Check Endpoint Addition

Add the following route to main.py if not already present:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
```

This endpoint is used by:
- Docker healthchecks
- Load balancers
- Monitoring systems
- Deployment platforms
