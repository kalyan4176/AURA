import sys
import asyncio
import uvicorn.loops.asyncio

# Force Uvicorn to return SelectorEventLoop on Windows instead of ProactorEventLoop
uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == '__main__':
    uvicorn.run("app.presentation.main:app", host="127.0.0.1", port=8000, reload=False)
