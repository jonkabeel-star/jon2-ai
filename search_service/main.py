"""Standalone, lightweight Jon2 search API. Retrieval only; never generates model answers."""
from __future__ import annotations
import os, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

app = FastAPI(title="Jon2 Search API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jonkabeel-star.github.io"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    category: Literal["web", "news", "science", "images"] = "web"
    time_range: Literal["any", "day", "week", "month", "year"] = "any"
    limit: int = Field(default=10, ge=1, le=20)

_cache: dict[str, tuple[float, list[dict]]] = {}
TTL = 900
UA = "Jon2AI-Search/1.0 (+https://jonkabeel-star.github.io/jon2-ai/)"

def fetch_json(url: str, timeout: int = 9) -> dict:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"upstream_http_{response.status}")
        import json
        data = json.loads(response.read(1_500_000).decode("utf-8"))
        return data if isinstance(data, dict) else {}

def searx_search(query: str, category: str, time_range: str) -> list[dict]:
    base = os.getenv("JON2_SEARXNG_URL", "").strip().rstrip("/")
    if not base:
        return []
    cats = {"web":"general", "news":"news", "science":"science", "images":"images"}
    params = {"q":query, "format":"json", "categories":cats[category], "language":"all", "safesearch":"1"}
    if time_range != "any": params["time_range"] = time_range
    data = fetch_json(base + "/search?" + urlencode(params))
    rows = []
    for x in data.get("results", []):
        if not isinstance(x, dict): continue
        url, title = str(x.get("url","")).strip(), str(x.get("title","")).strip()
        if not title or not url.startswith(("https://","http://")): continue
        image = str(x.get("thumbnail") or x.get("img_src") or "")
        rows.append({"title":title[:300], "extract":str(x.get("content",""))[:1800],
            "source_url":url[:2000], "source":str(x.get("engine","SearXNG"))[:80],
            "category":category, "published":x.get("publishedDate"),
            "image_url":image if image.startswith("https://") else None,
            "result_type":"image" if category=="images" else "webpage"})
    return rows

def wikipedia(query: str) -> list[dict]:
    import json
    langs = ["ar","en"] if re.search(r"[\u0600-\u06ff]", query) else ["en"]
    out=[]
    for lang in langs:
        p=urlencode({"action":"query","list":"search","srsearch":query,"srnamespace":0,"srlimit":6,"format":"json","utf8":1})
        data=fetch_json(f"https://{lang}.wikipedia.org/w/api.php?{p}")
        for hit in data.get("query",{}).get("search",[]):
            title=str(hit.get("title","")).strip()
            if not title: continue
            summary=fetch_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title,safe='')}")
            extract=str(summary.get("extract","")).strip()
            page=summary.get("content_urls",{}).get("desktop",{}).get("page")
            if extract and isinstance(page,str) and page.startswith("https://"):
                out.append({"title":title,"extract":extract[:1800],"source_url":page,
                    "source":"Wikipedia","category":"web","published":None,"image_url":None,"result_type":"article"})
        if out: break
    return out

def gdelt(query: str, time_range: str) -> list[dict]:
    days={"day":1,"week":7,"month":30,"year":365}.get(time_range)
    p={"query":query,"mode":"ArtList","format":"json","maxrecords":15,"sort":"HybridRel"}
    if days: p["startdatetime"]=time.strftime("%Y%m%d%H%M%S",time.gmtime(time.time()-days*86400))
    data=fetch_json("https://api.gdeltproject.org/api/v2/doc/doc?"+urlencode(p))
    out=[]
    for x in data.get("articles",[]):
        url,title=str(x.get("url","")),str(x.get("title","")).strip()
        if title and url.startswith("http"):
            out.append({"title":title,"extract":str(x.get("seendate",""))+" · "+str(x.get("domain","")),
                "source_url":url,"source":"GDELT News","category":"news","published":x.get("seendate"),
                "image_url":None,"result_type":"news"})
    return out

