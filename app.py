# =========================================================
# FINAL SHORT POC – AI B2B AGRO NEGOTIATION (UPDATED)
# =========================================================

import streamlit as st
import re, os
from openai import OpenAI

# =========================================================
# CONFIG
# =========================================================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.set_page_config(layout="wide", page_title="AI Agro Negotiation POC")

# =========================================================
# CUSTOMER & PRODUCT DATA
# =========================================================
CUSTOMERS = {
    "Ramesh Traders": {"type":"Regular","risk":"Low","language":"Hindi-Hinglish","purchase_history":{"Urea":{"price":82,"qty":20}}},
    "Shiv Agro": {"type":"New","risk":"High","language":"Marathi-English","purchase_history":{}},
    "Patil Fertilizers":{"type":"Bulk","risk":"Medium","language":"Marathi-Hinglish","purchase_history":{"DAP":{"price":1280,"qty":50}}}
}

PRODUCTS = {
    "Urea":{"cost":75,"ideal":92,"floor":80,"stock":120,"condition":"Healthy Margin"},
    "DAP":{"cost":1180,"ideal":1350,"floor":1250,"stock":35,"condition":"Low Margin"},
    "Hybrid Seeds":{"cost":420,"ideal":600,"floor":500,"stock":200,"condition":"High Margin"}
}

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def extract_price(text):
    nums = re.findall(r"\d{2,5}", text)
    return int(nums[0]) if nums else None

def extract_qty(text):
    patterns = [r"(\d+)\s*(bag|bags|packet|packets|pkt|quintal|qtl)",
                r"(\d+)\s*(pahije|chahiye|havi|lene|ghya)"]
    for p in patterns:
        m = re.search(p, text.lower())
        if m: return int(m.group(1))
    return None

def psychology_tags(customer, product):
    tags=[]
    if customer["type"]=="Regular": tags.append("Relationship Leverage")
    if customer["risk"]=="High": tags.append("Risk Protection")
    if product["stock"]<50: tags.append("Scarcity Pressure")
    return tags

def negotiate(customer, product, product_name, offer, qty):
    history = customer.get("purchase_history", {}).get(product_name, {})
    last_price = history.get("price", product["ideal"])
    last_qty = history.get("qty", 0)
    target = max(last_price+2, product["floor"], product["cost"]+5)
    if qty and qty>last_qty: target-=1
    reasoning={"last_price":last_price,"last_qty":last_qty,"target_price":target,
               "floor":product["floor"],"cost":product["cost"],
               "expected_margin":target-product["cost"]}
    if offer is None: decision="ASK"
    elif offer>=target: decision="ACCEPT"
    elif offer>=product["floor"]: decision="COUNTER"
    else: decision="WALK_AWAY"
    return decision, reasoning

def bubble(text,sender):
    bg="#DCF8C6" if sender=="customer" else "#FFFFFF"
    align="margin-left:auto" if sender=="customer" else ""
    st.markdown(f"<div style='background:{bg};padding:10px;border-radius:8px;margin:6px 0;width:70%;{align};border:1px solid #ccc'>{text}</div>",unsafe_allow_html=True)

# =========================================================
# AI MEMORY FOR CONTEXT
# =========================================================
if "ai_known" not in st.session_state: st.session_state.ai_known={}
def update_ai_known(customer_key, product_name, quantity=None, offer=None):
    if customer_key not in st.session_state.ai_known: st.session_state.ai_known[customer_key]={}
    if product_name not in st.session_state.ai_known[customer_key]: st.session_state.ai_known[customer_key][product_name]={}
    if quantity is not None: st.session_state.ai_known[customer_key][product_name]["quantity"]=quantity
    if offer is not None: st.session_state.ai_known[customer_key][product_name]["offer"]=offer

