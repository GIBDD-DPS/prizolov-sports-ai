+ from fastapi import FastAPI, HTTPException
+ from fastapi.middleware.cors import CORSMiddleware
+ 
+ from orchestrator.live_match_state import LiveMatchState
+ 
+ 
+ app = FastAPI(
+     title="Prizolov Sports AI - Public API",
+     version="1.10",
+     description="Public JSON API for prizolov.ru sports widgets (WordPress / Elementor)."
+ )
+ 
+ app.add_middleware(
+     CORSMiddleware,
+     allow_origins=["*"],
+     allow_credentials=True,
+     allow_methods=["*"],
+     allow_headers=["*"],
+ )
+ 
+ 
+ registry = {
+     "rpl_cska_dinamo_2026": LiveMatchState("rpl_cska_dinamo_2026")
+ }
+ 
+ 
+ @app.get("/api/match/live/{match_id}")
+ def get_live_match_state(match_id: str):
+     if match_id not in registry:
+         raise HTTPException(status_code=404, detail="Match not found")
+ 
+     return registry[match_id].build_state()
