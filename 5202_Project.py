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
from datetime import datetime
import tabulate
import plotly.express as px

app = dash.Dash(__name__)


# Layout of the dashboard
app.layout = html.Div(children=[
    html.H1(children='Games Dashboard',
            style={
            'textAlign': 'center'
            }
        ),
    
    # Upload button
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File'),
        multiple=False # Restrict to single file upload
    ),

    dcc.DatePickerRange(
        id='date-picker-range',
        display_format='YYYY-MM-DD',
        start_date='1900-01-01',  # Set default start date to 1900-01-01
        end_date=datetime.today().strftime('%Y-%m-%d'),  # Set default end date to today's date
        style={'margin': '20px 0'}
    ),
    
    # Text to display summary
    html.Div(id='data-summary-text',
             style={'width': '100%'}),

    # Containers for the six metrics
    html.Div(id='metrics-container', style={'display': 'flex', 'justifyContent': 'space-around', 'flexWrap': 'wrap', 'gap': '20px'}, children=[
        html.Div(children=[
            html.H4("Number of Games"),
            html.Div(id='num-games', className='metric-box')
        ], className='metric-container'),
        
        html.Div(children=[
            html.H4("Average Plays"),
            html.Div(id='avg-plays', className='metric-box')
        ], className='metric-container'),
        
        html.Div(children=[
            html.H4("Average Rating"),
            html.Div(id='avg-rating', className='metric-box')
        ], className='metric-container'),
        
        html.Div(children=[
            html.H4("Number of Descriptions"),
            html.Div(id='num-description', className='metric-box')
        ], className='metric-container')
    ])

], style={'backgroundColor': '#f0f0f0'})

# Add the below into containers section when data combined
"""
        html.Div(children=[
            html.H4("Number of Genres"),
            html.Div(id='num-genres', className='metric-box')
        ], className='metric-container'),

        html.Div(children=[
            html.H4("Number of Developers"),
            html.Div(id='unique-developers', className='metric-box')
        ], className='metric-container'),
"""


# Callback to update the graph based on the uploaded file
@app.callback(
    [Output('data-summary-text', 'children'),
     Output('num-games', 'children'),
     #Output('num-genres', 'children'),
     #Output('unique-developers', 'children'),
     Output('avg-plays', 'children'),
     Output('avg-rating', 'children'),
     Output('num-description', 'children')],
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)

def update_summary(content, filename, start_date, end_date):

    # Initial placeholders for the statistics
    num_games = avg_plays = avg_rating = num_description = 'N/A'
    # When data combined, use: num_games = num_genres = unique_developers = avg_plays = avg_rating = num_description = 'N/A'
    
    if content is None:
        return 'Upload a file to see the summary.', num_games, avg_plays, avg_rating, num_description
        # When data combined, use: return 'Upload a file to see the summary.', num_games, num_genres, unique_developers, avg_plays, avg_rating, num_description

    # Decode the uploaded file
    content_type, content_string = content.split(',')
    decoded = io.StringIO(base64.b64decode(content_string).decode('utf-8'))
    df = pd.read_csv(decoded)
    # Give a summary of the file
    summary_text = f'{filename} contains {len(df)} rows.'

    # Filter according to date selection
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
    # Overview of data within the selected date range
    num_games = len(filtered_df)
    #num_genres = filtered_df['genre'].nunique()
    #unique_developers = filtered_df['developer'].nunique()
    avg_plays = round(filtered_df['plays'].mean(), 2)
    avg_rating = round(filtered_df['rating'].mean(), 2)
    num_description = filtered_df['description'].notna().sum()

    
    return summary_text, num_games, avg_plays, avg_rating, num_description
    # When data combined, use: return summary_text, num_games, num_genres, unique_developers, avg_plays, avg_rating, num_description

    
if __name__ == '__main__':
    app.run_server(debug=True)
