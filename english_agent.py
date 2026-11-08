import os
import shutil

# ========== ffmpeg路径配置（本地/云端自适应） ==========
def get_ffmpeg_path():
    """获取ffmpeg可执行文件路径：优先环境变量，其次本地Windows路径，最后系统PATH（云端Docker）"""
    # 1. 环境变量指定
    env_path = os.environ.get("FFMPEG_BINARY")
    if env_path and os.path.isfile(env_path):
        return env_path
    # 2. 本地Windows开发环境
    local_path = r"D:\ffmpeg\bin\ffmpeg.exe"
    if os.path.isfile(local_path):
        return local_path
    # 3. 系统PATH中查找（云端Docker容器内通过apt安装）
    return shutil.which("ffmpeg")

FFMPEG_PATH = get_ffmpeg_path()

import streamlit as st
from openai import OpenAI
import subprocess
import tempfile
import base64
import io
import json
import random
from datetime import datetime, date, timedelta

# ========== 配置 DeepSeek API（密钥不入源码，按 secrets → 环境变量顺序读取） ==========
def get_api_key():
    """优先读 .streamlit/secrets.toml，其次读环境变量 DEEPSEEK_API_KEY"""
    try:
        key = st.secrets["DEEPSEEK_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("DEEPSEEK_API_KEY")


API_KEY = get_api_key()
client = OpenAI(api_key=API_KEY or "missing-key", base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"

# ========== 本地素材路径（现场演示不依赖外网） ==========
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(APP_DIR, "assets")
# 优先 assets/logo.png；仓库直接上传到根目录时退用根目录的 logo.png
LOGO_PATH = os.path.join(ASSET_DIR, "logo.png")
if not os.path.isfile(LOGO_PATH):
    LOGO_PATH = os.path.join(APP_DIR, "logo.png")


def ask_ai(messages, spinner_text="AI 正在处理..."):
    """统一调用 DeepSeek：成功返回文本，失败给出友好提示并返回 None。"""
    with st.spinner(spinner_text):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                timeout=60,
            )
            return resp.choices[0].message.content
        except Exception as e:
            st.error(":material/error: AI 服务暂时不可用，请检查网络连接或 API 额度后重试。")
            st.caption(f"错误类型：{type(e).__name__}")
            return None

# ========== 页面设置 ==========
st.set_page_config(page_title="AI英语学习智能体", page_icon=":material/library_books:", layout="wide")

if not API_KEY:
    st.error(":material/error: 未配置 DeepSeek API Key。请在 .streamlit/secrets.toml 中设置 DEEPSEEK_API_KEY，或设置同名环境变量后重启。")
    st.stop()

# ========== 背景主题预设 ==========
PRESET_THEMES = {
    "默认浅色": {"bg": "#ffffff", "sidebar_bg": "#f0f2f6", "text": "#1a1a1a"},
    "护眼淡绿": {"bg": "#e8f5e9", "sidebar_bg": "#c8e6c9", "text": "#1b5e20"},
    "深夜模式": {"bg": "#1e1e2e", "sidebar_bg": "#181825", "text": "#cdd6f4"},
    "暖橙渐变": {"bg": "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)", "sidebar_bg": "#ffd8b5", "text": "#5d4037"},
    "雾霾蓝": {"bg": "linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)", "sidebar_bg": "#b8d4f5", "text": "#2c3e50"},
}

# ========== 范文库预设 ==========
ESSAY_TEMPLATES = {
    "书信建议类": "Dear [Name],\nI am writing to you to offer some suggestions about [topic].\nFirst of all, ... In addition, ... Finally, ...\nI hope you will find these suggestions helpful.\nYours sincerely,\n[Your Name]",
    "观点对比类": "Nowadays, there is a widespread concern over [topic]. Some people believe that ... However, others argue that ...\nFrom my point of view, ... On the one hand, ... On the other hand, ...\nIn conclusion, we should ...",
    "现象解释类": "It is well-known that [phenomenon] has become a common phenomenon in our daily life.\nThere are several reasons accounting for this. Firstly, ... Secondly, ... Thirdly, ...\nAs far as I am concerned, ... Only in this way can we ...",
}

# ========== 初始化会话状态 ==========
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "word_collection" not in st.session_state:
    st.session_state.word_collection = []
if "practice_records" not in st.session_state:
    st.session_state.practice_records = {"对话练习": 0, "单词查询": 0, "长难句": 0, "作文批改": 0, "语法题": 0, "视频解析": 0, "口语跟读": 0, "听写练习": 0, "仿写练习": 0}
if "quiz_history" not in st.session_state:
    st.session_state.quiz_history = []
if "video_notes" not in st.session_state:
    st.session_state.video_notes = []
if "bg_theme" not in st.session_state:
    st.session_state.bg_theme = "默认浅色"
if "custom_bg" not in st.session_state:
    st.session_state.custom_bg = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
# 新增功能状态
if "checkin_days" not in st.session_state:
    st.session_state.checkin_days = 0
if "last_checkin" not in st.session_state:
    st.session_state.last_checkin = None
if "dictation_index" not in st.session_state:
    st.session_state.dictation_index = 0
if "dictation_list" not in st.session_state:
    st.session_state.dictation_list = []
if "dictation_score" not in st.session_state:
    st.session_state.dictation_score = 0
if "imitate_example" not in st.session_state:
    st.session_state.imitate_example = ""

# ========== 演示账号（比赛演示用） ==========
DEMO_ACCOUNTS = {
    "admin": "123456",
    "student": "123456",
}

# ========== 注入背景 CSS ==========
def inject_background():
    theme = PRESET_THEMES.get(st.session_state.bg_theme, PRESET_THEMES["默认浅色"])
    bg_css = theme["bg"]
    is_gradient = bg_css.startswith("linear-gradient")
    
    if st.session_state.custom_bg:
        bg_image = f"url('data:image/jpeg;base64,{st.session_state.custom_bg}')"
    else:
        bg_image = "none"
    
    if is_gradient:
        bg_value = bg_css
    else:
        bg_value = bg_css
    
    st.markdown(f"""
    <style>
    .stApp {{
        background: {bg_value};
        background-image: {bg_image};
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {theme["sidebar_bg"]};
    }}
    .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: {theme["text"]};
    }}
    </style>
    """, unsafe_allow_html=True)

inject_background()

# ========== 登录拦截 ==========
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        if os.path.isfile(LOGO_PATH):
            st.image(LOGO_PATH, width=100)
        st.title(":material/library_books: AI英语学习智能体")
        st.caption("面向全国人工智能应用创新大赛的参赛演示作品 · 请先登录")
        st.divider()

        login_user = st.text_input(":material/person: 用户名", placeholder="请输入用户名")
        login_pwd = st.text_input(":material/key: 密码", type="password", placeholder="请输入密码")

        if st.button("登 录", type="primary", use_container_width=True):
            if login_user in DEMO_ACCOUNTS and DEMO_ACCOUNTS[login_user] == login_pwd:
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.rerun()
            else:
                st.error(":material/delete: 用户名或密码错误，请重试")

        st.info(":material/lightbulb: 演示账号：`admin` / `student`，密码均为 `123456`；仅用于演示，未接入真实账号体系")

    st.stop()

# ========== 浏览器TTS语音朗读 ==========
st.markdown("""
<script>
if (!window._tts_injected) {
    window._tts_injected = true;
    window.speakText = function(text, lang, rate) {
        if (!text || !text.trim()) return;
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = lang || 'en-US';
        utter.rate = rate || 0.9;
        window.speechSynthesis.speak(utter);
    };
    window.stopSpeak = function() {
        window.speechSynthesis.cancel();
    };
}
</script>
""", unsafe_allow_html=True)

def speak_button(label, text, lang="en-US", key=None):
    if not text or not str(text).strip():
        return
    rate = st.session_state.get("tts_rate", 0.9)
    text_js = json.dumps(str(text), ensure_ascii=False)
    lang_js = json.dumps(lang)
    if st.button(label, key=key):
        st.markdown(
            f"<script>window.speakText({text_js}, {lang_js}, {rate});</script>",
            unsafe_allow_html=True,
        )

# ========== 侧边栏 ==========
with st.sidebar:
    if os.path.isfile(LOGO_PATH):
        st.image(LOGO_PATH, width=80)
    st.title("AI英语学习智能体")
    st.caption("参赛演示作品 · 基于 DeepSeek 大模型构建")
    st.divider()

    # 当前用户 + 退出登录
    st.subheader(f":material/person: 当前用户：{st.session_state.username}")
    if st.button(":material/logout: 退出登录", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
    st.divider()

    # 学习打卡
    st.subheader(":material/calendar_month: 学习打卡")
    today = str(date.today())
    col_checkin, col_streak = st.columns([2, 1])
    with col_checkin:
        if st.button("今日打卡", use_container_width=True):
            if st.session_state.last_checkin == today:
                st.warning("今天已打卡")
            else:
                yesterday = str(date.today() - timedelta(days=1))
                if st.session_state.last_checkin == yesterday:
                    st.session_state.checkin_days += 1
                else:
                    st.session_state.checkin_days = 1
                st.session_state.last_checkin = today
                st.success(f":material/check_circle: 打卡成功！已连续打卡 {st.session_state.checkin_days} 天")
    with col_streak:
        st.metric("连续天数", st.session_state.checkin_days)
    st.divider()

    # 学习水平选择
    st.subheader(":material/settings: 学习设置")
    level = st.selectbox("我的英语水平", ["小学", "初中", "高中", "大学四级", "大学六级"])
    role_style = st.selectbox("AI老师风格", ["专业严肃老师", "趣味口语外教", "温柔鼓励型"])
    tts_rate = st.slider(":material/volume_up: 朗读语速", min_value=0.5, max_value=1.5, value=0.9, step=0.1,
                         help="0.5 慢速（适合精听），1.0 正常，1.5 快速")
    
    st.divider()
    
    # 背景设置
    st.subheader(":material/palette: 背景设置")
    theme_options = list(PRESET_THEMES.keys()) + ["自定义图片"]
    selected_theme = st.selectbox("选择背景主题", theme_options, index=theme_options.index(st.session_state.bg_theme) if st.session_state.bg_theme in theme_options else 0)
    
    if selected_theme == "自定义图片":
        uploaded_img = st.file_uploader("上传背景图", type=["jpg", "jpeg", "png"])
        if uploaded_img is not None:
            bytes_data = uploaded_img.read()
            b64 = base64.b64encode(bytes_data).decode()
            st.session_state.custom_bg = b64
            st.session_state.bg_theme = "自定义图片"
        elif st.session_state.custom_bg is None:
            st.session_state.bg_theme = "默认浅色"
    else:
        st.session_state.bg_theme = selected_theme
        st.session_state.custom_bg = None
    
    if st.session_state.custom_bg and selected_theme != "自定义图片":
        st.session_state.custom_bg = None
    
    st.divider()
    
    # 快速统计
    st.subheader(":material/bar_chart: 学习统计")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("已学生词", len(st.session_state.word_collection))
    with col2:
        total_practice = sum(st.session_state.practice_records.values())
        st.metric("练习次数（累计）", total_practice)
    
    st.divider()
    if st.button(":material/delete: 清空所有学习记录", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.word_collection = []
        st.session_state.quiz_history = []
        st.session_state.video_notes = []
        st.session_state.practice_records = {"对话练习": 0, "单词查询": 0, "长难句": 0, "作文批改": 0, "语法题": 0, "视频解析": 0, "口语跟读": 0, "听写练习": 0, "仿写练习": 0}
        st.rerun()

# ========== 主页面Tabs ==========
tab_home, tab_chat, tab_word, tab_dictation, tab_sentence, tab_essay, tab_grammar, tab_video, tab_speaking, tab_report = st.tabs([
    ":material/home: 首页",
    ":material/chat: 对话练习",
    ":material/menu_book: 单词学习",
    ":material/abc: 单词听写",
    ":material/search: 长难句解析",
    ":material/edit: 作文批改",
    ":material/format_quote: 语法练习",
    ":material/movie: 视频解析",
    ":material/mic: 口语跟读",
    ":material/trending_up: 学习报告"
])

# ============================================================
# Tab 1: 首页
# ============================================================
with tab_home:
    st.title(":material/library_books: AI英语学习智能体")
    st.caption("基于 DeepSeek 大模型的轻量化英语学习工具 · 面向在校学生的课外练习场景")
    
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader(":material/lightbulb: 项目背景")
        st.markdown("""
        **问题**：一对一外教资源稀缺、成本较高；学生课后缺少可获得即时反馈的英语练习渠道。
        
        **方案**：基于 DeepSeek 大模型构建轻量化本地应用，普通办公电脑即可运行，覆盖词汇、语法、写作与听说练习。
        """)
        
        st.subheader(":material/auto_awesome: 核心创新点")
        st.markdown("""
        - :material/smart_toy: **AI 对话陪练**：按所选水平生成对话，逐轮指出语法与用词问题
        - :material/library_books: **智能生词本**：一键收藏，按收藏后第 1/2/4/7/15 天提示复习
        - :material/abc: **单词听写闯关**：从生词本随机抽词，按拼写完全匹配自动判分
        - :material/movie: **视频解析**：ffmpeg 提取音轨，粘贴字幕后由 AI 翻译并提取生词
        - :material/mic: **口语跟读评分**：将朗读转写文本与原文逐词比对，给出准确度评分与改进建议
        - :material/calendar_month: **学习打卡**：记录连续打卡天数
        - :material/trending_up: **学习报告**：数据统计 + AI个性化学习建议
        """)
    
    with col2:
        st.subheader(":material/bar_chart: 学习数据总览")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("对话轮次", len(st.session_state.chat_history) // 2)
            st.metric("已学生词", len(st.session_state.word_collection))
        with metrics_col2:
            st.metric("语法题数", len(st.session_state.quiz_history))
            st.metric("视频笔记", len(st.session_state.video_notes))
        with metrics_col3:
            total = sum(st.session_state.practice_records.values())
            st.metric("总练习次数", total)
        
        st.info(f"当前学习水平：**{level}** | 连续打卡：**{st.session_state.checkin_days}天**")
    
    st.divider()
    
    st.subheader(":material/rocket: 快速开始")
    st.markdown("""
    1. **对话练习** → 输入英文句子，AI 逐轮纠错并追问
    2. **单词学习** → 查询单词，自动加入生词本
    3. **单词听写** → 从生词本抽词闯关，巩固记忆
    4. **作文批改** → 粘贴作文，AI 逐句找出错误并给出修改建议
    5. **学习报告** → 查看统计数据，获取AI学习建议
    """)

# ============================================================
# Tab 2: 英语对话练习
# ============================================================
with tab_chat:
    st.subheader(":material/chat: AI英语对话练习")
    
    style_prompt = {
        "专业严肃老师": "你是一位专业严肃的英语老师，注重语法准确性，严格纠正错误。",
        "趣味口语外教": "你是一位轻松有趣的口语外教，鼓励多说，语气活泼，多用俚语。",
        "温柔鼓励型": "你是一位温柔鼓励的英语老师，多表扬少批评，耐心引导学生开口。"
    }
    level_prompt = {
        "小学": "使用小学水平词汇，句子简短简单。",
        "初中": "使用初中水平词汇，对话长度适中。",
        "高中": "使用高中水平词汇，可以有一些复杂句式。",
        "大学四级": "使用四级词汇，可以有较多从句。",
        "大学六级": "使用六级词汇，句式丰富，接近母语水平。"
    }
    
    user_input = st.text_input("输入英文句子，或用中文提问：", placeholder="例如：How can I improve my English writing?")
    
    col_send, col_clear = st.columns([1, 3])
    with col_send:
        if st.button("发送", type="primary") and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.practice_records["对话练习"] += 1
            
            system_prompt = f"{style_prompt[role_style]} {level_prompt[level]} 请用英语回复我，每次回复2-3句话，结尾提一个问题引导继续。同时用中文简要解释你的回复。"
            
            messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history
            ai_reply = ask_ai(messages, "AI 正在回复...")
            if ai_reply:
                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
    
    with col_clear:
        if st.button("清空对话"):
            st.session_state.chat_history = []
            st.rerun()
    
    st.divider()
    for idx, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.markdown(f"**:material/person: 你：** {msg['content']}")
        else:
            st.markdown(f"**:material/smart_toy: AI老师：** {msg['content']}")
            c1, c2 = st.columns([1, 5])
            with c1:
                speak_button(":material/volume_up: 朗读英文", msg["content"], lang="en-US", key=f"speak_chat_{idx}")
            with c2:
                speak_button(":material/casino: 朗读中文", msg["content"], lang="zh-CN", key=f"speak_chat_zh_{idx}")
    
    if st.session_state.chat_history:
        chat_text = "\n".join([f"{'我' if m['role']=='user' else 'AI'}: {m['content']}" for m in st.session_state.chat_history])
        st.download_button(":material/download: 导出对话记录", data=chat_text, file_name="英语对话记录.txt", mime="text/plain")

# ============================================================
# Tab 3: 单词学习 + 生词本（词根词缀解析）
# ============================================================
with tab_word:
    st.subheader(":material/menu_book: 单词查询与讲解")
    
    col_word, col_vocab = st.columns([1.2, 1])
    
    with col_word:
        word = st.text_input("输入英文单词：", placeholder="例如：ambitious")
        
        col_query, col_root = st.columns(2)
        with col_query:
            if st.button(":material/menu_book: 详细讲解", type="primary") and word.strip():
                st.session_state.practice_records["单词查询"] += 1
                prompt = f"""你是英语老师。请讲解单词：{word}
                要求：
                1. 音标（英式，IPA 标注）
                2. 中文释义（分词性）
                3. 常见搭配（2-3个）
                4. 例句（2个，附中文翻译）
                5. 记忆小技巧
                当前学生水平：{level}
                格式清晰。"""
                result = ask_ai([{"role": "user", "content": prompt}], "正在讲解...")
                if result:
                    st.markdown(result)
                    speak_button(f":material/volume_up: 朗读单词 '{word}'", word, lang="en-US", key=f"speak_word_{word}")

                word_lower = word.lower()
                exists = any(w[0].lower() == word_lower for w in st.session_state.word_collection)
                if not exists:
                    if st.button(f":material/star: 将 '{word}' 加入生词本"):
                        st.session_state.word_collection.append((word, datetime.now()))
                        st.success(f":material/check_circle: 已加入生词本！")
                        st.rerun()
                else:
                    st.caption("（该单词已在生词本中）")
        
        with col_root:
            if st.button(":material/extension: 词根词缀解析") and word.strip():
                st.session_state.practice_records["单词查询"] += 1
                prompt = f"""请解析单词 {word} 的词根词缀：
                1. 拆分词根、前缀、后缀（分别解释含义）
                2. 词源小故事
                3. 同根词扩展（3-5个）
                4. 记忆口诀
                学生水平：{level}
                用中文讲解，格式清晰。"""
                result = ask_ai([{"role": "user", "content": prompt}], "正在解析词根词缀...")
                if result:
                    st.markdown(result)
    
    with col_vocab:
        st.subheader(":material/library_books: 我的生词本")
        st.caption(":material/star: 标记的是今日建议复习的单词（按收藏后第 1/2/4/7/15 天提醒）")
        
        if st.session_state.word_collection:
            now = datetime.now()
            review_words = []
            for item in st.session_state.word_collection:
                w, add_time = item
                diff_days = (now - add_time).days
                is_review = diff_days in [1, 2, 4, 7, 15]
                marker = " :material/star:建议复习" if is_review else ""
                if is_review:
                    review_words.append(w)
                st.markdown(f"- **{w}**{marker}")
            
            st.caption(f"共 {len(st.session_state.word_collection)} 个单词 | 今日待复习 {len(review_words)} 个")
            
            vocab_text = "\n".join([w[0] for w in st.session_state.word_collection])
            st.download_button(":material/download: 导出生词本", data=vocab_text, file_name="我的生词本.txt", mime="text/plain")
            
            if st.button("清空生词本"):
                st.session_state.word_collection = []
                st.rerun()
        else:
            st.info("生词本为空。可在「单词学习」中查询单词并收藏。")

# ============================================================
# Tab 4: 单词听写闯关（新增）
# ============================================================
with tab_dictation:
    st.subheader(":material/abc: 单词听写闯关")
    st.caption("从生词本随机抽词，用浏览器语音朗读读音，由你拼写，按拼写完全匹配自动判分")
    
    if len(st.session_state.word_collection) < 3:
        st.info(":material/lightbulb: 生词本至少需要3个单词才能开始听写，先去「单词学习」收藏一些单词吧！")
    else:
        col_start, col_status = st.columns([1, 2])
        with col_start:
            if st.button(":material/sports_esports: 开始/重新听写", type="primary"):
                word_list = [w[0] for w in st.session_state.word_collection]
                random.shuffle(word_list)
                st.session_state.dictation_list = word_list
                st.session_state.dictation_index = 0
                st.session_state.dictation_score = 0
        
        if st.session_state.dictation_list:
            with col_status:
                progress = st.session_state.dictation_index / len(st.session_state.dictation_list)
                st.progress(progress, text=f"进度：{st.session_state.dictation_index}/{len(st.session_state.dictation_list)}")
            
            if st.session_state.dictation_index >= len(st.session_state.dictation_list):
                score = st.session_state.dictation_score
                total = len(st.session_state.dictation_list)
                st.success(f":material/celebration: 听写完成：答对 {score}/{total} 题，正确率 {int(score/total*100)}%")
                if score == total:
                    st.balloons()
                st.session_state.practice_records["听写练习"] += 1
                if st.button("再来一轮"):
                    st.session_state.dictation_list = []
                    st.rerun()
            else:
                current_word = st.session_state.dictation_list[st.session_state.dictation_index]
                st.divider()
                st.subheader(f"第 {st.session_state.dictation_index + 1} 题")
                
                speak_button(":material/volume_up: 播放读音（可重复听）", current_word, lang="en-US", key=f"dict_play_{st.session_state.dictation_index}")
                
                user_spell = st.text_input("请拼写这个单词：", key=f"dict_input_{st.session_state.dictation_index}")
                
                col_submit, col_hint = st.columns([1, 2])
                with col_submit:
                    if st.button("提交答案", type="primary"):
                        if user_spell.strip().lower() == current_word.lower():
                            st.success(":material/check_circle: 正确！")
                            st.session_state.dictation_score += 1
                        else:
                            st.error(f":material/delete: 错误，正确答案：**{current_word}**")
                        st.session_state.dictation_index += 1
                        st.rerun()
                with col_hint:
                    if st.button(":material/lightbulb: 提示（看首字母）"):
                        st.info(f"提示：单词以 **{current_word[0].upper()}** 开头，共 {len(current_word)} 个字母")

# ============================================================
# Tab 5: 长难句解析 + 句子仿写训练
# ============================================================
with tab_sentence:
    st.subheader(":material/search: 长难句解析")
    sentence = st.text_area("输入英文长难句：", height=100, placeholder="例如：The book that I bought yesterday, which was written by a famous author, has been translated into many languages.")
    
    if st.button("开始解析", type="primary") and sentence.strip():
        st.session_state.practice_records["长难句"] += 1
        prompt = f"""你是英语语法老师。请解析这个英文句子：{sentence}
        要求：
        1. 整句中文翻译
        2. 拆分句子结构（主句、从句、修饰成分）
        3. 标出重点短语和固定搭配
        4. 关键语法点讲解
        学生水平：{level}
        用中文清晰讲解。"""
        result = ask_ai([{"role": "user", "content": prompt}], "正在解析...")
        if result:
            st.markdown(result)
            speak_button(":material/volume_up: 朗读原句", sentence, lang="en-US", key="speak_sentence")
    
    st.divider()
    st.subheader(":material/edit_note: 句子仿写训练")
    st.caption("AI 提供例句，由你仿写；AI 给出相似度评分与修改建议")
    
    col_gen, col_check = st.columns([1, 2])
    with col_gen:
        if st.button(":material/casino: 生成仿写例句", type="secondary"):
            prompt = f"""给一个适合{level}水平的英文例句，句式有代表性，适合仿写。只输出例句本身，不要解释。"""
            example = ask_ai([{"role": "user", "content": prompt}], "生成例句中...")
            if example:
                st.session_state.imitate_example = example.strip()
    
    if st.session_state.imitate_example:
        st.info(f":material/push_pin: 例句：**{st.session_state.imitate_example}**")
        speak_button(":material/volume_up: 朗读例句", st.session_state.imitate_example, lang="en-US", key="speak_imitate_example")
        
        user_imitate = st.text_area("你的仿写句子：", height=80, key="imitate_input")
        if st.button("批改仿写", type="primary") and user_imitate.strip():
            st.session_state.practice_records["仿写练习"] += 1
            prompt = f"""你是英语写作老师。请批改学生的仿写句子：
            
            原例句：{st.session_state.imitate_example}
            学生仿写：{user_imitate}
            
            要求：
            1. 相似度评分（0-100）
            2. 语法错误指出
            3. 用词改进建议
            4. 优化后的仿写版本
            学生水平：{level}
            用中文讲解。"""
            result = ask_ai([{"role": "user", "content": prompt}], "AI 正在批改...")
            if result:
                st.markdown(result)

# ============================================================
# Tab 6: 作文批改 + 范文库
# ============================================================
with tab_essay:
    st.subheader(":material/edit: 英语作文批改")
    essay = st.text_area("粘贴你的英文作文：", height=200, placeholder="把你写的英语作文粘贴到这里...")
    
    if st.button("开始批改", type="primary") and essay.strip():
        st.session_state.practice_records["作文批改"] += 1
        prompt = f"""你是严格的英语写作老师。请批改这段英文作文：{essay}
        要求：
        1. 找出所有语法错误（原句→错误原因→修改建议）
        2. 用词提升建议（2-3处）
        3. 整体评价（优点+不足）
        4. 改进后的版本
        学生水平：{level}
        用中文讲解。"""
        result = ask_ai([{"role": "user", "content": prompt}], "AI 正在批改...")
        if result:
            st.markdown(result)
    
    st.divider()
    st.subheader(":material/bookmarks: 作文范文模板库")
    st.caption("内置三类常用作文结构模板，可据此生成同主题范文")
    
    col_tpl, col_gen = st.columns([1, 2])
    with col_tpl:
        tpl_type = st.selectbox("选择作文类型", list(ESSAY_TEMPLATES.keys()))
        st.text_area("模板参考", value=ESSAY_TEMPLATES[tpl_type], height=150, disabled=True)
    
    with col_gen:
        essay_topic = st.text_input("输入作文主题（例如：线上学习的利弊）：", placeholder="例如：线上学习的利弊")
        if st.button(":material/palette: AI生成范文", type="secondary") and essay_topic.strip():
            prompt = f"""请写一篇{level}水平的{tpl_type}作文，主题是：{essay_topic}
            要求：
            1. 字数120-180词
            2. 结构清晰（开头-主体-结尾）
            3. 使用常用高级词汇和句型
            4. 附中文翻译和重点短语标注
            用英文写作，中文注释。"""
            result = ask_ai([{"role": "user", "content": prompt}], "AI 正在生成范文...")
            if result:
                st.markdown(result)

# ============================================================
# Tab 7: 语法专项练习
# ============================================================
with tab_grammar:
    st.subheader(":material/format_quote: 语法专项练习")
    
    col_gen, col_check = st.columns([1, 1])
    
    with col_gen:
        if st.button(":material/casino: 生成一道语法题", type="primary"):
            st.session_state.practice_records["语法题"] += 1
            prompt = f"""你是英语出题老师。请出一道英语语法选择题：
            学生水平：{level}
            要求：
            1. 出一道语法单选题，有A/B/C/D四个选项
            2. 给出正确答案
            3. 给出详细解析
            格式：
            【题目】...
            A. ...  B. ...  C. ...  D. ...
            【答案】...
            【解析】...
            """
            quiz = ask_ai([{"role": "user", "content": prompt}], "正在出题...")
            if quiz:
                st.session_state.quiz_history.append(quiz)
                st.markdown(quiz)
    
    with col_check:
        st.subheader(":material/content_paste: 练习历史")
        if st.session_state.quiz_history:
            for i, q in enumerate(reversed(st.session_state.quiz_history[-5:]), 1):
                with st.expander(f"第 {len(st.session_state.quiz_history) - i + 1} 题"):
                    st.markdown(q)
        else:
            st.info("尚未生成题目。点击左侧「生成一道语法题」开始练习。")

# ============================================================
# Tab 8: 视频解析（ffmpeg提取音频）
# ============================================================
with tab_video:
    st.subheader(":material/movie: 英语视频解析")
    st.info("上传英语视频后可用 ffmpeg 提取音轨；将字幕粘贴到下方文本框，由 AI 翻译、提取生词并概括大意")
    if not FFMPEG_PATH:
        st.warning(":material/warning: 未检测到ffmpeg，音频提取功能不可用（字幕解析不受影响）")
    
    uploaded_video = st.file_uploader("上传视频文件（mp4推荐）", type=["mp4", "mov", "mkv"])
    
    if uploaded_video is not None:
        st.video(uploaded_video)
        
        if st.button(":material/music_note: 提取音频（ffmpeg）", type="primary"):
            if not FFMPEG_PATH:
                st.error(":material/delete: 未检测到ffmpeg，无法提取音频。请安装ffmpeg或设置 FFMPEG_BINARY 环境变量。")
            else:
                st.session_state.practice_records["视频解析"] += 1
                with st.spinner("正在提取音频..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_vid:
                        temp_vid.write(uploaded_video.read())
                        temp_vid_path = temp_vid.name
                    
                    temp_audio_path = temp_vid_path.replace(".mp4", ".mp3")
                    
                    cmd = [
                        FFMPEG_PATH,
                        "-i", temp_vid_path,
                        "-vn", "-acodec", "libmp3lame", "-y",
                        temp_audio_path
                    ]
                    try:
                        subprocess.run(cmd, capture_output=True, check=True)
                        with open(temp_audio_path, "rb") as f:
                            audio_data = f.read()
                        st.success(":material/check_circle: 音频提取成功！")
                        st.audio(audio_data, format="audio/mp3")
                        st.download_button(":material/download: 下载MP3音频", data=audio_data, file_name="extracted_audio.mp3", mime="audio/mpeg")
                    except Exception as e:
                        st.error(f"音频提取失败：{str(e)}")
                        st.info(f"ffmpeg路径：{FFMPEG_PATH}，请确认安装正确")
        
        st.divider()
        st.subheader(":material/format_quote: 字幕解析")
        subtitle = st.text_area("粘贴视频英文字幕（从视频中复制）：", height=150)
        
        if st.button(":material/smart_toy: AI解析字幕", type="primary") and subtitle.strip():
            prompt = f"""你是英语学习老师。请解析这段英文视频字幕：{subtitle}
            要求：
            1. 翻译成通顺中文
            2. 标出5-8个重点生词（单词+释义）
            3. 概括视频大意（2-3句话）
            4. 给出学习建议（适合精听还是泛听，重点掌握什么）
            学生水平：{level}
            格式清晰。"""
            analysis = ask_ai([{"role": "user", "content": prompt}], "AI 正在解析...")
            if analysis:
                st.markdown(analysis)
                st.session_state.video_notes.append(analysis)

# ============================================================
# Tab 9: 口语跟读评分
# ============================================================
with tab_speaking:
    st.subheader(":material/mic: 口语跟读评分")
    st.info("将你朗读的转写文本与标准原文逐词比对，AI 给出准确度评分与改进建议（不评估音色、语调等声学特征）")
    
    col_std, col_user = st.columns(2)
    with col_std:
        standard_text = st.text_area("标准英文原文：", height=120, placeholder="粘贴需要朗读的英文句子...")
        if standard_text.strip():
            speak_button(":material/volume_up: 朗读标准原文（先听后跟读）", standard_text, lang="en-US", key="speak_std")
    with col_user:
        user_read = st.text_area("你朗读的内容（语音转文字或手动输入）：", height=120, placeholder="输入你读到的内容...")
    
    if st.button(":material/target: 开始评分", type="primary") and standard_text.strip() and user_read.strip():
        st.session_state.practice_records["口语跟读"] += 1
        prompt = f"""你是口语发音评测老师。请对比原文和学生朗读的内容：
        
        原文：{standard_text}
        学生朗读：{user_read}
        
        要求：
        1. 给出准确度评分（0-100分）
        2. 找出漏读的单词
        3. 找出多读的单词
        4. 找出读错的单词（原文→学生读成的）
        5. 给出3条具体改进建议
        学生水平：{level}
        用中文讲解。"""
        result = ask_ai([{"role": "user", "content": prompt}], "AI 正在评分...")
        if result:
            st.markdown(result)

# ============================================================
# Tab 10: 学习报告
# ============================================================
with tab_report:
    st.subheader(":material/trending_up: 学习报告与AI建议")
    
    st.subheader(":material/bar_chart: 练习分布")
    practice_data = st.session_state.practice_records
    st.bar_chart(practice_data)
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("总练习次数", sum(practice_data.values()))
        st.metric("已学生词", len(st.session_state.word_collection))
    with col_stat2:
        st.metric("语法题数", len(st.session_state.quiz_history))
        st.metric("连续打卡", f"{st.session_state.checkin_days} 天")
    
    st.divider()
    
    st.subheader(":material/smart_toy: AI个性化学习建议")
    if st.button("生成学习建议", type="primary"):
        stats_text = f"""
        学生当前水平：{level}
        连续打卡天数：{st.session_state.checkin_days}
        练习数据：
        - 对话练习：{practice_data['对话练习']}次
        - 单词查询：{practice_data['单词查询']}次
        - 长难句解析：{practice_data['长难句']}次
        - 作文批改：{practice_data['作文批改']}次
        - 语法题：{practice_data['语法题']}次
        - 视频解析：{practice_data['视频解析']}次
        - 口语跟读：{practice_data['口语跟读']}次
        - 听写练习：{practice_data.get('听写练习', 0)}次
        - 仿写练习：{practice_data.get('仿写练习', 0)}次
        已学生词数量：{len(st.session_state.word_collection)}
        """
        prompt = f"""你是资深英语学习规划师。请根据以下学习数据，给出个性化学习建议：
        {stats_text}
        
        要求：
        1. 分析当前学习优势和薄弱环节
        2. 给出本周学习计划建议（具体到每天做什么）
        3. 推荐适合的学习资源类型
        4. 鼓励性的结语
        格式清晰，用中文。"""
        advice = ask_ai([{"role": "user", "content": prompt}], "AI 正在生成建议...")
        if advice:
            st.markdown(advice)
    
    st.divider()
    st.subheader(":material/download: 导出完整学习报告")
    report_text = f"""
================================
AI英语学习智能体 - 学习报告
================================
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
学生：{st.session_state.username}
当前水平：{level}
连续打卡：{st.session_state.checkin_days} 天

【练习统计】
- 对话练习：{practice_data['对话练习']} 次
- 单词查询：{practice_data['单词查询']} 次
- 长难句解析：{practice_data['长难句']} 次
- 作文批改：{practice_data['作文批改']} 次
- 语法题：{practice_data['语法题']} 次
- 听写练习：{practice_data.get('听写练习', 0)} 次
- 仿写练习：{practice_data.get('仿写练习', 0)} 次
- 总练习次数：{sum(practice_data.values())} 次

【生词本】（共 {len(st.session_state.word_collection)} 个）
"""
    for w, t in st.session_state.word_collection:
        report_text += f"  - {w}（收藏于 {t.strftime('%Y-%m-%d')}）\n"
    
    st.download_button(":material/download: 导出学习报告TXT", data=report_text, file_name="学习报告.txt", mime="text/plain")

# ========== 底部 ==========
st.divider()
st.caption(":material/warning: 本工具仅用于英语学习辅助；AI 生成内容可能存在偏差，请自行核对；请勿直接抄袭生成内容作为作业提交。 | AI英语学习智能体 · 2026")
