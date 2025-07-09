# Schema `storico`

## 📚 Tabelle
- [comune_trasformazioni](tabelle/comune_trasformazioni.md)
- [comuni](tabelle/comuni.md) — * **Archiviazione storica**   Riproduce lo schema di `config.comuni` per mantenere la storia completa di ogni record quando il flag `storicizza` è impostato a **true**. * **Allineamento con modifiche di struttura**   Ogni volta che in `config.comuni` viene aggiunta una colonna (es. `provincia_id` nel changelog Liquibase), la stessa modifica viene replicata in `storico.comuni`, assicurando che le due tabelle rimangano coerenti. * **Trigger automatico**   La funzione trigger `trgfn_comuni_upd_dlt_storico_comuni` si attiva su operazioni di update o delete in `config.comuni`, trasferendo i dati aggiornati nel record storico. * **Storicizzazione**   Il campo `storicizza` se true attiva il trigger per la storicizzazione delle informazioni sulla tabella `storico.comuni`. Il front-end dovrà sempre impostare a true il valore, solo per funzioni administrator si potrà non gestire a true.
- [indirizzi](tabelle/indirizzi.md)
- [stradario](tabelle/stradario.md) — * **Storico modifiche**   Memorizza ogni cambiamento sulle vie (aggiunta, modifica, cancellazione) registrato in `config.stradario`, garantendo la tracciabilità storica. * **Salvataggio descrizione originaria**   Include il campo `descrizione_via`, che conserva il testo della via al momento dell’operazione, in modo da mantenere la consistenza storica anche a seguito di rinominazioni. * **Controllo via flag di storicizzazione**   Il trigger si attiva solo se il flag `storicizza` nella tabella principale è impostato a **true**, permettendo all’amministratore di scegliere se registrare o meno una determinata modifica.
- [stradario_trasformazioni](tabelle/stradario_trasformazioni.md)

## ⚙️ Funzioni
