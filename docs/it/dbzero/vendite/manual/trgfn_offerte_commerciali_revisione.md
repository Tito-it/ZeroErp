## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_revisione()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni)
>
> Funzioni correlate:
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
>
> Contesto di sviluppo:
> [Brief DB offerte commerciali — Step 6](/dev/work-done/analisi-offerta-commerciale-db)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

La trigger function **`vendite.trgfn_offerte_commerciali_revisione()`** porta
automaticamente la revisione precedente (rev.N) in stato **SUPERATA** nel momento
in cui viene inserita una revisione successiva (rev.N+1).

E' applicata dal trigger `trg_offerte_commerciali_z90_revisione_ins`
(fase `_z90_`, `AFTER INSERT ON vendite.offerte_commerciali`).

---

### Logica operativa

1. **Guard rapido**: se `NEW.revisione_padre_id IS NULL`, la riga inserita e' una
   prima revisione (rev.1) e non c'e' nulla da fare. Esce subito.

2. **Lookup stato SUPERATA**: risolve `config.stati_doc_offerte.id` per
   `codice_interno = 'SUPERATA'` senza hardcodare l'id numerico.

3. **UPDATE revisione padre**: aggiorna `stato_doc_offerta_id` della riga con
   `id = NEW.revisione_padre_id`. Questo UPDATE riattiva il trigger guard
   `_a10_` sulla stessa tabella, che verifica la transizione `EMESSA → SUPERATA`:
   la transizione e' ammessa in `config.stati_doc_offerte_transizioni` (Step 4).

---

### Trigger associato

| Attributo | Valore |
| --------- | ------ |
| Nome      | `trg_offerte_commerciali_z90_revisione_ins` |
| Fase      | `_z90_` (effetto finale, dopo tutti i guard `_a10_`) |
| Evento    | `AFTER INSERT ON vendite.offerte_commerciali` |
| Granularita' | `FOR EACH ROW` |
| Migration | `20260524-26` |

---

### Interazione con il guard `_a10_`

L'UPDATE sulla revisione padre scatena il trigger
`trg_offerte_commerciali_a10_guard_transizione_upd`. Il guard verifica che
`EMESSA → SUPERATA` sia una transizione attiva in
`config.stati_doc_offerte_transizioni`: lo e', essendo inserita nel seed di
Step 4 (id=5, `stato_da=EMESSA`, `stato_a=SUPERATA`).

La catena e' quindi:

```
fn_crea_revisione_offerta (Step 7)
  └─ INSERT rev.N+1 (BOZZA)
       └─ trg_z90_revisione_ins (AFTER INSERT)
            └─ UPDATE rev.N → SUPERATA
                 └─ trg_a10_guard_transizione_upd (BEFORE UPDATE)
                      └─ controlla EMESSA→SUPERATA → ammessa ✓
```

---

### Nota O4 — Concorrenza intra-transazione

L'UPDATE agisce su una riga **diversa** da quella appena inserita
(`id = NEW.revisione_padre_id ≠ NEW.id`). Non vi e' autoricorsione ne'
conflitto di lock intra-transazione. Per questo motivo il trigger non e'
dichiarato `DEFERRABLE`: non e' necessario, e la mancata deferral semplifica
la testabilita' (i test pgTAP vedono il cambio di stato nella stessa
transazione senza dover fare commit).

---

### Note operative

* Il trigger non distingue lo stato attuale della revisione padre: si fida del
  guard `_a10_` per la validazione della transizione. Se per qualsiasi ragione
  la revisione padre non e' in stato `EMESSA` al momento dell'INSERT della
  rev.N+1, il guard blocchera' l'UPDATE con `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.
* La funzione non usa `script.fn_log_and_raise_error` in proprio: eventuali
  errori emergono dal guard `_a10_` durante l'UPDATE subordinato.
* Il lookup di `SUPERATA` e' fatto per `codice_interno` (immutabile per
  `script.trgfn_lock_columns`), non per `id` numerico: nessun hardcode.

---

{% include-markdown "signature-core.md" %}

---
