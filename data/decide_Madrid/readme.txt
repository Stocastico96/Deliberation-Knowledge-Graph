# Decide Madrid Dataset

## Provenance
This dataset is sourced from the Decide Madrid platform, the official citizen participation portal of the Madrid City Council. The platform allows citizens to propose, debate, and vote on various initiatives for the city.

## License
The data is provided under the Open Data Commons Open Database License (ODbL), which allows sharing, creating, and adapting the data as long as attribution is provided, and any derived database is shared under the same terms.

## Data Structure
The dataset contains two main files:
1. proposals.csv - Contains citizen proposals with the following fields:
   - id: Unique identifier for the proposal
   - url: Web address of the proposal on the Decide Madrid platform
   - code: Unique code for the proposal
   - title: Title of the proposal
   - userId: ID of the user who submitted the proposal
   - date: Date when the proposal was submitted
   - summary: Brief summary of the proposal
   - text: Full text of the proposal
   - numComments: Number of comments on the proposal
   - status: Current status of the proposal (e.g., archived)
   - numSupports: Number of supports/votes the proposal received
   - isAssociation: Whether the proposal was submitted by an association (0=no, 1=yes)

2. comments.csv - Contains comments on proposals with the following fields:
   - id: Unique identifier for the comment
   - proposalId: ID of the proposal the comment is associated with
   - userId: ID of the user who submitted the comment
   - date: Date when the comment was submitted
   - text: Content of the comment

## Research Value
This dataset is valuable for studying citizen participation, deliberative democracy, and the effectiveness of digital platforms in civic engagement. It provides insights into the types of proposals citizens make, how they are received by the community, and the nature of public discourse around urban issues.

## Citation
When using this dataset, please cite:
"Decide Madrid. Madrid City Council. https://decide.madrid.es/"
