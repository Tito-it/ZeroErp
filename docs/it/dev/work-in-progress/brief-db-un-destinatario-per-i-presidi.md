# Brief DB — Un destinatario per i presidi

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-09. **A chi:** team DB.
> **Origine:** `migliorie-generali-BE-FE-da-test-valutazione.md` §3 D13-bis, e
> §3 D10 del gemello sul DB (*«i presidi non hanno un destinatario»*).
>
> **In una riga:** trenta viste di presidio in `dbops` fanno il loro mestiere e
> non le legge nessuno; il backend può costruire il digest che le porta davanti
> a una persona, ma **non può decidere da solo quali righe siano un allarme** —
> e quella classificazione è un dato, non un elenco in Python.
>
> ⇒ **Servono due cose dal DB** (§4). La prima è una riga sola; la seconda è la
> parte che conta, e non è lavoro meccanico: è una **decisione per vista**.
>
> ⛔ **Il backend si ferma qui e aspetta**, come da regola: BE/FE solo con
> prerequisiti DB pronti. Ciò che il backend farà appena arrivano è scritto al §5,
> così il lavoro parte lo stesso giorno.

---

## 1. Come è nato — e non è un'ipotesi

Il 2026-09-09 il job `CHIUSURA_SCADENZE` risultava fallito **quattro notti
consecutive** (5, 6, 7 e 8 settembre), due esecuzioni per notte, tentativi
esauriti, tutte con lo stesso errore Python. Il difetto era una riga sola ed è
stato corretto in giornata (D13: `dict(riga[0])` su un `jsonb` che il driver
consegna come `str`).

⛔ **Ma la correzione non è la lezione.** Le otto righe stavano in
`dbops.vw_coda_lavori_**da_guardare**` — una vista che porta nel nome ciò che
serviva — e sono rimaste lì quattro notti. Il presidio ha funzionato
perfettamente: *guardare non è di nessuno*.

⚠️ E il conto **cresceva mentre si scriveva il documento**: sei righe la mattina,
otto la sera. È un fatto datato, non un argomento — l'argomento sta sul modello,
ed è che un presidio senza destinatario non presidia: produce una riga che
nessun processo è incaricato di leggere.

---

## 2. Il censimento — e perché cambia la forma del rimedio

> ⚠️ Lettura del **2026-09-09** sul database di sviluppo. Fatto datato: serve a
> dire *«questo caso esiste ed è gestito male»*, non a decidere la forma.

| | |
| --- | --- |
| Viste `dbops.vw_*` | **31** |
| Con un `COMMENT` che ne spiega lo scopo | **30 su 31** ⭐ |
| Non vuote in questo momento | **14** |

⛔ **E qui il rimedio ovvio si rompe.** «Manda un digest delle viste non vuote»
produrrebbe, oggi, un messaggio che si apre con **2.035 righe di
`vw_trigger_functions`** — che non è un allarme: è l'inventario dei trigger. Lo
stesso vale per `vw_function_list` (282), `vw_catalogo_oggetti` (173),
`vw_processi_programmazione` (21), `vw_processi_roster` (8).

⇒ Delle 14 non vuote, quelle la cui non-vuotezza **significa qualcosa** sono
poche, e non sono nemmeno tutte dello stesso tipo:

| Vista | Righe | Che cosa significa il numero |
| --- | --- | --- |
| `vw_coda_lavori_da_guardare` | 8 → **0** (archiviate il 2026-09-09) | 🔴 **qualunque riga è un allarme**: un lavoro è fallito adesso |
| `vw_processi_dominio_senza_identita` · `_senza_emittente` · `_senza_difesa` | **0** | 🔴 devono **restare** a zero: una riga è un invariante rotto |
| `vw_codici_errore_da_dichiarare` | 508 | 🟠 **registro di debito**: conta solo se **cresce** |
| `vw_fk_con_indice_missing_policy` | 57 | 🟠 idem |
| `vw_indici_ridondanti_prefisso` | 1 | 🟠 idem |
| `vw_processi_che_bypassano` | 1 | ⭐ **debito dichiarato**, con motivo e data di ritiro (fase 6-bis). È la riga fatta bene, ed è il modello |
| `vw_trigger_functions`, `vw_function_list`, `vw_catalogo_oggetti`, … | 2.035 · 282 · 173 · … | ⚪ **inventari**: non stanno in un digest, mai |

⭐ **Tre nature diverse, e nessuna è deducibile dal nome.** Un digest che non le
distingue è rumore, e un digest rumoroso viene ignorato al secondo invio — cioè
finisce come il presidio che voleva salvare.

---

## 3. ⛔ Perché il backend non può decidere da sé

La strada corta sarebbe un elenco in Python: *«queste sei viste sono allarmi,
queste tre sono registri, le altre no»*.

⛔ **Sarebbe una seconda sorgente di verità**, e diverge il giorno stesso in cui
il team DB aggiunge la trentaduesima vista: il presidio nuovo nascerebbe **fuori
dal digest**, in silenzio, e nessuno se ne accorgerebbe — che è, alla lettera, lo
stesso guasto che questo brief cerca di chiudere.

⭐ **Il precedente giusto è già nel progetto**: la configurazione delle liste è
**dato e non DDL** (`ui.lista_definizione` + `ui.lista_colonna`), e per la stessa
ragione — perché chi la cambia non deve toccare codice, e perché una sola sede
non può divergere da sé stessa.

⚠️ E la conoscenza sta dalla parte del DB, non del backend: **chi ha scritto la
vista sa se una sua riga è un allarme o un debito**. I 30 `COMMENT` su 31
dimostrano che quel sapere è già scritto — in prosa, cioè in una forma che nessun
programma può leggere.

---

## 4. 🔵 Che cosa serve

### 4.1 — Il catalogo dei presidi (la parte che conta)

Una tabella di configurazione — nome proposto `dbops.presidi`, seed in `80_data`
con il suo mirror CSV — che dica, **per vista**:

| Colonna | Che cosa porta |
| --- | --- |
| `vista` | nome qualificato (`dbops.vw_coda_lavori_da_guardare`) |
| `natura` | `ZERO` · `SOGLIA` · `INVENTARIO` — le tre del §2 |
| `soglia` | solo per `SOGLIA`: il valore **da cui non si deve salire**. `NULL` per le altre |
| `destinatario` | a chi arriva. ⚠️ Può essere lo stesso per tutte all'inizio: il campo serve perché non lo sia per sempre |
| `attivo` | per spegnere una riga senza cancellarla |
| `nota` | **il motivo**, e su una `SOGLIA` anche la data di ritiro |

⭐ **`natura` e `soglia` insieme fanno la cosa importante**: su un registro di
debito l'allarme non è «ci sono 508 righe» — quello si sa — ma **«sono
diventate 509»**. Un digest che ripete ogni giorno un numero che non cambia è il
modo più rapido per farsi ignorare.

⭐ **Il modello di come si compila una riga `SOGLIA` esiste già**, ed è
`vw_processi_che_bypassano`: una voce, con il motivo e il momento in cui sparisce.
Le altre tre (508, 57, 1) hanno un numero e non hanno un verso.

⚠️ **Non chiediamo di sanare i registri**: chiediamo di **dichiararli**. Portarli
a zero è un'altra decisione, e sta nel documento di valutazione (D10/D11).

⛔ **La riga `INVENTARIO` non è di scarto, ed è meglio dichiararla che ometterla**:
se una vista manca dal catalogo non si sa se è un inventario o una dimenticanza.
⇒ Proposta: un pgTAP che asserisce **ogni** `dbops.vw_*` presente in `dbops.presidi`
— così la trentaduesima vista non può nascere fuori dal digest.

### 4.2 — Una riga in `dbops.processi`

Perché il digest possa registrare il proprio giro su `maintenance.job_run_log`:
`registered_job` scrive `processo_codice` con **FK dura** verso `dbops.processi`,
e `backend/deploy/sveglie.json` pretende quel codice per installare l'unit.

| Campo | Valore proposto | Perché |
| --- | --- | --- |
| `codice` | `digest_presidi` | |
| `classe` | `MANUTENZIONE` | come `draina_coda_lavori`: non è un processo di dominio |
| `canale` | `COMMAND` | lo sveglia un timer systemd, non la coda |
| `attivo` | `true` | |

⭐ **`MANUTENZIONE` e non `DOMINIO` semplifica la richiesta**: le tre viste
`vw_processi_**dominio**_senza_identita` / `_senza_emittente` / `_senza_difesa`
guardano i soli processi di dominio, quindi **non servono né identità né
emittente** — il digest legge `dbops`, non dati di un'azienda. ⇒ È una riga, non
una terna.

⚠️ **E non serve nessun tipo di coda**: il digest **non** passa da
`dbops.coda_lavori`. Un lavoro di coda vuole identità, perimetro, ritentativi e
idempotenza; questo è una lettura periodica che non scrive niente nel dominio.
Metterlo in coda importerebbe quattro meccanismi per non usarne nessuno.

---

## 5. Che cosa fa il backend appena arrivano

Niente di questo richiede altro dal DB, ed è scritto qui perché possa partire lo
stesso giorno:

