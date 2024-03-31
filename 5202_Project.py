# Find the process using port 8050
# lsof -i :8050
# Kill this process
# kill -9 {PID}
# eg. kill -9 11300

import dash
from dash import dcc, html, State, callback_context
from dash.dependencies import Input, Output
import pandas as pd
import io
import base64
from datetime import datetime
import tabulate
import plotly.express as px


#新增：cluster analysis所需要的安装包
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from dash.exceptions import PreventUpdate
from dash import dash_table
from dash.dash_table.Format import Format 

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
            html.H4("Number of Genres"),
            html.Div(id='num-genres', className='metric-box')
        ], className='metric-container'),

        html.Div(children=[
            html.H4("Number of Developers"),
            html.Div(id='unique-developers', className='metric-box')
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
    ]),
    
    # 新增：用于显示时间序列图表的container
    html.Div(id='time-series-chart', style={'width': '100%', 'marginTop': '20px'}),
    #新增：聚类分析表格container
    html.Div(id='cluster-analysis-container', style={'display': 'none'}),
    # Search bar
    dcc.Input(id='search-bar', type='text', placeholder='Search for a game...'),
    html.Button(id='search-button', n_clicks=0, children='Search'),

    # Custom modal (hidden by default)
    html.Div(id='modal-game-info', style={'display': 'none'}, children=[
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'border-radius': '5px', 'position': 'fixed', 'top': '20%', 'left': '50%', 'transform': 'translate(-50%, -50%)', 'zIndex': '100'}, children=[
            html.H4("Game Details", id='modal-title'),
            html.Div(id='game-info'),
            html.Button('Close', id='modal-close', n_clicks=0),
        ]),
        # Overlay to capture clicks outside the modal
        html.Div(style={'position': 'fixed', 'top': 0, 'left': 0, 'height': '100%', 'width': '100%', 'backgroundColor': 'rgba(0,0,0,0.5)'})
    ]),

    # Store component for state management
    dcc.Store(id='store-searched-game', storage_type='session')

], style={'backgroundColor': '#ADD8E6'})


# Callback to update the graph based on the uploaded file
@app.callback(
    [Output('data-summary-text', 'children'),
     Output('num-games', 'children'),
     Output('num-genres', 'children'),
     Output('unique-developers', 'children'),
     Output('avg-plays', 'children'),
     Output('avg-rating', 'children'),
     Output('num-description', 'children'),
     Output('time-series-chart', 'children')],  # 新增：输出用于显示时间序列图表
    
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)

