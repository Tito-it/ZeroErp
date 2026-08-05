# Brief BE — ricadute della bonifica dei riferimenti morti

> 🟢 **CHIUSO — 2026-08-05, su ok di Tid.** Le sei voci del §6 sono chiuse; la
> settima (`FP_VARIADIC`) pure. Quello che prosegue vive in due posti, entrambi
> dichiarati qui sotto: nessuna riga di questo brief resta senza casa.
>
> **Il §5 — il punto serio — è chiuso end-to-end**, e non per deduzione dai
> changeSet: il giro completo è stato eseguito sul database vivo. Il DB manda il
> codice nel campo strutturato (`CONSTRAINT`, `20260805-05`), il translator lo
> legge per primo col testo come ripiego, la policy risolve:
>
> ```text
> script.fn_log_and_raise_error(... 'E_PREV_TRANSIZIONE_NON_AMMESSA' ...)
>   → constraint_name = E_PREV_TRANSIZIONE_NON_AMMESSA
>   → http 409 + «Transizione del preventivo non ammessa: da A a B.»
> ```
>
> Prima lo stesso errore usciva come `E_DATABASE` a 400 con messaggio generico.
> Il contratto invertito descritto nel §5 — più il seed è completo, meno
> l'error handling funziona — non esiste più.
>
> **`FP_VARIADIC`: zero call site sotto i sei argomenti** (famiglia F8, commit
> `b7d594244`). Verificato contando gli argomenti sul sorgente di ogni funzione
> viva. ⚠️ Un conteggio ingenuo ne segnala cinque: quattro sono menzioni dentro
> **commenti**, e il quinto è `anagrafiche.trgfn_clienti_sync_stato_pdp`, che di
> argomenti ne ha sette — il contatore si ferma prima perché in una chiave jsonb
> c'è **una parentesi chiusa di troppo** (`'…configurati correttamente)'`), che
> gli fa credere chiusa la chiamata. Svista innocua, ma da togliere se il team DB
> passa di lì.
>
> **Le due code, e dove sono andate:**
>
> | Cosa | Dove prosegue |
> | --- | --- |
> | §6 item 2 — il passo SDI gira per la prima volta e nessuno legge a valle (sospeso per decisione di Tid) | [fatturazione-roadmap §9](../work-in-progress/fatturazione-roadmap.md) — è materia di fatturazione, non di bonifica |
> | §5 → i 133 codici `E_*` sollevati dal DB e non dichiarati in `error_policies.py` | [brief-db-codice-errore-strutturato §12.5](../work-in-progress/brief-db-codice-errore-strutturato.md) — il figlio, che prosegue |
>
> ---

**Chi scrive:** team DB (`dev/db-tid`), 2026-08-04.
**Perché:** i changeSet `20260804-37..65` hanno riparato funzioni che il backend
chiama, e ne hanno droppate altre che il backend **documenta come attive**.
**Origine:** [brief-db-bonifica-riferimenti-morti](brief-db-bonifica-riferimenti-morti.md)
**Stato DB:** applicato e verde il 2026-08-04 (presidio: 0 difetti aperti).

---

## 1. Due funzioni che il BE chiama non hanno mai potuto girare

Non è un'ottimizzazione: erano **rotte**, e il backend le chiamava lo stesso.
PostgreSQL non ri-valida i corpi delle funzioni quando qualcosa cambia sotto,
quindi non se n'era accorto nessuno.

### 1.1 🔴 `script.fn_search_stradario` — autocomplete vie

`apps/core/db/lookup_repository.py::search_stradario` →
`apps/core/api/views_lookup.py`.

**Prima:** ogni chiamata falliva con
`structure of query does not match function result type`. Ogni ricerca via
dell'operatore finiva lì.

**Ora funziona**, con **due differenze nel payload**:

| Campo | Prima (teorico) | Ora |
|---|---|---|
| `provincia_sigla` | `char(10)` → `'FM        '` | `text` → `'FM'` |
| `cap` | `char` | `text` → `'63815'` |

⚠️ **Il FE va guardato**: se qualcuno faceva `trim()` sulla sigla provincia, ora
è superfluo ma innocuo; se invece confrontava con una stringa paddata
(`'FM        ' === x`), adesso non combacia più. I nomi delle colonne non
cambiano, e il repository mappa per nome (`rows_to_list`): nessuna modifica
obbligatoria lato Python.