1. `apps/core/services/presidi_digest.py` — legge `dbops.presidi`, interroga ogni
   vista attiva, e produce **tre elenchi**: allarmi (`ZERO` con righe), registri
   **cresciuti** oltre soglia, registri stabili (una riga di riepilogo, non
   l'elenco).
2. `manage.py digest_presidi` — il management command, con `registered_job` sul
   `processo_codice` del §4.2. ⭐ Lanciabile a mano da subito: un digest che si
   può guardare quando si vuole è già meglio di niente.
3. `--secco` / invio: il corpo via `config.fn_accoda_email_sistema(
   p_destinatario, p_oggetto, p_corpo_html, p_corpo_testo, …)`, che esiste già.
4. Una voce in `backend/deploy/sveglie.json` + la coppia di template in
   `deploy/systemd/` — *«Aggiungere una sveglia = una voce qui + la coppia di
   template. Niente altro»*, e gli unit sono validati in CI dal job
   `validate-deploy`.
5. Il test della **forma**: che un registro stabile **non** produca un invio.
   ⚠️ È la prova che conta, perché è la sola che impedisce al digest di diventare
   la posta che si archivia senza aprire.

⚠️ **Cadenza da decidere insieme**, ed è una scelta di merito: quotidiana per gli
allarmi `ZERO` (un lavoro fallito stanotte va visto stamattina), settimanale per
i registri (un debito non cambia in un giorno). Due sveglie sullo stesso
processo sono già ammesse — `run_fatturazione_batch` ne ha due.

---

## 6. Cosa NON stiamo chiedendo

* ⛔ **Di sanare i registri di debito.** 508 codici da dichiarare, 57 FK senza
  indice: quelli hanno una loro sede (D10/D11 del documento di valutazione). Qui
  si chiede solo di **dire quale numero è quello da non superare**.
* ⛔ **Un tipo di coda nuovo.** Vedi §4.2: sarebbe la sede sbagliata.
* ⛔ **Di cambiare le viste.** Nessuna delle 31 va toccata: sono già scritte bene,
  e 30 su 31 spiegano già in prosa quello che il catalogo renderà leggibile a un
  programma.
* ⚠️ **Un destinatario per vista, subito.** Il campo serve, il valore può essere
  lo stesso per tutte al primo giro.

---

---

## 7. 🔵 Risposta DB — consegnato il 2026-09-10

> **Chi risponde:** team DB (`dev/db-tid`). **Stato:** ✅ **applicato su dbdev il
> 2026-09-10 alle 15:44** (changeSet `20260910-05`, `-06`, `-07`, `-08`, tutti
> `EXECUTED`). pgTAP **11/11**, `pgtap-baseline.sh dbops` **0 rossi su 33,
> nessuna regressione**.
>
> **In una riga:** il catalogo c'è, e le due decisioni di merito sono state prese
> diversamente da come il §4.1 le proponeva. **Il §5 può partire adesso.**
>
> ⚠️ **Una cosa da sapere prima di leggere `data_update` o `tx_id`:** la tabella
> è nata dopo l'ultima corsa delle automazioni, quindi al 2026-09-10 non ha
> ancora i trigger di audit, `tx_id` e storico — li genera `ci_apply`, cioè il
> job pgAgent della sera. Fino ad allora `tx_id` resta `NULL` e `data_update` non
> si aggiorna da sola. Non è un difetto: è lo stato dichiarato di ogni tabella
> nuova, ed è il motivo per cui nessun changeSet di questo giro nomina quei
> trigger.

### 7.1 Che cosa trova il backend

| Oggetto | File |
| --- | --- |
| `dbops.presidi` (tabella) | `00_schema/dbops/20260910-05-create-presidi-mctit.yaml` |
| `dbops.fn_conta_presidio(text)` | `20_code/dbops/20260910-06-create-fn-conta-presidio-mctit.yaml` |
| `COMMENT` su `vw_trigger_functions` | `20_code/dbops/20260910-07-comment-vw-trigger-functions-mctit.yaml` |
| `E_PRESIDIO_NON_A_CATALOGO` (TECNICO, 500) | append a `codici_errore.csv` + `messaggi_errore.csv` (id 1060) |
| Seed: **32 righe** | `80_data/sql/dbops/presidi.csv` + `20260910-08-upsert-dbops-presidi-mctit.yaml` |
| Riga `digest_presidi` | append a `80_data/sql/dbops/processi.csv` (id 26, `MANUTENZIONE`/`COMMAND`) |
| Presidio, nei due versi | `db/pgtap/dbops/test-catalogo-presidi-v1.sql` (plan 10) |
| Doc manuale | `dbzero/dbops/manual/presidi.md`, `manual/fn_conta_presidio.md` |
| Il meccanismo condiviso | `guide/presidi-e-registri-del-debito.md` **§2-bis** — è lì che il catalogo è descritto; il resto ci rimanda |

Colonne di `dbops.presidi`: `vista` · `natura` · `colonna_stato` · `stato_atteso`
· `registro` · `presidiato_da` · `cadenza` · `perimetro` · `attivo` ·
`obsoleto_dal` · `nota`.

### 7.2 ⛔ Niente colonna `soglia`: il debito si tiene con un registro

Decisione di Tid, 2026-09-10. Un intero vede solo il **delta del conteggio** ed è
cieco sullo **scambio**: un debito saldato e un difetto nuovo comparsi lo stesso
giorno lasciano il numero fermo, e il presidio tace.

⭐ E il caso non è di scuola: è **`vw_processi_che_bypassano`**, che il §4.1 porta
come *«la riga fatta bene, ed è il modello»*. Alla fase 6-bis il debito dichiarato
si ritira; se nello stesso giro un ruolo applicativo nuovo prende `BYPASSRLS`
senza dichiararlo, il conteggio resta **1** e il presidio sulla RLS diventa muto.

⇒ `registro` porta il **nome della tabella** che tiene le voci note. Il progetto
ne aveva già tre con la stessa forma — `riferimenti_morti_esenzioni`,
`codici_errore_senza_policy`, `rls_perimetro_debito` — più la colonna
`debito_dichiarato` di `processi_bersagli`. Il §2 di
[presidi-e-registri-del-debito.md](../../guide/presidi-e-registri-del-debito.md)
lo descriveva già: *«una voce per caso, il motivo scritto, la data»*.

⚠️ Dove il registro non esiste ancora, `registro` è `NULL` **e la nota dice che
quello è il lavoro**. Un vuoto dichiarato.

### 7.3 🔴 Il §4.2 aveva l'argomento giusto per la conclusione sbagliata

Il §4.2 conclude «`MANUTENZIONE` ⇒ niente identità né emittente» perché *«le tre
viste `vw_processi_dominio_*` guardano i soli processi di dominio»*. Ciò che
decide il perimetro però non è la **classe di chi legge**: sono **le tabelle che
le viste interrogano**.

**Verificato:** `dbops.vw_eventi_non_dichiarati` è `security_invoker` su
`vendite.event_log`, dove `rls_event_log_ef_whitelist` pretende
`app.ruolo_applicativo = 'OPERATORE'`. Un management command non ha le GUC ⇒ la
policy è falsa su ogni riga ⇒ **zero righe**. Stessa forma per
`vw_af_senza_giro` e `vw_diag_v_clienti_links`.

⛔ E su una vista di natura `ZERO`, «zero righe» e «non ho potuto vedere» **si
scrivono uguale**: il digest riporterebbe *«tutto a posto»* proprio perché è
cieco. È il verde per sottrazione, sul presidio dei presidi.

⇒ **`dbops.fn_conta_presidio`**, `SECURITY DEFINER` del proprietario (la RLS è
`ENABLE` senza `FORCE`), stesso meccanismo di `config.fn_accoda_email_sistema`.
Torna **un `bigint`, mai le righe**, e conta **solo ciò che è a catalogo** — su
una vista non dichiarata **solleva**, non torna zero.
⭐ L'alternativa (ruolo `BYPASSRLS` dedicato) è stata scartata: avrebbe letto
tutto, e sarebbe comparsa come riga in `vw_processi_che_bypassano`.

⚠️ **`vw_af_senza_giro` è marcata `DEFINER` in anticipo**: oggi
`vendite.attivita_fatturabili` non ha la RLS (debito dichiarato in
`rls_perimetro_debito`), ma la vista è `security_invoker` — il giorno in cui quel
debito si salda il conteggio diventerebbe cieco **senza che nessuno tocchi la
riga**.

### 7.4 ⭐ Le nature sono cinque, e tre righe del §2 non tornano col contratto

Il vocabolario è `ZERO` · `REGISTRO` · `LAVORAZIONE` · `CANCELLO` · `INVENTARIO`
(13 · 1 · 8 · 3 · 7). Tre viste sono classificate diversamente dal §2, **sulla
scorta del `COMMENT` della vista stessa**:

| Vista | §2 del brief | Catalogo | Perché |
| --- | --- | --- | --- |
| `vw_codici_errore_da_dichiarare` | 🟠 registro, 508 righe | **CANCELLO** | Non è un registro: è la *misura*, «volutamente larga», e cresce a ogni codice errore nuovo e legittimo (+188 in due settimane). Il debito sono le voci del suo registro, oggi **vuoto**. Il presidio è `test_error_codes_db_policy_guardrail`, che blocca già il merge |
| `vw_fk_con_indice_missing_policy` | 🟠 registro, 57 | **LAVORAZIONE** | Il suo `COMMENT`: *«letta da `dbops.fn_seed_fk_index_policy`»*. È una coda che una funzione consuma |
| `vw_processi_che_bypassano` | 🟠 soglia 1, «il modello» | **ZERO** su colonna | Il suo `COMMENT`: *«ZERO righe con stato = NON_DICHIARATO»*. Non è una soglia |

⭐ **Non è un rilievo contro il brief: è la sua tesi, verificata.** Sette righe
scritte con cura da chi aveva letto tutto, e tre non tornano col contratto della
vista. *La natura la deve scrivere chi ha scritto la vista* — che è esattamente
ciò che il §3 sostiene.

⚠️ **Restano tre righe da confermare** (🔶 nella nota del seed):
`vw_af_senza_giro` (target `ZERO`, oggi cala da sola), `vw_run_senza_attore` e
`vw_processi_dominio_su_pgagent` — quest'ultima è **arrivata a vuota**, quindi da
qui in avanti una riga è una regressione.

### 7.5 ⭐ Si dichiara lo stato ATTESO, non quelli di allarme

Quattro viste portano una colonna di stato dove una riga può essere lì di
proposito. Elencare i valori **di allarme** è la scelta permissiva: uno stato
**nuovo**, aggiunto domani, non sarebbe nell'elenco e cadrebbe nel **silenzio** —
l'unico verso in cui un presidio marcisce senza che nessuno se ne accorga.

⇒ Si dichiara l'unico stato **accettato** (`stato_atteso`), e l'allarme è
`IS DISTINCT FROM` quello. Uno stato nuovo cade nell'**allarme**, e chi lo
aggiunge deve venire a decidere — è la stessa scelta scritta nel `COMMENT` di
`vw_processi_programmazione` per `da_guardare`.
⭐ E prende gratis il caso a tre stati di `vw_rls_perimetro_scoperto`:
`NON_DICHIARATO` (allarme) e `DEBITO_ESTINTO` (riga di registro da togliere)
senza doverli nominare. È il **test 10** del pgTAP.

### 7.6 ⭐ Il catalogo serviva, e la prova è arrivata prima della risposta

Le viste sono **32, non 31**: `dbops.vw_rls_perimetro_scoperto` è nata il
**2026-09-09** (changeSet `20260909-76`) — lo stesso giorno in cui il §2 ne
contava trentuno e il §3 argomentava che un elenco Python *«diverge il giorno in
cui il team DB aggiunge la trentaduesima vista»*.

⚠️ Il conteggio «30 `COMMENT` su 31» resta vero e ha un seguito utile: **l'unica
vista senza `COMMENT` era `vw_trigger_functions`**, cioè proprio quella che il §2
porta come esempio di rumore. L'unica la cui natura non era scritta da nessuna
parte era quella usata per dimostrare che la natura non è deducibile dal nome.
Il `COMMENT` è stato aggiunto (`20260910-07`); non è «cambiare una vista».

### 7.7 🔵 Tre cose che restano al backend

**0) 🔴 URGENTE — rigenerare `error_policies_generated.py`.** Il codice nuovo
`E_PRESIDIO_NON_A_CATALOGO` è a catalogo nel DB e **non** nel file generato del
backend: dal merge della PR #1552, `Tito-dev` è **rosso** con due fallimenti.

