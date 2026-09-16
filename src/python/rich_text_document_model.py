"""Authoritative V21.0 structured rich-text model and migration boundary."""
from __future__ import annotations
import copy, html, json, math, re
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import Any
from rich_text_contract import *
from typography_contract import COLOR_TOKENS, PAIRING_IDS

MODEL_VERSION=VERSION
ID_RE=re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
STYLE_RE=re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
CONTROL_RE=re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069\ufeff]")
KHMER_RE=re.compile(r"[\u1780-\u17ff\u19e0-\u19ff]")
LATIN_RE=re.compile(r"[A-Za-z\u00c0-\u024f]")
DOC_KEYS={"version","paragraphs","entities"}
PARA_KEYS={"id","paragraphStyleId","overrides","locale","direction","list","tabStops","runs"}
RUN_KEYS={"id","text","marks","locale","entityId"}
ENTITY_KEYS={"id","type","url","title"}
LIST_KEYS={"type","level","start","marker"}
TAB_KEYS={"position","align","leader"}


def _keys(value:dict,allowed:set[str],message:str):
 unknown=set(value)-allowed
 if unknown:raise ValueError(f"{message}: {sorted(unknown)[0]}")

def _obj(value:Any,message:str):
 if not isinstance(value,dict):raise ValueError(message)
 return value

def _finite(value,fallback,minimum,maximum,*,integer=False,strict=False):
 if isinstance(value,bool) or value is None or value=="" or isinstance(value,(list,dict,tuple,set)):
  if strict:raise ValueError("Invalid finite number")
  return fallback
 try:number=float(value)
 except (TypeError,ValueError):
  if strict:raise ValueError("Invalid finite number")
  return fallback
 if not math.isfinite(number):
  if strict:raise ValueError("Invalid finite number")
  return fallback
 if strict and not minimum<=number<=maximum:raise ValueError("Finite number outside allowed range")
 number=max(minimum,min(maximum,number))
 return int(round(number)) if integer else number

def _fnv(value:Any):
 h=0x811c9dc5
 for ch in str(value):
  h^=ord(ch);h=(h*0x01000193)&0xffffffff
 return f"{h:08x}"

def stable_id(prefix,seed):return f"{prefix}-{_fnv(seed)}"

def _safe_id(value,prefix,seed,*,strict=False,used=None):
 raw=str(value or "").strip().lower()
 if not ID_RE.fullmatch(raw):
  if strict and value not in (None,""):raise ValueError("Invalid rich-text ID")
  raw=stable_id(prefix,seed)
 if used is not None:
  base=raw;n=2
  while raw in used:
   if strict:raise ValueError("Duplicate rich-text ID")
   raw=f"{base}-{n}"[:MAX_ID_LENGTH];n+=1
  used.add(raw)
 return raw

def _text(value,*,strict=False,maximum=MAX_RUN_CHARACTERS):
 if not isinstance(value,str):
  if strict:raise ValueError("Run text must be a string")
  value=str(value or "")
 value=value.replace("\r\n","\n").replace("\r","\n")
 if CONTROL_RE.search(value):raise ValueError("Rich text contains forbidden control characters")
 if len(value)>maximum or len(value.encode("utf-8"))>maximum*4:
  if strict:raise ValueError("Rich text exceeds allowed length")
  value=value[:maximum]
 return value

def detect_locale(text,explicit="und"):
 raw=str(explicit or "und").lower()
 if raw in LOCALES and raw!="und":return raw
 value=str(text or "");km=bool(KHMER_RE.search(value));latin=bool(LATIN_RE.search(value))
 return "km" if km and not latin else "en" if latin and not km else "und"

def _locale(value,text,*,strict=False):
 raw=str(value or "und").lower()
 if raw in LOCALES:return detect_locale(text) if raw=="und" else raw
 if strict:raise ValueError("Unsupported locale")
 return detect_locale(text)

def _direction(value,*,strict=False):
 raw=str(value or "auto").lower()
 if raw in DIRECTIONS:return raw
 if strict:raise ValueError("Unsupported direction")
 return "auto"

