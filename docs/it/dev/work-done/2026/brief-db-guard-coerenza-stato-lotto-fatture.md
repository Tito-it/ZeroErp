# Brief DB — Guard di coerenza stato lotto ↔ stato fatture

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-22 · **Owner**: Tid · **Stato**: 🟢 **APPLICATO (DB) + CAUSA RADICE CHIUSA (BE)**
> — migrato sul DB di sviluppo, **non ancora pushato**.
>
> **Esito 2026-07-22**: il team DB ha applicato **tre** constraint trigger
> `DEFERRABLE INITIALLY DEFERRED` (verificati live) — su `vendite.fatture`
> (`trg_fatture_def_guard_stato_lotto_coerente_ins_upd`), su
> `vendite.fatturazione_lotti` (`trg_..._def_guard_stato_fatture_coerente_upd`) e sul
> ponte `fatturazione_lotti_fatture` — più la vista `vendite.vw_lotti_fatture_incoerenti`
> e il codice errore `E_LOTTO_FATTURE_STATO_INCOERENTE` (556).
> **E il guard ha subito ripagato**: ha reso evidente la **causa radice** dell'incidente,
> che era lato BE ed è ora chiusa (§6).
>
> **Perimetro**: SOLO DB. Un invariante che impedisca (o almeno rilevi) il disallineamento
> fra `vendite.fatturazione_lotti.stato_doc_fiscale_id` e lo stato delle sue fatture.
> Nessuna modifica BE/FE richiesta.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → guard
> restrittivo da subito, nessuna compatibilità da mantenere.
> **Origine**: smoke C-9 «parte alta» del cockpit fatturazione
> ([brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md), C-9).

---

## 1. L'incidente (dati reali, non ipotesi)

Due lotti di giugno (`106 LTF-0000229`, `107 LTF-0000230`, creati il 2026-06-19) si
trovavano in uno stato **impossibile per il modello**:

| | stato |
| --- | --- |
| lotto `fatturazione_lotti.stato_doc_fiscale_id` | **EMESSA** (2) |
| sue fatture (`207`, `208`), non escluse, non critical | **DRAFT** (1) |

Alla numerazione (step DEFINITIVA) `fn_sync_lotto_fatture_stato` tenta di portare le
fatture a DEFINITIVA (8) e il guard di transizione le respinge:

```text
E_LOTTO_PARAMETRO_NON_COERENTE — transizione 1→8 (fattura)
  vendite.trgfn_fatture_guard_stato  ←  vendite.fn_sync_lotto_fatture_stato
```

Ed è **corretto** che le respinga: nella matrice `config.stati_doc_fiscale_transizioni`
la riga `DRAFT → DEFINITIVA` esiste solo con `ammesso = false` e `solo_lotto = true` —
per la **fattura** quel salto non è previsto affatto. Il percorso obbligato è
`DRAFT → EMESSA → DEFINITIVA`.

**Il difetto quindi non è il guard: è che l'incoerenza sia potuta nascere.** Il sistema
l'ha prodotta davvero, e la ha resa visibile solo **un mese dopo**, come errore opaco
in un altro processo. Fino ad allora quei due lotti sembravano sani.

### Perché è grave anche se erano dati di test

1. **Fallimento differito e disallineato dalla causa**: chi ha rotto il dato (giugno) non
   è chi vede l'errore (luglio). In un caso reale l'operatore riceve un blocco fiscale
   su un lotto che «ieri funzionava».
2. **Nessun rilevamento intermedio**: nessuna vista, check o job segnala il
   disallineamento. È emerso per caso, da uno smoke su un altro tema.
3. **La classe di stati impossibili è più ampia** di questo caso: qualunque avanzamento
   del lotto che non chiami (o veda fallire in silenzio) il sync lascia lo stesso buco.

## 2. L'invariante da presidiare