def update_summary(content, filename, start_date, end_date):

    # Initial placeholders for the statistics
    num_games = num_genres = unique_developers = avg_plays = avg_rating = num_description = 'N/A'
    
    graphs = None  # 新增：默认值初始化 graphs
    
    if content is None:
        return 'Upload a file to see the summary.', num_games, num_genres, unique_developers, avg_plays, avg_rating, num_description, graphs  # 新增：graphs

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
    num_genres = filtered_df['genre'].nunique()
    unique_developers = filtered_df['developer'].nunique()
    avg_plays = round(filtered_df['plays'].mean(), 2)
    avg_rating = round(filtered_df['rating'].mean(), 2)
    num_description = filtered_df['description'].notna().sum()



    #以下为时间序列分析部分，共四个统计图，均可根据所选开始时间和结束时间进行动态变化
    #分为了两种情况：1.开始时间和结束时间年份不同； 2.开始时间和结束时间年份相同
    
    # Calculate the length of the date range
    start_year = pd.to_datetime(start_date).year
    end_year = pd.to_datetime(end_date).year
    
    # Create a copy of the filtered DataFrame and add new columns
    filtered_df = filtered_df.copy()
    
    filtered_df['year'] = filtered_df['date'].dt.year
    filtered_df['month'] = filtered_df['date'].dt.month

    
    if start_year != end_year:  #Starting and ending dates and years are different, analyze by year
        yearly_stats = filtered_df.groupby('year').agg(Num_Games=('id', 'count'), Total_Plays=('plays', 'sum'), Avg_Rating=('rating', 'mean')).reset_index()
        
        # Generate yearly statistical charts
        fig = px.line(yearly_stats, x='year', y='Num_Games', title='Number of Games Released Each Year', markers=True)
        fig.update_xaxes(type='category')
        fig2 = px.line(yearly_stats, x='year', y='Total_Plays', title='Total Plays Each Year', markers=True)
        fig2.update_xaxes(type='category')
        fig3 = px.line(yearly_stats, x='year', y='Avg_Rating', title='Average Rating Each Year', markers=True)
        fig3.update_xaxes(type='category')
   
    else:  #Starting and ending date years are the same, analyzed monthly
        monthly_stats = filtered_df.groupby('month').agg(Num_Games=('id', 'count'), Total_Plays=('plays', 'sum'), Avg_Rating=('rating', 'mean')).reset_index()
        
        # Generate monthly statistical charts
        fig = px.line(monthly_stats, x='month', y='Num_Games', title='Number of Games Released Each Month', markers=True)
        fig.update_xaxes(type='category')
        fig2 = px.line(monthly_stats, x='month', y='Total_Plays', title='Total Plays Each Month', markers=True)
        fig2.update_xaxes(type='category')
        fig3 = px.line(monthly_stats, x='month', y='Avg_Rating', title='Average Rating Each Month', markers=True)
        fig3.update_xaxes(type='category')


    # Analyzing genes requires splitting the 'gene' column and creating a new dataframe for splitting
    genre_df = filtered_df
    
    # Split a string into a list & Remove excess spaces from each element in the list
    genre_df['genre'] = genre_df['genre'].str.split(',')  
    genre_df['genre'] = genre_df['genre'].apply(lambda x: [i.strip() for i in x] if isinstance(x, list) else x)  
    
    #Split each list item into a new row
    genre_df = genre_df.explode('genre')  
    
    # Add year column for analysis
    genre_df['year'] = genre_df['date'].dt.year
    
    if start_year != end_year:  # start and end dates and years are different
       # Group by year and calculate the number of unique game types for each year
        genre_per_year = genre_df.groupby('year')['genre'].nunique().reset_index(name='Unique_Genres')

        fig4 = px.line(genre_per_year, x='year', y='Unique_Genres', title='Unique Game Genres Per Year', markers=True)
        fig4.update_xaxes(type='category')

    else: # one year
        # Calculate the number of games per 'genre'and descend order
        genre_stats = genre_df.groupby(['genre']).size().reset_index(name='Num_Games')
        genre_stats = genre_stats.sort_values(by='Num_Games', ascending=False)
        
        fig4 = px.bar(genre_stats, x='genre', y='Num_Games', title='Number of Games by Genre')

    
    # Convert plot charts to HTML elements
    graph_html = dcc.Graph(figure=fig)  
    graph_html2 = dcc.Graph(figure=fig2)  
    graph_html3 = dcc.Graph(figure=fig3)  
    
    graph_html4 = dcc.Graph(figure=fig4) 

    graphs = html.Div([graph_html, graph_html2, graph_html3, graph_html4])

    #新的return（删了一个多的return）
    return summary_text, num_games, num_genres, unique_developers, avg_plays, avg_rating, num_description, graphs



# Callback to update the searched game data
@app.callback(
    [Output('modal-game-info', 'style'),  # Controls the modal's visibility
     Output('game-info', 'children')],    # Updates the modal's content
    [Input('search-button', 'n_clicks'),  # Search button clicks
     Input('modal-close', 'n_clicks')],   # Close button clicks
    [State('search-bar', 'value'),        # Text input from the user
     State('upload-data', 'contents')]    # Contents of the uploaded file
)

