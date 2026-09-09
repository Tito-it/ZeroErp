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

*Brief aperto il 2026-09-09 dal backend. Le misure sono letture del catalogo
PostgreSQL e conteggi sulle viste di `dbops` del database di sviluppo, datati
2026-09-09, e valgono come controesempio — non come motivo. Il motivo sta sul
modello: un presidio senza destinatario non presidia.*
