## Documentazione Concettuale -- Tabella `config.email_log`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_account](/dbzero/config/tabelle/email_account)
> [config.email_template](/dbzero/config/tabelle/email_template)
> [config.email_outbox](/dbzero/config/tabelle/email_outbox)
> [config.email_allegato](/dbzero/config/tabelle/email_allegato)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---

### 🎯 Scopo Principale

La tabella `config.email_log` registra **ogni email che il sistema ha provato a mandare**, conservando il corpo esattamente come inviato (dopo eventuali modifiche manuali dall'outbox), lo stato di invio, il contesto e l'ambito di visibilita'.

⚠️ «Provato a mandare», non «inviata»: la distinzione e' il senso della colonna `stato`, e fino al 2026-09-11 la tabella non sapeva farla — vedi `SIMULATA` qui sotto.

---

### Ciclo di vita (stato)

```
PENDING → SENT      (invio riuscito)
PENDING → FAILED    (invio fallito)
PENDING → SIMULATA  (invio NON tentato, di proposito — terminale)
FAILED  → RETRY     (tentativo successivo schedulato)
RETRY   → SENT      (retry riuscito)
RETRY   → FAILED    (retry fallito, tentativi < max_tentativi → nuova RETRY)
```

Il management command `send_pending_emails` ripesca le email in `PENDING`, e quelle in `FAILED` o `RETRY` finche' `tentativi < max_tentativi`.

⚠️ **Che ripeschi anche i `FAILED` non e' un dettaglio: e' il recupero.** Se l'SMTP viene configurato entro i tre tentativi di default, la mail parte da sola. Il `tentativi + 1` lo scrivono entrambe le strade dell'esito — l'`UPDATE` diretto e `config.fn_chiudi_email_sistema` — quindi la riga si ferma da se'.
⛔ Questa riga diceva «processa le email PENDING e RETRY» e **ometteva i `FAILED`**: era sbagliata, e la stessa omissione stava nel commento in testa al command, da dove si e' propagata al codice del backend. *Un commento non e' una fonte.* Corretta il 2026-09-11.

#### ⭐ `SIMULATA` — «non ho nemmeno provato», e non e' un guasto

Introdotto il 2026-09-11 (changeSet `20260911-06`). Dice che l'invio **non e' stato tentato, di proposito**: un ambiente di sviluppo gira senza SMTP e la mail viene mostrata a chi sviluppa invece che spedita.

⛔ **Prima quel ramo scriveva `SENT`**, cioe' affermava una consegna mai avvenuta. Il giornale diceva «inviata», la prova di connessione rispondeva OK, e nessun presidio guardava oltre lo stato: l'unico modo di accorgersene era non veder arrivare la posta.

Perche' non uno dei quattro che c'erano gia':

| Valore | Perche' no |
| --- | --- |
| `SENT` | afferma una consegna che non c'e' stata — e' il difetto |
| `FAILED` | afferma un guasto che non c'e': in sviluppo il comportamento e' **voluto**, e riempire di rossi finti un ambiente insegna a ignorare i rossi |
| `PENDING` / `RETRY` | la rimetterebbero in coda senza fine |

⚠️ `SIMULATA` e' **terminale**: non compare fra gli stati che `send_pending_emails` ripesca, quindi nessuno la riprende in mano. E la riga **non porta `inviato_at`**: quella colonna data una consegna, e valorizzarla sposterebbe la bugia di una casella invece di toglierla. Il momento c'e' gia' in `data_insert`.

#### 🔵 Il vocabolario ha DUE sedi, e chi ne aggiunge una deve toccarle entrambe

| Sede | Che cosa contiene |
| --- | --- |
| `CHECK chk_email_log_stato` | tutti i valori ammessi sulla colonna |
| whitelist di `p_stato` in `config.fn_chiudi_email_sistema` | gli stessi, **meno `PENDING`** |

⛔ Non e' una ridondanza da sanare: quella funzione **chiude** e non rimette in coda, quindi `PENDING` ne e' escluso di proposito. L'invariante e' `whitelist = CHECK \ {PENDING}`, ed e' l'unica forma sensata — scritta come uguaglianza sarebbe sbagliata.

⚠️ **E la seconda sede non e' aggirabile**: `EmailRepository.update_log_stato` instrada su quella funzione **ogni** chiusura di ambito `SISTEMA` — digest dei presidi e reset password — perche' la row level security rifiuta l'`UPDATE` diretto. Un valore aggiunto al solo `CHECK` resterebbe irraggiungibile proprio per quelle righe.

⇒ Lo presidia `db/pgtap/config/test-fn-email-sistema.sql`, test 9. Il mirror lato backend (`email_constants.STATI_EMAIL_LOG`) ha un presidio suo, `core/tests/db/test_email_log_stati_guardrail.py`.

---

### Ambito di visibilita'

Ogni email ha un `ambito` che determina chi puo' consultarla:

| Ambito      | Visibilita'                                                |
| ----------- | ---------------------------------------------------------- |
| `SISTEMA`   | Solo admin (email transazionali: inviti, reset, notifiche) |
| `REPARTO`   | Tutti gli operatori dell'unita' organizzativa + admin      |
| `OPERATORE` | Solo l'operatore che l'ha creata + admin                   |

Le email con `pratica_id` valorizzato sono inoltre visibili dalla scheda pratica, indipendentemente dall'ambito.

**Chi applica la regola.** La applica il database, con la policy `rls_email_log_ambito`. La regola sta in una funzione sola, [`script.fn_scope_email_ambito`](/dbzero/script/funzioni/fn_scope_email_ambito), la stessa delle bozze:

* «admin» è il **super admin**;
* «chi l'ha creata» è la colonna **`creato_da_user_id`**. ⚠️ Non è `auth_user_id`, che è l'utente di cui la mail *parla*: l'operatore invitato, l'utente del reset password;
* sulle mail `REPARTO` e `OPERATORE` l'azienda (`emittente_fiscale_id`) deve essere anche nel perimetro di chi guarda: una mail di un'azienda che non si ha più in carico non si vede, nemmeno se la si è scritta;
* il processo che spedisce la posta (`send_pending_emails`) vede le mail di ogni ambito, perché deve ritentarle. Sulle mail `REPARTO` e `OPERATORE` vede solo quelle delle aziende che segue;
* una mail `REPARTO` deve indicare il reparto e una `OPERATORE` il suo autore: lo impongono due vincoli. Senza quella colonna la mail non la vedrebbe nessuno.

⚠️ La regola della scheda pratica, qui sopra, **non è ancora applicata** dal database: si scriverà insieme alla scheda pratica.

---

### Corpo inviato fedele

I campi `corpo_inviato_html` e `corpo_inviato_testo` conservano il testo **esattamente come inviato**. Questo e' diverso dal ri-renderizzare il template con le variabili originali (`contesto_json`): se l'operatore ha modificato il testo nell'outbox prima di inviare, il log riflette le modifiche.

---

### Collegamento a pratica

Il campo `pratica_id` collega l'email a una pratica. Dalla scheda pratica (tab "Comunicazioni") si vedono tutte le email inviate nel suo contesto, ricostruendo la storia comunicativa.

---

### Collegamento a outbox

Il campo `email_outbox_id` collega il log alla bozza che lo ha generato (se l'invio e' passato dall'outbox). Per invii diretti (senza anteprima, es. reset password self-service) il campo e' NULL.

---

### Indici principali

* `(stato, prossimo_tentativo)` -- per il command di retry
* `(ambito, unita_organizzativa_id)` -- per filtro reparto
* `pratica_id` -- per consultazione dalla pratica
* `auth_user_id` -- per filtro operatore destinatario
