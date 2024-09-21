import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import json
import numpy as np
import re

# Load the CSV file into a pandas DataFrame
csv_file='data/submissions.csv'
df = pd.read_csv(csv_file)


# Inject custom CSS
st.markdown(
    """
    <style>
    .step-container-culturing {
        padding: 10px;
        border-radius: 10px;
        background-color: #FFD9AD; /* Light orange background */
        margin-bottom: 20px;
        color: black; /* Text color for light blue box */
    }
    .step-container {
        padding: 10px;
        border-radius: 10px;
        background-color:  #DFE5FF; /* Light blue background */
        margin-bottom: 20px;
        color: black; /* Text color for white box */
        border: 1px solid #E0E0E0; /* Optional border for the white box */
    }
    .participant-container {
        padding: 5px; /* Slightly increase padding for better appearance */
        border-radius: 10px; /* Increase this value to make the box more rounded */
        background-color: #FFFFF; /* Light grey background */
        margin-bottom: 5px;
    }
    .participant-title {
        font-size: 20px; /* Increase the title size */
        font-weight: bold;
        text-align: center;
    
    }
    .custom-divider {
        border: none;
        height: 20px;
        background-color: #001158; /* Custom divider color */
        margin: 0px 0; /* Adds spacing above and below the divider */
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
        font-size: 60px; /* Make the arrow larger */
        margin: 0 auto;
        line-height: 1; /* Reduce line height to ensure it's tightly packed */
        align-items: center;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True
)

def extract_number_in_parentheses(input_string):
    # Use regular expression to find the number inside parentheses
    match = re.search(r'\((\d+)h\)', input_string)
    
    if match:
        # Return the number found inside parentheses
        return match.group(1)
    else:
        # Return None or some other default value if no match is found
        return None
    
def process_string(s):
    return re.sub(r'\s+', ' ', s) 

def convert_number_words_to_digits(input_string):
    # Dictionary to map number words to their corresponding integer values
    number_words = {
        'one': '1',
        'two': '2',
        'three': '3',
        'four': '4',
        'five': '5',
        'six': '6',
        'seven': '7',
        'eight': '8',
        'nine': '9',
        'ten': '10',
        'eleven': '11',
        'twelve': '12'
    }

    # Split the string into words
    words = input_string.split()

    # Replace any word that matches a key in the number_words dictionary
    converted_words = [number_words.get(word.lower(), word) for word in words]

    # Join the words back into a single string
    converted_string = ' '.join(converted_words)

    return converted_string

def is_empty_or_null(item):
    if isinstance(item, dict):
        return all(is_empty_or_null(v) for v in item.values())
    elif isinstance(item, list):
        return all(is_empty_or_null(v) for v in item)
    else:
        return item in [None, "", False]


# Filter the DataFrame to include only the rows with 'submitted' status
df_submitted = df[df['status'] == 'submitted'].reset_index(drop=True)


# Iterate through all submitted entries
for index, row in df_submitted.iterrows():
   # Load the 'merged_data' field for each entry into a dictionary
    dictentry = json.loads(row['merged_data'])
    ## REMOVE EMPTY KEYS
    # Function to check if all values in a nested dictionary are empty or None

    # List of keys to retain (will ignore these in the deletion)
    keys_to_retain = ['0', '1001', '-1']

    # List to store keys to remove
    keys_to_remove = []

    # Iterate over the dictionary
    for key, value in dictentry.items():
        if key not in keys_to_retain:
            # Convert the inner JSON string into a dictionary
            inner_dict = json.loads(value)
            
            # Check if all values in the inner dictionary are empty or null
            if is_empty_or_null(inner_dict):
                keys_to_remove.append(key)

    # Remove the keys with empty inner dictionaries
    for key in keys_to_remove:
        del dictentry[key]
    # Calculate the new step count (subtract 3 as per your logic)
    newstepcount = len(dictentry) - 1 - 1 - 1

     # Check and rename '1000' to the new step count
    if '1000' in dictentry:
        dictentry[str(newstepcount)] = dictentry.pop('1000')
    else:
        print ('error changing key 1000')
    
    # Check and rename '1001' to 'sequencingData'
    if '1001' in dictentry:
        dictentry['sequencingData'] = dictentry.pop('1001')
    else:
        print ('error changing key 1000')

    # Check and rename '-1' to 'cellLine'
    if '-1' in dictentry:
        dictentry['cellLine'] = dictentry.pop('-1')
    else:
        print ('error changing key 1000')
        
    # Save the updated dictionary back into the DataFrame
    df_submitted.at[index, 'merged_data'] = dictentry
    

st.title('Differentiation protocols')

#get all submitted pmids
pmids = df_submitted.publication_id.unique()
selected_pmid = st.selectbox("Select a PMID", pmids)


def plot_data_for_pmid(paper):

    st.subheader(f"PMID: {paper}")
    st.markdown(f"""<hr class="custom-divider">""", unsafe_allow_html=True)
    
    paper_submissions = df_submitted[df_submitted['publication_id'] == paper]
    
    for submission in range(len(paper_submissions)):
        entry = paper_submissions.iloc[submission]
        protocol_info = entry["merged_data"]
        participant_id = entry['participant_id']
        
        # Display Participant Information inside a box with step information
        st.markdown(f"""
            <div class="participant-container">
                <p class="participant-title"><strong>Participant ID: {participant_id}</strong></p>
            </div>
        """, unsafe_allow_html=True)
        
        # Extract cells of origin and target cells
        cell_lines = ', '.join([
                process_string(json.loads(protocol_info['cellLine'])['cellLineDetails'][i]['cellLineName'].strip().rstrip('.'))
                for i in range(len(json.loads(protocol_info['cellLine'])['cellLineDetails'])) if json.loads(protocol_info['cellLine'])['cellLineDetails'][i]['cellLineName']
            ])
        
        if cell_lines == '':
            cell_lines = 'Not specified'

        target = ', '.join([
            process_string(json.loads(protocol_info['cellLine'])['differentiationTarget'][i]['targetCell'].strip().rstrip('.'))
            for i in range(len(json.loads(protocol_info['cellLine'])['differentiationTarget'])) if json.loads(protocol_info['cellLine'])['differentiationTarget'][i]['targetCell']
        ])
        
        if target == '':
            target = 'Not specified'
        
        # Display two boxes with an arrow in between them
        col1, col2, col3 = st.columns([5, 0.5, 5])  # Adjusted column widths for the arrow
        
        with col1:
            st.markdown(f"""
                <div class="cell-box">
                    <strong>Cells of Origin:</strong><br>
                    {cell_lines}
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div class="arrow-box">
                   <span style='font-size:70px;'>&#8594;</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
                <div class="cell-box">
                    <strong>Target Cells:</strong><br>
                    {target}
                </div>
            """, unsafe_allow_html=True)
        
        
        no_steps = list(protocol_info.keys())
        no_steps.remove('sequencingData')
        no_steps.remove('cellLine')
        culturing =json.loads( protocol_info['0'])["culturingProtocol"][0]["isGiven"]
        if (culturing == False):
            no_steps.remove('0')
        
        # Initialize lists for lengths and labels
        lengths = []
        labels_time = []
        labels_step = []
        
        # Extract durationHours for each step
        for i in no_steps:
            step_info = json.loads(protocol_info[str(i)])  # Parse the JSON for each step
            duration_str = json.loads(protocol_info[str(i)])['duration'][0]['durationHours']
        
            duration_str = convert_number_words_to_digits(duration_str)
        
            # Check if the duration is in weeks, days, or hours
            if 'week' in duration_str.lower():
                step_times = re.findall(r'\d+', duration_str)
                if len(step_times) == 1:
                    length_step = float(step_times[0]) * 7 * 24
                else:
                    length_step = np.mean([float(time) * 7 * 24 for time in step_times])
                label = f"{int(length_step)} hours"
                
            elif 'day' in duration_str.lower():
                step_times = re.findall(r'\d+', duration_str)
                if len(step_times) == 1:
                    length_step = float(step_times[0]) * 24
                else:
                    length_step = np.mean([float(time) * 24 for time in step_times])
                label = f"{int(length_step)} hours"
            
            elif len(re.findall(r'\d+', duration_str)) == 0 or duration_str == '0':
                length_step = np.nan
            
            else:
                step_times = re.findall(r'\d+', duration_str)
                if len(step_times) >2:
                    if ('(' in duration_str):
                        length_step = float(extract_number_in_parentheses(duration_str))
                elif len(step_times) == 1:
                    length_step = float(step_times[0])
                else:
                    length_step = np.mean([float(time) for time in step_times])
                label = duration_str
        
            if np.isnan(length_step):
                length_step = 35  # Default length if unspecified
                label = 'Not specified'
                    
            elif 'hours' not in label.lower():
                label = label + '\nhours'
            else:
                label = label.replace(' hours', '\nhours')
        
            if length_step <35:
                length_step = 35
        
            labels_time.append(label)
            lengths.append(length_step)
        
        # Normalize lengths to calculate proportions for column widths
        total_length = sum(lengths)
        proportions = [length / total_length for length in lengths]
        
        # Adjust proportions if any value is less than 0.1
        for i, prop in enumerate(proportions):
            if prop < 0.1:
                # Find the index of the maximum element in proportions
                max_index = proportions.index(max(proportions))
                
                # Add 0.1 to the current element
                proportions[i] += 0.1
                
                # Subtract 0.1 from the maximum element
                proportions[max_index] -= 0.1
        
                # Ensure that the maximum element doesn't drop below 0.1 after adjustment
                if proportions[max_index] < 0.1:
                    proportions[max_index] = 0.1
        
        # Display the steps with proportional widths
        columns = st.columns(proportions)
        
        # Render each step inside the appropriate column
        for i in range(len(no_steps)):
            if no_steps[i] == '0':
                container_class = "step-container-culturing"
                label = 'Culturing'
            else:
                container_class = "step-container"
                label = f"Step {no_steps[i]}"
        
            with columns[i]:
                # Display the step label above the container with small font size
                st.markdown(f"<p class='small-text' style='text-align: center; font-weight: bold;'>{label}</p>", unsafe_allow_html=True)
        
                # Display the duration (labels_time) underneath the step label
                st.markdown(f"<p class='small-text' style='text-align: center;'>{labels_time[i]}</p>", unsafe_allow_html=True)
        
                # Build HTML content for the step container
                step_content = f"""
                <div class="{container_class}">
                    <p><strong>Basal media:</strong></p>
                """
                # Basal media
                media = ''
                try:
                    iterate = list(json.loads(protocol_info[no_steps[i]])["basalMedia"].keys())
                except AttributeError:
                    iterate =  range(len(json.loads(protocol_info[no_steps[i]])["basalMedia"]))
                for j in iterate:
                    if json.loads(protocol_info[no_steps[i]])["basalMedia"][j]["name"]:
                        if json.loads(protocol_info[no_steps[i]])["basalMedia"][j]["name"] not in ['-', 'NA']:
                            media += json.loads(protocol_info[no_steps[i]])["basalMedia"][j]["name"]
                            if j != iterate[-1]:
                                media += ', '
                if media == '':
                    media = 'Not specified'
                step_content += f"<p>{media}</p><hr>"
        
               # Supplements
                supplements = ''
                try:
                    iterate_supplements = list(json.loads(protocol_info[no_steps[i]])["SerumAndSupplements"].keys())
                except AttributeError:
                    iterate_supplements = range(len(json.loads(protocol_info[no_steps[i]])["SerumAndSupplements"]))
                for j in iterate_supplements:
                    if json.loads(protocol_info[no_steps[i]])["SerumAndSupplements"][j]["name"] not in ['-', 'NA']:
                        supplements += json.loads(protocol_info[no_steps[i]])["SerumAndSupplements"][j]["name"] 
                        if j != iterate_supplements[-1]:
                            supplements += ', '
                
                if supplements == '':
                    supplements = 'Not specified'
        
                step_content += f"<p><strong>Serum and supplements:</strong></p><p>{supplements}</p><hr>"
        
                # Growth factors
                gf = ''
                try:
                   iterate_gf = list(json.loads(protocol_info[no_steps[i]])["growthFactor"].keys())
                except AttributeError:
                   iterate_gf = range(len(json.loads(protocol_info[no_steps[i]])["growthFactor"]))
                for j in iterate_gf:
                    if json.loads(protocol_info[no_steps[i]])["growthFactor"][j]["name"] not in ['-', 'NA']:
                        gf += json.loads(protocol_info[no_steps[i]])["growthFactor"][j]["name"]
                        if j != iterate_gf[-1]:
                            gf += ', '
        
                if gf == '':
                    gf = 'Not specified'
        
                step_content += f"<p><strong>Growth factors:</strong></p><p>{gf}</p><hr>"


                 # Growth factors
                matrix = ''
                if ("cultureMatrix") in json.loads(protocol_info[no_steps[i]]).keys():
                    try:
                        iterate_mat = list(json.loads(protocol_info[no_steps[i]])["cultureMatrix"].keys())
                    except AttributeError:
                        iterate_mat = range(len(json.loads(protocol_info[no_steps[i]])["cultureMatrix"]))
                    for j in iterate_mat:
                        if json.loads(protocol_info[no_steps[i]])["cultureMatrix"][j]["name"] not in ['-', 'NA']:
                            matrix += json.loads(protocol_info[no_steps[i]])["cultureMatrix"][j]["name"]
                            if j != iterate_mat[-1]:
                                matrix += ', '
        
                if matrix == '':
                    matrix = 'Not specified'
        
                step_content += f"<p><strong>Culture matrix:</strong></p><p>{matrix}</p></div>"
        
                # Render the HTML content inside the container
                st.markdown(step_content, unsafe_allow_html=True)
                
        st.markdown(f"""<hr class="custom-divider">""", unsafe_allow_html=True)
    
    
plot_data_for_pmid(selected_pmid)
