## 📘 Documentazione Concettuale – Funzione `script.fn_get_stato_push_segment`

> 👀 **Vedi anche**
>
**Consumatori (push-list, eleggibile ⇔ LIBERA):**
>
• [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> • [vendite.fn_ddt_push_diagnosi](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi) — per il DDT lo legge lei (rank 4 e colonna `segment`), e il lister ne deriva
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

---

### 🔄 rev 2026-08-18 — riconosce il suffisso `#RET:` delle rettifiche

Brief: `brief-design-note-credito-resi` (slice **N11**).

L'avvertenza era già scritta, nel commento vivo di
`vendite.fn_list_ddt_da_pushare`:

> *«È l'unica cintura che impedirà di ri-spingere una riga la cui differenza
> torna positiva per una RETTIFICA (nota di credito): chi introdurrà un
> segment_key nuovo per la rettifica deve insegnarglielo.»*

Il predicato guadagna quindi:

```sql
OR ca.segment_key LIKE p_segment_key || '#RET:%'
```

che copre **entrambe** le forme, perché il suffisso `#CMP:` di un kit viene DOPO
`#RET:<n>`:

```text
DDT:<uid>:R:<id>#RET:1
DDT:<uid>:R:<id>#RET:1#CMP:<componente>
```

⚠️ Ed è anche il motivo per cui la madre scrive `#RET` **prima** di `#CMP` e non
il contrario: così `split_part(segment_key, '#CMP:', 1)` continua a dare il
`kit_key` e `vw_af_merce_per_riga` legge la rettifica senza modifiche.

#### ⚠️ Non è cosmesi

Su una partita fatturata dalla corsia **DDT** il segmento porta già l'attività
`NORMALE`, quindi risulta `EMESSA` comunque: lì non cambia nulla. Su una partita
fatturata dalla corsia **ORD**, invece, il segmento DDT non ha alcuna attività —
e resterebbe `LIBERA` anche dopo la nota di credito. A impedire una ri-spinta ci
sarebbe **solo** la cintura XOR sullo stato del documento d'ordine.

⭐ **Due cinture sono una; una è zero.** Con il suffisso riconosciuto, la partita
è protetta dalla propria storia e non da una condizione che vive altrove.

⚠️ **Nessun cambio di comportamento all'applicazione**: al 2026-08-18 le righe
`RETTIFICA` erano zero, quindi nessun segmento conteneva `#RET:` e il
classificatore rispondeva esattamente come prima su ogni riga esistente. È una
cintura che entra in funzione il giorno in cui serve.
