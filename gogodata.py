import numpy as np
import geopandas as gpd
import pandas as pd
import json

def gdf_to_geojson_madness(gdf,jfname, idkey):
    gdf.to_file(jfname, driver='GeoJSON')
    with open(jfname,'r') as f:
        geojson = json.load(f)
    for f in geojson['features']:
        f['id'] = f['properties'][idkey]
    return geojson


covid = pd.read_csv('data/Hospitalization_all_locs.csv')

states = gpd.read_file('data/cb_2018_us_state_500k.shp')
states = states.astype({'STATEFP': 'int64', 'GEOID':'int64'})
states = states.loc[states['STATEFP'] < 60] #Not states
states = states.loc[states['STATEFP'] != 2] #bye alaska
states = states.loc[states['STATEFP'] != 15] #bye hawaii

state_pop = pd.read_excel('data/nst-est2019-01.xlsx', header=1).dropna(0)
state_pop["Region"] = state_pop['Region'].str.strip('.')
state_pop = state_pop.rename(columns={'Region':'NAME', 2019:'pop2019'})
state_pop = state_pop[['NAME', 'pop2019']]

minimal = states[['GEOID', 'NAME', 'STUSPS', 'geometry']]
minimal = minimal.merge(state_pop, on='NAME')

l = []
for i,s in enumerate(states['NAME']):
    sdata = covid.loc[covid['location_name']==s]
    dtdates = pd.to_datetime(sdata['date'])
    sdata = sdata.loc[dtdates>pd.to_datetime('2020-02')]
    dtdates = pd.to_datetime(sdata['date'])
    dates = list(sdata['date'].values)
    td_mean = list(sdata['totdea_mean'].values)
    td_lower = list(sdata['totdea_lower'].values)
    td_upper = list(sdata['totdea_upper'].values)
    td_todate = td_mean[np.argmin(np.abs(dtdates-pd.to_datetime('2020-04-12')))]
    td_proj = td_mean[-1]
    l.append((s,  td_todate, td_proj, dtdates.values, td_mean, td_lower, td_upper))

state_covid = pd.DataFrame(data = l,columns=['NAME', 'td_todate', 'td_proj','dates','td_mean', 'td_lower', 'td_upper'])

minimal = minimal.merge(state_covid,on='NAME')

minimal = minimal.assign(td_per10k_now=lambda df: 1e4*df['td_todate']/df['pop2019'] )
minimal = minimal.assign(td_per10k_proj=lambda df: 1e4*df['td_proj']/df['pop2019'] )
minimal = minimal.assign(td_tocome=lambda df: (df['td_per10k_proj'] - df['td_per10k_now'])/df['td_per10k_proj'] )

minimal.drop(columns=['geometry']).to_csv('data/state_covid_traces.csv')

minimal[['GEOID', 'NAME', 'STUSPS', 'geometry', 'td_per10k_now','td_per10k_proj','td_tocome']].to_file(
        'data/state_covid.geojson', driver='GeoJSON')
