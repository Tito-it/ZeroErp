## 📘 Documentazione Funzione – `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
**Tabelle anagrafiche / dbops:**
>
[`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti)
> [`dbops.lock_columns_conditional`](/dbzero/dbops/tabelle/lock_columns_conditional) — le due righe che spengono CF e P.IVA nel form
>
**Funzioni / trigger correlati:**
>
[`anagrafiche.fn_id_fiscale_bloccato`](/dbzero/anagrafiche/manual/fn_id_fiscale_bloccato) — la regola, scritta in un posto solo
> [`anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cf_piva_obbligatori) — controlla la **presenza** di CF/P.IVA
> [`anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — valida il **formato** di CF/P.IVA
> [`dbops.fn_non_editable_fields`](/dbzero/dbops/funzioni/fn_non_editable_fields) — dice al form quali campi spegnere
> [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

La funzione **`anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`** è una **trigger
function di tipo "guard"** su [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti).

Fa valere una regola sola: **un codice fiscale o una partita IVA già scritti non si cambiano e
non si svuotano.** Solo il SUPER_ADMIN può correggerli.

| Situazione | Esito |
| --- | --- |
| il campo è scritto e si mette un valore diverso | **rifiutato** |
| il campo è scritto e lo si svuota | **rifiutato** |
| il campo è scritto e si riscrive lo stesso valore | passa: non è un cambio |
| il campo è vuoto e lo si riempie | passa |
| chi agisce è SUPER_ADMIN | passa sempre |

Dopo che un campo vuoto è stato riempito, da lì in poi è bloccato anche lui.

---

### ⭐ Perché

CF e P.IVA sono la **chiave d'unicità del soggetto**: il vincolo
`uq_soggetto_idstato_id_fiscale_univoco` sta sulla colonna generata
`id_fiscale_univoco_cf_piva`, che nasce da questi due campi. Cambiarli farebbe di un soggetto
**un altro soggetto**.

Riempire un campo vuoto invece non cambia il soggetto: la sua identità passa da incompleta a
completa. Per questo si può.

Un errore di battitura resta possibile: lo corregge il SUPER_ADMIN.

Prima la regola esisteva **solo nel form**: una modifica diretta cambiava un CF valorizzato senza
errori. Ora la fa valere il database.

---

### Tre guard, tre domande

| Funzione | Che cosa controlla |
| --- | --- |
| `trgfn_soggetti_valida_cf_piva_dispatch` | il **formato** |
| `trgfn_soggetti_guard_cf_piva_obbligatori` | la **presenza**, quando la natura del soggetto la richiede |
| `trgfn_soggetti_guard_id_fiscale_immutabile` | il **cambio** di un valore già scritto |

Chi svuota un CF o una P.IVA obbligatori era già fermato dal guard di presenza
(`E_CF_OBBLIGATORIO` / `E_PIVA_OBBLIGATORIA`). Questo guard ferma anche lo svuotamento del dato
facoltativo.

---

### 🧾 Firma della funzione e trigger associato

**Funzione (schema `anagrafiche`):**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile()
RETURNS trigger
LANGUAGE plpgsql;
```

**Trigger su `anagrafiche.soggetti`:**

```sql
CREATE TRIGGER trg_soggetti_a10_guard_id_fiscale_immutabile_upd
    BEFORE UPDATE OF codice_fiscale, partita_iva
    ON anagrafiche.soggetti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile();
```

📌 *Il trigger scatta solo in UPDATE, quando la scrittura nomina `codice_fiscale` o
`partita_iva`.* All'INSERT non c'è niente da proteggere: il valore nasce lì.

---

### Logica di funzionamento

Per ciascuno dei due campi, in ordine (prima il CF, poi la P.IVA):

1️⃣ Il valore nuovo è diverso da quello vecchio? (`IS DISTINCT FROM`: anche lo svuotamento è
un cambio.) Se no, il campo passa.

2️⃣ La regola [`anagrafiche.fn_id_fiscale_bloccato`](/dbzero/anagrafiche/manual/fn_id_fiscale_bloccato),
letta sul **valore vecchio**, dice che il campo è bloccato? Se sì, rifiuto.

La regola non è ricopiata qui: il guard la chiede alla funzione, e la stessa funzione decide che
cosa il form spegne. Form e database non possono dire due cose diverse.

Il confronto è sul valore scritto: il database non normalizza i due campi
(`trgfn_soggetti_normalize` non li tocca).

---

### Il form spegne ciò che il guard rifiuta

In `dbops.lock_columns_conditional` ci sono due righe per `anagrafiche.soggetti`, una per
`codice_fiscale` e una per `partita_iva`. La loro condizione è
`anagrafiche.fn_soggetto_id_fiscale_bloccato($1::uuid, '<colonna>')`, cioè la stessa regola
letta sulla riga. `dbops.fn_non_editable_fields` la valuta e dice al form quali campi spegnere.

* all'operatore il form spegne i campi già scritti, e lascia acceso un campo vuoto;
* al SUPER_ADMIN li lascia accesi.

⚠️ Il registro da solo non blocca niente: serve al form. A bloccare è questo guard.

---

### Errore

`E_SOGGETTO_ID_FISCALE_IMMUTABILE`, classe `CONFLITTO_STATO`:

> *«Il dato fiscale (%s) è già scritto: non si cambia e non si cancella. Solo un amministratore
> del software può correggerlo.»*

Il segnaposto è il nome del dato (`codice fiscale` o `partita IVA`). Il contesto porta
`campo` = la colonna (`codice_fiscale` o `partita_iva`), così il form sa quale campo segnare, e
l'id del soggetto.

---

### Test

`db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` (11 test):

* il guard è montato: `BEFORE UPDATE OF codice_fiscale, partita_iva`;
* l'operatore che cambia un CF scritto, o una P.IVA scritta, o svuota la P.IVA: rifiuto, con il
  campo giusto;
* riscrivere lo stesso valore passa;
* il form dell'operatore spegne CF e P.IVA; quello del SUPER_ADMIN li lascia accesi;
* il SUPER_ADMIN corregge CF e P.IVA;
* il form spegne solo il campo scritto: un campo vuoto resta acceso;
* un campo vuoto si riempie, anche dall'operatore, e da lì in poi è bloccato anche lui.

---

### Note di migrazione

* 2026-11-09 — nasce (`20261110-96`, con la regola in `20261110-95` e le righe del form in
  `20261110-97`; `brief-db-revisione-dbops`, S-BE-3). Decisione di Tid: CF e P.IVA scritti non
  si cambiano, salvo il SUPER_ADMIN. Prima la regola viveva solo nel form.

---

{% include-markdown "signature-core.md" %}
