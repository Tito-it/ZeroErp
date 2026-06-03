## 📘 Documentazione Concettuale – Funzione `vendite.fn_crea_revisione_offerta(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
> [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
>
> Trigger correlati:
> [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione)
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
> [vendite.trgfn_offerte_commerciali_gen_codice](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_gen_codice)
>
> Funzioni correlate:
> [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)
>
> Contesto di sviluppo:
> [Brief DB offerte commerciali — Step 7](/dev/work-done/analisi-offerta-commerciale-db)

---

### 🎯 Scopo Principale

(rev 2026-05-25)

`vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)` crea una **nuova
revisione** (rev.N+1) di un'offerta commerciale, copiando testata, eccezioni
attive e utility (1:1). Il pattern riusa concettualmente
`fn_crea_revisione_preventivo` (§6.3 analisi offerta).

---

### Regole principali

- **Stato ammesso**: solo offerte in stato `EMESSA`. BOZZA si modifica
  direttamente; ACCETTATA/RIFIUTATA/SUPERATA/ANNULLATA sono terminali
  immutabili e non revisionabili.
- **`uid` e codice** generati ex novo: `uid` da default `uuidv7()`, codice
  `OFC-NNNNNNN` dal trigger `trgfn_offerte_commerciali_gen_codice` (BEFORE
  INSERT, Step 5). Non vengono ereditati dalla rev.N.
- **`revisione_numero`** = rev.N.`revisione_numero` + 1.
- **`revisione_padre_id`** = `p_offerta_id` (FK self alla rev.N).
- **Stato iniziale rev.N+1**: `BOZZA`.
- **Timestamp di transizione** (`data_emissione`, `data_accettazione`,
  `data_rifiuto`, `data_annullamento`) restano `NULL` sulla rev.N+1: vengono
  valorizzati al momento delle proprie future transizioni.
- **Eccezioni copiate**: solo righe con `attivo IS TRUE` (1:1, senza
  reinterpretazione).
- **Stato approvazione prezzo carry-forward** (rev2, 2026-06-01): le colonne
  `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` delle eccezioni
  (aggiunte da `20260601-01`) sono copiate **1:1** nella nuova revisione, **non**
  azzerate. Razionale: i gate L1/L2/L3 scattano solo sull'edit BE della riga (non
  all'emissione/push), quindi lo stato approvazione è l'unico marcatore persistente
  che un prezzo fuori-soglia è autorizzato/in attesa; azzerarlo lascerebbe un prezzo
  fuori-policy non marcato, che potrebbe arrivare al contratto senza controllo. Il
  carry-forward preserva l'invariante "prezzo fuori-policy sempre marcato". L'edit
  successivo sulla nuova revisione resta governato dal guard
  [`script.trgfn_righe_guard_pending`](/dbzero/script/funzioni/trgfn_righe_guard_pending)
  (blocco struttura mentre `PENDING`). *Caveat lifecycle pratica su `PENDING` in
  revisione SUPERATA: di competenza del dominio approvazioni (livello applicativo).*
- **Utility copiata**: 1:1, un solo record per offerta (UNIQUE `offerta_id`).
- **Marcatura padre SUPERATA**: gestita automaticamente dal trigger
  `trg_offerte_commerciali_z90_revisione_ins` (AFTER INSERT, Step 6), non da
  questa funzione. La transizione `EMESSA → SUPERATA` è ammessa in
  `config.stati_doc_offerte_transizioni`.

---

### Parametri

| Parametro     | Tipo                                      | Note                                        |
| ------------- | ----------------------------------------- | ------------------------------------------- |
| `p_offerta_id` | `vendite.offerte_commerciali.id%TYPE`    | ID offerta da revisionare. Obbligatorio, > 0. |
| `p_user`      | `text`                                    | Utente che esegue l'operazione (audit).     |

---

### 📦 Output

| Campo        | Tipo     | Descrizione                     |
| ------------ | -------- | ------------------------------- |
| `RETURNS BIGINT` | bigint | ID della nuova revisione (rev.N+1). |

---

### Codici errore

| Codice                                  | Quando                                                          |
| --------------------------------------- | --------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`                  | `p_offerta_id` NULL o <= 0; offerta non trovata.                |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO` | Stato corrente diverso da `EMESSA`.                             |
| `E_CONFIG_MANCANTE`                     | Stato `BOZZA` non trovato in `config.stati_doc_offerte`.        |

---

### Interazione con i trigger

La catena al momento dell'INSERT della rev.N+1:

```text
fn_crea_revisione_offerta
  └─ INSERT testata rev.N+1 (BOZZA)
       ├─ BEFORE INSERT: trgfn_offerte_commerciali_gen_codice → assegna OFC-*
       └─ AFTER INSERT:  trg_offerte_commerciali_z90_revisione_ins
                           └─ UPDATE rev.N → SUPERATA
                                └─ BEFORE UPDATE: trgfn_offerte_commerciali_guard_transizione
                                                    └─ controlla EMESSA→SUPERATA → ammessa ✓
```

---

### Esempio d'uso

```sql
-- Crea rev.2 dell'offerta 42 (deve essere in stato EMESSA)
SELECT vendite.fn_crea_revisione_offerta(42, 'operatore1');
-- Restituisce: 99  (id della nuova rev.2 in stato BOZZA)
-- L'offerta 42 passa automaticamente a SUPERATA.
```

---

{% include-markdown "signature-core.md" %}