```bash
cd backend && ./manage-env.sh genera_error_policies   # poi committare il file
```

| Test rosso | Che cosa dice |
| --- | --- |
| `test_error_codes_db_policy_guardrail` · `test_nessun_codice_nuovo_senza_policy` | *«1 codice che il database può nominare non ha una policy e non è nel registro del debito: `E_PRESIDIO_NON_A_CATALOGO` (`dbops.fn_conta_presidio`)»* |
| `test_error_policies_divergenza_db` · `test_il_file_generato_e_allineato_al_catalogo` | *«diverge dal catalogo (12 righe). Rigenerare con `manage.py genera_error_policies` e committare»* |

⭐ **Non è un difetto: è il terzo lato che funziona.** Un codice seminato dal DB
deve ricevere una **classe** lato backend prima di poter rispondere con lo
status giusto, e il cancello è esattamente ciò che impedisce di dimenticarsene.
La classe è già decisa e sta nel CSV: **`TECNICO` (500)** — quel parametro non lo
fornisce nessuna persona in un form, lo passa il digest leggendo il catalogo.
⛔ Il DB non lo rigenera da sé: `backend/` è fuori dal perimetro di `dev/db-tid`,
e `error_policies_generated.py` è del backend anche quando la causa è nostra.

⚠️ **Ordine delle operazioni:** il DB è già dentro. Il commit del backend può
entrare quando volete — fino ad allora `Tito-dev` resta rosso su quei due test,
e **solo** su quelli.

---

**Le due che erano già scritte:**

**a) Il destinatario non è una colonna di `dbops.presidi`.** Un indirizzo
descrive *questa* installazione: dentro un CSV di catalogo o viaggia su ogni
installazione o rende la riga non seminabile ([§11.7](../../linee-guida-sql.md)).
⭐ Ed è la stessa ragione già accettata per `sveglie.json`: *come si sveglia un
processo è un fatto di deploy e vive dove vive il deploy* — il team DB rifiutò
per questo di dichiarare la cadenza dei job pgAgent su `dbops.processi`.
⇒ **Il destinatario sta nel deploy del backend**, non in `config.parameters` e
non qui.

**b) ⛔ Il digest muto e il digest morto si scrivono uguale.** Il §5.5 fa del
silenzio il caso normale — scelta giusta contro il rumore — e con ciò rende
**invisibile la morte del digest stesso**. È la firma di R-12
(`apply_storicizza_weekly`, morto ogni settimana per sei mesi, scoperto per
caso) e il terzo motivo di `vw_coda_lavori_da_guardare`: *«un worker spento non
produce errori, produce ASSENZA»*.
⚠️ E il DB **non può** accorgersene: `vw_processi_programmazione` classifica i
`COMMAND` come `FUORI_PORTATA`, ed è una decisione, non un limite da aggirare.
⇒ Tre righe, tutte lato backend:

1. `tolleranza_minuti` **valorizzato** nella voce di `sveglie.json` (oggi `null`
   significa *«la liveness NON si presidia da qui»*);
2. un **battito**: alla cadenza dei registri il digest parte comunque, con in
   testa la propria ultima corsa letta da `maintenance.job_run_log`;
3. `OnFailure=` nell'unit template.

### 7.8 Che cosa è stato verificato, e come

| Verifica | Esito |
| --- | --- |
| I quattro changeSet applicati | ✅ `EXECUTED` alle 15:44 del 2026-09-10 |
| `dbops.presidi` | ✅ **32 righe** — ZERO 13 · REGISTRO 1 · LAVORAZIONE 8 · CANCELLO 3 · INVENTARIO 7 |
| `E_PRESIDIO_NON_A_CATALOGO` | ✅ a catalogo, classe `TECNICO` |
| `digest_presidi` in `dbops.processi` | ✅ `MANUTENZIONE` / `COMMAND` |
| `test-catalogo-presidi-v1.sql` dal runner | ✅ **11/11** |
| `pgtap-baseline.sh dbops` | ✅ **0 rossi su 33**, nessuna regressione |
| I sei guardrail statici della CI | ✅ tutti verdi |

⭐ **E un difetto trovato dal migrate, che vale scrivere.** La prima corsa è
morta su `errore di sintassi presso ","`: un `si'` con l'apostrofo **singolo**
dentro un `COMMENT ON COLUMN` (§11.3). ⚠️ `guardrail_sql_letterali.py` era
**verde**, ed è corretto che lo fosse: prende il letterale che non si chiude
*mai*, non quello che si chiude nel punto sbagliato — è il suo limite già
dichiarato, e l'unica cosa che vede il secondo è il parser di PostgreSQL. La
prova che serve resta quella: eseguire l'SQL **estratto** dal changeSet, intero,
con `ON_ERROR_STOP=1`, in una transazione che si annulla.

⭐ **E un presupposto reso asserzione, sempre dal migrate.** Andando a vedere chi
possiede la funzione dopo l'`update` è emerso che Liquibase gira come `titodb`
in sviluppo e come `zeroerp` in CI: il `SECURITY DEFINER` attraversa la RLS
perché **chi migra possiede anche le tabelle** (misurato: 77 tabelle in RLS,
**zero con `FORCE`**). È vero oggi e non è un contratto ⇒ è il **test 11**, e il
suo ramo negativo è provato.

### 7.9 ⛔ Che cosa resta fuori, come da §6

* sanare i registri di debito (D10/D11);
* toccare le 31 viste — l'unica eccezione è il `COMMENT` che mancava;
* un tipo di coda nuovo.

⚠️ E le tre righe 🔶 del §7.4 restano da confermare quando i loro cantieri le
toccano: `vw_af_senza_giro`, `vw_run_senza_attore`,
`vw_processi_dominio_su_pgagent`.

---

*Brief aperto il 2026-09-09 dal backend. Le misure sono letture del catalogo
PostgreSQL e conteggi sulle viste di `dbops` del database di sviluppo, datati
2026-09-09, e valgono come controesempio — non come motivo. Il motivo sta sul
modello: un presidio senza destinatario non presidia.*
*Risposta DB del 2026-09-10: la classificazione delle 32 righe è derivata dai
`COMMENT` delle viste — che sono contratto — non dai conteggi.*

---

## 8. 🔵 Risposta backend — il piano, 2026-09-10

> **Chi risponde:** backend (`dev/backend-tid`). **Stato:** §7.7 punto 0
> **chiuso**; il resto è un piano in quattro fasi, con due decisioni che chiedono
> una risposta prima della fase 3.

> ### ✅ VERIFICATO E CONSEGNATO — lo stesso giorno, e non da questo piano
>
> **Il §5 è stato costruito mentre questo §8 lo pianificava**, da un secondo
> cantiere sullo stesso repository. La consegna è il **§9**, che è la sede da
> leggere: qui restano il ragionamento e le due richieste che ne sono uscite.
>
> **Che cosa è stato verificato** (backend, 2026-09-10, eseguito — non letto):
>
> | Verifica | Esito |
> | --- | --- |
> | I test del cantiere (`test_presidi_catalogo`, `test_presidi_repository`, `test_presidi_digest`, `test_processi_service`) | ✅ **43 verdi** |
> | Il test della FORMA che il §5.5 chiedeva — «un registro stabile non produce un invio» | ✅ c'è, ed è il primo del file |
> | Il **battito** del §7.7b | ✅ tre test, fra cui «una corsia mai girata non sparisce dal battito» |
> | La suite backend intera | ✅ **4590 verdi** |
> | `deploy/sveglie.json` | ✅ due corsie, `tolleranza_minuti` valorizzato su entrambe |
> | La seconda sede che il §8.3 denunciava (`PRESIDI_PROCESSI`) | ✅ **rimossa**: il pannello legge il catalogo |
>
> ⚠️ **Due cose sono uscite diverse da come le proponeva questo §8**, ed entrambe
> hanno una ragione migliore della mia — sono dichiarate al §9.2 e qui sotto,
> voce per voce. Restano scritte perché un piano corretto a posteriori non
> insegna niente: si vede solo dove si è cambiato idea, e perché.

