from shiny import App, ui, render
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Load the data
data = pd.read_csv('USA_Housing.csv.xls')
data['State'] = data['Address'].apply(lambda x: x.split(",")[-1].strip().split(" ")[0])

def extract_city(address):
    # Assuming the city name is always followed by a comma and state abbreviation
    parts = address.split(',')
    if len(parts) > 1:
        city = parts[-2].strip()  # This might need adjustment based on your address format
        return city
    return None

# Apply this function to create a new 'City' column
data['City'] = data['Address'].apply(lambda x: x.split('\n')[1].split(',')[0])

# State code to full name mapping
state_names = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

# Map state codes to names and filter out missing entries
data['State_Name'] = data['State'].map(state_names)
data = data.dropna(subset=['State_Name'])  # Drop rows where state name is NaN

# Round down number of bedrooms and extract unique values for selection
# Round down number of bedrooms and extract unique values for selection
data['Rounded_Bedrooms'] = np.floor(data['Avg. Area Number of Bedrooms']).astype(int)
bedroom_choices = sorted(list(data['Rounded_Bedrooms'].unique()))  # Sort the list in ascending order

# Round down number of rooms and extract unique values for selection
data['Rounded_Rooms'] = np.floor(data['Avg. Area Number of Rooms']).astype(int)
room_choices = list(data['Rounded_Rooms'].unique())



# Add an additional plot output for the pie chart in the main panel
app_ui = ui.page_fluid(
    ui.panel_title("USA Housing Data Dashboard"),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_select("state", "Select a state:", choices=list(data['State_Name'].unique()), selected="California"),
            ui.input_select("bedrooms", "Number of Bedrooms:", choices=[str(b) for b in bedroom_choices], selected='2'),
            ui.input_select("demographic", "Select Demographic Data:", 
                            choices=["Average Income", "Population", "House Age"], selected="Average Income"),
            ui.input_slider("num_cities", "Number of Cities:", min=1, max=20, value=10),
            ui.input_select("x_axis", "Choose X-Axis Variable:", 
                            choices=["Avg. Area Income", "Avg. Area House Age", "Avg. Area Number of Rooms", 
                                     "Area Population", "Price"], selected="Avg. Area Income"),
            ui.input_select("y_axis", "Choose Y-Axis Variable:", 
                            choices=["Avg. Area Income", "Avg. Area House Age", "Avg. Area Number of Rooms", 
                                     "Area Population", "Price"], selected="Price"),
            width=2,
        ),
        ui.panel_main(
            ui.output_plot("price_histogram"),
            ui.output_plot("demographic_chart"),
            ui.output_plot("scatter_plot"),
            ui.output_plot("combined_pie_charts"),  
        )
    )
)



def server(input, output, session):

    @output
    @render.plot
    def price_histogram():
        selected_state_name = input.state()
        selected_bedrooms = input.bedrooms()  # Get the value without converting it to int first
        
        # Check if selected_bedrooms is None or any other problematic value
        if selected_bedrooms is None:
            plt.figure()
            plt.text(0.5, 0.5, 'Please select a valid number of bedrooms.', horizontalalignment='center', verticalalignment='center')
            return
        
        selected_bedrooms = int(selected_bedrooms)  # Now convert to integer safely
        
        filtered_data = data[(data['State_Name'] == selected_state_name) & (data['Rounded_Bedrooms'] == selected_bedrooms)]
        
        if filtered_data.empty:
            plt.figure()
            plt.text(0.5, 0.5, 'No data available', horizontalalignment='center', verticalalignment='center')
            return

        # Extract city names and prices
        cities = filtered_data['Address'].apply(lambda x: x.split('\n')[1].split(',')[0])
        prices = filtered_data['Price']
        
        plt.figure(figsize=(10, 4))
        plt.bar(cities, prices, color='sienna')
        plt.xlabel('Cities')
        plt.ylabel('Prices (USD in millions)')
        plt.title(f'Prices in {selected_state_name} for homes with {selected_bedrooms} bedrooms')
        plt.xticks(rotation=45)
        plt.tight_layout()

    @output
    @render.plot("demographic_chart")
    def demographic_chart():
        selected_state_name = input.state()
        selected_demographic = input.demographic()
        num_cities = input.num_cities()  # Get the number of cities from the slider

        filtered_data = data[(data['State_Name'] == selected_state_name) & (data['City'].notna())]

        if filtered_data.empty:
            plt.figure()
            plt.text(0.5, 0.5, 'No demographic data available', horizontalalignment='center', verticalalignment='center')
            return

        if selected_demographic == "Population":
            demographic_data = filtered_data.groupby('City')['Area Population'].mean()
            ylabel = 'Population'
        elif selected_demographic == "Average Income":
            demographic_data = filtered_data.groupby('City')['Avg. Area Income'].mean()
            ylabel = 'Average Income ($)'
        elif selected_demographic == "House Age":
            demographic_data = filtered_data.groupby('City')['Avg. Area House Age'].mean()
            ylabel = 'Average House Age (Years)'

        demographic_data = demographic_data.nlargest(num_cities)  # Show only the selected number of cities

        plt.figure(figsize=(12, 4))
        plt.bar(demographic_data.index, demographic_data.values, color='mediumseagreen')
        plt.xlabel('Cities')
        plt.ylabel(ylabel)
        plt.title(f'{num_cities} Cities by {ylabel} in {selected_state_name}')
        plt.xticks(rotation=45)
        plt.tight_layout()
    @output
    @render.plot("combined_pie_charts")
    def combined_pie_charts():
        selected_state_name = input.state()

        # Filter data for the selected state
        state_data = data[data['State_Name'] == selected_state_name]

        if state_data.empty:
            plt.figure()
            plt.text(0.5, 0.5, 'No data available in this state.', horizontalalignment='center', verticalalignment='center')
            return

        # Count the occurrences for bedrooms and rooms
        bedroom_counts = state_data['Rounded_Bedrooms'].value_counts()
        room_counts = state_data['Rounded_Rooms'].value_counts()

        fig, axs = plt.subplots(1, 2, figsize=(16, 4))  # Set up a figure with two subplots

        # Pie chart for bedrooms
        axs[0].pie(bedroom_counts, labels=bedroom_counts.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.tab20.colors)
        axs[0].set_title(f'Distribution of Bedrooms in {selected_state_name}')

        # Pie chart for rooms
        axs[1].pie(room_counts, labels=room_counts.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.Pastel1.colors)
        axs[1].set_title(f'Distribution of Number of Rooms in {selected_state_name}')

        plt.tight_layout()
    @output
    @render.plot("scatter_plot")
    def scatter_plot():
        selected_state_name = input.state()
        x_variable = input.x_axis()
        y_variable = input.y_axis()

        # Filter data for the selected state
        state_data = data[data['State_Name'] == selected_state_name]

        if state_data.empty:
            plt.figure()
            plt.text(0.5, 0.5, 'No data available for this state.', horizontalalignment='center', verticalalignment='center')
            return

        plt.figure(figsize=(10, 4))
        plt.scatter(state_data[x_variable], state_data[y_variable], alpha=0.5)
        plt.xlabel(x_variable)
        plt.ylabel(y_variable)
        plt.title(f'Scatter Plot of {x_variable} vs {y_variable} in {selected_state_name}')
        plt.grid(True)
        plt.tight_layout()




app = App(app_ui, server)

if __name__ == "__main__":
    app.run()



