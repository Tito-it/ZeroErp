# Brief DB — i due **scrittori** che mancano al giro: `task_runs` e `commesse_push_log`

> **Cos'è.** Una richiesta del backend al team DB, non un disegno nuovo. Le
> decisioni sono già prese e sono **D-3** e **D-7** di
> [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md);
> qui si chiede l'unico pezzo che manca per realizzarle.
>
> **In una riga.** I changeSet **61** e **62** hanno consegnato le **colonne**
> (`correlation_id` su `fatturazione_lotti_task_runs`, `correlation_id` + `tx_id`
> + lo stato `IN_ESECUZIONE` su `commesse_push_log`). ⛔ **Nessuna funzione le
> scrive**, e il BE non può scriverle da sé senza aggirare le funzioni che
> possiedono quelle tabelle.
>
> **Chi scrive.** Backend (dev/backend-tid), 2026-08-22, misurato su `pg_proc`
> del DB di sviluppo dopo l'applicazione di L1+L4+L2.
>
> **Stato del resto.** Le consegne BE **BE-1, BE-3a, BE-4, BE-5, BE-6, BE-7,
> BE-9** sono **fatte**. Restano ferme **BE-2** e **BE-3b**, che sono
> esattamente le due che dipendono da questo brief.

---

## 1. La misura

Verificato con `pg_get_function_identity_arguments` sul database vivo, non
sugli YAML.

| Oggetto | Cosa gli serve | Stato |
| --- | --- | --- |
| `vendite.fn_start_lotto_task_run` | scrivere `correlation_id` | ⛔ nessun parametro: `(p_lotto_id, p_pipeline_id, p_stato_doc_fiscale_id, p_task_code, p_fase, p_meta)` |
| `vendite.fn_log_commessa_push_run` | aprire un giro `IN_ESECUZIONE`, e chiuderlo | ⛔ **rifiuta esplicitamente** `IN_ESECUZIONE`, nessun `p_correlation_id`, e non esiste nessuna funzione che chiuda un giro aperto |

Il rifiuto non è implicito: è un guard scritto nel corpo, e solleva.

```sql
IF v_stato NOT IN ('COMPLETATO', 'PARZIALE', 'ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(..., 'E_PARAMETRO_INVALIDO', ...,
        concat('p_stato=', v_stato, ' (ammessi: COMPLETATO, PARZIALE, ERRORE)'));
END IF;
```

⭐ **Il changeSet 62 ha allargato il `CHECK` a quattro valori, ma la funzione
che scrive quella colonna ha un guard suo e non lo sa.** È il caso in cui il
vincolo di tabella e la funzione che ci scrive dicono due cose diverse: passa la
migrazione, e a fallire è la prima scrittura.

---

## 2. Cosa si chiede

### 2.1 `fn_start_lotto_task_run` — un parametro

`p_correlation_id uuid DEFAULT NULL`, scritto nella colonna omonima. Nient'altro
cambia: né la `RETURNS TABLE`, né il calcolo del `tentativo`.

⚠️ **Con `DEFAULT NULL` in coda non serve un `DROP` della firma vecchia** e non
nasce nessun overload ambiguo, perché nessun chiamante passa argomenti
posizionali oltre il sesto. È la differenza con `fn_log_event`, che di parametri
ne **toglieva**.

### 2.2 `commesse_push_log` — la coppia apri/chiudi

⭐ **La proposta è di seguire il pattern che questa casa ha già**, cioè quello
dei `task_runs` — `fn_start_lotto_task_run` / `fn_complete_lotto_task_run` /
`fn_fail_lotto_task_run` — e non di allargare la funzione esistente:

| Funzione | Cosa fa |
| --- | --- |
| `fn_start_commessa_push_run(p_dry_run, p_source_types, p_correlation_id)` | `INSERT` della riga in testa, stato **`IN_ESECUZIONE`**, `run_at = now()`. Ritorna l'`id` |
| `fn_close_commessa_push_run(p_id, p_stato, p_risultato, p_durata_ms, p_source_types)` | `UPDATE` della riga aperta: stato finale, risultato, durata |

⛔ **E `fn_log_commessa_push_run` si toglie.** Con la riga che nasce in testa,
«inserisci un giro già finito» non è più un'operazione che esiste: lasciarla
sarebbe una seconda porta sulla stessa tabella, che scrive righe senza
`correlation_id` e senza passare dallo stato aperto. Non siamo in produzione
([memoria](../../../.codex/AGENTS.md), e la decisione D-4 dello stesso cantiere
ha già azzerato `event_log`): il `DROP` è la risposta pulita, e il BE adegua il
proprio repository nello stesso giro.

⚠️ **Due guard che valgono la pena di essere scritti**, perché sono i due modi
in cui questa coppia si romperebbe in silenzio:

