import json
import time
from yelpapi import YelpAPI
from dotenv import load_dotenv
load_dotenv()
import os
import pandas as pd
from typing import List, Dict, Any
import logging
from datetime import datetime

class MarylandRestaurantCollector:
    def __init__(self, api_key: str):
        """Initialize the Yelp API client and logger"""
        self.yelp_api = YelpAPI(api_key)
        self.all_restaurants = []
        self.setup_logger()
        
    def setup_logger(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('MarylandRestaurantCollector')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter('%(levelname)s - %(message)s')
        
        # File handler for detailed logs
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(f'logs/maryland_restaurants_{timestamp}.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Logger initialized successfully")
        
    def search_restaurants_by_location(self, location: str, offset: int = 0) -> Dict[str, Any]:
        """
        Search for restaurants in a specific location with pagination
        """
        try:
            self.logger.debug(f"Searching restaurants in {location} with offset {offset}")
            response = self.yelp_api.search_query(
                location=location,
                categories='restaurants',
                limit=50,  # Maximum allowed per request
                offset=offset,
                sort_by='best_match'
            )
            self.logger.debug(f"Successfully retrieved {len(response.get('businesses', []))} businesses from {location}")
            return response
        except Exception as e:
            self.logger.error(f"Error searching restaurants in {location} at offset {offset}: {e}")
            return None
    
    def get_business_details(self, business_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific business
        """
        try:
            self.logger.debug(f"Fetching details for business ID: {business_id}")
            details = self.yelp_api.business_query(id=business_id)
            self.logger.debug(f"Successfully retrieved details for business: {details.get('name', 'Unknown')}")
            return details
        except Exception as e:
            self.logger.error(f"Error getting details for business {business_id}: {e}")
            return None
    
    def collect_restaurants_from_location(self, location: str) -> List[Dict[str, Any]]:
        """
        Collect all restaurants from a specific location with pagination
        """
        restaurants = []
        offset = 0
        max_results = 1000  # Yelp API limit
        
        self.logger.info(f"Starting collection for location: {location}")
        start_time = time.time()
        
        while offset < max_results:
            self.logger.info(f"Fetching results {offset + 1}-{offset + 50} for {location}")
            
            response = self.search_restaurants_by_location(location, offset)
            
            if not response or 'businesses' not in response:
                self.logger.warning(f"No response or businesses found for {location} at offset {offset}")
                break
                
            businesses = response['businesses']
            
            if not businesses:
                self.logger.info(f"No more businesses found for {location} at offset {offset}")
                break
                
            # Get detailed information for each business
            for i, business in enumerate(businesses):
                business_id = business['id']
                business_name = business.get('name', 'Unknown')
                
                self.logger.debug(f"Processing business {i+1}/{len(businesses)}: {business_name} (ID: {business_id})")
                
                detailed_info = self.get_business_details(business_id)
                
                if detailed_info:
                    restaurants.append(detailed_info)
                    self.logger.debug(f"Added detailed info for: {business_name}")
                else:
                    self.logger.warning(f"Failed to get details for: {business_name}, using basic info")
                    restaurants.append(business)
                    
                # Add small delay to respect API rate limits
                time.sleep(0.1)
            
            offset += len(businesses)
            
            # If we got fewer than 50 results, we've reached the end
            if len(businesses) < 50:
                self.logger.info(f"Reached end of results for {location} (got {len(businesses)} results)")
                break
                
            # Add delay between pagination requests
            time.sleep(0.5)
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Completed collection for {location}: {len(restaurants)} restaurants in {elapsed_time:.2f} seconds")
        return restaurants
    
    def collect_all_maryland_restaurants(self) -> List[Dict[str, Any]]:
        """
        Collect restaurants from major Maryland cities and regions
        """
        self.logger.info("Starting collection of all Maryland restaurants")
        collection_start_time = time.time()
        
        maryland_locations = [
            "Baltimore, MD",
            "Annapolis, MD",
            "Frederick, MD",
            "Gaithersburg, MD",
            "Rockville, MD",
            "Bowie, MD",
            "Hagerstown, MD",
            "College Park, MD",
            "Salisbury, MD",
            "Cumberland, MD",
            "Takoma Park, MD",
            "Greenbelt, MD",
            "Laurel, MD",
            "Ocean City, MD",
            "Bethesda, MD",
            "Silver Spring, MD",
            "Columbia, MD",
            "Germantown, MD",
            "Waldorf, MD",
            "Glen Burnie, MD"
        ]
        
        self.logger.info(f"Will process {len(maryland_locations)} Maryland locations")
        
        all_restaurants = []
        seen_business_ids = set()
        location_stats = {}
        
        for i, location in enumerate(maryland_locations):
            self.logger.info(f"Processing location {i+1}/{len(maryland_locations)}: {location}")
            location_start_time = time.time()
            
            restaurants = self.collect_restaurants_from_location(location)
            
            # Track statistics for this location
            initial_count = len(restaurants)
            duplicates_removed = 0
            
            # Remove duplicates based on business ID
            for restaurant in restaurants:
                business_id = restaurant.get('id')
                if business_id and business_id not in seen_business_ids:
                    all_restaurants.append(restaurant)
                    seen_business_ids.add(business_id)
                else:
                    duplicates_removed += 1
                    self.logger.debug(f"Duplicate business ID found: {business_id}")
            
            location_elapsed = time.time() - location_start_time
            unique_added = initial_count - duplicates_removed
            
            location_stats[location] = {
                'total_found': initial_count,
                'duplicates_removed': duplicates_removed,
                'unique_added': unique_added,
                'processing_time': location_elapsed
            }
            
            self.logger.info(f"Location {location} summary: {initial_count} found, {duplicates_removed} duplicates, {unique_added} unique added")
            self.logger.info(f"Running total: {len(all_restaurants)} unique restaurants")
            
            # Add delay between locations to be respectful to API
            if i < len(maryland_locations) - 1:  # Don't wait after the last location
                self.logger.debug("Waiting 2 seconds before next location...")
                time.sleep(2)
        
        total_elapsed = time.time() - collection_start_time
        
        # Log final summary
        self.logger.info("=" * 60)
        self.logger.info("COLLECTION COMPLETE - FINAL SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total unique restaurants collected: {len(all_restaurants)}")
        self.logger.info(f"Total processing time: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
        
        # Log per-location statistics
        self.logger.info("\nPer-location statistics:")
        for location, stats in location_stats.items():
            self.logger.info(f"  {location}: {stats['unique_added']} unique ({stats['total_found']} total, {stats['duplicates_removed']} duplicates) - {stats['processing_time']:.1f}s")
        
        total_found = sum(stats['total_found'] for stats in location_stats.values())
        total_duplicates = sum(stats['duplicates_removed'] for stats in location_stats.values())
        
        self.logger.info(f"\nOverall statistics:")
        self.logger.info(f"  Total businesses found: {total_found}")
        self.logger.info(f"  Total duplicates removed: {total_duplicates}")
        self.logger.info(f"  Unique restaurants: {len(all_restaurants)}")
        self.logger.info(f"  Deduplication rate: {(total_duplicates/total_found)*100:.1f}%")
        
        self.all_restaurants = all_restaurants
        self.logger.info("Restaurant collection stored in class instance")
        return all_restaurants
    
    def save_to_json(self, filename: str = "maryland_restaurants.json"):
        """
        Save collected data to JSON file
        """
        try:
            self.logger.info(f"Saving {len(self.all_restaurants)} restaurants to JSON file: {filename}")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_restaurants, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Successfully saved data to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to JSON file {filename}: {e}")
    
    def save_to_csv(self, filename: str = "maryland_restaurants.csv"):
        """
        Save collected data to CSV file with flattened structure
        """
        if not self.all_restaurants:
            self.logger.warning("No data to save to CSV")
            return
        
        try:
            self.logger.info(f"Converting {len(self.all_restaurants)} restaurants to CSV format")
            
            # Flatten the nested data for CSV format
            flattened_data = []
            
            for restaurant in self.all_restaurants:
                flat_record = {
                    'id': restaurant.get('id'),
                    'name': restaurant.get('name'),
                    'alias': restaurant.get('alias'),
                    'image_url': restaurant.get('image_url'),
                    'is_closed': restaurant.get('is_closed'),
                    'url': restaurant.get('url'),
                    'review_count': restaurant.get('review_count'),
                    'rating': restaurant.get('rating'),
                    'phone': restaurant.get('phone'),
                    'display_phone': restaurant.get('display_phone'),
                    'price': restaurant.get('price'),
                    'distance': restaurant.get('distance'),
                    
                    # Location information
                    'address1': restaurant.get('location', {}).get('address1'),
                    'address2': restaurant.get('location', {}).get('address2'),
                    'address3': restaurant.get('location', {}).get('address3'),
                    'city': restaurant.get('location', {}).get('city'),
                    'zip_code': restaurant.get('location', {}).get('zip_code'),
                    'country': restaurant.get('location', {}).get('country'),
                    'state': restaurant.get('location', {}).get('state'),
                    'cross_streets': restaurant.get('location', {}).get('cross_streets'),
                    
                    # Coordinates
                    'latitude': restaurant.get('coordinates', {}).get('latitude'),
                    'longitude': restaurant.get('coordinates', {}).get('longitude'),
                    
                    # Categories
                    'categories': ', '.join([cat.get('title', '') for cat in restaurant.get('categories', [])]),
                    'category_aliases': ', '.join([cat.get('alias', '') for cat in restaurant.get('categories', [])]),
                    
                    # Hours
                    'is_open_now': restaurant.get('hours', [{}])[0].get('is_open_now') if restaurant.get('hours') else None,
                    
                    # Transactions
                    'transactions': ', '.join(restaurant.get('transactions', [])),
                }
                
                flattened_data.append(flat_record)
            
            df = pd.DataFrame(flattened_data)
            df.to_csv(filename, index=False)
            self.logger.info(f"Successfully saved {len(flattened_data)} records to CSV file: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving to CSV file {filename}: {e}")
    
    def print_summary(self):
        """
        Print summary statistics of collected data
        """
        if not self.all_restaurants:
            self.logger.warning("No data collected for summary")
            return
        
        self.logger.info("Generating summary statistics...")
        
        print(f"\n--- Maryland Restaurants Collection Summary ---")
        print(f"Total restaurants collected: {len(self.all_restaurants)}")
        
        # Rating distribution
        ratings = [r.get('rating', 0) for r in self.all_restaurants if r.get('rating')]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f"Average rating: {avg_rating:.2f}")
            print(f"Rating range: {min(ratings)} - {max(ratings)}")
            self.logger.info(f"Rating statistics: avg={avg_rating:.2f}, range={min(ratings)}-{max(ratings)}")
        
        # City distribution
        cities = {}
        for restaurant in self.all_restaurants:
            city = restaurant.get('location', {}).get('city', 'Unknown')
            cities[city] = cities.get(city, 0) + 1
        
        print(f"\nTop 10 cities by restaurant count:")
        top_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]
        for city, count in top_cities:
            print(f"  {city}: {count}")
        
        self.logger.info(f"Top cities: {dict(top_cities)}")
        
        # Price distribution
        prices = {}
        for restaurant in self.all_restaurants:
            price = restaurant.get('price', 'Not specified')
            prices[price] = prices.get(price, 0) + 1
        
        print(f"\nPrice distribution:")
        for price, count in sorted(prices.items()):
            print(f"  {price}: {count}")
            
        self.logger.info(f"Price distribution: {prices}")

def main():
    """
    Main function to collect Maryland restaurant data
    """
    # Initialize the collector with your API key
    api_key = os.getenv("YELPFUSION_API_KEY")
        
    collector = MarylandRestaurantCollector(api_key)
    
    # Collect all Maryland restaurants
    collector.logger.info("Starting Maryland restaurant data collection process")
    restaurants = collector.collect_all_maryland_restaurants()
    
    # Save the data
    collector.save_to_json("maryland_restaurants_full.json")
    collector.save_to_csv("maryland_restaurants_full.csv")
    
    # Print summary
    collector.print_summary()
    
    collector.logger.info("Data collection process completed successfully!")

if __name__ == "__main__":
    main()