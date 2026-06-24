# Assessment Content Files

This directory holds the downloadable assessment files served to candidates after
their content window unlocks.

## Files

| file_key | filename | label | category | media_type |
|---|---|---|---|---|
| `exercise_brief` | `exercise_brief.pdf` | Exercise Brief | brief | application/pdf |
| `turbine_data` | `turbine_data.csv` | Turbine Data | data | text/csv |
| `weather_limits` | `weather_limits.csv` | Weather Limits | data | text/csv |
| `wind_data_20yr` | `wind_data_20yr.xlsx` | 20-Year Wind Data | data | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| `terminology` | `terminology.pdf` | Terminology Reference | reference | application/pdf |
| `build_process` | `build_process.pdf` | Build Process Guide | reference | application/pdf |

## Admin instructions

The files above are **placeholder stubs** committed for development purposes.
Replace each file with the real content before deploying to candidates:

1. Drop the real files into this directory, keeping the exact filenames listed
   in the table above.
2. Filenames are hard-coded in `backend/app/content_manifest.py` — do **not**
   rename files without also updating the manifest.
3. The `.gitignore` for this project excludes data files from version control
   (only `.gitkeep` and `MANIFEST*` are tracked).  Store real files in a
   secure location (e.g., an encrypted S3 bucket or a secrets manager) and
   deploy them to the server separately from the codebase.
