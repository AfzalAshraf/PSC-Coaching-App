#!/usr/bin/env python3
"""
Kerala PSC Simulator v11 — Flashcard Review + No Emojis + Clean
python PSCapp.py
"""

import subprocess,sys,os,warnings,json,time,re,threading,urllib.request
from pathlib import Path
from typing import Optional
from dataclasses import dataclass,field
from datetime import datetime,timedelta

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"]="ignore"
os.environ["GRPC_VERBOSITY"]="ERROR"
os.environ["GLOG_minloglevel"]="3"

def _install():
    pkgs={"customtkinter":"customtkinter>=5.2.0","google.genai":"google-genai>=1.0.0",
          "openai":"openai>=1.0.0","PyPDF2":"PyPDF2>=3.0.0",
          "youtube_transcript_api":"youtube-transcript-api>=0.6.0",
          "PIL":"Pillow>=10.0.0"}
    miss=[]
    for imp,pip in pkgs.items():
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore");__import__(imp)
        except ImportError:miss.append(pip)
    if miss:
        print("\n  Installing...\n")
        for p in miss:
            n=p.split(">=")[0];print(f"    {n}...",end="",flush=True)
            try:
                subprocess.check_call([sys.executable,"-m","pip","install",p,"--quiet",
                    "--disable-pip-version-check"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                print(" OK")
            except:
                try:
                    subprocess.check_call([sys.executable,"-m","pip","install",n,"--quiet"],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(" OK")
                except:print(" FAIL")
        print()
_install()

import customtkinter as ctk
from tkinter import filedialog,messagebox
try:from PIL import Image;PIL_OK=True
except:PIL_OK=False
try:from google import genai as ggenai;from google.genai import types as gtypes;GEM=True
except:GEM=False
try:from openai import OpenAI;OAI=True
except:OAI=False
try:from PyPDF2 import PdfReader;RPDF=True
except:RPDF=False
try:from youtube_transcript_api import YouTubeTranscriptApi;RYT=True
except:RYT=False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")
PROFILE=Path.home()/".kerala_psc_v11.json"
LOGO_PATH=Path.home()/".kerala_psc_logo.png"


def get_logo(size=48):
    if not PIL_OK:return None
    try:
        if not LOGO_PATH.exists():
            for url in [
                "https://images.emojiterra.com/google/noto-emoji/unicode-17.0/color/1024/1f33f.png",
                "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u1f33f.png"
            ]:
                try:urllib.request.urlretrieve(url,str(LOGO_PATH));break
                except:continue
        if LOGO_PATH.exists():
            img=Image.open(str(LOGO_PATH))
            return ctk.CTkImage(light_image=img,dark_image=img,size=(size,size))
    except:pass
    return None


class C:
    BG="#080c14";CARD="#0f1629";ELEV="#1a2340";HOVER="#243056"
    BD="#182040";BD2="#253565"
    TX="#eef2ff";TX2="#8b9dc3";TX3="#4a5a80";TXB="#ffffff"
    AC="#22c997";AC2="#18a87a";ACD="#0a3d2e"
    GOLD="#ffc857";OK="#22c997";OKB="#0a2e20"
    ER="#ff5c5c";ERB="#3d1515";WN="#ffb347";WNB="#3d2800"
    INF="#5b9fff";INB="#152040";PURPLE="#e0aaff";PURPLEB="#1a1a2e"
    SU={"Polity":"#70b5ff","Math":"#b89aff","Science":"#5aecc0","GK":"#ffc857"}
    TITLE="#060a12"
    # Flashcard SRS
    FC_NEW="#5b9fff";FC_DUE="#ff5c5c";FC_GOOD="#22c997";FC_EASY="#ffc857"


MNEMONIC_INSTRUCTION = """
MNEMONIC TECHNIQUES — use these specific methods:
1. ACRONYMS: Word from first letters. "CCC FRENS" = 8 Core Industries
2. ACROSTICS: Sentence from first letters. "My Very Educated Mother..."
3. CHUNKING: Break sequences. Article 3-6-8: 3 readings, 6 months
4. NUMBER RHYMES: "Teen Sau FIFTEEN" = Article 315
5. VISUAL: Bizarre mental images. "Velu Thampi riding a giant sword"
6. LOCI: Place facts in rooms of your house
7. STORY: Chain facts into a narrative
8. MALAYALAM WORDPLAY: "PERIyar = longest PERIod of flow"

RULES: Short, punchy, weird/funny. NEVER "study more". Always map to the answer.
"""

SRS_INSTRUCTION = """
For EACH question also provide:
- flashcard_front: Simple recall question
- flashcard_back: Answer + mnemonic in 1 line
- feynman_explanation: Explain to a 10-year-old, no jargon, use analogies
- connected_web: Chain of 3-4 connected facts showing knowledge links
"""


# ═══════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════
class Prof:
    _d={"v":11,"provider":"","api_key":"","exams":0,"qs":0,"correct":0,
        "weak":[],"strong":[],"scores":{},"kb_notes":"",
        "lp":{"diff":5,"avg_t":0,"mistakes":[],"best":"","worst":"",
              "sessions":0,"last":"","trend":[]},
        "hist":[],"flashcards":[]}

    @classmethod
    def load(cls):
        try:
            if PROFILE.exists():
                d=json.loads(PROFILE.read_text("utf-8"))
                m={**cls._d,**d};m["lp"]={**cls._d["lp"],**d.get("lp",{})};return m
        except:pass
        return dict(cls._d)

    @classmethod
    def save(cls,d):
        try:PROFILE.write_text(json.dumps(d,indent=2,ensure_ascii=False),"utf-8")
        except:pass

    @classmethod
    def update(cls,d,a,qs,ans,elapsed):
        d["exams"]+=1;d["qs"]+=len(qs);tc=a.get("total_correct",0);d["correct"]+=tc
        for sa in a.get("subject_analysis",[]):
            s=sa.get("subject","")
            if s not in d["scores"]:d["scores"][s]={"t":0,"c":0}
            d["scores"][s]["t"]+=sa.get("total",0);d["scores"][s]["c"]+=sa.get("correct",0)
        weak=set(d.get("weak",[]));strong=set(d.get("strong",[]))
        for sa in a.get("subject_analysis",[]):
            s,p=sa.get("subject",""),sa.get("percentage",0)
            if p<50:weak.add(s);strong.discard(s)
            elif p>=75:strong.add(s);weak.discard(s)
        for w in a.get("weak_areas",[]):weak.add(w)
        d["weak"]=list(weak);d["strong"]=list(strong)
        lp=d["lp"];lp["sessions"]+=1;lp["last"]=datetime.now().isoformat()
        at=elapsed/max(len(qs),1)
        lp["avg_t"]=at if lp["avg_t"]==0 else round((lp["avg_t"]+at)/2,1)
        bp=wp="";bv=-1;wv=101
        for s,sc in d["scores"].items():
            if sc["t"]>0:
                p=sc["c"]/sc["t"]*100
                if p>bv:bv=p;bp=s
                if p<wv:wv=p;wp=s
        lp["best"]=bp;lp["worst"]=wp
        ep=round(tc/max(len(qs),1)*100,1);lp["trend"].append(ep)
        if len(lp["trend"])>20:lp["trend"]=lp["trend"][-20:]
        if ep>=80:lp["diff"]=min(10,lp["diff"]+1)
        elif ep<50:lp["diff"]=max(1,lp["diff"]-1)
        # Add flashcards for wrong answers
        for qr in a.get("question_reviews",[]):
            if not qr.get("was_correct",True):
                subj=""
                for q in qs:
                    if q["id"]==qr["id"]:subj=q.get("subject","");break
                    ms=lp.get("mistakes",[])
                    if subj and subj not in ms:ms.append(subj)
                    if len(ms)>10:ms=ms[-10:]
                    lp["mistakes"]=ms
                # Find original question for full context
                orig_q=next((q for q in qs if q["id"]==qr["id"]),{})
                fc={
                    "front":qr.get("flashcard_front",orig_q.get("question_text","")[:120]),
                    "back":qr.get("flashcard_back",f"{qr.get('correct_answer','')} — {qr.get('mnemonic','')[:80]}"),
                    "explanation":qr.get("explanation",""),
                    "mnemonic":qr.get("mnemonic",""),
                    "feynman":qr.get("feynman_explanation",""),
                    "connected":qr.get("connected_web",""),
                    "subject":subj,
                    "correct_answer":qr.get("correct_answer",""),
                    "question":orig_q.get("question_text",""),
                    "options":orig_q.get("options",{}),
                    "added":datetime.now().isoformat(),
                    "next_review":(datetime.now()+timedelta(days=1)).isoformat(),
                    "interval":1,"ease":2.5,"reviews":0,"box":1
                }
                cards=d.get("flashcards",[]);cards.append(fc)
                if len(cards)>300:cards=cards[-300:]
                d["flashcards"]=cards
        d["hist"].append({"date":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "n":len(qs),"c":tc,"pct":ep,"t":int(elapsed)})
        if len(d["hist"])>50:d["hist"]=d["hist"][-50:]
        cls.save(d);return d

    @classmethod
    def get_due_cards(cls,d):
        """Get flashcards due for review today."""
        now=datetime.now().isoformat()
        cards=d.get("flashcards",[])
        due=[c for c in cards if c.get("next_review","9999")<=now]
        # Sort by box (lower box = more urgent)
        due.sort(key=lambda c:c.get("box",1))
        return due

    @classmethod
    def update_card(cls,d,card_idx,quality):
        """
        Update card after review using Leitner system.
        quality: 'again'=forgot, 'hard'=struggled, 'good'=recalled, 'easy'=instant
        """
        cards=d.get("flashcards",[])
        if card_idx>=len(cards):return
        c=cards[card_idx]
        c["reviews"]=c.get("reviews",0)+1
        now=datetime.now()

        if quality=="again":
            c["box"]=1;c["interval"]=1
        elif quality=="hard":
            c["box"]=max(1,c.get("box",1))
            c["interval"]=max(1,c.get("interval",1))
        elif quality=="good":
            c["box"]=min(5,c.get("box",1)+1)
            # Leitner intervals: box1=1d, box2=3d, box3=7d, box4=16d, box5=45d
            intervals={1:1,2:3,3:7,4:16,5:45}
            c["interval"]=intervals.get(c["box"],1)
        elif quality=="easy":
            c["box"]=min(5,c.get("box",1)+2)
            intervals={1:1,2:3,3:7,4:16,5:45}
            c["interval"]=intervals.get(c["box"],1)*2

        c["next_review"]=(now+timedelta(days=c["interval"])).isoformat()
        cards[card_idx]=c
        d["flashcards"]=cards
        cls.save(d)


# ═══════════════════════════════════════════════════
# PROVIDERS & SCHEMAS
# ═══════════════════════════════════════════════════
PROVS={"gemini":{"name":"Google Gemini 2.5 Flash","tag":"Recommended  Free",
    "model":"gemini-2.5-flash","help":"aistudio.google.com/apikey"},
  "nemotron":{"name":"NVIDIA Nemotron 3 Ultra","tag":"Free  OpenRouter",
    "model":"nvidia/nemotron-3-ultra-550b-a55b:free","help":"openrouter.ai/keys",
    "url":"https://openrouter.ai/api/v1"},
  "llama":{"name":"Meta Llama 4 Maverick","tag":"Free  OpenRouter",
    "model":"meta-llama/llama-4-maverick:free","help":"openrouter.ai/keys",
    "url":"https://openrouter.ai/api/v1"}}

QS={"type":"object","properties":{"questions":{"type":"array","items":{"type":"object",
    "properties":{"id":{"type":"integer"},"subject":{"type":"string","enum":["Polity","Math","Science","GK"]},
    "complexity_rating":{"type":"integer"},"question_text":{"type":"string"},
    "options":{"type":"object","properties":{"A":{"type":"string"},"B":{"type":"string"},
    "C":{"type":"string"},"D":{"type":"string"}},"required":["A","B","C","D"]},
    "correct_option":{"type":"string","enum":["A","B","C","D"]}},
    "required":["id","subject","complexity_rating","question_text","options","correct_option"]}}},"required":["questions"]}

AS={"type":"object","properties":{"overall_score":{"type":"integer"},"total_correct":{"type":"integer"},
    "total_questions":{"type":"integer"},"grade":{"type":"string"},"overall_feedback":{"type":"string"},
    "subject_analysis":{"type":"array","items":{"type":"object","properties":{
    "subject":{"type":"string"},"correct":{"type":"integer"},"total":{"type":"integer"},
    "percentage":{"type":"number"},"verdict":{"type":"string"},"improvement_tip":{"type":"string"}},
    "required":["subject","correct","total","percentage","verdict","improvement_tip"]}},
    "question_reviews":{"type":"array","items":{"type":"object","properties":{
    "id":{"type":"integer"},"was_correct":{"type":"boolean"},"user_answer":{"type":"string"},
    "correct_answer":{"type":"string"},"explanation":{"type":"string"},"mnemonic":{"type":"string"},
    "related_topics":{"type":"string"},"exam_tip":{"type":"string"},
    "flashcard_front":{"type":"string"},"flashcard_back":{"type":"string"},
    "feynman_explanation":{"type":"string"},"connected_web":{"type":"string"}},
    "required":["id","was_correct","user_answer","correct_answer","explanation","mnemonic",
    "related_topics","exam_tip","flashcard_front","flashcard_back","feynman_explanation","connected_web"]}},
    "weak_areas":{"type":"array","items":{"type":"string"}},"study_plan":{"type":"string"}},
    "required":["overall_score","total_correct","total_questions","grade","overall_feedback",
    "subject_analysis","question_reviews","weak_areas","study_plan"]}


def q_prompt(n,diff,prof,kb=""):
    weak=prof.get("weak",[]);lp=prof.get("lp",{})
    ad=""
    if weak or prof.get("scores"):
        ad="\n=ADAPTIVE=\n"
        if weak:ad+=f"WEAK(more Qs):{','.join(weak)}\n"
        for s,sc in prof.get("scores",{}).items():
            if sc["t"]>0:ad+=f"  {s}:{round(sc['c']/sc['t']*100)}%\n"
        t=lp.get("trend",[])
        if len(t)>=2:ad+=f"TREND:{'improving' if t[-1]>=t[-2] else 'struggling'}\n"
    kbb=""
    if kb.strip():kbb=f"\n=MATERIAL=\n{kb[:10000]}\n=END=\n"
    return f"""Generate {n} Kerala PSC MCQs. ONLY raw JSON:
{json.dumps(QS,indent=2)}
IDs 1-{n}. Difficulty {diff}/10. Mix Polity/Math/Science/GK.
Kerala PSC: Constitution, history, geography, renaissance, culture, literature,
math reasoning, science, current affairs. Plausible distractors. Never repeat.
{ad}{kbb}JSON ONLY."""

def a_prompt(qs,ans,prof):
    qa=[{"id":q["id"],"subject":q["subject"],"complexity":q["complexity_rating"],
         "question":q["question_text"][:200],"options":q["options"],
         "correct":q["correct_option"],"user":ans.get(q["id"],"SKIPPED")} for q in qs]
    hc=""
    lp=prof.get("lp",{})
    if prof.get("exams",0)>0:
        hc=f"\n=PROFILE=\nSessions:{lp.get('sessions',0)} Acc:{round(prof.get('correct',0)/max(prof.get('qs',1),1)*100)}%\nWeak:{','.join(prof.get('weak',[])) or 'None'}\nMistakes:{','.join(lp.get('mistakes',[])) or 'None'}\n=END="
    return f"""Analyze Kerala PSC exam. ONLY raw JSON:
{json.dumps(AS,indent=2)}
{MNEMONIC_INSTRUCTION}
{SRS_INSTRUCTION}
Grade:A+(90+)A(80-89)B+(70-79)B(60-69)C(50-59)D(<50). 1-week study plan.{hc}
DATA:{json.dumps(qa,indent=2)}
JSON ONLY."""


# ═══════════════════════════════════════════════════
# KB + LLM
# ═══════════════════════════════════════════════════
class KB:
    @staticmethod
    def from_pdf(fp):
        if not RPDF:return "","PyPDF2 missing"
        try:
            r=PdfReader(fp)
            p=[f"[P{i+1}] {re.sub(r'\\s+',' ',pg.extract_text()).strip()}"
               for i,pg in enumerate(r.pages) if pg.extract_text() and pg.extract_text().strip()]
            return ("\n\n".join(p),f"{len(p)} pages") if p else ("","No text")
        except Exception as e:return "",str(e)
    @staticmethod
    def from_yt(url):
        if not RYT:return "","yt missing"
        try:
            m=re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})',url)
            if not m:return "","Bad URL"
            vid=m.group(1);tr=None
            for la in [['en'],['hi','ml','en-IN'],None]:
                try:
                    tr=(YouTubeTranscriptApi.get_transcript(vid,languages=la) if la
                        else next(iter(YouTubeTranscriptApi.list_transcripts(vid))).fetch())
                    break
                except:continue
            if not tr:return "","No captions"
            t=re.sub(r'\s+',' '," ".join(e.get("text","") for e in tr)).strip()
            return re.sub(r'\[.*?\]','',t),f"{len(t):,} chars"
        except Exception as e:return "",str(e)[:80]

class LLM:
    def __init__(self,prov,key):
        self.prov=prov;self.key=key.strip();self.model=PROVS[prov]["model"]
    def call(self,prompt,schema=None,mt=8000):
        err=None
        for i in range(1,4):
            try:
                raw=self._gem(prompt,schema,mt) if self.prov=="gemini" else self._oai(prompt,mt)
                t=raw.strip()
                for p in ["```json","```JSON","```"]:
                    if t.startswith(p):t=t[len(p):]
                if t.endswith("```"):t=t[:-3]
                t=t.strip();s,e=t.find("{"),t.rfind("}")
                if s!=-1 and e>s:return json.loads(t[s:e+1])
                raise ValueError("No JSON")
            except json.JSONDecodeError as e:err=f"JSON({i}):{e}"
            except Exception as e:
                s=str(e).lower()
                if any(k in s for k in ["api key","401","403","quota"]):raise
                err=f"API({i}):{e}"
            if i<3:time.sleep(2**i)
        raise Exception(err)
    def _gem(self,prompt,schema,mt):
        if not GEM:raise Exception("google-genai missing")
        cl=ggenai.Client(api_key=self.key)
        cfg=dict(system_instruction=prompt,response_mime_type="application/json",
                 temperature=0.8,top_p=0.95,max_output_tokens=mt)
        if schema:cfg["response_schema"]=schema
        return cl.models.generate_content(model=self.model,
            contents=[gtypes.Content(role="user",parts=[gtypes.Part(text="Generate now.")])],
            config=gtypes.GenerateContentConfig(**cfg)).text
    def _oai(self,prompt,mt):
        if not OAI:raise Exception("openai missing")
        cl=OpenAI(api_key=self.key,base_url=PROVS.get(self.prov,{}).get("url","https://openrouter.ai/api/v1"),
            timeout=180,max_retries=0)
        return cl.chat.completions.create(model=self.model,
            messages=[{"role":"system","content":prompt},{"role":"user","content":"Generate now."}],
            temperature=0.8,top_p=0.95,max_tokens=mt,
            extra_headers={"HTTP-Referer":"https://kerala-psc.app","X-Title":"KeralaPSC"}).choices[0].message.content


# ═══════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════
@dataclass
class St:
    prof:dict=field(default_factory=dict)
    prov:str="";key:str="";ready:bool=False
    n_qs:int=10;diff:int=5
    qs:list=field(default_factory=list);ans:dict=field(default_factory=dict)
    idx:int=0;on:bool=False;done:bool=False;t0:float=0
    analysis:Optional[dict]=None;kbs:list=field(default_factory=list);err:str=""
    @property
    def kb(self):return "\n\n".join(t for t in self.kbs if t.strip())
    def reset(self):
        self.qs=[];self.ans={};self.idx=0;self.on=self.done=False
        self.t0=0;self.analysis=None;self.err=""


# ═══════════════════════════════════════════════════
# TITLEBAR — logo only here, no emojis
# ═══════════════════════════════════════════════════
class TitleBar(ctk.CTkFrame):
    def __init__(self,master,root):
        super().__init__(master,fg_color=C.TITLE,height=40,corner_radius=0)
        self.root=root;self._mx=False;self._dx=0;self._dy=0
        self.pack_propagate(False)
        left=ctk.CTkFrame(self,fg_color="transparent")
        left.pack(side="left",fill="y",padx=12)
        logo=get_logo(20)
        if logo:
            ctk.CTkLabel(left,text="",image=logo).pack(side="left",padx=(0,8))
        ctk.CTkLabel(left,text="Kerala PSC Simulator",font=("Segoe UI",12,"bold"),
            text_color=C.AC).pack(side="left")
        ctk.CTkLabel(left,text="v11",font=("Segoe UI",9),text_color=C.TX3).pack(side="left",padx=6)
        right=ctk.CTkFrame(self,fg_color="transparent")
        right.pack(side="right",fill="y")
        for sym,cmd,hc in [("━",self._min,C.HOVER),("▢",self._mx,C.HOVER),("✕",self._cls,"#b91c1c")]:
            ctk.CTkButton(right,text=sym,width=46,height=40,fg_color="transparent",
                hover_color=hc,text_color=C.TX2,font=("Segoe UI",11),
                corner_radius=0,command=cmd).pack(side="left")
        for w in [self,left]:
            w.bind("<Button-1>",self._sd);w.bind("<B1-Motion>",self._drag)
            w.bind("<Double-Button-1>",lambda e:self._maxr())
    def _sd(self,e):self._dx=e.x_root-self.root.winfo_x();self._dy=e.y_root-self.root.winfo_y()
    def _drag(self,e):
        if not self._mx:self.root.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")
    def _min(self):
        self.root.overrideredirect(False);self.root.iconify()
        self.root.after(100,lambda:self.root.bind("<Map>",self._onmap))
    def _onmap(self,e=None):self.root.overrideredirect(True);self.root.unbind("<Map>")
    def _maxr(self):
        if self._mx:self.root.state("normal");(self.root.geometry(self._g) if hasattr(self,"_g") else None)
        else:self._g=self.root.geometry();self.root.state("zoomed")
        self._mx=not self._mx
    def _cls(self):self.root.destroy()


# ═══════════════════════════════════════════════════
# LOADER + REVEAL
# ═══════════════════════════════════════════════════
class Loader(ctk.CTkFrame):
    def __init__(self,master,title="Loading...",sub=""):
        super().__init__(master,fg_color=C.BG)
        c=ctk.CTkFrame(self,fg_color="transparent")
        c.place(relx=0.5,rely=0.45,anchor="center")
        logo=get_logo(64)
        if logo:ctk.CTkLabel(c,text="",image=logo).pack(pady=(0,8))
        ctk.CTkLabel(c,text=title,font=("Segoe UI",22,"bold"),text_color=C.AC).pack()
        self.sub=ctk.CTkLabel(c,text=sub,font=("Segoe UI",13),text_color=C.TX2)
        self.sub.pack(pady=8)
        self.pct=ctk.CTkLabel(c,text="0%",font=("Segoe UI",36,"bold"),text_color=C.TX)
        self.pct.pack(pady=(10,5))
        self.bar=ctk.CTkProgressBar(c,width=400,height=14,corner_radius=7,
            fg_color=C.ELEV,progress_color=C.AC)
        self.bar.pack(pady=5);self.bar.set(0)
        self.stat=ctk.CTkLabel(c,text="Initializing...",font=("Segoe UI",11),text_color=C.TX3)
        self.stat.pack(pady=8)
    def set(self,p,s=""):
        p=max(0,min(100,p));self.pct.configure(text=f"{int(p)}%");self.bar.set(p/100)
        if s:self.stat.configure(text=s)
        self.update_idletasks()

class Reveal(ctk.CTkFrame):
    def __init__(self,master,score,total,grade,on_go):
        super().__init__(master,fg_color=C.BG)
        self._s=score;self._t=total;self._g=grade;self._go=on_go
        self._cur=0;self._target=round(score/max(total,1)*100)
        c=ctk.CTkFrame(self,fg_color="transparent")
        c.place(relx=0.5,rely=0.45,anchor="center")
        logo=get_logo(64)
        if logo:ctk.CTkLabel(c,text="",image=logo).pack(pady=(0,10))
        ctk.CTkLabel(c,text="Exam Complete",font=("Segoe UI",28,"bold"),text_color=C.AC).pack()
        self._pl=ctk.CTkLabel(c,text="0%",font=("Segoe UI",72,"bold"),text_color=C.TX)
        self._pl.pack(pady=15)
        self._pb=ctk.CTkProgressBar(c,width=450,height=18,corner_radius=9,
            fg_color=C.ELEV,progress_color=C.AC)
        self._pb.pack(pady=5);self._pb.set(0)
        self._il=ctk.CTkLabel(c,text="",font=("Segoe UI",16),text_color=C.TX2)
        self._il.pack(pady=10)
        self._gl=ctk.CTkLabel(c,text="",font=("Segoe UI",32,"bold"))
        self._gl.pack(pady=5)
        self._btn=ctk.CTkButton(c,text="View Full Analysis",
            font=("Segoe UI",16,"bold"),fg_color=C.AC,hover_color=C.AC2,
            text_color=C.BG,height=52,corner_radius=14,width=400,command=on_go)
        self.after(500,self._anim)
    def _anim(self):
        if self._cur<self._target:
            self._cur=min(self._cur+2,self._target)
            self._pl.configure(text=f"{self._cur}%")
            self._pb.set(self._cur/100)
            cl=C.ER if self._cur<40 else C.WN if self._cur<60 else C.INF if self._cur<80 else C.OK
            self._pl.configure(text_color=cl);self._pb.configure(progress_color=cl)
            self.after(30,self._anim)
        else:
            gc={"A+":C.GOLD,"A":C.OK,"B+":C.AC,"B":C.INF,"C":C.WN,"D":C.ER}.get(self._g,C.TX)
            self._il.configure(text=f"{self._s} / {self._t} correct")
            self._gl.configure(text=f"Grade: {self._g}",text_color=gc)
            self._btn.pack(pady=20)


# ═══════════════════════════════════════════════════
# FLASHCARD REVIEW PAGE
# ═══════════════════════════════════════════════════
class FlashcardPage(ctk.CTkFrame):
    """
    Leitner box spaced repetition flashcard reviewer.
    Shows due cards, user rates recall, card moves between boxes.
    """
    def __init__(self,master,st,on_back):
        super().__init__(master,fg_color=C.BG)
        self.st=st;self.on_back=on_back
        self.due=Prof.get_due_cards(st.prof)
        self.all_cards=st.prof.get("flashcards",[])
        self.current=0;self._revealed=False
        self._build()

    def _build(self):
        sc=ctk.CTkScrollableFrame(self,fg_color=C.BG,
            scrollbar_button_color=C.BG,scrollbar_button_hover_color=C.HOVER)
        sc.pack(fill="both",expand=True,padx=20,pady=15)

        # Header with stats
        hdr=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
        hdr.pack(fill="x",pady=8)

        ctk.CTkLabel(hdr,text="Flashcard Review",font=("Segoe UI",22,"bold"),
            text_color=C.AC).pack(anchor="w",padx=20,pady=(15,5))

        # Box stats
        boxes={1:0,2:0,3:0,4:0,5:0}
        for c in self.all_cards:
            b=c.get("box",1);boxes[b]=boxes.get(b,0)+1

        stats_row=ctk.CTkFrame(hdr,fg_color="transparent")
        stats_row.pack(fill="x",padx=20,pady=5)

        total_cards=len(self.all_cards)
        due_count=len(self.due)

        for label,val,clr in [
            ("Total Cards",str(total_cards),C.TX),
            ("Due Today",str(due_count),C.FC_DUE if due_count>0 else C.FC_GOOD),
            ("Box 1 (Daily)",str(boxes[1]),C.ER),
            ("Box 2 (3 days)",str(boxes[2]),C.WN),
            ("Box 3 (Weekly)",str(boxes[3]),C.INF),
            ("Box 4 (16 days)",str(boxes[4]),C.AC),
            ("Box 5 (45 days)",str(boxes[5]),C.GOLD)]:
            sf=ctk.CTkFrame(stats_row,fg_color=C.ELEV,corner_radius=8)
            sf.pack(side="left",expand=True,fill="x",padx=2)
            ctk.CTkLabel(sf,text=label,font=("Segoe UI",8),text_color=C.TX3).pack(padx=4,pady=(4,0))
            ctk.CTkLabel(sf,text=val,font=("Segoe UI",14,"bold"),text_color=clr).pack(padx=4,pady=(0,4))

        ctk.CTkLabel(hdr,text="Leitner System: Correct cards advance to higher boxes (reviewed less often). Wrong cards drop back to Box 1 (reviewed daily).",
            font=("Segoe UI",10),text_color=C.TX3,wraplength=700).pack(padx=20,pady=(5,12))

        # Card display area
        self.card_frame=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
        self.card_frame.pack(fill="x",pady=10)

        if not self.due:
            self._show_empty()
        else:
            self._show_card()

        # Browse all cards
        ctk.CTkLabel(sc,text="All Wrong Answers (Flashcard Deck)",
            font=("Segoe UI",16,"bold"),text_color=C.TX).pack(anchor="w",pady=(20,8))

        if not self.all_cards:
            ctk.CTkLabel(sc,text="No flashcards yet. Take an exam and wrong answers will appear here.",
                font=("Segoe UI",12),text_color=C.TX3).pack(anchor="w",padx=10)
        else:
            for i,card in enumerate(reversed(self.all_cards)):
                cf=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=10)
                cf.pack(fill="x",pady=3)

                # Card header
                subj=card.get("subject","")
                box=card.get("box",1)
                box_colors={1:C.ER,2:C.WN,3:C.INF,4:C.AC,5:C.GOLD}
                bc=box_colors.get(box,C.TX3)

                ch=ctk.CTkFrame(cf,fg_color="transparent")
                ch.pack(fill="x",padx=15,pady=(10,4))
                ctk.CTkLabel(ch,text=f"[{subj}]",font=("Segoe UI",10,"bold"),
                    text_color=C.SU.get(subj,C.TX2)).pack(side="left")
                ctk.CTkLabel(ch,text=f"Box {box}",font=("Segoe UI",10,"bold"),
                    text_color=bc).pack(side="right")
                ctk.CTkLabel(ch,text=f"Reviews: {card.get('reviews',0)}",
                    font=("Segoe UI",9),text_color=C.TX3).pack(side="right",padx=10)

                # Question
                q_text=card.get("question",card.get("front",""))
                if q_text:
                    ctk.CTkLabel(cf,text=q_text,font=("Segoe UI",11),
                        text_color=C.TX,wraplength=680,justify="left").pack(anchor="w",padx=15,pady=2)

                # Correct answer
                ctk.CTkLabel(cf,text=f"Answer: {card.get('correct_answer',card.get('back',''))}",
                    font=("Segoe UI",11,"bold"),text_color=C.OK).pack(anchor="w",padx=15,pady=2)

                # Mnemonic
                mnem=card.get("mnemonic","")
                if mnem:
                    mf=ctk.CTkFrame(cf,fg_color=C.WNB,corner_radius=8)
                    mf.pack(fill="x",padx=15,pady=3)
                    ctk.CTkLabel(mf,text="Mnemonic",font=("Segoe UI",9,"bold"),
                        text_color=C.WN).pack(anchor="w",padx=10,pady=(5,1))
                    ctk.CTkLabel(mf,text=mnem,font=("Segoe UI",10),
                        text_color=C.TX,wraplength=650,justify="left").pack(anchor="w",padx=10,pady=(1,5))

                # Explanation
                expl=card.get("explanation","")
                if expl:
                    ef=ctk.CTkFrame(cf,fg_color=C.INB,corner_radius=8)
                    ef.pack(fill="x",padx=15,pady=3)
                    ctk.CTkLabel(ef,text="Explanation",font=("Segoe UI",9,"bold"),
                        text_color=C.INF).pack(anchor="w",padx=10,pady=(5,1))
                    ctk.CTkLabel(ef,text=expl,font=("Segoe UI",10),
                        text_color=C.TX,wraplength=650,justify="left").pack(anchor="w",padx=10,pady=(1,5))

                # Feynman
                feyn=card.get("feynman","")
                if feyn:
                    ff=ctk.CTkFrame(cf,fg_color=C.PURPLEB,corner_radius=8)
                    ff.pack(fill="x",padx=15,pady=3)
                    ctk.CTkLabel(ff,text="Simple Explanation (Feynman)",font=("Segoe UI",9,"bold"),
                        text_color=C.PURPLE).pack(anchor="w",padx=10,pady=(5,1))
                    ctk.CTkLabel(ff,text=feyn,font=("Segoe UI",10),
                        text_color=C.TX,wraplength=650,justify="left").pack(anchor="w",padx=10,pady=(1,5))

                ctk.CTkLabel(cf,text="",height=4).pack()

        # Back button
        ctk.CTkLabel(sc,text="",height=10).pack()
        ctk.CTkButton(sc,text="Back to Menu",font=("Segoe UI",14,"bold"),
            fg_color=C.ELEV,hover_color=C.HOVER,text_color=C.TX,
            height=44,corner_radius=12,width=200,command=self.on_back).pack(pady=10)

    def _show_empty(self):
        for w in self.card_frame.winfo_children():w.destroy()
        ctk.CTkLabel(self.card_frame,text="All caught up!",
            font=("Segoe UI",20,"bold"),text_color=C.OK).pack(pady=(30,10))
        ctk.CTkLabel(self.card_frame,text="No cards due for review right now.\nKeep taking exams to build your flashcard deck.",
            font=("Segoe UI",13),text_color=C.TX2,wraplength=500).pack(pady=(0,30))

    def _show_card(self):
        for w in self.card_frame.winfo_children():w.destroy()
        if self.current>=len(self.due):
            ctk.CTkLabel(self.card_frame,text="Review session complete!",
                font=("Segoe UI",20,"bold"),text_color=C.OK).pack(pady=(30,10))
            reviewed=self.current
            ctk.CTkLabel(self.card_frame,text=f"You reviewed {reviewed} card(s).",
                font=("Segoe UI",13),text_color=C.TX2).pack(pady=(0,30))
            return

        card=self.due[self.current]
        self._revealed=False
        remaining=len(self.due)-self.current

        # Progress
        ctk.CTkLabel(self.card_frame,text=f"Card {self.current+1} of {len(self.due)}  |  {remaining} remaining",
            font=("Segoe UI",11),text_color=C.TX3).pack(padx=20,pady=(15,5))

        prog=ctk.CTkProgressBar(self.card_frame,width=400,height=6,corner_radius=3,
            fg_color=C.ELEV,progress_color=C.AC)
        prog.set((self.current+1)/len(self.due))
        prog.pack(padx=20,pady=(0,10))

        # Subject + box
        subj=card.get("subject","")
        box=card.get("box",1)
        box_colors={1:C.ER,2:C.WN,3:C.INF,4:C.AC,5:C.GOLD}
        info_row=ctk.CTkFrame(self.card_frame,fg_color="transparent")
        info_row.pack(padx=20,pady=5)
        if subj:
            ctk.CTkLabel(info_row,text=f"[{subj}]",font=("Segoe UI",11,"bold"),
                text_color=C.SU.get(subj,C.TX2)).pack(side="left",padx=5)
        ctk.CTkLabel(info_row,text=f"Box {box}",font=("Segoe UI",11,"bold"),
            text_color=box_colors.get(box,C.TX3)).pack(side="left",padx=5)

        # Question (front of card)
        front=card.get("front",card.get("question","No question"))
        ctk.CTkLabel(self.card_frame,text=front,font=("Segoe UI",14),
            text_color=C.TX,wraplength=650,justify="left").pack(padx=20,pady=10)

        # Show options if available
        opts=card.get("options",{})
        if opts:
            for k in "ABCD":
                if k in opts:
                    ctk.CTkLabel(self.card_frame,text=f"  {k}. {opts[k]}",
                        font=("Segoe UI",11),text_color=C.TX3).pack(anchor="w",padx=25,pady=1)

        # Answer area (hidden until reveal)
        self.answer_frame=ctk.CTkFrame(self.card_frame,fg_color=C.ELEV,corner_radius=10)

        # Reveal button
        self.reveal_btn=ctk.CTkButton(self.card_frame,text="Show Answer",
            font=("Segoe UI",14,"bold"),fg_color=C.INF,hover_color="#4a8fdf",
            text_color=C.TXB,height=44,corner_radius=10,width=250,
            command=self._reveal)
        self.reveal_btn.pack(pady=15)

        # Rating buttons (hidden until reveal)
        self.rating_frame=ctk.CTkFrame(self.card_frame,fg_color="transparent")

    def _reveal(self):
        if self._revealed:return
        self._revealed=True
        self.reveal_btn.pack_forget()

        card=self.due[self.current]

        # Show answer
        self.answer_frame.pack(fill="x",padx=20,pady=10)

        correct=card.get("correct_answer",card.get("back",""))
        ctk.CTkLabel(self.answer_frame,text=f"Answer: {correct}",
            font=("Segoe UI",14,"bold"),text_color=C.OK).pack(anchor="w",padx=15,pady=(10,5))

        mnem=card.get("mnemonic","")
        if mnem:
            ctk.CTkLabel(self.answer_frame,text=f"Mnemonic: {mnem}",
                font=("Segoe UI",12),text_color=C.WN,wraplength=620,justify="left").pack(anchor="w",padx=15,pady=3)

        expl=card.get("explanation","")
        if expl:
            ctk.CTkLabel(self.answer_frame,text=expl,
                font=("Segoe UI",11),text_color=C.TX2,wraplength=620,justify="left").pack(anchor="w",padx=15,pady=3)

        feyn=card.get("feynman","")
        if feyn:
            ctk.CTkLabel(self.answer_frame,text=f"Simple: {feyn}",
                font=("Segoe UI",11),text_color=C.PURPLE,wraplength=620,justify="left").pack(anchor="w",padx=15,pady=(3,10))

        # Rating buttons
        self.rating_frame.pack(fill="x",padx=20,pady=10)
        ctk.CTkLabel(self.rating_frame,text="How well did you recall?",
            font=("Segoe UI",12),text_color=C.TX2).pack(pady=(0,8))

        btn_row=ctk.CTkFrame(self.rating_frame,fg_color="transparent")
        btn_row.pack()

        for text,quality,color in [
            ("Forgot","again",C.ER),
            ("Hard","hard",C.WN),
            ("Good","good",C.AC),
            ("Easy","easy",C.GOLD)]:
            ctk.CTkButton(btn_row,text=text,font=("Segoe UI",13,"bold"),
                fg_color=color,hover_color=color,text_color=C.BG,
                height=42,corner_radius=10,width=120,
                command=lambda q=quality:self._rate(q)).pack(side="left",padx=5)

    def _rate(self,quality):
        # Find this card's actual index in the full flashcards list
        card=self.due[self.current]
        all_cards=self.st.prof.get("flashcards",[])
        for i,c in enumerate(all_cards):
            if (c.get("front")==card.get("front") and
                c.get("added")==card.get("added")):
                Prof.update_card(self.st.prof,i,quality)
                break
        self.current+=1
        self._show_card()


