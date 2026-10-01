== HEADLINE ==
rows 2260668 | funded 34004208600.0
default rate mature, all terms 0.148636
default rate mature, 36M only 0.139421
LGD 0.891753 | live exposure 9510001923 | EL 1294977878 | EL rate (lifetime) 0.13617
weighted coupon (mature) 0.125308 | annualised loss 0.024418
gross cushion 0.10089 | break-even multiplier 5.13

== BY GRADE (mature) ==
        loans  default_rate  coupon  ann_loss  cushion
grade                                                 
A      144228        0.0550  0.0723    0.0078   0.0646
B      220255        0.1137  0.1089    0.0173   0.0916
C      180248        0.1830  0.1419    0.0290   0.1129
D       87158        0.2383  0.1739    0.0409   0.1331
E       32154        0.2940  0.2032    0.0465   0.1567
F       10352        0.3451  0.2325    0.0506   0.1819
G        2064        0.3735  0.2444    0.0529   0.1915

== 36-MONTH VINTAGES (loans = cohort size) ==
             loans  default_rate
issue_date                      
2007           603        0.2620
2008          2393        0.2073
2009          5281        0.1369
2010          9156        0.1092
2011         14101        0.1063
2012         43470        0.1358
2013        100422        0.1233
2014        162570        0.1373
2015        283173        0.1488

== CONCENTRATION ==
Funded HHI x10,000: 527.6
Funded top 5: {'CA': 0.1413, 'TX': 0.0862, 'NY': 0.0813, 'FL': 0.0686, 'IL': 0.0415} | combined 0.4189
Live exposure HHI x10,000: 507.1
Live exposure top 5: {'CA': 0.1328, 'TX': 0.0856, 'NY': 0.0802, 'FL': 0.0707, 'IL': 0.0434} | combined 0.4126

== FICO x DTI (cells with >= 1,000 mature loans, lowest cushion) ==
                    loans  default_rate  cushion
fico_band dti_band                              
740+      10-19     29117        0.0608   0.0747
          20-29     15119        0.0802   0.0753
          <10       21845        0.0617   0.0761
          30+        2853        0.0988   0.0843
700-739   10-19     82297        0.1043   0.0932

== DELINQUENCY AND STRESS ==
loan_status
16-30      47949886.0
31-120    244246366.0
Grace      92044362.0
Name: out_prncp, dtype: float64
delinquent share of live book 0.0404
EL base 1294977878 | stressed (PD x1.5, LGD +5pp) 2051379684 | change % 58.4
