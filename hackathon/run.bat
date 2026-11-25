@echo off
REM
cd /d %~dp0
docker compose --profile pc up -d
docker exec -it r_hacatonius bash
