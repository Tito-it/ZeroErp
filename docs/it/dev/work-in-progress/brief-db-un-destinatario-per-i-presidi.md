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