def safe_url(value,*,strict=False):
 if not isinstance(value,str):
  if strict:raise ValueError("Invalid link URL")
  return ""
 raw=value.strip()
 if not raw or CONTROL_RE.search(raw):
  if strict:raise ValueError("Invalid link URL")
  return ""
 parsed=urlparse(raw);scheme=parsed.scheme.lower()
 if scheme not in URL_PROTOCOLS:
  if strict:raise ValueError("Unsafe link protocol")
  return ""
 if scheme in {"http","https"} and not parsed.hostname:
  if strict:raise ValueError("Invalid link URL")
  return ""
 if scheme=="mailto" and not re.fullmatch(r"mailto:[^\s@]+@[^\s@]+",raw,re.I):
  if strict:raise ValueError("Invalid mail link")
  return ""
 if scheme=="tel" and not re.fullmatch(r"tel:\+?[0-9().\-\s]{3,32}",raw,re.I):
  if strict:raise ValueError("Invalid telephone link")
  return ""
 return raw

def _mark_seed(value):
 value=value if isinstance(value,dict) else {}
 def encode(item):
  if isinstance(item,bool):return "true" if item else "false"
  return str(item)
 return "|".join(f"{key}:{encode(value[key]) if key in value else ''}" for key in ("strong","emphasis","underline","strikethrough","colorToken","fontPairing","fontSize"))

def _marks(value=None,*,strict=False):
 if value is None:return {}
 value=_obj(value,"Marks must be an object")
 if strict:_keys(value,set(MARK_KEYS),"Unknown mark")
 out={}
 for key in ("strong","emphasis","underline","strikethrough"):
  if key in value:
   if not isinstance(value[key],bool):
    if strict:raise ValueError(f"Invalid {key} mark")
   elif value[key]:out[key]=True
 if "colorToken" in value:
  token=str(value["colorToken"] or "")
  if token not in COLOR_TOKENS:
   if strict:raise ValueError("Invalid color token")
  else:out["colorToken"]=token
 if "fontPairing" in value:
  pairing=str(value["fontPairing"] or "")
  if pairing not in PAIRING_IDS:
   if strict:raise ValueError("Invalid font pairing override")
  else:out["fontPairing"]=pairing
 if "fontSize" in value:out["fontSize"]=_finite(value["fontSize"],16,8,200,strict=strict)
 return out

def _overrides(value=None,*,strict=False):
 if value is None:return {}
 value=_obj(value,"Paragraph overrides must be an object")
 if strict:_keys(value,set(PARAGRAPH_OVERRIDE_KEYS),"Unknown paragraph override")
 out={}
 if "textAlign" in value:
  raw=str(value["textAlign"])
  if raw not in ALIGNMENTS:
   if strict:raise ValueError("Invalid paragraph alignment")
  else:out["textAlign"]=raw
 if "lineHeight" in value:out["lineHeight"]=_finite(value["lineHeight"],1.5,.8,3,strict=strict)
 for key in ("spaceBefore","spaceAfter"):
  if key in value:out[key]=_finite(value[key],0,0,200,strict=strict)
 for key in ("indentLeft","indentRight"):
  if key in value:out[key]=_finite(value[key],0,0,400,strict=strict)
 if "firstLineIndent" in value:out["firstLineIndent"]=_finite(value["firstLineIndent"],0,-200,400,strict=strict)
 if "direction" in value:out["direction"]=_direction(value["direction"],strict=strict)
 return out

def _list(value=None,*,strict=False):
 if value is None:return {"type":"none","level":0,"start":1,"marker":"disc"}
 value=_obj(value,"List settings must be an object")
 if strict:_keys(value,LIST_KEYS,"Unknown list field")
 kind=str(value.get("type","none"));marker=str(value.get("marker","decimal" if kind=="ordered" else "disc"))
 if kind not in LIST_TYPES:
  if strict:raise ValueError("Invalid list type")
  kind="none"
 if marker not in LIST_MARKERS:
  if strict:raise ValueError("Invalid list marker")
  marker="decimal" if kind=="ordered" else "disc"
 return {"type":kind,"level":_finite(value.get("level",0),0,0,MAX_LIST_DEPTH,integer=True,strict=strict),"start":_finite(value.get("start",1),1,1,10000,integer=True,strict=strict),"marker":marker}