> Per ogni lotto, **ogni fattura collegata che non sia `esclusa` né `critical` deve avere
> lo stesso `stato_doc_fiscale_id` del lotto**, alla fine della transazione.

Le due eccezioni non sono negoziabili — sono già la semantica di
`fn_sync_lotto_fatture_stato`, che salta esattamente quelle righe:

```sql
WHERE lf.lotto_id = p_lotto_id
  AND COALESCE(lf.esclusa, FALSE) IS FALSE      -- riga esclusa dal lotto
  AND COALESCE(f.critical, FALSE) IS FALSE      -- fattura in errore critico
```

⚠️ **Da validare dal team DB prima di blindare**: esistono flussi legittimi che lasciano
lotto e fatture disallineati *a fine transazione*? I candidati che vedo (e che non posso
escludere dal solo BE) sono: **SDI/INVIATA** (il sync ha già un ramo speciale
`GIORNALIERO + INVIATA → chiusura lotto`), **rettifiche/resi**, e i lotti `SINGOLO` vs
`MASSIVO`. Se uno di questi ha un disallineamento *voluto*, va aggiunto alle eccezioni,
non va indebolito l'invariante.

## 3. Proposta tecnica

### 3.1 Prevenzione — `CONSTRAINT TRIGGER` DEFERRED (raccomandato)

Un constraint trigger **`DEFERRABLE INITIALLY DEFERRED`** su `vendite.fatture` e
`vendite.fatturazione_lotti` che, **al COMMIT**, verifichi l'invariante §2 per i lotti
toccati e sollevi un errore parlante (via `script.fn_log_and_raise_error`, codice
suggerito `E_LOTTO_FATTURE_STATO_INCOERENTE`) elencando lotto, fatture e i due stati.

**Perché deferred e non immediato**: la pipeline aggiorna il lotto e poi sincronizza le
fatture *nella stessa transazione* (lo step è atomico). Un trigger immediato
fallirebbe sullo stato intermedio legittimo; a COMMIT invece si valuta solo il risultato
finale, che è ciò che l'invariante descrive.

**Effetto**: l'incoerenza diventa impossibile da persistere, e chi la causa riceve
l'errore **subito**, nel punto in cui sbaglia.

### 3.2 Rilevazione — vista di sorveglianza (complemento)

Una vista `vendite.vw_lotti_fatture_incoerenti` con la query §4.1, utile per (a) verificare
il pregresso prima di attivare il guard, (b) monitoraggio continuo. Costa poco e resta
utile anche dopo la prevenzione (rileverebbe righe entrate da percorsi non coperti,
es. import massivi con trigger disabilitati).

### 3.3 Errore parlante nel sync (nice-to-have)

Oggi, se le fatture sono indietro, l'errore che arriva all'operatore è
`transizione 1→8` — vero ma illeggibile. Un pre-check in
`fn_sync_lotto_fatture_stato` potrebbe sollevare prima un messaggio del tipo
«il lotto è in EMESSA ma la fattura 207 è in DRAFT: riallineare il lotto prima di
numerare». Migliora la diagnosi; non sostituisce il guard §3.1.

## 4. Verifiche

### 4.1 Query di rilevazione (pregresso e monitoraggio)

```sql
SELECT l.id AS lotto_id, l.codice, sl.codice AS stato_lotto,
       f.id AS fattura_id, sf.codice AS stato_fattura
  FROM vendite.fatturazione_lotti l
  JOIN vendite.fatturazione_lotti_fatture lf ON lf.lotto_id = l.id
  JOIN vendite.fatture f ON f.id = lf.fattura_id
  LEFT JOIN config.stati_doc_fiscale sl ON sl.id = l.stato_doc_fiscale_id
  LEFT JOIN config.stati_doc_fiscale sf ON sf.id = f.stato_doc_fiscale_id
 WHERE COALESCE(lf.esclusa, FALSE) IS FALSE
   AND COALESCE(f.critical, FALSE) IS FALSE
   AND f.stato_doc_fiscale_id IS DISTINCT FROM l.stato_doc_fiscale_id;
```

