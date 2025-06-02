import os
import time
import json
import math
import pandas as pd
import numpy as np
from matplotlib.patches import Rectangle
from dotenv import load_dotenv
from yelpapi import YelpAPI
from tqdm import tqdm

# Load API key from .env
load_dotenv()
api_key = os.getenv('YELP_API_KEY')

# Define Maryland's approximate boundaries
MD_NORTH = 39.72284  # Northern latitude boundary
MD_SOUTH = 37.9171  # Southern latitude boundary
MD_EAST = -75.0506  # Eastern longitude boundary
MD_WEST = -79.4870  # Western longitude boundary

# Create a reasonable grid (using 10×10 grid instead of 10m×10m)
# Each cell is roughly 20km × 40km which is more practical
GRID_ROWS = 10
GRID_COLS = 10

# Calculate cell dimensions
cell_height = (MD_NORTH - MD_SOUTH) / GRID_ROWS
cell_width = (MD_EAST - MD_WEST) / GRID_COLS

# Generate and export grid cell coordinates before starting search
def generate_grid_coordinates():
    grid_cells = []
    
    for i in range(GRID_ROWS):
        for j in range(GRID_COLS):
            # Calculate cell corners
            south = MD_SOUTH + i * cell_height
            north = MD_SOUTH + (i + 1) * cell_height
            west = MD_WEST + j * cell_width
            east = MD_WEST + (j + 1) * cell_width
            
            # Calculate cell center
            center_lat = (south + north) / 2
            center_lng = (west + east) / 2
            
            # Calculate search radius
            radius = calculate_search_radius(center_lat, center_lng, cell_height, cell_width)
            
            grid_cells.append({
                'cell_id': f"{i}_{j}",
                'south_lat': south,
                'north_lat': north,
                'west_lng': west,
                'east_lng': east,
                'center_lat': center_lat,
                'center_lng': center_lng,
                'search_radius_m': radius,
                'done': 'no'  # Add 'done' column to track search progress
            })
    
    # Convert to DataFrame and export to CSV
    grid_df = pd.DataFrame(grid_cells)
    grid_df.to_csv('maryland_grid_cells.csv', index=False)
    print(f"Exported {len(grid_cells)} grid cells to maryland_grid_cells.csv")
    return grid_cells

# Function to update grid cell status
def update_grid_status(cell_id, status='yes'):
    try:
        # Read the current grid cell file
        grid_df = pd.read_csv('maryland_grid_cells.csv')
        # Update the status of the specified cell
        grid_df.loc[grid_df['cell_id'] == cell_id, 'done'] = status
        # Save back to CSV
        grid_df.to_csv('maryland_grid_cells.csv', index=False)
        print(f"Updated cell {cell_id} status to {status}")
    except Exception as e:
        print(f"Warning: Failed to update grid status: {str(e)}")