### 8.0 ✅ Il punto 0 è chiuso — e con una riga che il §7.7 non chiedeva

`error_policies_generated.py` rigenerato: il diff è **una sola voce**,
`E_PRESIDIO_NON_A_CATALOGO: TECNICO`, più il contatore di intestazione
(852 → 853). Nessun altro codice: il DB non era avanti su altro, verificato col
`--check` prima di rigenerare.

⭐ **E serviva anche il ripiego**, che il §7.7 non nomina: il messaggio a
catalogo porta un `%s` («*Vista di presidio sconosciuta: %s non è dichiarata…*»),
e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` pretende per ogni codice
vivo una frase **senza segnaposto** — è proprio quando gli argomenti non arrivano
che il ripiego entra in scena, e un `%s` a video sarebbe la cosa peggiore da
mostrare in un caso già tecnico. Scritta in `error_messages_fallback.py`.

I tre cancelli del contratto errori sono verdi: `test_error_codes_db_policy_guardrail`,
`test_error_policies_divergenza_db`, `test_error_policies_classi`.

### 8.1 ⛔ RITIRATO — Le due decisioni, e dove il backend proponeva di metterle

> **Ritirato il 2026-09-10 (decisione di Tid, §9.2).** Il destinatario sta in
> un setting del backend (`ZEROERP_PRESIDI_DIGEST_DESTINATARIO` in
> `.env.systemd`), non in `config.parameters`. ⭐ Il §7.7a aveva ragione, e la
> sede scelta regge anche l'obiezione che questo paragrafo muoveva a
> `sveglie.json`: `.env.systemd` è **per-host e non versionato**, quindi
> nessun indirizzo finisce in un repository pubblico. ⚠️ E costa un
> prerequisito in meno: non serve il seed di un parametro, quindi la fase 3
> non aspettava più nessuno.
> ⭐ Resta valido ciò che questo paragrafo ha portato e che è stato adottato:
> il **precedente** di `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` (mai
> partito, unica traccia un `logger.info`) e la regola che ne discende —
> *vuoto ≠ spento, e il «non configurato» si dichiara dove chi guarda le
> corse lo vede*. La cadenza invece è finita dove diceva: `sveglie.json`.

> 🔴 **RITIRATA la riga sul destinatario** (Tid, 2026-09-10): il §7.7a aveva
> ragione, il destinatario sta nel **backend** e non in `config.parameters`.
> Dove sia finito, e perché `.env.systemd` regge anche l'obiezione sul
> repository pubblico, sta nel **§9.2**. ⚠️ Questo paragrafo resta per il
> ragionamento che ha portato alla decisione — e perché il precedente che porta
> (`VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`, l'email mai partita) vale
> identico nella sede nuova. La riga sulla **cadenza** resta invece in vigore.

| Cosa | Dove | Perché |
| --- | --- | --- |
| **Cadenza** | `backend/deploy/sveglie.json` | Non è una preferenza: è l'`OnCalendar` che `install-timers.sh` scrive nel timer, e quel file è **la sede unica** già presidiata in CI dal job `validate-deploy`. Due sveglie sullo stesso processo sono ammesse (`run_fatturazione_batch` ne ha due), quindi la cadenza doppia del §5 non chiede niente di nuovo |
| **Destinatario** | `config.parameters`, valore messo come **override** dalla schermata Impostazioni | È il posto **facile da configurare**: si cambia dall'applicazione, senza toccare un file, senza riavviare un timer, senza un deploy |

⚠️ **La seconda riga diverge dal §7.7a, e la divergenza va guardata perché
l'argomento del §7.7a è giusto.** Un indirizzo descrive *questa* installazione, e
in un CSV di catalogo o viaggia su ogni installazione o rende la riga non
seminabile. ⭐ Ma quell'argomento colpisce il **seed**, non il **valore**: in
`config.parameters` si semina il *codice* del parametro (che è contratto del
software, e su ogni installazione ci sta benissimo) mentre il **valore** vive in
`config.parameter_overrides`, che è dato di macchina e non viene seminato da
nessuno.

⭐ **Il precedente esiste ed è dello stesso genere** —
`VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`, il destinatario delle richieste di
approvazione prezzo, letto con la cascata di scope e **assente = skip
silenzioso**.

🔴 **E il suo esito è il motivo per cui il parametro va SEMINATO, non lasciato
nascere da un override** (misurato il 2026-09-10 leggendo il catalogo, non la
popolazione): `config.parameters` ha **53 righe** e quel codice **non è fra
quelle** — nessun parametro con `EMAIL` o `RECIPIENT` nel nome. Quindi
`_risolvi_email_approver` non lo trova mai, `_invia_email_richiesta_approvazione`
esce sul `if not destinatario` e **quell'email non è mai partita**, da quando
esiste il workflow L3. L'unica traccia è un `logger.info`.

⚠️ **È esattamente il difetto che questo cantiere combatte, in un altro punto**:
non un errore, un'ASSENZA. E dice due cose sul digest:

1. il parametro va **a catalogo con `default_value` vuoto** — così compare nella
   schermata Impostazioni e qualcuno *può* configurarlo. Un parametro che esiste
   solo se qualcuno indovina il codice non è configurabile: è invisibile;
2. il «non configurato» del digest non può essere un `logger.info`. Va **in coda
   al digest stesso** e nell'esito del `registered_job`, dove chi guarda le corse
   lo vede senza cercarlo.

⛔ **Perché NON `sveglie.json` per il destinatario**, che sarebbe la lettura
letterale del §7.7a: quel file è **versionato**, e questo repository è
**pubblico** (GPL v3, su GitHub). Un indirizzo aziendale committato è
ricognizione regalata e non si ritira più. La cadenza lì ci sta perché non è un
dato di nessuno.

⚠️ **In entrambi i casi il default è «non configurato», e non è la stessa cosa di
«spento»**: il digest si calcola comunque e lo **dichiara** in coda
(«*digest calcolato, nessun destinatario configurato: non è stato inviato*»).
Un invio che non parte in silenzio sarebbe la prima cosa da non fare in un
cantiere che nasce contro il silenzio.

### 8.2 ✅ CONSEGNATO — Il piano, in quattro fasi

> Le quattro fasi esistono tutte (§9.1). ⚠️ Con **due riserve dichiarate**,
> che non erano nel piano perché nessuno poteva prevederle: la corsia
> **settimanale è scritta e SPENTA** (leggere `vw_riferimenti_morti_*` fa
> cadere il cluster, §9.3) — e con lei è spento il battito — e `OnFailure=`
> non c'è, come **assenza dichiarata** e non come dimenticanza.

| # | Cosa | File | Il test che lo chiude |
| --- | --- | --- | --- |
| **1** | Il **lettore** del catalogo: `dbops.presidi` → righe attive, con natura, `colonna_stato`/`stato_atteso`, `registro`, `perimetro` | `apps/core/db/presidi_repository.py` | Su DB provvisto: il lettore torna le 32 righe e la natura di ciascuna viene dal catalogo, non da un elenco Python |
| **2** | Il **digest**: tre elenchi (allarmi `ZERO` con righe · registri **cresciuti** · registri stabili in una riga di riepilogo), il conteggio via `dbops.fn_conta_presidio` | `apps/core/services/presidi_digest.py` | ⭐ Il test della forma del §5.5: **un registro stabile non produce invio**. Più: uno stato NUOVO su una vista con `stato_atteso` cade nell'allarme (`IS DISTINCT FROM`), non nel silenzio |
| **3** | Il **command** + invio: `manage.py digest_presidi`, `registered_job` sul processo `digest_presidi` (id 26), corpo via `config.fn_accoda_email_sistema`, `--secco` per guardarlo senza inviare | `apps/core/management/commands/digest_presidi.py` | Il comando gira a mano e non invia niente se il destinatario non è configurato, dicendolo |
| **4** | Il **deploy**: voce in `sveglie.json` con `tolleranza_minuti` **valorizzato**, coppia di template systemd con `OnFailure=`, e il **battito** del §7.7b (alla cadenza dei registri il digest parte comunque, con in testa la propria ultima corsa da `maintenance.job_run_log`) | `backend/deploy/sveglie.json`, `deploy/systemd/` | `test-install-timers.sh` (CI, `validate-deploy`) + `test_ogni_processo_del_backend_ha_una_sveglia` |

⭐ **Le fasi 1 e 2 non aspettano nessuna delle due decisioni**: un digest che si
può guardare a mano è già meglio di niente (§5.2), e senza destinatario si
calcola lo stesso. Le decisioni servono alla **fase 3**.

### 8.3 ✅ CONSEGNATO — Il pannello a video, e una conseguenza che va saputa

> Il pannello legge le `ZERO` dal catalogo: `PRESIDI_PROCESSI` non esiste più.
>
> 🔴 **MA fra le `ZERO` c'è `vw_riferimenti_morti_rientrati`, e leggerla fa
> cadere il cluster** (§9.3, rischio **aperto**). Il rimedio giusto è già
> scritto lì — la colonna `attivo` del catalogo, non un elenco di esclusioni nel
> backend — e finché quella riga non è spenta **aprire quella schermata è
> pericoloso**.
>
> ⚠️ **E c'è un fatto in più, che nessuno ha ancora messo insieme: il pannello
> viene ricaricato PIÙ SPESSO di ieri, per una correzione entrata stamattina.**
> `ProcessiAutomaticiListView` caricava i presidi in `onMounted`; il difetto D8
> (view sotto `<KeepAlive>` che non ricaricano al rientro) l'ha spostato in
> `onActivated`, che è **giusto** — quei conteggi erano stantii — ma significa
> una lettura **a ogni rientro nella pagina** invece di una sola per montaggio.
> ⇒ La correzione non ha creato il difetto e non va disfatta: ne ha **alzato la
> frequenza**, e questo va saputo finché la riga di catalogo non è spenta.
> Chi lavora sul dbdev in queste ore: quella schermata si evita.

#### Il ragionamento di allora, che resta valido

`apps/core/db/processi_repository.py` porta `PRESIDI_PROCESSI`, una tupla di
**dieci** viste cablate: da oggi è la **seconda sede** di un fatto che il DB ha
messo a catalogo, ed è esattamente ciò contro cui il §3 argomenta. Confrontate:

| | |
| --- | --- |
| Viste `ZERO` a catalogo | **13** |
| …di cui nel pannello | **8** |
| 🔴 `ZERO` che **nessuno guarda** | **5** — `vw_operatori_senza_emittente`, `vw_liste_multi_emittente_non_certificate`, `vw_parameter_fk_surrogate_dangling`, `vw_riferimenti_morti_rientrati`, `vw_rls_perimetro_scoperto` |
| Nel pannello ma **non** `ZERO` | 2 — `vw_run_senza_attore` (LAVORAZIONE) e `maintenance.vw_job_run_da_guardare` |

⇒ **Decisione presa (Tid, 2026-09-10): il pannello mostra le `ZERO` lette dal
catalogo.** Sono gli allarmi veri — «questa vista deve restare vuota» — e
`LAVORAZIONE`, `CANCELLO` e `INVENTARIO` non lo sono: una coda con righe è
lavoro in corso, non un guasto, e un pannello che mostra righe verdi insegna a
leggere il verde come debito (è l'argomento già scritto nella costante per
`vw_processi_programmazione`).

⚠️ **Conseguenza da sapere prima**: cinque presidi compaiono, e
`vw_run_senza_attore` **sparisce** dal pannello — è `LAVORAZIONE`, quindi va nel
digest, non fra gli allarmi. È una delle tre righe 🔶 che il §7.4 lascia da
confermare: se il team DB la riclassifica `ZERO`, torna nel pannello senza che
nessuno tocchi il backend. *È il catalogo che decide, ed è il punto.*

### 8.4 🔵 APERTA — RICHIESTA AL TEAM DB: iscrivere `maintenance.vw_job_run_da_guardare`

> ⭐ **Nel frattempo il backend non la perde**: `presidi_repository` porta la
> riga in `_IN_ATTESA_DI_CATALOGO` — la STESSA che sta qui sotto — come
> debito dichiarato, e `test_il_debito_delle_viste_in_attesa_e_rientrato`
> diventa rosso il giorno dell'iscrizione, dicendo di cancellarla. ⛔ Toglierla
> dal pannello nell'attesa sarebbe stata la cosa peggiore: quella vista dice
> «l'ultima corsa di un job è fallita», ed è il presidio da cui il cantiere è
> nato. Vedi anche §9.5.

> **Decisione di Tid, 2026-09-10: si iscrive.** Qui sotto la riga pronta, con i
> valori derivati dal `COMMENT` della vista — non scelti dal backend.

Il pannello la interroga; il catalogo non la conosce. **Non è una svista**: il
perimetro del test 2 è derivato dagli schemi che il catalogo stesso nomina
(`SELECT DISTINCT split_part(vista,'.',1) FROM dbops.presidi`), e oggi nomina
solo `dbops` — quindi `maintenance` è fuori perimetro **per costruzione**, e il
pgTAP è verde a ragione.

⚠️ **Ma diventa un guasto alla fase 2**, non oggi: appena il conteggio passerà da
`dbops.fn_conta_presidio`, quella vista solleverà `E_PRESIDIO_NON_A_CATALOGO` —
il codice che questo stesso brief ha appena introdotto. ⭐ E sarebbe il caso
migliore: la funzione **rifiuta** invece di rispondere zero, quindi il difetto si
vede subito. È il test 8 del pgTAP che lo garantisce.

⭐ **La natura non la propone il backend: la dichiara il `COMMENT` della vista**,
che dice testualmente **«DEVE restare VUOTA»** — ed è il criterio del §3. Lo
stesso `COMMENT` chiude dicendo *«Chi la vede lo decide il backend con area
funzionale e profilo, come per le viste di presidio **sorelle**»*: la vista è
nata per stare accanto alle altre, ed è rimasta fuori solo perché sta in un
altro schema.

**La riga, pronta per `80_data/sql/dbops/presidi.csv`:**

```csv
maintenance.vw_job_run_da_guardare,ZERO,NULL,NULL,NULL,NULL,GIORNALIERA,LIBERO,t,NULL,"L ultima corsa di un job e fallita, o e rimasta aperta da oltre un ora, o il job e intermittente (verde adesso ma con rossi negli ultimi sette giorni). DEVE restare vuota. colonna_stato resta NULL DI PROPOSITO: la vista HA una colonna motivo, ma dice PERCHE la riga e li - FALLITA, APERTA DA TROPPO, INTERMITTENTE - e ognuna e comunque da guardare; filtrarla spegnerebbe il presidio, esattamente come su vw_coda_lavori_da_guardare. GIORNALIERA perche un lavoro fallito stanotte va visto stamattina. LIBERO perche la vista non ha RLS: un giro di manutenzione non appartiene a un azienda. Iscritta su richiesta del backend il 2026-09-10: e la decima spia del pannello presidi e l unica che il catalogo non conosceva."
```

| Campo | Valore | Da dove viene |
| --- | --- | --- |
| `natura` | `ZERO` | il `COMMENT` della vista: «DEVE restare VUOTA» |
| `colonna_stato` / `stato_atteso` | `NULL` | ogni riga è da guardare: `motivo` dice *perché* è lì, non se conta — stesso ragionamento già scritto nella nota di `vw_coda_lavori_da_guardare` |
| `cadenza` | `GIORNALIERA` | §5: «un lavoro fallito stanotte va visto stamattina» |
| `perimetro` | `LIBERO` | il `COMMENT`: «Niente RLS» |
| `registro` / `presidiato_da` | `NULL` | non è un registro di debito e non è un `CANCELLO` |

⚠️ **Effetto collaterale voluto**: iscrivendola, lo schema `maintenance` entra nel
perimetro del **test 2** — che è derivato dal catalogo, quindi si allarga da sé.
Da quel momento *ogni* vista di `maintenance` dovrà essere a catalogo. ⭐ Vale la
pena saperlo prima: se in `maintenance` ci sono viste che presidio non sono, il
test 2 diventerà rosso e andrà deciso caso per caso. Il backend non le ha
contate — è una lettura che tocca a chi possiede lo schema.

⛔ **Fino all'iscrizione la fase 2 non passa il conteggio da `fn_conta_presidio`
per quella vista**: la tiene sul conteggio diretto, con un commento che rimanda a
questo paragrafo. Nessun lavoro sprecato e nessuna riga che solleva.

### 8.5 ⛔ Cosa questo piano NON fa

* non tocca le viste, né i registri di debito (§6);
* non introduce un tipo di coda (§4.2);
* non decide la natura di nessuna riga di catalogo, comprese le tre 🔶 del §7.4.

---

## 9. 🔵 Risposta backend — il §5 è fatto, 2026-09-10

> **Chi risponde:** backend (`dev/backend-tid`). **Stato:** le quattro fasi del
> §8.2 sono scritte e provate; il digest gira e riferisce. ⛔ Restano **tre
> richieste al team DB**, e la prima è urgente perché non riguarda questo
> cantiere: **leggere una vista di presidio fa cadere il cluster**.

### 9.0 🔵 Che cosa serve dal team DB, in ordine

> ✅ **Risposto al §10** (team DB, 2026-09-10): **2 e 3 chiuse e applicate**; la
> **1 cambia diagnosi** — i 779 non erano riferimenti morti, ed è riparato ciò
> che si poteva riparare. La tabella qui sotto resta com'è scritta: è il
> documento di chi ha chiesto.

| # | Cosa | Che cosa sblocca | Dove |
| --- | --- | --- | --- |
| **1** | 🔴 Trovare perché leggere `dbops.fn_check_funzioni_riferimenti_morti` **uccide il backend PostgreSQL** (il log del server ha il segnale) | il pannello dei presidi torna sicuro da aprire; la corsia **settimanale** del digest si può accendere — e con lei il **battito**, che oggi non c'è | §9.3 |
| **1-bis** | *Se la causa non si trova subito*: `attivo = f` sulla sola `dbops.vw_riferimenti_morti_rientrati` — riga pronta nel §9.3 | toglie il rischio dal **pannello** senza toccare il backend. ⚠️ È un tampone: la riga sparisce dai controlli, e la nota deve dirlo | §9.3 |
| **2** | 🟠 `perimetro = DEFINER` sulle **due** righe `riferimenti_morti` — righe pronte nel §9.4 | il conteggio resta onesto e sparisce il percorso che è morto **tre volte su tre** (le letture *invoker*). ⛔ Non sostituisce la 1 | §9.4 |
| **3** | 🔵 Iscrivere `maintenance.vw_job_run_da_guardare` — riga pronta nel §8.4, già decisa (Tid, 2026-09-10) | toglie l'ultima riga di debito dal backend, e il suo presidio diventa rosso da solo il giorno dell'apply | §8.4, §9.5 |

⭐ **Nessuna delle tre blocca il resto**: il digest giornaliero gira già, e il
backend non aspetta niente. Sono cose che *tolgono un rischio* e *chiudono un
debito*, non prerequisiti di ciò che è stato consegnato.

✅ **Le righe CSV proposte qui sotto sono PROVATE, non solo scritte**: applicate
tutte e tre sul dbdev il 2026-09-10 dentro una transazione annullata (il pattern
degli smoke del progetto), passano ogni `CHECK` di `dbops.presidi` — e il
database è rimasto intatto, 32 righe come prima. È la prova che il §7.8 chiede
di suo pugno dopo il migrate morto su un apostrofo: *eseguire davvero l'SQL, in
una transazione che si annulla*.

⚠️ **E i tre punti del §7.7 sono chiusi**, così il team DB non deve andarli a
ricontrollare: il **punto 0** (`error_policies_generated`) è chiuso dal §8.0; il
**punto a** (destinatario) è chiuso dal §9.2, e la conclusione è quella del
§7.7a — sta nel backend; il **punto b** (digest muto contro digest morto) è
chiuso per due terzi — `tolleranza_minuti` è valorizzata **e letta** e il battito
c'è (§9.7), mentre `OnFailure=` resta un'assenza dichiarata con la sua ragione
(§9.6).

### 9.1 Che cosa c'è adesso

| Cosa | File | Prova |
| --- | --- | --- |
| Il **lettore** del catalogo | `apps/core/db/presidi_repository.py` | `tests/db/test_presidi_repository.py` (7, senza DB) |
| I **mirror** contro i `CHECK` veri | idem | `tests/db/test_presidi_catalogo.py` (8, su DB provvisto) |
| Il **digest** | `apps/core/services/presidi_digest.py` | `tests/services/test_presidi_digest.py` (17, senza DB) |
| Il **command** e l'invio | `apps/core/management/commands/digest_presidi.py` | `tests/services/test_digest_presidi_command.py` (6) + provato sul dbdev, run a giornale |
| La **liveness a due chiavi** | `MaintenanceRepository.job_liveness` | `tests/db/test_job_liveness_due_chiavi.py` (5) |
| Il **deploy** | `deploy/sveglie.json` + 4 template in `deploy/systemd/` | `tests/services/test_sveglie.py` (11) + `test-install-timers.sh` |
| Il **pannello** dalle `ZERO` a catalogo | `presidi_repository.stato_presidi` + `processi_service` | `tests/services/test_processi_service.py` (11) |

Suite intera: **4646 test verdi** (lettura del 2026-09-10).

⭐ **Il command non sa quali viste esistono.** Fa una domanda sola — «cosa
guardo a questa cadenza?» — e il catalogo risponde. ⛔ E non c'è nessun elenco
di nature da escludere: il `CHECK chk_presidi_fuori_digest_cadenza_mai` già
garantisce che INVENTARIO e CANCELLO abbiano cadenza `MAI`, quindi **filtrare
per cadenza è filtrare per digest**. Una seconda copia di quella regola non
conoscerebbe la natura che nascerà domani.

### 9.2 Le due decisioni, come sono state prese

**Destinatario → un setting del backend** (`PRESIDI_DIGEST_DESTINATARIO`, da
`ZEROERP_PRESIDI_DIGEST_DESTINATARIO` in `.env.systemd`). **Il §7.7a aveva
ragione e il §8.1 è ritirato** (decisione di Tid, 2026-09-10): a chi arriva la
posta è un fatto di *questa* installazione. ⭐ E `.env.systemd` è per-host e
**non versionato**, quindi regge anche l'obiezione che il §8.1 muoveva a
`sveglie.json`: nessun indirizzo aziendale finisce in un repository pubblico.
⚠️ Vuoto ≠ spento: il digest si calcola lo stesso e lo **dichiara** — su stderr e
nel `meta` del run (`"inviato": "NON_CONFIGURATO"`), dove chi guarda le corse lo
vede senza cercarlo. È la lezione di `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`,
che non è mai partita lasciando come unica traccia un `logger.info`.

**Cadenza → `deploy/sveglie.json`**, la sede unica del dichiarato, con due
corsie (`digest_presidi:giornaliera` alle 07:00, `:settimanale` il lunedì alle
07:30) e `tolleranza_minuti` valorizzato su entrambe.
⚠️ **Quando** si guarda è del deploy; **cosa** si guarda a quella cadenza lo dice
il catalogo. Sono due domande diverse e stanno in due sedi diverse, di proposito.

### 9.3 🔴 RICHIESTA 1 — leggere `vw_riferimenti_morti_*` FA CADERE IL CLUSTER

> Fatto datato, dbdev, 2026-09-10 fra le 18:16 e le 18:23: **tre** occorrenze in
> un'ora, tutte su viste che passano da `dbops.fn_check_funzioni_riferimenti_morti`.

Il sintomo è `consuming input failed: SSL error: unexpected eof while reading`,
seguito da `FATALE: il database è in modalità di ripristino`: non è un errore
applicativo, è un **backend PostgreSQL morto** e il cluster che fa crash
recovery — quindi **tutte** le connessioni cadono, non solo la nostra.
(`pg_postmaster_start_time` non cambia: muore il processo, non il postmaster.)

| Quando | Che cosa stava leggendo |
| --- | --- |
| 18:16 | `SELECT *` da una vista settimanale, dopo il conteggio, nella stessa connessione |
| 18:19 | `SELECT count(*) FROM dbops.vw_riferimenti_morti_da_sanare` (ruolo `zeroerp_app`) |
| 18:23 | `SELECT *` da `dbops.vw_riferimenti_morti_rientrati` |

⛔ **Non l'ho riprodotto una quarta volta di proposito**: far cadere il database
di sviluppo per completezza non vale il disturbo, e le tre occorrenze bastano a
dire dov'è. La riproduzione controllata la faccia chi può guardare il log del
server, dove ci sarà il segnale che ha ucciso il processo.

⭐ **E c'è un denominatore che vale più delle tre morti.** Le letture di quelle
viste, quel giorno, sono state di due tipi:

| Percorso | Come | Morti |
| --- | --- | ---: |
| **invoker** — `SELECT` diretto sulla vista come `zeroerp_app` | il pannello che elenca, il digest che chiede un esempio | **3 su 3** |
| **definer** — `dbops.fn_conta_presidio` (proprietario) | ogni conteggio | **0 su ~6** |

⚠️ **Non è una prova che il percorso definer sia sicuro** — sei letture non lo
dicono, e un campione piccolo che «non ha mai fallito» è esattamente il modo in
cui ci si convince di una cosa non vera. È un fatto datato con il suo
denominatore, e serve a **indirizzare la ricerca**: la differenza fra i due
percorsi non è la query, sono i privilegi di chi la esegue.

**Chi rischia oggi, vista per vista** — e sono due schermate diverse:

| Vista | Natura | Chi la legge | Rischio |
| --- | --- | --- | --- |
| `vw_riferimenti_morti_rientrati` | `ZERO` | **il pannello dei presidi** (legge tutte le `ZERO`) | 🔴 aperto |
| `vw_riferimenti_morti_da_sanare` | `REGISTRO` | il solo **digest settimanale**, che è **spento** | 🟡 dormiente |

⇒ **La mossa minima che toglie il rischio subito** è una riga sola, se la causa
non si trova in giornata:

```csv
dbops.vw_riferimenti_morti_rientrati,ZERO,NULL,NULL,NULL,NULL,SETTIMANALE,LIBERO,f,NULL,"Voci del registro che non corrispondono piu a nessun difetto: righe da TOGLIERE dal CSV. E il verso che impedisce al registro di diventare un elenco di eccezioni permanenti, cioe l unico verso in cui un presidio marcisce senza che nessuno se ne accorga. SPENTA il 2026-09-10 e NON per una scelta di merito: leggerla fa morire il backend PostgreSQL e trascina il cluster in crash recovery, tre occorrenze in un ora (brief 9.3). Si riaccende appena la causa e chiusa: finche resta spenta questo controllo NON GUARDA NIENTE, ed e un buco dichiarato."
```

⚠️ **Le righe qui sopra e nel §9.4 sono scritte SENZA apostrofi e senza accenti**,
e non e' pigrizia: e' la convenzione del file — trentadue righe su trentadue —
e ha una ragione pagata il 2026-09-10, quando un `si'` dentro un `COMMENT` ha
fatto morire il migrate con «errore di sintassi presso ","» (§7.8). Chi le
copia non deve inciampare nello stesso punto.

