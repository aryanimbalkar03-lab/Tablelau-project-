import sys
import numpy as np
import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else 'data/loans_clean.csv'
d = pd.read_csv(path, parse_dates=['issue_date'], low_memory=False)

BAD = ['Charged Off', 'Default', 'Does not meet the credit policy. Status:Charged Off']
LIVE = ['Current', 'In Grace Period', 'Late (16-30 days)', 'Late (31-120 days)']

d['default'] = d['loan_status'].isin(BAD).astype(int)
d['mature'] = (d['issue_date'].dt.year * 12 + d['issue_date'].dt.month + d['term_months']) <= 2018 * 12 + 12
d['live_exp'] = np.where(d['loan_status'].isin(LIVE), d['out_prncp'], 0.0)
d['net_loss'] = np.where((d['default'] == 1) & d['mature'],
                         d['funded_amnt'] - d['total_rec_prncp'] - d['recoveries'], 0.0)
d['cx'] = d['int_rate'] * d['funded_amnt']
d['yrs'] = d['funded_amnt'] * d['term_months'] / 12

m = d[d['mature']].copy()
pd_grade = m.groupby('grade')['default'].mean()
x = d[d['default'] == 1]
lgd = 1 - x['recoveries'].sum() / (x['funded_amnt'] - x['total_rec_prncp']).sum()
d['row_el'] = d['live_exp'] * d['grade'].map(pd_grade) * lgd
el = d['row_el'].sum()
live = d['live_exp'].sum()
coupon = m['cx'].sum() / m['funded_amnt'].sum() / 100
ann_loss = m['net_loss'].sum() / m['yrs'].sum()

print('== HEADLINE ==')
print('rows', len(d), '| funded', round(d['funded_amnt'].sum(), 2))
print('default rate mature, all terms', round(m['default'].mean(), 6))
print('default rate mature, 36M only', round(m.loc[m['term_months'] == 36, 'default'].mean(), 6))
print('LGD', round(lgd, 6), '| live exposure', round(live), '| EL', round(el), '| EL rate (lifetime)', round(el / live, 6))
print('weighted coupon (mature)', round(coupon, 6), '| annualised loss', round(ann_loss, 6))
print('gross cushion', round(coupon - ann_loss, 6), '| break-even multiplier', round(coupon / ann_loss, 2))

print('\n== BY GRADE (mature) ==')
g = m.groupby('grade').agg(loans=('default', 'size'), default_rate=('default', 'mean'),
                           cx=('cx', 'sum'), f=('funded_amnt', 'sum'),
                           nl=('net_loss', 'sum'), yrs=('yrs', 'sum'))
g['coupon'] = g['cx'] / g['f'] / 100
g['ann_loss'] = g['nl'] / g['yrs']
g['cushion'] = g['coupon'] - g['ann_loss']
print(g[['loans', 'default_rate', 'coupon', 'ann_loss', 'cushion']].round(4))

print('\n== 36-MONTH VINTAGES (loans = cohort size) ==')
m36 = m[m['term_months'] == 36]
v = m36.groupby(m36['issue_date'].dt.year).agg(loans=('default', 'size'), default_rate=('default', 'mean'))
print(v.round(4))

print('\n== CONCENTRATION ==')
for name, col in [('Funded', 'funded_amnt'), ('Live exposure', 'live_exp')]:
    s = d.groupby('addr_state')[col].sum()
    sh = s / s.sum()
    print(name, 'HHI x10,000:', round(float((sh ** 2).sum() * 10000), 1))
    print(name, 'top 5:', sh.nlargest(5).round(4).to_dict(), '| combined', round(float(sh.nlargest(5).sum()), 4))

print('\n== FICO x DTI (cells with >= 1,000 mature loans, lowest cushion) ==')
m['fico_band'] = pd.cut(m['fico'], [-np.inf, 660, 700, 740, np.inf], right=False,
                        labels=['<660', '660-699', '700-739', '740+'])
m['dti_band'] = pd.cut(m['dti'], [-np.inf, 10, 20, 30, np.inf], right=False,
                       labels=['<10', '10-19', '20-29', '30+'])
c = m.groupby(['fico_band', 'dti_band'], observed=True).agg(
    loans=('default', 'size'), default_rate=('default', 'mean'),
    cx=('cx', 'sum'), f=('funded_amnt', 'sum'), nl=('net_loss', 'sum'), yrs=('yrs', 'sum'))
c['cushion'] = c['cx'] / c['f'] / 100 - c['nl'] / c['yrs']
print(c[c['loans'] >= 1000][['loans', 'default_rate', 'cushion']].sort_values('cushion').head(5).round(4))

print('\n== DELINQUENCY AND STRESS ==')
bucket = {'In Grace Period': 'Grace', 'Late (16-30 days)': '16-30', 'Late (31-120 days)': '31-120'}
dl = d[d['loan_status'].isin(list(bucket))]
print(dl.groupby(dl['loan_status'].map(bucket))['out_prncp'].sum().round(0))
print('delinquent share of live book', round(dl['out_prncp'].sum() / live, 4))
pdm, add = 1.5, 0.05
stressed = (d['live_exp'] * np.minimum(1, d['grade'].map(pd_grade) * pdm) * min(1, lgd + add)).sum()
print('EL base', round(el), '| stressed (PD x1.5, LGD +5pp)', round(stressed), '| change %', round((stressed / el - 1) * 100, 1))

