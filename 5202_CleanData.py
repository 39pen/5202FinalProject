import pandas as pd
import re
import numpy as np

developers = pd.read_csv('developers.csv')
platforms = pd.read_csv('platforms.csv')
genres = pd.read_csv('genres.csv')
games = pd.read_csv('games.csv')

# Retain only the second developer data for each id, as the first is usually the publisher

def clean_duplicates(dataframe):
    counts = dataframe['id'].value_counts()
    duplicates = counts[counts > 1].index

    for id in duplicates:
        duplicate_rows = dataframe[dataframe['id'] == id]
        if len(duplicate_rows) > 1:
            second_entry_index = duplicate_rows.iloc[1].name
            rows_to_drop = duplicate_rows.index.difference([second_entry_index])
            dataframe = dataframe.drop(rows_to_drop)

    return dataframe.reset_index(drop=True)

cleaned_developers = clean_duplicates(developers)


# Clean up abnormalities in developer names

def is_valid_name(s):
    if pd.isna(s):
        return False
    return bool(re.fullmatch(r"[A-Za-z\s\-,\.&()_'/:0-9]+", s))

cleaned_developers['developer'] = cleaned_developers['developer'].apply(lambda x: pd.NA if not is_valid_name(x) else x)


# Concatenate platforms and genres data into a string for each id

grouped_platforms = platforms.groupby('id')['platform'].apply(lambda x: ', '.join(x)).reset_index()

grouped_genres = genres.groupby('id')['genre'].apply(lambda x: ', '.join(x)).reset_index()


# Remove the irregularity from the date column

games['date'] = pd.to_datetime(games['date'], errors='coerce', format='%Y-%m-%d')
games['date'] = games['date'].replace(pd.Timestamp('6969-06-09'), pd.NaT)


# Retain only the first row for each game

unique_games = games.drop_duplicates(subset=['name'])


# Combine all dataframes, with games as the primary one

combined_df = pd.merge(unique_games, cleaned_developers, on='id', how='left')
combined_df = pd.merge(combined_df, grouped_genres, on='id', how='left')
combined_df = pd.merge(combined_df, grouped_platforms, on='id', how='left')


# Change data types and adjust the variable order

columns_to_convert = ['reviews', 'plays', 'playing', 'backlogs', 'wishlists']
for column in columns_to_convert:
    combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce').fillna(0).astype(int)

cols = [col for col in combined_df.columns if col not in ['genre', 'developer', 'platform']]
date_index = cols.index('date')
new_cols = cols[:date_index + 1] + ['genre', 'developer', 'platform'] + cols[date_index + 1:]

combined_df = combined_df[new_cols]

print(combined_df.head())


#Testing

combined_df.to_csv('cleaned_games.csv', index=False)

start_date = '1900-01-01'
end_date = '2024-03-19'

filtered_df = combined_df[(combined_df['date'] >= pd.to_datetime(start_date)) & (combined_df['date'] <= pd.to_datetime(end_date))]

average = filtered_df['rating'].mean()

print(average)

num_games = len(filtered_df)

print(f"Number of games: {num_games}")

num_descriptions = filtered_df['description'].notna().sum()

print(f"Number of descriptions: {num_descriptions}")
