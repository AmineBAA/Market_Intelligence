# -*- coding: utf-8 -*-
"""
market_intelligence.py — Market Intelligence (Saham Bank)

Veille concurrentielle bancaire à partir d'éléments CURÉS MANUELLEMENT :
  • 3 rubriques alimentées par des fichiers de liens (.txt) :
      - Actualités        → Link_Actualités.txt
      - Partenariats      → Link_Partenariats.txt
      - Réglementations   → Link_Réglementation.txt
    Pour chaque lien, on récupère les métadonnées Open Graph
    (titre, image, description) → carte d'aperçu propre, comme un partage social.
  • 1 rubrique "Campagnes" → affiche les visuels d'ads des concurrents
    déposés dans le dossier Campagnes/ (le préfixe du nom de fichier sert de marque).

Aucun NLP, aucun filtre : tout est déjà sélectionné par l'analyste.
Design vert/orange Saham Bank conservé.
"""

import os
import re
import glob
import html
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

APP_VERSION = "2026-06-25-v10"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMPAGNES_DIR = os.path.join(BASE_DIR, "Campagnes")

# Les 4 rubriques. Pour les rubriques "liens", on indique le fichier source.
RUBRIQUES = {
    "Actualités": {"type": "links", "file": "Link_Actualités.txt", "icon": "📰"},
    "Partenariats": {"type": "links", "file": "Link_Partenariats.txt", "icon": "🤝"},
    "Réglementations": {"type": "links", "file": "Link_Réglementation.txt", "icon": "⚖️"},
    "Campagnes": {"type": "campaigns", "icon": "📣"},
}

