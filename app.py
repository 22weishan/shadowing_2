# app.py - 英语听力精听助手（无whisper依赖）
import streamlit as st
import tempfile
import os
import json
from pydub import AudioSegment
from pydub.silence import split_on_silence

# 页面配置
st.set_page_config(
    page_title="英语听力精听助手",
    page_icon="🎧",
    layout="wide"
)

# 初始化session state
if 'sentences' not in st.session_state:
    st.session_state.sentences = []
if 'current_sentence' not in st.session_state:
    st.session_state.current_sentence = 0
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'difficult_sentences' not in st.session_state:
    st.session_state.difficult_sentences = set()
if 'playback_speed' not in st.session_state:
    st.session_state.playback_speed = 1.0

# 自定义CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        font-size: 2.5em;
        color: #1E88E5;
        margin-bottom: 0.5em;
    }
    .sub-title {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .sentence-card {
        background: #f8f9fa;
        border-left: 4px solid #1E88E5;
        padding: 1em;
        margin: 0.5em 0;
        border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-title">🎧 英语听力精听助手</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">上传音频 · 智能断句 · 高效精听</div>', unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 断句参数
    st.subheader("断句参数")
    min_silence_len = st.slider("最小静音长度(ms)", 300, 1500, 500, 50)
    silence_thresh = st.slider("静音阈值(dBFS)", -60, -20, -40, 5)
    
    # 播放设置
    st.subheader("播放设置")
    st.session_state.playback_speed = st.select_slider(
        "播放速度",
        options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
        value=1.0
    )
    
    st.divider()
    
    # 工具按钮
    st.subheader("🛠️ 工具")
    if st.button("🔄 重置所有", use_container_width=True, type="secondary"):
        # 清理临时文件
        for sentence in st.session_state.sentences:
            if 'audio_path' in sentence and os.path.exists(sentence['audio_path']):
                try:
                    os.unlink(sentence['audio_path'])
                except:
                    pass
        
        # 重置session state
        keys = list(st.session_state.keys())
        for key in keys:
            del st.session_state[key]
        
        st.rerun()
    
    if st.button("📊 导出数据", use_container_width=True):
        if st.session_state.sentences:
            export_data = {
                "audio_name": st.session_state.audio_file.name if st.session_state.audio_file else "unknown",
                "total_sentences": len(st.session_state.sentences),
                "sentences": []
            }
            
            st.download_button(
                "下载JSON",
                json.dumps(export_data, indent=2),
                "listening_data.json",
                "application/json"
            )

# 主界面
tab1, tab2 = st.tabs(["📁 上传与断句", "🎵 听写练习"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("上传音频")
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择音频文件",
            type=["mp3", "wav", "m4a"],
            help="支持 MP3, WAV, M4A 格式"
        )
        
        if uploaded_file:
            st.session_state.audio_file = uploaded_file
            
            # 显示文件信息
            st.success(f"✅ {uploaded_file.name}")
            st.audio(uploaded_file, format=f"audio/{uploaded_file.type.split('/')[-1]}")
            
            # 断句按钮
            if st.button("🔍 开始智能断句", type="primary", use_container_width=True):
                with st.spinner("正在分析音频..."):
                    try:
                        # 保存临时文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                        
                        # 加载音频
                        audio = AudioSegment.from_file(tmp_path)
                        
                        # 断句
                        chunks = split_on_silence(
                            audio,
                            min_silence_len=min_silence_len,
                            silence_thresh=silence_thresh,
                            keep_silence=100
                        )
                        
                        # 保存句子
                        st.session_state.sentences = []
                        for i, chunk in enumerate(chunks):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as chunk_file:
                                chunk.export(chunk_file.name, format="mp3")
                                
                                sentence_data = {
                                    "id": i,
                                    "path": chunk_file.name,
                                    "duration": len(chunk) / 1000
                                }
                                st.session_state.sentences.append(sentence_data)
                        
                        st.session_state.transcripts = [""] * len(chunks)
                        st.session_state.current_sentence = 0
                        
                        st.success(f"✅ 断句完成！共 {len(chunks)} 个句子")
                        
                        # 清理主临时文件
                        os.unlink(tmp_path)
                        
                    except Exception as e:
                        st.error(f"处理失败: {str(e)}")
        
        # 使用说明
        with st.expander("📖 使用说明"):
            st.markdown("""
            1. **上传**：选择英语听力音频
            2. **断句**：点击智能断句按钮
            3. **练习**：逐句听写，反复练习
            4. **收藏**：标记难句重点复习
            """)
    
    with col2:
        if st.session_state.sentences:
            st.header("断句结果")
            
            # 导航
            total = len(st.session_state.sentences)
            current = st.session_state.current_sentence
            
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("⬅️ 上一句") and current > 0:
                    st.session_state.current_sentence -= 1
                    st.rerun()
            
            with col_nav2:
                selected = st.selectbox(
                    "选择句子",
                    range(total),
                    index=current,
                    format_func=lambda x: f"句子 {x+1}",
                    label_visibility="collapsed"
                )
                if selected != current:
                    st.session_state.current_sentence = selected
                    st.rerun()
            
            with col_nav3:
                if st.button("➡️ 下一句") and current < total - 1:
                    st.session_state.current_sentence += 1
                    st.rerun()
            
            # 当前句子
            sentence = st.session_state.sentences[current]
            
            st.markdown(f"""
            <div class="sentence-card">
                <b>句子 {current + 1}</b> | 时长: {sentence['duration']:.1f}秒
            </div>
            """, unsafe_allow_html=True)
            
            # 播放音频
            if os.path.exists(sentence['path']):
                with open(sentence['path'], 'rb') as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
            
            # 听写区域
            transcript = st.text_area(
                "听写内容",
                value=st.session_state.transcripts[current],
                height=150,
                placeholder="写下你听到的内容..."
            )
            
            if transcript != st.session_state.transcripts[current]:
                st.session_state.transcripts[current] = transcript
            
            # 收藏按钮
            col_fav1, col_fav2 = st.columns([3, 1])
            with col_fav2:
                if current in st.session_state.difficult_sentences:
                    if st.button("⭐ 已收藏", type="secondary"):
                        st.session_state.difficult_sentences.remove(current)
                        st.rerun()
                else:
                    if st.button("☆ 收藏"):
                        st.session_state.difficult_sentences.add(current)
                        st.rerun()
        
        else:
            st.info("👈 请先上传音频并进行断句")

with tab2:
    if st.session_state.sentences:
        st.header("听写练习")
        
        # 练习控制
        current = st.session_state.current_sentence
        sentence = st.session_state.sentences[current]
        
        # 播放控制
        col_play1, col_play2 = st.columns([4, 1])
        with col_play1:
            if os.path.exists(sentence['path']):
                with open(sentence['path'], 'rb') as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
        
        with col_play2:
            if st.button("🔁 重播"):
                pass
        
        # 听写输入
        user_input = st.text_area(
            "你的答案",
            height=100,
            key=f"practice_{current}"
        )
        
        # 控制按钮
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("提交", type="primary"):
                if user_input:
                    st.session_state.transcripts[current] = user_input
                    st.success("已保存！")
        
        with col_btn2:
            if st.button("下一句") and current < total - 1:
                st.session_state.current_sentence += 1
                st.rerun()
        
        with col_btn3:
            if st.button("完成练习"):
                st.balloons()
                st.success("练习完成！")
        
        # 进度
        completed = sum(1 for t in st.session_state.transcripts if t.strip())
        total = len(st.session_state.transcripts)
        st.progress(completed / total if total > 0 else 0)
        st.caption(f"进度: {completed}/{total}")
    
    else:
        st.info("请先上传音频并进行断句")

# 底部信息
st.divider()
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>英语听力精听助手 | Streamlit 版本 | 本地运行，保护隐私</p>
</div>
""", unsafe_allow_html=True)