def crossref(query: str) -> list[dict]:
    p=urlencode({"query.bibliographic":query,"rows":8,"select":"title,published,URL,abstract"})
    data=fetch_json("https://api.crossref.org/works?"+p)
    out=[]
    for x in data.get("message",{}).get("items",[]):
        title=(x.get("title") or [""])[0]; url=x.get("URL")
        if title and isinstance(url,str) and url.startswith("https://"):
            abstract=re.sub(r"<[^>]+>"," ",str(x.get("abstract","")))
            out.append({"title":str(title),"extract":abstract[:1800] or "Academic publication record.",
                "source_url":url,"source":"Crossref","category":"science","published":None,
                "image_url":None,"result_type":"research"})
    return out

def openalex(query: str) -> list[dict]:
    p=urlencode({"search":query,"per-page":8,"select":"id,title,publication_year,primary_location"})
    data=fetch_json("https://api.openalex.org/works?"+p)
    out=[]
    for x in data.get("results",[]):
        title=str(x.get("title") or "").strip(); loc=x.get("primary_location") or {}
        url=(loc.get("landing_page_url") if isinstance(loc,dict) else None) or x.get("id")
        if title and isinstance(url,str) and url.startswith("http"):
            out.append({"title":title,"extract":"Research work · "+str(x.get("publication_year") or "date unavailable"),
                "source_url":url,"source":"OpenAlex","category":"science","published":x.get("publication_year"),
                "image_url":None,"result_type":"research"})
    return out

def rank(query: str, rows: list[dict]) -> list[dict]:
    terms=set(re.findall(r"[\w\u0600-\u06ff]{2,}",query.lower()))
    scored=[]
    for x in rows:
        title=set(re.findall(r"[\w\u0600-\u06ff]{2,}",x["title"].lower()))
        body=set(re.findall(r"[\w\u0600-\u06ff]{2,}",x["extract"].lower()))
        score=(len(terms & title)/len(terms)*.72 + len(terms & body)/len(terms)*.28) if terms else 0
        scored.append({**x,"relevance":round(score,4)})
    scored.sort(key=lambda x:(x["relevance"],bool(x.get("published")),len(x.get("extract",""))),reverse=True)
    unique=[]; seen=set()
    for x in scored:
        key=x["source_url"].split("#",1)[0].rstrip("/")
        if key not in seen: seen.add(key); unique.append(x)
    return unique

@app.get("/")
def root():
    return {"project":"Jon2 Search API","status":"online","health":"/api/health","search":"/api/knowledge/search"}

@app.get("/api/health")
def health():
    return {"project":"Jon2 AI","status":"online","service":"search","search_ready":True,
            "searxng_configured":bool(os.getenv("JON2_SEARXNG_URL","").strip()),
            "providers":["SearXNG (optional)","Wikipedia","GDELT","Crossref","OpenAlex"]}

@app.post("/api/knowledge/search")
def search(req: SearchRequest):
    key="|".join((req.query.casefold(),req.category,req.time_range))
    cached=_cache.get(key)
    if cached and cached[0] > time.time():
        rows=cached[1][:req.limit]; was_cached=True
    else:
        providers=[]
        if os.getenv("JON2_SEARXNG_URL","").strip():
            providers.append(lambda:searx_search(req.query,req.category,req.time_range))
        if req.category=="web": providers.append(lambda:wikipedia(req.query))
        elif req.category=="news": providers.append(lambda:gdelt(req.query,req.time_range))
        elif req.category=="science": providers.extend([lambda:crossref(req.query),lambda:openalex(req.query)])
        gathered=[]
        with ThreadPoolExecutor(max_workers=max(1,len(providers))) as pool:
            futures=[pool.submit(fn) for fn in providers]
            for future in as_completed(futures,timeout=20):
                try: gathered.extend(future.result())
                except Exception: pass
        ranked=rank(req.query,gathered)
        _cache[key]=(time.time()+TTL,ranked)
        rows=ranked[:req.limit]; was_cached=False
    return {"project":"Jon2 AI","query":req.query,"category":req.category,"time_range":req.time_range,
        "status":"ok" if rows else "no_results","cached":was_cached,"results":rows,
        "sources_used":sorted({x["source"] for x in rows}),
        "answer":None,"answer_type":"retrieved_sources_only",
        "notice":"النتائج مقتطفات وروابط من المصادر؛ ليست إجابة مولّدة من عقل Jon2.",
        "sources":[{"title":x["title"],"url":x["source_url"],"source":x["source"]} for x in rows]}