**Verificato sul DB dopo la riparazione:**

```
 stradario_id | toponimo | denominazione | provincia_sigla |  cap
--------------+----------+---------------+-----------------+-------
         3608 | CONTRADA | ROMANI        | FM              | 63815
```

ℹ️ Il suo pgTAP era rosso in `baseline-rossi.tsv` classificato `ERRORE_FIXTURE`.
Era una classificazione sbagliata: non la fixture, la funzione. Ora è 8/8 verde e
la riga è stata tolta dalla baseline.

### 1.2 🔴 `vendite.fn_prepare_sdi_payload` — passo di due pipeline attive

`apps/vendite/db/pipeline_repository.py::run_prepare_sdi_payload_lotto_task`,
task `prepare_sdi_payload_lotto` (registry id 9), montato sulle pipeline
**MASSIVO (id 5)** e **GIORNALIERO (id 7)**, entrambe con
`"force_new_tentativo": false`.

**Prima:** due difetti in serie. La funzione nominava la colonna `tentativo`
(che si chiama `tentativo_num`), e riparato quello il calcolo del numero di
tentativo dava **0** al primo giro con `force_new_tentativo=false` — cioè nella
configurazione in seed — violando `chk_fatture_sdi_tentativo_num CHECK (> 0)`.

**Ora**, verificato su un lotto reale (in transazione, poi rollback):

```
force=false, primo giro   -> tentativo_num = 1   (prima: 0, CHECK violato)
force=true,  secondo giro -> tentativo_num = 2
```

⚠️ **Cosa aspettarsi lato Python.** Il contratto di `SdiPayloadRow` non cambia
(stesse colonne, stesso ordine). Ma questo passo della pipeline **non è mai
riuscito**: se c'è codice a valle scritto sull'ipotesi che fallisse sempre — o
mai testato perché irraggiungibile — adesso viene esercitato per la prima volta.

ℹ️ Comportamento da conoscere, **non modificato** perché è preesistente e
sembra voluto: con `force_new_tentativo=false`, le fatture che hanno **già** una
riga `fatture_sdi` non vengono né aggiornate né **restituite**. Il payload
contiene solo le fatture al primo invio. Se serve il payload completo del lotto,
si chiama con `force_new_tentativo=true` (che però apre un tentativo nuovo).
Da decidere insieme se è il comportamento voluto.

⚠️ **Non esiste nessun pgTAP su questa funzione.** La copertura del passo SDI
vale zero. È nel piano DB, ma se il BE ha un test d'integrazione sulla pipeline
è il momento di includerlo.

---

## 2. Documentazione BE che promette presidi non più esistenti

Due punti dicono che un guard fa fail-fast. Quel guard **non esiste dal
2026-05-15**, e la funzione è stata droppata il 2026-08-04 (`20260804-51`).

### 2.1 `apps/vendite/db/contratti_repository.py:762`

```python
# Scopo: Cambia lo stato documentale del contratto. Il trigger
#        trgfn_contratti_guard_modalita_c_activation fa fail-fast
#        se modalita' C e righe incomplete.
def update_stato(self, contratto_id: int, stato_doc_contratto_id: int) -> bool:
```

Il trigger fu droppato da `20260515-10-alter-contratti-add-listino-versione-drop-modalita`,
che ha smontato il modello di pricing a modalità A/B/C. La logica sostitutiva
(Step 2.3) è in servizio: su `contratti` presidiano
`trgfn_contratti_guard_transizione_stato` e `trgfn_contratti_lock_post_attivazione`.

