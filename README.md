# Multi-Functional Data Analysis and Insights Copilot

This Streamlit-based application serves as a comprehensive toolkit for various data analysis and insight generation tasks. It integrates Large Language Models (LLMs) for advanced text processing and data interpretation. Key functionalities include a Medical Insights Copilot, Spreadsheet Analysis with DAG generation, Sales Forecasting using Prophet, and interactive Clustering Analysis.

## Key Features

This application offers a suite of tools to assist with various data-driven tasks:

*   **Medical Insights Copilot:**
    *   Leverages Large Language Models (LLMs) like Groq, ZhipuAI, Gemini, and Tencent Hunyuan for advanced medical text analysis.
    *   Generates general and disease-specific tags from text.
    *   Rewrites text based on specified institutions, departments, or persons.
    *   Identifies key problems or questions within medical texts.
    *   Generates structured data (e.g., tables) from unstructured medical information.
    *   Provides a Q&A interface for querying a medical knowledge base.
    *   Allows exporting generated reports to Microsoft Word (`.docx`) format.

*   **Spreadsheet Analysis:**
    *   Upload and analyze data from Excel (`.xlsx`) or CSV (`.csv`) files, or by pasting JSON data.
    *   Performs automated data analysis and interpretation using LLMs.
    *   Generates Directed Acyclic Graphs (DAGs) to visualize potential relationships and dependencies within the data.
    *   Produces a comprehensive business report summarizing findings and insights.

*   **Sales Forecasting:**
    *   Upload Excel files containing time series data (e.g., sales figures).
    *   Configure forecasting parameters such as date columns, target variables, grouping columns, and forecast horizon.
    *   Utilizes Facebook Prophet to generate time series forecasts.
    *   Visualizes historical data, forecasts, and confidence intervals.
    *   Calculates and displays training and validation accuracy metrics.
    *   Supports the inclusion of covariates to potentially improve forecast accuracy.

*   **Clustering Analysis:**
    *   Upload data files (CSV or Excel) for exploratory analysis.
    *   Perform clustering using K-means or DBSCAN algorithms on selected numeric features.
    *   Option to use existing categorical columns as cluster labels.
    *   Visualizes clustering results, including t-SNE plots for high-dimensional data.
    *   Generates a heatmap of adjusted residuals to analyze the relationship and significance between two different clustering results (or a clustering result and another categorical variable).

*   **Background Audio Player:**
    *   Features an integrated audio player that can play MP3 files from the `audio_folder`.
    *   Allows users to listen to relevant audio content (e.g., medical news, insights) while using the application.

## Setup and Installation

Follow these steps to set up and run the application locally:

**1. Prerequisites:**

*   **Python:** Ensure you have Python 3.8 or higher installed.
*   **Git:** Required to clone the repository.

**2. Clone the Repository:**

```bash
git clone <repository_url> # Replace <repository_url> with the actual URL
cd <repository_directory_name>
```

**3. Install Dependencies:**

It's recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required packages:

```bash
pip install -r requirements.txt
```

**4. Configure API Keys:**

This application uses various Large Language Models, which require API keys. Set these as environment variables:

*   **Groq:** `GROQ_API_KEY`
*   **ZhipuAI (智谱AI):** `ZHIPU_API_KEY`
*   **Google Gemini:** `GEMINI_API_KEY`
*   **Tencent Hunyuan (腾讯混元):** `TENCENT_SECRET_ID` and `TENCENT_SECRET_KEY`

Refer to the respective LLM provider's documentation for obtaining these keys. You can set environment variables in your system or use a `.env` file (ensure `.env` is in your `.gitignore`).

**Example (using a `.env` file with a library like `python-dotenv` - not listed in requirements, so manual loading or direct env setting is assumed):**
Create a file named `.env` in the project root:
```
GROQ_API_KEY="your_groq_api_key"
ZHIPU_API_KEY="your_zhipu_api_key"
GEMINI_API_KEY="your_gemini_api_key"
TENCENT_SECRET_ID="your_tencent_secret_id"
TENCENT_SECRET_KEY="your_tencent_secret_key"
```
*Note: The application's `functions.py` directly uses `os.environ.get()`, so these variables must be available in the environment when the Python script runs.*

**5. Docker Setup (Alternative):**

The project includes a `Dockerfile` and `docker_build.sh` script for containerized deployment.

*   **Build the Docker image:**
    ```bash
    ./docker_build.sh
    ```
*   **Run the Docker container:**
    (The `docker_build.sh` script might include a run command, or you'll need to run it manually, ensuring API keys are passed to the container's environment).
    Example:
    ```bash
    docker run -p 8501:8501 -e GROQ_API_KEY=$GROQ_API_KEY -e ZHIPU_API_KEY=$ZHIPU_API_KEY ... <image_name>
    ```
    Adjust the `docker run` command based on the image name and how API keys are managed in your Docker workflow.

## Usage

Once the setup is complete, you can run the Streamlit application:

```bash
streamlit run main.py
```

This will typically open the application in your default web browser (e.g., at `http://localhost:8501`).

**Navigating the Application:**

*   Use the sidebar to select the desired functionality:
    *   **Medical Insights Copilot:** For text analysis, generation, and Q&A.
    *   **Spreadsheet Analysis:** To upload and analyze tabular data.
    *   **Sales Forecasting:** For time series prediction.
    *   **Cluster Analysis:** For K-means/DBSCAN clustering and heatmap visualizations.
*   Follow the on-screen instructions within each section to upload files, input text, or configure parameters.

**Audio Player:**

*   The application includes a background audio player.
*   You can add your own `.mp3` files to the `audio_folder` in the repository.
*   Select the audio file from the dropdown menu at the top of the application to play it.

## Project Structure (Overview)

Here's a brief overview of some key files and directories:

*   `main.py`: The main entry point for the Streamlit application. Handles UI layout and navigation between different modules.
*   `functions.py`: Contains core functions for interacting with LLMs, data processing, and other backend logic.
*   `config.py`: Likely stores configuration variables, prompts, and lists used throughout the application (e.g., topics, diseases, system messages for LLMs).
*   `layout.py`: Potentially defines the layout and UI components for the Streamlit interface, specifically for the Medical Insights Copilot.
*   `dagrelation.py`: Contains the `DAGRelations` class used for analyzing and reporting relationships in the Spreadsheet Analysis feature.
*   `datadescription.py`: Includes the `DataDescription` class for generating descriptive statistics of datasets in the Spreadsheet Analysis feature.
*   `requirements.txt`: Lists all Python dependencies for the project.
*   `Dockerfile` & `docker_build.sh`: Used for building and managing Docker containers for the application.
*   `audio_folder/`: Contains MP3 files for the background audio player.
*   `.streamlit/config.toml`: Streamlit configuration file.
*   `*.pkl` files: These are likely serialized Python objects, possibly pre-trained models, embeddings, or cached data. Examples: `medical_text_embeddings.pkl`.

## Contributing

Contributions are welcome! If you'd like to improve the application or add new features, please follow these general steps:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name
    ```
3.  **Make your changes** and commit them with clear messages.
4.  **Push your branch** to your fork:
    ```bash
    git push origin feature/your-feature-name
    ```
5.  **Open a Pull Request** to the main repository, describing your changes.

Please ensure your code adheres to any existing style guidelines and that you test your changes thoroughly.

## License

This project is currently not licensed.

It is recommended to add a license file (e.g., MIT, Apache 2.0) to define how others can use, modify, and distribute the code. Once a license is chosen, update this section to refer to the `LICENSE` file in the repository.
