import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Log Analysis Tool", layout="wide")
DATA_FILE = 'fe_url_vs_time.csv'

@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

# Correcting the regular expression for time taken and app context extraction
time_taken_regex = re.compile(r'Time Taken in ms= (\d+)')

def extract_details_with_timestamp(data, url_filter, context_depth):
    # Dynamically construct the application context regex based on context depth
    app_context_regex_template = rf'^/([^/]+/?){{0,{context_depth}}}'
    app_context_regex = re.compile(app_context_regex_template)
    
    # Filter data based on URL filter if provided
    if url_filter:
        data = data[data['url'].str.contains(re.escape(url_filter), na=False)]
    
    results = []
    for _, row in data.iterrows():
        url = row['url']
        message = row['message']
        
        app_context_match = re.match(app_context_regex, url)
        time_taken_match = re.search(time_taken_regex, message)
        
        app_context = app_context_match.group(0) if app_context_match else 'App Context Not found'
        time_taken = time_taken_match.group(1) if time_taken_match else 'Time Taken Not found'
        
        results.append({'@timestamp': row['@timestamp'], 'url': url, 'Application Context': app_context, 'Time Taken (ms)': time_taken})
    
    return pd.DataFrame(results)

def to_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue().decode("utf-8")

def main():
    st.title('Log Analysis Tool')
    
    url_filter = st.sidebar.text_input('URL Filter', '')
    context_depth = st.sidebar.slider('Context Depth', 1, 20, 1)
    
    data = load_data(DATA_FILE)
    extracted_details_df = extract_details_with_timestamp(data, url_filter, context_depth)
    
    st.metric("Total URLs Processed", len(extracted_details_df))
    st.write('Filtered and Extracted Details')
    st.dataframe(extracted_details_df, width=1800, height=100)
    
    if not extracted_details_df.empty:
        extracted_details_df['Time Taken (ms)'] = pd.to_numeric(extracted_details_df['Time Taken (ms)'], errors='coerce')
        stats_data = extracted_details_df.dropna(subset=['Time Taken (ms)'])
        stats = stats_data.groupby('Application Context')['Time Taken (ms)'].agg(['min', 'max', 'mean', 'median']).reset_index()
        stats.columns = ['Application Context', 'Min Time (ms)', 'Max Time (ms)', 'Average Time (ms)', 'Median Time (ms)']
        st.write('Performance Statistics')
        st.dataframe(stats, width=1800)
        
        csv_filtered_details = to_csv(extracted_details_df)
        csv_stats = to_csv(stats)
        
        with st.sidebar:
            st.download_button(label="Download Filtered Details as CSV", data=csv_filtered_details, file_name='filtered_details.csv', mime='text/csv')
            st.download_button(label="Download Stats as CSV", data=csv_stats, file_name='stats.csv', mime='text/csv')

if __name__ == "__main__":
    main()
