import altair as alt
import pandas as pd
import streamlit as st
from vega_datasets import data


#####################################################################################################
# SET UP

st.set_page_config(
    layout="wide",
	initial_sidebar_state = "auto"
)

@st.cache_data
def load_data():
    # import std data
    std_df = pd.read_csv('https://raw.githubusercontent.com/YoyoMan0414/BMI706_Project/main/STD_by_state.csv')
    # import social determinants data
    sdh_df = pd.read_csv('https://raw.githubusercontent.com/YoyoMan0414/BMI706_Project/main/SD_health.csv')

    # convert object data type to numeric
    std_df['Cases'] = pd.to_numeric(std_df['Cases'].str.replace(',', ''), errors='coerce')
    std_df['Rate per 100000'] = pd.to_numeric(std_df['Rate per 100000'], errors='coerce')
    sdh_df['Numerator'] = pd.to_numeric(sdh_df['Numerator'].str.replace(',', ''), errors='coerce')

    std_df['Year'] = std_df['Year'].str.replace(r"\(COVID-19 Pandemic\)", "", regex=True).str.strip()
    sdh_df['Year'] = sdh_df['Year'].str.replace(r"\(COVID-19 Pandemic\)", "", regex=True).str.strip()
    sdh_df['Year'] = pd.to_numeric(sdh_df['Year'], errors='coerce')
    std_df['Year'] = pd.to_numeric(std_df['Year'], errors='coerce')

    std_df = std_df[std_df['Year'] > 2010]

    #pivoted_df
    pivoted_std_df = std_df.pivot(index=['FIPS', 'Geography', 'Year'], columns='Indicator', values=['Cases'])

    # Rename the pivoted columns and reset index in a concise way
    pivoted_std_df.columns = [f'{indicator}_{val}'.lower().replace(' ', '_') for val, indicator in pivoted_std_df.columns]
    pivoted_std_df = pivoted_std_df.reset_index()

    # Social Determinants of Health Table
    pivoted_sdh_df = sdh_df.pivot(index=['FIPS', 'Geography', 'Year'], columns='Indicator', values=['Numerator'])

    # Rename the pivoted columns and reset index in a concise way
    pivoted_sdh_df.columns = [f'{indicator}_{val}'.lower().replace(' ', '_') for val, indicator in pivoted_sdh_df.columns]
    pivoted_sdh_df = pivoted_sdh_df.reset_index()

    pivoted_df = pd.merge(pivoted_std_df, pivoted_sdh_df, on=['FIPS', 'Geography', 'Year'], how='left')

    #combined_df
    combined_df = pd.concat([std_df, sdh_df], ignore_index=True)
    combined_df = combined_df.fillna(0)

    return combined_df, pivoted_df


# load data
df, pivoted_df = load_data()

# title
st.write("## STD Dashboard")

#####################################################################################################
# SELECTORS
st.write("#### Geographic Distribution")
# st.slider of Year
min_year, max_year = 2011, df['Year'].max()
year = st.slider('Year', min_value=int(min_year), max_value=int(max_year), value=2016)
subset = df[df["Year"] == year]

# std and sdh select in sidebar
with st.sidebar: 
    std_options = ['Chlamydia',
               'Congenital Syphilis',
               'Early Non-Primary, Non-Secondary Syphilis',
               'Gonorrhea',
               'Primary and Secondary Syphilis']
    std = st.multiselect('**STD**', options=std_options, default = std_options)
    subset_std = subset[subset["Indicator"].isin(std)]

    # multiselect social determinants
    sdh_options = ['Households living below the federal poverty level',
                'Population 25 years and older w/o HS diploma',
                'Uninsured',
                'Vacant housing']
    sdh = st.multiselect('**Social Determinants of Health**', options=sdh_options, default = sdh_options)
    subset_sdh = subset[subset["Indicator"].isin(sdh)]

#####################################################################################################
# US MAPS

# std map
source = alt.topo_feature(data.us_10m.url, 'states')
std_data = subset_std.groupby(['Geography', 'Year', 'FIPS'])['Cases'].sum().reset_index()

width = 600
height = 300
project = 'albersUsa'