def search_game(n_clicks_search, n_clicks_close, search_value, content):
    ctx = callback_context

    # Determine which button was clicked
    if not ctx.triggered:
        button_id = 'No buttons clicked yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # If the search button was clicked and there's valid input and file content
    if button_id == 'search-button' and n_clicks_search and search_value and content:
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

        # Normalize case for a case-insensitive full match
        search_value_lower = search_value.lower()
        df['name_lower'] = df['name'].str.lower()

        # Check for a full match rather than a partial match
        match_df = df[df['name_lower'] == search_value_lower]
        
        if not match_df.empty:
            # Assuming the first match is the desired one
            game_info = match_df.iloc[0][['name', 'date', 'genre', 'developer', 'platform', 'rating', 'wishlists', 'description']].to_dict()
            game_details = [
                html.H4(game_info.get('name', 'No Name')),
                html.P(f"Date: {game_info.get('date', 'No available information')}"),
                html.P(f"Genre: {game_info.get('genre', 'No available information')}"),
                html.P(f"Developer: {game_info.get('developer', 'No available information')}"),
                html.P(f"Platform: {game_info.get('platform', 'No available information')}"),
                html.P(f"Rating: {game_info.get('rating', 'No available information')}"),
                html.P(f"Wishlists: {game_info.get('wishlists', 'No available information')}"),
                html.P(f"Description: {game_info.get('description', 'No description available.')}"),
            ]
            return {'display': 'block'}, game_details  # Show modal with details
        else:
            # No exact match found
            no_match_message = html.P("Game information not available.")
            return {'display': 'block'}, [no_match_message]

    # If the close button was clicked or there's no search action
    if button_id == 'modal-close' or button_id == 'search-button':
        return {'display': 'none'}, []  # Hide modal

    # Default return (e.g., initial load)
    return {'display': 'none'}, []
    
if __name__ == '__main__':
    app.run_server(debug=True)



#新增：cluster analysis部分
def generate_cluster_summary_table(df, numeric_features, categorical_features):
    # 首先，计算数值型特征的平均值
    numeric_summary = df.groupby('cluster')[numeric_features].mean().reset_index()

    # 对数值型特征进行四舍五入，保留两位小数
    numeric_summary[numeric_features] = numeric_summary[numeric_features].round(2)
    
    # 接下来，找出每个聚类中最常见的分类特征的值
    for feature in categorical_features:
        # 对每个聚类，计算每个分类特征的众数，并创建一个新的列来存储这些值
        mode_series = df.groupby('cluster')[feature].agg(lambda x: x.mode()[0] if not x.mode().empty else 'Unknown').rename(f'most_common_{feature}')
        # 因为mode_series是Series，所以使用reset_index来转换为DataFrame，以便进行merge操作
        mode_df = mode_series.reset_index()
        numeric_summary = numeric_summary.merge(mode_df, on='cluster')

    return numeric_summary


@app.callback(
    [Output('cluster-analysis-container', 'children'),
     Output('cluster-analysis-container', 'style')],  # 更新style使容器可见
    [Input('upload-data', 'contents')]
)
def update_cluster_analysis(contents):
    if contents is None:
        raise PreventUpdate
    # 解析上传的文件内容
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 解析上传的数据并进行预处理、聚类分析...
    # 定义预处理转换器
    numeric_features = ['rating', 'reviews', 'plays']
    numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),  # 使用中位数填充缺失值
    ('scaler', StandardScaler())  # 标准化
    ])

    categorical_features = ['platform', 'genre', 'developer']
    categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),  # 填充缺失值
    ('onehot', OneHotEncoder(handle_unknown='ignore'))  # 独热编码
    ])

# 组合预处理步骤
    preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ]
    )


# 假设 df 是你上传的DataFrame
# 应用预处理
    X_preprocessed = preprocessor.fit_transform(df)

# 执行K-Means聚类
    kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)  # 选择聚类数量为3
    kmeans.fit(X_preprocessed)
    df['cluster'] = kmeans.labels_

    cluster_summary = generate_cluster_summary_table(df, numeric_features, categorical_features)  # 假设这个函数生成了聚类总结的DataFrame

    # 将DataFrame转换为Dash DataTable
    table = dash_table.DataTable(
        data=cluster_summary.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in cluster_summary.columns]
    )

    # 返回表格和更新的样式来展示容器
    return table, {'display': 'block'}
