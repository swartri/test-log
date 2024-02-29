import streamlit as st
import pandas as pd
import re
import zipfile

DATA_ZIP = 'url_vs_time.zip'

@st.cache_data
def load_and_filter_data(zip_path):
    exclude_url_pattern = 'http://erp-sys-apigateway:8765/error'
    all_extracted_details = pd.DataFrame()

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.csv'):
                with zip_ref.open(file_name) as file:
                    data = pd.read_csv(file)
                    # Filter out rows where 'message' contains the exclude_url_pattern
                    data = data[~data['message'].str.contains(exclude_url_pattern, na=False)]
                    all_extracted_details = pd.concat([all_extracted_details, data], ignore_index=True)
    
    return all_extracted_details

def process_data_frame(data, context_depth, url):
    data['URL'] = data['message'].str.extract(r'(http://[^ ,]+)')[0].str.rstrip(',')
    app_context_regex = rf'http://[^/]+/([^/]+(?://?[^/, ]+){{0,{context_depth}}})'
    data['Application Context'] = data['message'].str.extract(app_context_regex)[0]
    data['Time Taken (ms)'] = pd.to_numeric(data['message'].str.extract(r'Time Taken in ms= (\d+)')[0], errors='coerce')
    data = data[data['URL'] == url].dropna(subset=['Time Taken (ms)'])
    return data[['@timestamp', 'URL', 'Application Context', 'Time Taken (ms)']]

def main():
    st.set_page_config(page_title="Log Analysis Tool", layout="wide")
    st.title('Log Analysis Tool')

    context_depth = st.sidebar.slider('Select the context depth', 0, 20, 0)
    
    # Load and filter data
    all_extracted_details = load_and_filter_data(DATA_ZIP)

    unique_contexts = all_extracted_details['message'].str.extract(r'http://[^/]+/([^/]+)')[0].dropna().unique()
    selected_context = st.selectbox('Select an Application Context:', options=[''] + sorted(unique_contexts))

    if selected_context:
        context_specific_urls = all_extracted_details[all_extracted_details['message'].str.contains(selected_context, na=False)]['message'].str.extract(r'(http://[^ ,]+)')[0].dropna().unique()
        selected_url = st.selectbox('Select a URL:', options=[''] + sorted(context_specific_urls))

        if selected_url:
            processed_data = process_data_frame(all_extracted_details, context_depth, selected_url)
            if not processed_data.empty:
                stats = processed_data.groupby('Application Context')['Time Taken (ms)'].agg(['min', 'max', 'median', 'mean']).reset_index()
                stats.columns = [f"{col} (ms)" if col not in ['Application Context'] else col for col in stats.columns]
                st.metric(label="Total URLs Processed", value=len(processed_data))
                st.write('Extracted Details')
                st.dataframe(processed_data, width=1800, height=100)
                st.write('Performance Statistics')
                st.dataframe(stats, width=1800)

                # Download buttons
                with st.sidebar:
                    st.download_button("Download Extracted Details as CSV", data=processed_data.to_csv(index=False), file_name='extracted_details.csv', mime='text/csv')
                    st.download_button("Download Statistics as CSV", data=stats.to_csv(index=False), file_name='statistics.csv', mime='text/csv')
            
if __name__ == "__main__":
    main()
