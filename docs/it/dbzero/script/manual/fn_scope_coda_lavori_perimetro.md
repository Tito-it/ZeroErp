## 📘 Documentazione Concettuale – Funzione `script.fn_scope_coda_lavori_perimetro(...)`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda che la regola protegge
>
> Approfondimento funzioni:
>
> * [script.fn_scope_ef_perimetro](/dbzero/script/funzioni/fn_scope_ef_perimetro) — il confronto dell'azienda col perimetro, per i lavori operatore
> * [script.fn_scope_identita_processo](/dbzero/script/funzioni/fn_scope_identita_processo) — «chi guarda è il drenatore?»
> * [script.fn_scope_email_ambito_perimetro](/dbzero/script/funzioni/fn_scope_email_ambito_perimetro) — la stessa forma per le email, con le righe di sistema
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta della coda, che fa da sé lo stesso controllo
>
> Guide:
>
> * [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)

---

### 🎯 Scopo Principale

**Chi guarda può vedere questo lavoro della coda?** È la regola della policy
`rls_coda_lavori_ef_perimetro` su `dbops.coda_lavori`, e ne è la sede unica:

| Lavoro | Chi lo vede |
| --- | --- |
| `OPERATORE` | chi ha l'azienda del lavoro nel perimetro (perimetro `NULL` = tutte, il super admin) |
| `SISTEMA` | il super admin, o l'identità tecnica viva del drenatore (`draina_coda_lavori`) |
| altro | nessuno |

Le tre cose che servono di chi guarda non dipendono dal lavoro, e la funzione **non le calcola**:
gliele passa la policy, una volta per istruzione, in tre sottoquery:

* super admin (`script.fn_is_super_admin`);
* identità del drenatore (`script.fn_scope_identita_processo` con `draina_coda_lavori`);
* perimetro emittenti (`script.fn_get_emittenti_scope_pk_ids`: `NULL` = tutte).

Per ogni lavoro resta questa funzione: pura, senza letture, e incorporata nel piano.

---

### ⛔ Il drenatore non ha un ramo per i lavori operatore

Il drenatore prende i lavori di un'azienda alla volta, con l'utente tecnico di quell'azienda: un
lavoro operatore lo vede perché la sua azienda è nel perimetro di quell'utente, come per chiunque
altro. Un ramo «il drenatore vede tutto» sarebbe una porta fra le aziende, cioè proprio ciò che la
separazione nel database deve impedire. Il ramo del drenatore vale solo per i lavori di sistema, che
un'azienda non ce l'hanno.

---

### Il risultato non è mai `NULL`

Una risposta mancante (un `NULL` dove serviva un sì o un no) vale «no»: la funzione restituisce
sempre un booleano, e un `run_as` fuori vocabolario non vede nessuno.

---

### Test

* `db/pgtap/rls/test-rls-coda-lavori-perimetro-v1.sql` — la regola sui valori (test 4) e la policy
  che la usa, armata dentro la transazione.
* `db/pgtap/script/test-policy-funzioni-cost-v1.sql` — fra le funzioni economiche misurate: non
  legge tabelle, quindi niente `COST`.
* `db/pgtap/script/test-scope-ef-perimetro-una-volta-per-istruzione-v1.sql` — chi guarda arriva in
  sottoquery, calcolato una volta per istruzione.

---

### Note di migrazione

* 2026-11-07 — nasce con la policy della coda (`brief-db-revisione-dbops`, giro 5, `20261107-52`).

---

{% include-markdown "signature-core.md" %}
