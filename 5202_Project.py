# Find the process using port 8050
# lsof -i :8050
# Kill this process
# kill -9 {PID}
# eg. kill -9 11300

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import io
import base64
import tabulate
import plotly.express as px

app = dash.Dash(__name__)

# Generate dropdown options for hours (0-23) and minutes (0-59)
hour_options = [{'label': str(i).zfill(2), 'value': str(i).zfill(2)} for i in range(24)]
minute_options = [{'label': str(i).zfill(2), 'value': str(i).zfill(2)} for i in range(60)]


# Layout of the dashboard
app.layout = html.Div(children=[
    html.H1(children='My Data Dashboard',
            style={
            'textAlign': 'center'
            }
        ),
    
    # Upload button
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File'),
        multiple=False
    ),

    # Text to display summary
    html.Div(id='data-summary-text',
             style={'width': '100%'}),

    # Times-series analysis
    html.Div([
        dcc.DatePickerRange(
            id='date-picker-range',
            display_format='MM/DD/YYYY',  # Include date only
            start_date=pd.to_datetime('12/01/2010').strftime('%Y-%m-%d'),  # Set default to 12/01/2010
            #start_date=pd.to_datetime('today').strftime('%Y-%m-%d'),  # Set default to today's date
            end_date=pd.to_datetime('today').strftime('%Y-%m-%d'),  # Set default to today's date
            style={'width': '50%'}  # Set the width to 50%
        ),
        html.Label('Select Time Range:'),
        dcc.RangeSlider(
            id='time-range-slider',
            marks={i: {'label': str(i).zfill(2)} for i in range(24)},
            min=0,
            max=23,
            step=1,
            value=[0, 23]
        ),
    ], style={'width': '80%', 'margin': 'auto'}),  # Set an explicit width and center the date picker

    # Pie chart
    dcc.Graph(id='pie-chart'),

    # Bar graph
    dcc.Graph(id='bar-graph'),
    
    # Text to display
    html.Div(id='text-to-display',
             style={'width': '100%'}),

    # Display filtered_df
    html.Div(id='filtered-data-display',
             style={'width': '100%', 'whiteSpace': 'pre-line'}),

])


# Callback to update the graph based on the uploaded file
@app.callback(
    Output('data-summary-text', 'children'),
    Output('text-to-display', 'children'),
    Output('filtered-data-display', 'children'),
    Output('pie-chart', 'figure'),
    Output('bar-graph', 'figure'),
    Input('upload-data', 'contents'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('time-range-slider', 'value'),
)

def update_summary(contents, start_date, end_date, selected_time_range):
    
    if contents is None:
        return 'Upload a file to see the summary.', "", "", px.pie(), px.bar()

    # Read the uploaded CSV file
    content_type, content_string = contents.split(',')
    decoded = io.StringIO(base64.b64decode(content_string).decode('latin1'))
    df = pd.read_csv(decoded)

    # Convert 'InvoiceDate' to datetime format
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], format='%m/%d/%Y %H:%M', errors='coerce')
    
    # Convert selected start and end dates along with hours and minutes to pandas Timestamp objects
    start_datetime = pd.to_datetime(start_date, format='%Y-%m-%d', errors='coerce') + pd.to_timedelta(selected_time_range[0], unit='h')
    end_datetime = pd.to_datetime(end_date, format='%Y-%m-%d', errors='coerce') + pd.to_timedelta(selected_time_range[-1], unit='h')

    date_msg = f"From {start_datetime} to {end_datetime}."
    
    # Filter data based on selected date range
    filtered_df = df[(df['InvoiceDate'] >= start_datetime) & (df['InvoiceDate'] <= end_datetime)]

    # Get summary information
    num_rows = len(df)
    summary_msg = f"The uploaded file contains {num_rows} rows."
    filtered_rows = len(filtered_df)
    filtered_msg = f"The selected date range contains {filtered_rows} rows."
    final_msg = summary_msg + '\n' +filtered_msg

    # Display filtered_df as text in html.Div
    filtered_df_display = html.Div([
        html.Hr(),
        html.H4("Filtered Data:"),
        dcc.Markdown(f"Number of rows: {filtered_rows}"),
        dcc.Markdown(filtered_df.to_markdown())
    ])

    # Calculate percentage distribution of countries within the filtered DataFrame
    country_percentages = (filtered_df['Country'].value_counts() / filtered_rows) * 100
    country_msg = f"{country_percentages}."

    # Check if the filtered DataFrame is not empty
    if filtered_rows > 0:
        # Create a pie chart using plotly express
        pie_chart = px.pie(names=country_percentages.index, values=country_percentages, title='Distribution by Country')

        # Create a bar graph using plotly express
        bar_graph = px.bar(
            x=filtered_df['Country'].value_counts().index,
            y=filtered_df['Country'].value_counts().values,
            labels={'x': 'Country', 'y': 'Frequency'},
            title='Frequency of Each Country'
        )

        # Adjust the width of the bars in the bar graph
        bar_graph.update_layout(bargap=0.8)
        
    else:
        # If the filtered DataFrame is empty, create an empty pie chart and bar graph
        pie_chart = px.pie(title='Distribution by Country')
        bar_graph = px.bar(title='Frequency of Each Country')
    
    return final_msg, date_msg, filtered_df_display, pie_chart, bar_graph


    """
    decoded = None
    if 'csv' in filename:
        # Decode CSV file
        decoded = pd.read_csv(StringIO(content_string))
    elif 'xls' in filename:
        # Decode Excel file
        decoded = pd.read_excel(BytesIO(content_string))

    print(f'Decoded DataFrame: {decoded}')
        
    if decoded is None or decoded.empty:
        return f'Invalid or empty file. Upload a valid file. Decoded: {decoded}'

    print('File read.')
    
    
    # Calculate total sales per country
    total_sales_per_country = decoded.groupby('Country')['Quantity'].sum()

    # Create a summary text
    summary_text = f'Total Sales per Country:\n\n{total_sales_per_country}'

    return summary_text
    """
    
if __name__ == '__main__':
    app.run_server(debug=True)
