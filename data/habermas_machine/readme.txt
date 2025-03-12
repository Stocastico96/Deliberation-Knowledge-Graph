# Habermas Machine Dataset

## Provenance
The Habermas Machine dataset is derived from a deliberative democracy experiment inspired by Jürgen Habermas's theories of communicative rationality and deliberative democracy. The experiment was designed to study how structured deliberation affects preference formation and decision-making in groups.

## License
The dataset is provided for research purposes. For specific licensing details, please refer to the original research publication or contact the authors.

## Data Structure
The dataset contains several Parquet files:

1. hm_all_candidate_comparisons.parquet - Contains pairwise comparisons between candidates/options made by participants during the deliberation process.

2. hm_all_final_preference_rankings.parquet - Contains the final preference rankings of participants after the deliberation process.

3. hm_all_position_statement_ratings.parquet - Contains ratings given to position statements by participants.

4. hm_all_round_survey_responses.parquet - Contains survey responses collected from participants after each round of deliberation.

The Parquet file format is a columnar storage format that provides efficient data compression and encoding schemes. These files can be read using tools like Python's pandas library with the pyarrow or fastparquet engine.

## Research Value
This dataset is valuable for studying deliberative democracy, preference formation, and the impact of structured deliberation on decision-making. It provides insights into how individuals' preferences change through deliberation and how group dynamics influence collective decision-making.

## Citation
When using this dataset, please cite the original research publication (details to be provided by the dataset owners).

## Note on Data Format
The dataset is stored in Parquet format, which is optimized for analytical processing. To work with this data, you may need specialized tools or libraries that support the Parquet format, such as:
- Python: pandas with pyarrow or fastparquet
- R: arrow package
- SQL: Presto, Hive, or other big data query engines