# Détection de la marque concurrente à partir du nom de fichier de l'ad
# (ex: "CIH_ad 1.png" → "CIH", "ATTIJARI_ad 1.png" → "ATTIJARI")
BRAND_LABELS = {
    "cih": "CIH Bank",
    "attijari": "Attijariwafa bank",
    "cfg": "CFG Bank",
    "bcp": "Banque Populaire",
    "boa": "Bank Of Africa",
    "bmci": "BMCI",
    "cdm": "Crédit du Maroc",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# --------------------------------------------------------------------------
# Récupération des métadonnées d'un lien (Open Graph)
# --------------------------------------------------------------------------

def read_links(filename: str) -> list[str]:
    """Lit un fichier de liens (un par ligne, ignore les lignes vides)."""
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip().startswith("http")]


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_link_preview(url: str) -> dict:
    """Récupère titre / image / description via les balises Open Graph."""
    preview = {
        "url": url,
        "title": url,
        "image": None,
        "description": "",
        "site": urlparse(url).netloc.replace("www.", ""),
        "error": None,
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def meta(prop):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            return tag["content"].strip() if tag and tag.get("content") else None

        preview["title"] = html.unescape(
            meta("og:title") or (soup.title.string.strip() if soup.title else url)
        )
        preview["image"] = meta("og:image") or meta("twitter:image")
        preview["description"] = html.unescape(
            meta("og:description") or meta("description") or ""
        )
        # Corrige les URLs d'image relatives ou avec espaces
        if preview["image"]:
            preview["image"] = preview["image"].replace(" ", "%20")
            if preview["image"].startswith("/"):
                base = "{0.scheme}://{0.netloc}".format(urlparse(url))
                preview["image"] = base + preview["image"]
    except Exception as exc:
        preview["error"] = str(exc)
    return preview


@st.cache_data(ttl=24 * 3600, show_spinner="Chargement des aperçus...")
def load_rubrique_links(filename: str) -> list[dict]:
    return [fetch_link_preview(url) for url in read_links(filename)]


# --------------------------------------------------------------------------
# Campagnes (visuels d'ads)
# --------------------------------------------------------------------------

def detect_brand(filename: str) -> str:
    name = os.path.basename(filename).lower()
    prefix = re.split(r"[_\s]", name)[0]
    return BRAND_LABELS.get(prefix, prefix.upper())


def load_campaigns() -> list[dict]:
    """Liste les visuels d'ads, groupés par marque concurrente."""
    if not os.path.isdir(CAMPAGNES_DIR):
        return []
    files = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        files.extend(glob.glob(os.path.join(CAMPAGNES_DIR, ext)))
    return [{"path": f, "brand": detect_brand(f), "name": os.path.basename(f)}
            for f in sorted(files)]


# --------------------------------------------------------------------------
# Interface Streamlit — design vert/orange Saham Bank
# --------------------------------------------------------------------------

st.set_page_config(page_title="Saham Bank – Market Intelligence", page_icon="🏦", layout="wide")

CUSTOM_CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.5rem; max-width: 100%;}
body, .stApp {background-color: #122420; color: #FFFFFF;}
section[data-testid="stSidebar"] {background-color: #1A332E; border-right: 1px solid #2D544E;}
section[data-testid="stSidebar"] button {
    width:100%;text-align:left;background:transparent;color:#A0B2AF;
    border:none;border-radius:6px;padding:12px 15px;font-weight:500;font-size:15px;
}
section[data-testid="stSidebar"] button:hover {background-color:#D24B2C;color:#fff;}
section[data-testid="stSidebar"] button:focus {background-color:#D24B2C;color:#fff;}
.card {background-color:#24443F;border-radius:10px;padding:0;border:1px solid #2D544E;
       margin-bottom:20px;overflow:hidden;}
.card-img {width:100%;height:200px;object-fit:cover;display:block;background:#1A332E;}
.card-body {padding:18px;}
.badge {background-color:#122420;color:#D24B2C;padding:3px 10px;border-radius:4px;
        font-weight:bold;border:1px solid #D24B2C;font-size:12px;}
.card-title {font-size:17px;font-weight:600;color:#FFFFFF;margin:12px 0 8px;line-height:1.35;}
.card-desc {font-size:14px;color:#A0B2AF;line-height:1.5;}
.card-meta {font-size:12px;color:#6E8783;margin-top:12px;display:flex;
            justify-content:space-between;align-items:center;}
.card-link {color:#1D9E75;text-decoration:none;font-size:13px;font-weight:600;}
.section-head {font-size:24px;font-weight:600;margin-bottom:6px;}
.section-sub {color:#A0B2AF;font-size:14px;margin-bottom:24px;}
.brand-head {font-size:18px;font-weight:600;color:#D24B2C;margin:20px 0 12px;
             border-left:4px solid #D24B2C;padding-left:12px;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Sidebar ---
if "rubrique" not in st.session_state:
    st.session_state.rubrique = "Actualités"

logo_path = os.path.join(BASE_DIR, "logo_bank.png")
logo_files = [logo_path] if os.path.exists(logo_path) else glob.glob(os.path.join(BASE_DIR, "logo*"))
if logo_files:
    st.sidebar.image(logo_files[0], width='stretch')
else:
    st.sidebar.markdown(
        "<div style='text-align:center;padding:15px;font-weight:bold;font-size:18px;"
        "border-bottom:1px solid #2D544E;margin-bottom:10px;'>SAHAM BANK</div>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    "<p style='color:#FFF;font-weight:600;font-size:13px;text-transform:uppercase;"
    "letter-spacing:1px;margin:10px 0;'>Saham Market Intelligence</p>",
    unsafe_allow_html=True,
)

for name, conf in RUBRIQUES.items():
    if st.sidebar.button(f"{conf['icon']}  {name}", key=f"nav_{name}"):
        st.session_state.rubrique = name

st.sidebar.divider()
st.sidebar.caption(f"Version {APP_VERSION}")
if st.sidebar.button("🔄 Actualiser les aperçus"):
    st.cache_data.clear()
    st.rerun()

# --- Contenu principal ---
rubrique = st.session_state.rubrique
conf = RUBRIQUES[rubrique]

SUBTITLES = {
    "Actualités": "Dernières actualités produits et services des banques marocaines.",
    "Partenariats": "Accords et alliances stratégiques du secteur bancaire.",
    "Réglementations": "Décisions et communications de Bank Al-Maghrib et des régulateurs.",
    "Campagnes": "Visuels publicitaires des concurrents sur les réseaux sociaux.",
}

st.markdown(f"<div class='section-head'>{conf['icon']} {rubrique}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='section-sub'>{SUBTITLES.get(rubrique, '')}</div>", unsafe_allow_html=True)


def render_link_card(preview: dict):
    img_html = (
        f"<img src='{preview['image']}' class='card-img' alt=''>"
        if preview.get("image") else
        "<div class='card-img' style='display:flex;align-items:center;"
        "justify-content:center;color:#6E8783;'>Aperçu indisponible</div>"
    )
    desc = preview.get("description", "")
    desc = (desc[:180] + "…") if len(desc) > 180 else desc
    st.markdown(
        f"""<div class='card'>
            {img_html}
            <div class='card-body'>
                <span class='badge'>{preview['site']}</span>
                <div class='card-title'>{preview['title']}</div>
                <div class='card-desc'>{desc}</div>
                <div class='card-meta'>
                    <a href='{preview['url']}' target='_blank' class='card-link'>Lire l'article →</a>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ----- Rubriques de type "liens" -----
if conf["type"] == "links":
    previews = load_rubrique_links(conf["file"])
    if not previews:
        st.info(
            f"Aucun lien dans **{conf['file']}**. Ajoute des URLs (une par ligne) "
            f"dans ce fichier pour alimenter la rubrique."
        )
    else:
        cols = st.columns(3)
        for i, preview in enumerate(previews):
            with cols[i % 3]:
                render_link_card(preview)
        # Liens en erreur signalés discrètement
        errors = [p for p in previews if p.get("error")]
        if errors:
            with st.expander(f"⚠️ {len(errors)} lien(s) n'ont pas pu être chargés"):
                for p in errors:
                    st.caption(f"{p['url']} — {p['error'][:80]}")

# ----- Rubrique "Campagnes" -----
elif conf["type"] == "campaigns":
    campaigns = load_campaigns()
    if not campaigns:
        st.info(
            "Aucun visuel dans le dossier **Campagnes/**. Dépose des images d'ads "
            "nommées `MARQUE_ad N.png` (ex: `CIH_ad 1.png`)."
        )
    else:
        # Groupement par marque concurrente
        brands = {}
        for c in campaigns:
            brands.setdefault(c["brand"], []).append(c)
        for brand, ads in brands.items():
            st.markdown(f"<div class='brand-head'>{brand} · {len(ads)} visuel(s)</div>",
                        unsafe_allow_html=True)
            cols = st.columns(3)
            for i, ad in enumerate(ads):
                with cols[i % 3]:
                    st.image(ad["path"], width='stretch')