⛔ **E va detto che cos'è**: un controllo spento è un controllo che non presidia.
La nota lo dichiara perché nessuno lo legga come «risolto» — è la stessa
differenza fra un debito registrato e un debito nascosto che questo catalogo
esiste per tenere.

⚠️ **Conseguenze già prese lato backend, e sono due:**

1. la corsia **settimanale** è **scritta e SPENTA** (`abilita: false` in
   `sveglie.json`, con la ragione nella nota): fra le sue viste c'è quella
   famiglia, e accenderla vorrebbe dire far cadere il database ogni lunedì. La
   giornaliera resta accesa — le sue viste non la toccano.
   ⚠️ **E va saputo che spegnendola si spegne anche il BATTITO**: è la corsa
   settimanale a portarlo, perché la giornaliera manderebbe un messaggio al
   giorno che dice «niente da segnalare» — cioè la posta che si impara ad
   archiviare senza aprire. Finché resta spenta, che il digest sia vivo lo si
   vede solo dal giornale dei run;
2. il **pannello dei presidi** ora legge le `ZERO` dal catalogo, e fra quelle
   c'è `vw_riferimenti_morti_rientrati`: finché il difetto è aperto, **aprire
   quella schermata può far cadere il cluster**. ⛔ Non l'ho provata in app per
   questo. Il rimedio non è un elenco di esclusioni nel backend: è la colonna
   `attivo` del catalogo, che esiste apposta — spegnere quelle righe con la nota
   che dice perché, e il pannello smette di leggerle **senza che nessuno tocchi
   il backend**.

