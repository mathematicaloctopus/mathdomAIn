import os, requests
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr,standard_transformations,implicit_multiplication_application
import gradio as gr

GROQ_API_KEY=os.environ.get("GROQ_API_KEY","keyyy")
GROQ_MODEL="llama-3.3-70b-versatile"
GROQ_URL="https://api.groq.com/openai/v1/chat/completions"


_T = standard_transformations+(implicit_multiplication_application,)

x=sp.Symbol("x");y=sp.Symbol("y");z=sp.Symbol("z")
a=sp.Symbol("a");b=sp.Symbol("b");c=sp.Symbol("c")
# dont even use half these but whatever
m=sp.Symbol("m");n=sp.Symbol("n");k=sp.Symbol("k");t=sp.Symbol("t")


def _p(s):
    # fix the stupid caret thing
    return parse_expr(s.replace("^","**"),transformations=_T)


def _ask_groq(usermsg,sysmsg):
    if not GROQ_API_KEY or GROQ_API_KEY=="keyyy":
        return "forgot the API key"
    try:
        r=requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
            json={"model":GROQ_MODEL,"temperature":0.4,
                  "messages":[{"role":"system","content":sysmsg},{"role":"user","content":usermsg}]},
            timeout=60)
        
    
    except Exception as err:
        return f"api broke lmao: {err}"


def _compute(ttype,expr,vstr,xtra):
    
    vsym = sp.Symbol(vstr.strip()) if vstr.strip() else x

    try:
        if ttype=="Solve Equation":
            if "==" in expr:   l,r=expr.split("==")
            elif "=" in expr:  l,r=expr.split("=")
            else:              l,r=expr,"0"
            eq=sp.Eq(_p(l),_p(r))

            sols=sp.solveset(eq,vsym,domain=sp.S.Reals)
            return str(sols), f"eq: {eq}\nsolving {vsym}\ngot: {sols}"

        elif ttype=="Simplify":


            e=_p(expr); s=sp.simplify(e)
            return str(s),f"input: {e}\nsimplified: {s}"

        elif ttype=="Expand":
            e=_p(expr); ex=sp.expand(e)
            return str(ex),f"input: {e}\nexpanded: {ex}"

        elif ttype=="Factor":
            e=_p(expr); f2=sp.factor(e)
            return str(f2),f"input: {e}\nfactored: {f2}"

        elif ttype=="Differentiate":
            e=_p(expr)

            dd=sp.simplify(sp.diff(e,vsym))
            return str(dd),(
                f"f({vsym})={e}\n"
                f"raw deriv={sp.diff(e,vsym)}\n"
                f"simplified={dd}"
            )

        elif ttype=="Integrate":
            e=_p(expr)
            if xtra.strip():
                lo,hi=xtra.split(",")
                res=sp.integrate(e,(vsym,_p(lo),_p(hi)))
                wrk=f"f({vsym})={e}\ndefinite integral [{lo},{hi}] = {res}"
            else:
                res=sp.integrate(e,vsym)
                wrk=f"f({vsym})={e}\nantideriv={res} + C"
            return str(res),wrk

        elif ttype=="Quadratic Formula":
            raw=expr
            if "=" in raw:


                ll,rr=raw.split("=")
                e=_p(ll)-_p(rr)
            else:
                e=_p(raw)
            poly=sp.Poly(e,vsym)
            cfs=poly.all_coeffs()
            while len(cfs)<3: cfs.insert(0,0)
            av,bv,cv=cfs[-3],cfs[-2],cfs[-1]
            disc=bv**2-4*av*cv
            solns=sp.solve(sp.Eq(e,0),vsym)
            wrk=(
                f"{av}{vsym}^2 + {bv}{vsym} + {cv} = 0\n"
                f"a={av} b={bv} c={cv}\n"
                f"discriminant={disc}\n"
                f"solutions={solns}"
            )
            return str(solns),wrk

        elif ttype=="Limit":
            e=_p(expr)
            pt=_p(xtra) if xtra.strip() else 0
            lv=sp.limit(e,vsym,pt)
            return str(lv),f"f({vsym})={e}\nlim as {vsym}->{pt} = {lv}"

        elif ttype=="Evaluate Numerically":
            e=_p(expr); val=e.evalf()
            return str(val),f"{e} ≈ {val}"

        else:
            return "???","unknown task"

    except Exception as boom:
        return f"Error: {boom}",f"sympy died: {boom}"



def go(ttype,expr,vstr,xtra,grade):
    if not expr.strip():
        return "nothing to solve lol", ""

    ans,steps=_compute(ttype,expr,vstr,xtra)

    if ans.startswith("Error") or ans=="???":
        return ans,"math part blew up, cant explain it. double check what u typed"

    grade_=grade.strip() or "10"

    explanation=_ask_groq(
        f"Task: {ttype}\nProblem: {expr}\n"
        f"Variable: {vstr.strip() or 'x'}\n"
        f"Grade level: {grade_}\n"
        f"Sympy work (already correct dont second guess it):\n{steps}\n\n"
        f"Explain for grade {grade_} student. Final answer is: {ans}",

        "You are a friendly high-school math tutor. "
        "Sympy already calculated the correct answer, your ONLY job is explaining how to get there. "
        "Do not recalculate or verify. Explain step by step, then state the final answer clearly."
    )
    return ans, explanation


_tasks=[
    "Solve Equation","Quadratic Formula","Simplify",
    "Expand","Factor","Differentiate","Integrate","Limit","Evaluate Numerically"
]

_examples=[
    ["Solve Equation","2*x + 3 == 11","x","","8"],
    ["Quadratic Formula","x^2 - 5*x + 6 = 0","x","","10"],
    ["Differentiate","x^3 + 2*x^2 - 5*x","x","","11"],
    ["Integrate","3*x^2 + 2*x","x","","12"],
    ["Integrate","x^2","x","0,2","12"],
    ["Factor","x^2 - 9","x","","9"],
    ["Limit","(x^2 - 1)/(x - 1)","x","1","12"],
]

with gr.Blocks(title="math domAIn") as demo:
    gr.Markdown("#correct math explanations hero")
    with gr.Row():
        with gr.Column():
            tt   = gr.Dropdown(_tasks,label="what do u want",value="Solve Equation")
            eq   = gr.Textbox(label="equation",placeholder="x^2 - 5*x + 6 = 0")
            vv   = gr.Textbox(label="variable",value="x")
            xt   = gr.Textbox(label="extra (limits: point, integrals: lo,hi)",placeholder="e.g. 1  or  0,5")
            grd  = gr.Textbox(label="grade level",value="10")
            btn  = gr.Button("go")
        with gr.Column():
            out1 = gr.Textbox(label="answer")
            out2 = gr.Textbox(label="explanation",lines=15)

    gr.Examples(examples=_examples,inputs=[tt,eq,vv,xt,grd])
    btn.click(go,inputs=[tt,eq,vv,xt,grd],outputs=[out1,out2])

demo.launch(share=True)

#ive given up on latex