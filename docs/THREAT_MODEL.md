# Threat model

## Assets
- URL analysis results
- Stored analysis history
- Backend API integrity
- Model metadata and schema version

## Threats
- Malicious input strings designed to trigger parser issues
- Unsafe remote fetch or browser preview attempts
- Unsafe code execution via untrusted strings
- Data leakage through debug errors

## Controls
- Strict URL validation and allowed scheme restriction
- Backend-only parsing with no network access
- Safe data handling and limited storage
- Generic error handling for HTTP responses