# a gray map using as the visualization background

background = alt.Chart(source
                       ).mark_geoshape(
    fill='#aaa',
    stroke='white'
).properties(
    width=width,
    height=height
).project(project)

selector = alt.selection_single(
    on='click',
    fields=['Geography']
)

chart_base = alt.Chart(source
    ).properties(
        width=width,
        height=height
    ).project(project
    ).add_selection(selector
    ).transform_lookup(
        lookup="id",
        from_=alt.LookupData(std_data, "FIPS", ['Geography','Cases']),
    )
    
# Map values
#num_scale = alt.Scale(domain=[std_data['Cases'].min(), std_data['Cases'].max()], scheme='oranges')
num_color = alt.Color(field="Cases", type="quantitative", scale=alt.Scale(domain=[0, 300000], scheme='bluepurple'))
std_map = chart_base.mark_geoshape().encode(
    color=num_color,
    tooltip=['Cases:Q', 'Geography:N']
).transform_filter(
    selector
    )

# sdh map
sdh_data = subset_sdh.groupby(['Geography', 'Year', 'FIPS'])['Numerator'].sum().reset_index()

chart_base_sdh = alt.Chart(source
    ).properties(
        width=width,
        height=height
    ).project(project
    ).transform_lookup(
        lookup="id",
        from_=alt.LookupData(sdh_data, "FIPS", ['Geography','Numerator']),
    )

#num_scale = alt.Scale(domain=[sdh_data['Numerator'].min(), sdh_data['Numerator'].max()], scheme='oranges')
num_color = alt.Color(field="Numerator", type="quantitative", scale=alt.Scale(domain=[0, 12000000], scheme='purples')) #, scale=num_scale)
sdh_map = chart_base_sdh.mark_geoshape().encode(
    color=num_color,
    tooltip=['Numerator:Q', 'Geography:N']
)

# map layout
col1, col2 = st.columns(2)
with col1:
    st.write(f'**STD Cases in U.S. :blue[{year}]**')
    map_left = background + std_map
    st.altair_chart(map_left,use_container_width=True)
with col2:
    st.write(f'**Social Determinants of Health Numerator in U.S. :blue[{year}]**')
    map_right = background + sdh_map
    st.altair_chart(map_right,use_container_width=True)

#####################################################################################################
# Line Chart & Table
st.write("#### Temporal Trends Overview")
# Line Chart
subset_std_disease = df[df["Indicator"].isin(std)]
std_data_year_cases = subset_std_disease.groupby(['Indicator','Year'])['Cases'].sum().reset_index()

line_chart = alt.Chart(std_data_year_cases).mark_line().encode(
    x=alt.X("Year:O",axis=alt.Axis(labelAngle=0)),
    y=alt.Y("Cases:Q"),
    color="Indicator",
    tooltip = ['Year','Cases', 'Indicator']
).properties(
    title='STD Cases Trends',
    width=800,
    height=500
)

# Table
df_state = subset_std.groupby(['Geography'])['Cases'].sum().reset_index().sort_values(by=['Cases'], ascending = False).reset_index(drop=True)
df_state = df_state.rename(columns = {'Geography': 'State'})

# layout
col1, col2 = st.columns([3, 1])
with col1:
    st.altair_chart(line_chart,use_container_width=True)
with col2:
    st.write(f"**STD Cases by States in :blue[{year}]**")
    st.dataframe(df_state, use_container_width=True)
    st.caption(f"Total Cases of {std}")


#####################################################################################################
# State-specific Charts
st.write("#### State-level Statistics")
# state selector
state = st.selectbox(
    'Select a State',
    pivoted_df['Geography'].unique())

# Stacked Bar Chart of Rate 
subset_std_trend = df[df["Indicator"].isin(std)]
subset_state = subset_std_trend[subset_std_trend['Geography'] == state].pivot(index=['Year'], columns='Indicator', values=['Rate per 100000'])
subset_state.columns = [f'{indicator}' for val, indicator in subset_state.columns]
subset_state = subset_state.reset_index()

st.write(f"**Yearly Breakdown of STD Rate per 100,000 in :blue[{state}]**")
st.bar_chart(subset_state, x='Year', height=300)

