import streamlit as st
import tempfile
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import json
import base64

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
    .highlight {
        background-color: #fffacd;
        padding: 2px 4px;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎧 英语听力精听助手</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">上传音频，智能断句，高效精听</div>', unsafe_allow_html=True)

# 初始化session state
def init_session_state():
    defaults = {
        'sentences': [],
        'current_sentence': 0,
        'audio_data': None,
        'audio_name': '',
        'transcripts': [],
        'difficult_sentences': set(),
        'playback_speed': 1.0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# 音频处理函数
def process_audio_file(uploaded_file):
    """处理上传的音频文件"""
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # 加载音频
        audio = AudioSegment.from_file(tmp_path)
        
        # 保存到session state
        st.session_state.audio_data = audio
        st.session_state.audio_name = uploaded_file.name
        
        return audio, tmp_path
        
    except Exception as e:
        st.error(f"音频处理失败: {str(e)}")
        return None, None

def split_audio_into_sentences(audio, min_silence_len=500, silence_thresh=-40):
    """将音频分割成句子"""
    try:
        # 使用静音检测进行断句
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=100
        )
        
        sentences = []
        temp_files = []
        
        for i, chunk in enumerate(chunks):
            # 保存每个句子为临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                chunk.export(tmp.name, format="mp3", bitrate="128k")
                
                sentence_data = {
                    "id": i,
                    "audio_path": tmp.name,
                    "duration": len(chunk) / 1000,
                    "start_time": getattr(chunk, 'start_time', 0),
                    "end_time": getattr(chunk, 'end_time', len(chunk))
                }
                sentences.append(sentence_data)
                temp_files.append(tmp.name)
        
        return sentences, temp_files
        
    except Exception as e:
        st.error(f"断句失败: {str(e)}")
        return [], []

def get_audio_duration(audio):
    """获取音频时长"""
    return len(audio) / 1000

def clean_temp_files(file_paths):
    """清理临时文件"""
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.unlink(path)
            except:
                pass

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 断句设置
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
    repeat_count = st.selectbox("单句重复次数", [1, 2, 3, 5, 8], index=0)
    
    st.markdown("---")
    
    # 功能按钮
    st.subheader("🛠️ 工具")
    if st.button("🗑️ 重置所有", use_container_width=True):
        # 清理临时文件
        for sentence in st.session_state.sentences:
            if 'audio_path' in sentence and os.path.exists(sentence['audio_path']):
                os.unlink(sentence['audio_path'])
        
        # 重置session state
        for key in ['sentences', 'current_sentence', 'audio_data', 'transcripts', 'difficult_sentences']:
            if key in st.session_state:
                st.session_state[key] = [] if key in ['sentences', 'transcripts'] else 0 if key == 'current_sentence' else None
        
        st.rerun()
    
    if st.button("📥 导出数据", use_container_width=True):
        if st.session_state.sentences:
            export_data = {
                "audio_name": st.session_state.audio_name,
                "total_sentences": len(st.session_state.sentences),
                "sentences": [
                    {
                        "id": s["id"],
                        "duration": s["duration"],
                        "transcript": st.session_state.transcripts[i] if i < len(st.session_state.transcripts) else ""
                    }
                    for i, s in enumerate(st.session_state.sentences)
                ],
                "difficult_sentences": list(st.session_state.difficult_sentences)
            }
            
            st.download_button(
                label="下载JSON数据",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name=f"{st.session_state.audio_name}_listening.json",
                mime="application/json"
            )

# 主界面
tab1, tab2, tab3 = st.tabs(["📁 上传音频", "🎵 精听练习", "⭐ 收藏夹"])

# Tab 1: 上传音频
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("1. 上传音频文件")
        
        uploaded_file = st.file_uploader(
            "选择音频文件",
            type=["mp3", "wav", "m4a", "ogg"],
            help="支持 MP3, WAV, M4A, OGG 格式"
        )
        
        if uploaded_file is not None:
            if st.session_state.audio_data is None or st.session_state.audio_name != uploaded_file.name:
                with st.spinner("正在处理音频..."):
                    audio, temp_path = process_audio_file(uploaded_file)
                    
                    if audio:
                        st.success(f"✅ {uploaded_file.name} 加载成功！")
                        
                        # 显示音频信息
                        duration = get_audio_duration(audio)
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.metric("音频时长", f"{duration:.1f}秒")
                        with col_info2:
                            st.metric("采样率", f"{audio.frame_rate}Hz")
                        
                        # 播放完整音频
                        st.audio(uploaded_file, format=f"audio/{uploaded_file.type.split('/')[-1]}")
            
            # 断句按钮
            st.header("2. 智能断句")
            if st.button("🔍 开始断句分析", type="primary", use_container_width=True):
                if st.session_state.audio_data:
                    with st.spinner("正在分析音频并断句..."):
                        # 清理之前的临时文件
                        for sentence in st.session_state.sentences:
                            if 'audio_path' in sentence and os.path.exists(sentence['audio_path']):
                                os.unlink(sentence['audio_path'])
                        
                        sentences, _ = split_audio_into_sentences(
                            st.session_state.audio_data,
                            min_silence_len,
                            silence_thresh
                        )
                        
                        if sentences:
                            st.session_state.sentences = sentences
                            st.session_state.transcripts = [""] * len(sentences)
                            st.session_state.current_sentence = 0
                            
                            st.success(f"✅ 断句完成！共分割出 {len(sentences)} 个句子")
                            st.rerun()
                        else:
                            st.error("未能检测到有效句子")
                else:
                    st.warning("请先上传音频文件")
        
        # 使用示例
        with st.expander("📚 使用说明", expanded=False):
            st.markdown("""
            ### 使用方法：
            1. **上传音频**：选择要练习的英语听力材料
            2. **智能断句**：自动将长音频分割成句子
            3. **精听练习**：逐句听写，反复练习
            4. **标记难句**：将难句加入收藏夹重点复习
            
            ### 推荐练习步骤：
            - 第一遍：完整听一遍，了解大意
            - 第二遍：逐句精听，写下听到的内容
            - 第三遍：对照原文，检查错误
            - 第四遍：重点练习难句，反复跟读
            """)
    
    with col2:
        if st.session_state.sentences:
            st.header("📋 断句结果")
            
            # 进度显示
            total = len(st.session_state.sentences)
            current = st.session_state.current_sentence + 1
            progress = current / total
            
            st.progress(progress, text=f"进度: {current}/{total} 句")
            
            # 导航控制
            col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 2, 1])
            with col_nav1:
                if st.button("⏮️ 第一句", use_container_width=True):
                    st.session_state.current_sentence = 0
                    st.rerun()
            
            with col_nav2:
                if st.button("⬅️ 上一句", use_container_width=True):
                    if st.session_state.current_sentence > 0:
                        st.session_state.current_sentence -= 1
                    st.rerun()
            
            with col_nav3:
                sentence_idx = st.selectbox(
                    "快速跳转",
                    range(total),
                    index=st.session_state.current_sentence,
                    format_func=lambda x: f"句子 {x+1} ({st.session_state.sentences[x]['duration']:.1f}s)",
                    label_visibility="collapsed"
                )
                if sentence_idx != st.session_state.current_sentence:
                    st.session_state.current_sentence = sentence_idx
                    st.rerun()
            
            with col_nav4:
                if st.button("➡️ 下一句", use_container_width=True):
                    if st.session_state.current_sentence < total - 1:
                        st.session_state.current_sentence += 1
                    st.rerun()
            
            # 当前句子详情
            current_sentence = st.session_state.sentences[st.session_state.current_sentence]
            
            st.markdown(f"""
            <div class="sentence-card">
                <span class="sentence-number">句子 {st.session_state.current_sentence + 1}</span>
                <span>时长: {current_sentence['duration']:.1f}秒 | </span>
                <span>速度: {st.session_state.playback_speed}倍</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 播放控制
            col_play1, col_play2 = st.columns([3, 1])
            with col_play1:
                if os.path.exists(current_sentence['audio_path']):
                    with open(current_sentence['audio_path'], 'rb') as f:
                        audio_bytes = f.read()
                    
                    # 播放音频
                    st.audio(audio_bytes, format="audio/mp3")
            
            with col_play2:
                is_difficult = st.session_state.current_sentence in st.session_state.difficult_sentences
                button_text = "⭐ 已收藏" if is_difficult else "☆ 收藏难句"
                if st.button(button_text, use_container_width=True):
                    if is_difficult:
                        st.session_state.difficult_sentences.remove(st.session_state.current_sentence)
                    else:
                        st.session_state.difficult_sentences.add(st.session_state.current_sentence)
                    st.rerun()
            
            # 重复播放
            if repeat_count > 1:
                with st.expander(f"🔁 重复播放 ({repeat_count}次)", expanded=True):
                    for i in range(repeat_count):
                        if i > 0:
                            st.caption(f"第 {i+1} 次重复")
                        st.audio(current_sentence['audio_path'], format="audio/mp3")
            
            # 听写区域
            st.subheader("✍️ 听写练习")
            transcript = st.text_area(
                "写下你听到的内容：",
                value=st.session_state.transcripts[st.session_state.current_sentence],
                height=150,
                placeholder="仔细听，逐字写下听到的句子...",
                key=f"transcript_{st.session_state.current_sentence}"
            )
            
            # 保存听写内容
            if transcript != st.session_state.transcripts[st.session_state.current_sentence]:
                st.session_state.transcripts[st.session_state.current_sentence] = transcript
            
            # 显示所有句子缩略图
            st.subheader("📝 所有句子")
            cols = st.columns(5)
            for i in range(min(total, 15)):  # 最多显示15个
                with cols[i % 5]:
                    is_current = i == st.session_state.current_sentence
                    is_difficult = i in st.session_state.difficult_sentences
                    
                    label = f"{'⭐' if is_difficult else ''}{i+1}"
                    if st.button(
                        label,
                        key=f"btn_{i}",
                        use_container_width=True,
                        type="primary" if is_current else "secondary"
                    ):
                        st.session_state.current_sentence = i
                        st.rerun()
            
            if total > 15:
                st.caption(f"... 还有 {total - 15} 个句子")
        
        else:
            st.info("👈 请先上传音频文件并进行断句")
            
            # 显示示例
            st.markdown("""
            ### 🎯 精听练习的好处：
            
            **提高听力理解能力**
            > 通过反复听写，训练耳朵识别英语音素和连读
            
            **增强短期记忆**
            > 逐句听写可以有效锻炼短期记忆能力
            
            **积累地道表达**
            > 接触真实语境中的英语表达方式
            
            **提升拼写准确度**
            > 听写过程中同时练习拼写和语法
            """)

# Tab 2: 精听练习
with tab2:
    if st.session_state.sentences:
        st.header("🎯 精听练习模式")
        
        # 练习设置
        col_set1, col_set2, col_set3 = st.columns(3)
        with col_set1:
            mode = st.selectbox("练习模式", ["顺序练习", "随机练习", "难句优先"])
        with col_set2:
            show_hint = st.checkbox("显示时长提示", value=True)
        with col_set3:
            if st.button("开始新练习", type="primary"):
                st.session_state.current_sentence = 0
                st.rerun()
        
        # 练习界面
        current = st.session_state.sentences[st.session_state.current_sentence]
        
        # 题目区域
        st.markdown("### 请听写以下句子：")
        
        if show_hint:
            st.info(f"句子时长: {current['duration']:.1f}秒 | 播放速度: {st.session_state.playback_speed}倍")
        
        # 播放区域
        col_audio1, col_audio2 = st.columns([4, 1])
        with col_audio1:
            if os.path.exists(current['audio_path']):
                with open(current['audio_path'], 'rb') as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
        
        with col_audio2:
            if st.button("🔁 重播", use_container_width=True):
                st.rerun()
        
        # 听写输入
        user_input = st.text_area(
            "你的听写：",
            height=120,
            placeholder="在这里写下你听到的完整句子..."
        )
        
        # 控制按钮
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            if st.button("⏸️ 暂停", use_container_width=True):
                st.info("练习已暂停")
        
        with col_ctrl2:
            if st.button("✅ 完成听写", type="primary", use_container_width=True):
                if user_input.strip():
                    st.session_state.transcripts[st.session_state.current_sentence] = user_input
                    st.success("听写已保存！")
                else:
                    st.warning("请输入听写内容")
        
        with col_ctrl3:
            if st.button("➡️ 继续下一句", use_container_width=True):
                if st.session_state.current_sentence < len(st.session_state.sentences) - 1:
                    st.session_state.current_sentence += 1
                else:
                    st.balloons()
                    st.success("🎉 恭喜完成所有句子！")
                st.rerun()
        
        # 进度统计
        completed = sum(1 for t in st.session_state.transcripts if t.strip())
        total = len(st.session_state.transcripts)
        if total > 0:
            st.metric("完成进度", f"{completed}/{total}", f"{completed/total*100:.0f}%")
    
    else:
        st.info("请先上传音频并进行断句以开始练习")
        st.markdown("""
        ### 精听练习四步法：
        
        1. **初听理解**：完整听一遍，了解大意
        2. **逐句精听**：一句一停，写下听到的内容
        3. **对照检查**：对比原文，分析错误原因
        4. **跟读模仿**：模仿语音语调，练习发音
        
        ### 每日练习建议：
        - 初级：15-30分钟，10-15个句子
        - 中级：30-45分钟，20-30个句子
        - 高级：45-60分钟，30-40个句子
        """)

# Tab 3: 收藏夹
with tab3:
    st.header("⭐ 我的收藏夹")
    
    if st.session_state.difficult_sentences:
        difficult_list = sorted(list(st.session_state.difficult_sentences))
        
        st.metric("收藏的难句", len(difficult_list))
        
        # 难句列表
        for idx, sentence_id in enumerate(difficult_list):
            if sentence_id < len(st.session_state.sentences):
                sentence = st.session_state.sentences[sentence_id]
                
                col_fav1, col_fav2, col_fav3 = st.columns([1, 4, 1])
                
                with col_fav1:
                    st.markdown(f"**#{idx+1}**")
                
                with col_fav2:
                    st.write(f"句子 {sentence_id+1} | 时长: {sentence['duration']:.1f}s")
                    if sentence_id < len(st.session_state.transcripts):
                        transcript = st.session_state.transcripts[sentence_id]
                        if transcript:
                            st.caption(f"你的听写: {transcript[:50]}..." if len(transcript) > 50 else transcript)
                
                with col_fav3:
                    if st.button("练习", key=f"practice_{sentence_id}", use_container_width=True):
                        st.session_state.current_sentence = sentence_id
                        st.switch_page("🎵 精听练习")
        
        # 批量操作
        st.markdown("---")
        col_batch1, col_batch2 = st.columns(2)
        with col_batch1:
            if st.button("清空收藏夹", type="secondary"):
                st.session_state.difficult_sentences.clear()
                st.rerun()
        
        with col_batch2:
            if st.button("导出收藏夹", type="primary"):
                export_data = {
                    "difficult_sentences": [
                        {
                            "id": s_id,
                            "duration": st.session_state.sentences[s_id]["duration"],
                            "transcript": st.session_state.transcripts[s_id] if s_id < len(st.session_state.transcripts) else ""
                        }
                        for s_id in difficult_list
                    ]
                }
                
                st.download_button(
                    "下载收藏夹数据",
                    json.dumps(export_data, indent=2, ensure_ascii=False),
                    "difficult_sentences.json",
                    "application/json"
                )
    
    else:
        st.info("暂无收藏的难句")
        st.markdown("""
        ### 如何有效使用收藏夹？
        
        1. **标记难点**：在练习过程中遇到难句时点击收藏
        2. **定期复习**：每周回顾收藏的难句
        3. **分析原因**：找出听不懂的原因（词汇、连读、语速等）
        4. **专项突破**：针对性地练习同类难句
        
        > 💡 建议：每天结束时复习当天收藏的难句
        """)

# 底部信息
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🎧 英语听力精听助手 | 版本 1.0 | 基于 Streamlit 构建</p>
    <p>💡 提示：本应用为本地运行，音频数据不会上传到服务器</p>
</div>
""", unsafe_allow_html=True)
