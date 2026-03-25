# Area 'anagrafiche' (Backend)

## API
- [api_contatti_ruolo](manual/api_contatti_ruolo.md) — Endpoint REST per la gestione dei contatti a livello ruolo con supporto utility. Implementa la cascata a 3 livelli: utility specifica, ruolo generico, soggetto (fallback readonly).
- [api_conti_bancari_ruolo](manual/api_conti_bancari_ruolo.md) — Endpoint REST per la gestione dei conti bancari a livello ruolo con supporto utility. La lista implementa la cascata a 3 livelli: utility specifica, ruolo generico, soggetto (fallback readonly).
- [api_geo_config](manual/api_geo_config.md) — API per la gestione delle tabelle di configurazione geografica: stati, regioni, province, comuni, toponomastica e codici postali. Ogni entita` segue un pattern uniforme CRUD con lista paginata e, dove previsto, endpoint…
- [api_indirizzi](manual/api_indirizzi.md) — Gestione degli indirizzi dettaglio: ricerca paginata, creazione, consultazione, aggiornamento e verifica duplicati.
- [api_indirizzi_ruolo](manual/api_indirizzi_ruolo.md) — Endpoint REST per la gestione degli indirizzi a livello ruolo con supporto utility. Implementa la cascata a 3 livelli: utility specifica, ruolo generico, soggetto (fallback readonly).
- [api_soggetti](manual/api_soggetti.md) — Endpoint REST per la gestione completa dei soggetti anagrafici: persone fisiche (PF), persone giuridiche (PG) ed enti. Copre CRUD soggetti, contatti, indirizzi, ruoli e utility di validazione/generazione codice fiscale.