### 9.4 🟠 RICHIESTA 2 — due righe dichiarano `perimetro = LIBERO` e sono cieche

Misurato lo stesso giorno, e regge a quattro letture consecutive:

| Vista | Letta da `zeroerp_app` | Letta dal proprietario (`fn_conta_presidio`) |
| --- | ---: | ---: |
| `dbops.vw_riferimenti_morti_da_sanare` | **0** | **779** |
| `dbops.vw_riferimenti_morti_rientrati` | **0** | **1** |

La causa è a monte della vista: `dbops.fn_check_funzioni_riferimenti_morti` è
`SECURITY INVOKER`, quindi da un ruolo che non possiede gli oggetti ispezionati
risponde vuoto. ⇒ Il `perimetro` di quelle due righe è **`DEFINER`**, non
`LIBERO`.

⭐ **E questa è la conferma più forte della scelta del §7.3.** Il §7.3 aveva
individuato **tre** viste da contare per forza dalla funzione; il backend ha
deciso di far passare **tutte** le letture da `fn_conta_presidio` «così l'allarme
è onesto ovunque e il chiamante non deve scegliere». Sono proprio le due viste
che quell'elenco non nominava: con un `count(*)` scritto nel backend, il digest
avrebbe riferito **«tutto a posto»** su 779 riferimenti morti e su un rientro —
il verde per sottrazione, sul presidio dei presidi, su due righe che nessuno
aveva classificato come a rischio.