# Visualize the grid and save as JPG
def visualize_grid(grid_cells):
    try:
        # Import necessary libraries for map visualization
        import contextily as ctx
        import matplotlib.pyplot as plt
        from matplotlib.pyplot import cm
        
        plt.figure(figsize=(15, 12))
        
        # Create base plot with Maryland boundaries
        plt.plot([MD_WEST, MD_EAST, MD_EAST, MD_WEST, MD_WEST], 
                [MD_SOUTH, MD_SOUTH, MD_NORTH, MD_NORTH, MD_SOUTH], 
                'r-', linewidth=3, alpha=0.7, label='Maryland Boundaries')
        
        # Plot each grid cell
        for cell in grid_cells:
            width = cell['east_lng'] - cell['west_lng']
            height = cell['north_lat'] - cell['south_lat']
            rect = Rectangle((cell['west_lng'], cell['south_lat']), width, height, 
                           fill=False, edgecolor='blue', linewidth=1.5, alpha=0.7)
            plt.gca().add_patch(rect)
            
            # Add cell ID label in the center
            plt.text(cell['center_lng'], cell['center_lat'], cell['cell_id'], 
                   ha='center', va='center', fontsize=9, 
                   bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
            
            # Add a small dot at the center point
            plt.plot(cell['center_lng'], cell['center_lat'], 'ro', markersize=4)
            
            # Draw search radius for each cell (circular approximation)
            radius_deg = cell['search_radius_m'] / 111000  # rough conversion from meters to degrees
            circle = plt.Circle((cell['center_lng'], cell['center_lat']), radius_deg, 
                              fill=False, color='green', linewidth=1.2, alpha=1.0, linestyle='--')
            plt.gca().add_patch(circle)
        
        # Set plot limits with a bit of padding
        padding = 0.1
        plt.xlim(MD_WEST - padding, MD_EAST + padding)
        plt.ylim(MD_SOUTH - padding, MD_NORTH + padding)
        
        # Add map tiles as background with higher resolution and exact coordinate system matching
        ax = plt.gca()
        # Force CRS to EPSG:4326 (standard lat/lon) to ensure exact coordinate alignment
        ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik, 
                        zoom=11, attribution_size=8)
        
        # Ensure axis ticks match the exact coordinates
        plt.xticks(np.arange(round(MD_WEST - padding, 1), round(MD_EAST + padding, 1), 0.5))
        plt.yticks(np.arange(round(MD_SOUTH - padding, 1), round(MD_NORTH + padding, 1), 0.5))
        
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('Maryland Grid for Yelp Fusion API Search', fontsize=14)
        
        # Add legend
        plt.plot([], [], 'r-', linewidth=3, alpha=0.7, label='Maryland Boundary')
        plt.plot([], [], 'b-', linewidth=1.5, alpha=0.7, label='Grid Cells')
        plt.plot([], [], 'ro', markersize=4, label='Search Points')
        plt.plot([], [], 'g--', linewidth=1.2, alpha=0.5, label='Search Radius')
        plt.legend(loc='upper right')
        
        # Save as PNG with high quality (JPG can lose quality with maps)
        plt.savefig('maryland_grid_visualization.png', dpi=300, bbox_inches='tight')
        print("Grid visualization with map saved as maryland_grid_visualization.png")
        
        # Also save as JPG as originally requested
        plt.savefig('maryland_grid_visualization.jpg', dpi=300, bbox_inches='tight')
        print("Grid visualization with map also saved as maryland_grid_visualization.jpg")
        
        plt.close()
        
    except ImportError:
        print("Warning: contextily package not found. Installing required packages...")
        print("Run: pip install contextily geopandas")
        
        # Fall back to basic visualization without map background
        plt.figure(figsize=(12, 10))
        
        # Plot Maryland boundaries
        plt.plot([MD_WEST, MD_EAST, MD_EAST, MD_WEST, MD_WEST], 
                [MD_SOUTH, MD_SOUTH, MD_NORTH, MD_NORTH, MD_SOUTH], 
                'k-', linewidth=2, label='Maryland Boundaries')
        
        # Plot each grid cell
        for cell in grid_cells:
            width = cell['east_lng'] - cell['west_lng']
            height = cell['north_lat'] - cell['south_lat']
            rect = Rectangle((cell['west_lng'], cell['south_lat']), width, height, 
                           fill=False, edgecolor='blue', alpha=0.5)
            plt.gca().add_patch(rect)
            
            # Add cell ID label in the center
            plt.text(cell['center_lng'], cell['center_lat'], cell['cell_id'], 
                   ha='center', va='center', fontsize=8)
            
            # Add a small dot at the center point
            plt.plot(cell['center_lng'], cell['center_lat'], 'ro', markersize=3)
        
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('Maryland Grid for Yelp Fusion API Search')
        plt.grid(True, alpha=0.3)
        
        # Save as JPG with high quality
        plt.savefig('maryland_grid_visualization.jpg', dpi=300, bbox_inches='tight')
        print("Grid visualization saved as maryland_grid_visualization.jpg (without map background)")
        
        plt.close()

# Function to calculate search radius (in meters) to cover cell
def calculate_search_radius(lat, lng, cell_height, cell_width):
    # Convert degrees to approx meters (1° latitude ≈ 111,000 meters)
    lat_meters = cell_height * 111000 / 2
    # Longitude degrees vary with latitude
    lng_meters = cell_width * 111000 * math.cos(math.radians(lat)) / 2
    # Calculate diagonal radius (with 20% overlap)
    radius = math.sqrt(lat_meters**2 + lng_meters**2) * 1.2
    # Yelp API maximum radius is 40000 meters
    return min(int(radius), 40000)

