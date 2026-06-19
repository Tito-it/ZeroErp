## 📘 Documentazione Funzione – `pratiche.fn_prendi_in_carico_flusso`

> 👀 **Vedi anche**
>
> [pratiche.competenze_flussi](/dbzero/pratiche/manual/competenze_flussi)
> [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/manual/fn_coda_lavoro_operatore)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale

Assegna un flusso DA_ESEGUIRE all'operatore corrente applicando la **policy di eligibilita' reparto-first + competenza opzionale** (vedi sotto). Operazione atomica con lock pessimistico (`FOR UPDATE`) per evitare race condition.

> **Rev 2026-06-18** (brief-db-assegnazione-flusso): la competenza passa da **obbligatoria** a **condizionale**. Prima ogni flusso template-based richiedeva competenza; ora la competenza e' un lucchetto **opzionale** che governa solo dove la matrice e' configurata; altrove governa l'appartenenza al reparto o la presa libera.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_prendi_in_carico_flusso(
    p_flusso_id        pratiche.flussi.id%TYPE,
    p_risorsa_umana_id anagrafiche.risorse_umane.id%TYPE
)
RETURNS BOOLEAN
LANGUAGE plpgsql
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_flusso_id` | bigint | SI | ID del flusso da prendere in carico |
| `p_risorsa_umana_id` | bigint | SI | ID dell'operatore che prende in carico |

---

### Valore di ritorno

| Valore | Significato |
|--------|-------------|
| `TRUE` | Flusso assegnato con successo |
| `FALSE` | Flusso gia' assegnato allo stesso operatore (noop) |
| RAISE | Errore se il flusso non esiste, stato errato, gia' assegnato ad altro, o **non eligibile** per la policy (competenza o reparto) |

---

### Regole di validazione (ordine di esecuzione)

| # | Guard | Errore |
|---|-------|--------|
| 1 | Parametri obbligatori (NOT NULL, > 0) | `E_PARAMETRO_INVALIDO` |
| 2 | Il flusso deve esistere | `E_VALORE_MANCANTE` |
| 3 | Il flusso deve essere in stato DA_ESEGUIRE | `FLUSSI_PRESA_CARICO_STATO_ERRATO` (320) |
| 4 | Se gia' assegnato allo stesso operatore | Return `FALSE` (noop) |
| 5 | Se gia' assegnato ad altro operatore | `FLUSSI_GIA_ASSEGNATO` (321) |
| 6 | **Eligibilita'** (policy reparto-first, vedi sotto) | `FLUSSI_COMPETENZA_MANCANTE` (322) **oppure** `FLUSSI_PRESA_NON_ELIGIBILE` (496) |

---

### Policy di eligibilita' (reparto-first + competenza opzionale)

Per un flusso `F` (DA_ESEGUIRE, non assegnato) e un operatore `O` si definiscono:

* **skill-lock** = esiste almeno una competenza **attiva** (`competenze_flussi`) per `F.template_flusso_id` → la matrice e' configurata per quel tipo di step;
* **competente** = esiste competenza **attiva** `(template = F.template, operatore = O)`;
* **nel-reparto** = `F.unita_organizzativa_id IS NOT NULL` **e** coincide col reparto **anagrafico** dell'operatore (`anagrafiche.risorse_umane.unita_organizzativa_id`).

| Caso | Condizione su F | Eligibile se | Errore se non eligibile |
|---|---|---|---|
| **A — reparto + skill** | reparto valorizzato, skill-lock presente | `competente` | `FLUSSI_COMPETENZA_MANCANTE` |
| **B — reparto, no skill** | reparto valorizzato, skill-lock assente | `nel-reparto` | `FLUSSI_PRESA_NON_ELIGIBILE` |
| **C — niente configurato** | reparto NULL, skill-lock assente | **libero** (chiunque) | — |
| **D — skill senza reparto** | reparto NULL, skill-lock presente | `competente` | `FLUSSI_COMPETENZA_MANCANTE` |

In pratica: la competenza e' un lucchetto **opzionale**; quando per il template non esiste competenza, governa l'appartenenza al reparto (o la presa libera se nemmeno il reparto e' impostato).

> **skill-lock = competenza ATTIVA** (non "qualsiasi riga"): se tutte le competenze del template sono disattivate, lo step **non** e' skill-gated → evita flussi bloccati e non prendibili da nessuno. Coerente con `fn_coda_lavoro_operatore`.

---

### Gestione concorrenza

La funzione usa `SELECT ... FOR UPDATE` sulla riga del flusso per evitare race condition:
se due operatori provano a prendere in carico lo stesso flusso contemporaneamente,
il secondo attende il rilascio del lock e poi fallira' con `FLUSSI_GIA_ASSEGNATO`.

---

### Esempi di utilizzo

```sql
-- Operatore 42 prende in carico flusso 100
SELECT pratiche.fn_prendi_in_carico_flusso(100, 42);
-- Ritorna TRUE se assegnato, FALSE se gia' suo

-- Da invocare dal service Python, non direttamente dalla UI
```

---

### Note operative

* Da invocare sempre tramite il service Python (`pratiche_service`), che gestisce l'envelope di errore per la UI.
* Per flussi manuali (senza `template_flusso_id`) non c'e' skill-lock: governano reparto (caso B) o presa libera (caso C).
* La presa in carico esegue `UPDATE risorsa_umana_id` → fa scattare il giornale `FLUSSO_ASSEGNAZIONE_CAMBIATA` (trigger `trgfn_flussi_giornale_assegnazione`): anche l'auto-presa e' tracciata.
* Dopo l'UPDATE, verifica che esattamente 1 riga sia stata aggiornata (`GET DIAGNOSTICS`).
* Allineata a `fn_coda_lavoro_operatore`: i casi A/D emergono come livello COMPETENZA, il B come REPARTO, il C come LIBERO.

---

{% include-markdown "signature-core.md" %}
