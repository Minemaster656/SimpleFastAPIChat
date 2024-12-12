To install requirements:
> *If you have python but pip doesn't work, use `python -m` before you command (`like python -m pip instal..`). If `python -m` doesn't work, try `py -m`*
1. Create Venv if not exists:
```bash
py -m venv venv
```
On windows:
```bash
venv\Scripts\activate
```
On Linux:
```bash
source venv/bin/activate
```

2. Install requirements:
```bash
pip install websockets uvicorn fastapi asyncio
```

3. Run:
```bash
uvicorn {main or script name if you renamed it}:app --port {your port} --host 0.0.0.0
```
> *(Of course without {})*