**Il commento va riscritto**, non tolto: dice la cosa giusta (c'è un fail-fast)
con il nome sbagliato. Un commento che nomina un presidio inesistente è peggio di
nessun commento — chi legge crede di avere una rete che non c'è.

### 2.2 `docs/it/backend/vendite/manual/api_contratti.md:935`

```
- `trgfn_contratti_righe_componenti_guard_pending` — immutabilita' componenti
```

Sostituita da `script.trgfn_componenti_guard_pending` (generico, `20260526-23`),
che **è** agganciato a `trg_contratti_righe_componenti_a10_guard_pending_upd`.
Il presidio c'è, cambia solo il nome. Il manuale del generico
(`docs/it/dbzero/script/manual/trgfn_componenti_guard_pending.md`) documenta già
la migrazione.

---

## 3. Funzioni droppate — nessuna era chiamata dal BE

Verificate in sei sedi (BE, FE, seed/registry, pgTAP, altre funzioni, repo
intero): **zero consumatori**. Elencate per completezza, nel caso qualcosa sia in
lavorazione su un branch non ancora integrato:

| Funzione | Perché |
|---|---|
| `vendite.fn_list_attivita_sorgenti_abilitate` | legge una tabella droppata il 2026-02-27 |
| `vendite.trgfn_attivita_fatturabili_lotti_gen_codice` | orfana, tabella inesistente |
| `vendite.trgfn_attivita_fatturabili_guard_fonte` | orfana dal 2025-10-26 (riuso del nome di trigger) |
| `vendite.trgfn_contratti_guard_modalita_c_activation` | trigger droppato dal refactor contratti |
| `vendite.trgfn_contratti_righe_guard_modalita_c` | idem |
| `vendite.trgfn_contratti_righe_componenti_guard_pending` | sostituita dal generico |

Rimossa anche la riga `lotti_attivita` da `config.sistema_codici` e la sequenza
`vendite.attivita_fatturabili_lotti_codice_seq`.

---

## 4. Tre pgTAP corretti (2026-08-04) — due erano verdi per il motivo sbagliato

Emersi misurando, non causati dalla bonifica. Corretti e verdi.

| Test | Perché era rosso | Correzione |
|---|---|---|
| `anagrafiche/test-fn-crea-auth-user` | asseriva il **codice** dentro il messaggio | asserisce SQLSTATE + il messaggio ottenuto da `fn_get_messaggio(<codice>)` |
| `script/test-fn-available-actions-preventivo-v1` | pretendeva 0 azioni su ACCETTATO | pretende l'insieme `["annulla"]` |
| `script/test-fn-available-actions-ordine-v1` | pretendeva `can_change_state=false` su CONFERMATO | pretende `true` + insieme `["annulla","push_commessa"]` |

Gli ultimi due erano semplicemente **rimasti indietro** rispetto al cantiere
*vie d'uscita per l'operatore* (`20260804-33/34/35`, applicato alle 13:25), che ha
riacceso le transizioni `→ ANNULLATO` su preventivi e ordini: dare all'operatore
una via d'uscita è lo scopo dichiarato di quel lavoro. In entrambi ora si
asserisce **l'insieme delle chiavi** e non il conteggio — `= 1` sarebbe passato
anche con l'azione sbagliata.

---

## 5. 🔴 Il codice errore di dominio non arriva al backend

Questo è il punto serio, ed è uscito indagando il primo di quei test.

`script.fn_log_and_raise_error` chiude così:

```sql
RAISE EXCEPTION '%', v_msg
    USING DETAIL = coalesce(v_detail, ''),
          HINT   = coalesce(v_hint, '');
```

**Nessun `ERRCODE`.** Lo SQLSTATE è quindi sempre `P0001`, `DETAIL` è la colonna
`causa` e `HINT` è `soluzione`. Il codice (`E_ADMIN_USERNAME_DUPLICATO`, …) **non
compare in nessuno dei tre**.

Lato Python, `ErrorTranslator._extract_app_error_code` lo cerca con una regex nel
testo del messaggio, e il commento dice:

```python
# Cerca codice errore applicativo nel messaggio DB (es. E_UTENTE_DISABILITATO).
# fn_log_and_raise_error include il codice nel RAISE EXCEPTION via fn_get_messaggio.
```

Quel commento **non è vero**. `script.fn_get_messaggio` include il codice solo nel
fallback, quando la riga manca dal seed:

```sql
IF tmpl IS NULL THEN
    RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
END IF;
```

Misurato sul DB: **0 su 635** messaggi `it` contengono il proprio codice, e
nemmeno `causa` o `soluzione` lo contengono.

### Cosa significa in pratica

Per ogni errore di dominio **correttamente seedato**, `_extract_app_error_code`
torna `None` e il translator ripiega su `code = "E_DATABASE"`. Il che vuol dire
che la mappa `apps/core/services/error_policies.py` — codice → HTTP status →
azione UI, centinaia di voci — **non scatta**.

⚠️ È un contratto invertito: funziona solo per gli errori a cui *manca* il
messaggio. Più il seed è completo, meno l'error handling funziona. E si degrada
in silenzio, un codice alla volta, ogni volta che qualcuno aggiunge una riga al
CSV dei messaggi.

### Cosa proponiamo (da decidere insieme, tocca DB e BE)

L'opzione pulita è far portare il codice all'eccezione stessa, così il BE smette
di fare parsing di testo:

```sql
RAISE EXCEPTION '%', v_msg
    USING ERRCODE = 'P0001',
          COLUMN  = p_error_code,   -- oppure un campo dedicato
          DETAIL  = ..., HINT = ...;
```

psycopg espone `diag.column_name`, quindi il translator leggerebbe un campo
strutturato invece di una regex. Alternative: un prefisso convenzionale nel
messaggio (semplice ma sporca la UI), oppure `SQLSTATE` custom della classe `U0`
(pulito ma richiede una mappa codice→sqlstate).

⚠️ Qualunque strada si prenda, tocca **una** funzione DB e **un** metodo Python,
ma cambia il comportamento di ogni errore dell'applicazione: va fatta come slice
a sé, con un pgTAP e un test Django che asseriscono il giro completo.

> **Risposta del BE (2026-08-05):**
> [brief-db-codice-errore-strutturato](../work-in-progress/brief-db-codice-errore-strutturato.md).
> Misurato sul percorso reale: il codice **arriva nel 91% dei casi**, non perché
> il DB lo mandi ma perché il driver allega lo statement chiamante, dove il
> codice è scritto come letterale. Si perde sui **9** call site che lo passano da
> variabile — le guard di cambio stato — e sui **76** che usano codici senza
> prefisso `E_`. Forma scelta: `CONSTRAINT = p_error_code` (round-trip verificato
> fino a `django.db.DatabaseError`, `str(exc)` invariato → il DB può andare per
> primo senza toccare il BE).

---

## 6. Riepilogo di cosa serve dal BE

| # | Cosa | Dove | Urgenza | Stato (BE, 2026-08-05) |
|---|---|---|---|---|
| 1 | 🔴 Decidere come far arrivare il codice errore al translator (§5) | `fn_log_and_raise_error` + `error_translator.py` | **alta** | ✅ analizzato e rilanciato al DB: [brief-db-codice-errore-strutturato](../work-in-progress/brief-db-codice-errore-strutturato.md) |
| 2 | Esercitare il passo SDI, che ora gira per la prima volta | pipeline MASSIVO/GIORNALIERO | **alta** | ⏸️ **sospeso** (decisione Tid). `vendite.fatture_sdi` ha **0 righe**: mai girato. Da ora le pipeline 5 e 7 ci scrivono, ma nessuno legge — il builder XML non esiste e l'executor scarta il valore di ritorno |
| 3 | Decidere se `force_new_tentativo=false` deve restituire anche le fatture già registrate | `fn_prepare_sdi_payload` | media | ✅ deciso: **no**. La semantica attuale è quella giusta per una pipeline (ciò che torna è ciò che va spedito). Il payload completo del lotto, se servirà, è una **funzione read-only separata** |
| 4 | Controllare il FE su `provincia_sigla` non più paddata | lookup vie | media | ✅ **niente da fare**: `StradarioAutocomplete` usa solo `indirizzo_normalizzato`, `useIndirizzoBase` solo `codice_postale_id`. Né `provincia_sigla` né `cap` sono letti |
| 5 | Riscrivere il commento a `contratti_repository.py:762` | contratti | bassa | ✅ fatto — più **due** occorrenze non censite a `contratti_repository.py:1057` |
| 6 | Correggere `api_contratti.md:935` | doc BE | bassa | ✅ fatto — anche `:934` (`trg_contratti_righe_propaga_qta_componenti` non esiste: è `trg_contratti_righe_z90_propaga_qta_componenti_upd`) |

⚠️ **Fuori lista, ma vivo**: la classe `FP_VARIADIC` del brief DB non è rumore —
**20 call site in 15 funzioni** chiamano `fn_log_and_raise_error`/`fn_log_error_only`
con 5 argomenti, e una funzione `VARIADIC text[]` non è chiamabile con zero
argomenti variadici (42883 a runtime, provato live). Dettaglio e censimento in
[brief-db-codice-errore-strutturato §8](../work-in-progress/brief-db-codice-errore-strutturato.md).
