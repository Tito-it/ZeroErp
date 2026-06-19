## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_giornale_assegnazione`

> 👀 **Vedi anche**
>
> [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/manual/fn_prendi_in_carico_flusso)
>
Trigger:
>
`trg_flussi_z90_giornale_assegnazione_upd` (AFTER UPDATE OF risorsa_umana_id, unita_organizzativa_id su `pratiche.flussi`)

---
### 🎯 Scopo Principale

Registra l'evento **`FLUSSO_ASSEGNAZIONE_CAMBIATA`** nel giornale a ogni cambio di assegnazione del singolo flusso (operatore e/o reparto). E' il **mirror a livello flusso** di `trgfn_pratiche_giornale_assegnazione` (che opera sulla pratica).

> **Nuovo 2026-06-18** (brief-db-assegnazione-flusso): prima il giornale tracciava solo l'assegnazione di **pratica**; il flusso non aveva traccia. La presa in carico (`fn_prendi_in_carico_flusso`, che fa `UPDATE risorsa_umana_id`) e l'assegnazione esplicita (service `assegna_flusso`) producono ora una riga di giornale.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_giornale_assegnazione()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Trigger associato

```sql
CREATE TRIGGER trg_flussi_z90_giornale_assegnazione_upd
  AFTER UPDATE OF risorsa_umana_id, unita_organizzativa_id
  ON pratiche.flussi
  FOR EACH ROW
  WHEN (
    OLD.risorsa_umana_id        IS DISTINCT FROM NEW.risorsa_umana_id
    OR OLD.unita_organizzativa_id IS DISTINCT FROM NEW.unita_organizzativa_id
  )
  EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_assegnazione();
```

La clausola `WHEN (... IS DISTINCT FROM ...)` evita righe a vuoto: il giornale viene scritto solo se almeno uno dei due campi cambia davvero.

---

### Riga di giornale prodotta

| Campo | Valore |
|---|---|
| `pratica_id` | `NEW.pratica_id` |
| `flusso_id` | `NEW.id` |
| `azione` | `'FLUSSO_ASSEGNAZIONE_CAMBIATA'` (ammessa da `chk_giornale_azione`) |
| `origine` | `'UTENTE'` |
| `dettaglio` (JSONB) | `risorsa_umana_precedente_id`, `risorsa_umana_nuova_id`, `unita_organizzativa_precedente_id`, `unita_organizzativa_nuova_id` (OLD/NEW) |
| `tx_id` | `NEW.tx_id` |

> **`origine = 'UTENTE'`** (e non `SISTEMA` come il mirror pratica): a livello flusso l'assegnazione e' compiuta dall'operatore. Quando nascera' l'assegnazione automatica (algoritmo di bilanciamento carico) si potra' distinguere con `SISTEMA`.

---

### Note operative

* La riga di giornale NON elenca `user_insert`: l'utente reale e' impostato dall'audit (GUC `app.jwt_user`, brief audit-utente-pratiche Part B) tramite il trigger audit sulla tabella `giornale`.
* Fase `z90` (finale), coerente con gli altri trigger di giornale dei flussi (`trg_flussi_z90_giornale_stato_upd`).
* Anche l'auto-presa via `fn_prendi_in_carico_flusso` produce una riga (cambia `risorsa_umana_id`).
* Test: `db/pgtap/pratiche/test-assegnazione-flusso-eligibilita.sql`.

---

{% include-markdown "signature-core.md" %}