def _tabs(value=None,*,strict=False):
 if value is None:return []
 if not isinstance(value,list):raise ValueError("Tab stops must be an array")
 if len(value)>MAX_TAB_STOPS:raise ValueError("Too many tab stops")
 out=[]
 for item in value:
  item=_obj(item,"Invalid tab stop")
  if strict:_keys(item,TAB_KEYS,"Unknown tab-stop field")
  position=_finite(item.get("position",0),0,0,1000,strict=strict);align=str(item.get("align","left"));leader=str(item.get("leader","none"))
  if align not in TAB_ALIGNMENTS:
   if strict:raise ValueError("Invalid tab alignment")
   continue
  if leader not in TAB_LEADERS:
   if strict:raise ValueError("Invalid tab leader")
   continue
  out.append({"position":position,"align":align,"leader":leader})
 out.sort(key=lambda x:x["position"])
 positions=set()
 for item in out:
  if item["position"] in positions:
   if strict:raise ValueError("Duplicate tab stop")
  positions.add(item["position"])
 return [item for i,item in enumerate(out) if i==0 or item["position"]!=out[i-1]["position"]]

def _entity(value,id_hint,*,strict=False):
 value=_obj(value,"Invalid link entity")
 if strict:_keys(value,ENTITY_KEYS,"Unknown entity field")
 if value.get("type")!="link":raise ValueError("Unsupported entity type")
 entity_id=_safe_id(value.get("id") or id_hint,"link",id_hint,strict=strict);url=safe_url(value.get("url"),strict=strict)
 if not url:raise ValueError("Link entity requires a safe URL")
 out={"id":entity_id,"type":"link","url":url}
 title=value.get("title")
 if title not in (None,""):
  if not isinstance(title,str):
   if strict:raise ValueError("Invalid link title")
   title=str(title)
  if CONTROL_RE.search(title):raise ValueError("Link title contains forbidden control characters")
  if len(title)>MAX_ENTITY_TITLE_LENGTH:
   if strict:raise ValueError("Link title is too long")
   title=title[:MAX_ENTITY_TITLE_LENGTH]
  if title.strip():out["title"]=title.strip()
 return out