# Stacked Bar Chart of Social Determinant Percent (removed)
subset_sdh_trend = df[df["Indicator"].isin(sdh)]
subset_sdh_state = subset_sdh_trend[subset_sdh_trend['Geography'] == state]
#subset_state2 = subset_sdh_trend[subset_sdh_trend['Geography'] == state].pivot(index=['Year'], columns='Indicator', values=['Percent'])
#subset_state2.columns = [f'{indicator}' for val, indicator in subset_state2.columns]
#subset_state2 = subset_state2.reset_index()
# st.write(f"Yearly Breakdown of Social Determinants of Health **Percent** of Population in {state}")
# st.bar_chart(subset_state2, x='Year', height=300)

# Line Chart of Social Determinant Percent
line_chart2 = alt.Chart(subset_sdh_state).mark_line().encode(
    x=alt.X("Year:O",axis=alt.Axis(labelAngle=0)),
    y=alt.Y("Percent:Q"),
    color="Indicator",
    tooltip = ['Year','Cases', 'Indicator']
).properties(
    width=800,
    height=500
)

# Table
sdh_subset = df[df["Indicator"].isin(sdh)]
sdh_percent_state = sdh_subset[sdh_subset['Geography'] == state][['Year', 'Indicator', 'Percent']].reset_index(drop=True)
sdh_percent_state = sdh_percent_state.rename(columns = {'Indicator': 'Determinants', 'Percent':'Population Percent'})

# layout
col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"**Yearly Trend of Social Determinants of Health Population Percent in :blue[{state}]**")
    st.altair_chart(line_chart2,use_container_width=True)
with col2:
    st.write(f"**SDH Population Percent in :blue[{state}]**")
    st.dataframe(sdh_percent_state,use_container_width=True)


#####################################################################################################
# Heatmap & Scatterplot
st.write("#### Correlation Exploration")
#correlation matrix
cor_df = pivoted_df.drop(['FIPS', 'Geography','Year'], axis = 1)
corr_matrix = cor_df.corr()
corr_matrix_long = corr_matrix.reset_index().melt('index')

heatmap = alt.Chart(corr_matrix_long).mark_rect().encode(
    x='index:O',
    y='variable:O',
    color=alt.Color('value:Q', scale=alt.Scale(domain=[1, -1], scheme='pinkyellowgreen')),
    tooltip=[
        alt.Tooltip('index', title='Variable 1'),
        alt.Tooltip('variable', title='Variable 2'),
        alt.Tooltip('value', title='Correlation')
    ]
).properties(
    title='Correlation Heatmap',
    width=alt.Step(40),  # Controls the width of the heatmap cells
    height=alt.Step(40)  # Controls the height of the heatmap cells
).configure_axis(
    labelFontSize=10
)

# layout 
col1, col2 = st.columns([1.5, 1])
with col1:
    # Display the heatmap in Streamlit
    st.altair_chart(heatmap,use_container_width=True)
with col2:
    var1 = st.selectbox('Select STD (by Cases) Variable:', options=std_options, index=0)
    #var1 = st.radio('Select STD (by Cases)Variable:', options=std_options, index=0, key='var1')
    var2 = st.selectbox('Select SDH (by Counts) Variable:', options=sdh_options, index=1)
    #var2 = st.radio('Select SDH Variable:', options=sdh_options, index=0, key='var2')

    # Generate and display scatterplot based on selections
    cor_df2 = cor_df.set_axis(std_options + sdh_options, axis=1)
    st.write(f'**:rainbow[{var1}] vs :rainbow[{var2}]**')
    if var1 and var2:
        scatterplot = alt.Chart(cor_df2).mark_circle(size=60, color = 'pink').encode(
            x=alt.X(f'{var1}:Q', title=var1),
            y=alt.Y(f'{var2}:Q', title=var2),
            tooltip=[var1, var2]
        ).properties(
            width=450,
            height=400
        )

        st.altair_chart(scatterplot)  # Display heatmap and scatterplot side by side
    else:
        st.altair_chart(heatmap,use_container_width=True)  
