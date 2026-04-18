import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

def generate_static_plots():
    df = pd.read_csv('projects/smart-energy-ai/data/processed/optimization_results.csv')
    
    # 1. Price & Solar Plot
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['Hour'], y=df['Price'], name="Price (UAH)", line=dict(color='firebrick', width=4)))
    fig1.add_trace(go.Bar(x=df['Hour'], y=df['Solar'], name="Solar Gen (kW)", marker_color='orange', opacity=0.6))
    fig1.update_layout(title="Market Price & Solar Generation", xaxis_title="Hour of Day", yaxis_title="UAH / kW")
    
    # 2. Battery SOC Plot
    fig2 = px.area(df, x='Hour', y='SOC', title="Battery State of Charge (SOC)", color_discrete_sequence=['#00CC96'])
    
    # Save as PNG
    if not os.path.exists('projects/smart-energy-ai/plots'): os.makedirs('projects/smart-energy-ai/plots')
    fig1.write_image("projects/smart-energy-ai/plots/price_solar.png")
    fig2.write_image("projects/smart-energy-ai/plots/battery_soc.png")
    print("Plots saved to projects/smart-energy-ai/plots/")

if __name__ == "__main__":
    generate_static_plots()
