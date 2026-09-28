import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

def generate_lofi_track(filename="scratch/lofi_beat.wav", duration_sec=40, sample_rate=44100):
    bpm = 85
    seconds_per_beat = 60.0 / bpm
    total_samples = int(duration_sec * sample_rate)
    
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    audio = np.zeros(total_samples, dtype=np.float32)
    
    # Chord frequencies (Hz) for Cmaj7, Am7, Fmaj7, G7
    # Cmaj7: C4, E4, G4, B4
    # Am7:   A3, C4, E4, G4
    # Fmaj7: F3, A3, C4, E4
    # G7:    G3, B3, D4, F4
    chords = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [174.61, 220.00, 261.63, 329.63],  # Fmaj7
        [196.00, 246.94, 293.66, 349.23],  # G7
    ]
    
    bass_notes = [130.81, 110.00, 87.31, 98.00] # C3, A2, F2, G2
    
    bar_duration = seconds_per_beat * 4  # 4 beats per chord
    
    # 1. Synthesize Chords & Bass (Rhodes/E-Piano emulation)
    for i in range(int(duration_sec / bar_duration) + 1):
        chord_idx = i % len(chords)
        chord_freqs = chords[chord_idx]
        bass_freq = bass_notes[chord_idx]
        
        start_sample = int(i * bar_duration * sample_rate)
        end_sample = min(start_sample + int(bar_duration * sample_rate), total_samples)
        num_s = end_sample - start_sample
        if num_s <= 0:
            continue
            
        t_segment = np.linspace(0, num_s / sample_rate, num_s, endpoint=False)
        
        # Chord synth
        chord_signal = np.zeros(num_s, dtype=np.float32)
        env = np.exp(-1.2 * t_segment)  # Smooth piano decay
        
        for f in chord_freqs:
            # Soft sine + subtle harmonics for warm E-piano tone
            wave = 0.6 * np.sin(2 * np.pi * f * t_segment) + \
                   0.25 * np.sin(2 * np.pi * f * 2 * t_segment) + \
                   0.1 * np.sin(2 * np.pi * f * 3 * t_segment)
            chord_signal += wave * env
            
        chord_signal = chord_signal / len(chord_freqs) * 0.4
        
        # Bass synth
        bass_env = np.exp(-0.8 * t_segment)
        bass_wave = 0.5 * np.sin(2 * np.pi * bass_freq * t_segment) + \
                    0.2 * np.sin(2 * np.pi * bass_freq * 2 * t_segment)
        bass_signal = bass_wave * bass_env * 0.35
        
        audio[start_sample:end_sample] += (chord_signal + bass_signal)

    # 2. Synthesize Lo-Fi Hip Hop Drum Pattern
    num_beats = int(duration_sec / seconds_per_beat)
    for b in range(num_beats):
        beat_start = int(b * seconds_per_beat * sample_rate)
        beat_type = b % 4  # 0, 1, 2, 3
        
        # Kick on Beat 0 and Beat 2.5 (syncopated)
        if beat_type in [0, 2]:
            k_len = int(0.18 * sample_rate)
            k_end = min(beat_start + k_len, total_samples)
            if k_end > beat_start:
                k_t = np.linspace(0, (k_end - beat_start) / sample_rate, k_end - beat_start)
                # Pitch sweep for punchy low kick
                freq_sweep = 120 * np.exp(-30 * k_t) + 45
                kick = 0.6 * np.sin(2 * np.pi * freq_sweep * k_t) * np.exp(-12 * k_t)
                audio[beat_start:k_end] += kick
                
        # Snare / Soft Rimshot on Beat 1 and 3
        if beat_type in [1, 3]:
            s_len = int(0.15 * sample_rate)
            s_end = min(beat_start + s_len, total_samples)
            if s_end > beat_start:
                s_t = np.linspace(0, (s_end - beat_start) / sample_rate, s_end - beat_start)
                noise = np.random.uniform(-1, 1, len(s_t))
                body = np.sin(2 * np.pi * 180 * s_t)
                snare = (0.2 * body + 0.3 * noise) * np.exp(-22 * s_t)
                audio[beat_start:s_end] += snare
                
        # Hi-Hats on 8th notes (2 per beat)
        for sub in [0, 0.5]:
            hh_start = int((b + sub) * seconds_per_beat * sample_rate)
            hh_len = int(0.05 * sample_rate)
            hh_end = min(hh_start + hh_len, total_samples)
            if hh_end > hh_start:
                hh_t = np.linspace(0, (hh_end - hh_start) / sample_rate, hh_end - hh_start)
                hh_noise = np.random.uniform(-0.15, 0.15, len(hh_t)) * np.exp(-60 * hh_t)
                audio[hh_start:hh_end] += hh_noise

    # 3. Add Subtle Vinyl Texture & Warm Filter
    vinyl_dust = np.random.normal(0, 0.008, total_samples).astype(np.float32)
    audio += vinyl_dust
    
    # Lowpass Butter Filter (Cutoff = 2800 Hz) for nostalgic warm lo-fi feel
    nyquist = 0.5 * sample_rate
    cutoff = 2800.0 / nyquist
    b_coeff, a_coeff = butter(2, cutoff, btype='low')
    lofi_audio = lfilter(b_coeff, a_coeff, audio)
    
    # Normalize peak audio
    max_val = np.max(np.abs(lofi_audio))
    if max_val > 0:
        lofi_audio = (lofi_audio / max_val) * 0.85
        
    # Convert to 16-bit PCM
    audio_int16 = (lofi_audio * 32767).astype(np.int16)
    
    wavfile.write(filename, sample_rate, audio_int16)
    print(f"Generated upbeat lo-fi track saved to: {filename}")

if __name__ == "__main__":
    generate_lofi_track()
