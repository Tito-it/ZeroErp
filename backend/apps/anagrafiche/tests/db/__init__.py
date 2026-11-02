# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del dominio anagrafiche che interrogano il DATABASE VERO — il
#        livello che i test unitari col cursore mockato non possono raggiungere.
# Note: girano solo con `ZEROERP_TEST_DB_E2E=1` e uno schema Liquibase completo;
#       altrimenti `richiedi_db_provvisto` li SALTA dichiarando il motivo,
#       invece di passare senza aver guardato niente.
# ------------------------------------------------------------
