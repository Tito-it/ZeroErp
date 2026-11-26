## 📘 Documentazione Concettuale – Funzione `script.fn_guard_livello_area`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) — le aree, una per schema
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) — l'eccezione utente sull'area
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) — la regola che applica, la stessa del backend
> * [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello) — la gemella, sull'oggetto con la ricaduta sull'area
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il guard dell'azione di processo
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — chiamante: `TUTTO` sull'area `pagamenti`
> * [vendite.fn_guard_passaggio_lotto](/dbzero/vendite/funzioni/fn_guard_passaggio_lotto) — chiamante: il passaggio del lotto senza azione, `TUTTO` sull'area `vendite`
>
> Guide:
>
> * [Architettura permessi](/guide/architettura-permessi-e-autorizzazioni) §7.4 — il permesso nel verbo di scrittura

---

### 🎯 Scopo Principale

È il guard con cui un verbo di scrittura chiede che **chi agisce abbia almeno un certo livello su
un'area funzionale**, senza un oggetto. Si chiama nella prima riga del verbo: se il livello non
basta, il verbo si ferma prima di toccare qualunque cosa.

---

### Quando si usa, e quando no

Serve ai verbi dietro un endpoint che decide **sull'area**, perché la sua view non dichiara un
oggetto. Il verbo chiede a DB la stessa cosa, così chi arriva dall'interfaccia non riceve un rifiuto
nuovo.

Se il verbo scrive su un oggetto si usa la gemella,
[`script.fn_guard_livello`](/dbzero/script/funzioni/fn_guard_livello): decide sull'oggetto, e ricade
sull'area solo se l'oggetto non ha un livello suo. ⚠️ Le due non sono intercambiabili: con
`fn_guard_livello` un'eccezione dell'utente sull'oggetto deciderebbe al posto dell'area, cioè il
database direbbe una cosa diversa dall'endpoint.

Le operazioni di processo chiedono invece un'azione, con
[`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione).

---

### Cosa risponde

La regola la decide [`script.fn_resolve_livello_area`](/dbzero/script/funzioni/fn_resolve_livello_area),
la stessa del backend: il contesto da cui entra chi agisce, il SUPER_ADMIN, l'eccezione dell'utente,
il profilo.

| Situazione | Esito |
| --- | --- |
| il livello di chi agisce arriva al minimo | niente: il verbo prosegue |
| il livello è sotto il minimo | `E_PERMESSO_NEGATO`, lo stesso codice del backend |
| nessun utente in sessione, area o minimo mancanti | `E_PERMESSO_NEGATO` (nel dubbio, no) |

Il rifiuto ha la stessa forma di quello di `fn_guard_livello`: stesso codice, nessun segnaposto nel
messaggio, e nel contesto l'area, il livello trovato e il minimo chiesto.

⚠️ **I livelli sono ordinati al contrario di come si leggono**: nel database `TUTTO` viene prima di
`LETTURA`, che viene prima di `BLOCCATO`. «Arrivare al minimo» vuol dire avere un livello **uguale
o precedente**.

`SECURITY INVOKER` come la gemella: non legge niente da proprietario.

---

### Chi la chiama

* [`pagamenti.fn_annulla_sistemazione`](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) —
  `TUTTO` sull'area `pagamenti`, il controllo dell'endpoint di annullo.
* [`vendite.fn_guard_passaggio_lotto`](/dbzero/vendite/funzioni/fn_guard_passaggio_lotto), per
  l'annullo e il ritorno in bozza del lotto — `TUTTO` sull'area `vendite`, quando la riga del
  passaggio non ha azione.

---

### Codici errore

* `E_PERMESSO_NEGATO` — livello sotto il minimo, oppure utente, area o minimo mancanti.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — l'annullo del lotto con l'area
  `vendite` a `LETTURA` e l'annullo della sistemazione con l'area `pagamenti` a `LETTURA` rifiutano
  con `E_PERMESSO_NEGATO`.

Nei test il livello d'area si concede con
[`dbops.fn_pgtap_concedi_livello_area`](/dbzero/dbops/funzioni/fn_pgtap_concedi_livello_area).

---

### Note di migrazione

* 2026-11-25 — nasce con l'annullo della sistemazione e i verbi del reset del lotto, che diventano
  `SECURITY DEFINER` e chiedono il livello d'area dell'endpoint (brief-db-porte-aperte-dalla-sola-guc,
  giro 8 + 1-7, D-U a).

---

{% include-markdown "signature-core.md" %}
