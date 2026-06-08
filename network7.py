import streamlit as st
import pandas as pd
import networkx as nx
import os
import uuid
import base64
from pyvis.network import Network
import unicodedata
import chardet
import io

st.set_page_config(layout="wide")
st.title("🏫アニメ・漫画 相関図ジェネレーター")

st.markdown("""
    <style>
        div[data-testid="stIFrame"] {
            border: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        iframe {
            display: block !important;
            vertical-align: bottom !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 共通の描画処理関数 ---
def draw_graph(df, image_data_map=None, uploaded_bg=None):
    net = Network(height="600px", width="100%", bgcolor="transparent", font_color="black", directed=True)
    
    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "font": { "size": 16, "background": "rgba(255,255,255,0.7)" }
      },
      "edges": {
        "width": 3,  
        "smooth": {
          "type": "dynamic",
          "roundness": 0.8
        },
        "font": {
          "size": 14,
          "align": "middle",
          "background": "rgba(255,255,255,0.5)"
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "springLength": 250,
          "springConstant": 0.2,
          "centralGravity": 0.01,
          "avoidOverlap": 0.5
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    # さらに、optionsを直接設定して背景色を無効化します
   
    
    nodes = set(df['source']).union(set(df['target']))
    for node in nodes:
        # 画像マップか、ローカルのsample_imagesフォルダを探す
        image_url = None
        if image_data_map and node in image_data_map:
            image_url = image_data_map[node]
        elif os.path.exists(f"./sample_images/{node}.png"):
            # 画像をBase64に変換して埋め込む（後半の形式に合わせる）
            with open(f"./sample_images/{node}.png", "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                image_url = f"data:image/png;base64,{b64}"

        if image_url:
            net.add_node(node, label=node, shape='image', image=image_url, size=40)
        else:
            net.add_node(node, label=node, shape='dot', color='orange', size=20)
    
    for _, row in df.iterrows():
        net.add_edge(row['source'], row['target'], label=row['label'])
    
   
    # HTML生成（後半のエンコード修正ロジックをそのまま使用）
    html_file = f"temp_{uuid.uuid4()}.html"
    net.save_graph(html_file)
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    #st.code(html_content[:3000])
    
    b64_bg = ""
    if uploaded_bg:
        uploaded_bg.seek(0)
        b64_bg = base64.b64encode(uploaded_bg.read()).decode()

    frame_css = f"""
    <style>
        body {{ 
            margin: 0; padding: 0; 
            background-image: url('data:image/png;base64,{b64_bg}');
            background-size: cover;
            background-position: center;
            height: 100vh;
            width: 100vw; /* body自体も幅いっぱいにする */
          
            justify-content: center;
            align-items: center;
            z-index: 1000; 
            overflow: hidden !important; /* 線の原因となる余白のスクロールバーを殺す */
            line-height: 0 !important;   /* ← 追加 */
            font-size: 0 !important;     /* ← 追加 */
        }}
        
        #mynetwork {{ 
            width: 100% !important;   /* 幅を目一杯に */
            height: 100% !important;  /* 高さもコンテナに合わせる */
            min-height: 600px;        /* ただし最小の高さは確保 */
            background: rgba(255, 255, 255, 0.0) !important; 
            border-radius: 0px !important; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.0) !important;
            margin: 0 !important;
            position: fixed !important;
            top: 0 !important;          /* 画面の一番上に配置 */
            left: 0 !important;
            z-index: 1000;              /* 他の要素より手前に表示 */
            pointer-events: auto;       /* グラフの操作を可能にする */
        }}
        canvas {{
            background-color: transparent !important;
            border: none !important; 
            outline: none !important; 
            box-shadow: none !important; 
            background: transparent !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 0;  
        }}
        
        /* Streamlitのコンポーネント用iframeの余白を消す */
        div[data-testid="stIFrame"] {{
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        
    </style>
    """
    
    
    
    force_style_js = """
    <script>
        (function() {
            var checkInterval = setInterval(function() {
                if (typeof network !== 'undefined') {
                    network.fit();
                    clearInterval(checkInterval);
                }
            }, 100);
        })();
    </script>
    """
    
    
    
    # 既存のhtml_content.replaceの直前に追加
    html_content = html_content.replace('</body>', f'{force_style_js}</body>')
    html_content = html_content.replace(
        '</head>', 
        '<style>#mynetwork { border: none !important; box-shadow: none !important; }</style></head>'
    )
    html_content = html_content.replace(
        '</head>', 
        '<style>#mynetwork, canvas { border: none !important; outline: none !important; } body { border: none !important; }</style></head>'
    )
    html_content = html_content.replace('</head>', f'{frame_css}</head>')
    html_content = html_content.replace('<iframe', '<iframe style="border:none !important;"')
    html_content = html_content.replace('background-color: white', 'background-color: transparent')
    html_content = html_content.replace('background-color: #ffffff', 'background-color: transparent')
    # ついでにこれも追加
    html_content = html_content.replace('style="background-color: white;"', 'style="background-color: transparent;"')
    
    
    html_content = html_content.replace(
        'border: 1px solid lightgray;',
        'border: none;'
    )

    # ★追加：Bootstrapのcardも透明にする
    html_content = html_content.replace(
        '<div class="card" style="width: 100%">',
        '<div style="width: 100%; border: none !important; background: transparent !important;">'
    )
    
    if '<meta charset="UTF-8">' not in html_content:
        html_content = html_content.replace('<head>', '<head><meta charset="UTF-8">')
    
    
    st.components.v1.html(html_content, height=800, scrolling=False)
    #st.components.v1.html(html_content, height=550, width=550, scrolling=False)
    
    if os.path.exists(html_file): os.remove(html_file)



st.sidebar.title("設定")
mode = st.sidebar.radio("モード選択", ["サンプルを見る(架空アニメ)", "自分のデータを使う"])

if mode == "サンプルを見る(架空アニメ)":
  
    data = [
        #家族
        ("ひなた", "たくみ", "憧れ・父"),
        ("たくみ", "ひなた", "子"),
        ("ひなた", "しおり", "母"),
        ("しおり", "ひなた", "子"),
        ("ひなた", "かなた", "兄"),
        ("かなた", "ひなた", "弟・おっちょこちょい"),
        ("ひなた", "りこ",  "姉・愛着"),
        ("りこ", "ひなた", "弟・愛着"),
        ("かなた", "りこ",  "姉"),
        ("りこ", "かなた", "弟・愛着"),
        
        ("ひなた", "ひな", "公園仲間"),
        ("ひな", "ひなた", "公園仲間・いたずら"),

        #りこの学校
        ("りこ", "ももか", "親友"),
        ("りこ", "みやび",  "吹奏楽部員"),
        ("りこ", "はな", "吹奏楽部員"),
        ("りこ", "ことね", "学級委員長"),
        ("ことね", "りこ", "トラブルメーカー"),
        ("りこ", "はるか",  "バスケ部員"),
        ("はるか", "あおい",  "バスケ部長"),
        ("はるか", "みお", "親友・バスケ部員"),
        ("ももか", "まこと", "片思い"),
        ("まこと", "なぎ", "双子"),
        ("なぎ", "まこと", "双子"),
        ("なぎ", "りこ", "仲良し"),
        
        #かなたの関係図
        ("かなた", "しゅん", "クラスメイト・運動神経抜群"),
        ("かなた", "れん", "クラスメイト・友達"),
        ("かなた", "つむぎ", "幼馴染"),
        ("かなた", "かなで", "クラスメイト・友達"),
        ("かなた", "ひより", "憧れのお姉さん"),
        ("ひより", "かなた", "可愛がってる"),
        ("かなた", "先生", "先生"),
        ("先生", "ゆずは", "推しのVtuber"),
    
        #その他
        ("しゅん", "めい", "姉"),
        ("めい", "しゅん", "弟・愛着"),
        ("めい", "りこ", "クラスメイト"),
        ("ひなた", "近所のお姉さん", "ミステリアス")
    ]

    df = pd.DataFrame(data, columns=['source', 'target', 'label'])
    if os.path.exists("./sample_images/壁紙.png"):
        with open("./sample_images/壁紙.png", "rb") as f:
            #st.sidebar.image("./sample_images/壁紙.png", caption="読み込まれた壁紙")
            draw_graph(df, uploaded_bg=f)
    else:
        st.sidebar.warning("壁紙.png が見つかりません")
        draw_graph(df)
else:
    csv_file = st.file_uploader("関係図CSVをアップロード(。´･ω･)?", type=["csv", "tsv", "txt"], label_visibility="visible")
    image_files = st.file_uploader("顔画像フォルダの中身（png, jpg, jpeg）を全てアップロード(*´з`)", accept_multiple_files=True)
    uploaded_bg = st.sidebar.file_uploader("背景壁紙を選択 (壁紙.png)", type=["png", "jpg", "jpeg"])


    if csv_file and image_files:
        # 画像マップ作成
        image_data_map = {}
        for img in image_files:
            b64 = base64.b64encode(img.read()).decode()
            name = unicodedata.normalize('NFKC', os.path.splitext(img.name)[0])
            image_data_map[name] = f"data:image/jpeg;base64,{b64}"
        
        # CSV読み込み
        raw_data = csv_file.read()
        df = pd.read_csv(io.BytesIO(raw_data), sep=None, encoding=chardet.detect(raw_data)['encoding'], engine='python')
        df.columns = df.columns.str.strip()
        
        # 【修正】背景がある場合は、ここで seek(0) をして先頭に戻してから渡す
        if uploaded_bg is not None:
            uploaded_bg.seek(0)
        
        draw_graph(df, image_data_map, uploaded_bg)