"""
Musica Vibe - MusicXML 3.1 Score Generator
Converts transcribed notes and detected tempo/key into standard MusicXML
readable by OpenSheetMusicDisplay (OSMD), MuseScore, etc.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def midi_to_note_name(pitch):
    octave = (pitch // 12) - 1
    semitone = pitch % 12
    return f"{NOTE_NAMES[semitone]}{octave}"

def pitch_to_step_alter_octave(pitch):
    octave = (pitch // 12) - 1
    semitone = pitch % 12
    
    # Map semitone to diatonic step and alter (-1, 0, 1)
    mapping = {
        0: ("C", 0),
        1: ("C", 1),
        2: ("D", 0),
        3: ("D", 1),
        4: ("E", 0),
        5: ("F", 0),
        6: ("F", 1),
        7: ("G", 0),
        8: ("G", 1),
        9: ("A", 0),
        10: ("A", 1),
        11: ("B", 0),
    }
    step, alter = mapping[semitone]
    return step, alter, octave


def duration_to_type(duration_divisions, divisions_per_quarter=4):
    """
    Given duration in divisions (quarter note = divisions_per_quarter):
    16 = whole (4 quarters)
    8  = half (2 quarters)
    4  = quarter (1 quarter)
    2  = eighth (0.5 quarter)
    1  = 16th (0.25 quarter)
    """
    quarters = duration_divisions / divisions_per_quarter
    if quarters >= 3.5:
        return "whole"
    elif quarters >= 1.75:
        return "half"
    elif quarters >= 0.85:
        return "quarter"
    elif quarters >= 0.4:
        return "eighth"
    else:
        return "16th"


def create_musicxml(notes, tempo_bpm=120.0, key_name="C Major", time_signature=(4, 4), output_path=None):
    """
    Creates a valid MusicXML 3.1 score for grand staff (Piano).
    """
    num, den = time_signature
    divisions = 4  # 4 divisions per quarter note (1 division = 16th note)
    quarter_seconds = 60.0 / max(tempo_bpm, 10.0)
    measure_duration_sec = (num * (4.0 / den)) * quarter_seconds
    measure_divisions = int(num * (4.0 / den) * divisions)

    # Sort notes by start time, then pitch
    sorted_notes = sorted(notes, key=lambda n: (float(n.get("start", 0)), int(n.get("pitch", 60))))
    
    # Find total duration
    if sorted_notes:
        max_time = max(float(n.get("start", 0)) + float(n.get("duration", 0.5)) for n in sorted_notes)
    else:
        max_time = 4.0
        
    total_measures = max(1, int(round((max_time + measure_duration_sec * 0.5) / measure_duration_sec)))

    # Root XML
    score = ET.Element("score-partwise", version="3.1")
    
    # Work & Identification
    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = "Transcribed Piano Score"
    
    ident = ET.SubElement(score, "identification")
    creator = ET.SubElement(ident, "creator", type="composer")
    creator.text = "Musica AI Vibe"
    
    # Part list
    part_list = ET.SubElement(score, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Piano"
    
    part = ET.SubElement(score, "part", id="P1")
    
    # Group notes into measures based on start time
    measure_notes = [[] for _ in range(total_measures)]
    for n in sorted_notes:
        start_sec = float(n.get("start", 0))
        m_idx = int(start_sec / measure_duration_sec)
        if 0 <= m_idx < total_measures:
            measure_notes[m_idx].append(n)
        elif m_idx >= total_measures:
            measure_notes[-1].append(n)

    # Key signature fifths estimation
    fifths_map = {
        "C Major": 0, "A Minor": 0,
        "G Major": 1, "E Minor": 1,
        "D Major": 2, "B Minor": 2,
        "A Major": 3, "F# Minor": 3,
        "E Major": 4, "C# Minor": 4,
        "B Major": 5, "G# Minor": 5,
        "F Major": -1, "D Minor": -1,
        "Bb Major": -2, "G Minor": -2,
        "Eb Major": -3, "C Minor": -3,
        "Ab Major": -4, "F Minor": -4,
        "Db Major": -5, "Bb Minor": -5,
    }
    fifths = fifths_map.get(key_name, 0)
    
    for m_num in range(1, total_measures + 1):
        m_elem = ET.SubElement(part, "measure", number=str(m_num))
        
        # Attributes in Measure 1
        if m_num == 1:
            attrs = ET.SubElement(m_elem, "attributes")
            ET.SubElement(attrs, "divisions").text = str(divisions)
            
            key = ET.SubElement(attrs, "key")
            ET.SubElement(key, "fifths").text = str(fifths)
            ET.SubElement(key, "mode").text = "minor" if "Minor" in key_name else "major"
            
            time = ET.SubElement(attrs, "time")
            ET.SubElement(time, "beats").text = str(num)
            ET.SubElement(time, "beat-type").text = str(den)
            
            ET.SubElement(attrs, "staves").text = "2"
            
            # Clefs: Staff 1 = Treble (G2), Staff 2 = Bass (F4)
            clef1 = ET.SubElement(attrs, "clef", number="1")
            ET.SubElement(clef1, "sign").text = "G"
            ET.SubElement(clef1, "line").text = "2"
            
            clef2 = ET.SubElement(attrs, "clef", number="2")
            ET.SubElement(clef2, "sign").text = "F"
            ET.SubElement(clef2, "line").text = "4"
            
            # Metronome direction
            direction = ET.SubElement(m_elem, "direction", placement="above")
            dir_type = ET.SubElement(direction, "direction-type")
            metronome = ET.SubElement(dir_type, "metronome")
            ET.SubElement(metronome, "beat-unit").text = "quarter"
            ET.SubElement(metronome, "per-minute").text = str(int(round(tempo_bpm)))
            sound = ET.SubElement(direction, "sound", tempo=str(int(round(tempo_bpm))))

        # Populate measure with notes or rests
        m_start_sec = (m_num - 1) * measure_duration_sec
        curr_notes = measure_notes[m_num - 1]
        
        if not curr_notes:
            # Whole measure rest for staff 1 and 2
            for staff_num in (1, 2):
                rest_elem = ET.SubElement(m_elem, "note")
                ET.SubElement(rest_elem, "rest")
                ET.SubElement(rest_elem, "duration").text = str(measure_divisions)
                ET.SubElement(rest_elem, "voice").text = str(staff_num)
                ET.SubElement(rest_elem, "type").text = "whole"
                ET.SubElement(rest_elem, "staff").text = str(staff_num)
                if staff_num == 1:
                    # Backup to write staff 2
                    backup = ET.SubElement(m_elem, "backup")
                    ET.SubElement(backup, "duration").text = str(measure_divisions)
            continue
            
        # Separate into staff 1 (pitch >= 60, treble) and staff 2 (pitch < 60, bass)
        staff1_notes = [n for n in curr_notes if int(n.get("pitch", 60)) >= 60]
        staff2_notes = [n for n in curr_notes if int(n.get("pitch", 60)) < 60]
        
        # Build staff events: fill each staff up to measure_divisions
        for staff_num, s_notes in [(1, staff1_notes), (2, staff2_notes)]:
            if staff_num == 2 and staff1_notes:
                # Backup divisions after staff 1
                backup = ET.SubElement(m_elem, "backup")
                ET.SubElement(backup, "duration").text = str(measure_divisions)
                
            if not s_notes:
                rest_elem = ET.SubElement(m_elem, "note")
                ET.SubElement(rest_elem, "rest")
                ET.SubElement(rest_elem, "duration").text = str(measure_divisions)
                ET.SubElement(rest_elem, "voice").text = str(staff_num)
                ET.SubElement(rest_elem, "type").text = "whole"
                ET.SubElement(rest_elem, "staff").text = str(staff_num)
                continue
                
            accum_divs = 0
            for i, n in enumerate(s_notes):
                pitch = int(n.get("pitch", 60))
                dur_sec = float(n.get("duration", 0.5))
                dur_divs = max(1, int(round((dur_sec / quarter_seconds) * divisions)))
                
                # Check if exceeds measure
                if accum_divs + dur_divs > measure_divisions:
                    dur_divs = max(1, measure_divisions - accum_divs)
                    
                step, alter, oct_val = pitch_to_step_alter_octave(pitch)
                
                note_elem = ET.SubElement(m_elem, "note")
                pitch_elem = ET.SubElement(note_elem, "pitch")
                ET.SubElement(pitch_elem, "step").text = step
                if alter != 0:
                    ET.SubElement(pitch_elem, "alter").text = str(alter)
                ET.SubElement(pitch_elem, "octave").text = str(oct_val)
                
                ET.SubElement(note_elem, "duration").text = str(dur_divs)
                ET.SubElement(note_elem, "voice").text = str(staff_num)
                ET.SubElement(note_elem, "type").text = duration_to_type(dur_divs, divisions)
                if alter == 1:
                    ET.SubElement(note_elem, "accidental").text = "sharp"
                elif alter == -1:
                    ET.SubElement(note_elem, "accidental").text = "flat"
                ET.SubElement(note_elem, "staff").text = str(staff_num)
                
                accum_divs += dur_divs
                if accum_divs >= measure_divisions:
                    break
                    
            # If notes didn't fill entire measure, add trailing rest
            if accum_divs < measure_divisions:
                rest_divs = measure_divisions - accum_divs
                rest_elem = ET.SubElement(m_elem, "note")
                ET.SubElement(rest_elem, "rest")
                ET.SubElement(rest_elem, "duration").text = str(rest_divs)
                ET.SubElement(rest_elem, "voice").text = str(staff_num)
                ET.SubElement(rest_elem, "type").text = duration_to_type(rest_divs, divisions)
                ET.SubElement(rest_elem, "staff").text = str(staff_num)

    xml_str = ET.tostring(score, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
            
    return pretty_xml