# =========================================================
# AI REPLY FUNCTION USING PROPER CHAT ROLES
# =========================================================
def ai_reply(ctx, chat, customer_key, product_name, qty, offer):
    # Update AI memory
    update_ai_known(customer_key, product_name, quantity=qty, offer=offer)

    # Build messages list for Chat API with correct roles
    messages=[]
    for sender,msg in chat[-10:]:
        if sender=="customer": messages.append({"role":"user","content":msg})
        else: messages.append({"role":"assistant","content":msg})

    # Add system prompt with negotiation context
    messages.insert(0, {"role":"system","content":f"""
You are an Indian B2B agro sales executive.
You negotiate with customers in Hindi, English, Marathi, Hinglish mix.
Product: {product_name}
Customer Type: {ctx['customer']['type']}
Last Price: ₹{ctx['reasoning']['last_price']}
Target Price: ₹{ctx['reasoning']['target_price']}
Floor: ₹{ctx['reasoning']['floor']}
Psychology Tags: {', '.join(ctx['psychology'])}
Use negotiation logic, avoid repeating info AI already knows.
Respond naturally and continue the conversation smoothly.
"""})

    # Generate AI response
    res=client.chat.completions.create(model="gpt-4o-mini",messages=messages,temperature=0.6)
    return res.choices[0].message.content

# =========================================================
# UI SETUP
# =========================================================
st.title("🤖 AI B2B Agro Negotiation – Final POC")
c1,c2=st.columns(2)
with c1: customer_key=st.selectbox("Customer",CUSTOMERS.keys())
with c2: product_name=st.selectbox("Product",PRODUCTS.keys())
customer=CUSTOMERS[customer_key]
product=PRODUCTS[product_name]

# Dashboard: Customers & Products
st.subheader("📊 Dashboard Overview")
st.dataframe([{"Customer":k,"Type":v["type"],"Risk":v["risk"],"Language":v["language"],"Products":", ".join(v["purchase_history"].keys())} for k,v in CUSTOMERS.items()])
st.dataframe([{"Product":k,"Cost":v["cost"],"Ideal":v["ideal"],"Floor":v["floor"],"Stock":v["stock"],"Condition":v["condition"]} for k,v in PRODUCTS.items()])

# Chat Tabs
tabs=st.tabs(["🌐 Web Chat","💬 WhatsApp","📞 Telecalling"])
if "web_chat" not in st.session_state: st.session_state.web_chat=[("ai","Namaste 🙏 rate aur quantity batayiye.")]
if "wa_chat" not in st.session_state: st.session_state.wa_chat=[("ai","Hello 👋 WhatsApp pe deal finalize karte hain.")]
if "call_chat" not in st.session_state: st.session_state.call_chat=[("ai","📞 Namaskar, main Agro AI bol raha hoon.")]

def chat_ui(chat_key,label):
    chat=st.session_state[chat_key]
    for s,m in chat: bubble(m,s)
    msg=st.text_input(f"Customer message ({label})",key=f"input_{chat_key}")
    if st.button("Send",key=f"send_{chat_key}"):
        offer=extract_price(msg)
        qty=extract_qty(msg)
        decision,reasoning=negotiate(customer,product,product_name,offer,qty)
        psych=psychology_tags(customer,product)
        ctx={"customer":customer,"product":product,"product_name":product_name,"reasoning":reasoning,"psychology":psych}
        reply=ai_reply(ctx,chat,customer_key,product_name,qty,offer)
        chat.append(("customer",msg))
        chat.append(("ai",reply))
        st.session_state.last_ctx=ctx

with tabs[0]: chat_ui("web_chat","Web")
with tabs[1]: chat_ui("wa_chat","WhatsApp")
with tabs[2]: chat_ui("call_chat","Telecalling")

# AI Internal Logic
st.divider()
st.subheader("🧠 AI Internal Logic")
if "last_ctx" in st.session_state:
    r=st.session_state.last_ctx["reasoning"]
    st.markdown(f"""
- Last Price: ₹{r['last_price']}
- Target Price: ₹{r['target_price']}
- Floor: ₹{r['floor']}
- Cost: ₹{r['cost']}
- Expected Margin: ₹{r['expected_margin']}
- Psychology Tags: {", ".join(st.session_state.last_ctx['psychology'])}
""")

# Show all chat histories for stakeholders
st.subheader("💬 Chat Histories")
for key,label in [("web_chat","Web"),("wa_chat","WhatsApp"),("call_chat","Telecalling")]:
    st.markdown(f"**{label} Chat**")
    for s,m in st.session_state[key]: bubble(m,s)

