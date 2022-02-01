import pandas as pd
import os
from os  import getcwd
import pickle
from flask import Flask, render_template, request

# Initiate flask app
app = Flask(__name__)

directory = getcwd()

# # Import the required Pickle files
prod_ranking_model = pickle.load(open(os.path.join(directory,'prod_ranking_model.pkl'),'rb'))
cust_prod_ranking_model = pickle.load(open(os.path.join(directory,'cust_prod_ranking_model.pkl'),'rb'))
cust_correlation_model = pickle.load(open(os.path.join(directory,'cust_correlation_model.pkl'),'rb'))
prod_correlation_model = pickle.load(open(os.path.join(directory,'prod_correlation_model.pkl'),'rb'))


#HTML code for displaying table
def html_code_table(prod_df,table_name,file_name,side):
    table_style = '<table style="border: 2px solid; float: ' + side + '; width: 40%;">'
    table_head = '<caption style="text-align: center; caption-side: top; font-size: 140%; font-weight: bold; color:black;"><strong>' + table_name + '</strong></caption>'
    table_head_row = '<tr><th>Product Name</th><th>Price (in Rupees(INR).)</th></tr>'
    html_code = table_style + table_head + table_head_row
    
    for i in range(len(prod_df.index)):
        row = '<tr><td>' + str(prod_df['Product'][i]) + '</td><td>' + str(prod_df['Rate'][i]) + '</td></tr>'
        html_code = html_code + row
        
    html_code = html_code + '</table>'
    
    file_path = os.path.join(directory,'templates/')
    hs = open(file_path + file_name + '.html', 'w')
    hs.write(html_code)

# Most Popular Products
def most_popular_table():
    most_popular_prods = prod_ranking_model.sort_values('Popularity_Rank',ascending=True)[['Product','Rate']].head(10).reset_index(drop=True)
    html_code_table(most_popular_prods,'Most Popular Products','mostpopulartable','left')

# Top Selling Products
def top_sell_table():
    top_sell_prods = prod_ranking_model.sort_values('Top_Sell_Rank',ascending=True)[['Product','Rate']].head(10).reset_index(drop=True)
    html_code_table(top_sell_prods,'Top Selling Products','topselltable','right')

# Customer Frequently Purchased and Purchased the Most Products
def cust_most_popular_table(cust_name):
    cust_most_popular_prods = cust_prod_ranking_model[cust_prod_ranking_model['Party'] == cust_name]
    cust_most_popular_prods = cust_most_popular_prods.sort_values('Popularity_Rank',ascending=True)[['Product','Rate']].head(10).reset_index(drop=True)
    html_code_table(cust_most_popular_prods,'Products you Frequently Purchased','custmostpopulartable','left')

# This function calls the html_code_table function to create a .html file for Top Selling Products of a Customer
def cust_top_sell_table(cust_name):
    cust_top_sell_prods = cust_prod_ranking_model[cust_prod_ranking_model['Party'] == cust_name]
    cust_top_sell_prods = cust_top_sell_prods.sort_values('Top_Sell_Rank',ascending=True)[['Product','Rate']].head(10).reset_index(drop=True)
    html_code_table(cust_top_sell_prods,'Products you Purchased the Most','custtopselltable','right')

# Recommendation part of code
def recommend_prod_cust(cust_name):
    similar_custs_corr = cust_correlation_model.loc[cust_name].sort_values(ascending=False)
    prod_by_similar_custs = pd.DataFrame()
    
    # get the products purchased by each customer and multiply with the customer "correlation coefficient"
    for i in range(len(similar_custs_corr)):
        if similar_custs_corr.index[i] != cust_name:
            cust_top_sell_prods = cust_prod_ranking_model[cust_prod_ranking_model['Party'] == similar_custs_corr.index[i]]
            cust_top_sell_prods = cust_top_sell_prods[['Product','Qty','Rate']].reset_index(drop=True)
            cust_top_sell_prods['Qty_Corr'] = cust_top_sell_prods['Qty'] * similar_custs_corr.iloc[i]
            prod_by_similar_custs = pd.concat([cust_top_sell_prods,prod_by_similar_custs])
    
    # Aggregation
    prod_by_similar_custs = prod_by_similar_custs.groupby('Product').agg({'Qty_Corr':'sum','Rate':'max'})
    prod_by_similar_custs.reset_index(inplace=True)
    
    # ignore the products already purchased by the input customer
    input_cust_top_sell_prods = cust_prod_ranking_model[cust_prod_ranking_model['Party'] == cust_name]
    df_merge = pd.merge(prod_by_similar_custs,input_cust_top_sell_prods[['Product','No_of_Orders']],how='left',on='Product')
    prod_recommend_to_cust = df_merge[df_merge['No_of_Orders'].isnull()]
    
    # Sort dataframe
    prod_recommend_to_cust = prod_recommend_to_cust.sort_values('Qty_Corr',ascending=False)[['Product','Rate']].head(10).reset_index(drop=True)
    
    # finally recommend to customer
    html_code_table(prod_recommend_to_cust,'Products you may like','prodrecommendtable','center')


# Similar Products Section

def similar_prods(prod_name):
    similar_prods_corr = prod_correlation_model.loc[prod_name].sort_values(ascending=False)
    similar_prods = pd.merge(similar_prods_corr,prod_ranking_model[['Product','Rate']],how='left',on='Product')
    prod_price = similar_prods[similar_prods['Product'] == prod_name]['Rate'].values[0]
    input_prod_index = similar_prods[similar_prods['Product'] == prod_name].index
    similar_prods.drop(index=input_prod_index,inplace=True)
    similar_prods = similar_prods[['Product','Rate']].head(10).reset_index(drop=True)
    html_code_table(similar_prods,'Customers who purchased this product also purchased these','similarprodtable','left')
    
    return prod_price

@app.route("/")
def home():
    most_popular_table()
    top_sell_table()
    return render_template('home.html')


@app.route("/login")
def login():
    most_popular_table()
    top_sell_table()
    cust_name = str(request.args.get('name')).upper()
    
    if cust_name in cust_prod_ranking_model['Party'].unique():
        cust_most_popular_table(cust_name)
        cust_top_sell_table(cust_name)
        recommend_prod_cust(cust_name)
        return render_template('cust_home.html',name=cust_name,new='n')
    else:
        return render_template('cust_home.html',name=cust_name,new='y')

    
@app.route("/view")
def view():
    prod_name = str(request.args.get('prod')).upper()
    
    if prod_name in prod_ranking_model['Product'].unique():
        prod_price = similar_prods(prod_name)
        return render_template('prod_view.html',prod=prod_name,price=prod_price,exists='y')
    else:
        return render_template('prod_view.html',prod=prod_name,exists='n')


if __name__ == "__main__":
    app.run(debug=True)
