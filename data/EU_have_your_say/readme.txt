# EU Have Your Say Dataset

## Provenance
This dataset is sourced from the European Commission's "Have Your Say" platform, which allows citizens, businesses, and other stakeholders to provide feedback on EU initiatives, laws, and policies at different stages of the legislative process.

## License
The data is provided under the European Commission's reuse policy, which is based on the Creative Commons Attribution 4.0 International (CC BY 4.0) license. This allows for reuse of the data for both commercial and non-commercial purposes, as long as appropriate credit is given.

## Data Structure
The dataset contains several files:

1. feedback.csv - Contains feedback submissions with the following fields:
   - id: Unique identifier for the feedback
   - publication_id: ID of the initiative/publication the feedback is related to
   - timestamp: Time when the feedback was submitted
   - tr_number: Transaction number
   - language: Language of the feedback
   - country: Country of origin
   - organization: Organization name (if applicable)
   - surname: Submitter's surname
   - first_name: Submitter's first name
   - status: Status of the feedback
   - feedback: The actual feedback text
   - date_feedback: Date of submission
   - publication: Title of the initiative/publication
   - user_type: Type of user (individual, organization, etc.)
   - company_size: Size of the company (if applicable)
   - reference_initiative: Reference to the initiative

2. initiatives.csv - Contains information about EU initiatives with fields such as:
   - id: Unique identifier for the initiative
   - title: Title of the initiative
   - description: Description of the initiative
   - status: Current status of the initiative
   - start_date: Start date of the consultation period
   - end_date: End date of the consultation period
   - policy_area: Policy area the initiative belongs to
   - type: Type of initiative

3. haveyoursay.db - SQLite database containing the structured data from the platform

## Research Value
This dataset is valuable for studying public participation in EU policy-making, stakeholder engagement, and the influence of public feedback on legislative outcomes. It provides insights into the concerns and priorities of different stakeholders across EU member states and how they engage with various policy areas.

## Citation
When using this dataset, please cite:
"European Commission. Have Your Say: Your Voice in Europe. https://ec.europa.eu/info/law/better-regulation/have-your-say"
