-- Migration 003: per-task Google Sheet allocation. Each market (= scrape task) can point at its
-- own spreadsheet (sheet_id) or share the default one with a highlight colour (sheet_color, hex).
alter table markets add column if not exists sheet_id text;
alter table markets add column if not exists sheet_color text;
alter table markets add column if not exists task_label text;
