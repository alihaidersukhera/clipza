"""ClipReward — clipping campaigns with pay-per-view rewards (by JONNY PRODUCTIONS).

Brands post clipping campaigns with a rate per 1,000 views.
Clippers cut clips, post them, submit the links, and earn per verified views.
"""
import streamlit as st

import rewards_core as core

core.init_db()

st.set_page_config(page_title="ClipReward — Content Rewards", page_icon="💰", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  .stApp { background: radial-gradient(1200px 600px at 20% -10%, #1c1706 0%, #0b0b0f 55%) fixed; }
  * { font-family: 'Inter', sans-serif !important; }

  .cr-hero {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #14141b 0%, #241c05 60%, #2e2404 100%);
    border: 1px solid #3a3208; border-radius: 22px;
    padding: 32px 34px; margin-bottom: 18px;
    box-shadow: 0 12px 40px rgba(245,197,24,0.07);
  }
  .cr-hero h1 {
    margin: 0; font-size: 2.6rem; font-weight: 800; letter-spacing: -1px;
    background: linear-gradient(92deg, #ffe08a, #f5c518 45%, #fff6cf 80%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .cr-hero p { color: #cfcfda; margin: 10px 0 0 0; font-size: 1.03rem; line-height: 1.55; }
  .cr-hero .cr-tag {
    display: inline-block; margin-bottom: 10px;
    background: rgba(245,197,24,0.12); color: #ffd94d; border: 1px solid rgba(245,197,24,0.35);
    font-size: 0.72rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
    border-radius: 999px; padding: 5px 14px;
  }

  .cr-card {
    background: linear-gradient(180deg, #16161d, #131318);
    border: 1px solid #26262f; border-radius: 18px;
    padding: 20px 22px; margin-bottom: 16px;
    transition: border-color .2s, transform .2s;
  }
  .cr-card:hover { border-color: #4a4210; transform: translateY(-1px); }
  .cr-rate { font-size: 1.7rem; font-weight: 800; color: #ffd94d; }
  .cr-meta { color: #9a9aa5; font-size: 0.88rem; }
  .cr-rules { background: #101014; border-radius: 12px; padding: 12px 16px;
    color: #c9c9d4; font-size: 0.88rem; white-space: pre-line; margin-top: 10px; }
  .cr-status { display: inline-block; font-weight: 700; border-radius: 999px;
    padding: 3px 13px; font-size: 0.8rem; }
  .cr-status.live { background: rgba(46,204,113,0.14); color: #5df08f; border: 1px solid rgba(46,204,113,0.45); }
  .cr-status.paused { background: rgba(255,193,7,0.12); color: #ffd94d; border: 1px solid rgba(255,193,7,0.4); }
  .cr-status.ended { background: rgba(150,150,160,0.12); color: #a9a9b8; border: 1px solid rgba(150,150,160,0.35); }
  .cr-status.pending { background: rgba(93,156,255,0.14); color: #8db8ff; border: 1px solid rgba(93,156,255,0.4); }
  .cr-status.approved { background: rgba(46,204,113,0.14); color: #5df08f; border: 1px solid rgba(46,204,113,0.45); }
  .cr-status.rejected { background: rgba(255,99,99,0.12); color: #ff8f8f; border: 1px solid rgba(255,99,99,0.4); }
  .cr-earn { font-size: 1.4rem; font-weight: 800; color: #5df08f; }

  .stButton > button, .stDownloadButton > button { border-radius: 12px; font-weight: 700; transition: transform .15s; }
  .stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ffe08a, #f5c518); color: #161105; border: none;
    box-shadow: 0 6px 22px rgba(245,197,24,0.28);
  }
  .cr-footer { text-align: center; color: #6d6d78; font-size: 0.8rem; margin: 30px 0 10px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cr-hero">
  <span class="cr-tag">Pay-per-view clipping campaigns</span>
  <h1>💰 ClipReward</h1>
  <p><b>Brands:</b> post a clipping campaign with a rate per 1,000 views.
  <b>Clippers:</b> cut clips, post them on TikTok / Shorts / Reels, submit the link —
  and earn for every verified view.</p>
  <a href="https://clipza.streamlit.app/" target="_blank"
     style="display:inline-block; margin-top:14px; background:linear-gradient(135deg,#ffe08a,#f5c518);
     color:#161105; font-weight:800; border-radius:10px; padding:9px 20px; text-decoration:none;">
     ✂️ Need clips? Cut them free with Clipza →</a>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar --
with st.sidebar:
    st.markdown("### 🧭 Menu")
    role = st.radio("I am a…", ["🔍 Browse campaigns", "🏢 Brand", "✂️ Clipper",
                                "🏆 Leaderboard"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<span class='cr-meta'>ClipReward by <b>JONNY PRODUCTIONS</b><br>"
                "Views are verified by the brand.</span>", unsafe_allow_html=True)


def status_pill(status):
    return f"<span class='cr-status {status}'>{status.upper()}</span>"


# ------------------------------------------------------------------ browse ---
if role.startswith("🔍"):
    st.subheader("Live campaigns")
    campaigns = core.list_campaigns()
    if not campaigns:
        st.info("No campaigns yet. Brands can create one from the 🏢 Brand tab. "
                "Or load sample data:")
        if st.button("Load demo data"):
            core.load_demo_data()
            st.rerun()
    for c in campaigns:
        stats = core.campaign_stats(c["id"])
        cap = f"{c['cap_per_clip']:,}" if c["cap_per_clip"] else "No cap"
        st.markdown(f"""
        <div class="cr-card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div><b style="font-size:1.15rem;">{c['name']}</b><br>
            <span class="cr-meta">by {c['brand_name']}</span></div>
            <div style="text-align:right;"><div class="cr-rate">${c['rate_per_1k']:.2f}</div>
            <span class="cr-meta">per 1,000 views</span></div>
          </div>
          <div style="margin-top:10px;">
            <span class="cr-meta">Min views: <b>{c['min_views']:,}</b></span> &nbsp;•&nbsp;
            <span class="cr-meta">Cap per clip: <b>{cap}</b></span> &nbsp;•&nbsp;
            <span class="cr-meta">Budget left: <b>${stats['remaining'] if stats['remaining'] is not None else '—'}</b></span>
            &nbsp; {status_pill(c['status'])}
          </div>
          {f"<div class='cr-rules'>{c['rules']}</div>" if c['rules'] else ""}
          {f"<div class='cr-meta' style='margin-top:8px;'>📎 Source material: <a href='{c['materials_url']}'>{c['materials_url']}</a></div>" if c['materials_url'] else ""}
          <div class="cr-meta" style="margin-top:8px;">👁 {stats['total_views']:,} verified views •
          {stats['submissions']} submissions • ${stats['spent']:.2f} paid out</div>
          <a href="https://clipza.streamlit.app/" target="_blank"
             style="display:inline-block; margin-top:10px; border:1px solid rgba(245,197,24,0.5);
             color:#ffd94d; font-weight:700; border-radius:9px; padding:6px 14px;
             text-decoration:none; font-size:0.85rem;">✂️ Cut clips for this campaign with Clipza →</a>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------- brand ---
elif role.startswith("🏢"):
    tab1, tab2 = st.tabs(["➕ New campaign", "📥 Review submissions"])
    with tab1:
        st.subheader("Create a campaign")
        with st.form("new_campaign"):
            name = st.text_input("Campaign name", placeholder="e.g. Summer Sale Clips")
            brand = st.text_input("Brand / company name")
            c1, c2 = st.columns(2)
            with c1:
                rate = st.number_input("Rate per 1,000 views ($)", 0.1, 100.0, 1.0, 0.1)
                min_views = st.number_input("Minimum views to count", 0, 1000000, 1000, 100)
            with c2:
                cap = st.number_input("Cap per clip (views, 0 = no cap)", 0, 100000000, 0, 1000)
                budget = st.number_input("Total budget ($, 0 = unlimited)", 0.0, 1000000.0, 0.0, 10.0)
            rules = st.text_area("Campaign rules (one per line)",
                                 placeholder="1. Clip must come from the source video…\n2. Minimum 8 seconds…\n3. No botted views…")
            materials = st.text_input("Source video / materials link (optional)")
            if st.form_submit_button("🚀 Launch campaign", type="primary"):
                if not name or not brand:
                    st.warning("Campaign name and brand name are required.")
                else:
                    cid = core.create_campaign(name, brand, rate, min_views, cap,
                                               budget, rules, materials)
                    st.success(f"Campaign **#{cid} — {name}** is live! "
                               f"Clippers can now submit clips.")
    with tab2:
        st.subheader("Review submissions")
        campaigns = core.list_campaigns()
        if not campaigns:
            st.info("No campaigns yet.")
        else:
            cmap = {f"#{c['id']} — {c['name']}": c["id"] for c in campaigns}
            sel = st.selectbox("Campaign", list(cmap.keys()))
            cid = cmap[sel]
            camp = core.get_campaign(cid)
            stats = core.campaign_stats(cid)
            st.markdown(f"**{stats['pending']}** pending • **{stats['approved']}** approved • "
                        f"${stats['spent']:.2f} paid out" +
                        (f" • ${stats['remaining']:.2f} budget left"
                         if stats["remaining"] is not None else ""))
            pending = core.list_submissions(campaign_id=cid, status="pending")
            if not pending:
                st.info("No pending submissions for this campaign.")
            for s in pending:
                with st.expander(f"#{s['id']} — {s['clipper_name']} • "
                                 f"{s['platform']} • {s['reported_views']:,} reported views"):
                    st.markdown(f"🔗 [Open post]({s['post_url']})")
                    st.markdown(f"<span class='cr-meta'>Clipper reported "
                                f"{s['reported_views']:,} views. Enter the views you "
                                f"verified by opening the link — payment = "
                                f"verified views ÷ 1,000 × ${camp['rate_per_1k']:.2f}, "
                                f"minimum {camp['min_views']:,} views to count.</span>",
                                unsafe_allow_html=True)
                    v1, v2 = st.columns(2)
                    with v1:
                        vv = st.number_input("Verified views", 0, 1000000000,
                                             s["reported_views"], 100,
                                             key=f"vv_{s['id']}")
                    with v2:
                        st.write("")
                        st.write("")
                        ok = st.button("✅ Approve", key=f"ok_{s['id']}")
                        no = st.button("❌ Reject", key=f"no_{s['id']}")
                    if ok:
                        earn = core.review_submission(s["id"], vv, approve=True)
                        st.success(f"Approved — clipper earns **${earn:.2f}**.")
                        st.rerun()
                    if no:
                        core.review_submission(s["id"], vv, approve=False)
                        st.warning("Rejected.")
                        st.rerun()
            done = [s for s in core.list_submissions(campaign_id=cid)
                    if s["status"] != "pending"]
            if done:
                st.markdown("**Decided submissions**")
                for s in done:
                    st.markdown(f"{status_pill(s['status'])} #{s['id']} — "
                                f"{s['clipper_name']} • {s['verified_views']:,} views • "
                                f"**${s['earnings']:.2f}**")
            c1b, _ = st.columns([1, 4])
            with c1b:
                if camp["status"] == "live" and st.button("⏸ Pause campaign"):
                    core.set_campaign_status(cid, "paused")
                    st.rerun()
                if camp["status"] == "paused" and st.button("▶ Resume campaign"):
                    core.set_campaign_status(cid, "live")
                    st.rerun()
                if camp["status"] != "ended" and st.button("⏹ End campaign"):
                    core.set_campaign_status(cid, "ended")
                    st.rerun()

# ----------------------------------------------------------------- clipper ---
elif role.startswith("✂️"):
    tab1, tab2 = st.tabs(["📤 Submit a clip", "💵 My earnings"])
    with tab1:
        st.subheader("Submit your clip")
        campaigns = core.list_campaigns(status="live")
        if not campaigns:
            st.info("No live campaigns right now. Check back soon!")
        else:
            cmap = {f"#{c['id']} — {c['name']} (${c['rate_per_1k']:.2f}/1k views)": c
                    for c in campaigns}
            sel = st.selectbox("Campaign", list(cmap.keys()))
            c = cmap[sel]
            st.markdown(f"<span class='cr-meta'>Min {c['min_views']:,} views to count • "
                        f"Brand: {c['brand_name']}</span>", unsafe_allow_html=True)
            st.markdown("<span class='cr-meta'>✂️ No clip yet? "
                        "<a href='https://clipza.streamlit.app/' target='_blank'>"
                        "Cut one free with Clipza</a>, post it, then submit the link below.</span>",
                        unsafe_allow_html=True)
            with st.form("submit"):
                clipper = st.text_input("Your clipper name")
                platform = st.selectbox("Platform", ["TikTok", "YouTube Shorts",
                                                     "Instagram Reels"])
                url = st.text_input("Link to your posted clip")
                views = st.number_input("Current views on the post", 0,
                                        1000000000, 0, 100)
                if st.form_submit_button("📤 Submit for review", type="primary"):
                    if not clipper or not url:
                        st.warning("Clipper name and post link are required.")
                    else:
                        sid = core.submit_clip(c["id"], clipper, platform, url, views)
                        st.success(f"Submitted as **#{sid}**! The brand will verify "
                                   f"your views — payment lands after approval.")
    with tab2:
        st.subheader("My earnings")
        name = st.text_input("Enter your clipper name")
        if name:
            subs = [s for s in core.list_submissions()
                    if s["clipper_name"].strip().lower() == name.strip().lower()]
            if not subs:
                st.info("No submissions found for this name yet.")
            else:
                total = round(sum(s["earnings"] for s in subs), 2)
                st.markdown(f"<div class='cr-card'>Total earned: "
                            f"<span class='cr-earn'>${total:.2f}</span></div>",
                            unsafe_allow_html=True)
                for s in subs:
                    camp = core.get_campaign(s["campaign_id"]) or {}
                    st.markdown(f"{status_pill(s['status'])} "
                                f"#{s['id']} — {camp.get('name', '?')} • "
                                f"{s['platform']} • {s['verified_views']:,} verified views • "
                                f"**${s['earnings']:.2f}**")

# -------------------------------------------------------------- leaderboard --
else:
    st.subheader("🏆 Top clippers")
    board = core.leaderboard()
    if not board:
        st.info("No approved submissions yet — the leaderboard is empty.")
    else:
        for i, row in enumerate(board, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            st.markdown(f"""
            <div class="cr-card">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div><b style="font-size:1.1rem;">{medal} {row['clipper_name']}</b><br>
                <span class="cr-meta">{row['clips']} approved clips •
                {row['views']:,} verified views</span></div>
                <div class="cr-earn">${row['earnings']:.2f}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<div class='cr-footer'>💰 ClipReward by <b>JONNY PRODUCTIONS</b> • "
            "Demo build — views are verified by brands manually</div>",
            unsafe_allow_html=True)
