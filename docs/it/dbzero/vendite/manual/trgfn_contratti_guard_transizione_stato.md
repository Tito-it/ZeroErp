## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_guard_transizione_stato()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)
> [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — prezzi non autorizzati, chiesto all'ingresso in ATTIVO (dal 2026-09-24)
> [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto) — spegne «Attiva» con gli stessi motivi
>
Pattern correlato:
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato)
>
Linee guida:
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)

### 🎯 Scopo Principale

(latest review 24-09-2026 — il prezzo non autorizzato dal building block; 12-05-2026 — aggiunto check PENDING componenti BoM CASO A)

La trigger function **`vendite.trgfn_contratti_guard_transizione_stato()`**
blocca le transizioni di stato non ammesse sul workflow contratti
(`DRAFT -> ATTIVO -> CESSATO`) e impone la **precondizione temporale**
sulla cessazione: `ATTIVO -> CESSATO` e' consentita **solo se**
`valido_al < CURRENT_DATE`.

**Prezzo non autorizzato (rev 2026-09-24)**: blocca l'ingresso in `ATTIVO`
se una riga **o** un componente BoM, **attivi**, hanno il prezzo in attesa di
approvazione (`PENDING`) o **rifiutato** (`REJECTED`). Un contratto non diventa
operativo con un prezzo che nessuno ha autorizzato. Vedi la sezione in fondo.

> Storia: dal 2026-05-12 al 2026-09-24 il controllo guardava i **soli
> componenti** BoM CASO A (`contratti_righe_componenti`) in `PENDING`: una riga
> in attesa e ogni prezzo rifiutato passavano.

E' applicata dal trigger
`trg_contratti_a10_guard_transizione_stato_upd` (fase `_a10_`,
`BEFORE UPDATE OF stato_doc_contratto_id`).

Il guard fa **lookup via `codice_interno`** su
`config.stati_doc_contratti` per stabilita' rispetto al relabelling
del codice business-visible (codice_interno e' immutabile per
`script.trgfn_lock_columns`).

---

### Matrice transizioni

| Da | A | Ammessa | Condizione aggiuntiva |
| --- | --- | --- | --- |
| DRAFT | ATTIVO | si | Nessun prezzo non autorizzato (`PENDING`/`REJECTED`) su righe e componenti attivi (dal 24-09-2026; prima solo componenti `PENDING`) |
| ATTIVO | CESSATO | si | `NEW.valido_al IS NOT NULL AND NEW.valido_al < CURRENT_DATE` |
| (qualsiasi) | (stesso stato) | si | no-op (filtrato dal `WHEN` del trigger) |
| DRAFT | CESSATO | **no** | la bozza si cancella, non si chiude |
| ATTIVO | DRAFT | **no** | irreversibile |
| CESSATO | * | **no** | stato terminale |
| (qualsiasi) | SOSPESO | **non gestito** | fuori scope operativo attuale |
| SOSPESO | * | **non gestito** | fuori scope operativo attuale |

> Nota: lo stato `SOSPESO` esiste come `codice_interno` in
> `config.stati_doc_contratti` ma non e' attualmente parte del
> workflow operativo gestito dal guard. Una transizione che lo
> coinvolge cade nel ramo "non ammessa" → raise.

---

### Logica operativa

1. **Lookup combinato** di `codice_interno` per OLD e NEW in una
   sola query (pivot `MAX(CASE...)`) sul catalog
   `config.stati_doc_contratti`. Riduce 2 round-trip a 1.
2. **Dispatch** sul codice OLD/NEW:
   * `DRAFT -> ATTIVO`: ammessa.
   * `ATTIVO -> CESSATO`: ammessa solo se `NEW.valido_al < CURRENT_DATE`.
   * Tutte le altre combinazioni: ammessa = false.
3. Se non ammessa: `script.fn_log_and_raise_error` con codice
   `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` e contesto JSONB
   (`contratto_id`, `numero`, `stato_da`, `stato_a`, `valido_al`).
4. Se la destinazione è `ATTIVO`: solleva il primo motivo di
   [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati)
   con `script.fn_raise_primo_motivo_se_presente` (contesto `contratto_id`,
   `numero`, `stato_da`, `stato_a`).

Il filtro `WHEN (OLD.stato_doc_contratto_id IS DISTINCT FROM NEW.stato_doc_contratto_id)`
nel trigger garantisce che la funzione non venga invocata su no-op:
non e' presente nel corpo della funzione.

---

### Compatibilita' con il framework di chiusura automatica

L'UPDATE eseguito da `dbops.fn_apply_chiusura_scadenze()` (job
notturno `chiusura_scadenze_daily`) **soddisfa per costruzione** la
condizione `valido_al < CURRENT_DATE` del guard (la query del
framework ha lo stesso WHERE). Quindi il job passa il guard senza
bypass, in modo del tutto naturale.

Semantica `valido_al`: ultimo giorno **incluso** (convenzione della
colonna generata `validita`, linee-guida-sql §7b). Implica che:

* `valido_al = oggi` → cessazione manuale **vietata** (la condizione
  `< CURRENT_DATE` non e' soddisfatta); il job notturno dell'indomani
  chiudera' automaticamente.
* `valido_al = ieri` → cessazione manuale **ammessa** (oppure il job
  l'ha gia' fatto stanotte).

---

### Errori sollevati

| Codice | Quando | Contesto |
| --- | --- | --- |
| `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` | Transizione non ammessa | `contratto_id`, `numero`, `stato_da`, `stato_a`, `valido_al`. |
| `E_DOC_PREZZO_PENDENTE` | → ATTIVO con una riga o un componente attivi col prezzo in attesa | `contratto_id`, `numero`, `stato_da`, `stato_a`; conteggio in `valori`. Dal 2026-09-24. |
| `E_DOC_PREZZO_RIFIUTATO` | → ATTIVO con una riga o un componente attivi col prezzo rifiutato | come sopra. Dal 2026-09-24. |

Fino al 2026-09-24 qui usciva `E_COMPONENTE_PREZZO_PENDENTE` (id 439): quel codice
resta vivo, ma solo per il guard **per riga** dei componenti (un componente in
attesa non si modifica).

---

### Esempi

**1) Transizione ammessa (attivazione di una bozza):**

```sql
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
 WHERE id = 123 AND stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT');
-- ok
```

**2) Cessazione manuale anticipata (bloccata):**

```sql
-- Contratto attivo con valido_al = 2026-12-31 (futuro):
UPDATE vendite.contratti SET stato_doc_contratto_id = 5 WHERE id = 123;
-- ERROR:  P0001 — Contratto 123: transizione stato ATTIVO -> CESSATO non ammessa (valido_al=2026-12-31).
```

**3) Cessazione manuale dopo scadenza (ammessa):**

```sql
-- Contratto attivo con valido_al = 2025-12-31 (gia' passato):
UPDATE vendite.contratti SET stato_doc_contratto_id = 5 WHERE id = 123;
-- ok (oppure il job notturno l'ha gia' fatto)
```

**4) Pattern raccomandato dal service backend (cessazione data-driven):**

```python
# apps/vendite/services/contratti_service.py
# 1. PATCH valido_al
contratto.valido_al = data_cessazione
contratto.save()
# 2. Se data_cessazione < oggi: lo stato passa a CESSATO subito (transazione)
# 3. Se data_cessazione >= oggi: stato resta ATTIVO; il job notturno
#    chiudera' automaticamente al primo run dopo data_cessazione+1
```

---

### Note operative

* Lookup `codice_interno` (immutabile, UNIQUE) e non `codice` (relabellabile).
* Il guard scatta solo su UPDATE OF `stato_doc_contratto_id` (NON su INSERT). L'INSERT diretto in qualunque stato e' permesso (seed/import).
* Il trigger e' in fase `_a10_` (guard pre-audit), priorita' lessicografica garantita.

---

### Rev 2026-09-24 — il prezzo non autorizzato dal building block

Regola nuova, decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla
bozza*. Per il contratto vuol dire: non si attiva.

* Il controllo non è più scritto qui: lo fa
  [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
  la sede unica per preventivi, contratti, offerte, ordini e DDT. Questa funzione
  si limita a sollevare il primo motivo.
* Guarda **righe e componenti**, e sia il prezzo **in attesa** sia quello
  **rifiutato**. Prima guardava i soli componenti in attesa.
* Contano solo righe e componenti **attivi**: un componente spento resterebbe
  rifiutato per sempre e bloccherebbe il contratto senza rimedio.
* I codici diventano `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`.
* Il pulsante «Attiva» si spegne con gli stessi motivi:
  [`script.fn_available_actions_contratto`](/dbzero/script/funzioni/fn_available_actions_contratto)
  legge la stessa funzione, quindi pulsante e database non possono dissentire.
* L'annullamento della bozza non cambia: resta sempre possibile.

(changeSet `20260924-25`, brief `brief-db-preventivi-congelamento-pricing`.)

---

### Rev 2026-10-20 — sopra un contratto vincolante non si attiva, e lo dice

Un contratto non si attiva se il suo periodo si sovrappone a un altro contratto
**vincolante** (attivo o cessato, cioè né bozza né annullato) dello stesso cliente,
punto di fornitura, utility e ambito.

* Prima lo fermava solo il vincolo di esclusione `ex_contratti_no_overlap`, con un
  errore generico che non nominava il contratto in conflitto. Il vincolo resta come
  difesa dura: lo prende chi scrive un contratto già vincolante senza passare da una
  transizione (un INSERT diretto in ATTIVO).
* Il controllo lo fa
  [`script.fn_check_contratto_sovrapposto`](/dbzero/script/funzioni/fn_check_contratto_sovrapposto);
  qui si solleva il primo motivo, dopo prezzi e indirizzi:
  `E_CONTRATTO_OVERLAP_ESISTENTE`, col numero del contratto in conflitto.
* Si giudicano le date **nuove**: chi attiva e sposta le date nella stessa
  scrittura viene giudicato sul periodo che sta scrivendo.
* Il pulsante «Attiva» si spegne con lo stesso motivo.

(changeSet `20261020-21`, richiesta del backend del 2026-10-19.)

---

{% include-markdown "signature-core.md" %}

---
