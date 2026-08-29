"""Authoritative server-side mirror of the V20 TypographyDocumentModel.

The browser and server consume the same generated font registry contract. This
module normalizes the document-level semantic style catalog, object links, and
per-object overrides before the broader invitation validator runs.
"""
from __future__ import annotations
import copy,re,math
from typing import Any
from typography_contract import COLOR_TOKENS,MAX_TEXT_STYLES, finite_number, normalize_font_id, normalize_pairing_id, paired_font

MODEL_VERSION=1
KHMER_RE=re.compile(r"[\u1780-\u17ff\u19e0-\u19ff]")
STYLE_ID_RE=re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
HEX_RE=re.compile(r"^#[0-9a-fA-F]{6}$")
STYLE_FIELDS=("fontPairing","fontSize","textAutoFit","textAutoFitMax","textMinFontSize","fontWeight","fontStyle","lineHeight","letterSpacing","colorToken","color","textAlign","textVerticalAlign","textWrap","textColumns","textColumnGap","textPadding")
DEFAULT_STYLES={
 "display":{"id":"display","name":"Display","semantic":"display","fontPairing":"serif-formal","fontSize":64,"textAutoFit":"fit","textAutoFitMax":88,"textMinFontSize":18,"fontWeight":"700","fontStyle":"normal","lineHeight":1.08,"letterSpacing":0,"colorToken":"heading","textAlign":"center","textVerticalAlign":"middle","textWrap":"balance","textColumns":1,"textColumnGap":24,"textPadding":8,"builtin":True},
 "heading":{"id":"heading","name":"Heading","semantic":"heading","fontPairing":"serif-formal","fontSize":42,"textAutoFit":"fit","textAutoFitMax":56,"textMinFontSize":16,"fontWeight":"700","fontStyle":"normal","lineHeight":1.16,"letterSpacing":0,"colorToken":"heading","textAlign":"center","textVerticalAlign":"middle","textWrap":"balance","textColumns":1,"textColumnGap":24,"textPadding":8,"builtin":True},
 "subheading":{"id":"subheading","name":"Subheading","semantic":"subheading","fontPairing":"sans-modern","fontSize":28,"textAutoFit":"fit","textAutoFitMax":36,"textMinFontSize":14,"fontWeight":"700","fontStyle":"normal","lineHeight":1.25,"letterSpacing":0,"colorToken":"heading","textAlign":"center","textVerticalAlign":"middle","textWrap":"pretty","textColumns":1,"textColumnGap":24,"textPadding":8,"builtin":True},
 "body":{"id":"body","name":"Body","semantic":"body","fontPairing":"sans-modern","fontSize":18,"textAutoFit":"none","textAutoFitMax":22,"textMinFontSize":12,"fontWeight":"400","fontStyle":"normal","lineHeight":1.5,"letterSpacing":0,"colorToken":"text","textAlign":"left","textVerticalAlign":"top","textWrap":"pretty","textColumns":1,"textColumnGap":24,"textPadding":8,"builtin":True},
 "caption":{"id":"caption","name":"Caption","semantic":"caption","fontPairing":"sans-modern","fontSize":13,"textAutoFit":"none","textAutoFitMax":16,"textMinFontSize":10,"fontWeight":"400","fontStyle":"normal","lineHeight":1.4,"letterSpacing":.1,"colorToken":"muted","textAlign":"center","textVerticalAlign":"middle","textWrap":"normal","textColumns":1,"textColumnGap":16,"textPadding":6,"builtin":True},
 "khmer-ceremonial":{"id":"khmer-ceremonial","name":"Khmer Ceremonial","semantic":"khmer-ceremonial","fontPairing":"ceremonial-khmer","fontSize":48,"textAutoFit":"fit","textAutoFitMax":68,"textMinFontSize":18,"fontWeight":"700","fontStyle":"normal","lineHeight":1.42,"letterSpacing":0,"colorToken":"heading","textAlign":"center","textVerticalAlign":"middle","textWrap":"balance","textColumns":1,"textColumnGap":24,"textPadding":10,"builtin":True},
}
DEFAULT_ORDER=list(DEFAULT_STYLES)

