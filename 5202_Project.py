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
import plotly.graph_objs as go

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

    # Search bar
    html.Div(
        style={'display': 'flex', 'justifyContent': 'flex-end', 'marginRight': '10px'},
        children=[
            dcc.Input(id='search-bar', type='text', placeholder='Search for a game...'),
            html.Button(id='search-button', n_clicks=0, children='Search'),
        ]
    ),

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
    dcc.Store(id='store-searched-game', storage_type='session'),

    # Text asks user to upload file
    html.Div(id='data-summary-text',
             style={'width': '100%'}),

    dcc.DatePickerRange(
        id='date-picker-range',
        display_format='YYYY-MM-DD',
        start_date='1900-01-01',  # Set default start date to 1900-01-01
        end_date=datetime.today().strftime('%Y-%m-%d'),  # Set default end date to today's date
        style={'margin': '20px 0'}
    ),
    

    dcc.Tabs(id="tabs", children = [
        
        dcc.Tab(label='Overview', children=[  
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

            html.Div(
                style={'marginTop': '40px', 'textAlign': 'center'},
                children=[html.H2("Time Series Analysis")],
            ),

            # 新增：用于显示时间序列图表的container
            html.Div(id='time-series-chart', style={'width': '100%', 'marginTop': '20px'}),
        ]),

        dcc.Tab(label='Relationship', children=[
            #新增relationship的表格
            html.Div(id='reviews-rating-chart', style={'width': '100%', 'marginTop': '20px'}),
            html.Div(id='plays-playing-chart', style={'width': '100%', 'marginTop': '20px'}),
            dcc.Graph(id='rating-comparison-chart'),
        ]),

        dcc.Tab(label='Feedback', children=[
            dcc.Graph(id='genre-distribution-chart'),
            html.Div(id='top-games-by-plays'),
            html.Div(id='genre-rating-chart', style={'width': '100%', 'marginTop': '20px'}),
            html.Div(id='genre-reviews-chart', style={'width': '100%', 'marginTop': '20px'}),
            html.Div(id='output-progress'),
            dcc.Graph(id='platform-distribution-pie'),
        ]),
            
    ]),

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
    summary_text = ''

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
                html.P(f"Date: {game_info['date'] if pd.notna(game_info['date']) else 'No information available'}"),
                html.P(f"Genre: {game_info['genre'] if pd.notna(game_info['genre']) else 'No information available'}"),
                html.P(f"Developer: {game_info['developer'] if pd.notna(game_info['developer']) else 'No information available'}"),
                html.P(f"Platform: {game_info['platform'] if pd.notna(game_info['platform']) else 'No information available'}"),
                html.P(f"Rating: {game_info['rating'] if pd.notna(game_info['rating']) else 'No information available'}"),
                html.P(f"Wishlists: {game_info['wishlists'] if pd.notna(game_info['wishlists']) else 'No information available'}"),
                html.P(f"Description: {game_info['description'] if pd.notna(game_info['description']) else 'No information available'}"),
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

    
       
    
#新增relationship
@app.callback(
    Output('reviews-rating-chart', 'children'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_reviews_rating_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate
    
    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    
    # 过滤数据集以符合选择的日期范围
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # 生成散点图
    fig = px.scatter(filtered_df, x='reviews', y='rating', 
                     title='Relationship between Number of Reviews and Rating',
                     hover_data=['name'])  # 悬停时显示游戏名称
    
    # 转换图表为HTML元素
    graph_html = dcc.Graph(figure=fig)
    
    return graph_html




@app.callback(
    Output('plays-playing-chart', 'children'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_plays_playing_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate
    
    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    
    # 过滤数据集以符合选择的日期范围
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    
    # 生成散点图
    fig = px.scatter(filtered_df, x='plays', y='playing', 
                     title='Relationship between Plays and Playing',
                     hover_data=['name'])  # 悬停时显示游戏名称
    
    # 转换图表为HTML元素
    graph_html = dcc.Graph(figure=fig)
    
    return graph_html

@app.callback(
    Output('rating-comparison-chart', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_rating_comparison_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()

    # Identify the developer category based on inclusion of Sony, Microsoft, or Nintendo
    conditions = [
        filtered_df['developer'].str.contains('Sony', case=False, na=False),
        filtered_df['developer'].str.contains('Microsoft', case=False, na=False),
        filtered_df['developer'].str.contains('Nintendo', case=False, na=False)
    ]
    choices = ['Sony', 'Microsoft', 'Nintendo']
    filtered_df['Developer Category'] = np.select(conditions, choices, default='Others').copy()

    # Plotting the box plot
    fig = px.box(filtered_df, x='Developer Category', y='rating', title='Rating Distribution by Developer Category')

    return fig

@app.callback(
    Output('genre-distribution-chart', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_genre_distribution_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate
    
    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 过滤数据集以符合选择的日期范围
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].copy()
    
    # 拆分 'genre' 列中的字符串为列表
    filtered_df['genre'] = filtered_df['genre'].str.split(', ')
    
    # 展开这些列表为新的行
    exploded_df = filtered_df.explode('genre')
    
    # 按 'genre' 分组并计算每个 'genre' 的游戏数量
    genre_counts = exploded_df['genre'].value_counts().reset_index()
    genre_counts.columns = ['genre', 'count']
    
    # 使用 Plotly Express 或 Graph Objects 构造图表
    fig = px.bar(genre_counts, x="genre", y="count", title="Genre Distribution")
    
    return fig  # 直接返回构造好的图表对象



@app.callback(
    Output('genre-rating-chart', 'children'),  # 确保你的布局中有一个与此ID相对应的组件
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_genre_rating_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate

    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 过滤数据集以符合选择的日期范围
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].copy()

    # 拆分 'genre' 列中的字符串为列表
    filtered_df['genre'] = filtered_df['genre'].str.split(', ')

    # 展开这些列表为新的行
    exploded_df = filtered_df.explode('genre')

    # 按 'genre' 分组并计算每个 'genre' 的平均评分
    genre_avg_rating = exploded_df.groupby('genre')['rating'].mean().reset_index()
    genre_avg_rating.columns = ['genre', 'average_rating']

    # 找出平均评分前三的 'genre'
    top_genres = genre_avg_rating.nlargest(3, 'average_rating')['genre']

    # 为平均评分前三的 'genre' 设置颜色，其它的 'genre' 使用默认颜色
    genre_avg_rating['color'] = genre_avg_rating['genre'].apply(lambda x: 'Top 3' if x in top_genres.values else 'Other')

    # 生成条形图，并使用颜色列来定义每个条形的颜色
    fig = px.bar(genre_avg_rating, x='genre', y='average_rating', 
                 title='Average Rating by Genre in Selected Date Range'
                 )

    # 返回图表
    return dcc.Graph(figure=fig)


@app.callback(
    Output('genre-reviews-chart', 'children'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_genre_reviews_chart(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate

    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 过滤数据集以符合选择的日期范围
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].copy()

    # 拆分 'genre' 列中的字符串为列表
    filtered_df['genre'] = filtered_df['genre'].str.split(', ')

    # 展开这些列表为新的行
    exploded_df = filtered_df.explode('genre')

    # 按 'genre' 分组并计算每个 'genre' 的平均评论数
    genre_avg_reviews = exploded_df.groupby('genre')['reviews'].mean().reset_index()
    genre_avg_reviews.columns = ['genre', 'average_reviews']

    # 找出平均评论数前三的 'genre'
    top_genres_reviews = genre_avg_reviews.nlargest(3, 'average_reviews')['genre']

    # 为平均评论数前三的 'genre' 设置颜色，其它的 'genre' 使用默认颜色
    genre_avg_reviews['color'] = genre_avg_reviews['genre'].apply(lambda x: 'Top 3' if x in top_genres_reviews.values else 'Other')

    # 生成条形图，并使用颜色列来定义每个条形的颜色
    fig = px.bar(genre_avg_reviews, x='genre', y='average_reviews',
                 title='Average Reviews by Genre in Selected Date Range'
                 )

    # 返回图表
    return dcc.Graph(figure=fig)




@app.callback(
    Output('top-games-by-plays', 'children'),  # 输出到一个展示游戏名称列表的容器
    [Input('genre-distribution-chart', 'clickData'),     # 监听条形图的点击事件
     Input('upload-data', 'contents')]          # 同时需要原始数据
)
def display_top_games_by_plays(clickData, contents):
    if clickData is None or contents is None:
        raise PreventUpdate

    # 解析上传的文件内容
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 获取被点击的 'genre'
    genre_clicked = clickData['points'][0]['x']

    # 筛选出该 'genre' 的所有游戏并按plays排序，取前五名
    top_games = df[df['genre'].str.contains(genre_clicked, na=False)].nlargest(5, 'plays')[['name', 'plays']]

    # 生成游戏名称列表
    children = [html.Div(f"{name}: {plays}", style={'margin': '5px'}) for name, plays in zip(top_games['name'], top_games['plays'])]

    # 返回名称列表
    return children


@app.callback(
    Output('output-progress', 'children'),
    [Input('upload-data', 'contents'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_output(contents, start_date, end_date):
    if contents is None or start_date is None or end_date is None:
        return 'Please upload a file and select a date range.'

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 确保 'date' 列是日期格式
    df['date'] = pd.to_datetime(df['date'])

    # 筛选选中的时间段和 rating 大于 4 的游戏
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date) & (df['rating'] > 3.5)]

    # 计算百分比
    total_games = len(df[(df['date'] >= start_date) & (df['date'] <= end_date)])
    high_rating_games = len(filtered_df)
    if total_games > 0:
        percentage = (high_rating_games / total_games) * 100
    else:
        return 'No games found in the selected date range.'

    # 显示进度条
    progress_bar = html.Progress(value=str(percentage), max="100")


    return html.Div([
        f'In the selected date range, {high_rating_games} out of {total_games} games have a rating greater than 3.5, which is {percentage:.2f}%.',
        progress_bar
    ])


@app.callback(
    Output('platform-distribution-pie', 'figure'),  # 注意更改输出组件ID
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('upload-data', 'contents')]
)
def update_platform_distribution_pie(start_date, end_date, contents):
    if contents is None:
        raise PreventUpdate
    
    # 解析上传的文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    # 转换日期格式并按照指定日期范围过滤数据
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

    # 拆分 'platform' 列中的字符串为列表
    filtered_df['platform'] = filtered_df['platform'].str.split(', ')
    
    # 展开这些列表为新的行，使每行只包含一个平台
    exploded_df = filtered_df.explode('platform')

    # 将非“Windows PC”, “Linux”, “Web browser”的所有平台替换为“others”
    specified_platforms = ['Windows PC', 'Linux', 'Web browser']
    exploded_df['platform'] = exploded_df['platform'].apply(lambda x: x if x in specified_platforms else 'others')

    # 按 'platform' 分组并计算每个平台的游戏数量
    platform_counts = exploded_df['platform'].value_counts().reset_index()
    platform_counts.columns = ['platform', 'count']
    
    # 使用 Plotly Express 构造饼状图
    fig = px.pie(platform_counts, names="platform", values="count", title="Platform Distribution within Selected Date Range")

    return fig  # 直接返回构造好的图表对象




import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, callback  # 根据您的Dash版本，导入方式可能略有不同

# 假设以下是您Dash应用的一部分




if __name__ == '__main__':
    app.run_server(debug=True)
