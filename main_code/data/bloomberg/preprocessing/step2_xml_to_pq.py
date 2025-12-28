# this script converts Bloomberg XML files to parquet format

import xml.etree.ElementTree as ET
import pandas as pd
import os
from datetime import datetime

def parse_bloomberg_story(content):
    """Parse a single ContentT element containing a story."""
    story_data = {
        'eid': content.get('EID'),
        'capture_time': content.get('CaptureTime'),
        'origin': content.get('Origin'),
        'event': None,
        'story_id': None,
        'body': None,
        'body_text_type': None,
        'version': None,
        'wire_id': None,
        'class_num': None,
        'wire_name': None,
        'headline': None,
        'time_of_arrival': None,
        'language_id': None,
        'language_string': None,
        'hot_level': None,
        'web_url': None,
        'assignedtopics': [],
        'derivedtickers': [],
        'derivedtickers_scores': [],
        'derivedtopics': [],
        'derivedtopics_scores': [],
        'derivedpeople': [],
        'derivedpeople_scores': []
    }
    
    # Extract story content
    story_content = content.find('StoryContent')
    if story_content is not None:
        # Get SUID
        id_elem = story_content.find('.//SUID')
        if id_elem is not None:
            story_data['story_id'] = id_elem.text
            
        # Get Event
        event_elem = story_content.find('Event')
        if event_elem is not None:
            story_data['event'] = event_elem.text
        
        # Get Story elements
        story = story_content.find('Story')
        if story is not None:
            # Basic story elements
            body = story.find('Body')
            story_data['body'] = body.text if body is not None else None
            
            body_type = story.find('BodyTextType')
            story_data['body_text_type'] = body_type.text if body_type is not None else None
            
            version = story.find('Version')
            story_data['version'] = version.text if version is not None else None
            
            # Metadata
            metadata = story.find('Metadata')
            if metadata is not None:
                story_data['wire_id'] = metadata.find('WireId').text if metadata.find('WireId') is not None else None
                story_data['class_num'] = metadata.find('ClassNum').text if metadata.find('ClassNum') is not None else None
                story_data['wire_name'] = metadata.find('WireName').text if metadata.find('WireName') is not None else None
                story_data['headline'] = metadata.find('Headline').text if metadata.find('Headline') is not None else None
                story_data['time_of_arrival'] = metadata.find('TimeOfArrival').text if metadata.find('TimeOfArrival') is not None else None
            
            # Language
            story_data['language_id'] = story.find('LanguageId').text if story.find('LanguageId') is not None else None
            story_data['language_string'] = story.find('LanguageString').text if story.find('LanguageString') is not None else None
            
            # Hot Level
            hot_level = story.find('HotLevel')
            story_data['hot_level'] = hot_level.text if hot_level is not None else None
            
            # Web URL
            web_url = story.find('WebURL')
            story_data['web_url'] = web_url.text if web_url is not None else None
            
            # Derived Data
            for derived_type in ['DerivedTickers', 'DerivedTopics', 'DerivedPeople']:
                base_key = derived_type.lower()
                for entity in story.findall(f'.//{derived_type}/ScoredEntity'):
                    id_elem = entity.find('Id')
                    score_elem = entity.find('Score')
                    if id_elem is not None:
                        story_data[base_key].append(id_elem.text)
                        if score_elem is not None:
                            story_data[f'{base_key}_scores'].append(score_elem.text)
                        else:
                            story_data[f'{base_key}_scores'].append(None)
    
    # Convert lists to pipe-separated strings
    for key in ['derivedtickers', 'derivedtickers_scores', 
                'derivedtopics', 'derivedtopics_scores',
                'derivedpeople', 'derivedpeople_scores']:
        story_data[key] = '|'.join(map(str, story_data[key])) if story_data[key] else None
    
    return story_data

def convert_xml_to_parquet(xml_file, output_file, error_log_file):
    """Convert a Bloomberg XML file to parquet format."""
    print(f"Processing {xml_file}")
    
    try:
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Get archive metadata
        archive_start = root.get('StartTime')
        archive_end = root.get('EndTime')

        # Extract stories
        stories = []
        for content in root.findall('.//ContentT'):
            story_data = parse_bloomberg_story(content)
            # Add archive metadata
            story_data['archive_start_time'] = archive_start
            story_data['archive_end_time'] = archive_end
            stories.append(story_data)

        # Convert to DataFrame
        df = pd.DataFrame(stories)

        # Convert timestamps to datetime
        timestamp_cols = ['capture_time', 'time_of_arrival', 'archive_start_time', 'archive_end_time']
        for col in timestamp_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])

        # Save to parquet
        df.to_parquet(output_file, compression='snappy')
        print(f"Saved {len(df)} stories to {output_file}")
        
    except Exception as e:
        # Log the error and file name if an exception occurs
        with open(error_log_file, 'a') as log:
            log.write(f"Error processing {xml_file}: {str(e)}\n")
        print(f"Error processing {xml_file}. Check the error log for details.")
        
    return None  # Return None to indicate an error occurred (no DataFrame returned)

# Process multiple files
def process_directory(input_dir, output_dir, error_log_file="error_log.txt"):
    """Process all XML files in a directory."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure the error log file is created or cleared before starting
    with open(error_log_file, 'w') as log:
        log.write("Error Log - Processed Files with Errors\n")
    
    xml_files = [f for f in os.listdir(input_dir) if f.endswith('.xml')]
    
    for xml_file in xml_files:
        input_path = os.path.join(input_dir, xml_file)
        output_path = os.path.join(output_dir, xml_file.replace('.xml', '.parquet'))
        
        if os.path.exists(output_path):
            print(f"Skipping {xml_file} - already processed")
            continue
        
        # Call the function, passing the error log file
        convert_xml_to_parquet(input_path, output_path, error_log_file)

# Usage example
input_dir = "H:/data_common_master/Bloomberg_News/xml/"
output_dir = "H:/data_common_master/Bloomberg_News/parquet/"
process_directory(input_dir, output_dir)
# input_dir = "path/to/xml/files"
# output_dir = "path/to/output/parquet"
# process_directory(input_dir, output_dir)