# ═══════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════
class Setup(ctk.CTkFrame):
    def __init__(self,master,st,done):
        super().__init__(master,fg_color=C.BG)
        self.st=st;self.done=done;self._pv=ctk.StringVar(value=st.prov or "gemini")
        c=ctk.CTkFrame(self,fg_color="transparent")
        c.place(relx=0.5,rely=0.5,anchor="center")
        logo=get_logo(64)
        if logo:ctk.CTkLabel(c,text="",image=logo).pack(pady=(0,5))
        ctk.CTkLabel(c,text="Kerala PSC",font=("Segoe UI",38,"bold"),text_color=C.AC).pack()
        ctk.CTkLabel(c,text="Adaptive Mock Exam Simulator",font=("Segoe UI",13),text_color=C.TX2).pack()
        p=st.prof
        if p.get("exams",0)>0:
            fc=len(p.get("flashcards",[]))
            ctk.CTkLabel(c,text=f"Welcome back  |  {p['exams']} exams  |  {round(p['correct']/max(p['qs'],1)*100)}% avg  |  {fc} flashcards",
                font=("Segoe UI",11),text_color=C.GOLD).pack(pady=5)
        ctk.CTkFrame(c,height=2,fg_color=C.BD,width=500).pack(pady=15)
        ctk.CTkLabel(c,text="1.  AI Provider",font=("Segoe UI",16,"bold"),
            text_color=C.TX,anchor="w").pack(fill="x",padx=20,pady=(0,8))
        for key,info in PROVS.items():
            row=ctk.CTkFrame(c,fg_color=C.CARD,corner_radius=12)
            row.pack(fill="x",padx=20,pady=3)
            ctk.CTkRadioButton(row,text=f"  {info['name']}",variable=self._pv,value=key,
                font=("Segoe UI",13),text_color=C.TX,fg_color=C.AC,hover_color=C.ACD,
                border_color=C.TX3,command=self._pc).pack(side="left",padx=15,pady=12)
            ctk.CTkLabel(row,text=info["tag"],font=("Segoe UI",10),
                text_color=C.AC).pack(side="right",padx=15)
        self.hlp=ctk.CTkLabel(c,text=f"Get free key: {PROVS[self._pv.get()]['help']}",
            font=("Segoe UI",12),text_color=C.INF)
        self.hlp.pack(pady=8)
        ctk.CTkLabel(c,text="2.  API Key",font=("Segoe UI",16,"bold"),
            text_color=C.TX,anchor="w").pack(fill="x",padx=20,pady=(8,5))
        self.ke=ctk.CTkEntry(c,placeholder_text="Paste API key...",show="*",
            font=("Consolas",13),height=48,corner_radius=12,fg_color=C.ELEV,
            border_color=C.BD2,text_color=C.TX,width=460)
        self.ke.pack(padx=20,pady=5)
        if st.key:self.ke.insert(0,st.key)
        self._sv=ctk.CTkCheckBox(c,text="  Remember locally",font=("Segoe UI",11),
            text_color=C.TX2,fg_color=C.AC,hover_color=C.ACD,border_color=C.TX3)
        self._sv.pack(anchor="w",padx=20,pady=8)
        if st.key:self._sv.select()
        ctk.CTkButton(c,text="Continue",font=("Segoe UI",16,"bold"),fg_color=C.AC,
            hover_color=C.AC2,text_color=C.BG,height=52,corner_radius=14,width=460,
            command=self._go).pack(padx=20,pady=12)
        self.err=ctk.CTkLabel(c,text="",font=("Segoe UI",12),text_color=C.ER)
        self.err.pack()
    def _pc(self):self.hlp.configure(text=f"Get free key: {PROVS[self._pv.get()]['help']}")
    def _go(self):
        k=self.ke.get().strip()
        if not k or len(k)<8:self.err.configure(text="Enter valid key (8+ chars)");return
        self.st.prov=self._pv.get();self.st.key=k;self.st.ready=True
        self.st.prof["provider"]=self.st.prov
        self.st.prof["api_key"]=k if self._sv.get() else ""
        Prof.save(self.st.prof);self.done()


