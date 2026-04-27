# Costanti codici errore per il modulo anagrafiche.
# Registrati in apps/core/services/error_policies.py.

E_ANAG_VALIDAZIONE = "E_ANAG_VALIDAZIONE"
E_ANAG_DUPLICATO = "E_ANAG_DUPLICATO"
E_ANAG_NOT_FOUND = "E_ANAG_NOT_FOUND"
E_ANAG_CONTO_NOT_FOUND = "E_ANAG_CONTO_NOT_FOUND"
E_ANAG_CONTO_SOGGETTO_NOT_FOUND = "E_ANAG_CONTO_SOGGETTO_NOT_FOUND"

# Refactor operatore-emittenti (2026-04-08, decisione Q6).
# Gli altri due codici (E_EMITTENTE_NON_MODIFICABILE,
# E_USER_EMITTENTE_DELETE_VIETATO) sono sollevati solo dai trigger DB:
# l'estrattore regex in error_translator li raccoglie dal messaggio PG
# e applica le policy in error_policies.py — niente literal Python.
E_BA_ADMIN_GLOBALE_VIETATO = "E_BA_ADMIN_GLOBALE_VIETATO"

# Fase 5 refactor anagrafiche (2026-04-28). Sollevato dal classify
# centralizzato in services/contatti_service.py quando il payload contatto
# inline ha almeno un campo valorizzato MA mancano gli obbligatori
# (nominativo e tipo_contatto_id). Sostituisce il "silent skip" che
# faceva perdere dati senza preavviso.
E_CONTATTO_INCOMPLETO = "E_CONTATTO_INCOMPLETO"
