# DeliData Dataset

## Provenance
DeliData is a dataset for deliberation in multi-party problem solving, created by Georgi Karadzhov, Tom Stafford, and Andreas Vlachos. It was published in the Proceedings of the ACM on Human-Computer Interaction.

## License
The dataset is provided for research purposes under academic fair use. For specific licensing details, please refer to the original publication.

## Data Structure
The dataset contains deliberation records with the following key fields:

- group_id: Unique identifier of the group chat
- message_id: Message identifier (system messages have an id of -1)
- message_type: Type of message (INITIAL, SUBMIT, MESSAGE)
- origin: The alias of the participant who submitted a message/solution
- original_text: Original text as said in the collected conversation
- clean_text: Normalized message with applied tokenization and masking of special tokens
- annotation_type: First level of DeliAnnotation (Probing, Non-probing deliberation, None)
- annotation_target: Second level of DeliAnnotation (Moderation, Reasoning, Solution, Agree, Disagree)
- annotation_additional: Third level of DeliAnnotation
- team_performance: An approximation of team performance based on user submissions and solution mentions
- performance_change: Change of performance compared to the previous utterance
- sol_tracker_message: Extracted solution from the current message
- sol_tracker_all: Up-to-date "state-of-mind" for each participant

## Research Value
This dataset is valuable for studying deliberation processes, multi-party problem-solving, and the dynamics of group decision-making. It provides insights into how teams collaborate to solve problems and how different types of communication affect team performance.

## Citation
When using this dataset, please cite:
```
@article{karadzhov2023delidata,
    title={DeliData: A dataset for deliberation in multi-party problem solving},
    author={Karadzhov, Georgi and Stafford, Tom and Vlachos, Andreas},
    journal={Proceedings of the ACM on Human-Computer Interaction},
    volume={7},
    number={CSCW2},
    pages={1--25},
    year={2023},
    publisher={ACM New York, NY, USA}
}
```

For more information, visit: https://delibot.xyz/delidata
