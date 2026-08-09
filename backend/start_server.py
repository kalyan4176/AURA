import os
import sys
import asyncio
import uvicorn.loops.asyncio

# Force Uvicorn to return SelectorEventLoop on Windows instead of ProactorEventLoop
if sys.platform == 'win32':
    uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.presentation.main:app", host="0.0.0.0", port=port, reload=False)

