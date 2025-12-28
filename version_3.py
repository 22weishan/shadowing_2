import streamlit as st
import tempfile
import os
import json
import io
import base64

# 页面配置
st.set_page_config(
    page_title="英语听力练习工具",
    page_icon="🎧",
    layout="wide"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sentence-card {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🎧 英语听力练习工具</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align: center; color: #666; margin-bottom: 2rem;">手动分割 · 逐句练习 · 高效提升</div>', unsafe_allow_html=True)

# 初始化session state
def init_session():
    defaults = {
        'audio_file': None,
        'audio_name': '',
        'sentences': [],  # 每句的内容和开始时间
        'current_sentence': 0,
        'transcripts': [],
        'playback_speed': 1.0,
        'audio_bytes': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 播放设置
    st.session_state.playback_speed = st.select_slider(
        "播放速度",
        options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
        value=1.0
    )
    
    st.divider()
    
    # 操作按钮
    if st.button("🔄 重置所有", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_session()
        st.rerun()
    
    if st.button("📊 导出进度", use_container_width=True):
        if st.session_state.transcripts:
            data = {
                "audio": st.session_state.audio_name,
                "transcripts": st.session_state.transcripts
            }
            st.download_button(
                "下载数据",
                json.dumps(data, indent=2, ensure_ascii=False),
                "listening_progress.json",
                "application/json"
            )

# 主界面 - 两个标签页
tab1, tab2 = st.tabs(["📁 上传音频", "🎵 句子练习"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("1. 上传音频")
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择音频文件",
            type=["mp3", "wav", "m4a"],
            help="支持MP3, WAV, M4A格式"
        )
        
        if uploaded_file:
            # 保存音频数据
            st.session_state.audio_file = uploaded_file
            st.session_state.audio_name = uploaded_file.name
            st.session_state.audio_bytes = uploaded_file.getvalue()
            
            st.success(f"✅ {uploaded_file.name}")
            
            # 播放完整音频
            st.audio(st.session_state.audio_bytes, format=f"audio/{uploaded_file.type.split('/')[-1]}")
            
            # 手动分割设置
            st.header("2. 手动分割")
            
            if st.button("✂️ 手动添加句子", type="primary"):
                if 'sentences' not in st.session_state or not st.session_state.sentences:
                    st.session_state.sentences = []
                    st.session_state.transcripts = []
                
                # 添加新句子
                new_sentence = {
                    "id": len(st.session_state.sentences),
                    "name": f"句子 {len(st.session_state.sentences) + 1}",
                    "start_time": 0,
                    "end_time": 0
                }
                st.session_state.sentences.append(new_sentence)
                st.session_state.transcripts.append("")
                st.rerun()
            
            # 显示已分割的句子
            if st.session_state.sentences:
                st.subheader(f"已分割 {len(st.session_state.sentences)} 个句子")
                
                for i, sentence in enumerate(st.session_state.sentences):
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.write(f"📝 {sentence['name']}")
                    with cols[1]:
                        if st.button("编辑", key=f"edit_{i}"):
                            st.session_state.current_sentence = i
                            st.rerun()
        
        # 使用说明
        with st.expander("📖 使用说明", expanded=True):
            st.markdown("""
            ### 使用步骤：
            
            1. **上传音频** - 选择你的英语听力材料
            2. **手动分割** - 点击"手动添加句子"按钮
            3. **设置时间** - 为每个句子设置起止时间
            4. **开始练习** - 逐句进行听写练习
            
            ### 练习方法：
            
            **第一遍**：完整听一遍，了解大意
            **第二遍**：逐句精听，写下听到的内容
            **第三遍**：对照检查，分析错误
            **第四遍**：跟读模仿，练习发音
            """)
    
    with col2:
        if st.session_state.audio_file and st.session_state.sentences:
            st.header("3. 编辑句子时间")
            
            current_idx = st.session_state.current_sentence
            sentence = st.session_state.sentences[current_idx]
            
            # 句子信息
            st.markdown(f"""
            <div class="sentence-card">
                <b>{sentence['name']}</b> - 编辑起止时间
            </div>
            """, unsafe_allow_html=True)
            
            # 时间设置
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                start_time = st.number_input(
                    "开始时间(秒)",
                    min_value=0.0,
                    max_value=1000.0,
                    value=float(sentence.get('start_time', 0)),
                    step=0.5,
                    key=f"start_{current_idx}"
                )
            
            with col_time2:
                end_time = st.number_input(
                    "结束时间(秒)",
                    min_value=0.0,
                    max_value=1000.0,
                    value=float(sentence.get('end_time', 10)),
                    step=0.5,
                    key=f"end_{current_idx}"
                )
            
            # 更新句子时间
            if start_time != sentence.get('start_time', 0) or end_time != sentence.get('end_time', 10):
                sentence['start_time'] = start_time
                sentence['end_time'] = end_time
                sentence['duration'] = end_time - start_time
            
            # 控制按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("⬅️ 上一句") and current_idx > 0:
                    st.session_state.current_sentence = current_idx - 1
                    st.rerun()
            
            with col_btn2:
                st.write(f"第 {current_idx + 1}/{len(st.session_state.sentences)} 句")
            
            with col_btn3:
                if st.button("➡️ 下一句") and current_idx < len(st.session_state.sentences) - 1:
                    st.session_state.current_sentence = current_idx + 1
                    st.rerun()
            
            # 删除按钮
            if st.button("🗑️ 删除此句", type="secondary"):
                st.session_state.sentences.pop(current_idx)
                st.session_state.transcripts.pop(current_idx)
                # 重新编号
                for i, s in enumerate(st.session_state.sentences):
                    s['id'] = i
                    s['name'] = f"句子 {i + 1}"
                if current_idx >= len(st.session_state.sentences):
                    st.session_state.current_sentence = len(st.session_state.sentences) - 1
                st.rerun()
            
            # 显示所有句子
            if st.session_state.sentences:
                st.subheader("所有句子列表")
                
                for i, s in enumerate(st.session_state.sentences):
                    is_current = i == current_idx
                    bg_color = "#e3f2fd" if is_current else "transparent"
                    
                    cols = st.columns([1, 2, 1])
                    with cols[0]:
                        st.markdown(f"**{s['name']}**")
                    with cols[1]:
                        duration = s.get('duration', 0)
                        st.write(f"{s.get('start_time', 0):.1f}s - {s.get('end_time', 0):.1f}s ({duration:.1f}s)")
                    with cols[2]:
                        if st.button("选择", key=f"select_{i}"):
                            st.session_state.current_sentence = i
                            st.rerun()
        
        elif st.session_state.audio_file:
            st.info("👆 请先点击'手动添加句子'按钮来分割音频")
        
        else:
            st.info("👈 请先上传音频文件")

with tab2:
    if st.session_state.audio_file and st.session_state.sentences:
        st.header("🎯 听写练习")
        
        current_idx = st.session_state.current_sentence
        sentence = st.session_state.sentences[current_idx]
        
        # 显示当前句子信息
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("当前句子", sentence['name'])
        with col_info2:
            duration = sentence.get('duration', 0)
            st.metric("时长", f"{duration:.1f}秒")
        with col_info3:
            speed = st.session_state.playback_speed
            st.metric("播放速度", f"{speed}倍")
        
        # 播放说明
        st.info("💡 提示：由于技术限制，本版本需要您手动控制音频播放器定位到指定时间")
        st.write(f"**请将音频播放器定位到：{sentence.get('start_time', 0):.1f}秒**")
        
        # 播放完整音频（用户手动控制时间）
        st.audio(st.session_state.audio_bytes, format=f"audio/{st.session_state.audio_file.type.split('/')[-1]}")
        
        # 听写区域
        st.subheader("✍️ 听写内容")
        transcript = st.text_area(
            "写下你听到的内容：",
            value=st.session_state.transcripts[current_idx],
            height=150,
            placeholder="仔细听音频，写下完整的句子...",
            key=f"write_{current_idx}"
        )
        
        # 保存听写内容
        if transcript != st.session_state.transcripts[current_idx]:
            st.session_state.transcripts[current_idx] = transcript
        
        # 练习控制
        col_control1, col_control2, col_control3 = st.columns(3)
        with col_control1:
            if st.button("✅ 保存并继续", type="primary"):
                if current_idx < len(st.session_state.sentences) - 1:
                    st.session_state.current_sentence = current_idx + 1
                    st.success("已保存！")
                    st.rerun()
                else:
                    st.balloons()
                    st.success("🎉 恭喜完成所有句子！")
        
        with col_control2:
            if st.button("🔁 重练此句"):
                st.rerun()
        
        with col_control3:
            if st.button("📋 查看进度"):
                completed = sum(1 for t in st.session_state.transcripts if t.strip())
                total = len(st.session_state.transcripts)
                st.info(f"完成进度: {completed}/{total} ({completed/total*100:.0f}%)")
        
        # 导航栏
        st.subheader("📝 快速导航")
        
        # 显示所有句子的按钮
        cols = st.columns(6)
        for i in range(min(len(st.session_state.sentences), 12)):
            with cols[i % 6]:
                is_current = i == current_idx
                has_transcript = st.session_state.transcripts[i].strip() != ""
                
                label = f"{i+1}"
                if has_transcript:
                    label = f"✅ {label}"
                
                if st.button(
                    label,
                    key=f"nav_{i}",
                    type="primary" if is_current else "secondary",
                    use_container_width=True
                ):
                    st.session_state.current_sentence = i
                    st.rerun()
        
        if len(st.session_state.sentences) > 12:
            st.caption(f"... 还有 {len(st.session_state.sentences) - 12} 个句子")
        
        # 进度统计
        st.divider()
        completed = sum(1 for t in st.session_state.transcripts if t.strip())
        total = len(st.session_state.transcripts)
        
        col_prog1, col_prog2 = st.columns([3, 1])
        with col_prog1:
            st.progress(completed / total if total > 0 else 0)
        with col_prog2:
            st.metric("完成度", f"{completed}/{total}")
    
    elif st.session_state.audio_file:
        st.info("请先在'上传音频'页面分割句子")
    
    else:
        st.info("请先上传音频文件")

# 底部信息
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🎧 英语听力练习工具 | 简易版 | 零依赖，快速启动</p>
    <p>💡 提示：本工具完全在浏览器中运行，不保存任何数据到服务器</p>
</div>
""", unsafe_allow_html=True)