def normalize_rich_text(value:dict,*,strict=False,seed="rich",style_ids=None,default_style_id="body"):
 value=_obj(value,"RichTextDocument must be an object")
 if strict:_keys(value,DOC_KEYS,"Unknown rich-text document field")
 if "version" in value and int(value["version"])!=MODEL_VERSION:raise ValueError("Unsupported rich-text model version")
 style_ids=set(style_ids or ())
 raw_entities=value.get("entities",{})
 if not isinstance(raw_entities,dict):raise ValueError("Entities must be an object")
 if len(raw_entities)>MAX_ENTITIES:raise ValueError("Too many rich-text entities")
 entities={};entity_ids=set()
 for key,item in raw_entities.items():
  entity=_entity(item,key,strict=strict)
  if entity["id"] in entity_ids:raise ValueError("Duplicate entity ID")
  entity_ids.add(entity["id"]);entities[entity["id"]]=entity
 raw_paragraphs=value.get("paragraphs",[])
 if not isinstance(raw_paragraphs,list):raise ValueError("Paragraphs must be an array")
 if len(raw_paragraphs)>MAX_PARAGRAPHS:raise ValueError("Too many paragraphs")
 paragraphs=[];paragraph_ids=set();run_ids=set();total_runs=0;total_chars=0
 for pi,raw in enumerate(raw_paragraphs):
  raw=_obj(raw,"Invalid paragraph")
  if strict:_keys(raw,PARA_KEYS,"Unknown paragraph field")
  raw_runs=raw.get("runs",[])
  if not isinstance(raw_runs,list):raise ValueError("Runs must be an array")
  paragraph_id=_safe_id(raw.get("id"),"p",f"{seed}|p|{pi}|{'␞'.join(str((run or {}).get('text','')) if isinstance(run,dict) else str(run) for run in raw_runs)}",strict=strict,used=paragraph_ids)
  style_id=str(raw.get("paragraphStyleId") or default_style_id).strip().lower()
  if not STYLE_RE.fullmatch(style_id):
   if strict:raise ValueError("Invalid paragraph style ID")
   style_id=default_style_id
  if style_ids and style_id not in style_ids:
   if strict:raise ValueError("Unknown paragraph style ID")
   style_id=default_style_id if default_style_id in style_ids else next(iter(style_ids),"body")
  if not raw_runs and strict:raise ValueError("Paragraph requires at least one run")
  runs=[];paragraph_chars=0
  for ri,rr in enumerate(raw_runs or [{"text":""}]):
   rr=_obj(rr,"Invalid run")
   if strict:_keys(rr,RUN_KEYS,"Unknown run field")
   text=_text(rr.get("text",""),strict=strict)
   run_id=_safe_id(rr.get("id"),"r",f"{seed}|p|{pi}|r|{ri}|{text}|{_mark_seed(rr.get('marks'))}|{str(rr.get('entityId') or '')}",strict=strict,used=run_ids)
   run={"id":run_id,"text":text,"marks":_marks(rr.get("marks"),strict=strict),"locale":_locale(rr.get("locale"),text,strict=strict)}
   if rr.get("entityId") not in (None,""):
    entity_id=str(rr["entityId"])
    if entity_id not in entities:raise ValueError("Run references a missing entity")
    run["entityId"]=entity_id
   runs.append(run);paragraph_chars+=len(text);total_chars+=len(text);total_runs+=1
  if paragraph_chars>MAX_PARAGRAPH_CHARACTERS:raise ValueError("Paragraph is too large")
  if total_runs>MAX_RUNS:raise ValueError("Too many rich-text runs")
  if total_chars>MAX_DOCUMENT_CHARACTERS:raise ValueError("Rich-text document is too large")
  paragraph_text="".join(run["text"] for run in runs)
  paragraphs.append({"id":paragraph_id,"paragraphStyleId":style_id,"overrides":_overrides(raw.get("overrides"),strict=strict),"locale":_locale(raw.get("locale"),paragraph_text,strict=strict),"direction":_direction(raw.get("direction"),strict=strict),"list":_list(raw.get("list"),strict=strict),"tabStops":_tabs(raw.get("tabStops"),strict=strict),"runs":runs})
 if not paragraphs:
  paragraph_id=_safe_id(None,"p",f"{seed}|empty",used=paragraph_ids)
  paragraphs=[{"id":paragraph_id,"paragraphStyleId":default_style_id,"overrides":{},"locale":"und","direction":"auto","list":_list(),"tabStops":[],"runs":[{"id":_safe_id(None,"r",f"{paragraph_id}|empty",used=run_ids),"text":"","marks":{},"locale":"und"}]}]
 return {"version":MODEL_VERSION,"paragraphs":paragraphs,"entities":{key:entities[key] for key in sorted(entities)}}

def export_plain_text(model):
 normalized=normalize_rich_text(model,strict=True)
 return "\n".join("".join(run["text"] for run in p["runs"]) for p in normalized["paragraphs"])

def _run_html(run,entities):
 text=html.escape(run["text"],quote=False).replace("\n","<br>");marks=run.get("marks",{})
 if marks.get("strong"):text=f"<strong>{text}</strong>"
 if marks.get("emphasis"):text=f"<em>{text}</em>"
 if marks.get("underline"):text=f"<u>{text}</u>"
 if marks.get("strikethrough"):text=f"<s>{text}</s>"
 entity=entities.get(run.get("entityId",""))
 if entity and entity.get("type")=="link":text=f'<a href="{html.escape(entity["url"],quote=True)}">{text}</a>'
 return text

def export_legacy_html(model):
 normalized=normalize_rich_text(model,strict=True);parts=[];open_list=None
 def close():
  nonlocal open_list
  if open_list:parts.append(f"</{open_list}>");open_list=None
 for index,p in enumerate(normalized["paragraphs"]):
  body="".join(_run_html(run,normalized["entities"]) for run in p["runs"])
  if p["list"]["type"] in {"bullet","ordered"}:
   tag="ol" if p["list"]["type"]=="ordered" else "ul"
   if open_list!=tag:close();parts.append(f"<{tag}>");open_list=tag
   parts.append(f"<li>{body}</li>")
  else:
   close();parts.append(body)
   if index<len(normalized["paragraphs"])-1:parts.append("<br>")
 close();return "".join(parts)

