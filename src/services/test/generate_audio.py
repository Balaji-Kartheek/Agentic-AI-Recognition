import os
import asyncio
from gtts import gTTS
from pydub import AudioSegment
from TTS.api import TTS as CoquiTTS
from melo.api import TTS as MeloTTS


def ensure_folder(path):
    """Ensure the directory exists and return its path."""
    os.makedirs(path, exist_ok=True)
    return path


def generate_gtts(text):
    """Generate audio with gTTS and create faster and slower versions."""
    folder = ensure_folder("output/gTTS")
    base = os.path.join(folder, "normal.mp3")

    # Always overwrite existing files
    gTTS(text, lang="en", tld="com").save(base)

    sound = AudioSegment.from_file(base)
    sound.speedup(1.5).export(os.path.join(folder, "faster.mp3"), format="mp3")
    sound._spawn(sound.raw_data, {"frame_rate": int(sound.frame_rate * 0.75)}).set_frame_rate(sound.frame_rate)\
        .export(os.path.join(folder, "slower.mp3"), format="mp3")

    print(f"✅ gTTS outputs saved in {folder}")


def generate_coqui_tts(text):
    """Generate audio using CoquiTTS."""
    folder = ensure_folder("output/CoquiTTS")
    path = os.path.join(folder, "voice.wav")

    # Initialize and overwrite
    tts = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)
    tts.tts_to_file(text=text, file_path=path)
    print(f"✅ CoquiTTS output saved at {path}")


def generate_melotts(text):
    """Generate audio for all available speakers using MeloTTS."""
    print("🔊 Generating audio using MeloTTS...")
    output_dir = ensure_folder("output/MeloTTS")

    model = MeloTTS(language='EN', device='auto')
    speaker_ids = model.hps.data.spk2id

    for spk_name, spk_id in speaker_ids.items():
        output_path = os.path.join(output_dir, f"{spk_name}.wav")
        print(f"Generating for speaker: {spk_name} ...")
        model.tts_to_file(text, spk_id, output_path, speed=1.0)

    print(f"✅ All MeloTTS audio files saved in '{output_dir}/'")


def main():
    text = "Can you please help me confirm my appointment? My date of birth is 1990-01-01 and my name is John Doe."
    print("Choose engine:\n1) gTTS\n2) CoquiTTS\n3) MeloTTS")
    choice = input("Choice: ").strip()

    if choice == "1":
        generate_gtts(text)
    elif choice == "2":
        generate_coqui_tts(text)
    elif choice == "3":
        generate_melotts(text)
    else:
        print("❌ Invalid choice.")


if __name__ == "__main__":
    main()
