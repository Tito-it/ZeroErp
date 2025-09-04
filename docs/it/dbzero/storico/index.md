# Schema `storico`

## 📚 Tabelle
- [articoli](tabelle/articoli.md)
- [articoli_componenti](tabelle/articoli_componenti.md)
- [attivita_fatturabili](tabelle/attivita_fatturabili.md)
- [billing_account](tabelle/billing_account.md)
- [clienti](tabelle/clienti.md)
- [comune_trasformazioni](tabelle/comune_trasformazioni.md)
- [comuni](tabelle/comuni.md) — * **Audit Trail**: Conservare una traccia immutabile di ogni modifica e cancellazione applicata a `config.comuni`. * **Versioning dei record**: Permettere la ricostruzione dello stato storico di ogni comune in un dato momento. * **Query storiche**: Supportare interrogazioni basate su intervalli temporali grazie ai campi `valid_from` e `valid_to`. * **Classificazione operazioni**: Utilizzare `tipo_operazione_id` e `change_type` per distinguere INSERT iniziale, UPDATE e DELETE. ---
- [conti_bancari](tabelle/conti_bancari.md)
- [dati_catastali](tabelle/dati_catastali.md)
- [dati_societari](tabelle/dati_societari.md) — * **Versionamento completo**   Acquisire snapshot di ogni record di `anagrafiche.dati_societari` per garantire la tracciabilità delle evoluzioni nel tempo. * **Audit e compliance**   Conservare informazioni su chi (`user_insert`) e quando (`data_insert`) è stata eseguita l’operazione, nonché su quale transazione di business (`tx_id`). * **Intervalli di validità**   Definire periodi di efficacia di ciascuno snapshot con `valid_from` (inclusivo) e `valid_to` (esclusivo), facilitando interrogazioni temporali.
- [emittenti_fiscali](tabelle/emittenti_fiscali.md)
- [fatture](tabelle/fatture.md)
- [fornitori](tabelle/fornitori.md)
- [indirizzi](tabelle/indirizzi.md) — * **Versionamento degli indirizzi**     Ogni operazione su `anagrafiche.indirizzi` (INSERT, UPDATE, DELETE) genera un record nello storico che ne conserva lo stato precedente o iniziale.
- [indirizzi_dettaglio](tabelle/indirizzi_dettaglio.md) — * **Audit Trail**: tracciare ogni modifica ai dettagli degli indirizzi consentendo la ricostruzione dello stato storico. * **Versioning temporale**: supportare query basate su periodi di validità tramite `valid_from` e `valid_to`. * **Schema futuro‑proof**: salvare l’intero stato del record in JSONB senza richiedere aggiornamenti di schema a ogni nuova colonna.
- [istanze_dati_precontrattuali](tabelle/istanze_dati_precontrattuali.md)
- [parameter_overrides](tabelle/parameter_overrides.md) — * **Versionamento degli override**   Catturare ogni modifica ai record di `config.parameter_overrides`, consentendo di risalire allo stato precedente o iniziale di un override. * **Audit e compliance**   Archivio immutabile di tutte le operazioni, con metadati di utente e timestamp, per garantire tracciabilità e analisi storiche.
- [parameters](tabelle/parameters.md) — * **Versionamento dei parametri**   Registrare ogni modifica (INSERT, UPDATE, DELETE) sui parametri definiti in `config.parameters`, abilitando rollback e analisi storica. * **Audit e compliance**   Documentare chi (`user_insert`) e quando (`data_insert`) hanno effettuato le modifiche, mantenendo un registro immutabile.
- [pdp](tabelle/pdp.md) — `storico.pdp` conserva la **timeline** dei Punti di Prelievo: per ogni modifica allo stato corrente (`anagrafiche.pdp`) registra uno **snapshot JSONB**, la **tipologia di operazione** (`I`,`U`,`D`), il **tx_id** e la **finestra di validità** (`valid_from`, `valid_to`). È di fatto una **SCD Type 2** (Slowly Changing Dimension) specializzata per i PDP.
- [registri_fatturazione](tabelle/registri_fatturazione.md)
- [regole_fatturazione_articolo](tabelle/regole_fatturazione_articolo.md)
- [resellers](tabelle/resellers.md)
- [soggetti](tabelle/soggetti.md) — * **Versionamento dei soggetti**   Ogni modifica (INSERT, UPDATE, DELETE) su `anagrafiche.soggetti` genera un record in storico con lo stato precedente, il tipo di operazione e i metadati di audit.
- [soggetti_conti_bancari](tabelle/soggetti_conti_bancari.md)
- [soggetti_ruoli_conti_bancari](tabelle/soggetti_ruoli_conti_bancari.md)
- [sto_demo_storico](tabelle/sto_demo_storico.md)
- [stradario](tabelle/stradario.md) — * **Audit Trail**: Conservare una traccia completa di ogni modifica o cancellazione effettuata su `config.stradario`. * **Versioning dei record**: Permettere la ricostruzione dello stato di una via in un dato momento, grazie ai campi `valid_from` e `valid_to`. * **Riproduzione dello schema**: Utilizzare il campo **`snapshot`** (JSONB) per salvare tutti i dettagli di `config.stradario` al momento dell’operazione, anche a fronte di evoluzioni dello schema. * **Classificazione delle operazioni**: Impiegare **`tipo_operazione_id`** (1=insert iniziale, 2=update, 3=delete) e **`change_type`** (A=Active, S=Suppressed, F=Fused, D=Divided) per distinguere rapidamente la natura del cambiamento.
- [stradario_trasformazioni](tabelle/stradario_trasformazioni.md)
- [vettori](tabelle/vettori.md)

## ⚙️ Funzioni

## 🔍 Views