⚠️ Intanto il digest **lo dichiara invece di tacere**: quando il conteggio dice
N e l'elenco torna vuoto su una vista marcata elencabile, il messaggio scrive
*«il conteggio dice N ma da qui la vista risponde VUOTA: il perimetro dichiarato
non regge»*. Un numero seguito dal nulla si leggerebbe come un difetto del
digest.

⭐ **E la correzione ha un secondo effetto, che vale da solo**: su `DEFINER` il
backend **non elenca** le righe — è il guard che sta nel repository. Cioè
sparisce proprio il percorso *invoker* che è morto tre volte su tre (§9.3).
⛔ Ma non sostituisce la richiesta 1: il conteggio continua a passare dalla
funzione, e finché non si sa **perché** quel codice uccide il processo, «non è
mai successo su questo percorso» non è una garanzia.

**Le due righe pronte per `80_data/sql/dbops/presidi.csv`** (cambia il solo
`perimetro`, `LIBERO` → `DEFINER`; la coda della nota dice il perché):

```csv
dbops.vw_riferimenti_morti_rientrati,ZERO,NULL,NULL,NULL,NULL,SETTIMANALE,DEFINER,t,NULL,"Voci del registro che non corrispondono piu a nessun difetto: righe da TOGLIERE dal CSV. E il verso che impedisce al registro di diventare un elenco di eccezioni permanenti, cioe l unico verso in cui un presidio marcisce senza che nessuno se ne accorga. DEFINER dal 2026-09-10: dbops.fn_check_funzioni_riferimenti_morti e SECURITY INVOKER, quindi da un ruolo che non possiede gli oggetti ispezionati la vista risponde ZERO — misurato, zeroerp_app legge 0 dove il proprietario legge 1."
dbops.vw_riferimenti_morti_da_sanare,REGISTRO,NULL,NULL,dbops.riferimenti_morti_esenzioni,NULL,SETTIMANALE,DEFINER,t,NULL,"Riferimenti morti non coperti dal registro del debito: e la lista di lavoro, e deve essere vuota. Ogni SELECT ri-compila circa cinquecento funzioni: e il motivo della cadenza settimanale e non giornaliera. Il costo di lettura e un attributo della riga, non del digest. DEFINER dal 2026-09-10: la funzione a monte e SECURITY INVOKER e da zeroerp_app la vista risponde 0 dove il proprietario legge 779 — il conteggio era onesto solo perche passa da fn_conta_presidio."
```

⚠️ **Il conteggio non cambia di una riga**: passava già dalla funzione. Cambia
che il backend smette di **elencare** — cioè smette di mostrare un elenco vuoto
accanto a un numero che non è zero.

### 9.5 🔵 RICHIESTA 3 — resta aperta l'iscrizione del §8.4

`maintenance.vw_job_run_da_guardare` non è ancora a catalogo. Il backend la
tiene con una **riga di debito dichiarata** in `presidi_repository`
(`_IN_ATTESA_DI_CATALOGO`) che porta gli stessi valori della riga CSV del §8.4:
toglierla dal pannello nell'attesa sarebbe stato il rimedio peggiore, perché è
la spia che dice «l'ultima corsa di un job è fallita».
⭐ Il giorno dell'apply il presidio
`test_presidi_catalogo.test_il_debito_delle_viste_in_attesa_e_rientrato` diventa
**rosso** e dice di cancellare quella riga: il debito ha il suo verso di ritiro.

⚠️ E oggi quella vista **non è vuota**: il digest giornaliero riporta
`sync_auth_user_active` — ultima corsa verde ma 31 rossi negli ultimi sette
giorni, cioè il ramo «intermittente». È un processo **ritirato** il 2026-09-07
(`obsoleto_dal`), quindi la riga è probabilmente il residuo di un timer ancora
acceso su un host: vale la pena guardarlo, ed è esattamente il genere di cosa
per cui il digest esiste.

### 9.6 ⛔ Che cosa NON è stato fatto, e perché

* **`OnFailure=` sugli unit** (§7.7b punto 3): **assenza dichiarata**, scritta
  nei template. Un `OnFailure=` serve a dire che il giro è fallito, ma l'unico
  canale che raggiunge una persona qui è la coda email, che vive nel database:
  se il giro è fallito perché il database non risponde, la notifica non parte
  comunque, e senza database resta una riga nel journal — che systemd scrive già
  da sé. ⇒ Un fallimento **con il database vivo** lascia `ok=false` su
  `job_run_log`, che è ciò che `vw_job_run_da_guardare` raccoglie e che il digest
  riporta al giro seguente. Il residuo — «fallito con il database
  irraggiungibile» — resta aperto e vuole un canale che dal database non
  dipenda: è una decisione sua, non un pezzo di questo cantiere.
* **Sanare i registri di debito** (§6): fuori perimetro, come da patto.
* **Un destinatario per vista** (§4.1): il campo non serve ancora, e il §6 lo
  dichiarava rimandabile.

*Risposta backend del 2026-09-10. Le misure di questo paragrafo sono letture del
dbdev di quel giorno e valgono come controesempio — «questo caso esiste ed è
gestito male» — non come motivo: il motivo sta sul modello, ed è che un presidio
che non si può leggere non presidia.*

### 9.7 ⭐ Quello che la revisione ha trovato — e sono tutti della stessa specie

Riletto il proprio codice a freddo (2026-09-10), i difetti veri erano **sei**, e
nessuno avrebbe fatto fallire niente:

| Difetto | Perché contava |
| --- | --- |
| `tolleranza_minuti` **stampata e mai confrontata** | era un campo del deploy dichiarato senza lettore, cioè un presidio che sembra tale e non lo è — il difetto contro cui nasce questo cantiere. ⇒ Ora il battito la usa per dire quali corsie sono **ferme**, e la liveness si chiede per `processo_codice` (la chiave con la FK) invece di comporre i nomi delle corsie |
| Una corsia **mai girata spariva** dal battito | `job_liveness` non elenca i jobname che il giornale non conosce — sta nel suo contratto. Senza le corsie **attese**, «mai partita» si leggeva come «nessun problema» |
| `CADENZE_DEL_DIGEST` e le scelte della CLI **scritte a mano** | una cadenza nuova a catalogo non sarebbe stata guardata da nessuna corsa, in silenzio. ⇒ Derivate dal vocabolario del catalogo, con il presidio che lo verifica contro il `CHECK` |
| Il **jobname della corsia** composto in due sedi | il comando lo scriveva, il battito lo cercava: al primo cambio di forma il battito avrebbe risposto «mai girato» invece di «non lo so» |
| `troncato` calcolato **anche dove le righe non si chiedono** | sul pannello produceva *«prime 0 righe»* su una vista con perimetro; nel digest avrebbe scritto «e altre 779» sotto un elenco che non c'è |
| La testata del pannello **verde con presidi non letti** | zero accesi e tre non letti dava un tag verde: «tutto a posto» detto proprio da chi non ha visto niente |

⭐ **Sono tutti la stessa specie**, ed è quella che questo cantiere combatte: un
dato che *sembra* dire «va bene» mentre dice «non lo so». Il difetto non era
nella logica — era nel modo in cui l'assenza si traveste da esito.

⚠️ Corretti anche due punti di fragilità: la connessione si chiude ora con
`close_if_unusable_or_obsolete` (il pannello gira dentro una richiesta web, e
chiudere una connessione sana è un effetto che nessuno si aspetta da una
lettura), e più destinatari separati da virgola diventano destinatario + copie
invece di finire interi in un campo solo — un invio che sarebbe fallito dentro
la coda email, cioè tardi e per caso.

---

## 10. 🔵 Risposta DB — le tre richieste del §9, 2026-09-10