# Function to load existing grid status
def load_grid_status():
    """Load the grid status from CSV, or create a new file if it doesn't exist"""
    try:
        if os.path.isfile('maryland_grid_cells.csv'):
            grid_df = pd.read_csv('maryland_grid_cells.csv')
            print(f"Loaded grid status: {len(grid_df)} cells, {len(grid_df[grid_df['done'] == 'yes'])} completed")
            return grid_df
        else:
            print("No existing grid file found. Will create a new one.")
            return generate_grid_coordinates()
    except Exception as e:
        print(f"Error loading grid status: {str(e)}. Generating new grid.")
        return generate_grid_coordinates()

# Function to load existing restaurants
def load_existing_restaurants():
    """Load existing restaurants from CSV to avoid duplicates"""
    try:
        if os.path.isfile('maryland_restaurants.csv'):
            restaurants_df = pd.read_csv('maryland_restaurants.csv')
            print(f"Loaded {len(restaurants_df)} existing restaurants")
            
            # Create a dictionary of restaurants by ID for fast lookup
            restaurant_ids = set(restaurants_df['id'].unique())
            return restaurant_ids
        else:
            print("No existing restaurants file found")
            return set()
    except Exception as e:
        print(f"Error loading restaurants: {str(e)}")
        return set()

# Function to append restaurant data to CSV, checking for duplicates
def append_to_restaurants_csv(restaurants, cell_id, existing_restaurant_ids):
    """Append restaurants to CSV, skipping duplicates"""
    # Filter out restaurants that already exist
    new_restaurants = [r for r in restaurants if r['id'] not in existing_restaurant_ids]
    
    if not new_restaurants:
        print(f"No new restaurants to add from cell {cell_id}")
        return 0
    
    # Convert restaurant data to DataFrame rows
    rows = []
    for r in new_restaurants:
        rows.append({
            'cell_id': cell_id,
            'id': r['id'],
            'name': r['name'],
            'rating': r.get('rating'),
            'review_count': r.get('review_count'),
            'price': r.get('price', ''),
            'categories': str([c['title'] for c in r.get('categories', [])]),
            'address': ', '.join(r.get('location', {}).get('display_address', [])),
            'city': r.get('location', {}).get('city', ''),
            'state': r.get('location', {}).get('state', ''),
            'zip_code': r.get('location', {}).get('zip_code', ''),
            'latitude': r.get('coordinates', {}).get('latitude'),
            'longitude': r.get('coordinates', {}).get('longitude'),
            'phone': r.get('phone', ''),
            'url': r.get('url', '')
        })
        
        # Add to the existing IDs set to avoid duplicates within this batch
        existing_restaurant_ids.add(r['id'])
    
    # Create DataFrame from rows
    df = pd.DataFrame(rows)
    
    # Check if the file exists
    file_exists = os.path.isfile('maryland_restaurants.csv')
    
    # Append data to CSV (create file if it doesn't exist)
    df.to_csv('maryland_restaurants.csv', mode='a', header=not file_exists, index=False)
    
    print(f"Appended {len(rows)} new restaurants from cell {cell_id} to maryland_restaurants.csv")
    return len(rows)