# ═══════════════════════════════════════════════════
# CONFIG — with flashcard review button
# ═══════════════════════════════════════════════════
class Config(ctk.CTkFrame):
    def __init__(self,master,st,go_exam,go_flashcards):
        super().__init__(master,fg_color=C.BG)
        self.st=st;self.go_exam=go_exam;self.go_fc=go_flashcards
        sc=ctk.CTkScrollableFrame(self,fg_color=C.BG,
            scrollbar_button_color=C.BG,scrollbar_button_hover_color=C.HOVER)
        sc.pack(fill="both",expand=True,padx=20,pady=15)

        hdr=ctk.CTkFrame(sc,fg_color="transparent")
        hdr.pack(pady=(0,5))
        logo=get_logo(36)
        if logo:ctk.CTkLabel(hdr,text="",image=logo).pack(side="left",padx=(0,10))
        ctk.CTkLabel(hdr,text="Kerala PSC Simulator",font=("Segoe UI",26,"bold"),
            text_color=C.AC).pack(side="left")

        p=st.prof

        # Flashcard review card — shown prominently at top
        fc_count=len(p.get("flashcards",[]))
        due_count=len(Prof.get_due_cards(p))

        if fc_count>0:
            fcf=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
            fcf.pack(fill="x",pady=10)

            fch=ctk.CTkFrame(fcf,fg_color="transparent")
            fch.pack(fill="x",padx=20,pady=(15,5))
            ctk.CTkLabel(fch,text="Flashcard Review",font=("Segoe UI",16,"bold"),
                text_color=C.PURPLE).pack(side="left")
            if due_count>0:
                ctk.CTkLabel(fch,text=f"{due_count} cards due!",font=("Segoe UI",12,"bold"),
                    text_color=C.FC_DUE).pack(side="right")

            ctk.CTkLabel(fcf,text=f"{fc_count} total cards from wrong answers  |  Review your mistakes to build permanent memory",
                font=("Segoe UI",11),text_color=C.TX3).pack(anchor="w",padx=20,pady=3)
            ctk.CTkLabel(fcf,text="Leitner System: Box 1 (daily) > Box 2 (3 days) > Box 3 (weekly) > Box 4 (16 days) > Box 5 (45 days)",
                font=("Segoe UI",10),text_color=C.TX3).pack(anchor="w",padx=20,pady=(0,8))

            btn_row=ctk.CTkFrame(fcf,fg_color="transparent")
            btn_row.pack(fill="x",padx=20,pady=(0,15))
            if due_count>0:
                ctk.CTkButton(btn_row,text=f"Review {due_count} Due Cards",
                    font=("Segoe UI",14,"bold"),fg_color=C.FC_DUE,hover_color="#cc4040",
                    text_color=C.TXB,height=44,corner_radius=12,width=250,
                    command=self.go_fc).pack(side="left",padx=5)
            ctk.CTkButton(btn_row,text="Browse All Cards",
                font=("Segoe UI",13),fg_color=C.ELEV,hover_color=C.HOVER,
                text_color=C.TX2,height=40,corner_radius=10,width=200,
                command=self.go_fc).pack(side="left",padx=5)

        # Profile stats
        if p.get("exams",0)>0:
            pc=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
            pc.pack(fill="x",pady=8)
            ctk.CTkLabel(pc,text="Your Profile",font=("Segoe UI",14,"bold"),
                text_color=C.TX).pack(anchor="w",padx=20,pady=(12,5))
            sr=ctk.CTkFrame(pc,fg_color="transparent")
            sr.pack(fill="x",padx=20,pady=5)
            for lab,val in [("Exams",str(p["exams"])),("Accuracy",f"{round(p['correct']/max(p['qs'],1)*100)}%"),
                ("Best",p["lp"].get("best","--")),("Weakest",p["lp"].get("worst","--")),
                ("Cards",str(fc_count))]:
                sf=ctk.CTkFrame(sr,fg_color=C.ELEV,corner_radius=8)
                sf.pack(side="left",expand=True,fill="x",padx=3)
                ctk.CTkLabel(sf,text=lab,font=("Segoe UI",9),text_color=C.TX3).pack(padx=8,pady=(6,0))
                ctk.CTkLabel(sf,text=val,font=("Segoe UI",14,"bold"),text_color=C.TX).pack(padx=8,pady=(0,6))
            weak=p.get("weak",[])
            if weak:
                ctk.CTkLabel(pc,text=f"Focus areas: {', '.join(weak[:5])}",font=("Segoe UI",11),
                    text_color=C.WN).pack(anchor="w",padx=20,pady=(5,4))
            trend=p["lp"].get("trend",[])
            if len(trend)>=2:
                ar="Improving" if trend[-1]>=trend[-2] else "Needs work"
                ctk.CTkLabel(pc,text=f"{ar}: {' > '.join(f'{t}%' for t in trend[-6:])}",
                    font=("Consolas",12),text_color=C.AC).pack(anchor="w",padx=20,pady=(0,12))

        # Question count
        qf=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
        qf.pack(fill="x",pady=8)
        ctk.CTkLabel(qf,text="Number of Questions",font=("Segoe UI",14,"bold"),
            text_color=C.TX).pack(anchor="w",padx=20,pady=(15,8))
        self._cnt=ctk.IntVar(value=10)
        bf=ctk.CTkFrame(qf,fg_color="transparent")
        bf.pack(padx=20,pady=(0,15))
        for n in [5,10,15,25,50]:
            ctk.CTkRadioButton(bf,text=f" {n}",variable=self._cnt,value=n,
                font=("Segoe UI",14),text_color=C.TX,fg_color=C.AC,
                hover_color=C.ACD,border_color=C.TX3).pack(side="left",padx=10)

        # Difficulty
        df=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
        df.pack(fill="x",pady=8)
        ctk.CTkLabel(df,text="Difficulty",font=("Segoe UI",14,"bold"),
            text_color=C.TX).pack(anchor="w",padx=20,pady=(15,5))
        rd=p.get("lp",{}).get("diff",5)
        self._df=ctk.CTkSlider(df,from_=1,to=10,number_of_steps=9,width=400,
            fg_color=C.ELEV,progress_color=C.AC,button_color=C.AC,button_hover_color=C.AC2)
        self._df.set(rd);self._df.pack(padx=20,pady=5)
        self._dl=ctk.CTkLabel(df,text=f"Level {rd}",font=("Segoe UI",12,"bold"),text_color=C.AC)
        self._dl.pack(padx=20,pady=(0,15));self._df.configure(command=self._dc)

        # KB
        kf=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14)
        kf.pack(fill="x",pady=8)
        ctk.CTkLabel(kf,text="Study Material",font=("Segoe UI",14,"bold"),
            text_color=C.TX).pack(anchor="w",padx=20,pady=(15,5))
        self.kbl=ctk.CTkLabel(kf,text=f"{len(st.kbs)} source(s)",font=("Segoe UI",11),text_color=C.TX3)
        self.kbl.pack(anchor="w",padx=20,pady=(0,5))
        kr=ctk.CTkFrame(kf,fg_color="transparent")
        kr.pack(padx=20,pady=(0,15))
        for txt,cmd in [("PDFs",self._pdf),("Notes",self._notes),("YouTube",self._yt)]:
            ctk.CTkButton(kr,text=txt,font=("Segoe UI",11),fg_color=C.ELEV,
                hover_color=C.HOVER,text_color=C.TX2,height=34,corner_radius=8,
                command=cmd).pack(side="left",padx=4)

        ctk.CTkButton(sc,text="Begin Exam",font=("Segoe UI",18,"bold"),fg_color=C.AC,
            hover_color=C.AC2,text_color=C.BG,height=56,corner_radius=14,
            command=self._start).pack(fill="x",pady=20)

    def _dc(self,v):
        n=int(v);self._dl.configure(text=f"Level {n} -- "+("Easy" if n<=3 else "Medium" if n<=6 else "Hard" if n<=8 else "Expert"))
    def _start(self):self.st.n_qs=self._cnt.get();self.st.diff=int(self._df.get());self.go_exam()
    def _pdf(self):
        fs=filedialog.askopenfilenames(title="PDFs",filetypes=[("PDF","*.pdf")])
        for f in fs:
            t,m=KB.from_pdf(f)
            if t:self.st.kbs.append(t)
            messagebox.showinfo("PDF",f"{os.path.basename(f)}: {m}")
        self.kbl.configure(text=f"{len(self.st.kbs)} source(s)")
    def _notes(self):
        w=ctk.CTkToplevel(self);w.title("Notes");w.geometry("620x420");w.grab_set()
        tb=ctk.CTkTextbox(w,font=("Segoe UI",12),fg_color=C.ELEV,text_color=C.TX,corner_radius=10)
        tb.pack(fill="both",expand=True,padx=20,pady=20);tb.insert("1.0",self.st.prof.get("kb_notes",""))
        def sv():
            txt=tb.get("1.0","end").strip()
            if txt:self.st.kbs.append(txt)
            self.st.prof["kb_notes"]=txt;Prof.save(self.st.prof)
            self.kbl.configure(text=f"{len(self.st.kbs)} source(s)");w.destroy()
        ctk.CTkButton(w,text="Save",fg_color=C.AC,hover_color=C.AC2,height=40,
            corner_radius=10,command=sv).pack(pady=10)
    def _yt(self):
        w=ctk.CTkToplevel(self);w.title("YouTube");w.geometry("520x200");w.grab_set()
        ue=ctk.CTkEntry(w,placeholder_text="YouTube URL...",font=("Segoe UI",12),
            height=42,corner_radius=10,fg_color=C.ELEV,border_color=C.BD)
        ue.pack(fill="x",padx=20,pady=20)
        sl=ctk.CTkLabel(w,text="",font=("Segoe UI",11));sl.pack()
        def go():
            u=ue.get().strip()
            if not u:return
            sl.configure(text="Extracting...",text_color=C.INF)
            def _d():
                t,m=KB.from_yt(u)
                if t:self.st.kbs.append(t)
                w.after(0,lambda:[messagebox.showinfo("YT",m),w.destroy()] if t
                        else sl.configure(text=m,text_color=C.ER))
            threading.Thread(target=_d,daemon=True).start()
        ctk.CTkButton(w,text="Extract",fg_color=C.AC,hover_color=C.AC2,
            height=42,corner_radius=10,command=go).pack(pady=5)


