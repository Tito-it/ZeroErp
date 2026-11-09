## 📘 Documentazione Concettuale – Funzioni `anagrafiche.fn_id_fiscale_bloccato` e `anagrafiche.fn_soggetto_id_fiscale_bloccato`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/manual/soggetti) — la chiave d'unicità del soggetto
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le due righe del form che chiamano la regola
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile](/dbzero/anagrafiche/manual/trgfn_soggetti_guard_id_fiscale_immutabile) — il guard che rifiuta il cambio
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — valuta la regola per il form
> * [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — chi è SUPER_ADMIN

---

### 🎯 Scopo Principale

La regola **«CF e P.IVA già scritti non si cambiano»**, in un posto solo.

Le funzioni sono due, ma la regola è una:

| Funzione | Che cosa riceve | Chi la legge |
| --- | --- | --- |
| `anagrafiche.fn_id_fiscale_bloccato(valore)` | il **valore attuale** del campo | il guard, con il valore vecchio |
| `anagrafiche.fn_soggetto_id_fiscale_bloccato(soggetto, colonna)` | il **soggetto** e il nome della colonna | il form, attraverso il registro dei blocchi |

La seconda non ha una regola sua: legge il valore dalla riga e chiede alla prima.

---

### La regola: `fn_id_fiscale_bloccato(valore)`

Risponde **vero** (il campo non si cambia) quando valgono insieme due cose:

1. il valore è **scritto** (non NULL);
2. chi agisce **non è SUPER_ADMIN**.

Altrimenti risponde falso:

* un valore NULL si può **riempire**: l'identità del soggetto passa da incompleta a completa,
  non da un soggetto a un altro;
* il SUPER_ADMIN può correggere un errore di battitura.

Chi agisce è l'utente della richiesta, letto da `app.current_user_id`. Se è SUPER_ADMIN lo dice
[`script.fn_is_super_admin`](/dbzero/script/funzioni/fn_is_super_admin), la stessa regola del
backend. **Senza utente** la risposta è «non è SUPER_ADMIN»: un valore scritto resta bloccato.

Il parametro è dichiarato con il tipo di `anagrafiche.soggetti.codice_fiscale`, che si risolve
alla creazione: la firma è `fn_id_fiscale_bloccato(text)`.

---

### ⭐ Perché

CF e P.IVA sono la **chiave d'unicità del soggetto** (vincolo
`uq_soggetto_idstato_id_fiscale_univoco`, sulla colonna generata `id_fiscale_univoco_cf_piva`).
Cambiarli farebbe di un soggetto un altro.

---

### La stessa regola letta sulla riga: `fn_soggetto_id_fiscale_bloccato(soggetto, colonna)`

Il form non ha in mano il valore: ha l'id della riga. Questa funzione:

1. legge il soggetto per id;
2. prende il valore della colonna indicata (`codice_fiscale` o `partita_iva`);
3. lo passa a `fn_id_fiscale_bloccato`.

Soggetto inesistente o colonna diversa da quelle due: **falso**.

È la condizione delle due righe di
[`dbops.lock_columns_conditional`](/dbzero/dbops/tabelle/lock_columns_conditional) su
`anagrafiche.soggetti`:

```sql
anagrafiche.fn_soggetto_id_fiscale_bloccato($1::uuid, 'codice_fiscale')
anagrafiche.fn_soggetto_id_fiscale_bloccato($1::uuid, 'partita_iva')
```

[`dbops.fn_non_editable_fields`](/dbzero/dbops/funzioni/fn_non_editable_fields) le valuta e dice
al form quali campi spegnere. Poiché il guard chiede alla stessa regola, **il form spegne
esattamente ciò che il guard rifiuta**.

---

### Firme

```sql
anagrafiche.fn_id_fiscale_bloccato(p_valore text) RETURNS boolean          -- LANGUAGE sql, STABLE
anagrafiche.fn_soggetto_id_fiscale_bloccato(p_soggetto_id uuid, p_colonna text) RETURNS boolean  -- LANGUAGE sql, STABLE
```

---

### Codici errore

Nessuno: rispondono vero o falso, e non sollevano. Il rifiuto lo solleva il guard
(`E_SOGGETTO_ID_FISCALE_IMMUTABILE`).

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` — il guard rifiuta e il form
  spegne gli stessi campi: per l'operatore i campi scritti sono bloccati, per il SUPER_ADMIN no;
  un campo vuoto resta acceso e si riempie, poi è bloccato anche lui.

---

### Note di migrazione

* 2026-11-09 — nascono (`20261110-95`, `brief-db-revisione-dbops`, S-BE-3). Decisione di Tid: CF
  e P.IVA scritti non si cambiano, salvo il SUPER_ADMIN; un campo vuoto si riempie.

---

{% include-markdown "signature-core.md" %}
