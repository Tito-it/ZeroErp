## 📘 Documentazione Concettuale – Funzione `script.fn_get_stato_push_segment`

> 👀 **Vedi anche**
>
**Consumatori (push-list, eleggibile ⇔ LIBERA):**
>
• [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> • [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)
> • [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/funzioni/fn_list_contratti_da_pushare)
>
**Consumatori (rami reason delle capability):**
>
• [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine)
> • [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)

### 🎯 Scopo Principale

(creata 2026-07-19 — brief-db-push-commessa-gia-inviato §4b, rilievo ORD0000227)

**Classificatore condiviso dello stato-push di una riga documento** rispetto a
`vendite.commesse_attivita`. Prende la `segment_key` della riga (quella emessa
dalle push-list) e ritorna:

| valore | significato |
|---|---|
| `LIBERA` | nessuna attività: riga mai instradata in commessa |
| `ALLOCATA` | attività presenti, non tutte fatturate — pushata, in attesa di billing. **ANNULLATA inclusa** (decisione preventivi 2026-06-28: instradata = esclusa; il ri-push è un flusso da progettare a parte) |
| `EMESSA` | attività presenti e **tutte** fatturate |

Il match è `uguaglianza OR LIKE '<key>#CMP:%'`: vede anche le attività dei
**componenti BoM**, il cui suffisso `#CMP:<componente_id>` è appeso dal BE
esattamente alla segment_key della riga (`commesse_source_handlers.py`).

### Perché esiste

Prima il predicato «già inviato» viveva in **due forme divergenti** — nelle
`fn_list_*_da_pushare` e nella query inline del ramo reason della capability
ordine — entrambe ancorate alla *fatturazione* (`stato_emissione = 'EMESSA'`)
e cieche sui `#CMP`. Effetto (ORD0000227): righe già pushate ri-elencate a ogni
giro del batch e azione «Invia a commessa» ri-offerta dopo il consumo. Ora
liste e capability leggono **lo stesso verdetto**: al prossimo cambio di
semantica si tocca un posto solo.

### Regole

- **Pura**, `LANGUAGE sql STABLE`: nessun raise, nessuna scrittura.
- Il parametro è la segment_key **completa** emessa dalla lista: per i
  contratti include `:M:<YYYY-MM>` (il push contratti è ricorrente mensile by
  design — il mese successivo ha chiave diversa e resta `LIBERA`).
- `fn_list_consumi_da_pushare` NON la usa: la sua chiave è un prefisso
  per-documento (`CONS:<uid>:%`), già corretto; lì il fix è stato solo
  rimuovere il filtro su `stato_emissione`.
- ⚠️ Performance: il ramo `LIKE '...#CMP:%'` non usa il btree standard su
  `segment_key` (collazione non-C). Costo già accettato dal precedente
  preventivi; se il batch rallenta, la cura è un indice `varchar_pattern_ops`.

### Dipendenze DB

`vendite.commesse_attivita` (`segment_key`, `stato_emissione`).