# ═══════════════════════════════════════════════════
# EXAM
# ═══════════════════════════════════════════════════
class Exam(ctk.CTkFrame):
    def __init__(self,master,st,on_sub):
        super().__init__(master,fg_color=C.BG);self.st=st;self.on_sub=on_sub;self._build()
    def _build(self):
        top=ctk.CTkFrame(self,fg_color=C.CARD,height=48,corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top,text="Mock Exam",font=("Segoe UI",13,"bold"),text_color=C.AC).pack(side="left",padx=16)
        self.tmr=ctk.CTkLabel(top,text="00:00",font=("Consolas",13,"bold"),text_color=C.GOLD)
        self.tmr.pack(side="right",padx=16)
        self.plbl=ctk.CTkLabel(top,text="Q 1/10",font=("Segoe UI",12),text_color=C.TX2)
        self.plbl.pack(side="right",padx=8)
        self.pbar=ctk.CTkProgressBar(top,width=180,height=8,fg_color=C.ELEV,progress_color=C.AC,corner_radius=4)
        self.pbar.pack(side="right",padx=8);self.pbar.set(0)
        info=ctk.CTkFrame(self,fg_color=C.ELEV,height=28,corner_radius=0);info.pack(fill="x")
        self.acnt=ctk.CTkLabel(info,text="Answered: 0/10",font=("Segoe UI",11),text_color=C.TX2)
        self.acnt.pack(side="left",padx=16)
        self.main=ctk.CTkScrollableFrame(self,fg_color=C.BG,scrollbar_button_color=C.BG,scrollbar_button_hover_color=C.HOVER)
        self.main.pack(fill="both",expand=True,padx=16,pady=8)
        self.qc=ctk.CTkFrame(self.main,fg_color=C.CARD,corner_radius=14);self.qc.pack(fill="x",pady=8)
        qh=ctk.CTkFrame(self.qc,fg_color="transparent");qh.pack(fill="x",padx=20,pady=(18,8))
        self.sbdg=ctk.CTkLabel(qh,text=" GK ",font=("Segoe UI",10,"bold"),text_color=C.SU["GK"],fg_color=C.ELEV,corner_radius=10,padx=10,pady=3)
        self.sbdg.pack(side="left")
        self.clbl=ctk.CTkLabel(qh,text="Lvl 5",font=("Segoe UI",11,"bold"),text_color=C.TX3);self.clbl.pack(side="left",padx=10)
        self.qlbl=ctk.CTkLabel(qh,text="Q.1",font=("Consolas",11),text_color=C.TX3);self.qlbl.pack(side="right")
        ctk.CTkFrame(self.qc,height=1,fg_color=C.BD).pack(fill="x",padx=20)
        self.qtxt=ctk.CTkTextbox(self.qc,font=("Segoe UI",14),fg_color=C.CARD,text_color=C.TX,height=130,corner_radius=0,wrap="word",activate_scrollbars=False)
        self.qtxt.pack(fill="x",padx=20,pady=14)
        ctk.CTkFrame(self.qc,height=1,fg_color=C.BD).pack(fill="x",padx=20)
        self._sel=ctk.StringVar(value="")
        self.of=ctk.CTkFrame(self.qc,fg_color="transparent");self.of.pack(fill="x",padx=20,pady=14)
        self.obs={}
        for k in "ABCD":
            b=ctk.CTkRadioButton(self.of,text=f" {k}. --",variable=self._sel,value=k,font=("Segoe UI",13),text_color=C.TX,fg_color=C.AC,hover_color=C.ACD,border_color=C.TX3)
            b.pack(fill="x",pady=4,padx=8);self.obs[k]=b
        nav=ctk.CTkFrame(self.main,fg_color="transparent");nav.pack(fill="x",pady=8)
        self.pbtn=ctk.CTkButton(nav,text="Prev",font=("Segoe UI",12),fg_color=C.ELEV,hover_color=C.HOVER,text_color=C.TX,height=40,corner_radius=10,width=100,command=self._prev);self.pbtn.pack(side="left",padx=4)
        ctk.CTkButton(nav,text="Skip",font=("Segoe UI",12),fg_color=C.ELEV,hover_color=C.HOVER,text_color=C.TX2,height=40,corner_radius=10,width=80,command=self._skip).pack(side="left",padx=4)
        self.nbtn=ctk.CTkButton(nav,text="Save & Next",font=("Segoe UI",12,"bold"),fg_color=C.AC,hover_color=C.AC2,text_color=C.BG,height=40,corner_radius=10,width=150,command=self._snext);self.nbtn.pack(side="left",padx=4)
        ctk.CTkButton(nav,text="Submit Exam",font=("Segoe UI",12,"bold"),fg_color="#dc2626",hover_color="#b91c1c",text_color="white",height=40,corner_radius=10,width=140,command=self._submit).pack(side="right",padx=4)
        ctk.CTkLabel(self.main,text="Navigator",font=("Segoe UI",11,"bold"),text_color=C.TX2).pack(anchor="w",pady=(8,4))
        self.nf=ctk.CTkFrame(self.main,fg_color=C.CARD,corner_radius=10);self.nf.pack(fill="x",pady=4);self.nbs=[];self._tick()
    def load(self):
        for w in self.nf.winfo_children():w.destroy()
        self.nbs=[];tot=len(self.st.qs);cols=min(10,tot)
        for i in range(tot):
            b=ctk.CTkButton(self.nf,text=str(i+1),width=38,height=33,font=("Segoe UI",10),fg_color=C.ELEV,hover_color=C.HOVER,text_color=C.TX,corner_radius=6,command=lambda x=i:self._goto(x))
            b.grid(row=i//cols,column=i%cols,padx=2,pady=2);self.nbs.append(b)
        self._show(0)
    def _show(self,idx):
        self.st.idx=idx;q=self.st.qs[idx];tot=len(self.st.qs)
        self.plbl.configure(text=f"Q {idx+1}/{tot}");self.pbar.set((idx+1)/tot)
        self.acnt.configure(text=f"Answered: {len(self.st.ans)}/{tot}")
        s=q["subject"];co=q["complexity_rating"]
        self.sbdg.configure(text=f" {s.upper()} ",text_color=C.SU.get(s,C.TX2))
        self.clbl.configure(text=f"Lvl {co}",text_color=C.OK if co<=3 else C.WN if co<=6 else C.ER)
        self.qlbl.configure(text=f"Q.{idx+1}")
        self.qtxt.delete("1.0","end");self.qtxt.insert("1.0",q["question_text"])
        for k,b in self.obs.items():b.configure(text=f" {k}. {q['options'].get(k,'--')}")
        self._sel.set(self.st.ans.get(q["id"],""))
        for i,nb in enumerate(self.nbs):
            qid=self.st.qs[i]["id"]
            if i==idx:nb.configure(fg_color=C.INF,text_color=C.TXB)
            elif qid in self.st.ans:nb.configure(fg_color=C.ACD,text_color=C.AC)
            else:nb.configure(fg_color=C.ELEV,text_color=C.TX)
        self.pbtn.configure(state="normal" if idx>0 else "disabled")
        self.nbtn.configure(text="Save (Last)" if idx>=tot-1 else "Save & Next")
    def _sv(self):
        q=self.st.qs[self.st.idx];sel=self._sel.get()
        if sel:self.st.ans[q["id"]]=sel
    def _snext(self):self._sv();(self._show(self.st.idx+1) if self.st.idx<len(self.st.qs)-1 else None)
    def _skip(self):(self._show(self.st.idx+1) if self.st.idx<len(self.st.qs)-1 else None)
    def _prev(self):self._sv();(self._show(self.st.idx-1) if self.st.idx>0 else None)
    def _goto(self,i):self._sv();self._show(i)
    def _submit(self):
        self._sv();a=len(self.st.ans);t=len(self.st.qs)
        msg=f"Answered {a}/{t}."
        if t-a>0:msg+=f"\n{t-a} unanswered = wrong."
        if messagebox.askyesno("Submit",msg+"\nSubmit?"):self.on_sub()
    def _tick(self):
        if self.st.on and not self.st.done:
            el=int(time.time()-self.st.t0);m,s=divmod(el,60);h,m=divmod(m,60)
            self.tmr.configure(text=f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")
        self.after(1000,self._tick)


# ═══════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════
class Analysis(ctk.CTkFrame):
    def __init__(self,master,st,on_new):
        super().__init__(master,fg_color=C.BG);self.st=st;self.on_new=on_new
    def show(self):
        for w in self.winfo_children():w.destroy()
        a=self.st.analysis;
        if not a:return
        sc=ctk.CTkScrollableFrame(self,fg_color=C.BG,scrollbar_button_color=C.BG,scrollbar_button_hover_color=C.HOVER)
        sc.pack(fill="both",expand=True,padx=10,pady=10)
        hdr=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=16);hdr.pack(fill="x",padx=8,pady=8)
        h=ctk.CTkFrame(hdr,fg_color="transparent");h.pack(fill="x",padx=28,pady=18)
        left=ctk.CTkFrame(h,fg_color="transparent");left.pack(side="left")
        ctk.CTkLabel(left,text="Exam Analysis",font=("Segoe UI",22,"bold"),text_color=C.AC).pack(anchor="w")
        ctk.CTkLabel(left,text=a.get("overall_feedback",""),font=("Segoe UI",12),text_color=C.TX2,wraplength=500).pack(anchor="w",pady=5)
        right=ctk.CTkFrame(h,fg_color="transparent");right.pack(side="right")
        pct=a.get("overall_score",0);gr=a.get("grade","?")
        gc={"A+":C.GOLD,"A":C.OK,"B+":C.AC,"B":C.INF,"C":C.WN,"D":C.ER}.get(gr,C.TX)
        ctk.CTkLabel(right,text=f"{pct}%",font=("Segoe UI",44,"bold"),text_color=gc).pack()
        ctk.CTkLabel(right,text=f"Grade {gr}  |  {a.get('total_correct',0)}/{a.get('total_questions',0)}",font=("Segoe UI",13),text_color=C.TX2).pack()
        wrong=a.get("total_questions",0)-a.get("total_correct",0)
        if wrong>0:
            ctk.CTkLabel(hdr,text=f"{wrong} wrong answers added as flashcards for spaced review",font=("Segoe UI",11),text_color=C.INF).pack(pady=(0,14))

        ctk.CTkLabel(sc,text="Subjects",font=("Segoe UI",18,"bold"),text_color=C.TX).pack(anchor="w",padx=8,pady=(14,6))
        sf=ctk.CTkFrame(sc,fg_color="transparent");sf.pack(fill="x",padx=8);sf.columnconfigure((0,1),weight=1)
        ic={"Polity":"[P]","Math":"[M]","Science":"[S]","GK":"[G]"}
        for i,sa in enumerate(a.get("subject_analysis",[])):
            cd=ctk.CTkFrame(sf,fg_color=C.CARD,corner_radius=12);cd.grid(row=i//2,column=i%2,sticky="nsew",padx=4,pady=4)
            su=sa.get("subject","?");scl=C.SU.get(su,C.TX2);sp=sa.get("percentage",0)
            ctk.CTkLabel(cd,text=f"{ic.get(su,'')} {su}",font=("Segoe UI",14,"bold"),text_color=scl).pack(anchor="w",padx=14,pady=(10,2))
            bar=ctk.CTkProgressBar(cd,width=180,height=10,corner_radius=5,fg_color=C.ELEV,progress_color=scl);bar.set(sp/100);bar.pack(padx=14,pady=3,anchor="w")
            ctk.CTkLabel(cd,text=f"{sa.get('correct',0)}/{sa.get('total',0)} ({sp:.0f}%)",font=("Segoe UI",11),text_color=C.TX2).pack(anchor="w",padx=14)
            ctk.CTkLabel(cd,text=sa.get("verdict",""),font=("Segoe UI",11,"bold"),text_color=C.OK if sp>=60 else C.WN if sp>=40 else C.ER).pack(anchor="w",padx=14,pady=2)
            ctk.CTkLabel(cd,text=sa.get("improvement_tip",""),font=("Segoe UI",10),text_color=C.TX3,wraplength=320).pack(anchor="w",padx=14,pady=(2,10))

        ctk.CTkLabel(sc,text="Question-by-Question Teaching",font=("Segoe UI",18,"bold"),text_color=C.TX).pack(anchor="w",padx=8,pady=(18,6))
        for qr in a.get("question_reviews",[]):
            qid=qr["id"];ok=qr.get("was_correct",False);oq=next((q for q in self.st.qs if q["id"]==qid),None)
            cd=ctk.CTkFrame(sc,fg_color=C.CARD,corner_radius=14);cd.pack(fill="x",padx=8,pady=5)
            qh=ctk.CTkFrame(cd,fg_color=C.OKB if ok else C.ERB,corner_radius=10);qh.pack(fill="x",padx=5,pady=5)
            rc=C.OK if ok else C.ER
            ctk.CTkLabel(qh,text=f"{'CORRECT' if ok else 'INCORRECT'}  Q.{qid}",font=("Segoe UI",13,"bold"),text_color=rc).pack(side="left",padx=14,pady=8)
            if oq:
                ctk.CTkLabel(qh,text=f"{oq.get('subject','')}  Lvl {oq.get('complexity_rating','')}",font=("Segoe UI",10),text_color=C.TX3).pack(side="right",padx=14,pady=8)
                ctk.CTkLabel(cd,text=oq.get("question_text",""),font=("Segoe UI",12),text_color=C.TX,wraplength=680,justify="left").pack(anchor="w",padx=18,pady=(8,4))
                opts=oq.get("options",{});ck=qr.get("correct_answer","");uk=qr.get("user_answer","SKIP")
                for k in "ABCD":
                    if k==ck:ic_,cl,bg="[correct]",C.OK,C.OKB
                    elif k==uk and uk!=ck:ic_,cl,bg="[your answer]",C.ER,C.ERB
                    else:ic_,cl,bg="",C.TX3,"transparent"
                    or_=ctk.CTkFrame(cd,fg_color=bg,corner_radius=6);or_.pack(fill="x",padx=18,pady=1)
                    ctk.CTkLabel(or_,text=f"  {k}. {opts.get(k,'')}  {ic_}",font=("Segoe UI",11),text_color=cl).pack(anchor="w",padx=8,pady=3)
            ctk.CTkLabel(cd,text=f"Your answer: {qr.get('user_answer','SKIP')}   Correct: {qr.get('correct_answer','')}",font=("Segoe UI",11,"bold"),text_color=rc).pack(anchor="w",padx=18,pady=(6,3))
            for title,key,color,bg in [("Explanation","explanation",C.INF,C.INB),("Mnemonic Trick","mnemonic",C.WN,C.WNB),("Connected Knowledge","connected_web",C.AC,C.ACD),("Related Topics","related_topics",C.AC,C.ACD),("Exam Strategy","exam_tip",C.GOLD,C.ELEV)]:
                val=qr.get(key,"")
                if not val:continue
                fr=ctk.CTkFrame(cd,fg_color=bg,corner_radius=10);fr.pack(fill="x",padx=14,pady=3)
                ctk.CTkLabel(fr,text=title,font=("Segoe UI",11,"bold"),text_color=color).pack(anchor="w",padx=12,pady=(7,1))
                ctk.CTkLabel(fr,text=val,font=("Segoe UI",11),text_color=C.TX,wraplength=660,justify="left").pack(anchor="w",padx=12,pady=(1,8))
            feyn=qr.get("feynman_explanation","")
            if feyn:
                ff=ctk.CTkFrame(cd,fg_color=C.PURPLEB,corner_radius=10);ff.pack(fill="x",padx=14,pady=3)
                ctk.CTkLabel(ff,text="Feynman (Explain Like I'm 10)",font=("Segoe UI",11,"bold"),text_color=C.PURPLE).pack(anchor="w",padx=12,pady=(7,1))
                ctk.CTkLabel(ff,text=feyn,font=("Segoe UI",11),text_color=C.TX,wraplength=660,justify="left").pack(anchor="w",padx=12,pady=(1,8))
            if not ok:
                fc_f=qr.get("flashcard_front","");fc_b=qr.get("flashcard_back","")
                if fc_f or fc_b:
                    fcf=ctk.CTkFrame(cd,fg_color="#0d1f3c",corner_radius=10);fcf.pack(fill="x",padx=14,pady=3)
                    ctk.CTkLabel(fcf,text="Flashcard (saved for spaced review)",font=("Segoe UI",11,"bold"),text_color=C.INF).pack(anchor="w",padx=12,pady=(7,1))
                    if fc_f:ctk.CTkLabel(fcf,text=f"Q: {fc_f}",font=("Segoe UI",11,"bold"),text_color=C.TX,wraplength=660).pack(anchor="w",padx=12,pady=1)
                    if fc_b:ctk.CTkLabel(fcf,text=f"A: {fc_b}",font=("Segoe UI",11),text_color=C.AC,wraplength=660).pack(anchor="w",padx=12,pady=(1,8))
            ctk.CTkLabel(cd,text="",height=4).pack()

        weak=a.get("weak_areas",[])
        if weak:
            ctk.CTkLabel(sc,text="Weak Areas",font=("Segoe UI",18,"bold"),text_color=C.WN).pack(anchor="w",padx=8,pady=(16,6))
            wf=ctk.CTkFrame(sc,fg_color=C.WNB,corner_radius=12);wf.pack(fill="x",padx=8,pady=4)
            for w in weak:ctk.CTkLabel(wf,text=f"  - {w}",font=("Segoe UI",12),text_color=C.TX,wraplength=680,justify="left").pack(anchor="w",padx=18,pady=2)
            ctk.CTkLabel(wf,text="",height=4).pack()
        plan=a.get("study_plan","")
        if plan:
            ctk.CTkLabel(sc,text="Study Plan",font=("Segoe UI",18,"bold"),text_color=C.INF).pack(anchor="w",padx=8,pady=(14,6))
            pf=ctk.CTkFrame(sc,fg_color=C.INB,corner_radius=12);pf.pack(fill="x",padx=8,pady=4)
            ctk.CTkLabel(pf,text=plan,font=("Segoe UI",12),text_color=C.TX,wraplength=680,justify="left").pack(padx=18,pady=14)

        ctk.CTkLabel(sc,text="",height=8).pack()
        br=ctk.CTkFrame(sc,fg_color="transparent");br.pack(fill="x",padx=8,pady=14)
        ctk.CTkButton(br,text="New Exam",font=("Segoe UI",14,"bold"),fg_color=C.AC,hover_color=C.AC2,text_color=C.BG,height=48,corner_radius=12,width=200,command=self.on_new).pack(side="left",padx=8)
        ctk.CTkButton(br,text="Review Flashcards",font=("Segoe UI",13),fg_color=C.PURPLE,hover_color="#c090dd",text_color=C.BG,height=44,corner_radius=10,width=200,command=lambda:self.on_new()).pack(side="left",padx=8)


# ═══════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.st=St();self.st.prof=Prof.load()
        if self.st.prof.get("api_key"):self.st.key=self.st.prof["api_key"]
        if self.st.prof.get("provider"):self.st.prov=self.st.prof["provider"]
        if self.st.prof.get("kb_notes"):self.st.kbs.append(self.st.prof["kb_notes"])
        threading.Thread(target=get_logo,daemon=True).start()
        self._init()
        if self.st.key and self.st.prov:self.st.ready=True;self._config()
        else:self._setup()

    def _init(self):
        self.overrideredirect(True)
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        w,h=min(1420,int(sw*0.9)),min(920,int(sh*0.92))
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1050,700);self.configure(fg_color=C.BG)

    def _clr(self):
        for w in self.winfo_children():w.destroy()
    def _tb(self):
        TitleBar(self,self).pack(fill="x")
        ctk.CTkFrame(self,height=1,fg_color=C.BD,corner_radius=0).pack(fill="x")
    def _setup(self):self._clr();self._tb();Setup(self,self.st,self._config).pack(fill="both",expand=True)
    def _config(self):self._clr();self._tb();Config(self,self.st,self._gen,self._flashcards).pack(fill="both",expand=True)
    def _flashcards(self):self._clr();self._tb();FlashcardPage(self,self.st,self._config).pack(fill="both",expand=True)

    def _gen(self):
        self._clr();self._tb()
        self.ld=Loader(self,title="Generating Your Exam",sub=f"{self.st.n_qs} questions  Level {self.st.diff}/10")
        self.ld.pack(fill="both",expand=True)
        def gen():
            try:
                llm=LLM(self.st.prov,self.st.key);n=self.st.n_qs;all_qs=[]
                if n<=10:
                    self.after(0,lambda:self.ld.set(15,"Sending to AI..."))
                    result=llm.call(q_prompt(n,self.st.diff,self.st.prof,self.st.kb),QS)
                    self.after(0,lambda:self.ld.set(85,"Processing..."))
                    all_qs=result.get("questions",[])
                else:
                    bs=min(10,n);batches=[];rem=n;bid=1
                    while rem>0:
                        bn=min(bs,rem);p=q_prompt(bn,self.st.diff,self.st.prof,self.st.kb)+f"\nBatch {bid}. IDs from {n-rem+1}."
                        batches.append(p);rem-=bn;bid+=1
                    total=len(batches);done=[0];lock=threading.Lock()
                    self.after(0,lambda:self.ld.set(10,f"Generating {total} batches..."))
                    def run(idx,p):
                        r=llm.call(p,QS);qs=r.get("questions",[])
                        with lock:
                            done[0]+=1;pct=10+int(done[0]/total*75)
                            self.after(0,lambda p=pct,c=done[0]:self.ld.set(p,f"Batch {c}/{total} done"))
                        return qs
                    threads=[];rl=[None]*total
                    for i,p in enumerate(batches):
                        def w(idx=i,pr=p):
                            try:rl[idx]=run(idx,pr)
                            except:rl[idx]=[]
                        t=threading.Thread(target=w);t.start();threads.append(t);time.sleep(0.4)
                    for t in threads:t.join(timeout=120)
                    for bq in rl:
                        if bq:all_qs.extend(bq)
                if not all_qs:raise Exception("No questions")
                for i,q in enumerate(all_qs):q["id"]=i+1
                self.st.qs=all_qs[:n];self.st.ans={};self.st.idx=0
                self.st.on=True;self.st.t0=time.time();self.st.err=""
                self.after(0,lambda:self.ld.set(100,"Ready!"))
                time.sleep(0.4);self.after(0,self._exam)
            except Exception as e:
                self.st.err=str(e);self.after(0,lambda:self._error(str(e)))
        threading.Thread(target=gen,daemon=True).start()

    def _error(self,err):
        self._clr();self._tb()
        ef=ctk.CTkFrame(self,fg_color=C.BG);ef.place(relx=0.5,rely=0.5,anchor="center")
        ctk.CTkLabel(ef,text="Error",font=("Segoe UI",22,"bold"),text_color=C.ER).pack(pady=10)
        ctk.CTkLabel(ef,text=err,font=("Segoe UI",12),text_color=C.TX2,wraplength=500).pack(pady=8)
        ctk.CTkButton(ef,text="Retry",fg_color=C.AC,hover_color=C.AC2,height=42,corner_radius=10,command=self._gen).pack(pady=8)
        ctk.CTkButton(ef,text="Back",fg_color=C.ELEV,hover_color=C.HOVER,text_color=C.TX2,height=36,corner_radius=8,command=self._config).pack(pady=4)

    def _exam(self):
        self._clr();self._tb()
        self.ep=Exam(self,self.st,self._on_sub);self.ep.pack(fill="both",expand=True);self.ep.load()

    def _on_sub(self):
        self.st.done=True;elapsed=time.time()-self.st.t0
        self._clr();self._tb()
        self.ld=Loader(self,title="Analyzing Answers",sub="Generating explanations, mnemonics, flashcards and study plan")
        self.ld.pack(fill="both",expand=True)
        def analyze():
            try:
                self.after(0,lambda:self.ld.set(10,"Building analysis..."))
                prompt=a_prompt(self.st.qs,self.st.ans,self.st.prof)
                self.after(0,lambda:self.ld.set(25,"AI analyzing with mnemonic techniques..."))
                result=LLM(self.st.prov,self.st.key).call(prompt,AS,mt=12000)
                self.after(0,lambda:self.ld.set(75,"Creating flashcards..."))
                self.st.analysis=result
                self.st.prof=Prof.update(self.st.prof,result,self.st.qs,self.st.ans,elapsed)
                self.after(0,lambda:self.ld.set(95,"Preparing reveal..."))
                time.sleep(0.3);self.after(0,lambda:self.ld.set(100,"Done!"))
                time.sleep(0.3)
                tc=result.get("total_correct",0);gr=result.get("grade","?")
                self.after(0,lambda:self._reveal(tc,len(self.st.qs),gr))
            except Exception as e:
                self.st.err=str(e);self.after(0,lambda:self._error(str(e)))
        threading.Thread(target=analyze,daemon=True).start()

    def _reveal(self,c,t,g):self._clr();self._tb();Reveal(self,c,t,g,self._analysis).pack(fill="both",expand=True)
    def _analysis(self):self._clr();self._tb();p=Analysis(self,self.st,self._new);p.pack(fill="both",expand=True);p.show()
    def _new(self):self.st.reset();self._config()


if __name__=="__main__":
    print(f"\n  Kerala PSC Simulator v11.0\n  {'='*40}\n  Profile: {PROFILE}\n  Launching...\n")
    try:App().mainloop()
    except KeyboardInterrupt:print("\n  Bye!")
    except Exception as e:print(f"\n  Error: {e}");import traceback;traceback.print_exc();sys.exit(1)