1. **`fn_close_...` non deve accettare `IN_ESECUZIONE`** come stato finale: un
   giro «chiuso in esecuzione» è una riga che nessuno riaprirà mai e che i
   conteggi leggeranno come aperta per sempre.
2. **`fn_close_...` su una riga che non è `IN_ESECUZIONE`** è una doppia
   chiusura, e va rifiutata: significa che il chiamante ha perso il filo del
   proprio giro.

⭐ Sul **codice errore** di quei due rifiuti vale il criterio di
`.codex/AGENTS.md`: il dato lo fornisce solo un **chiamante rotto**, non una
persona in un form ⇒ classe **`TECNICO`**, messaggio che nomina il parametro,
e ⛔ **non** si riusa `E_PARAMETRO_INVALIDO` (è un debito, non una sede). Il
precedente è `E_VENDITE_PRICING_ESITO_ASSENTE`.

---

## 3. Cosa fa il BE quando arrivano

Nessuna sorpresa: è già scritto nel §5 dell'altro brief.

| | Consegna | Cosa diventa |
| --- | --- | --- |
| **BE-2** | il `correlation_id` del giro | il runner genera **un `uuid` nuovo a ogni giro** (oggi passa `lock_batch_id`, che nasce col lotto e **non cambia mai**: due corse dello stesso lotto sono indistinguibili) e lo scrive su eventi, `task_runs` e `commesse_push_log` |
| **BE-3b** | la riga del giro in testa | `CommessaPushOrchestrator._run_locked` apre il giro **prima** di eseguire gli handler e lo chiude alla fine |

⭐ **E il guadagno che non era nel piano**: un push **interrotto** oggi non
lascia traccia — muore e sparisce. Con la riga aperta in testa, quella rimasta a
`IN_ESECUZIONE` è l'unica prova che qualcosa è partito e non è tornato.

⚠️ **Con un limite da dire adesso, perché varrà solo per metà.**
`pr_run_commesse_push_one` (il push singolo dal drawer) avvolge tutto il giro in
una `transaction.atomic()` esterna, con semantica **all-or-nothing**: lì la riga
`IN_ESECUZIONE` viene rollata insieme al resto, e di un giro fallito non resta
niente. Il guadagno vale sul **batch**, che gira in autocommit. Non è un difetto
da correggere qui — è il prezzo dell'all-or-nothing, ed è giusto che sia scritto
prima che qualcuno lo scopra cercandolo.

---

## 4. Due cose viste misurando, che non sono richieste

Nessuna delle due blocca il BE. Si segnalano perché sono state misurate e
sarebbe peggio tacerle.

### 4.1 ⚠️ Il `tx_id` non è attaccato a nessuna delle due tabelle

Su questo database, `event_log` e `commesse_push_log` hanno la **colonna**
`tx_id` ma **nessun trigger** che la riempia:

```
vendite.event_log          trg_..._a10_deriva_scope_ins · trg_..._append_only_ud · trg_..._audit_data_user_upd
vendite.commesse_push_log  trg_..._audit_data_user_upd
```

È coerente con quanto il changeSet 62 dichiara — l'automazione
`dbops.fn_run_automations_tx_id` gira in `ci_apply`, e su un migrate manuale
arriva col pgagent la sera. ⭐ Ma vuol dire che **oggi la D-5 non è viva**: il
`tx_id` esiste come colonna e vale `NULL` su ogni riga, quindi `event_log` non si
aggancia ancora a `error_log`, che era la ragione per cui D-5 «non era
rinviabile». Da verificare dopo il prossimo `ci_apply`, non da rifare.

### 4.2 Verificato che il resto della riga si compone da sé

Provato in transazione con `system_process_context`, chiamando il repository
**vero** del backend (non un mock):

```
LOTTO 6260    → emittente_soggetto_ruolo_id = 72 · cleanup_at = 2028-09-10 · severity INFO
COMMESSA 15370 → emittente_soggetto_ruolo_id = 72 · severity WARN
```

⭐ Il perimetro lo deriva il trigger, la scadenza sono i **750 giorni** della
D-13 (2026-08-22 + 750 = 2028-09-10, torna), e `auth_user_id` resta `NULL` sul
canale batch — che è corretto: lì non c'è un `app.current_user_id`, e «chi» lo
dice `user_insert`.

---

## 5. Registro

### 2026-08-22 · Nascita

Scritto dal backend dopo aver applicato le sette consegne che non dipendevano
dal DB. Il brief nasce da una misura, non da una lettura del piano: le due
funzioni sono state interrogate su `pg_proc`, e il guard di
`fn_log_commessa_push_run` è stato letto nel corpo vivo.

⭐ **Il rilievo che ha dato forma alla richiesta** è che il changeSet 62 aveva
fatto la metà giusta del lavoro — allargare il `CHECK` — e che la metà mancante
non era visibile da lì: un vincolo di tabella e una funzione che ci scrive
possono dissentire, e il migrate passa lo stesso.
