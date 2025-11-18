#!/usr/bin/env python3
"""Development server runner for Space Conquest."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.server.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )
