# Brief BE → DB — il registro errori non sa nominare due terzi degli errori

> **Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** `config.messaggi_errore` non contiene **207 dei 360** codici che
> l'applicativo dichiara. Quando uno di quelli viene loggato, `dbops.error_log`
> registra la riga sotto `MESSAGGIO_NON_DEFINITO` e **il codice originale è
> perduto**: resta traccia che è successo qualcosa, non di *cosa*.
> **Cosa chiediamo:** un seed. La proposta SQL è già scritta, validata in
> rollback e idempotente:
> [`backend/scripts/db-proposals/PROPOSTA_seed_messaggi_errore_mancanti.sql`](../../../../backend/scripts/db-proposals/PROPOSTA_seed_messaggi_errore_mancanti.sql).
> **Correlati:** [Messaggi-di-Errore-e-Generazione-Log.md](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) ·
> [analisi-diagnostica-produzione-senza-accesso-db.md](analisi-diagnostica-produzione-senza-accesso-db.md) (Fase 0)

---

## 1. Il fatto, misurato

| | |
| --- | --- |
| codici in `config.messaggi_errore` | **373** |
| codici dichiarati in `apps/core/services/error_policies.py` | **360** |
| **dichiarati ma NON a catalogo** | **207** (57%) |
| righe di `dbops.error_log` già degradate a `MESSAGGIO_NON_DEFINITO` | **41.885 su 62.418** (67%) |

I 207 mancanti coprono tutte le famiglie del dominio, non un angolo:
`E_VENDITE` 18 · `E_UI` 16 · `E_PIPELINE` 13 · `E_AI` 8 · `E_PREV` 8 ·
`E_CATALOGO` 7 · `E_COMMESSA` 7 · `E_NOTA` 7 · `E_DOCUMENTI` 6 · `E_ORD` 6 ·
`E_TASK` 6 · `E_ANAG` 5 · `E_DDT` 5 …

## 2. Perché è più grave di un messaggio brutto

`script.fn_log_error_only` risolve il codice contro il catalogo; se non lo
trova ripiega su `MESSAGGIO_NON_DEFINITO` — e siccome `error_log` conserva
**`messaggio_errore_id`** (FK) e non il codice in chiaro, **quel ripiego è
distruttivo**: verificato sui dati, il `context` jsonb delle righe degradate
non contiene il codice originale.

```
context delle righe MESSAGGIO_NON_DEFINITO (ultime 3):
  {"field": "articolo_id", "value": "xxx"}
  {"uom_id": 0}
  {"ba_id": 100, "uom_id": 5, "utility_id": 7, "articolo_id": "019bac81-…"}
```

Non è quindi «il log è meno leggibile»: è che **41.885 errori registrati non
sono più attribuibili**, e nessuna analisi a posteriori potrà recuperarli. Ogni
giorno che passa la quota cresce.

> 💡 **Perché lo scopriamo ora.** Cercavamo tutt'altro: uno strumento per
> consultare i log di fatturazione (richiesta di Tid, 2026-08-03). Il primo
> sguardo al contenuto reale di `error_log` ha mostrato che il 67% delle righe
> non sa dire quale errore rappresenta — cioè che **costruire il visualizzatore
> prima di questo seed significherebbe costruire una finestra sul rumore**.

## 3. Cosa chiediamo

**Applicare il seed** dei 207 codici in `config.messaggi_errore`, lingua `it`.

La proposta è già pronta e **non è un elenco di codici da riempire a mano**:
il testo di ogni riga è il `user_message` che `error_policies.py` già
restituisce all'utente per quel codice. Non abbiamo inventato messaggi nuovi —
abbiamo portato nel catalogo quelli che l'API pronuncia da sempre, così che
anche il log possa nominarli. Nessuno dei 207 era privo di `user_message`.

```sql
INSERT INTO config.messaggi_errore (codice, lingua, messaggio) VALUES
    ('E_ADMIN_EMAIL_DUPLICATA', 'it', 'Email gia'' in uso.'),
    ('E_AI_TOOL_DENIED', 'it', 'Non hai i permessi per questo strumento AI.'),
    …  -- 207 righe
ON CONFLICT (codice, lingua) DO NOTHING;
```

✅ **Validato in transazione con rollback** sul DB di sviluppo:
374 → 581 righe (207 inserite), **secondo giro idempotente** (581 → 581),
nessun vincolo violato (`uq_messaggi_errore_codice_lingua` regge).

`causa` e `soluzione` restano **NULL** di proposito: sono campi di diagnosi
che meritano di essere scritti con calma e con la vostra conoscenza del
modello, non dedotti da noi in blocco.

## 4. Due decisioni che lasciamo a voi

| # | Questione | La nostra opinione |
| --- | --- | --- |
| **4.1** | **Lingua `en`.** Il catalogo ha `it` e `en`; noi proponiamo solo `it`. | Non bloccante: `fn_get_messaggio` fa cascata con fallback `it`. L'`en` può seguire quando serve davvero — meglio 207 righe italiane oggi che 414 righe di cui metà tradotte male |
| **4.2** | **Come evitare che si riapra.** Oggi nulla impedisce di aggiungere un codice a `error_policies.py` e dimenticarlo a catalogo — è così che siamo arrivati a 207. | Un **check CI** che confronti i due insiemi e fallisca sui nuovi disallineati. Lo scriviamo noi lato BE (gira senza DB, stesso stile di `test_transaction_atomicity_guardrail`) se siete d'accordo sul principio. Da valutare se far fallire solo sui codici NUOVI o su tutti (col seed applicato la distinzione sparisce) |

## 5. Cosa NON chiediamo

| Cosa | Perché no |
| --- | --- |
| Bonificare le 41.885 righe già degradate | Il codice originale **non è recuperabile**: non è nel `context`. Riscriverle significherebbe inventare. Restano come sono, e il seed ferma l'emorragia da qui in avanti |
| Cambiare `fn_log_error_only` perché salvi il codice in chiaro | Sarebbe una modifica di modello sensata (un `codice_originale text` accanto alla FK renderebbe il ripiego non distruttivo), ma è **un'altra discussione**: il seed la rende molto meno urgente, e non vogliamo accoppiare le due cose. Se la ritenete interessante, apriamola separatamente |
| Toccare `error_policies.py` | È il registro applicativo, resta nostro |

## 6. Un difetto nostro che questo seed chiude

`E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA` è nato **oggi** (dashboard
competenza, traccia del fallimento della previsione fatture) e l'abbiamo
registrato in `error_policies.py` **senza accorgerci che il catalogo DB è un
secondo registro da alimentare**. Sarebbe finito anch'esso in
`MESSAGGIO_NON_DEFINITO` al primo guasto — cioè la traccia che avevamo appena
aggiunto per non perdere l'informazione l'avrebbe persa comunque.

È nell'elenco dei 207, ed è anche il motivo per cui proponiamo il check di
§4.2: la disciplina da sola non ha retto 207 volte, non reggerà la 208ª.

## 7. Definizione di «fatto»

1. `config.messaggi_errore` contiene i 207 codici in lingua `it`;
2. un errore applicativo di un codice prima mancante compare in
   `dbops.error_log` **col proprio codice**, non con `MESSAGGIO_NON_DEFINITO`
   (controprova diretta: sollevare `E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA`
   e rileggere l'ultima riga del registro);
3. la quota di righe degradate **smette di crescere** (le vecchie restano);
4. deciso il §4.2 — con o senza check CI, ma deciso.

---

## 8. Nota operativa

Il seed va **committato** per avere effetto sul logging: `fn_log_error_only`
scrive via `dblink` su una connessione separata, che non vede una transazione
non ancora conclusa. È il motivo per cui la nostra validazione in rollback ha
potuto verificare l'INSERT e l'idempotenza, ma **non** la controprova del
punto 7.2 — quella si fa dopo l'apply, ed è una riga.
