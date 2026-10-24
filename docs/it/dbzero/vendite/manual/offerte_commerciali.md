## 📘 Documentazione Concettuale – Tabella `vendite.offerte_commerciali` (testata)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
> • [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> • [vendite.note_offerte_commerciali](/dbzero/vendite/tabelle/note_offerte_commerciali)
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> • [vendite.listini](/dbzero/vendite/tabelle/listini)
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
**Trigger e funzioni associate:**
>
> • `vendite.trgfn_offerte_commerciali_guard_transizione` — guard state machine ✅ (Step 4)
> • `vendite.trgfn_offerte_commerciali_gen_codice` — generazione `OFC-NNNNNNN` ✅ (Step 5)
> • `vendite.trgfn_offerte_commerciali_revisione` — marca padre SUPERATA all'INSERT rev.N+1 ✅ (Step 6)
> • [`vendite.fn_crea_revisione_offerta`](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — crea revisione N+1 ✅ (Step 7)
> • [`vendite.fn_push_offerta_a_contratto`](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — push idempotente a contratto DRAFT ✅ (Step 8)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

`vendite.offerte_commerciali` e' la **testata dell'offerta commerciale**: il documento
pre-contrattuale che propone al cliente condizioni quadro per una specifica utility,
prima della formalizzazione in contratto.

A differenza del preventivo (transazione puntuale → commessa → fattura),
l'offerta commerciale segue il percorso:

```
offerta ACCETTATA → fn_push_offerta_a_contratto → contratto DRAFT
offerta ACCETTATA → fn_genera_ordine_da_offerta → ordine DRAFT   (in alternativa, mai entrambi)
```

La simmetria strutturale con `vendite.contratti` e' intenzionale e garantisce che
`fn_push_offerta_a_contratto` sia una copia 1:1 senza conversioni (§5.1 analisi).

---

### Collocazione nel flusso operativo

1. **Creazione offerta** (BOZZA) — compilazione emittente, BA, istanza utility, listino,
   variazione globale ed eccezioni puntuali.
2. **Emissione** (BOZZA → EMESSA) — il trigger guard congela `listino_versione_id` se NULL
   e verifica che la versione sia ATTIVA (§5.3). Viene valorizzata `data_emissione`. Dal
   2026-10-21 rifiuta anche un'offerta con una riga che la regola intera non ammette piu'
   (`script.fn_check_righe_documento`, `E_DOC_RIGA_NON_AMMESSA`): le regole di una riga
   dipendono da dati che stanno fuori dalla riga (listino in vigore, vocabolario del
   perimetro), e le righe gia' scritte le intercetta il primo passo che le usa.
3. **Esito commerciale** — il cliente risponde:
   - **ACCETTATA** → `fn_push_offerta_a_contratto` crea un contratto DRAFT, oppure
     `fn_genera_ordine_da_offerta` crea un ordine DRAFT (dal 2026-10-21 un verbo DB; prima
     lo componeva il backend). Pulsanti spenti col motivo se una riga non puo' andare nel
     documento da generare (`fn_check_righe_documento`, `fn_check_righe_offerta_in_ordine`).
   - **RIFIUTATA** → l'operatore inserisce `motivazione_rifiuto`; valorizzata `data_rifiuto`.
4. **Annullamento** (BOZZA → ANNULLATA) — ritiro interno prima dell'emissione;
   valorizzate `data_annullamento` e `motivazione_rifiuto`. Dal 2026-10-21 anche
   **ACCETTATA → ANNULLATA**, l'uscita quando l'offerta non si trasforma: ammessa solo se
   l'offerta non vive in un contratto o in un ordine non annullato
   (`script.fn_check_offerta_annullabile`, `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`).
5. **Revisione** (Step 7) — `fn_crea_revisione_offerta` crea rev.N+1 e marca la rev.N
   corrente come SUPERATA (stato terminale tecnico).

---

### State machine

| Da       | A          | Chi la esegue              | Note                                          |
| -------- | ---------- | -------------------------- | --------------------------------------------- |
| BOZZA    | EMESSA     | operatore                  | Congela listino_versione_id; valorizza data_emissione |
| BOZZA    | ANNULLATA  | operatore                  | Ritiro interno; valorizza data_annullamento e motivazione_rifiuto |
| EMESSA   | ACCETTATA  | operatore                  | Apre push a contratto o genera ordine; valorizza data_accettazione |
| ACCETTATA | ANNULLATA | operatore                  | Dal 2026-10-21: solo senza contratto o ordine vivo; motivazione obbligatoria |
| EMESSA   | RIFIUTATA  | operatore                  | No del cliente; valorizza data_rifiuto e motivazione_rifiuto |
| EMESSA   | SUPERATA   | trigger (fn_crea_revisione) | Stato terminale tecnico; rev.N+1 diventa la nuova offerta |

Stati terminali immutabili: **RIFIUTATA**, **ANNULLATA**. **SUPERATA** ha il solo rientro
automatico (SUPERATA → EMESSA, quando la revisione si annulla). **ACCETTATA** non e' terminale:
si trasforma in un contratto o in un ordine, oppure si annulla (`brief-db-offerta-emissione-ed-erogazione`
§H.3, H-R3).

#### Timestamp di transizione

| Colonna              | Valorizzata al passaggio |
| -------------------- | ------------------------ |
| `data_emissione`     | BOZZA → EMESSA           |
| `data_accettazione`  | EMESSA → ACCETTATA       |
| `data_rifiuto`       | EMESSA → RIFIUTATA       |
| `data_annullamento`  | BOZZA o ACCETTATA → ANNULLATA |

`data_rifiuto` e `data_annullamento` sono distinte per consentire report separati sui
due flussi di chiusura negativa (rifiuto cliente vs. ritiro interno).

`motivazione_rifiuto` e' valorizzata su entrambi i passaggi negativi (RIFIUTATA e ANNULLATA)
ed e' dato di prima cittadinanza: visibile in lista, esportabile, filtrabile — non appartiene
a `meta` JSONB.

---

### Identita e numerazione

- **`uid`** (UUID, default `uuidv7()`, UNIQUE, immutabile) — usato come `sorgente_uid`
  in `vendite.contratti` al momento del push (pattern sorgente §6.3 pratiche).
- **`codice`** (`OFC-NNNNNNN`, UNIQUE, immutabile) — generato da
  `trgfn_offerte_commerciali_gen_codice` tramite `config.sistema_codici` (Step 5).

---

### Listino e variazione globale

- `listino_id` — listino di riferimento proposto nell'offerta. Obbligatorio.
- `listino_versione_id` — versione congelata all'emissione (§5.3). NULL ammesso solo
  in BOZZA; il trigger guard blocca il passaggio BOZZA → EMESSA se NULL o versione
  non ATTIVA.
- `tipo_variazione_globale` — `PERCENTUALE | VALORE_FISSO | NULL` (NULL = nessuna
  variazione). CHECK `chk_offerte_tipo_variazione_globale` (specchio di `contratti`).
- `valore_variazione_globale` — percentuale o valore fisso (numeric(10,4), default 0).
  CHECK `chk_offerte_variazione_globale_coerenza`: se tipo e' valorizzato, valore
  deve essere NOT NULL; se tipo e' NULL, valore deve essere NULL o 0.

Le eccezioni puntuali articolo per articolo risiedono in `offerte_commerciali_eccezioni`.

---

### Valuta (dal 2026-05-29)

- `valuta_id` — FK a `config.valute(id)`, **nullable**. Source-of-truth della valuta
  sulla testata, fissata come **snapshot a INSERT-time** (simmetria con
  `vendite.preventivi` e `vendite.contratti`).
- Valorizzata dal trigger `trg_offerte_commerciali_a10_default_valuta_ins`
  (→ [`trgfn_offerte_commerciali_default_valuta`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_default_valuta))
  **solo se non passata esplicitamente** nel payload: il trigger delega al
  resolver canonico [`vendite.fn_get_valuta_id`](/dbzero/vendite/funzioni/fn_get_valuta_id)
  con catena **BA → emittente → gestore**. Nessuna logica di risoluzione duplicata.
- Il trigger ordina dopo `_a10_default_emittente_*`, quindi `emittente_fiscale_id`
  e' gia' risolto e viene mappato a `soggetto_ruolo_id` per la fn.
- Se la catena non risolve alcuna valuta, `fn_get_valuta_id` solleva
  `E_CONFIG_MANCANTE` (id 205) via `script.fn_log_and_raise_error`.
- L'indice FK e' gestito dalla policy centralizzata (`dbops.fk_index_policy`,
  `consentito=false` come `fk_preventivi_valuta`): nessun indice manuale.

---

### Validita temporale

`validita_dal` e `validita_al` indicano la finestra commerciale proposta al cliente.
La scadenza (`validita_al`) e' un **avviso non bloccante** (§5.6): l'offerta resta
accettabile anche dopo la scadenza; la UI segnala lo stato "scaduta" come attributo
calcolato. Nessun job automatico cambia stato in v1.

CHECK `chk_offerte_validita_date`: `validita_al >= validita_dal` quando entrambe valorizzate.

---

### Revisioni

- `revisione_numero` — parte da 1, incrementato da `fn_crea_revisione_offerta` (Step 7).
- `revisione_padre_id` — FK self → `offerte_commerciali(id)`. NULL su rev.1; su rev.N+1
  punta all'id della rev.N precedente (che viene marcata SUPERATA dal trigger Step 6).
- CHECK `chk_offerte_revisione_numero`: `revisione_numero >= 1`.

La catena di revisioni e' navigabile risalendo `revisione_padre_id`.

---

### Push a contratto (Step 8)

All'accettazione, `fn_push_offerta_a_contratto` crea un `vendite.contratti` DRAFT:

- copia 1:1 di tutti i campi compatibili (billing_account, istanza_utility, utility,
  listino, listino_versione, variazione globale);
- copia eccezioni da `offerte_commerciali_eccezioni` → `contratti_righe`;
- copia snapshot da `offerte_commerciali_utilities` → `contratti_utilities`;
- imposta `contratti.offerta_id` e `sorgente_uid = offerta.uid` (idempotenza UNIQUE).

La funzione e' **idempotente**: rilanciarla sullo stesso `offerta_id` non crea duplicati
grazie al vincolo UNIQUE su `contratti.offerta_id` (pattern A §6.9.3).

---

### Cardinalita mono-utility

Un'offerta riguarda una sola utility (mono-utility §5.1): `istanza_utility_id` e
`utility_id` sono NOT NULL e non ammettono array o pivot. Il caso multi-utility
viene gestito con N offerte distinte, eventualmente raggruppate in futuro tramite
un pacchetto commerciale additivo (§5.1-bis, non implementato in v1).

---

{% include-markdown "signature-core.md" %}

---

### Il listino del documento (dal 2026-10-08)

L'offerta si riferisce solo a un listino della **sua utility** e del **suo emittente**. Lo dice la
check pura `script.fn_check_listino_documento(listino, utility, emittente_fiscale_id)`, che il guard
`script.trgfn_doc_guard_listino_documento` solleva all'INSERT e quando cambiano `listino_id`,
`utility_id` o `emittente_fiscale_id` (`E_DOC_LISTINO_UTILITY_DIVERSA`,
`E_DOC_LISTINO_EMITTENTE_DIVERSO`, campo `listino_id`). I documenti già scritti non si
rigiudicano. La tendina del form legge la stessa check da `vendite.fn_listini_selezionabili(utility,
emittente_fiscale_id)`. Brief `brief-db-offerta-emissione-ed-erogazione` §F.2.

