#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 14:39:33 2024

@author: dogagulek
"""
import os
import pandas as pd
import json
import chardet  # Optional, for encoding detection
import re
import numpy as np
import matplotlib.pyplot as plt
import textwrap


# Load the CSV file into a pandas DataFrame
csv_file='data/submissions.csv'
df = pd.read_csv(csv_file)

# Filter the DataFrame to include only the rows with 'submitted' status
df_submitted = df[df['status'] == 'submitted']


# Iterate through all submitted entries
for index, row in df_submitted.iterrows():
    try:
        # Load the 'merged_data' field for each entry into a dictionary
        dictentry = json.loads(row['merged_data'])

        # Calculate the new step count (subtract 3 as per your logic)
        newstepcount = len(dictentry) - 1 - 1 - 1

        # Rename dictionary keys as required
        dictentry[str(newstepcount)] = dictentry.pop('1000')  # Rename '1000' to new step number
        dictentry['sequencingData'] = dictentry.pop('1001')   # Rename '1001' to 'sequencingData'
        dictentry['cellLine'] = dictentry.pop('-1')           # Rename '-1' to 'cellLine'

        # Save the updated dictionary back into the DataFrame
        df_submitted.at[index, 'merged_data'] = dictentry

    except (KeyError, json.JSONDecodeError) as e:
        # Handle any errors related to missing keys or JSON issues
        print(f"Error processing entry at index {index}: {e}")
        continue

# Save the entire DataFrame as a pickle file
#df_submitted.to_csv('data/processed_submissions.csv')

#%% FUNCTIONS

def process_string(s):
    words = s.split()  # Split the string into words
    num_words = len(words)
    
    if num_words > 2:
        mid_index = num_words // 2  # Find the middle index
        # Join the words, inserting a newline between the two middle words
        processed_string = ' '.join(words[:mid_index]) + '\n' + ' '.join(words[mid_index:])
        return processed_string
    else:
        return s  # Return the string as is if there are 2 or fewer words

# Function to wrap text
def wrap_text(text, max_chars_per_line):
    return "\n".join(textwrap.fill(line, max_chars_per_line) for line in text.splitlines())
#%%
# Define text colors
media_color = 'firebrick'
supplements_color = 'teal'
gf_color = 'indigo'

#get all submitted pmids
pmids = df_submitted.publication_id.unique()

#extract only entries of one paper
paper = pmids[12]



paper_submissions = df_submitted[df_submitted['publication_id'] == paper]

#ax.text(0, 1, f'PMID: {pmid} | Participant ID: {participant_id}', ha='left', fontsize=12)


#for entry in paper_submissions:
entry = paper_submissions.iloc[1]
protocol_info = entry['merged_data']

#Extract information 
participant_id = entry['participant_id']
pmid = entry['publication_id']
cell_line = process_string(json.loads(protocol_info['cellLine'])['cellLineDetails'][0]['cellLineName'].strip().rstrip('.'))
target =  process_string(json.loads(protocol_info['cellLine'])['differentiationTarget'][0]['targetCell'].strip().rstrip('.'))
no_steps = len(protocol_info.keys()) - 2
culturing = ('0' in protocol_info.keys())


# Initialize list to store lengths (duration hours)
lengths = []
labels_time = []
labels_step = []

if (culturing):
   labels_step.append( 'Culturing')

for step in range(1, no_steps):
    labels_step.append('Step '+ str (step))

# Extract durationHours for each step
for i in range(no_steps):
    step_info = json.loads(protocol_info[str(i)])  # Parse the JSON for each 
    step_times = re.findall(r'\d+', json.loads(protocol_info[str(i)])['duration'][0]['durationHours'])
    if (len(step_times) == 1):
        length_step  =  float(step_times[0])
    else: 
        length_step = np.mean([float(time) for time in step_times])
    
    label  =  json.loads(protocol_info[str(i)])['duration'][0]['durationHours']

    if 'hours' not in label:
        label = label + '\nhours'
    else:
        label = label.replace (' hours', '\nhours')
    
    if np.isnan(length_step):
        length_step = 96
        label = 'Duration \nnot specified'
    
    labels_time.append(label)
    lengths.append(length_step)
    
      
x_position = 50
# Set up the plot
fig, ax = plt.subplots(figsize=(30, 4))  # Adjust the figure size for better readability

ax.add_patch(plt.Rectangle((0, 0), x_position, 0.6, edgecolor='white', facecolor='white'))

x_position_start = x_position
rect_positions = [] 
# Plot each rectangle and add labels
for i, length in enumerate(lengths):
    
    if(culturing) & (i == 0):
        ax.add_patch(plt.Rectangle((x_position, 0), length * 3, 0.8, edgecolor='white', facecolor='moccasin'))
    else:
        ax.add_patch(plt.Rectangle((x_position, 0), length * 3, 0.8, edgecolor='white', facecolor='lavender'))

    
    # Add time label centered below each rectangle
    ax.text(x_position + (length * 3) / 2, -0.07, labels_time[i], ha='center', va='top')
    # Add step label centered above each rectangle
    ax.text(x_position + (length * 3) / 2, 0.9, labels_step[i], ha='center', va='top')
    
    
    #Basal media
    media = ''
    for j in range(len(json.loads(protocol_info[str(i)])["basalMedia"])):
        if json.loads(protocol_info[str(i)])["basalMedia"][j]["name"] != '-':
            media = media + json.loads(protocol_info[str(i)])["basalMedia"][j]["name"]
            if j!= len(json.loads(protocol_info[str(i)])["basalMedia"])-1:
               media = media + ', '
            
    #supplements
    supplements = ''
    for j in range(len(json.loads(protocol_info[str(i)])['SerumAndSupplements'])):
        if json.loads(protocol_info[str(i)])['SerumAndSupplements'][j]["name"] != '-':
            supplements =  supplements + json.loads(protocol_info[str(i)])['SerumAndSupplements'][j]["name"]
            if j!= len(json.loads(protocol_info[str(i)])['SerumAndSupplements'])-1:
                supplements =  supplements + ', '
    
    #growth factors
    gf = ''
    for j in range(len(json.loads(protocol_info[str(i)])['growthFactor'])):
        if json.loads(protocol_info[str(i)])['growthFactor'][j]["name"] != '-':
            gf  = gf + json.loads(protocol_info[str(i)])['growthFactor'][j]["name"]
            if j!= len(json.loads(protocol_info[str(i)])['growthFactor'])-1:
                gf  = gf  + ', '
    

    # Calculate a rough max character length for wrapping based on rectangle width
    max_chars_per_line = int((length * 3) / 5)  # Adjust this value based on font size and scaling
    # Wrap the text for each string
    wrapped_media = wrap_text(media, max_chars_per_line)
    wrapped_supplements = wrap_text(supplements, max_chars_per_line)
    wrapped_gf = wrap_text(gf, max_chars_per_line)
    
    # Add the text to the rectangle in different colors
    y_position = 0.7 # Adjust the y position for each text block
    ax.text(x_position + 5, y_position, wrapped_media, ha='left', va='top', fontsize=10, color=media_color)
    y_position -=0.1  # Move down for the next text block
    ax.text(x_position + 5, y_position, wrapped_supplements, ha='left', va='top', fontsize=10, color=supplements_color)
    y_position -= 0.1  # Move down for the next text block
    ax.text(x_position + 5 + (length * 3) / 2, y_position, wrapped_gf, ha='left', va='top', fontsize=10, color=gf_color)
    
    
    # Store x_position to calculate midpoints for arrows
    rect_positions.append(x_position + length * 3)
    
    # Move x_position for the next rectangle to be stacked horizontally
    x_position += length *3
    
#annotate cell line and target
# Move cell_line text to the left, outside of the rectangle
ax.annotate('', xy=(x_position_start+10, 0.45), xytext=(x_position_start, 0.45), arrowprops=dict(facecolor='black', shrink=0.05))
ax.text(0, 0.45, cell_line, ha='center', va='center', fontsize=10)
# Move target text to the right, outside of the rectangle
ax.annotate('', xy=(x_position, 0.45), xytext=(x_position-10, 0.45), arrowprops=dict(facecolor='black', shrink=0.05))
ax.text(x_position + 15, 0.45, target, ha='left', va='center', fontsize=10)

# Add arrows between the rectangles
for i in range(1, len(rect_positions)):
    mid_x = rect_positions[i - 1]
    ax.annotate('', xy=(mid_x+10, 0.87), xytext=(mid_x ,0.87), arrowprops=dict(facecolor='black', shrink=0.04))


# Add PMID and Participant ID at the top
ax.text(0, 1, f'Participant ID: {participant_id}', ha='left', fontsize=12)

# Remove x-axis and y-axis labels and ticks
ax.set_xticks([])  # Remove x-axis ticks
ax.set_yticks([])  # Remove y-axis ticks
ax.set_xlabel('')  # Remove x-axis label
ax.set_ylabel('')  # Remove y-axis label

# Adjust the x-axis limit based on the total length
ax.set_xlim(0, sum(lengths) * 3 + 50)  # Add some padding for better readability

# Remove spines to clean up the look
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)

# Show the plot
plt.show()