# Main execution function
def main():
    # Load existing data
    grid_df = load_grid_status()
    existing_restaurant_ids = load_existing_restaurants()
    
    # Create grid cells object for visualization
    grid_cells = grid_df.to_dict('records')
    
    # Visualize the grid
    #print("Visualizing Maryland grid...")
    #visualize_grid(grid_cells)
    
    all_restaurants = {}  # Using dict to ensure unique entries
    yelp_api = YelpAPI(api_key, timeout_s=5.0)
    
    print(f"Starting search across Maryland using a {GRID_ROWS}×{GRID_COLS} grid")
    cell_count = 0
    
    try:
        # Process each cell in the grid
        for i in range(GRID_ROWS):
            for j in range(GRID_COLS):
                cell_id = f"{i}_{j}"
                cell_count += 1
                
                # Check if this cell is already done
                if grid_df.loc[grid_df['cell_id'] == cell_id, 'done'].iloc[0] == 'yes':
                    print(f"\nSkipping completed cell {cell_count}/{GRID_ROWS*GRID_COLS}: {cell_id}")
                    continue
                
                print(f"\nProcessing cell {cell_count}/{GRID_ROWS*GRID_COLS}: {cell_id}")
                
                # Calculate cell center coordinates
                lat = MD_SOUTH + (i + 0.5) * cell_height
                lng = MD_WEST + (j + 0.5) * cell_width
                
                # Calculate appropriate search radius
                radius = calculate_search_radius(lat, lng, cell_height, cell_width)
                
                print(f"Searching at {lat:.4f}, {lng:.4f} with radius {radius}m")
                
                offset = 0
                total_found = 0
                cell_restaurants = []  # Store restaurants found in this cell
                
                # Search for restaurants with improved error handling
                try:
                    # Use pagination to get all results for this cell
                    while True:
                        try:
                            # Search for restaurants
                            search_results = yelp_api.search_query(
                                term="restaurant",
                                latitude=lat,
                                longitude=lng,
                                radius=radius,
                                limit=50,  # Max results per query
                                offset=offset,
                                categories="restaurants",
                                sort_by="distance"
                            )
                            
                            # Process results
                            if 'businesses' in search_results and search_results['businesses']:
                                businesses = search_results['businesses']
                                total_found += len(businesses)
                                
                                # Get detailed info for each business
                                for business in businesses:
                                    business_id = business['id']
                                    if business_id not in all_restaurants and business_id not in existing_restaurant_ids:
                                        try:
                                            # Get full business details
                                            business_details = yelp_api.business_query(id=business_id)
                                            all_restaurants[business_id] = business_details
                                            cell_restaurants.append(business_details)
                                            time.sleep(0.2)  # Respect rate limits
                                        except Exception as e:
                                            print(f"Error getting details for {business['name']}: {str(e)}")
                                
                                # Check if we need to paginate (max 1000 results per search)
                                if len(businesses) < 50 or offset > 950:
                                    break
                                
                                # Next page
                                offset += 50
                                time.sleep(0.5)
                            else:
                                break
                                
                        except Exception as e:
                            error_msg = str(e)
                            print(f"Error in search: {error_msg}")
                            
                            # Specific handling for 429 Too Many Requests error
                            if "429 Client Error: Too Many Requests" in error_msg:
                                print(f"Rate limit exceeded for cell {cell_id}. Marking as incomplete.")
                                # Save whatever data we've collected from this cell
                                if cell_restaurants:
                                    append_to_restaurants_csv(cell_restaurants, cell_id, existing_restaurant_ids)
                                # Mark this cell as not done
                                update_grid_status(cell_id, 'no')
                                # Save current progress to JSON
                                with open('maryland_restaurants_progress.json', 'w') as f:
                                    json.dump(list(all_restaurants.values()), f)
                                exit(1)
                            else:
                                # For other errors, wait a bit and continue
                                time.sleep(2)
                                break
                    
                    # Append this cell's restaurants to the main CSV file
                    if cell_restaurants:
                        new_count = append_to_restaurants_csv(cell_restaurants, cell_id, existing_restaurant_ids)
                        print(f"Added {new_count} new unique restaurants from this cell")
                    
                    # Mark this cell as done
                    update_grid_status(cell_id, 'yes')
                    
                    print(f"Found {total_found} restaurants in cell {cell_id} ({len(cell_restaurants)} unique in this cell)")
                    
                except Exception as e:
                    print(f"Error processing cell {cell_id}: {str(e)}")
                    # If there was an error, mark as not done
                    update_grid_status(cell_id, 'no')
                
                # Save progress periodically to JSON (backup)
                if cell_count % 5 == 0:
                    with open('maryland_restaurants_progress.json', 'w') as f:
                        json.dump(list(all_restaurants.values()), f)
                
                time.sleep(1)  # Brief pause between cells
        
        # Save final results as JSON (backup)
        restaurant_list = list(all_restaurants.values())
        with open('maryland_restaurants_json_backup.json', 'w') as f:
            json.dump(restaurant_list, f)
        
        print(f"\nSearch complete! Found {len(restaurant_list)} new unique restaurants in Maryland.")
        print(f"Total restaurants in database: {len(existing_restaurant_ids) + len(restaurant_list)}")
        print("All data has been saved to maryland_restaurants.csv")
        print("Grid cell statuses have been updated in maryland_grid_cells.csv")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Save whatever data we've collected so far
        if all_restaurants:
            with open('maryland_restaurants_emergency_save.json', 'w') as f:
                json.dump(list(all_restaurants.values()), f)

# Call the main function to start execution
if __name__ == "__main__":
    main()