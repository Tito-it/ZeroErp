# Schema `storico`

## 📚 Tabelle
- [comune_trasformazioni](tabelle/comune_trasformazioni.md)
- [comuni](tabelle/comuni.md) — * **Audit Trail**: Conservare una traccia immutabile di ogni modifica e cancellazione applicata a `config.comuni`. * **Versioning dei record**: Permettere la ricostruzione dello stato storico di ogni comune in un dato momento. * **Query storiche**: Supportare interrogazioni basate su intervalli temporali grazie ai campi `valid_from` e `valid_to`. * **Classificazione operazioni**: Utilizzare `tipo_operazione_id` e `change_type` per distinguere INSERT iniziale, UPDATE e DELETE. ---
- [indirizzi](tabelle/indirizzi.md) — * **Versionamento degli indirizzi**     Ogni operazione su `anagrafiche.indirizzi` (INSERT, UPDATE, DELETE) genera un record nello storico che ne conserva lo stato precedente o iniziale.
- [indirizzi_dettaglio](tabelle/indirizzi_dettaglio.md) — * **Audit Trail**: tracciare ogni modifica ai dettagli degli indirizzi consentendo la ricostruzione dello stato storico. * **Versioning temporale**: supportare query basate su periodi di validità tramite `valid_from` e `valid_to`. * **Schema futuro‑proof**: salvare l’intero stato del record in JSONB senza richiedere aggiornamenti di schema a ogni nuova colonna.
- [stradario](tabelle/stradario.md) — * **Audit Trail**: Conservare una traccia completa di ogni modifica o cancellazione effettuata su `config.stradario`. * **Versioning dei record**: Permettere la ricostruzione dello stato di una via in un dato momento, grazie ai campi `valid_from` e `valid_to`. * **Riproduzione dello schema**: Utilizzare il campo **`snapshot`** (JSONB) per salvare tutti i dettagli di `config.stradario` al momento dell’operazione, anche a fronte di evoluzioni dello schema. * **Classificazione delle operazioni**: Impiegare **`tipo_operazione_id`** (1=insert iniziale, 2=update, 3=delete) e **`change_type`** (A=Active, S=Suppressed, F=Fused, D=Divided) per distinguere rapidamente la natura del cambiamento.
- [stradario_trasformazioni](tabelle/stradario_trasformazioni.md)

## ⚙️ Funzioni

## 🔍 Views
