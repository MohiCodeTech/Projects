"""
Musica Vibe - Pure Python Standard MIDI File (SMF Format 0/1) Generator
Generates valid .mid files without external dependencies.
"""

import struct


def _write_var_len(val):
    """Encode an integer as a MIDI variable-length quantity."""
    val = int(val)
    if val < 0:
        val = 0
    buf = bytearray([val & 0x7F])
    val >>= 7
    while val > 0:
        buf.insert(0, 0x80 | (val & 0x7F))
        val >>= 7
    return bytes(buf)


def create_midi_file(notes, tempo_bpm=120.0, time_signature=(4, 4), output_path=None):
    """
    Creates a standard MIDI file from a list of note events.
    
    notes: list of dicts with:
        pitch: int (0-127, e.g. 60 for C4)
        start: float (seconds)
        duration: float (seconds)
        velocity: float (0.0 to 1.0) or int (0-127)
    tempo_bpm: detected tempo in BPM
    time_signature: tuple (numerator, denominator)
    output_path: file path to write to (optional, returns bytes if None)
    """
    ticks_per_beat = 480
    microsec_per_beat = int(round(60_000_000.0 / max(tempo_bpm, 10.0)))
    
    # Track events: (tick, event_type_priority, bytes)
    # Event priority: 0 = meta tempo/time-sig, 1 = note_off, 2 = note_on
    raw_events = []
    
    # Tempo meta-event at tick 0
    # FF 51 03 tt tt tt (3-byte microseconds per quarter note)
    tempo_bytes = struct.pack(">I", microsec_per_beat)[1:]  # 3 bytes
    raw_events.append((0, 0, bytes([0xFF, 0x51, 0x03]) + tempo_bytes))
    
    # Time signature meta-event at tick 0
    # FF 58 04 nn dd cc bb
    # dd is stored as power of 2 (e.g., 4 -> 2)
    num, den = time_signature
    den_pow = 2
    if den == 2:
        den_pow = 1
    elif den == 4:
        den_pow = 2
    elif den == 8:
        den_pow = 3
    elif den == 16:
        den_pow = 4
    raw_events.append((0, 0, bytes([0xFF, 0x58, 0x04, num & 0xFF, den_pow, 24, 8])))
    
    # Track name meta-event: "Musica AI Vibe"
    track_name = b"Musica AI Vibe Piano"
    raw_events.append((0, 0, bytes([0xFF, 0x03, len(track_name)]) + track_name))
    
    # Program change (Acoustic Grand Piano = 0)
    raw_events.append((0, 0, bytes([0xC0, 0x00])))
    
    # Convert notes into note-on and note-off events
    for note in notes:
        pitch = int(note.get("pitch", 60))
        pitch = max(0, min(127, pitch))
        
        start_sec = float(note.get("start", 0.0))
        dur_sec = max(0.05, float(note.get("duration", 0.25)))
        end_sec = start_sec + dur_sec
        
        vel = note.get("velocity", 80)
        if isinstance(vel, float) and vel <= 1.0:
            vel = int(vel * 127)
        vel = max(1, min(127, int(vel)))
        
        start_tick = int(round((start_sec / 60.0) * tempo_bpm * ticks_per_beat))
        end_tick = int(round((end_sec / 60.0) * tempo_bpm * ticks_per_beat))
        if end_tick <= start_tick:
            end_tick = start_tick + int(ticks_per_beat / 4)
            
        # Note on: 90 pitch velocity
        raw_events.append((start_tick, 2, bytes([0x90, pitch, vel])))
        # Note off: 80 pitch 0
        raw_events.append((end_tick, 1, bytes([0x80, pitch, 0x00])))
        
    # Sort events by tick, then priority
    raw_events.sort(key=lambda x: (x[0], x[1]))
    
    # Serialize to delta-time events
    track_bytes = bytearray()
    last_tick = 0
    
    for tick, _, evt_bytes in raw_events:
        delta = max(0, tick - last_tick)
        track_bytes.extend(_write_var_len(delta))
        track_bytes.extend(evt_bytes)
        last_tick = tick
        
    # End of track meta-event (FF 2F 00)
    track_bytes.extend(_write_var_len(0))
    track_bytes.extend(bytes([0xFF, 0x2F, 0x00]))
    
    # Construct MIDI file format 0 (single track containing all data)
    # Header Chunk: "MThd", length=6, format=0, ntracks=1, division=ticks_per_beat
    header = struct.pack(">4sIHHH", b"MThd", 6, 0, 1, ticks_per_beat)
    track_chunk = struct.pack(">4sI", b"MTrk", len(track_bytes)) + bytes(track_bytes)
    
    midi_data = header + track_chunk
    
    if output_path:
        with open(output_path, "wb") as f:
            f.write(midi_data)
            
    return midi_data