class _LegacyDepthParser(HTMLParser):
 VOID={"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
 def __init__(self):super().__init__(convert_charrefs=True);self.depth=0
 def handle_starttag(self,tag,attrs):
  if tag.lower() in self.VOID:return
  self.depth+=1
  if self.depth>MAX_LEGACY_NESTING:raise ValueError("Legacy HTML nesting limit exceeded")
 def handle_endtag(self,tag):
  if tag.lower() not in self.VOID:self.depth=max(0,self.depth-1)

class _LegacyParser(HTMLParser):
 def __init__(self,object_id,default_style_id):
  super().__init__(convert_charrefs=True);self.object_id=object_id;self.default_style_id=default_style_id;self.paragraphs=[];self.entities={};self.current=None;self.marks=[];self.lists=[];self.blocked=0;self.entity_stack=[]
 def _ensure(self):
  if self.current is None:
   item=self.lists[-1] if self.lists else {"type":"none","level":0,"start":1,"marker":"disc"}
   self.current={"paragraphStyleId":self.default_style_id,"overrides":{},"locale":"und","direction":"auto","list":dict(item),"tabStops":[],"runs":[]};self.paragraphs.append(self.current)
  return self.current
 def _finish(self):
  if self.current is not None and not self.current["runs"]:self.current["runs"].append({"text":"","marks":{},"locale":"und"})
  self.current=None
 def _current_marks(self):
  out={}
  for item in self.marks:out.update(item)
  return out
 def _add(self,text):
  if self.blocked:return
  text=_text(re.sub(r"[\t ]+"," ",text),strict=False)
  if not text:return
  p=self._ensure();marks=self._current_marks();locale=detect_locale(text);entity_id=self.entity_stack[-1] if self.entity_stack else ""
  if p["runs"] and p["runs"][-1].get("marks")==marks and p["runs"][-1].get("locale")==locale and p["runs"][-1].get("entityId","")==entity_id:p["runs"][-1]["text"]+=text
  else:
   run={"text":text,"marks":marks,"locale":locale}
   if entity_id:run["entityId"]=entity_id
   p["runs"].append(run)
 def handle_starttag(self,tag,attrs):
  tag=tag.lower();attr={str(k).lower():str(v or "") for k,v in attrs}
  if tag in {"script","style","iframe","object","embed","svg","math","template","noscript"}:self.blocked+=1;return
  if self.blocked:return
  if tag in {"p","div","h1","h2","h3","h4","h5","h6","blockquote"}:self._finish();self._ensure()
  if tag in {"ul","ol"}:self.lists.append({"type":"ordered" if tag=="ol" else "bullet","level":min(MAX_LIST_DEPTH,len(self.lists)),"start":1,"marker":"decimal" if tag=="ol" else "disc"})
  if tag=="li":self._finish();self._ensure()
  if tag=="br":self._add("\n");return
  mark={}
  if tag in {"b","strong"}:mark["strong"]=True
  if tag in {"i","em"}:mark["emphasis"]=True
  if tag=="u":mark["underline"]=True
  if tag in {"s","strike","del"}:mark["strikethrough"]=True
  if tag=="span":
   style=attr.get("style","").lower()
   if re.search(r"font-weight\s*:\s*(?:bold|[6-9]00)",style):mark["strong"]=True
   if re.search(r"font-style\s*:\s*(?:italic|oblique)",style):mark["emphasis"]=True
   if re.search(r"text-decoration\s*:[^;]*underline",style):mark["underline"]=True
   if re.search(r"text-decoration\s*:[^;]*line-through",style):mark["strikethrough"]=True
  self.marks.append(mark)
  entity_id=""
  if tag=="a":
   url=safe_url(attr.get("href",""),strict=False)
   if url:
    entity_id=stable_id("link",url);self.entities[entity_id]={"id":entity_id,"type":"link","url":url}
  self.entity_stack.append(entity_id)
 def handle_endtag(self,tag):
  tag=tag.lower()
  if tag in {"script","style","iframe","object","embed","svg","math","template","noscript"}:
   if self.blocked:self.blocked-=1
   return
  if self.blocked:return
  if self.marks:self.marks.pop()
  if self.entity_stack:self.entity_stack.pop()
  if tag in {"li","p","div","h1","h2","h3","h4","h5","h6","blockquote"}:self._finish()
  if tag in {"ul","ol"}:self._finish();self.lists.pop() if self.lists else None
 def handle_data(self,data):self._add(data)

def migrate_legacy(object_id,obj,*,style_ids=None,default_style_id="body"):
 source=str(obj.get("html",obj.get("text","")) or "")
 if len(source.encode("utf-8"))>MAX_HTML_BYTES:raise ValueError("Legacy rich text is too large")
 style_id=str(obj.get("textStyleId") or default_style_id)
 if not STYLE_RE.fullmatch(style_id):style_id=default_style_id
 parser=_LegacyParser(object_id,style_id)
 if re.search(r"<[a-z][\s\S]*>",source,re.I):
  depth_parser=_LegacyDepthParser();depth_parser.feed(source);depth_parser.close();parser.feed(source);parser.close()
 else:
  for line in source.replace("\r\n","\n").replace("\r","\n").split("\n"):
   parser._ensure();parser._add(html.unescape(line));parser._finish()
 if not parser.paragraphs:parser._ensure();parser._finish()
 for p in parser.paragraphs:p["locale"]=detect_locale("".join(r["text"] for r in p["runs"]))
 return normalize_rich_text({"version":MODEL_VERSION,"paragraphs":parser.paragraphs,"entities":parser.entities},seed=str(object_id),style_ids=style_ids,default_style_id=style_id)

def normalize_object_rich_text(obj:dict,object_id:str,document:dict,*,strict=True):
 if obj.get("type") not in (None,"text","decoration"):return obj
 catalog=(document.get("typography") or {}).get("styles") or {};style_ids=set(catalog);default_style_id=(document.get("typography") or {}).get("defaultStyleId","body")
 has_model="richText" in obj;has_version="richTextModelVersion" in obj
 if strict and has_model!=has_version:raise ValueError("Invalid mixed legacy/rich-text state")
 if has_model:
  if obj.get("richTextModelVersion")!=MODEL_VERSION:raise ValueError("Unsupported rich-text model version")
  rich=normalize_rich_text(obj["richText"],strict=strict,seed=object_id,style_ids=style_ids,default_style_id=default_style_id)
  canonical=export_legacy_html(rich);plain=export_plain_text(rich)
  if strict and "html" in obj and str(obj.get("html") or "")!=canonical:raise ValueError("Legacy HTML projection does not match authoritative rich text")
  if strict and "text" in obj and str(obj.get("text") or "")!=plain:raise ValueError("Legacy plain-text projection does not match authoritative rich text")
 else:rich=migrate_legacy(object_id,obj,style_ids=style_ids,default_style_id=default_style_id)
 obj["richTextModelVersion"]=MODEL_VERSION;obj["richText"]=rich;obj["html"]=export_legacy_html(rich)
 if "text" in obj:obj["text"]=export_plain_text(rich)
 return obj

def normalize_document_rich_text(document:dict,*,strict=True):
 modern=document.get("richTextModelVersion")==MODEL_VERSION
 if strict and "richTextModelVersion" in document and not modern:raise ValueError("Unsupported invitation rich-text model version")
 def visit(mapping):
  if not isinstance(mapping,dict):raise ValueError("Invalid design object map")
  for object_id,obj in mapping.items():
   if not isinstance(obj,dict):raise ValueError("Invalid design object")
   has_modern="richText" in obj or "richTextModelVersion" in obj
   if strict and modern and obj.get("type") in (None,"text","decoration") and not has_modern:raise ValueError("Modern invitation contains a legacy text object")
   normalize_object_rich_text(obj,str(object_id),document,strict=strict)
 visit(document.get("objects",{}))
 pages=document.get("designPages",[]) or []
 if not isinstance(pages,list):raise ValueError("Invalid visual pages")
 for page in pages:
  if not isinstance(page,dict):raise ValueError("Invalid visual page")
  visit(page.get("objects",{}))
 document["richTextModelVersion"]=MODEL_VERSION
 return document