def _number(value:Any,fallback:float,minimum:float,maximum:float,*,strict:bool,integer:bool=False):
 if strict and integer and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(float(value)) and float(value)!=int(float(value)):raise ValueError("Integer typography value required")
 return finite_number(value,fallback,minimum,maximum,strict=strict,integer=integer)

def _clean_name(value:Any,fallback:str,*,strict:bool):
 if not isinstance(value,str):
  if strict:raise ValueError("Invalid text style name")
  return fallback
 value=re.sub(r"[\x00-\x1f\x7f]","",value).strip()
 if not value or len(value)>80:
  if strict:raise ValueError("Invalid text style name")
  return (value[:80] or fallback)
 return value

def _style_id(value:Any,*,strict:bool,fallback="body"):
 if isinstance(value,str) and STYLE_ID_RE.fullmatch(value):return value
 if strict:raise ValueError("Invalid text style ID")
 return fallback

def normalize_style(value:Any,style_id:str,*,strict=True):
 if not isinstance(value,dict):raise ValueError("Text style must be an object")
 semantic=str(value.get("semantic") or (style_id if style_id in DEFAULT_STYLES else "body"))[:40]
 base=DEFAULT_STYLES.get(semantic,DEFAULT_STYLES.get(style_id,DEFAULT_STYLES["body"]))
 font_size=_number(value.get("fontSize",base["fontSize"]),base["fontSize"],8,200,strict=strict)
 maximum=_number(value.get("textAutoFitMax",max(font_size,base["textAutoFitMax"])),max(font_size,base["textAutoFitMax"]),8,200,strict=strict)
 minimum=_number(value.get("textMinFontSize",base["textMinFontSize"]),base["textMinFontSize"],8,72,strict=strict)
 if minimum>maximum:
  if strict:raise ValueError("Minimum text size exceeds auto-fit maximum")
  minimum=maximum
 auto_fit=value.get("textAutoFit",base["textAutoFit"])
 if auto_fit not in {"none","fit"}:raise ValueError("Invalid text auto-fit mode")
 weight=str(value.get("fontWeight",base["fontWeight"]))
 if weight not in {"400","700"}:raise ValueError("Invalid font weight")
 font_style=value.get("fontStyle",base["fontStyle"])
 if font_style not in {"normal","italic"}:raise ValueError("Invalid font style")
 align=value.get("textAlign",base["textAlign"])
 if align not in {"left","center","right","justify"}:raise ValueError("Invalid text alignment")
 vertical=value.get("textVerticalAlign",base["textVerticalAlign"])
 if vertical not in {"top","middle","bottom"}:raise ValueError("Invalid vertical text alignment")
 wrap=value.get("textWrap",base["textWrap"])
 if wrap not in {"normal","balance","pretty"}:raise ValueError("Invalid text wrapping mode")
 token=value.get("colorToken",base["colorToken"])
 if token not in COLOR_TOKENS:raise ValueError("Invalid typography color token")
 result={
  "id":style_id,"name":_clean_name(value.get("name",base["name"]),base["name"],strict=strict),"semantic":semantic,
  "fontPairing":normalize_pairing_id(value.get("fontPairing",value.get("fontPairId",base["fontPairing"])),strict=strict),
  "fontSize":font_size,"textAutoFit":auto_fit,"textAutoFitMax":maximum,"textMinFontSize":minimum,"fontWeight":weight,"fontStyle":font_style,
  "lineHeight":_number(value.get("lineHeight",base["lineHeight"]),base["lineHeight"],.8,3,strict=strict),
  "letterSpacing":_number(value.get("letterSpacing",base["letterSpacing"]),base["letterSpacing"],-2,20,strict=strict),
  "colorToken":token,"textAlign":align,"textVerticalAlign":vertical,"textWrap":wrap,
  "textColumns":_number(value.get("textColumns",base["textColumns"]),base["textColumns"],1,3,strict=strict,integer=True),
  "textColumnGap":_number(value.get("textColumnGap",base["textColumnGap"]),base["textColumnGap"],0,64,strict=strict),
  "textPadding":_number(value.get("textPadding",base["textPadding"]),base["textPadding"],0,64,strict=strict),
  "builtin":bool(value.get("builtin",False)),
 }
 color=value.get("color")
 if color not in (None,""):
  if not isinstance(color,str) or not HEX_RE.fullmatch(color):raise ValueError("Invalid text style color")
  result["color"]=color.lower()
 return result

