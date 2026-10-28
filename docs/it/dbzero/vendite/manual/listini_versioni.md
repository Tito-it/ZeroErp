## 📘 Documentazione Concettuale – Tabella `vendite.listini_versioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
### ⛔ Rev 2026-09-05 — il perimetro arriva dal LISTINO PADRE

La tabella non porta l'emittente, e **non deve portarlo**: una versione non può
appartenere a un'azienda diversa dal proprio listino, quindi una colonna qui sarebbe
una **seconda scrittura dello stesso fatto** — e due scritture prima o poi dissentono.

⇒ Il percorso è `listino_id → listini.emittente_soggetto_ruolo_id`, ed è applicato da:

| | |
| --- | --- |
| `rls_listini_versioni_ef_whitelist` | policy, via [fn_scope_ef_whitelist_via_listino](/dbzero/script/manual/fn_scope_ef_whitelist_via_listino) |
| `trg_listini_versioni_a10_guard_emittente_scope_ins_upd` | guard di scrittura, modo `listino` |

⭐ `listino_id` è `NOT NULL`: non esiste una versione orfana, quindi il percorso non ha
il buco tipico delle figlie facoltative — dove «padre assente» diventa «nessun
perimetro» e la policy si spegne da sola.

⚠️ **Su UPDATE il guard esce se `listino_id` non è cambiato.** Copre il caso peggiore —
spostare una versione sotto il listino di un altro — mentre le modifiche di merito (il
prezzo) le ferma la policy, che valuta ogni riga. Non è una svista: sono due presidi
con due compiti.

---

### ⛔ La trappola: padre e figlia nella STESSA istruzione

```sql
-- ⛔ Non funziona più
WITH lst AS (INSERT INTO vendite.listini (...) RETURNING id),
     v   AS (INSERT INTO vendite.listini_versioni (listino_id, ...)
             SELECT id FROM lst RETURNING id)
SELECT ...;
```

La policy legge il listino padre con **lo snapshot dell'istruzione**, che non contiene
la riga appena scritta dalla CTE sorella. ⇒ Padre invisibile, perimetro `NULL`, e la
scrittura viene rifiutata.

**Due istruzioni separate**: il padre prima, la figlia poi.

⚠️ E un secondo caso, più insidioso: i **vincoli differiti** — in testa
`trgfn_child_requires_active_parent` — non scattano all'`INSERT` ma alla verifica dei
vincoli, e lì leggono **col contesto attivo in quel momento**. Chi cambia utente fra la
scrittura e il commit si vede alzare *«Padre non attivo»* su un listino perfettamente
attivo. ⇒ I vincoli differiti si chiudono **nei panni di chi ha scritto**.

---

### 🎯 Scopo Principale
(ultima revisione 28-10-2026 — brief `brief-modello-documento-vendita` §16)

La tabella `vendite.listini_versioni` gestisce il versionamento temporale dei listini.
Ogni versione definisce una **finestra di validità atomica** dei prezzi: tutte le righe
prezzo (`vendite.listini_righe`) ereditano l'intervallo dalla versione che le contiene —
le righe **non hanno date proprie**. Per cambiare i prezzi in un nuovo periodo si crea una
**nuova versione** (anche clonando) e la si attiva.

---

### Regole principali

* univocità per `listino_id + codice_versione`;
* `valido_al` maggiore o uguale a `valido_dal` se valorizzato;
* una versione **CHIUSA ha sempre `valido_al`** (`chk_listini_versioni_chiusa_con_fine`);
* per ogni data **al più una versione in vigore** dello stesso listino: le versioni attive in
  stato ATTIVA o CHIUSA non si sovrappongono (`ex_listini_versioni_no_overlap`). Le BOZZE
  restano fuori: si preparano in anticipo accanto alla versione in uso. La domanda «quale
  versione vale in questa data» ha una sede sola:
  [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore).

---

### Lo stato, sul modello del documento

Lo stato è `stato_doc_listino_versione_id`, id del vocabolario
[config.stati_doc_listino_versioni](/dbzero/config/tabelle/stati_doc_listino_versioni)
(BOZZA, ATTIVA, CHIUSA); i passaggi sono nella matrice
[config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni).
Le regole comuni stanno nella [guida del modello](/guide/modello-documento-di-vendita).

| Pezzo | Oggetto |
| --- | --- |
| nascita in BOZZA | `trg_listini_versioni_a05_stato_iniziale_ins` (BB `script.trgfn_doc_stato_iniziale`) |
| porta: lo stato solo dai verbi | `trg_listini_versioni_a05_stato_solo_dal_verbo_upd` (BB `script.trgfn_doc_stato_solo_dal_verbo`) |
| passaggi dalla matrice; verso ATTIVA i motivi dell'attivazione; verso CHIUSA la fine passata | [trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato) |
| che cosa si cambia e si cancella, stato per stato | [trgfn_listini_versioni_guard_per_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_per_stato) |
| «Attiva» (BOZZA → ATTIVA), con la chiusura delle precedenti | [fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino), azione `attiva_listino` |
| le precedenti che l'attivazione chiude (anche l'anteprima) | [fn_versioni_listino_da_chiudere](/dbzero/vendite/funzioni/fn_versioni_listino_da_chiudere) |
| perché «Attiva» è spento (spenta, senza prezzi) | [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile), superficie [vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) |
| la chiusura a scadenza (ATTIVA → CHIUSA, di processo) | [fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute), dal job `chiusura_scadenze_daily` ([dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze), colonna `verbo_chiusura`) |

Che cosa si cambia: in **BOZZA** tutto, e la versione si elimina; di una **ATTIVA** solo
`valido_al` (la chiusura programmata, o quella delle precedenti all'attivazione di una nuova);
di una **CHIUSA** niente. Si chiude una versione impostandone la fine: lo stato CHIUSA lo
scrive il job alla scadenza. Fra la scadenza e il job la versione è ATTIVA con la fine passata:
non è più in vigore (decidono le date).

⚠️ Gli id di ATTIVA (2) e CHIUSA (3) sono scritti nel predicato dell'esclusione e nel CHECK
della chiusa (un vincolo non legge un'altra tabella); il pgTAP
`vendite/test-listino-versione-al-modello-v1` li confronta coi codici del vocabolario.

---

### Utilizzo previsto

* garantire coerenza storica prezzi per data di riferimento;
* supportare publish controllata di nuove versioni;
* finestre temporali "atomiche" per i prezzi: ogni versione è una *fotografia*
  immutabile dei prezzi validi nel suo intervallo.

### Asimmetrie del modello (note operative)

* **Le righe non hanno date proprie**: per cambiare un prezzo a metà intervallo
  bisogna creare una nuova versione e ricopiare *tutte* le righe (anche quelle
  invariate).
* **Una versione = una sola valuta**: il modello è implicitamente monovaluta
  (nessuna colonna `valuta_id` su `listini_versioni`).
* **`pricing_mode` non ancora esplicito**: le righe hanno un prezzo unitario costante.

---

{% include-markdown "signature-core.md" %}
