# Cleanup Plan for eehxpe Repository

## Root Directory Files

### KEEP (Essential for Production)
- `start_production.py` - Main production server startup
- `manage_server.ps1` - Server management commands
- `README.md` - Main documentation
- `.env.production` - Production environment config
- `.env.production.example` - Template for setup
- `.gitignore` - Git configuration

### REMOVE (One-time/Development Scripts)
- `change_all_passwords.py` - One-time password reset script
- `check_db.py` - Debug/inspection tool
- `check_orphans.py` - One-time validation script
- `check_schema.py` - Debug tool
- `create_users.py` - One-time setup script
- `crop_logo.py` - One-time image processing
- `make_logo_transparent.py` - One-time image processing
- `migrate_json_to_db.py` - One-time migration script
- `recreate_db.py` - One-time setup/recovery script
- `restore_january.py` - One-time data recovery script
- `test_query.py` - Debug script
- `test_server.py` - Test script
- `test_wsgi.py` - Test script
- `dev.ps1` - Development script
- `disable-auto-restart.ps1` - One-time configuration script
- `setup-admin.ps1` - One-time setup script
- `DEV-README.md` - Development documentation
- `SETUP.md` - One-time setup guide
- `PUBLISHING.md` - Development workflow doc
- `QUICKSTART.md` - Duplicate of info in README
- `TROUBLESHOOTING.md` - Can consolidate into README if needed

## Badminton App Directory

### KEEP (Essential for Production)
- `app.py` - Main Flask application
- `auth.py` - Authentication module
- `database.py` - Database connection management
- `models.py` - Database models
- `match_storage.py` - Database-backed storage
- `player_stats.py` - Stats calculation
- `matchup_generator.py` - Matchup algorithm
- `calculate_mmr.py` - MMR calculation
- `game_valuation.py` - Game value calculation
- `mmr_calculator.py` - MMR utilities
- `requirements.txt` - Python dependencies
- `README.md` - App documentation
- `templates/` directory - HTML templates
- `static/` directory - CSS/JS/images

### REMOVE (One-time/Development/Obsolete)
- `main.py` - CLI version (not used in web app)
- `match_storage_json_backup.py` - Old JSON implementation backup
- `link_admin_to_hayden.py` - One-time setup script
- `make_hayden_admin.py` - One-time setup script
- `setup_user_accounts.py` - One-time setup script
- `test_database.py` - Test script
- `test_mmr_monthly.py` - Test script
- `list_routes.py` - Debug tool
- `generate_icons.py` - One-time icon generation
- `start_all.ps1` - Superseded by root start_production.py
- `start_server.ps1` - Superseded by root start_production.py
- `start-flask.ps1` - Old startup script
- `stop-flask.ps1` - Old management script
- `CHANGES.md` - Changelog (use git history instead)
- `DEPLOYMENT.md` - Detailed deployment guide (can consolidate)
- `FLASK_SCRIPTS.md` - Development notes
- `SESSION_IMPLEMENTATION.md` - Implementation notes
- `WARP.md` - Development notes
- `WEB_README.md` - Duplicate documentation
- `QUICKSTART.md` - Duplicate of README content

### KEEP in migrations/ (May need for future reference)
- `migrations/init_db.py` - Database initialization utility
- `migrations/migrate_json_to_db.py` - Historical migration (keep for reference)

## Summary
- Root: Keep 6 files, Remove 18 files
- Badminton app: Keep ~15 core files + templates/static, Remove ~20 files
