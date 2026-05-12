## Overview

This project implements a lightweight ETL pipeline using Python and DuckDB to process daily provider delta files and maintain a full provider dataset.


## To run
Create a python virtual enviornment by running: 
`make install`

To run the generator: 
`make run-generator`

## AI Usage:
I used AI to generate a method of creating sample data - 
Prompt given: Create fake data with this schema so that I can test daily delta file changes. The daily delta file contains: 
New providers to be added
Changes to existing providers (matched on id)
model used: Claude Sonnet 4.6
result:generator.py