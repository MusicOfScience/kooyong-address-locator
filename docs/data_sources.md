# Data Sources

MOE uses loader interfaces for:
- Australian Electoral Commission (AEC) federal files.
- State and territory commissions.
- Manual CSV/XLSX uploads.
- Booth-level historical and live count files.

## Required schema (MVP)
- `live_count.csv`: `booth,candidate,votes,vote_type`
- `declaration_votes.csv`: `vote_type,envelopes_remaining`
- `booths.csv`: `booth,lat,lon,swing,formal_votes`
- `polls.csv`: `date,party,primary,sample_size,house_effect,mode`
