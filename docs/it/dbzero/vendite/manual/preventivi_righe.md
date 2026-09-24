## 📘 Documentazione Concettuale – Tabella `vendite.preventivi_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [config.iva](/dbzero/config/tabelle/iva)  
>
**Approfondimento funzioni/trigger:**
>
• [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa)  
• [vendite.trgfn_preventivi_righe_guard_pending](/dbzero/script/funzioni/trgfn_righe_guard_pending) — guard workflow L3 approvazione prezzo (dal 22-04-2026)  
• [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — controllo complementare sul preventivo (dal 2026-09-24): una riga attiva PENDING o REJECTED blocca EMESSO e ACCETTATO  

**Tipi ENUM correlati:**
>
• `config.stato_approvazione_prezzo` — PENDING/APPROVED/REJECTED per il workflow L3 (valorizza `stato_approvazione_prezzo` sulla riga)  

---
### 🎯 Scopo Principale
`vendite.preventivi_righe` contiene il dettaglio economico-tecnico del preventivo:
articolo, quantita`, prezzo, sconto, IVA e snapshot UoM operativa.

Le righe sono la base informativa per la successiva generazione di
`attivita_fatturabili` nel ramo `PREVENTIVI`.

---

### Quantita` e UoM operativa

> **Refactor 2026-05-31**: direzione canonica unica `qta_operativa → quantita`,
> allineata a `contratti_righe` / `offerte_commerciali_eccezioni`.

La **sorgente** e' sempre la quantita operativa scelta dall'operatore; la quantita
base e' **derivata** dal trigger:

* `qta_operativa` + `uom_operativa_id` — **SORGENTE** (input operatore nella UoM
  operativa scelta). `qta_operativa` e' **NOT NULL**: il preventivo non ha
  `fonte_quantita_attesa` (documento one-shot, nessuna sorgente esterna che
  differisca la quantita), quindi l'operatore la fornisce sempre.
* `quantita` — **DERIVATA** (UoM base), **nullable**: la calcola solo il trigger
  `script.trgfn_qta_from_operativa` come `qta_operativa * factor_to_base`.
* `factor_to_base` — snapshot del fattore di conversione, **nullable**: se NULL il
  trigger lo deriva dal mapping `catalogo.articoli_uom_operativa` e lo salva (snapshot
  DB-first: ne' FE ne' BE devono conoscere il fattore).

> La derivazione avviene **una sola volta** (nel trigger). Prima del refactor il BE
> calcolava anche `qta_operativa = quantita × factor`, componendosi col trigger e
> producendo `quantita = quantita × factor²` (bug latente per `factor ≠ 1`): ora
> rimossa, resta solo la direzione canonica.

---

### Regole principali

1. Ogni riga appartiene a un preventivo (`preventivo_id` obbligatorio).
2. `articolo_id` obbligatorio e referenziato a catalogo.
3. Controllo sullo sconto (`chk_prevrighe_sconto`) e vincolo sulla **sorgente**
   quantita: `chk_prevrighe_qta_operativa_nonzero` (`qta_operativa <> 0`). Le
   quantita possono essere **negative** (resi/storni); vietato solo lo zero. Non
   esiste piu' un vincolo di positivita' su `quantita` (rimosso
   `chk_prevrighe_quantita_pos`).
4. Flag `attivo` per escludere righe senza cancellazione fisica.

---

### Ruolo nel flusso fatturazione

1. Le righe alimentano la valutazione di eleggibilita` del preventivo.
2. In stato testata idoneo (es. `ACCETTATO`) diventano fonte per creare
   attività in `vendite.attivita_fatturabili`.
3. Le attività, non le righe preventivo direttamente, entrano nel flusso lotto/fatture.

---

### Campi chiave funzionali

* `preventivo_id`, `articolo_id`
* `descrizione`
* `quantita`, `qta_operativa`, `uom_operativa_id`, `factor_to_base`
* `prezzo_unitario`, `sconto_percentuale`, `iva_id`
* `ordine`, `attivo`
* `meta`

---

### Audit e qualità dati

* audit standard (`data_insert`, `user_insert`, `data_update`, `user_update`);
* trigger di validazione referenziale su articoli/IVA/UoM attivi;
* prevenzione disattivazione riga se esistono note collegate (`note_preventivo`).

---

### Ruolo nel sistema

`vendite.preventivi_righe` rappresenta il livello di granularita` commerciale
necessario per trasformare il preventivo in elementi fatturabili in modo tracciabile,
coerente e idempotente lungo la pipeline.

### 🔄 rev 2026-09-13 — la data di consegna richiesta dal cliente

Colonna nuova, facoltativa: **`data_consegna_richiesta_cliente`**
(`20260913-07`). Solo la richiesta, non la conferma: su un preventivo non c'è
ancora niente da confermare. Al push verso l'ordine la data passa sulla riga
d'ordine (`fn_push_preventivo_a_ordine`, dal `20260913-20`), attraverso la
vista [vw_preventivi_righe_smistabili_ordine](/dbzero/vendite/views/vw_preventivi_righe_smistabili_ordine).
⭐ **E sopravvive anche alla revisione** (dal `20260914-13`): la rev N+1 nasce
con le righe ricopiate da
[fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo),
che le copia con un elenco esplicito di colonne — fino a quel giorno la data
non era nominata e la revisione nasceva con la data a `NULL`, in silenzio
(segnalazione del BE, 2026-09-14). Sono **due** passaggi in cui la riga si
ricopia, e vanno tenuti allineati entrambi: il presidio è
`db/pgtap/vendite/test-date-consegna-ordine-v1.sql` (test 4 per il push, 11
per la revisione).
Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezioni 2 e 6-quinquies.

### 🔄 rev 2026-09-14 — le marche di approvazione prezzo sopravvivono alla revisione

`stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` passano 1:1
sulla riga della rev N+1 (`20260914-14`, decisione di Tid): un prezzo fuori
policy approvato o in attesa resta **marcato** anche dopo una revisione, e la
riga `PENDING` copiata resta congelata dal guard. Dal 2026-04-22 a quel giorno
le due colonne non erano nominate nella copia e la rev N+1 nasceva senza marca.
⭐ Da quel giorno l'elenco delle colonne copiate è **presidiato**
(`test-fn-crea-revisione-preventivo-riga-completa-v1`, test 1): una colonna
nuova su questa tabella fa rosso finché non viene o copiata o dichiarata
esclusa con la ragione. Dettaglio in
[fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo).
