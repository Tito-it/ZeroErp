## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_filiale_bancaria`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg), [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — i due builder che questa funzione compone
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-che-costruiscono-giro-2` (§10)

---
### 🎯 Scopo Principale

(rev 2026-09-23 — D7, lotto 1)

**Una filiale bancaria costruita**: il soggetto della banca, il suo ruolo BANK_B con gli
indirizzi che quel ruolo pretende, e la filiale. Serve a chi deve agganciare un conto.

```sql
CREATE TEMP TABLE tmp_banca AS
SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('enti incasso');
```

---
### 🧭 Perché esiste

`anagrafiche.bank_branches` è **dato di macchina**, non un catalogo distribuito: su un
database ricostruito è vuota. Tre file di `pagamenti` la pescavano e in CI morivano tutti
sullo stesso errore — «bank_branch_id non può essere nullo» — che parla della colonna e
non della filiale che manca.

⚠️ E la catena ha la sua trappola: è una **saga**, e i controlli del ruolo bancario sono
di quelli che scattano solo a fine transazione. Il preambolo dei test li rende immediati,
quindi la finestra va riaperta e richiusa — ed è proprio ciò che un builder toglie dalle
spalle di chi scrive il file.

---
### 🚫 Cosa NON scrive

Il **conto bancario** e il suo legame col titolare: IBAN e intestatario sono il caso del
test, e i tre file ne scrivono ognuno uno diverso.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper.
