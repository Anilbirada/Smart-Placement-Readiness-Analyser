# ML workflow

This directory holds the reproducible model workflow for the suspicious URL detector.

## Expected dataset

The training script expects a CSV file with at least these columns:

- `url`
- `label`

Optional columns may be included for provenance or source metadata.

## Training script

Run:

```bash
python ml/scripts/train_model.py --dataset-path /path/to/urls.csv --output-path ml/models/url_classifier.joblib
```

The script performs basic validation, feature extraction, a train/test split, and a logistic regression baseline. It then saves the model and metadata in a compatible format.

## Notes

If no trusted dataset is configured, the application stays in the documented rule-based fallback mode and clearly labels that state.
