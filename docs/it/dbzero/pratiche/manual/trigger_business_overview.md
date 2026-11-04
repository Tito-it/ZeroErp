## 📘 Documentazione Concettuale – Trigger Business-Specific del Modulo Pratiche

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[fn_check_prerequisiti_flusso](fn_check_prerequisiti_flusso.md)
> [fn_guard_prerequisiti_flusso](fn_guard_prerequisiti_flusso.md)
> [fn_genera_pratica_da_flusso](fn_genera_pratica_da_flusso.md)
>
Tabelle:
>
[pratiche.giornale](giornale.md)
> [pratiche.pratiche](pratiche.md)
> [pratiche.flussi](flussi.md)

---
### 🎯 Scopo Principale
Questo documento descrive i **trigger business-specific** del modulo pratiche. Sono trigger che implementano logica di dominio (giornale di bordo, guard prerequisiti, generazione cross-pratica).

> **Nota**: i trigger standard (audit, tx_id, storico, lock_columns, attivo) **NON** sono inclusi qui. Sono applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

### Matrice Trigger

#### `pratiche.pratiche` — 4 trigger business

| Nome trigger | Fase | Evento | Trigger Function | Azione giornale |
|-------------|------|--------|------------------|-----------------|
| `trg_pratiche_z90_giornale_ins` | AFTER | INSERT | `trgfn_pratiche_giornale_ins` | PRATICA_CREATA |
| `trg_pratiche_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `trgfn_pratiche_giornale_stato` | STATO_CAMBIATO |
| `trg_pratiche_z90_giornale_assegnazione_upd` | AFTER | UPDATE OF risorsa_umana_id, unita_organizzativa_id | `trgfn_pratiche_giornale_assegnazione` | ASSEGNAZIONE_CAMBIATA |
| `trg_pratiche_z90_giornale_priorita_upd` | AFTER | UPDATE OF priorita_id | `trgfn_pratiche_giornale_priorita` | PRIORITA_CAMBIATA |

I trigger UPDATE usano `WHEN (OLD.colonna IS DISTINCT FROM NEW.colonna)` per evitare scritture nel giornale quando il valore non cambia realmente.

---

#### `pratiche.flussi` — 4 trigger business

| Nome trigger | Fase | Evento | Trigger Function | Scopo |
|-------------|------|--------|------------------|-------|
| `trg_flussi_a10_guard_prerequisiti_ins` | BEFORE | INSERT | `trgfn_flussi_guard_prerequisiti` | Blocca insert se prerequisiti non soddisfatti |
| `trg_flussi_z90_giornale_ins` | AFTER | INSERT | `trgfn_flussi_giornale_ins` | FLUSSO_CREATO |
| `trg_flussi_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `trgfn_flussi_giornale_stato` | FLUSSO_STATO_CAMBIATO |
| `trg_flussi_z90_generazione_upd` | AFTER | UPDATE OF stato_id | `trgfn_flussi_generazione` | Generazione cross-pratica su COMPLETATO |

**Ordine di esecuzione** (per UPDATE stato_id):
1. `_z90_giornale_stato_upd` — prima logga nel giornale
2. `_z90_generazione_upd` — poi genera pratiche cross (se COMPLETATO)

Il guard prerequisiti (`_a10_`) scatta solo su INSERT ed e' BEFORE — blocca la transazione prima che il flusso venga creato se i prerequisiti non sono soddisfatti.

---

#### `pratiche.note_pratiche` / `pratiche.note_flussi` — 1 trigger ciascuno

| Nome trigger | Fase | Evento | Trigger Function | Azione giornale |
|-------------|------|--------|------------------|-----------------|
| `trg_note_pratiche_z90_giornale_ins` | AFTER | INSERT | `trgfn_note_pratiche_giornale` | NOTA_AGGIUNTA |
| `trg_note_flussi_z90_giornale_ins` | AFTER | INSERT | `trgfn_note_flussi_giornale` | NOTA_AGGIUNTA |

Per le note a livello flusso, la trigger function recupera `pratica_id` dal flusso per inserire nel giornale a livello pratica.

---

#### `pratiche.allegati_pratiche` / `pratiche.allegati_flussi` — 1 trigger ciascuno

| Nome trigger | Fase | Evento | Trigger Function | Azione giornale |
|-------------|------|--------|------------------|-----------------|
| `trg_allegati_pratiche_z90_giornale_ins` | AFTER | INSERT | `trgfn_allegati_pratiche_giornale` | ALLEGATO_AGGIUNTO |
| `trg_allegati_flussi_z90_giornale_ins` | AFTER | INSERT | `trgfn_allegati_flussi_giornale` | ALLEGATO_AGGIUNTO |

Le tabelle allegati sono **immutabili** (solo `data_insert/user_insert`), quindi non hanno `tx_id`. Il campo `tx_id` nel giornale resta NULL per gli eventi allegato.

---

### Convenzioni di naming

I trigger seguono la convenzione progetto:

```
trg_<tabella>_<fase>_<descrizione>_<eventi>
```

| Parte | Significato |
|-------|-------------|
| `_a10_` | Guard/block — fase iniziale, puo' bloccare la transazione |
| `_z90_` | Finale — dopo le operazioni principali (logging, side effects) |
| `_ins` | Evento INSERT |
| `_upd` | Evento UPDATE |

---

### Trigger Function per il Giornale

Tutte le trigger function giornale seguono lo stesso pattern:
1. Inseriscono una riga in `pratiche.giornale` con l'azione corrispondente.
2. Usano `'SISTEMA'` come `origine`.
3. Catturano i dati rilevanti in `dettaglio` (jsonb).
4. Propagano `tx_id` dalla riga sorgente (se disponibile).
5. Per tabelle figlio di flussi, recuperano `pratica_id` tramite join su `pratiche.flussi`.

---

### Generazione Cross-Pratica

Il meccanismo di generazione si attiva quando un flusso passa a stato COMPLETATO:

1. Il trigger `trg_flussi_z90_generazione_upd` invoca `trgfn_flussi_generazione()`.
2. La trigger function verifica che il nuovo stato abbia `codice_interno = 'COMPLETATO'`.
3. Cerca regole matching in `regole_generazione`:
   - `template_flusso_origine_id` = template del flusso completato
   - `auto = true` e `attivo = true`
   - `esito_richiesto` NULL (qualsiasi esito) o uguale all'esito del flusso
4. Per ogni regola, invoca `fn_genera_pratica_da_flusso(flusso_id, regola_id)`.
5. La pratica generata ha `flusso_origine_id` impostato per tracciabilita'.
