import streamlit as st
import whisper
import tempfile
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import numpy as np
import json
import time

# 页面配置
st.set_page_config(
    page_title="英语听力精听助手",
    page_icon="🎧",
    layout="wide"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sentence-card {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
        background-color: #f8f9fa;
    }
    .sentence-number {
        font-weight: bold;
        color: #1E88E5;
        margin-right: 10px;
    }
    .stAudio {
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎧 英语听力精听助手</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">上传音频，智能断句，高效精听</div>', unsafe_allow_html=True)

# 初始化session state
if 'sentences' not in st.session_state:
    st.session_state.sentences = []
if 'current_sentence' not in st.session_state:
    st.session_state.current_sentence = 0
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []

# 侧边栏 - 功能选择
with st.sidebar:
    st.header("功能设置")
    
    # 断句设置
    st.subheader("断句参数")
    min_silence_len = st.slider("最小静音长度(ms)", 300, 1500, 500, 50)
    silence_thresh = st.slider("静音阈值(dBFS)", -60, -20, -40, 5)
    
    # 播放设置
    st.subheader("播放设置")
    repeat_count = st.selectbox("单句重复次数", [1, 2, 3, 5, 8], index=0)
    auto_pause = st.checkbox("句末自动暂停", value=True)
    
    # 功能按钮
    st.subheader("功能操作")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎵 重置", use_container_width=True):
            st.session_state.sentences = []
            st.session_state.current_sentence = 0
            st.session_state.transcripts = []
            st.rerun()
    
    with col2:
        if st.button("💾 导出", use_container_width=True):
            if st.session_state.sentences:
                # 创建导出数据
                export_data = {
                    "sentences": st.session_state.sentences,
                    "transcripts": st.session_state.transcripts
                }
                st.download_button(
                    label="下载JSON",
                    data=json.dumps(export_data, indent=2, ensure_ascii=False),
                    file_name="listening_data.json",
                    mime="application/json"
                )
            else:
                st.warning("没有可导出的数据")

# 主界面 - 两个标签页
tab1, tab2 = st.tabs(["📁 上传与断句", "🎵 听写练习"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("1. 上传音频")
        
        # 上传方式选择
        upload_method = st.radio("选择上传方式", ["本地文件", "URL链接"], horizontal=True)
        
        if upload_method == "本地文件":
            audio_file = st.file_uploader(
                "上传音频文件",
                type=["mp3", "wav", "m4a", "ogg", "flac"],
                help="支持 MP3, WAV, M4A, OGG, FLAC 格式"
            )
            
            if audio_file is not None:
                # 保存临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    tmp_file.write(audio_file.getvalue())
                    audio_path = tmp_file.name
                
                try:
                    # 加载音频
                    audio = AudioSegment.from_file(audio_path)
                    st.session_state.audio_data = audio
                    
                    # 显示音频信息
                    duration = len(audio) / 1000  # 转换为秒
                    st.success(f"✅ 上传成功！")
                    st.info(f"**音频信息**: {audio_file.name}")
                    st.info(f"**时长**: {duration:.1f}秒")
                    st.info(f"**采样率**: {audio.frame_rate}Hz")
                    st.info(f"**声道**: {audio.channels}")
                    
                    # 播放完整音频
                    st.audio(audio_file, format="audio/mp3")
                    
                except Exception as e:
                    st.error(f"音频加载失败: {str(e)}")
                finally:
                    # 清理临时文件
                    if os.path.exists(audio_path):
                        os.unlink(audio_path)
        
        else:  # URL方式
            url = st.text_input("输入音频URL", placeholder="https://example.com/audio.mp3")
            if st.button("从URL导入", use_container_width=True) and url:
                st.info("URL导入功能正在开发中...")
        
        # 断句按钮
        st.header("2. 智能断句")
        if st.session_state.audio_data is not None:
            if st.button("🔍 开始智能断句", use_container_width=True, type="primary"):
                with st.spinner("正在分析音频并断句..."):
                    try:
                        # 使用静音检测进行断句
                        audio = st.session_state.audio_data
                        chunks = split_on_silence(
                            audio,
                            min_silence_len=min_silence_len,
                            silence_thresh=silence_thresh,
                            keep_silence=100  # 保留100ms静音
                        )
                        
                        # 保存断句结果
                        st.session_state.sentences = []
                        st.session_state.transcripts = []
                        
                        for i, chunk in enumerate(chunks):
                            # 保存为临时文件用于播放
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                                chunk.export(tmp.name, format="mp3")
                                sentence_data = {
                                    "id": i,
                                    "audio_path": tmp.name,
                                    "duration": len(chunk) / 1000,
                                    "start_time": (chunk.start_time if hasattr(chunk, 'start_time') else 0),
                                    "end_time": (chunk.end_time if hasattr(chunk, 'end_time') else 0)
                                }
                                st.session_state.sentences.append(sentence_data)
                                st.session_state.transcripts.append("")  # 空白的听写区域
                        
                        st.success(f"✅ 断句完成！共分割出 {len(chunks)} 个句子")
                        
                    except Exception as e:
                        st.error(f"断句失败: {str(e)}")
        
        # 手动调整断句
        if st.session_state.sentences:
            st.header("3. 手动调整")
            st.write(f"当前有 {len(st.session_state.sentences)} 个句子")
            
            # 合并短句选项
            if st.checkbox("显示合并选项"):
                sentence_to_merge = st.selectbox(
                    "选择要合并的句子",
                    range(len(st.session_state.sentences)),
                    format_func=lambda x: f"句子 {x+1}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("与前句合并", use_container_width=True):
                        st.info("合并功能开发中...")
                with col2:
                    if st.button("与后句合并", use_container_width=True):
                        st.info("合并功能开发中...")
    
    with col2:
        # 显示断句结果
        if st.session_state.sentences:
            st.header("断句结果预览")
            
            # 句子导航
            cols = st.columns([2, 1, 1])
            with cols[0]:
                sentence_index = st.selectbox(
                    "跳转到句子",
                    range(len(st.session_state.sentences)),
                    format_func=lambda x: f"句子 {x+1} (时长: {st.session_state.sentences[x]['duration']:.1f}s)",
                    key="sentence_selector"
                )
                st.session_state.current_sentence = sentence_index
            
            with cols[1]:
                if st.button("⬅️ 上一句", use_container_width=True):
                    if st.session_state.current_sentence > 0:
                        st.session_state.current_sentence -= 1
                    st.rerun()
            
            with cols[2]:
                if st.button("➡️ 下一句", use_container_width=True):
                    if st.session_state.current_sentence < len(st.session_state.sentences) - 1:
                        st.session_state.current_sentence += 1
                    st.rerun()
            
            # 显示当前句子
            current = st.session_state.sentences[st.session_state.current_sentence]
            
            st.markdown(f"""
            <div class="sentence-card">
                <span class="sentence-number">句子 {st.session_state.current_sentence + 1}</span>
                <span>时长: {current['duration']:.1f}秒</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 播放当前句子
            if os.path.exists(current['audio_path']):
                with open(current['audio_path'], 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                
                # 重复播放控制
                for i in range(repeat_count):
                    st.audio(audio_bytes, format="audio/mp3")
                    if i < repeat_count - 1:
                        st.caption(f"重复播放 ({i+1}/{repeat_count})")
            
            # 听写输入框
            st.subheader("听写区域")
            transcript = st.text_area(
                "在这里输入你听到的内容",
                value=st.session_state.transcripts[st.session_state.current_sentence],
                height=150,
                key=f"transcript_{st.session_state.current_sentence}",
                placeholder="逐句听写你听到的内容..."
            )
            
            # 保存听写内容
            if transcript != st.session_state.transcripts[st.session_state.current_sentence]:
                st.session_state.transcripts[st.session_state.current_sentence] = transcript
            
            # 显示所有句子列表
            with st.expander("📋 查看所有句子", expanded=False):
                for i, sentence in enumerate(st.session_state.sentences):
                    is_current = i == st.session_state.current_sentence
                    bg_color = "#e3f2fd" if is_current else "white"
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="background-color:{bg_color}; padding:10px; border-radius:5px; margin:5px 0;">
                            <b>{'▶️' if is_current else ''} 句子 {i+1}</b> 
                            (时长: {sentence['duration']:.1f}s)
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("播放", key=f"play_{i}", use_container_width=True):
                            st.session_state.current_sentence = i
                            st.rerun()
        
        else:
            st.info("👈 请先上传音频并进行断句")
            st.image("https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=800&auto=format&fit=crop", 
                    caption="高效英语精听练习")

with tab2:
    if st.session_state.sentences:
        st.header("🎯 听写练习模式")
        
        # 练习设置
        col1, col2, col3 = st.columns(3)
        with col1:
            practice_mode = st.selectbox("练习模式", ["顺序练习", "随机练习", "难句复习"])
        with col2:
            show_transcript = st.checkbox("显示原文", value=False)
        with col3:
            if st.button("开始练习", type="primary", use_container_width=True):
                st.session_state.current_sentence = 0
        
        # 练习界面
        if st.session_state.sentences:
            current = st.session_state.sentences[st.session_state.current_sentence]
            
            # 音频播放区域
            st.audio(current['audio_path'], format="audio/mp3")
            
            # 听写输入
            user_input = st.text_area(
                "听写内容",
                height=100,
                placeholder="在这里写下你听到的内容..."
            )
            
            # 控制按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔁 重新播放", use_container_width=True):
                    st.rerun()
            
            with col2:
                if st.button("✅ 提交", type="primary", use_container_width=True):
                    st.success("提交成功！")
                    # 这里可以添加对比原文的功能
            
            with col3:
                if st.button("➡️ 下一句", use_container_width=True):
                    if st.session_state.current_sentence < len(st.session_state.sentences) - 1:
                        st.session_state.current_sentence += 1
                    st.rerun()
            
            # 显示原文（可选）
            if show_transcript and 'transcript' in current:
                with st.expander("查看原文"):
                    st.write(current.get('transcript', '暂无原文'))
    
    else:
        st.info("请先上传音频并进行断句，然后开始听写练习")
        st.markdown("""
        ### 精听练习步骤：
        1. 上传英语音频文件
        2. 使用智能断句功能分割句子
        3. 逐句听写练习
        4. 对比原文，找出薄弱点
        5. 重复练习难句
        """)

# 底部信息
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>🎧 英语听力精听助手 | 基于 Streamlit + Python 构建</p>
    <p>功能持续开发中，欢迎反馈建议！</p>
</div>
""", unsafe_allow_html=True)
