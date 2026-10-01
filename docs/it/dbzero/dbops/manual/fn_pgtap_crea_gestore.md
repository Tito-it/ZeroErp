## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_gestore`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_filiale_bancaria](/dbzero/dbops/funzioni/fn_pgtap_crea_filiale_bancaria) — la filiale su cui i conti del gestore si agganciano
>
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg), [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — i due builder che compone
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-che-costruiscono-giro-2` (§11)

---
### 🎯 Scopo Principale

(rev 2026-09-23 — D7, lotto 2)

**Il gestore dell'installazione**: il soggetto della società che usa l'ERP, il suo ruolo GE
con gli indirizzi che quel ruolo pretende, e la riga in `anagrafiche.gestori`.

```sql
CREATE TEMP TABLE tmp_gestore AS
SELECT * FROM dbops.fn_pgtap_crea_gestore('conto gestore');
```

---
### 🧭 Prendi-o-costruisci, e non è pigrizia

`anagrafiche.gestori` è **dato di macchina**: su un database ricostruito è vuota, e
«il primo Gestore» non esiste — quattro file di `anagrafiche/` lo leggevano così.

⚠️ Ma il gestore è un **singleton**: un secondo viene rifiutato da un guard («Esiste già
un record di gestore»). Quindi la funzione **prende quello che c'è** e costruisce solo se
non ce n'è: sulla macchina di sviluppo non scrive niente, in CI costruisce. Un builder che
creasse sempre sarebbe rosso proprio dove oggi il test è verde.

⚠️ Nota al margine, per chi cerca il vincolo: quello che porta il nome del singleton —
`uq_gestori_singleton` — vieta due righe con lo **stesso id**, cioè ripete la chiave
primaria e non impedisce un secondo gestore. A impedirlo è il guard. Il nome promette
qualcosa che la definizione non fa.

---
### 🚫 Cosa NON scrive

I **conti bancari** del gestore: uso, IBAN e predefinito sono il caso del test, e i quattro
file che lo usano ne vogliono uno diverso ciascuno.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper. Quando costruisce, apre la
finestra differita da sé: il ruolo GE ha indirizzi obbligatori con un controllo che scatta
solo a fine transazione.