def normalize_catalog(value:Any,*,strict=True):
 if value in (None,{}):value={}
 if not isinstance(value,dict):raise ValueError("Typography catalog must be an object")
 raw_styles=value.get("styles",{})
 if raw_styles in (None,{}):raw_styles={}
 if not isinstance(raw_styles,dict) or len(raw_styles)>MAX_TEXT_STYLES:raise ValueError("Invalid typography style catalog")
 styles={}
 for style_id in DEFAULT_ORDER:
  merged={**copy.deepcopy(DEFAULT_STYLES[style_id]),**copy.deepcopy(raw_styles.get(style_id,{}) or {}),"id":style_id,"builtin":True}
  styles[style_id]=normalize_style(merged,style_id,strict=strict)
 for raw_id,raw_style in raw_styles.items():
  style_id=_style_id(raw_id,strict=strict)
  if style_id in styles:continue
  styles[style_id]=normalize_style(raw_style,style_id,strict=strict)
 raw_order=value.get("styleOrder",DEFAULT_ORDER)
 if not isinstance(raw_order,list) or len(raw_order)>MAX_TEXT_STYLES:raise ValueError("Invalid typography style order")
 order=[]
 for raw_id in raw_order:
  style_id=_style_id(raw_id,strict=strict)
  if style_id not in styles:raise ValueError("Typography style order references a missing style")
  if style_id not in order:order.append(style_id)
 for style_id in styles:
  if style_id not in order:order.append(style_id)
 default_id=_style_id(value.get("defaultStyleId","body"),strict=strict)
 if default_id not in styles:raise ValueError("Default typography style is missing")
 return {"version":MODEL_VERSION,"defaultStyleId":default_id,"styles":styles,"styleOrder":order}

def _pair_for_font(value:Any):
 font=normalize_font_id(value if value is not None else "noto-serif",strict=True)
 if font in {"noto-sans","noto-sans-khmer"}:return "sans-modern"
 if font=="sans-arial":return "modern-system"
 if font=="sans-trebuchet":return "friendly-system"
 if font=="serif-georgia":return "classic-system"
 return "serif-formal"

def infer_style_id(obj:dict,object_id=""):
 text=str(obj.get("html") or obj.get("text") or "")
 size=_number(obj.get("fontSize",32),32,8,200,strict=False)
 key=str(object_id).lower()
 if KHMER_RE.search(text) and size>=34:return "khmer-ceremonial"
 if key=="title" or size>=52:return "display"
 if size>=34:return "heading"
 if key=="subtitle" or size>=23:return "subheading"
 if size<=14:return "caption"
 return "body"

def _legacy_projection(obj:dict,*,strict=True):
 font_size=_number(obj.get("fontSize",32),32,8,200,strict=strict)
 maximum=_number(obj.get("textAutoFitMax",font_size),font_size,8,200,strict=strict)
 minimum=_number(obj.get("textMinFontSize",10),10,8,72,strict=strict)
 if minimum>maximum:raise ValueError("Minimum text size exceeds auto-fit maximum")
 raw_pair=obj.get("fontPairing",obj.get("fontPairId"))
 raw_token=obj.get("colorToken")
 return {
  "fontPairing":normalize_pairing_id(raw_pair,strict=strict) if raw_pair is not None else _pair_for_font(obj.get("font","noto-serif")),"fontSize":font_size,"textAutoFit":obj.get("textAutoFit","none"),"textAutoFitMax":maximum,"textMinFontSize":minimum,
  "fontWeight":str(obj.get("fontWeight","400")),"fontStyle":obj.get("fontStyle","normal"),
  "lineHeight":_number(obj.get("lineHeight",1.35),1.35,.8,3,strict=strict),"letterSpacing":_number(obj.get("letterSpacing",0),0,-2,20,strict=strict),
  "colorToken":raw_token if raw_token in COLOR_TOKENS else "text","color":str(obj.get("color")).lower() if HEX_RE.fullmatch(str(obj.get("color") or "")) else None,
  "textAlign":obj.get("textAlign","center"),"textVerticalAlign":obj.get("textVerticalAlign","middle"),"textWrap":obj.get("textWrap","normal"),
  "textColumns":_number(obj.get("textColumns",1),1,1,3,strict=strict,integer=True),"textColumnGap":_number(obj.get("textColumnGap",24),24,0,64,strict=strict),"textPadding":_number(obj.get("textPadding",8),8,0,64,strict=strict),
 }