**Esito 2026-07-22 dopo bonifica: 0 righe su 27 lotti** — il DB di sviluppo è pulito,
quindi il guard §3.1 può essere attivato **senza migrazione dati preliminare**.

### 4.2 Test attesi (pgTAP)

1. Transazione che porta il lotto a EMESSA **senza** sincronizzare le fatture → **fallisce
   al commit** con `E_LOTTO_FATTURE_STATO_INCOERENTE`.
2. Transazione che porta lotto **e** fatture a EMESSA (ordine qualsiasi) → **passa**
   (prova che il deferred non ostacola la pipeline reale).
3. Fattura `esclusa` / `critical` disallineata → **passa** (eccezioni §2).
4. Lotto senza fatture → **passa**.
5. Il percorso `fn_sync_lotto_fatture_stato` esistente resta verde (non-regressione).

## 5. Cosa è già stato fatto (lato BE, non serve rifarlo)

- **Bonifica dei 2 lotti** (2026-07-22, ok Tid — dati di test): riallineate le fatture
  207/208 a EMESSA con la funzione canonica
  `vendite.fn_sync_lotto_fatture_stato(<lotto_id>, 2)`, non con UPDATE grezzi, così da
  rispettare guard, `esclusa`, `critical` e il sync di `stato_esecuzione` sul ponte.
  Verificato: 0 incoerenze residue.
- **Errore non più muto**: `LottoPipelineRunner.run_lotto_until_done` ora conserva
  `errore {code, message, detail}` nell'esito invece di scartarlo, e
  `fatturazione_numera_handler` lo riporta in `saltati_dett`. Prima l'operatore leggeva
  un `motivo_stop: ERRORE` senza causa; ora vede il perché e può agire. **Questo migliora
  la diagnosi ma NON sostituisce il guard**: il dato incoerente continuerebbe a nascere.

## 6. Causa radice — trovata dal team DB, chiusa lato BE (2026-07-22)

Il guard ha fatto emergere **da dove nasceva** l'incoerenza, che il §1 lasciava aperta:
in `pipeline_runner._execute_pipeline_step` l'avanzamento dello stato del lotto
(`update_lotto_stato_doc`) era **incondizionato**, mentre la sync delle fatture era sotto
`if not dry_run` — entrambi dentro la `transaction.atomic()` della «Fase 2», che
**committa**. Quindi **un dry-run avanzava in modo permanente lo stato fiscale del lotto
lasciando indietro le fatture**: esattamente lo stato dei lotti 106/107.

Chiusi entrambi i difetti segnalati:

1. **Il dry-run non persiste più nulla** — `transaction.set_rollback(True)` sull'intera
   Fase 2 quando `dry_run`, invece di condizionare le singole scritture (più robusto: non
   dipende dal ricordarsi di condizionare ogni scrittura futura). Deve restare l'ultima
   istruzione del blocco: dentro un atomic marcato per rollback Django vieta altre query.
2. **Stato lotto e stato fatture non possono più viaggiare separati** — la sync è ora
   **incondizionata**: la coppia è indivisibile per costruzione. In dry-run non persiste
   (rollback) e in più il dry-run diventa *fedele*, perché esercita le stesse scritture
   del run vero e ne predice gli errori.

**Verificato sul DB reale**: dry-run su un lotto DRAFT → esegue gli step e lo lascia
**identico** (`DRAFT/COMPLETATO` prima e dopo), 0 incoerenze nella vista. Test unit:
la coppia `..._syncs_fatture_to_step_stato_on_forward` / `..._dry_run_sincronizza_ma_non_persiste`
differisce solo per il flag e asserisce sync-eseguita + rollback-marcato. Suite BE verde.

> ✅ Conseguenza per il team DB: **il dry-run è di nuovo utilizzabile** — non fallisce più
> al commit contro il guard.
