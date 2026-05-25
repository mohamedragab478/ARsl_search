# Arabic Sign Language (ArSL) Search

A tool for searching and retrieving Arabic Sign Language (ArSL) GIFs based on text queries. 

## Features
- **Text-to-Sign Search:** Find relevant sign language GIFs using Arabic text.
- **Dataset Generation:** Scripts to process and format the GIF dataset.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/yourusername/ARsl_search.git
cd ARsl_search

# Install dependencies
uv sync
```

## Dataset (`data_gifs`)

The `data_gifs` directory contains the required GIF files for the signs. Due to its large size, it is not included in this repository. 
Please ensure you place the `data_gifs` folder (containing the `.gif` files) in the root directory before running the scripts.

## Usage

Run the main search interface:
```bash
python sign_search.py
```