def normalize_overrides(value:Any,*,strict=True):
 if value in (None,{}):return {}
 if not isinstance(value,dict):raise ValueError("Typography overrides must be an object")
 unknown=set(value)-set(STYLE_FIELDS)
 if unknown:raise ValueError("Unsupported typography override")
 probe=normalize_style({**DEFAULT_STYLES["body"],**value,"id":"probe","name":"Probe"},"probe",strict=strict)
 result={}
 for key in value:
  if key=="color":
   color=value[key]
   if not isinstance(color,str) or not HEX_RE.fullmatch(color):raise ValueError("Invalid typography override color")
   result[key]=color.lower()
  else:result[key]=probe[key]
 return result

def normalize_object_typography(obj:dict,object_id:str,catalog:dict,*,strict=True):
 if not isinstance(obj,dict):raise ValueError("Invalid design object")
 if obj.get("type") not in (None,"text","decoration"):return obj
 style_id=obj.get("textStyleId") or infer_style_id(obj,object_id)
 style_id=_style_id(style_id,strict=strict)
 if style_id not in catalog["styles"]:raise ValueError("Design object references a missing text style")
 base=catalog["styles"][style_id]
 overrides=normalize_overrides(obj.get("typographyOverrides"),strict=strict)
 legacy=_legacy_projection(obj,strict=strict)
 if not obj.get("typographyModelVersion"):
  for key in STYLE_FIELDS:
   if key in legacy and legacy[key] is not None and legacy[key]!=base.get(key):overrides.setdefault(key,legacy[key])
 elif obj.get("typographyResolvedSnapshot") is not None:
  snapshot=normalize_overrides(obj.get("typographyResolvedSnapshot"),strict=strict)
  for key in STYLE_FIELDS:
   if key in legacy and key in snapshot and legacy[key]!=snapshot[key]:overrides[key]=legacy[key]
 detached=obj.get("typographyDetached",False)
 if not isinstance(detached,bool):raise ValueError("Invalid typography detach state")
 resolved={**base,**(legacy if detached else overrides)}
 obj["typographyModelVersion"]=MODEL_VERSION;obj["textStyleId"]=style_id;obj["typographyDetached"]=detached;obj["typographyOverrides"]={k:v for k,v in overrides.items() if v is not None}
 locale="km" if KHMER_RE.search(str(obj.get("html") or "")) else "en"
 raw_font=obj.get("font")
 if raw_font is None:compatibility_font=paired_font(resolved["fontPairing"],"en")
 elif obj.get("typographyModelVersion"):
  compatibility_font=normalize_font_id(raw_font,strict=True)
 else:
  compatibility_font=normalize_font_id(raw_font,strict=True)
 obj["font"]=compatibility_font
 obj["fontPairing"]=resolved["fontPairing"]
 obj["colorToken"]=resolved.get("colorToken","text")
 for key in ("fontSize","textAutoFit","textAutoFitMax","textMinFontSize","fontWeight","fontStyle","lineHeight","letterSpacing","textAlign","textVerticalAlign","textWrap","textColumns","textColumnGap","textPadding"):
  obj[key]=resolved[key]
 if resolved.get("color"):obj["color"]=resolved["color"]
 obj["typographyResolvedSnapshot"]={key:resolved[key] for key in STYLE_FIELDS if key in resolved and resolved[key] is not None}
 return obj

def normalize_document_typography(document:dict,*,strict=True):
 catalog=normalize_catalog(document.get("typography"),strict=strict)
 document["typography"]=catalog
 def visit(mapping):
  if not isinstance(mapping,dict):raise ValueError("Invitation contains invalid design objects")
  for object_id,obj in mapping.items():normalize_object_typography(obj,object_id,catalog,strict=strict)
 visit(document.get("objects",{}))
 pages=document.get("designPages",[]) or []
 if not isinstance(pages,list):raise ValueError("Invalid visual pages")
 for page in pages:
  if isinstance(page,dict):visit(page.get("objects",{}))
 return document
