const ORIGIN = "https://jonkabeel-star.github.io";
const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "access-control-allow-origin": ORIGIN,
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "Content-Type, Accept",
  "cache-control": "no-store"
};
const json = (data, status = 200) => new Response(JSON.stringify(data), {status, headers: JSON_HEADERS});
const clean = value => String(value ?? "").replace(/<[^>]*>/g, " ").replace(/&amp;/g,"&").replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/\s+/g," ").trim();
const safeUrl = value => typeof value === "string" && /^https?:\/\//i.test(value);
const timeRanges = {day:"1d",week:"7d",month:"1m",year:"1y"};

async function getJson(url) {
  const response = await fetch(url, {headers:{"accept":"application/json","user-agent":"Jon2AI-Search/1.0"}});
  if (!response.ok) throw new Error("upstream_" + response.status);
  return response.json();
}
function makeResult(title, extract, sourceUrl, source, category, published = null, imageUrl = null, resultType = "webpage") {
  return {title:clean(title).slice(0,300), extract:clean(extract).slice(0,1800), source_url:sourceUrl,
    source, category, published, image_url:safeUrl(imageUrl) ? imageUrl : null, result_type:resultType};
}
async function wikiSearch(query) {
  const lang = /[\u0600-\u06ff]/.test(query) ? "ar" : "en";
  const u = new URL("https://" + lang + ".wikipedia.org/w/api.php");
  Object.entries({action:"query",list:"search",srsearch:query,srnamespace:"0",srlimit:"8",format:"json",utf8:"1"}).forEach(([k,v])=>u.searchParams.set(k,v));
  const data = await getJson(u);
  return (data.query?.search || []).map(x => makeResult(x.title, clean(x.snippet), "https://"+lang+".wikipedia.org/?curid="+x.pageid, "Wikipedia", "web", null, null, "article"));
}
async function newsSearch(query, range) {
  const u = new URL("https://api.gdeltproject.org/api/v2/doc/doc");
  Object.entries({query,mode:"ArtList",format:"json",maxrecords:"15",sort:"HybridRel",...(timeRanges[range]?{timespan:timeRanges[range]}:{})}).forEach(([k,v])=>u.searchParams.set(k,v));
  const data = await getJson(u);
  return (data.articles || []).filter(x=>safeUrl(x.url)).map(x=>makeResult(x.title, [x.domain,x.seendate].filter(Boolean).join(" · "), x.url, "GDELT News", "news", x.seendate, null, "news"));
}
async function researchSearch(query) {
  const cross = new URL("https://api.crossref.org/works");
  Object.entries({"query.bibliographic":query,rows:"8",select:"title,published,URL,abstract"}).forEach(([k,v])=>cross.searchParams.set(k,v));
  const open = new URL("https://api.openalex.org/works");
  Object.entries({search:query,"per-page":"8",select:"id,title,publication_year,primary_location"}).forEach(([k,v])=>open.searchParams.set(k,v));
  const [a,b] = await Promise.allSettled([getJson(cross),getJson(open)]);
  const rows = [];
  if (a.status==="fulfilled") for (const x of a.value.message?.items || []) {
    const title=x.title?.[0], url=x.URL;
    if (title && safeUrl(url)) rows.push(makeResult(title,clean(x.abstract)||"Academic publication record.",url,"Crossref","science",null,null,"research"));
  }
  if (b.status==="fulfilled") for (const x of b.value.results || []) {
    const title=x.title, url=x.primary_location?.landing_page_url || x.id;
    if (title && safeUrl(url)) rows.push(makeResult(title,"Research work · "+(x.publication_year || "date unavailable"),url,"OpenAlex","science",x.publication_year,null,"research"));
  }
  return rows;
}
async function imageSearch(query) {
  const u = new URL("https://commons.wikimedia.org/w/api.php");
  Object.entries({action:"query",generator:"search",gsrsearch:"filetype:bitmap "+query,gsrnamespace:"6",gsrlimit:"12",prop:"imageinfo",iiprop:"url",iiurlwidth:"640",format:"json",origin:"*"}).forEach(([k,v])=>u.searchParams.set(k,v));
  const data = await getJson(u);
  return Object.values(data.query?.pages || {}).map(x => {
    const info=x.imageinfo?.[0] || {};
    const page="https://commons.wikimedia.org/?curid="+x.pageid;
    return makeResult(x.title, "Wikimedia Commons · "+(x.title || ""), page, "Wikimedia Commons", "images", null, info.thumburl || info.url, "image");
  }).filter(x=>x.image_url);
}
async function searxSearch(query, category, range, env) {
  const base=String(env.JON2_SEARXNG_URL || "").replace(/\/$/,"");
  if (!base) return [];
  const u=new URL(base+"/search");
  Object.entries({q:query,format:"json",categories:({web:"general",news:"news",science:"science",images:"images"})[category] || "general",language:"all",safesearch:"1",...(timeRanges[range]?{time_range:range}:{})}).forEach(([k,v])=>u.searchParams.set(k,v));
  const data=await getJson(u);
  return (data.results || []).filter(x=>safeUrl(x.url)).map(x=>makeResult(x.title,x.content,x.url,x.engine || "SearXNG",category,x.publishedDate,x.thumbnail || x.img_src,category==="images"?"image":"webpage"));
}
function rank(query, rows) {
  const words=query.toLocaleLowerCase().match(/[\p{L}\p{N}]{2,}/gu) || [];
  const unique=[...new Set(words)];
  const score=x => {
    const title=(x.title||"").toLocaleLowerCase(), body=(x.extract||"").toLocaleLowerCase();
    return unique.length ? unique.reduce((n,w)=>n+(title.includes(w)?2:body.includes(w)?1:0),0)/unique.length : 0;
  };
  const seen=new Set();
  return rows.map(x=>({...x,relevance:Number(score(x).toFixed(4))}))
    .sort((a,b)=>b.relevance-a.relevance)
    .filter(x=>{const key=x.source_url.split("#")[0].replace(/\/$/,"");if(seen.has(key))return false;seen.add(key);return true;});
}
async function handleSearch(body, env) {
  if (!body || typeof body.query!=="string") return {error:"query_required"};
  const query=body.query.trim(), category=body.category || "web", range=body.time_range || "any";
  const limit=Math.min(20,Math.max(1,Number(body.limit)||10));
  if (query.length<3 || query.length>500) return {error:"query_length_invalid"};
  if (!["web","news","science","images"].includes(category) || !["any","day","week","month","year"].includes(range)) return {error:"filter_invalid"};
  const tasks=[];
  if (env.JON2_SEARXNG_URL) tasks.push(searxSearch(query,category,range,env));
  if (category==="web") { tasks.push(wikiSearch(query)); tasks.push(newsSearch(query,range)); }
  if (category==="news") tasks.push(newsSearch(query,range));
  if (category==="science") tasks.push(researchSearch(query));
  if (category==="images") tasks.push(imageSearch(query));
  const settled=await Promise.allSettled(tasks);
  const rows=settled.filter(x=>x.status==="fulfilled").flatMap(x=>x.value);
  const results=rank(query,rows).slice(0,limit);
  return {project:"Jon2 AI",query,category,time_range:range,status:results.length?"ok":"no_results",cached:false,
    results,sources_used:[...new Set(results.map(x=>x.source))],answer:null,answer_type:"retrieved_sources_only",
    notice:"النتائج مقتطفات وروابط من المصادر؛ ليست إجابة مولّدة من عقل Jon2.",
    sources:results.map(x=>({title:x.title,url:x.source_url,source:x.source}))};
}
export default {
  async fetch(request, env) {
    const url=new URL(request.url);
    if (request.method==="OPTIONS") return new Response(null,{status:204,headers:JSON_HEADERS});
    if (url.pathname==="/" || url.pathname==="/api/health") {
      if (request.method!=="GET") return json({error:"method_not_allowed"},405);
      return json({project:"Jon2 AI",status:"online",service:"search",search_ready:true,chat_ready:false,
        model_ready:false,providers:["Wikipedia","GDELT","Crossref","OpenAlex","Wikimedia Commons",...(env.JON2_SEARXNG_URL?["SearXNG"]:[])]});
    }
    if (url.pathname==="/api/knowledge/search") {
      if (request.method!=="POST") return json({error:"method_not_allowed"},405);
      let body; try { body=await request.json(); } catch { return json({error:"invalid_json"},400); }
      try {
        const result=await handleSearch(body,env);
        if (result.error) return json({error:result.error},400);
        return json(result);
      } catch (error) {
        console.error("Jon2 search failed",error?.message || error);
        return json({error:"search_upstream_unavailable",message:"تعذر جلب النتائج من المصادر حاليًا."},502);
      }
    }
    return json({error:"not_found"},404);
  }
};
