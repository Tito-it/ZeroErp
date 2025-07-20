# Schema `storico`

## 📚 Tabelle
- [comune_trasformazioni](tabelle/comune_trasformazioni.md)
- [comuni](tabelle/comuni.md) — * **Audit Trail**: Conservare una traccia immutabile di ogni modifica e cancellazione applicata a `config.comuni`. * **Versioning dei record**: Permettere la ricostruzione dello stato storico di ogni comune in un dato momento. * **Query storiche**: Supportare interrogazioni basate su intervalli temporali grazie ai campi `valid_from` e `valid_to`. * **Classificazione operazioni**: Utilizzare `tipo_operazione_id` e `change_type` per distinguere INSERT iniziale, UPDATE e DELETE. ---
- [indirizzi](tabelle/indirizzi.md)
- [stradario](tabelle/stradario.md) — * **Storico modifiche**   Memorizza ogni cambiamento sulle vie (aggiunta, modifica, cancellazione) registrato in `config.stradario`, garantendo la tracciabilità storica. * **Salvataggio descrizione originaria**   Include il campo `descrizione_via`, che conserva il testo della via al momento dell’operazione, in modo da mantenere la consistenza storica anche a seguito di rinominazioni. * **Controllo via flag di storicizzazione**   Il trigger si attiva solo se il flag `storicizza` nella tabella principale è impostato a **true**, permettendo all’amministratore di scegliere se registrare o meno una determinata modifica.
- [stradario_trasformazioni](tabelle/stradario_trasformazioni.md)

## ⚙️ Funzioni
