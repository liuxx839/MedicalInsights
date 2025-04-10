import pandas as pd
import numpy as np
import json
from scipy import stats
import warnings
import re

class DataDescription:
    def __init__(self, data, include_histogram=False, string_threshold=30):
        """
        Initialize the data description analyzer.
        
        Parameters:
        data (pandas.DataFrame): DataFrame to analyze
        include_histogram (bool): Whether to include histogram data for continuous variables
        string_threshold (int): Maximum average word length to classify as categorical instead of string
        """
        self.data = data
        self.descriptions = {}
        self.errors = []
        self.include_histogram = include_histogram
        self.string_threshold = string_threshold
        
    def analyze_data(self):
        """
        Analyze all columns in the dataframe based on their data types.
        Returns self for chaining.
        """
        # Suppress specific warnings
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
        
        for column in self.data.columns:
            try:
                print(f"Analyzing {column}...")
                self._analyze_column(column)
            except Exception as e:
                error_msg = f"Error analyzing {column}: {str(e)}"
                print(error_msg)
                self.errors.append(error_msg)
        
        return self
    
    def _is_string_type(self, column):
        """
        Determines if a column should be classified as string type rather than categorical.
        
        Parameters:
        column (str): Column name to analyze
        
        Returns:
        bool: True if the column should be classified as string, False otherwise
        """
        col_data = self.data[column].dropna().astype(str)
        
        if len(col_data) == 0:
            return False
            
        # Check if values contain longer text
        avg_length = col_data.str.len().mean()
        
        # Check for word count
        avg_word_count = col_data.str.split().str.len().mean()
        
        # Check if values contain sentences (periods, exclamation, question marks)
        has_sentences = any(col_data.str.contains(r'[.!?]\s+[A-Z]'))
        
        # Check uniqueness ratio - high uniqueness suggests strings/descriptions
        uniqueness_ratio = len(col_data.unique()) / len(col_data)
        
        # Determine if string type based on thresholds
        is_string = (avg_length > self.string_threshold or 
                    avg_word_count > 5 or 
                    has_sentences or 
                    uniqueness_ratio > 0.8)
        
        return is_string
    
    def _analyze_column(self, column):
        """
        Analyze a single column based on its data type.
        
        Parameters:
        column (str): Column name to analyze
        """
        # Skip analysis if column has all NaN values
        if self.data[column].isna().all():
            self.descriptions[column] = {
                "type": "unknown",
                "missing_count": len(self.data),
                "missing_percentage": 100.0,
                "analysis": "Column contains all missing values"
            }
            return
        
        # Determine the data type
        col_data = self.data[column]
        col_type = col_data.dtype
        
        # Count missing values
        missing_count = col_data.isna().sum()
        missing_percentage = (missing_count / len(col_data)) * 100
        
        # Determine if the column should be treated as categorical, continuous, or string
        if np.issubdtype(col_type, np.number):
            # Additional check for binary or few-valued numeric columns
            unique_values = col_data.dropna().unique()
            if len(unique_values) <= min(10, len(col_data) // 10):  # Heuristic for categorical numeric data
                self._analyze_categorical(column, missing_count, missing_percentage)
            else:
                self._analyze_continuous(column, missing_count, missing_percentage)
        elif col_type == 'bool':
            self._analyze_boolean(column, missing_count, missing_percentage)
        elif np.issubdtype(col_type, np.datetime64):
            self._analyze_datetime(column, missing_count, missing_percentage)
        else:
            # Check if this should be treated as a string field rather than categorical
            if self._is_string_type(column):
                self._analyze_string(column, missing_count, missing_percentage)
            else:
                # For strings with shorter values, analyze as categorical
                self._analyze_categorical(column, missing_count, missing_percentage)
    
    def _analyze_continuous(self, column, missing_count, missing_percentage):
        """
        Analyze a continuous numeric column.
        """
        col_data = self.data[column].dropna()
        
        # Basic statistics
        stats_dict = {
            "type": "continuous",
            "count": len(col_data),
            "missing_count": missing_count,
            "missing_percentage": missing_percentage,
            "min": float(col_data.min()),
            "max": float(col_data.max()),
            "mean": float(col_data.mean()),
            "median": float(col_data.median()),
            "std": float(col_data.std()),
            "q1": float(col_data.quantile(0.25)),
            "q3": float(col_data.quantile(0.75)),
            "iqr": float(col_data.quantile(0.75) - col_data.quantile(0.25))
        }
        
        # Add variance
        stats_dict["variance"] = float(col_data.var())
        
        # Add skewness and kurtosis
        try:
            stats_dict["skewness"] = float(stats.skew(col_data))
            stats_dict["kurtosis"] = float(stats.kurtosis(col_data))
        except:
            stats_dict["skewness"] = None
            stats_dict["kurtosis"] = None
        
        # Test for normality
        try:
            if len(col_data) >= 8:  # Minimum sample size for Shapiro-Wilk test
                shapiro_test = stats.shapiro(col_data.sample(min(5000, len(col_data))))
                stats_dict["normality_test"] = {
                    "test": "shapiro",
                    "statistic": float(shapiro_test[0]),
                    "p_value": float(shapiro_test[1]),
                    "is_normal": shapiro_test[1] > 0.05
                }
        except:
            pass
        
        # Detect outliers using IQR method
        q1 = col_data.quantile(0.25)
        q3 = col_data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
        
        stats_dict["outliers"] = {
            "count": int(len(outliers)),
            "percentage": float((len(outliers) / len(col_data)) * 100) if len(col_data) > 0 else 0,
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound)
        }
        
        # Calculate histogram data for distribution overview only if requested
        if self.include_histogram:
            try:
                hist_values, hist_bins = np.histogram(col_data, bins='auto')
                stats_dict["histogram"] = {
                    "bin_edges": hist_bins.tolist(),
                    "counts": hist_values.tolist()
                }
            except:
                pass
        
        self.descriptions[column] = stats_dict
    
    def _analyze_categorical(self, column, missing_count, missing_percentage):
        """
        Analyze a categorical column.
        """
        col_data = self.data[column].dropna()
        
        # Get value counts and calculate percentages
        value_counts = col_data.value_counts()
        value_percentages = (col_data.value_counts(normalize=True) * 100).round(2)
        
        # Combine counts and percentages
        categories = {}
        for val in value_counts.index:
            categories[str(val)] = {
                "count": int(value_counts[val]),
                "percentage": float(value_percentages[val])
            }
        
        stats_dict = {
            "type": "categorical",
            "count": int(len(col_data)),
            "missing_count": int(missing_count),
            "missing_percentage": float(missing_percentage),
            "unique_values": int(len(value_counts))
        }
        
        # Add most and least common categories
        if len(value_counts) > 0:
            most_common = value_counts.index[0]
            least_common = value_counts.index[-1]
            stats_dict["most_common"] = {
                "value": str(most_common),
                "count": int(value_counts[most_common]),
                "percentage": float(value_percentages[most_common])
            }
            stats_dict["least_common"] = {
                "value": str(least_common),
                "count": int(value_counts[least_common]),
                "percentage": float(value_percentages[least_common])
            }
        
        # Calculate entropy to measure distribution uniformity
        try:
            probs = value_percentages / 100
            entropy = -(probs * np.log2(probs)).sum()
            max_entropy = np.log2(len(value_counts)) if len(value_counts) > 0 else 0
            stats_dict["entropy"] = {
                "value": float(entropy),
                "max_possible": float(max_entropy),
                "normalized": float(entropy / max_entropy) if max_entropy > 0 else 0
            }
        except:
            pass
        
        # If too many categories, limit the output
        if len(categories) > 20:
            top_categories = {}
            for val in value_counts.index[:10]:  # Top 10
                top_categories[str(val)] = categories[str(val)]
            stats_dict["categories"] = {
                "top_10": top_categories,
                "total_categories": len(categories)
            }
        else:
            stats_dict["categories"] = categories
        
        self.descriptions[column] = stats_dict
    
    def _analyze_string(self, column, missing_count, missing_percentage):
        """
        Analyze a string/text column.
        """
        col_data = self.data[column].dropna().astype(str)
        
        # Basic text statistics
        char_lengths = col_data.str.len()
        word_counts = col_data.str.split().str.len()
        
        stats_dict = {
            "type": "string",
            "count": int(len(col_data)),
            "missing_count": int(missing_count),
            "missing_percentage": float(missing_percentage),
            "unique_values": int(len(col_data.unique())),
            "uniqueness_ratio": float(len(col_data.unique()) / len(col_data)) if len(col_data) > 0 else 0,
            "text_length": {
                "min_chars": int(char_lengths.min()) if not char_lengths.empty else 0,
                "max_chars": int(char_lengths.max()) if not char_lengths.empty else 0,
                "avg_chars": float(char_lengths.mean()) if not char_lengths.empty else 0,
                "min_words": int(word_counts.min()) if not word_counts.empty else 0,
                "max_words": int(word_counts.max()) if not word_counts.empty else 0,
                "avg_words": float(word_counts.mean()) if not word_counts.empty else 0
            }
        }
        
        # Check for patterns
        has_emails = col_data.str.contains(r'[^@]+@[^@]+\.[^@]+').any()
        has_urls = col_data.str.contains(r'https?://\S+|www\.\S+').any()
        has_numbers = col_data.str.contains(r'\d+').any()
        has_special_chars = col_data.str.contains(r'[^\w\s]').any()
        
        stats_dict["patterns"] = {
            "contains_emails": bool(has_emails),
            "contains_urls": bool(has_urls),
            "contains_numbers": bool(has_numbers),
            "contains_special_chars": bool(has_special_chars)
        }
        
        # Common words and their frequency (if more than one word present)
        if word_counts.max() > 1:
            # Flatten all words into a single list
            all_words = []
            for text in col_data:
                words = re.findall(r'\b\w+\b', text.lower())
                all_words.extend(words)
            
            # Count word frequencies
            if all_words:
                word_freq = pd.Series(all_words).value_counts()
                top_words = {}
                for word, count in word_freq.head(10).items():
                    top_words[word] = int(count)
                
                stats_dict["word_frequency"] = {
                    "total_words": len(all_words),
                    "unique_words": len(word_freq),
                    "top_words": top_words
                }
        
        # Sample values (first few values)
        if len(col_data) > 0:
            sample_values = col_data.head(3).tolist()
            stats_dict["sample_values"] = sample_values
        
        self.descriptions[column] = stats_dict
    
    def _analyze_boolean(self, column, missing_count, missing_percentage):
        """
        Analyze a boolean column.
        """
        col_data = self.data[column].dropna()
        
        true_count = col_data.sum()
        false_count = len(col_data) - true_count
        
        stats_dict = {
            "type": "boolean",
            "count": int(len(col_data)),
            "missing_count": int(missing_count),
            "missing_percentage": float(missing_percentage),
            "true_count": int(true_count),
            "false_count": int(false_count),
            "true_percentage": float((true_count / len(col_data)) * 100) if len(col_data) > 0 else 0,
            "false_percentage": float((false_count / len(col_data)) * 100) if len(col_data) > 0 else 0
        }
        
        self.descriptions[column] = stats_dict
    
    def _analyze_datetime(self, column, missing_count, missing_percentage):
        """
        Analyze a datetime column.
        """
        col_data = self.data[column].dropna()
        
        stats_dict = {
            "type": "datetime",
            "count": int(len(col_data)),
            "missing_count": int(missing_count),
            "missing_percentage": float(missing_percentage),
            "min": col_data.min().isoformat() if not col_data.empty else None,
            "max": col_data.max().isoformat() if not col_data.empty else None,
            "range_days": int((col_data.max() - col_data.min()).days) if not col_data.empty else None
        }
        
        # Calculate time distribution by year, month, day of week
        if not col_data.empty:
            years_count = col_data.dt.year.value_counts().to_dict()
            months_count = col_data.dt.month.value_counts().sort_index().to_dict()
            weekdays_count = col_data.dt.dayofweek.value_counts().sort_index().to_dict()
            
            # Convert keys to strings for JSON serialization
            stats_dict["distribution"] = {
                "years": {str(k): int(v) for k, v in years_count.items()},
                "months": {str(k): int(v) for k, v in months_count.items()},
                "weekdays": {str(k): int(v) for k, v in weekdays_count.items()}
            }
        
        self.descriptions[column] = stats_dict
    
    def to_json(self, indent=2):
        """
        Convert the descriptions to a JSON string.
        
        Parameters:
        indent (int): Indentation level for JSON formatting
        
        Returns:
        str: JSON string representation of the data descriptions
        """
        # Create a copy to avoid modifying the original
        output_dict = {
            "column_descriptions": self.descriptions,
            "dataset_info": {
                "rows": int(len(self.data)),
                "columns": int(len(self.data.columns)),
                "total_cells": int(len(self.data) * len(self.data.columns)),
                "missing_cells": int(self.data.isna().sum().sum()),
                "missing_percentage": float((self.data.isna().sum().sum() / (len(self.data) * len(self.data.columns)) * 100) if len(self.data) * len(self.data.columns) > 0 else 0)
            }
        }
        
        # Add data types summary
        type_counts = {}
        for col, desc in self.descriptions.items():
            col_type = desc.get("type", "unknown")
            type_counts[col_type] = type_counts.get(col_type, 0) + 1
        output_dict["data_types_summary"] = type_counts
        
        # Add errors if any
        if self.errors:
            output_dict["errors"] = self.errors
        
        # Convert to JSON
        return json.dumps(output_dict, indent=indent, default=str)
    
    def save_json(self, filename):
        """
        Save the descriptions to a JSON file.
        
        Parameters:
        filename (str): Name of the file to save to
        
        Returns:
        bool: True if successful, False otherwise
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            print(f"Successfully saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            return False


# # Example usage
# if __name__ == "__main__":
#     try:
#         # Load sample data
#         df = pd.read_excel('CV_B1-guangdong1_poc.group_bound.nogongguan_actual.xlsx')
#         print(f"Successfully loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
        
#         # Analyze the data (histogram disabled by default)
#         analyzer = DataDescription(df, include_histogram=False, string_threshold=10)
#         analyzer.analyze_data()
        
#         # Output to JSON
#         json_output = analyzer.to_json()
#         print("Analysis complete. JSON output sample:")
#         print(json_output[:500] + "..." if len(json_output) > 500 else json_output)
        
#         # Save to file
#         analyzer.save_json('data_description.json')
        
#     except Exception as e:
#         print(f"Error in main: {str(e)}")