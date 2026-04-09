## 📘 Documentazione Concettuale – Tabella `vendite.listini_associazioni`

> 👀 **Vedi anche**
>
> **Guida concettuale**: [gestione-listini](/guide/gestione-listini)
>
> **Refactor 2026-04-09**: [WIP listini-commercio](/dev/work-in-progress/listini-commercio)
>
> **Approfondimento tabelle:**
>
> * [vendite.listini](/dbzero/vendite/tabelle/listini)
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)

---

### 🎯 Scopo Principale
(latest review 09-04-2026)

La tabella `vendite.listini_associazioni` definisce **a quale contesto operativo si applica un listino**: il filtro di visibilita usato dal resolver come **Fase 1** della risoluzione prezzo (`vendite.fn_resolve_prezzo_listino`).

Ogni associazione collega un listino a una *triple di scope dimensionale*:

* `billing_account_id` — il cliente specifico (NULL = qualunque)
* `utility_id` — il tipo di servizio (NULL = qualunque)
* `emittente_soggetto_ruolo_id` — l'emittente fiscale (NULL = qualunque)

Le dimensioni `NULL` agiscono come **wildcard discreto**: una associazione `(NULL, NULL, NULL)` matcha qualunque richiesta, una associazione `(BA=42, NULL, NULL)` matcha solo le richieste per BA=42 indipendentemente da utility/emittente.

---

### 🔒 Invariante centrale (refactor 2026-04-09)

> **Per ogni triple `(BA, utility, emittente)`** — con `NULL` come wildcard discreto — **esiste al massimo una associazione attiva sull'intervallo temporale, indipendentemente dal listino.**

Vincolo dichiarativo: **`ex_listini_associazioni_no_overlap`** (EXCLUDE USING gist) con:

* `COALESCE(billing_account_id, -1::bigint) WITH =`
* `COALESCE(utility_id, -1) WITH =`
* `COALESCE(emittente_soggetto_ruolo_id, -1::bigint) WITH =`
* `daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]') WITH &&`
* `WHERE attivo IS TRUE`

Il vincolo e **cross-listino**: blocca due associazioni di listini diversi con stesso scope e overlap temporale, non solo due dello stesso listino.

#### Cosa garantisce

A una data data, per uno scope dimensionale dato, **un solo listino e responsabile del prezzo**. Niente competizione, niente tie-break, niente ambiguita. Il resolver `fn_resolve_prezzo_listino` non puo mai trovare due associazioni concorrenti.

#### Storia del vincolo

Prima del refactor 2026-04-09 il vincolo era `uq_listini_associazioni_key_attiva` con `listino_id` nella key e `valido_dal` come scalare — permetteva sia (a) due listini sullo stesso scope, sia (b) due righe con date di inizio diverse ma attive entrambe sull'intervallo di overlap. Il refactor ha sostituito l'unique con un EXCLUDE GIST che corregge entrambe le falle. Vedi [WIP listini-commercio §2](/dev/work-in-progress/listini-commercio).

---

### Workflow di sostituzione (autoclose + insert)

Per sostituire un'associazione esistente (cambio listino, cambio annuale, override temporaneo):

1. **Autoclose della vecchia**: `UPDATE listini_associazioni SET valido_al = nuova.valido_dal - 1 WHERE id = vecchia_id`
2. **Insert della nuova**: `INSERT INTO listini_associazioni (..., valido_dal, valido_al) VALUES (..., nuova_valido_dal, nuova_valido_al)`
3. Tutto in **transazione atomica**

Stesso pattern adottato per `listini_versioni` (publish di una nuova versione con autoclose della precedente, post-fix `20260409-01`).

#### Caso "promo temporanea"

Per applicare un listino "promo" su un BA per `[Pmin, Pmax]`:

```text
1. UPDATE base BA: valido_al = Pmin - 1
2. INSERT promo BA: valido_dal = Pmin, valido_al = Pmax
3. INSERT base BA ripristino: valido_dal = Pmax + 1, valido_al = NULL
Tutto in transazione atomica.
```

L'eventuale endpoint backend dedicato `apply_temporary_pricing(BA, Pmin, Pmax, listino_id)` verra aperto come issue separata se/quando emerge il caso d'uso reale. Vedi [WIP listini-commercio §3.4](/dev/work-in-progress/listini-commercio).

---

### Regole secondarie

* `valido_al > valido_dal` se valorizzato (chk_listini_associazioni_date).
* FK obbligatoria su `listino_id`. FK opzionali su `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`.
* Trigger `child_requires_active_parent`: l'INSERT/UPDATE fallisce se il listino parent non e attivo.

> 🗑️ **Campo `priorita` RIMOSSO il 2026-04-09 (Fase 2 refactor)**: con l'invariante univocita stretta per scope (`ex_listini_associazioni_no_overlap`) non discriminava piu nulla. La colonna e il check constraint `chk_listini_associazioni_priorita` sono stati droppati con la migration `20260409-04-drop-priorita-listini-associazioni`. Vedi [WIP listini-commercio §5](/dev/work-in-progress/listini-commercio).

---

### Ruolo nel resolver `fn_resolve_prezzo_listino`

Le associazioni sono la **Fase 1** del resolver:

1. Si filtra `listini_associazioni` per `attivo IS TRUE`, `valido_dal <= data_riferimento`, `valido_al IS NULL OR valido_al >= data_riferimento`
2. Si verifica compatibilita scope: `billing_account_id IS NULL OR billing_account_id = p_BA` (analogo per utility e emittente)
3. I listini risultanti sono i candidati per le fasi successive (versioni → righe → match per specificita)

**Post refactor 2026-04-09**: la fase 1 ritorna **al massimo un listino candidato per ogni scope** (garanzia data dall'invariante univocita). Niente competizione tra candidati, niente tie-break.

---

### Garanzie operative

* **Determinismo**: a parita di input (`articolo, uom, data, BA, utility, emittente`) il resolver restituisce sempre lo stesso prezzo.
* **No fallback silenzioso**: se nessuna associazione matcha lo scope, il resolver solleva `E_PREZZO_LISTINO_NON_TROVATO`. Niente prezzo arbitrario.
* **Errore esplicito su violazione invariante**: tentativo di INSERT/UPDATE che produrrebbe overlap → DB rifiuta con `ex_listini_associazioni_no_overlap`. Niente caos da configurazione.

---

{% include-markdown "signature-core.md" %}
