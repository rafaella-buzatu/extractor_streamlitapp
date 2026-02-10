import os
import re
import json
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
st.title("Differentiation protocols")

# ----------------------------
# CSS
# ----------------------------
st.markdown(
    """
    <style>
    .step-container-culturing {
        padding: 10px;
        border-radius: 10px;
        background-color: #FFD9AD;
        margin-bottom: 20px;
        color: black;
    }
    .step-container {
        padding: 10px;
        border-radius: 10px;
        background-color:  #DFE5FF;
        margin-bottom: 20px;
        color: black;
    }
    .readout-container {
        padding: 10px;
        border-radius: 10px;
        background-color: #EAFFE4;
        margin-bottom: 20px;
        color: black;
    }
    .participant-container {
        padding: 5px;
        border-radius: 10px;
        background-color: #FFFFF;
        margin-bottom: 5px;
    }
    .participant-title {
        font-size: 20px;
        font-weight: bold;
        text-align: center;
    }
    .custom-divider {
        border: none;
        height: 20px;
        background-color: #001158;
        margin: 0px 0;
    }
    .cell-box {
        border-radius: 10px;
        padding: 10px;
        background-color: #FAE8F1;
        text-align: center;
        margin: 10px;
    }
    .arrow-box {
        text-align: center;
        display: flex;
        font-size: 60px;
        margin: 0 auto;
        line-height: 1;
        align-items: center;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers (unchanged behavior, but used lazily)
# ----------------------------
def extract_number_in_parentheses(input_string: str):
    match = re.search(r"\((\d+)h\)", input_string or "")
    return match.group(1) if match else None

def process_string(s: str):
    return re.sub(r"\s+", " ", s or "").strip()

def convert_number_words_to_digits(input_string: str):
    number_words = {
        "one": "1","two": "2","three": "3","four": "4","five": "5","six": "6",
        "seven": "7","eight": "8","nine": "9","ten": "10","eleven": "11","twelve": "12",
    }
    if input_string is None:
        return ""
    words = str(input_string).split()
    return " ".join([number_words.get(w.lower(), w) for w in words])

def is_empty_or_null(item):
    if isinstance(item, dict):
        return all(is_empty_or_null(v) for v in item.values())
    if isinstance(item, list):
        return all(is_empty_or_null(v) for v in item)
    return item in [None, "", False]

def convert_to_duration_fixed(string: str):
    pattern = re.compile(r"(\d+)-(\d+)")
    def replace_with_duration(match):
        num1 = int(match.group(1))
        num2 = int(match.group(2))
        difference = num2 - num1 + 1
        if "day" in (string or "").lower():
            unit = "day"
        elif "week" in (string or "").lower():
            unit = "week"
        elif "hour" in (string or "").lower():
            unit = "hour"
        else:
            unit = ""
        return f"{difference} {unit}{'s' if difference > 1 else ''}"
    return pattern.sub(replace_with_duration, string or "")

def _safe_str(x):
    if pd.isna(x):
        return None
    try:
        if isinstance(x, (int, np.integer)):
            return str(int(x))
        if isinstance(x, float) and x.is_integer():
            return str(int(x))
    except Exception:
        pass
    return str(x).strip()

def load_blacklists(excel_path: str):
    remove_all_participants = set()
    remove_pairs = set()      # (participant_id_str, pmid_str)
    remove_pmids_full = set() # pmid_str

    if not excel_path or not os.path.exists(excel_path):
        return remove_all_participants, remove_pairs, remove_pmids_full

    # Sheet1: participant_id + submissionsToRemove (PMIDs or 'all')
    try:
        sheet1 = pd.read_excel(excel_path, sheet_name="Sheet1")
        if "participant_id" in sheet1.columns and "submissionsToRemove" in sheet1.columns:
            for _, r in sheet1[["participant_id", "submissionsToRemove"]].iterrows():
                pid = _safe_str(r["participant_id"])
                subs = _safe_str(r["submissionsToRemove"])
                if not pid or not subs:
                    continue
                if subs.lower() == "all":
                    remove_all_participants.add(pid)
                else:
                    pmids = re.findall(r"\d+", subs)
                    for p in pmids:
                        remove_pairs.add((pid, p))
    except Exception:
        pass

    # Sheet2: PMIDs to remove fully (first column)
    try:
        sheet2 = pd.read_excel(excel_path, sheet_name="Sheet2", header=None)
        for v in sheet2.iloc[:, 0].dropna().tolist():
            pmid = _safe_str(v)
            if pmid and re.fullmatch(r"\d+", pmid):
                remove_pmids_full.add(pmid)
    except Exception:
        pass

    return remove_all_participants, remove_pairs, remove_pmids_full

def find_blacklist_path():
    candidates = [
        "participant_blacklist.xlsx",
        os.path.join("data", "participant_blacklist.xlsx"),
    ]
    return next((p for p in candidates if os.path.exists(p)), None)

# ----------------------------
# Load base table fast (NO merged_data parsing here)
# ----------------------------
@st.cache_data(show_spinner=True)
def load_submissions_table(csv_file: str):
    df = pd.read_csv(csv_file)

    # submitted only
    df_submitted = df[df["status"] == "submitted"].reset_index(drop=True)

    # remove known test submissions
    df_submitted = df_submitted[df_submitted["participant_id"] != 1246060743644676199]
    df_submitted = df_submitted[df_submitted["participant_id"] != 753972611481993256]
    df_submitted = df_submitted[df_submitted["participant_id"] != 204295234522185728]

    # normalize IDs
    df_submitted["participant_id"] = df_submitted["participant_id"].apply(_safe_str)
    df_submitted["publication_id"] = df_submitted["publication_id"].apply(_safe_str)

    # apply blacklists (fast)
    bl_path = find_blacklist_path()
    remove_all_participants, remove_pairs, remove_pmids_full = load_blacklists(bl_path)

    if remove_pmids_full:
        df_submitted = df_submitted[~df_submitted["publication_id"].isin(remove_pmids_full)]
    if remove_all_participants:
        df_submitted = df_submitted[~df_submitted["participant_id"].isin(remove_all_participants)]
    if remove_pairs:
        remove_keys = set([f"{pid}||{pmid}" for pid, pmid in remove_pairs])
        keys = df_submitted["participant_id"].astype(str) + "||" + df_submitted["publication_id"].astype(str)
        df_submitted = df_submitted[~keys.isin(remove_keys)]

    return df_submitted.reset_index(drop=True)

# ----------------------------
# Parse & normalize ONE merged_data blob (lazy)
# ----------------------------
def parse_and_normalize_protocol(merged_raw):
    """
    Returns dictentry (dict) or None.
    This is the expensive part, so we only do it for the rows the user wants to see.
    """
    try:
        if merged_raw is None:
            return None
        if isinstance(merged_raw, float) and pd.isna(merged_raw):
            return None
        if isinstance(merged_raw, (bytes, bytearray)):
            merged_raw = merged_raw.decode("utf-8", errors="replace")
        if isinstance(merged_raw, str):
            if merged_raw.strip() == "":
                return None
            dictentry = json.loads(merged_raw)
        elif isinstance(merged_raw, dict):
            dictentry = merged_raw
        else:
            return None

        if not isinstance(dictentry, dict):
            return None

        # REMOVE EMPTY KEYS (keeping 0, 1001, -1)
        keys_to_retain = {"0", "1001", "-1"}
        keys_to_remove = []
        for key, value in dictentry.items():
            if key in keys_to_retain:
                continue
            try:
                inner_dict = json.loads(value) if isinstance(value, str) else value
            except Exception:
                # if inner json is broken, treat as non-empty to avoid deleting
                continue
            if is_empty_or_null(inner_dict):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            dictentry.pop(key, None)

        # step count calc as in your original logic
        newstepcount = len(dictentry) - 1 - 1 - 1

        # rename keys for consistency with downstream code
        if "1000" in dictentry:
            dictentry[str(newstepcount)] = dictentry.pop("1000")
        if "1001" in dictentry:
            dictentry["sequencingData"] = dictentry.pop("1001")
        if "-1" in dictentry:
            dictentry["cellLine"] = dictentry.pop("-1")

        return dictentry
    except Exception:
        return None

# ----------------------------
# Data load (fast now)
# ----------------------------
csv_file = "data/submissions.csv"
df_submitted = load_submissions_table(csv_file)

# ----------------------------
# UI selection
# ----------------------------
protocol_options = st.columns(2)
pmids = sorted([p for p in df_submitted.publication_id.dropna().unique().tolist() if p is not None])

with protocol_options[0]:
    selected_pmid = st.selectbox("Select a PMID", pmids + ["show all"])

if selected_pmid != "show all":
    participants = sorted(
        [p for p in df_submitted[df_submitted["publication_id"] == selected_pmid]["participant_id"].dropna().unique().tolist() if p is not None]
    )
else:
    participants = sorted([p for p in df_submitted["participant_id"].dropna().unique().tolist() if p is not None])

with protocol_options[1]:
    selected_participants = st.selectbox("Select a Participant ID", ["show all"] + participants)

st.write("Plotting parameters:")
checks = st.columns(6)
with checks[1]:
    mediacheckbox = st.checkbox("Show media", value=True)
with checks[2]:
    supplementscheckbox = st.checkbox("Show supplements", value=True)
with checks[3]:
    gfcheckbox = st.checkbox("Show growth factors", value=True)
with checks[4]:
    matrixcheckbox = st.checkbox("Show culture matrix", value=True)
with checks[5]:
    markerscheckbox = st.checkbox("Show readout", value=True)
with checks[0]:
    cellcheckbox = st.checkbox("Show cell lines and targets", value=True)

st.markdown("""<hr class="custom-divider">""", unsafe_allow_html=True)

# Optional: don't do any heavy work until user clicks
run = st.button("Load / Render selection", type="primary")

def plot_data_for_selection(selected_pmid, selected_participants):
    if selected_participants == "show all" and selected_pmid == "show all":
        paper_submissions = df_submitted[:10]
        st.markdown("<p> Showing first 10 entries </p>", unsafe_allow_html=True)
    elif selected_participants == "show all":
        paper_submissions = df_submitted[df_submitted["publication_id"] == selected_pmid]
    elif selected_pmid == "show all":
        paper_submissions = df_submitted[df_submitted["participant_id"] == selected_participants]
    else:
        paper_submissions = df_submitted[
            (df_submitted["publication_id"] == selected_pmid) &
            (df_submitted["participant_id"] == selected_participants)
        ]

    for submission in range(len(paper_submissions)):
        entry = paper_submissions.iloc[submission]
        pmid = entry["publication_id"]
        participant_id = entry["participant_id"]

        try:
            protocol_info = parse_and_normalize_protocol(entry.get("merged_data", None))
            if protocol_info is None:
                continue

            st.subheader(f"PMID: {pmid} | Participant ID: {participant_id}")

            # --- cell line info ---
            if cellcheckbox:
                cell_blob = protocol_info.get("cellLine")
                cell_data = json.loads(cell_blob) if isinstance(cell_blob, str) else (cell_blob or {})
                cell_line_details = cell_data.get("cellLineDetails", []) or []
                diff_targets = cell_data.get("differentiationTarget", []) or []

                cell_lines = ", ".join(
                    [process_string(d.get("cellLineName", "")).rstrip(".") for d in cell_line_details if d.get("cellLineName")]
                ) or "Not specified"

                target = ", ".join(
                    [process_string(t.get("targetCell", "")).rstrip(".") for t in diff_targets if t.get("targetCell")]
                ) or "Not specified"

                col1, col2, col3 = st.columns([5, 0.5, 5])
                with col1:
                    st.markdown(
                        f"""
                        <div class="cell-box">
                            <strong>Cells of Origin:</strong><br>
                            {cell_lines}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        """
                        <div class="arrow-box">
                        <span style='font-size:70px;'>&#8594;</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.markdown(
                        f"""
                        <div class="cell-box">
                            <strong>Target Cells:</strong><br>
                            {target}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # --- steps ---
            no_steps = list(protocol_info.keys())
            for k in ["sequencingData", "cellLine"]:
                if k in no_steps:
                    no_steps.remove(k)

            # culturing flag
            try:
                culturing = json.loads(protocol_info.get("0", "{}")).get("culturingProtocol", [{}])[0].get("isGiven", True)
            except Exception:
                culturing = True
            if culturing is False and "0" in no_steps:
                no_steps.remove("0")

            lengths = []
            labels_time = []

            for step_key in no_steps:
                step_blob = protocol_info.get(str(step_key), "{}")
                step_data = json.loads(step_blob) if isinstance(step_blob, str) else (step_blob or {})
                duration_str = (step_data.get("duration", [{}])[0].get("durationHours", "") or "")

                duration_str = convert_number_words_to_digits(duration_str)

                if "-" in duration_str and duration_str and duration_str[0].isalpha():
                    duration_str = convert_to_duration_fixed(duration_str.lower())

                if "week" in duration_str.lower():
                    step_times = re.findall(r"\d+", duration_str)
                    length_step = float(step_times[0]) * 7 * 24 if len(step_times) == 1 else np.mean([float(t) * 7 * 24 for t in step_times])
                    label = f"{int(length_step)} hours"
                elif "day" in duration_str.lower():
                    step_times = re.findall(r"\d+", duration_str)
                    length_step = float(step_times[0]) * 24 if len(step_times) == 1 else np.mean([float(t) * 24 for t in step_times])
                    label = f"{int(length_step)} hours"
                elif len(re.findall(r"\d+", duration_str)) == 0 or duration_str == "0":
                    length_step = np.nan
                    label = ""
                else:
                    step_times = [float(nr) for nr in re.findall(r"\d+\.\d+|\d+", duration_str)]
                    if len(step_times) > 2 and "(" in duration_str:
                        try:
                            length_step = float(extract_number_in_parentheses(duration_str))
                        except Exception:
                            length_step = np.nan
                    elif len(step_times) == 1:
                        length_step = float(step_times[0])
                    else:
                        length_step = np.mean(step_times) if step_times else np.nan
                    label = duration_str

                if np.isnan(length_step):
                    length_step = 35
                    label = "Not specified"
                elif "hours" not in label.lower():
                    label = label + "\nhours"
                else:
                    label = label.replace(" hours", "\nhours")

                if length_step < 35:
                    length_step = 35

                labels_time.append(label)
                lengths.append(length_step)

            total_length = sum(lengths) if lengths else 1.0
            proportions = [l / total_length for l in lengths] if lengths else [1.0]

            for i, prop in enumerate(proportions):
                if prop < 0.1 and len(proportions) > 1:
                    max_index = proportions.index(max(proportions))
                    proportions[i] += 0.05
                    proportions[max_index] -= 0.05
                    if proportions[max_index] < 0.1:
                        proportions[max_index] = 0.1

            columns = st.columns(proportions)

            for i, step_key in enumerate(no_steps):
                if step_key == "0":
                    container_class = "step-container-culturing"
                    label = "Culturing"
                else:
                    container_class = "step-container"
                    label = f"Step {step_key}"

                step_blob = protocol_info.get(str(step_key), "{}")
                step_data = json.loads(step_blob) if isinstance(step_blob, str) else (step_blob or {})

                with columns[i]:
                    st.markdown(f"<p class='small-text' style='text-align: center; font-weight: bold;'>{label}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='small-text' style='text-align: center;'>{labels_time[i]}</p>", unsafe_allow_html=True)

                    step_content = f"""<div class="{container_class}">"""

                    # Basal media
                    if mediacheckbox:
                        media = ""
                        bm = step_data.get("basalMedia", []) or []
                        for j in range(len(bm)):
                            name = bm[j].get("name") if isinstance(bm[j], dict) else None
                            if name and name not in ["-", "NA"]:
                                media += name + ", "
                        media = media.rstrip(", ") or "Not specified"
                        step_content += f"<p><strong>Basal media:</strong></p><p>{media}</p><hr>"

                    # Supplements
                    if supplementscheckbox:
                        supplements = ""
                        ss = step_data.get("SerumAndSupplements", []) or []
                        for j in range(len(ss)):
                            name = ss[j].get("name") if isinstance(ss[j], dict) else None
                            if name and name not in ["-", "NA"]:
                                supplements += name + ", "
                        supplements = supplements.rstrip(", ") or "Not specified"
                        step_content += f"<p><strong>Serum and supplements:</strong></p><p>{supplements}</p><hr>"

                    # Growth factors
                    if gfcheckbox:
                        gf = ""
                        gfs = step_data.get("growthFactor", []) or []
                        for j in range(len(gfs)):
                            name = gfs[j].get("name") if isinstance(gfs[j], dict) else None
                            if name and name not in ["-", "NA"]:
                                gf += name + ", "
                        gf = gf.rstrip(", ") or "Not specified"
                        step_content += f"<p><strong>Growth factors:</strong></p><p>{gf}</p><hr>"

                    # Culture matrix
                    if matrixcheckbox:
                        matrix = ""
                        cm = step_data.get("cultureMatrix", []) or []
                        for j in range(len(cm)):
                            name = cm[j].get("name") if isinstance(cm[j], dict) else None
                            if name and name not in ["-", "NA", "Not given"]:
                                matrix += name + ", "
                        matrix = matrix.rstrip(", ") or "Not specified"
                        step_content += f"<p><strong>Culture matrix:</strong></p><p>{matrix}</p><hr>"

                    step_content += "</div>"

                    # Markers
                    if markerscheckbox and step_key != "0":
                        markers = ""
                        gm = step_data.get("geneMarkers", []) or []
                        for j in range(len(gm)):
                            if not isinstance(gm[j], dict):
                                continue
                            name = gm[j].get("name")
                            if name in ["-", "NA", "Not given", None]:
                                continue

                            markers += name
                            if "geneEnrichment" in gm[j]:
                                if gm[j]["geneEnrichment"] == "upregulated":
                                    markers += " ↑"
                                elif gm[j]["geneEnrichment"] == "downregulated":
                                    markers += " ↓"
                                elif gm[j]["geneEnrichment"] is None:
                                    markers += " (direction not specified)"
                            else:
                                markers += " (direction not specified)"

                            markers += ", "

                        markers = markers.rstrip(", ") or "Not specified"
                        step_content += f"""<div class="readout-container"><p><strong>Readout:</strong></p><p>{markers}</p></div>"""

                    st.markdown(step_content, unsafe_allow_html=True)

            st.markdown("""<hr class="custom-divider">""", unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"Skipping PMID {pmid} | Participant ID {participant_id} due to error: {e}")
            continue

if run:
    plot_data_for_selection(selected_pmid, selected_participants)
else:
    st.info("Select a PMID / Participant, then click **Load / Render selection** to parse and display protocols.")
