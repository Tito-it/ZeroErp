## 📘 Documentazione Concettuale – Tabella `dbops.automazione_chiusura_scadenze`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — bersaglio: il contratto cessa alla scadenza
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — bersaglio: la versione di listino si chiude alla scadenza
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — bersaglio: il preventivo emesso scade
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove la chiusura arriva come lavoro, uno per azienda
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) — il motore che legge questa tabella e chiude
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — la sveglia che accoda la chiusura per ogni azienda
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta del modello del documento, che decide fra verbo e scrittura diretta
>
> Guide:
>
> * [Processi automatici: classe e identità](/guide/processi-automatici-classe-e-identita) — perché la chiusura gira con l'identità di un'azienda
> * [Linee guida SQL — 7c Ciclo stato + finestra di validità](/linee-guida-sql#7c-ciclo-stato-finestra-di-validita) — il modello delle tabelle che entrano qui

---

### 🎯 Scopo Principale

Il registro delle tabelle che si chiudono **per scadenza**: una riga per tabella bersaglio, con
quello che serve a portare lo stato da «attivo» a «chiuso» quando la data di fine validità è
passata. Lo legge solo `dbops.fn_apply_chiusura_scadenze`.

Aggiungere una tabella al giro non chiede codice nuovo: basta una riga nel seed, purché la tabella
segua il modello «ciclo stato + finestra di validità».

---

### Che cosa descrive una riga

Una riga dice **dove** guardare e **come** cambiare lo stato:

* la tabella, la colonna di stato e la colonna con la data di fine validità (`col_valido_al`, che
  non si chiama sempre `valido_al`: sul preventivo è `validita_al`);
* il codice dello stato «attivo» e di quello «chiuso». Sono sempre **codici**, mai id numerici:
  restano gli stessi fra sviluppo, CI e produzione;
* `tipo_stato`: `VARCHAR` se la colonna contiene direttamente il codice, `FK` se punta a un
  vocabolario. Con `FK` le quattro colonne `fk_lookup_*` dicono in quale tabella e su quali colonne
  il codice si traduce nell'id da scrivere; con `VARCHAR` restano vuote. Il vincolo
  `chk_automazione_chiusura_scadenze_fk_coerente` tiene insieme le due cose;
* `verbo_chiusura`: per una testata sotto la porta del modello del documento, la funzione che la
  chiude (vedi sotto);
* `attivo`: una riga spenta resta in tabella ma non entra nel giro.

La chiave naturale è la coppia schema e tabella: una tabella ha **una** riga, non due regole che
potrebbero contraddirsi.

---

### ⭐ Una testata sotto la porta si chiude col suo verbo

Le testate che seguono il modello del documento (oggi contratto, versione di listino e preventivo)
hanno lo stato protetto dalla porta `script.trgfn_doc_stato_solo_dal_verbo`: lo stato lo scrive
solo un verbo, e una scrittura diretta della colonna è rifiutata. Per loro il framework non scrive
lo stato: chiama il verbo dichiarato in `verbo_chiusura`, una funzione senza argomenti, qualificata
con lo schema, che chiude le righe scadute e dice quante sono.

Il vincolo `chk_automazione_chiusura_scadenze_verbo_qualificato` pretende la forma
`schema.funzione`; che la funzione esista e non abbia argomenti lo controlla il framework al
momento di usarla.

Porta e verbo si guardano **prima** di scegliere come scrivere lo stato, con qualunque
`tipo_stato` (`VARCHAR` o `FK`):

| La riga | Che cosa fa il framework |
| --- | --- |
| dichiara un verbo | lo chiama, sempre: lo stato lo scrive il verbo, e il conteggio è il suo |
| non dichiara un verbo, e la tabella è sotto la porta | rifiuta la riga: è una configurazione non valida, perché la scrittura diretta sarebbe respinta |
| non dichiara un verbo, e la tabella non ha la porta | scrive lo stato direttamente |

Oggi tutte e tre le righe del seed sono testate sotto la porta, con il loro verbo:
`vendite.fn_cessa_contratti_scaduti`, `vendite.fn_chiudi_versioni_listino_scadute` e
`vendite.fn_chiudi_preventivi_scaduti`.

---

### ⭐ La classe sta sul bersaglio, non sul job

`classe` dice la natura della **tabella** che si chiude. Sta qui e non sul processo perché la
natura del giro è quella dei suoi bersagli: una classe sul job avrebbe costretto a dichiarare di
dominio un lavoro che tocca anche dati di nessuno, o di manutenzione uno che tocca contratti.

⛔ **Il registro ammette solo `DOMINIO`** (`chk_automazione_chiusura_scadenze_classe`). Il giro
gira dentro la coda, un lavoro per azienda con l'identità e la row level security di quell'azienda:
è l'esecutore giusto per righe che hanno un padrone, e solo per quelle. Un bersaglio di un'altra
natura (`MANUTENZIONE`, `AMMINISTRAZIONE`) chiede un esecutore che lavori una volta sola con
un'identità tecnica, e quell'esecutore non c'è: finché non lo si sviluppa, il CHECK respinge la
riga e il motore la rifiuterebbe (`E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`, motivo
`classe_senza_esecutore`).

⛔ **Il `NOT NULL` è il cancello**: una riga nuova deve dichiarare di chi sono le righe che tocca.
Senza, arruolerebbe un'altra tabella nel giro senza dirlo, che è il difetto per cui la colonna
esiste.

I bersagli portano l'emittente: il contratto e il preventivo con una colonna propria, la
versione di listino attraverso il listino. La row level security fa il perimetro.

---

### Chi la scrive

È configurazione: la scrive solo il seed (`80_data/sql/dbops/automazione_chiusura_scadenze.csv`),
mai un utente. Per sospendere la chiusura di una tabella si spegne la sua riga (`attivo`), e il
giro successivo la salta.

---

### Test

* `db/pgtap/dbops/test-fn-apply-chiusura-scadenze-v1.sql` — il giro col verbo su versione di
  listino e contratto, l'idempotenza, i rifiuti di una riga che punta a una tabella, una colonna o
  un codice inesistente, una testata sotto la porta senza verbo o con un verbo che non esiste.
* `db/pgtap/dbops/test-chiusura-scadenze-classe.sql` — la colonna `classe`, il CHECK che ammette
  solo `DOMINIO`, il `NOT NULL` come cancello, i bersagli del seed tutti `DOMINIO`, il motore senza
  argomenti e il suo rifiuto di un bersaglio di altra classe; il verbo usato anche con
  `tipo_stato = VARCHAR`, e una testata `VARCHAR` sotto la porta senza verbo rifiutata.
* `db/pgtap/dbops/test-chiusura-scadenze-audit-v1.sql` — un giro scrive la sua riga di audit.
* `db/pgtap/vendite/test-listino-versione-al-modello-v1.sql` e
  `db/pgtap/vendite/test-preventivo-scadenza-v1.sql` — la riga del seed della versione di listino e
  del preventivo, e la chiusura attraverso il loro verbo.

---

### Note di migrazione

* 2026-04-26 — nasce come promozione a `dbops` della chiusura per scadenza già scritta per la
  versione di listino e per il contratto.
* 2026-09-04 — nasce `classe`, `NOT NULL` dalla stessa data
  (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-05 — la chiusura passa da pgAgent alla coda: pgAgent sveglia, il lavoro lo fa il
  drenatore, un'azienda alla volta.
* 2026-10-28 — nasce `verbo_chiusura`; la versione di listino passa a stato in vocabolario
  (`tipo_stato = FK`) e sotto la porta (`brief-modello-documento-vendita`).
* 2026-10-31 — entra il preventivo (`brief-db-scadenza-preventivi`).
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.
* 2026-11-08 — `classe` ammette solo `DOMINIO` (prima anche `MANUTENZIONE` e `AMMINISTRAZIONE`,
  che il motore avrebbe lavorato con l'identità di ogni azienda); porta e verbo valgono per ogni
  `tipo_stato` (prima il verbo si leggeva solo con `FK` sotto la porta).

---

{% include-markdown "signature-core.md" %}
