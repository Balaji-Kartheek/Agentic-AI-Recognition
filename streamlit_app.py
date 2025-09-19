import asyncio
import glob
import json
import os
import time
import threading
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# Disable tokenizers parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from config.config import Config
from config.config import config as global_config
from src.app import AvaamoAudioEvaluator
from src.services.evaluation.html_report_service import HTMLReportService
from src.models.types import PATHS
from src.services.conversation.synthetic_run_service import SyntheticRunService
from src.services.conversation.dynamic_run_service import DynamicRunService
from src.services.tts.tts_utils import synthesize_steps, list_speakers


def parse_conversation_ids(raw_text: str) -> List[str]:
    cleaned = [line.strip() for line in raw_text.replace(",", "\n").splitlines()]
    return [c for c in cleaned if c]


def load_latest_test_result(conversation_id: Optional[str] = None) -> Optional[Dict]:
    results_dir = PATHS.TEST_RESULTS
    candidates = sorted(results_dir.glob("test_result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if conversation_id:
        candidates = [p for p in candidates if f"_{conversation_id}_" in p.name]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["__file_path__"] = str(path)
                return data
        except Exception:
            continue
    return None


def list_all_test_results() -> List[Path]:
    return sorted(PATHS.TEST_RESULTS.glob("test_result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def render_test_summary(test_result: Dict):
    def _result_color(value: str) -> str:
        m = {
            'PASS': '#28a745',
            'FAIL': '#dc3545',
            'UNKNOWN': '#6c757d'
        }
        return m.get(value.upper(), '#6c757d')

    result_text = str(test_result.get("scenario_result", "unknown")).upper()
    badge_color = _result_color(result_text)
    st.markdown(
        f"""
        <div style='display:inline-block;padding:6px 14px;border-radius:20px;font-weight:700;color:white;background:{badge_color};margin-bottom:8px;'>
            {result_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cols[0].metric("Result", result_text)
    cols[1].metric("Audio Files", str(test_result.get("metadata", {}).get("audio_files_sent", 0)))
    cols[2].metric("Total Messages", str(test_result.get("metadata", {}).get("total_messages", 0)))
    cols[3].metric("Model", str(test_result.get("metadata", {}).get("evaluation_model", "-")))

    st.markdown("**Scenario:** " + str(test_result.get("scenario", "Unknown")))
    st.markdown("**Test ID:** " + str(test_result.get("test_id", "unknown")))


def generate_and_show_html_report(test_result: Dict):
    result = HTMLReportService.generate_html_report(test_result)
    if not result.get("success"):
        st.error(f"Failed to generate HTML report: {result.get('error')}")
        return
    html_path = result["filepath"]
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.success(f"HTML report generated: {html_path}")
        st.download_button("Download HTML Report", data=html_content, file_name=Path(html_path).name, mime="text/html")
        st.components.v1.html(html_content, height=900, scrolling=True)
    except Exception as error:
        st.error(f"Unable to display HTML report: {error}")


def create_config_from_inputs(widget_suffix: str = "") -> Config:
    cfg = Config()
    cfg.access_token = st.session_state.get(f"access_token_{widget_suffix}", cfg.access_token)
    cfg.channel_id = st.session_state.get(f"channel_id_{widget_suffix}", cfg.channel_id)
    cfg.base_url = st.session_state.get(f"base_url_{widget_suffix}", cfg.base_url)
    cfg.ws_url = st.session_state.get(f"ws_url_{widget_suffix}", cfg.ws_url)
    cfg.conversation_mode = st.session_state.get(f"conversation_mode_{widget_suffix}", getattr(cfg, "conversation_mode", "voice"))
    cfg.llm_model = st.session_state.get(f"llm_model_{widget_suffix}", cfg.llm_model)
    # Synthetic fields populated later only for Synthetic tab

    raw_conv = st.session_state.get(f"conversation_ids_raw_{widget_suffix}", "")
    parsed = parse_conversation_ids(raw_conv) if raw_conv else cfg.conversation_ids
    cfg.conversation_ids = parsed if parsed else cfg.conversation_ids
    cfg.conversation_id = cfg.conversation_ids[0]

    # Mirror into global config for components that rely on it (e.g., WebSocketService)
    global_config.access_token = cfg.access_token
    global_config.channel_id = cfg.channel_id
    global_config.base_url = cfg.base_url
    global_config.ws_url = cfg.ws_url
    global_config.conversation_mode = cfg.conversation_mode
    global_config.llm_model = cfg.llm_model
    # run_type is set by the page/tab handler below
    return cfg


def run_evaluator(cfg: Config) -> Dict:
    app = AvaamoAudioEvaluator(cfg)
    return asyncio.run(app.run())


def tail_file(path: Path, max_lines: int = 300) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            dq = deque(f, maxlen=max_lines)
        return ''.join(dq)
    except Exception:
        return ''


def start_background_run(cfg: Config, widget_suffix: str = ""):
    if f'runner_{widget_suffix}' in st.session_state and st.session_state[f'runner_{widget_suffix}'] is not None:
        runner = st.session_state[f'runner_{widget_suffix}']
        if runner.is_alive():
            st.warning('A run is already in progress.')
            return

    # Clear app.log before starting a fresh run so Live App Log shows only current run
    try:
        log_path = PATHS.LOGS / 'app.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'w', encoding='utf-8'):
            pass
    except Exception:
        # Do not fail run if log clearance fails
        pass

    # Create/attach a cancellation event for cooperative stop
    try:
        import threading as _threading
        stop_event = _threading.Event()
    except Exception:
        stop_event = None

    if stop_event is not None:
        setattr(cfg, 'cancel_event', stop_event)
        st.session_state[f'stop_event_{widget_suffix}'] = stop_event

    st.session_state[f'run_in_progress_{widget_suffix}'] = True
    st.session_state[f'run_start_ts_{widget_suffix}'] = time.time()
    st.session_state[f'run_result_{widget_suffix}'] = None
    st.session_state[f'run_error_{widget_suffix}'] = None

    def _worker():
        try:
            result = run_evaluator(cfg)
            st.session_state[f'run_result_{widget_suffix}'] = result
        except Exception as e:
            st.session_state[f'run_error_{widget_suffix}'] = str(e)
        finally:
            st.session_state[f'run_in_progress_{widget_suffix}'] = False

    t = threading.Thread(target=_worker, daemon=True)
    st.session_state[f'runner_{widget_suffix}'] = t
    t.start()


def page_run(title: str = "Run Evaluation"):
    st.subheader(title)

    # Use defaults from config; allow overrides in UI
    cfg_defaults = global_config
    model_options = ["gpt-4o", "gpt-4o-mini", "gpt-4.1"]
    widget_suffix = title.lower().replace(' ', '_')
    default_model = st.session_state.get(f"llm_model_{widget_suffix}", cfg_defaults.llm_model)
    model_index = model_options.index(default_model) if default_model in model_options else 0

    is_synth = title.lower().startswith("synthetic")
    is_dynamic = title.lower().startswith("dynamic")
    is_translation = title.lower().startswith("translation")

    # Human tab form only
    submitted = False
    if not (is_synth or is_dynamic or is_translation):
        form_key = f"run_form_{title.lower().replace(' ', '_')}"
        with st.form(form_key):
            st.text_input("Channel ID", key=f"channel_id_{widget_suffix}", value=st.session_state.get(f"channel_id_{widget_suffix}", cfg_defaults.channel_id))
            st.text_input("Base URL", key=f"base_url_{widget_suffix}", value=st.session_state.get(f"base_url_{widget_suffix}", cfg_defaults.base_url))
            st.text_input("WebSocket URL", key=f"ws_url_{widget_suffix}", value=st.session_state.get(f"ws_url_{widget_suffix}", cfg_defaults.ws_url))
            st.text_area(
                "Conversation IDs (comma or newline separated)",
                key=f"conversation_ids_raw_{widget_suffix}",
                height=90,
                value=st.session_state.get(f"conversation_ids_raw_{widget_suffix}", "\n".join(cfg_defaults.conversation_ids)),
            )
            st.selectbox("LLM Model", model_options, key=f"llm_model_{widget_suffix}", index=model_index)
            submitted = st.form_submit_button("Start Run")

    if submitted:
        cfg = create_config_from_inputs(widget_suffix)
        cfg.run_type = "human"

        if not cfg.access_token or not cfg.channel_id or not cfg.base_url:
            st.error("Missing required configuration: access token, channel id, or base url")
            return

        start_background_run(cfg, widget_suffix)

    # Synthetic steps tools (only for Synthetic tab) - show FIRST on the page
    if is_synth:
        # Channel ID input
        st.text_input(
            "Channel ID",
            key=f"channel_id_{widget_suffix}",
            value=st.session_state.get(f"channel_id_{widget_suffix}", "".join(global_config.channel_id))
        )
        # Mode selection for synthetic run
        st.selectbox(
            "Mode",
            ["text", "voice"],
            key=f"conversation_mode_{widget_suffix}",
            index=(1 if cfg_defaults.conversation_mode == "voice" else 0)
        )
        # Example steps path (used by the example generator)
        example_path = PATHS.STEP_SCRIPTS / "example_steps.txt"
        
        # Freeform steps input
        steps_text = st.text_area(
            "Enter steps (one per line or 'Step N: ...')",
            key=f"synth_steps_input_{widget_suffix}",
            height=140,
            value="Step 1: Hello, I want to confirm my appointment.\nStep 2: My name is John Doe.\nStep 3: My date of birth is January 1st, nineteen ninety.\nStep 4: Thank you, that is all."
        )

        # Voice mode: show TTS controls; Text mode: skip TTS
        if st.session_state.get(f"conversation_mode_{widget_suffix}", "voice") == "voice":
            # TTS engine and controls
            st.markdown("**TTS Settings**")
            tts_engine = st.selectbox("Engine", ["Google", "MeloTTS", "Coqui", "EdgeTTS"], index=1, key=f"tts_engine_{widget_suffix}")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                language = st.text_input("Language", value="en", key=f"tts_lang_{widget_suffix}")
            with col_b:
                speed = st.slider("Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.05, key=f"tts_speed_{widget_suffix}")
            with col_c:
                emotion_options = ["(none)", "Neutral", "Happy", "Sad", "Angry", "Calm", "Excited"]
                selected_emotion = st.selectbox("Emotion (optional)", emotion_options, index=0, key=f"tts_emotion_{widget_suffix}")
                emotion = None if selected_emotion == "(none)" else selected_emotion

            # Accent/speaker selection
            speakers = list_speakers(tts_engine, language)
            if tts_engine.lower() == "google":
                accent = st.text_input("Accent/TLD (e.g., com, co.uk)", value="com", key=f"tts_accent_{widget_suffix}")
            else:
                label = "Speaker (Coqui)" if tts_engine.lower()=="coqui" else "Speaker/Accent"
                chosen = st.selectbox(label, speakers, key=f"tts_accent_{widget_suffix}")
                accent = None if chosen == "(auto)" else chosen

            gen_col1, gen_col2 = st.columns(2)
            with gen_col1:
                if st.button("Generate audio from example", key=f"gen_from_example_{widget_suffix}"):
                    st.session_state[f"_steps_src_{widget_suffix}"] = str(example_path)
                    with st.spinner("Generating audio..."):
                        result = asyncio.run(SyntheticRunService.generate_audio_from_steps_file(
                            example_path,
                            engine=("melo" if tts_engine.lower()=="melotts" else ("coqui" if tts_engine.lower()=="coqui" else ("edgetts" if tts_engine.lower()=="edgetts" else "google"))),
                            language=language,
                            accent=accent,
                            speed=float(speed),
                            emotion=(emotion or None),
                            sample_rate=24000,
                        ))
                    if result.get("success"):
                        st.success(f"Generated {result['count']} file(s) in {PATHS.SYNTH_STEPS}")
                        st.session_state[f"_synth_files_{widget_suffix}"] = result["files"]
                        # Also cache utterance texts parsed from the example file
                        try:
                            from src.services.conversation.steps_service import read_steps_file
                            st.session_state[f"_synth_texts_{widget_suffix}"] = read_steps_file(example_path)
                        except Exception:
                            st.session_state[f"_synth_texts_{widget_suffix}"] = []
                    else:
                        st.error(f"Generation failed: {result.get('error')}")
            with gen_col2:
                if st.button("Generate audio from entered steps", key=f"gen_from_text_{widget_suffix}"):
                    from src.services.conversation.steps_service import parse_steps_from_text
                    from src.services.tts.google_tts_service import GoogleTTSService
                    steps = parse_steps_from_text(steps_text or "")
                    if not steps:
                        st.error("Please enter at least one step.")
                    else:
                        with st.spinner("Generating audio..."):
                            result_files = synthesize_steps(
                                engine=tts_engine,
                                texts=steps,
                                output_dir=PATHS.SYNTH_STEPS,
                                language=language,
                                accent=accent,
                                speed=float(speed),
                                emotion=(emotion or None),
                                sample_rate=24000,
                            )
                        st.success(f"Generated {len(result_files)} file(s) in {PATHS.SYNTH_STEPS}")
                        st.session_state[f"_synth_files_{widget_suffix}"] = [str(p) for p in result_files]
                        # Cache utterance texts from entered steps
                        st.session_state[f"_synth_texts_{widget_suffix}"] = steps

            # Start synthetic run using the same evaluator flow as Human, with synthetic inputs
            if st.button("Start Synthetic Run", key=f"send_synth_{widget_suffix}"):
                synth_dir = PATHS.SYNTH_STEPS
                files_wav = sorted([str(p) for p in synth_dir.glob("*.wav")])
                files_mp3 = sorted([str(p) for p in synth_dir.glob("*.mp3")])
                files = files_wav or files_mp3
                if not files:
                    st.error(f"No generated files found in {synth_dir}. Please generate first.")
                else:
                    cfg = create_config_from_inputs(widget_suffix)
                    texts_cached = st.session_state.get(f"_synth_texts_{widget_suffix}") or []
                    steps_src_cached = st.session_state.get(f"_steps_src_{widget_suffix}")
                    if not texts_cached and steps_src_cached and Path(steps_src_cached).exists():
                        try:
                            from src.services.conversation.steps_service import read_steps_file
                            texts_cached = read_steps_file(Path(steps_src_cached))
                        except Exception:
                            texts_cached = []
                    if len(texts_cached) < len(files):
                        texts_cached = (texts_cached + [""] * len(files))[:len(files)]

                    # Populate synthetic mode in config
                    cfg.synthetic_mode = True
                    cfg.run_type = "synthetic"
                    cfg.synthetic_files = files
                    cfg.synthetic_texts = texts_cached
                    # Ensure single-run semantics for synthetic mode
                    cfg.conversation_ids = [cfg.conversation_id]

                    # Reuse the same background runner as Human
                    start_background_run(cfg, widget_suffix)
        else:
            # Text mode: start run by sending steps as text messages directly
            if st.button("Start Synthetic Run (Text)", key=f"send_synth_text_{widget_suffix}"):
                from src.services.conversation.steps_service import parse_steps_from_text
                steps = parse_steps_from_text(steps_text or "")
                if not steps:
                    st.error("Please enter at least one step.")
                else:
                    cfg = create_config_from_inputs(widget_suffix)
                    cfg.synthetic_mode = True
                    cfg.run_type = "synthetic"
                    cfg.synthetic_files = []
                    cfg.synthetic_texts = steps
                    cfg.conversation_ids = [cfg.conversation_ids[0]]
                    start_background_run(cfg, widget_suffix)

    # Dynamic Synthetic tab UI
    if is_dynamic:
        st.markdown("Configure a dynamic scenario. LLM will generate responses in real-time based on conversation context.")
        scenario = st.text_input("Scenario", value=st.session_state.get(f"dyn_scenario_{widget_suffix}", "Confirm the appointment"), key=f"dyn_scenario_{widget_suffix}")
        max_steps = st.number_input("Max steps", min_value=1, max_value=20, value=int(st.session_state.get(f"dyn_max_steps_{widget_suffix}", 6)), key=f"dyn_max_steps_{widget_suffix}")
        temperature = st.slider("LLM temperature", min_value=0.0, max_value=1.0, value=float(st.session_state.get(f"dyn_temp_{widget_suffix}", 0.3)), step=0.05, key=f"dyn_temp_{widget_suffix}")

        # Basic connection/LLM settings
        st.text_input("Channel ID", key=f"channel_id_{widget_suffix}", value=st.session_state.get(f"channel_id_{widget_suffix}", cfg_defaults.channel_id))
        st.text_input("Base URL", key=f"base_url_{widget_suffix}", value=st.session_state.get(f"base_url_{widget_suffix}", cfg_defaults.base_url))
        st.text_input("WebSocket URL", key=f"ws_url_{widget_suffix}", value=st.session_state.get(f"ws_url_{widget_suffix}", cfg_defaults.ws_url))
        st.selectbox("LLM Model", model_options, key=f"llm_model_{widget_suffix}", index=model_index)



        # Start dynamic synthetic run
        if st.button("Start Dynamic Synthetic Run", key=f"start_dynamic_{widget_suffix}"):
            cfg = create_config_from_inputs(widget_suffix)
            if not cfg.access_token or not cfg.channel_id or not cfg.base_url:
                st.error("Missing required configuration: access token, channel id, or base url")
                return
            if not global_config.openai_api_key:
                st.error("OpenAI API key is required for dynamic synthetic mode")
                return
            # Set dynamic fields
            cfg.dynamic_synthetic_mode = True
            cfg.dynamic_scenario = scenario
            cfg.dynamic_max_steps = int(max_steps)
            cfg.dynamic_temperature = float(temperature)
            cfg.run_type = "dynamic"
            # Ensure single-run semantics
            cfg.conversation_ids = [cfg.conversation_id]
            start_background_run(cfg, widget_suffix)
        
    if is_translation:
        # Mode override for WebSocket (voice/text)
        st.selectbox("Mode", ["text", "voice"], key=f"conversation_mode_{widget_suffix}", index=(0 if cfg_defaults.conversation_mode == "voice" else 1))

        # Non-English steps
        st.text_input(
            "Channel ID",
            key=f"channel_id_{widget_suffix}",
            value=st.session_state.get(f"channel_id_{widget_suffix}", "".join(global_config.channel_id))
        )
        steps_text = st.text_area(
            "Enter steps in non-English (one per line or 'Step N: ...')",
            key=f"trans_steps_input_{widget_suffix}",
            height=140,
            value="Step 0: Can you change your language to French?\nStep 1: Hola, quiero confirmar mi cita.\nStep 2: Mi nombre es Juan Pérez.\nStep 3: Mi fecha de nacimiento es 1 de enero de 1990.\nStep 4: Gracias, eso es todo."
        )

        # TTS engine and controls (for generating non-English audio) - only show when mode is voice
        if st.session_state.get(f"conversation_mode_{widget_suffix}", "voice") == "voice":
            st.markdown("**TTS Settings**")
            tts_engine = st.selectbox("Engine", ["Google", "MeloTTS", "Coqui", "EdgeTTS"], index=1, key=f"tts_engine_{widget_suffix}")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                language = st.text_input("Language (non-English code)", value="es", key=f"tts_lang_{widget_suffix}")
            with col_b:
                speed = st.slider("Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.05, key=f"tts_speed_{widget_suffix}")
            with col_c:
                emotion_options = ["(none)", "Neutral", "Happy", "Sad", "Angry", "Calm", "Excited"]
                selected_emotion = st.selectbox("Emotion (optional)", emotion_options, index=0, key=f"tts_emotion_{widget_suffix}")
                emotion = None if selected_emotion == "(none)" else selected_emotion

            # Accent/speaker selection
            speakers = list_speakers(tts_engine, language)
            if tts_engine.lower() == "google":
                accent = st.text_input("Accent/TLD (e.g., com, co.uk)", value="com", key=f"tts_accent_{widget_suffix}")
            else:
                label = "Speaker (Coqui)" if tts_engine.lower()=="coqui" else "Speaker/Accent"
                chosen = st.selectbox(label, speakers, key=f"tts_accent_{widget_suffix}")
                accent = None if chosen == "(auto)" else chosen

        # Generate audio for entered steps - only show when mode is voice
        if st.session_state.get(f"conversation_mode_{widget_suffix}", "voice") == "voice":
            if st.button("Generate non-English audio from steps", key=f"gen_trans_from_text_{widget_suffix}"):
                from src.services.conversation.steps_service import parse_steps_from_text
                steps = parse_steps_from_text(steps_text or "")
                if not steps:
                    st.error("Please enter at least one step.")
                else:
                    with st.spinner("Generating audio..."):
                        result_files = synthesize_steps(
                            engine=tts_engine,
                            texts=steps,
                            output_dir=PATHS.TRANSLATION_STEPS,
                            language=language,
                            accent=accent,
                            speed=float(speed),
                            emotion=(emotion or None),
                            sample_rate=24000,
                        )
                    st.success(f"Generated {len(result_files)} file(s) in {PATHS.TRANSLATION_STEPS}")
                    st.session_state[f"_trans_files_{widget_suffix}"] = [str(p) for p in result_files]
                    st.session_state[f"_trans_texts_{widget_suffix}"] = steps

            # Start translation synthetic run (voice)
            if st.button("Start Translation Run", key=f"send_trans_{widget_suffix}"):
                synth_dir = PATHS.TRANSLATION_STEPS
                files_wav = sorted([str(p) for p in synth_dir.glob("*.wav")])
                files_mp3 = sorted([str(p) for p in synth_dir.glob("*.mp3")])
                files = files_wav or files_mp3
                if not files:
                    st.error(f"No generated files found in {synth_dir}. Please generate first.")
                else:
                    cfg = create_config_from_inputs(widget_suffix)
                    texts_cached = st.session_state.get(f"_trans_texts_{widget_suffix}") or []
                    if len(texts_cached) < len(files):
                        texts_cached = (texts_cached + [""] * len(files))[:len(files)]
                    cfg.synthetic_mode = True
                    cfg.run_type = "translation"
                    cfg.synthetic_files = files
                    cfg.synthetic_texts = texts_cached
                    cfg.conversation_ids = [cfg.conversation_ids[0]]
                    start_background_run(cfg, widget_suffix)
        else:
            # Text mode: start run by sending steps as text messages directly
            if st.button("Start Translation Run (Text)", key=f"send_trans_text_{widget_suffix}"):
                from src.services.conversation.steps_service import parse_steps_from_text
                steps = parse_steps_from_text(steps_text or "")
                if not steps:
                    st.error("Please enter at least one step.")
                else:
                    cfg = create_config_from_inputs(widget_suffix)
                    cfg.synthetic_mode = True
                    cfg.run_type = "translation"
                    cfg.synthetic_files = []
                    cfg.synthetic_texts = steps
                    cfg.conversation_ids = [cfg.conversation_ids[0]]
                    start_background_run(cfg, widget_suffix)
                
    # Status area
    st.markdown("### Run Status")
    run_in_progress = st.session_state.get(f'run_in_progress_{widget_suffix}', False)
    runner = st.session_state.get(f'runner_{widget_suffix}')
    run_result = st.session_state.get(f'run_result_{widget_suffix}')
    run_error = st.session_state.get(f'run_error_{widget_suffix}')
    run_start_ts = st.session_state.get(f'run_start_ts_{widget_suffix}')

    cols = st.columns(4)
    if run_in_progress and runner and runner.is_alive():
        cols[0].markdown("""
        <span style='font-weight:700;color:#fd7e14;'>Status: Running ⏳</span>
        """, unsafe_allow_html=True)
        # Stop button shown only while running
        if cols[3].button("Stop Run", key=f"stop_run_{widget_suffix}"):
            stop_event = st.session_state.get(f'stop_event_{widget_suffix}')
            if stop_event:
                stop_event.set()
            st.session_state[f'run_error_{widget_suffix}'] = 'Stopped by user'
    elif run_error:
        cols[0].markdown("""
        <span style='font-weight:700;color:#dc3545;'>Status: Failed ❌</span>
        """, unsafe_allow_html=True)
    elif run_result is not None:
        cols[0].markdown("""
        <span style='font-weight:700;color:#28a745;'>Status: Completed ✅</span>
        """, unsafe_allow_html=True)
    else:
        cols[0].markdown("""
        <span style='font-weight:700;color:#6c757d;'>Status: Idle</span>
        """, unsafe_allow_html=True)

    elapsed = int(time.time() - run_start_ts) if run_start_ts else 0
    cols[1].metric("Elapsed (s)", elapsed)
    cols[3].button("Refresh logs", key=f"refresh_logs_{widget_suffix}", type="primary")


    col1,col2 = st.columns(2)
    
    with col1:
        # Live logs (tail)
        st.markdown("### Live App Log (tail)")
        app_log_path = PATHS.LOGS / 'app.log'
        if app_log_path.exists():
            st.text_area("app.log", value=tail_file(app_log_path, 500), height=400, key=f"app_log_{widget_suffix}")
        else:
            st.info("No app.log yet.") 

    with col2:
        # Latest conversation log (tail)
        st.markdown("### Latest Conversation Log (tail)")
        convo_logs = sorted(PATHS.LOGS.glob("conversation_history_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if convo_logs:
            st.text_area(convo_logs[0].name, value=tail_file(convo_logs[0], 500), height=400, key=f"convo_log_{widget_suffix}")
        else:
            st.info("No conversation history logs yet.")
            
            
    # Latest test result and HTML report
    st.markdown("### Test Result")
    latest = load_latest_test_result()
    if latest:
        render_test_summary(latest)
        with st.expander("Raw JSON", expanded=False):
            st.json(latest)
        if st.button("Generate HTML Report", key=f"gen_html_{title.lower().replace(' ', '_')}"):
            generate_and_show_html_report(latest)
    else:
        st.info("No test result JSON found yet.")



def main():
    st.set_page_config(page_title="AgenticAI Testing Suite", layout="wide")
    st.title("AgenticAI Testing Suite")
    st.caption("Run conversations, review results, and generate beautiful HTML reports.")

    tabs = st.tabs(["Human Voice Run", "Synthetic Voice Run", "Translation Run", "Dynamic Synthetic Voice"]) 
    with tabs[0]:
        page_run("Human Voice Run")
    with tabs[1]:
        page_run("Synthetic Voice Run")
    with tabs[2]:
        page_run("Translation Run")
    with tabs[3]:
        page_run("Dynamic Synthetic Voice")


if __name__ == "__main__":
    main()