> **Chi risponde:** team DB (`dev/db-tid`). **Stato:** richieste **2 e 3
> CHIUSE e applicate**; la **1 cambia diagnosi** — i 779 non erano difetti, e la
> parte riparabile è riparata. Resta aperta la causa dei segfault, che non è di
> questo cantiere.
>
> Applicato su dbdev alle 23:12: `20260910-35`, `-36`, `-37`. `dbops.presidi`
> ha **33 righe**, 5 `DEFINER`, 1 in `maintenance`. pgTAP del catalogo 11/11,
> `test-riferimenti-morti-v1.sql` verde con `plan(6)`.

### 10.1 🟠 Richiesta 2 — chiusa

`perimetro` → **`DEFINER`** su `dbops.vw_riferimenti_morti_rientrati` e
`..._da_sanare`, changeSet **`20260910-35`** (mirror ri-ancorato sullo stesso
CSV: il `-08` è mergiato e non si tocca).

Il ragionamento del §9.4 regge, e con la §10.3 acquista un secondo effetto: su
`DEFINER` il backend **non elenca**, quindi sparisce il percorso *invoker* che
era morto tre volte su tre.

### 10.2 🔵 Richiesta 3 — chiusa, con la lettura che il §8.4 chiedeva a noi

`maintenance.vw_job_run_da_guardare` è a catalogo. Valori come proposti, e
verificati uno per uno contro il `COMMENT` della vista — «DEVE restare VUOTA»
→ `ZERO`, «Niente RLS» → `LIBERO`, la colonna `motivo` dice *perché* la riga è
lì e ognuna è da guardare → nessun filtro.

⭐ **Il §8.4 chiedeva al team DB di contare, prima, che cosa sarebbe entrato nel
perimetro del test 2 allargandolo a `maintenance`. Contate: in quello schema
c'è QUELLA SOLA vista.** Nessun caso da decidere, nessun rosso: lo schema si
chiude in un colpo, e il test resta verde.

### 10.3 🔴 Richiesta 1 — la diagnosi cambia: **i 779 non erano difetti**

Il §9.3 e il §9.4 leggono il numero 779 come una popolazione di riferimenti
morti. Non lo era, e si dimostra dal codice senza eseguire niente.

`dbops.fn_check_funzioni_riferimenti_morti` avvolge ogni chiamata a
`plpgsql_check_function` in un `EXCEPTION WHEN OTHERS` che scrive
`error:CHECK-KO:` + il `SQLERRM`. Poi classifica **per forma del messaggio**:

| ramo | pretende |
| --- | --- |
| `FP_RAMO_ALTRA_TABELLA` | più tabelle sul trigger |
| `FP_TRANSITION_TABLE` | `^error:42P01:` |
| `FP_SQL_DINAMICO` | `^error:42601:` + `:EXECUTE:` |
| `FP_VARIADIC` | `^error:42883:` |
| **`ELSE`** | **→ `REALE`** |

⛔ `error:CHECK-KO:` non corrisponde a **nessuno** dei quattro: cadeva
nell'`ELSE`. ⇒ **Ogni funzione che non si è potuta controllare usciva riportata
come riferimento morto.** 779 su 780 funzioni plpgsql, con un registro del
debito di **due** voci e lo stesso controllo verde in CI.

⭐ **E il crash conferma la diagnosi invece di essere un capitolo a parte**: un
`EXCEPTION WHEN OTHERS` cattura qualunque errore SQL. Se il processo muore lo
stesso, quello che muore è **dentro l'estensione in C** — nessun gestore
PL/pgSQL può intercettare un segfault. Su alcune funzioni `plpgsql_check`
*errava* (i 779), su altre *crollava* (i quattro segnali 11).

**Riparato**, e su tutti e quattro i lati del presidio:

| Dove | Cosa |
| --- | --- |
| `20260910-36` | la forma `error:CHECK-KO:` esce come classe **`NON_MISURATO`**, non più `REALE` |
| `20260910-37` | `vw_riferimenti_morti_da_sanare` **include** la classe nuova |
| `scripts/sql/guardrail_riferimenti_morti.sql` | controllo **(A-bis)**, che solleva **prima** di (A) e (B) |
| `db/pgtap/dbops/test-riferimenti-morti-v1.sql` | test **1-bis**, `plan` da 5 a 6 |
| `scripts/sql/check_funzioni_riferimenti_morti.sql` | la lente lo mostra per primo |

⛔ **Perché la vista deve VEDERE la classe nuova, e non filtrarla via.**
Togliere quelle righe le farebbe sparire, e la vista che «deve restare vuota»
tornerebbe **vuota** — cioè direbbe «nessun riferimento morto» proprio quando
nessuno ha potuto guardare. Sarebbe stato peggio del difetto di partenza: i 779
falsi almeno si vedevano. ⭐ E la conta anche il **digest**, per cui quella
vista è un `REGISTRO` a cadenza settimanale: una vista che torna zero perché lo
strumento è rotto è esattamente ciò che il digest è nato per non fare.

⭐ **La regola era già scritta, nello stesso file.**
`guardrail_riferimenti_morti.sql` gestisce già l'estensione **assente**, e la
gestisce bene: *«NON si passa in silenzio: un guardrail che non misura e non lo
dice è peggio di uno assente»*. Estensione assente → rosso parlante; estensione
presente che si rompe → 779 falsi difetti. Stesso principio, due esiti opposti.
È anche il §6 punto 5 della guida dei presidi: *fai fallire il controllo quando
non può misurare*.

⚠️ **Limite dichiarato**: il ramo `NON_MISURATO` è scritto, compila, e il test
1-bis ne asserisce l'**assenza** — ma da quando esiste **non si è mai acceso**,
perché lo strumento ha ripreso a funzionare (§10.4). Che non produca falsi
positivi è provato; che si accenda quando deve, no.

### 10.4 ⭐ Il crash: due ipotesi ELIMINATE, e una sola resta

Dopo il riavvio della macchina (**19:18**, riavvio del sistema intero — non del
solo servizio) `test-riferimenti-morti-v1.sql` è tornato **verde**: la funzione
ha ricontrollato tutte e **780** le funzioni senza sollevare e senza morire.

Quel fatto elimina due cose, perché **il software non è cambiato**:

| Ipotesi | Verificato dopo il riavvio | Esito |
| --- | --- | --- |
| incompatibilità `plpgsql_check` ↔ PostgreSQL | **2.10** e **18.6**, le stesse di prima | ⛔ **esclusa** |
| una funzione «velenosa» entrata alle 17:24 | `vendite.trgfn_attivita_fatturabili_guard_ba_coerenza` è ancora lì, stessi 2345 caratteri, stesso trigger | ⛔ **esclusa** |
| stato della **macchina** | l'unica variabile che è cambiata | 🔴 **resta** |

**Il fatto datato che la sostiene**, e va letto come indizio, non come prova:

| | |
| --- | ---: |
| RAM totale della macchina | **5,2 GiB** |
| `shared_buffers` | 1 GiB |
| `maintenance_work_mem` | 512 MiB |
| `autovacuum_work_mem` | `-1` → eredita i 512 MiB, **× 3 worker** |

2,5 GiB impegnabili prima di qualunque query, su una macchina che ospita anche
il backend Django. ⭐ E il **quinto** processo morto, alle 18:34, è proprio un
**worker di autovacuum** — quello che si prende i 512 MiB, e che
`plpgsql_check` non lo esegue affatto.

⚠️ **Non è una prova, e va detto**: la memoria esaurita di solito dà `SIGKILL`
(segnale 9), non `SIGSEGV` (11). Ma un'estensione in C che non controlla una
`malloc` fallita dereferenzia NULL, e quello è segnale 11 — spiegherebbe tutti e
cinque i morti con **una** causa invece di due coincidenze.
⚠️ E il log del kernel non aiuta: `kernel.print-fatal-signals = 0`, quindi i
segfault dello spazio utente **non vengono registrati affatto**. Il silenzio lì
era atteso e non significa niente. Nessun errore EDAC/MCE: la memoria non
segnala guasti hardware.

⇒ **Cosa resta da fare, e non è di questo cantiere**: guardare la pressione di
memoria nella finestra 17:30–19:20, e decidere se i parametri del server sono
tarati per una macchina da 5 GiB. Finché non è chiuso, `NON_MISURATO` è la rete
che impedisce al presidio di **mentire** la prossima volta che succede.

### 10.5 ⛔ Che cosa il team DB NON ha fatto, e perché

* **Non ha riprodotto il crash.** Ogni riproduzione manda il cluster in crash
  recovery e butta giù tutte le connessioni, non solo la propria. Il §9.3 aveva
  già deciso così, e la decisione regge.
* **Non ha toccato `vw_riferimenti_morti_rientrati`.** Guarda le voci del
  *registro* che non trovano più un difetto, e nel registro non entrano né
  entreranno voci `NON_MISURATO`: quelle non si registrano come debito, si
  riparano nello strumento.
* **Non ha spento nessuna riga** (§9.3, richiesta 1-bis): `attivo = f` era il
  tampone se la causa non si fosse trovata. Lo strumento funziona, il tampone
  non serve — e una riga spenta è un controllo che non presidia.
* **Le tre righe 🔶 del §7.4** restano da confermare quando i loro cantieri le
  toccheranno (`vw_af_senza_giro`, `vw_run_senza_attore`,
  `vw_processi_dominio_su_pgagent`). Sono dichiarate nelle note del catalogo:
  è debito scritto, non nascosto.

*Risposta DB del 2026-09-10. Le misure sono letture del catalogo PostgreSQL e
del database di sviluppo di quel giorno: valgono come controesempio, non come
motivo. Il motivo sta sul modello, ed è che un presidio che non sa distinguere
«non ho trovato difetti» da «non ho potuto guardare» dice la cosa più pericolosa
che un presidio possa dire.*
