# Brief DB — I presidi parlano a chi deve agire: cosa significa, cosa fare, chi lo fa

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6), che **attende** la consegna DB.
> **Origine:** §5-bis del collaudo in-app dell'osservabilità
> ([collaudo-in-app-osservabilita-giornale-errori-pallino.md](../work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md),
> chiuso il 2026-10-06), trovato a video da Tid il 2026-09-19.
> **Decisioni:** ⏳ **da confermare da Tid** (§3). Le proposte sono marcate.
> **Stato:** ✏️ scritto, da applicare.

## 1. Perché

Il pannello **Strumenti → Diagnostica → Processi automatici** mostra sotto ogni
presidio il `COMMENT` della vista (`presidi_repository.py`, `obj_description`), e
il digest mostra la `nota` di `presidi.csv`. Sono due testi scritti **per chi
mantiene il presidio**: spiegano perché esiste, citano i brief, dichiarano
perimetro e cadenza. Devono restare così, perché quello è il loro lettore.

Il pannello però lo legge **chi deve agire**, e quella persona ha due domande sole:
*cosa vuol dire* e *cosa devo fare*. Il pannello risponde alla domanda sbagliata
perché l'unico testo che ha in mano è stato scritto per un altro lettore.

Il caso del 19-09: con due presidi accesi
(`dbops.vw_articoli_a_magazzino_prontezza` in `NESSUNO_MARCATO` e
`dbops.vw_lotti_fermi_da_guardare` con 16 righe), il testo a video era
*«complicato da capire»*. La stessa cosa detta in due righe:

* «nessun articolo è gestito a magazzino: marcane uno dal drawer articolo»;
* «sono lotti di prova con critiche aperte: rilanciali o annullali»

ha reso ovvia l'azione, e i due presidi si sono spenti in pochi minuti.

Manca quindi un pezzo del catalogo: **il testo per chi agisce**. È una
lacuna del modello, non della grafica: senza quel dato a DB nessuna
schermata può mostrarlo.

## 2. Cosa manca, sul modello

Per ogni presidio che può accendersi servono **tre** fatti, non uno:

| Fatto | Cosa risponde | Esempio (`vw_lotti_fermi_da_guardare`) |
| --- | --- | --- |
| **Significato** | *Cosa vuol dire una riga*, in parole di chi usa l'applicazione | «Ci sono giri di fatturazione fermi da oltre un'ora, con errori o critiche aperte, che nessuno ha rilanciato o annullato.» |
| **Azione** | *Cosa fare per spegnerlo*, all'imperativo | «Apri ogni lotto indicato: correggi le critiche e rilancialo, oppure annullalo se era di prova.» |
| **Chi agisce** | *Chi lo può spegnere*: chi legge, chi gestisce il server, o lo sviluppo | `AMMINISTRATORE` |

Il §5-bis proponeva **una** colonna (`azione_operatore`). Scrivendo le frasi
presidio per presidio (§5) sono venute fuori due cose:

1. **Il significato e l'azione sono due domande diverse.** In metà dei casi
   l'azione è «avvisa lo sviluppo»: senza il significato accanto, chi legge non
   sa *cosa* deve riferire.
2. **«Chi agisce» è un dato, non una frase.** Dei 43 presidi che possono
   accendersi, circa due terzi non li spegne chi legge il pannello: servono lo
   sviluppo o il sistemista. Se lo si scrive dentro la frase, il pannello non
   può distinguere «tocca a te» da «inoltra» (per esempio con un badge, o
   ordinando prima quello che puoi sistemare tu), e il digest non può
   raggrupparli.

## 3. Le decisioni (⏳ da confermare da Tid)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | Dove vivono significato e azione? | **A DB, in una tabella di testi per lingua** (`dbops.presidi_testi`, §4.1). Non in chiavi i18n del FE: il testo serve anche al **digest**, che il BE scrive per email e senza locali. Il precedente è `config.messaggi_errore`, che tiene a DB per lingua il testo per l'operatore (`messaggio`, `causa`, `soluzione`) e lo legge sia il BE sia il FE. La regola «il testo non si scrive in SQL» (linee-guida-sql §12.2) riguarda i tooltip di `available_actions`, che legge solo il FE. |
| D-2 | Per lingua da subito, o colonne in italiano su `dbops.presidi`? | **Per lingua da subito**, con l'italiano obbligatorio. Spostare il testo in una tabella figlia più avanti sarebbe una migrazione, mentre la chiave `lingua` adesso non costa niente (sviluppo concentrico). |
| D-3 | Quali valori per «chi agisce»? | **Tre**: `AMMINISTRATORE` (si spegne dall'applicazione), `SISTEMISTA` (server, servizi, schedulatori), `SVILUPPO` (serve una modifica al codice o al database). Sono tre persone diverse, e il testo dell'azione cambia per ognuna. |
| D-4 | Le **misure** che sono larghe per costruzione hanno un conteggio che non indica un problema: cosa se ne fa? | **Rilievo, da decidere a parte** (§7): non lo blocca questo brief. Per questo brief basta dar loro il testo onesto: «misura per lo sviluppo, il numero non indica un problema». |

## 4. Richiesta

### 4.1 La tabella dei testi

`dbops.presidi_testi`, una riga per (presidio, lingua):

| Colonna | Tipo | Note |
| --- | --- | --- |
| presidio | riferimento a `dbops.presidi` | Per il seed, la chiave naturale è `vista` (`uq_presidi_vista`), **mai l'`id`** (nessun ID numerico cablato). La forma della FK la sceglie il team DB secondo le linee guida |
| lingua | text | Stesso dominio di `config.messaggi_errore.lingua` |
| significato | text NOT NULL | Una o due frasi, nel linguaggio dell'applicazione. `CHECK` non vuota |
| azione | text NOT NULL | All'imperativo. `CHECK` non vuota |
| colonne di audit | | come il resto di `dbops` |

* `UNIQUE (presidio, lingua)`.
* Seed: un CSV accanto a `presidi.csv` (`80_data/sql/dbops/presidi_testi.csv`,
  colonne `vista,lingua,significato,azione`), con le righe `it` del §5.
* `COMMENT` sulla tabella e sulle colonne: questi testi sono scritti **per chi
  agisce**; il `COMMENT` della vista e la `nota` restano per chi mantiene il
  presidio, e **non si riscrivono**.
* `GRANT SELECT` a `zeroerp_app` (il pannello e il digest la leggono).

### 4.2 «Chi agisce» sul catalogo

Colonna `chi_agisce` su `dbops.presidi`:

* `CHECK chk_presidi_chi_agisce` sui tre valori di D-3;
* `CHECK chk_presidi_chi_agisce_se_allarma`:
  `natura = 'INVENTARIO' OR chi_agisce IS NOT NULL`. Un presidio che può
  accendersi non nasce senza sapere a chi tocca. Un `INVENTARIO` non si accende,
  quindi può restare `NULL`;
* valori nel `presidi.csv` (colonna nuova), dalla colonna *Chi* del §5.

### 4.3 La completezza dei testi

Un `CHECK` non può guardare un'altra tabella, quindi lo garantisce il **pgTAP**
(§4.4): ogni presidio **attivo, non obsoleto e non `INVENTARIO`** ha la riga
`it`. È il verso che conta: la prossima vista di presidio non entra a catalogo
senza le sue due frasi, e l'errore sta nella build, non a video.

### 4.4 Test (pgTAP)

1. Ogni presidio attivo, non obsoleto e non `INVENTARIO` ha una riga `it` in
   `dbops.presidi_testi` (il messaggio di fallimento nomina le viste scoperte).
2. Nessuna riga di testo punta a un presidio obsoleto (è il verso del ritiro:
   un testo orfano è una frase che nessuno legge più).
3. `chk_presidi_chi_agisce_se_allarma` rifiuta un non-`INVENTARIO` con
   `chi_agisce` NULL e accetta un `INVENTARIO` con `chi_agisce` NULL.
4. `chk_presidi_chi_agisce` rifiuta un valore fuori dominio.
5. `zeroerp_app` legge `dbops.presidi_testi`.

## 5. I testi proposti (`it`)

> ⚠️ **Le frasi sono una proposta della sessione BE/FE**, scritta leggendo la
> `nota` e il `COMMENT` di ogni vista. **Il team DB le verifica una per una**:
> conosce il rimedio vero, e una frase che indica l'azione sbagliata è peggio
> della prosa tecnica di oggi. Le correzioni vanno nel §8, con il motivo.
>
> Regole con cui sono scritte: niente nomi di tabelle o di funzioni; le
> schermate si chiamano come nel menu; l'azione dice **dove** si fa; quando il
> rimedio è «capire chi ha scritto», l'azione dice **cosa non fare** (correggere
> il dato a mano).

### 5.1 Natura ZERO — devono restare vuoti

| Vista | Chi | Significato | Azione |
| --- | --- | --- | --- |
| `dbops.vw_coda_lavori_da_guardare` | AMMINISTRATORE | Ci sono lavori in coda falliti, rimasti a metà o mai partiti da oltre un'ora. | Apri la coda lavori e rilancia o annulla quelli in errore. Se ci sono lavori mai presi, il servizio che li esegue è fermo: avvisa chi gestisce il server. |
| `dbops.vw_emittenti_non_serviti` | AMMINISTRATORE | Un processo automatico non lavora per un'azienda emittente perché manca il suo utente tecnico: il processo gira, non vede i dati di quell'azienda e chiude senza errori. Le sue fatture non partono. | Crea l'utente tecnico del processo per quell'azienda emittente. |
| `dbops.vw_operatori_senza_emittente` | AMMINISTRATORE | Ci sono operatori senza nessuna azienda emittente assegnata: entrano nell'applicazione e non vedono nessun dato. | Dalla lista Operatori assegna l'azienda emittente, oppure disattiva l'operatore se non deve più entrare. |
| `dbops.vw_processi_programmazione_da_guardare` | AMMINISTRATORE | Un processo automatico non è partito quando doveva, oppure è partito senza lasciare traccia della sua corsa. | Apri il processo indicato e guarda l'ultima corsa. Se non c'è nessuna corsa recente, il programmatore dei processi è fermo: avvisa chi gestisce il server. |
| `dbops.vw_processi_dominio_senza_identita` | SVILUPPO | La configurazione dei processi automatici non torna: un processo non ha un utente con cui lavorare, oppure un utente tecnico non è usato da nessun processo. | Avvisa lo sviluppo indicando il processo o l'utente elencato. |
| `dbops.vw_liste_multi_emittente_non_certificate` | SVILUPPO | Una lista è dichiarata adatta a più aziende emittenti, ma non mostra in nessuna colonna a quale azienda appartiene ogni riga. | Avvisa lo sviluppo: la lista va completata con la colonna dell'azienda emittente, oppure la dichiarazione va tolta. |
| `dbops.vw_parameter_fk_surrogate_dangling` | AMMINISTRATORE | Alcuni parametri di configurazione puntano a un valore che non esiste più. | Apri i parametri indicati e scegli un valore valido. |
| `dbops.vw_riferimenti_morti_rientrati` | SVILUPPO | Il registro dei difetti noti del database contiene voci già risolte. | Avvisa lo sviluppo: quelle voci vanno tolte dal registro. Nessuna urgenza. |
| `dbops.vw_processi_dominio_su_pgagent` | SVILUPPO | Un processo che tocca i documenti è tornato a girare nello schedulatore del database, dove non ha un'identità e i suoi errori non arrivano a nessuno. | Avvisa lo sviluppo: è una regressione nella configurazione dei processi. |
| `dbops.vw_processi_che_bypassano` | SISTEMISTA | Un utente del database usato dall'applicazione può scavalcare la separazione dei dati fra aziende emittenti, e nessuno l'ha dichiarato. | Avvisa subito chi gestisce il database: è un rischio di sicurezza. |
| `dbops.vw_processi_dominio_senza_emittente` | SVILUPPO | Un processo automatico non sa a quale azienda emittente appartengono i dati che tocca, quindi non può limitarsi ai dati giusti. | Avvisa lo sviluppo indicando il processo elencato. |
| `dbops.vw_processi_dominio_senza_difesa` | SVILUPPO | Una tabella con dati di più aziende emittenti non è protetta dalla separazione dei dati. | Avvisa subito lo sviluppo: è un rischio di sicurezza. |
| `dbops.vw_rls_perimetro_scoperto` | SVILUPPO | Una tabella che dovrebbe separare i dati per azienda emittente non lo fa, oppure il registro dei difetti noti ha una voce già risolta. | Avvisa lo sviluppo indicando la tabella elencata. |
| `maintenance.vw_job_run_da_guardare` | SISTEMISTA | Un'attività programmata è fallita all'ultima esecuzione, è rimasta bloccata a metà, oppure fallisce a intermittenza. | Leggi l'errore dell'ultima corsa. Se riguarda il server (spazio, servizio fermo, connessione), avvisa chi gestisce il server; altrimenti avvisa lo sviluppo. |
| `dbops.vw_fatture_stampa_coda_da_guardare` | AMMINISTRATORE | Ci sono stampe di fatture fallite, bloccate a metà o mai partite da oltre un'ora. | Apri la coda stampe e rilancia quelle in errore. Se ci sono stampe mai prese, il servizio di stampa è fermo: avvisa chi gestisce il server. |
| `dbops.vw_email_da_guardare` | SISTEMISTA | Ci sono email in attesa di invio da oltre un'ora. | L'invio automatico delle email è fermo o non riesce a svuotare la coda: avvisa chi gestisce il server. In Log Email vedi quali sono. |
| `dbops.vw_storico_scope_da_dichiarare` | SVILUPPO | Per la storia delle modifiche di alcune tabelle non è ancora deciso quali aziende emittenti possono vederla. | Avvisa lo sviluppo. Nessuna urgenza. |
| `dbops.vw_magazzino_valore_giacenza_divergente` | SVILUPPO | Per alcuni articoli il valore di magazzino non corrisponde alla somma dei movimenti: qualcosa ha scritto senza passare dalla procedura. | Non ricalcolare il valore a mano: avvisa lo sviluppo, che deve prima capire chi ha scritto il dato. |
| `dbops.vw_sorgenti_orfane` | SVILUPPO | Alcune registrazioni rimandano a un documento di origine che è stato cancellato. | Non cancellare le registrazioni: avvisa lo sviluppo, che deve capire chi ha cancellato il documento. |
| `dbops.vw_articoli_a_magazzino_prontezza` | AMMINISTRATORE | Nessun articolo è gestito a magazzino, quindi il magazzino non registra niente. | Dal drawer dell'articolo, marca come gestiti a magazzino gli articoli che lo sono. |
| `dbops.vw_lotti_fermi_da_guardare` | AMMINISTRATORE | Ci sono giri di fatturazione fermi da oltre un'ora, con errori o critiche aperte, che nessuno ha rilanciato o annullato. | Apri ogni lotto indicato: correggi le critiche e rilancialo, oppure annullalo se era di prova. |
| `dbops.vw_lotti_chiusi_con_errori_da_guardare` | SVILUPPO | Un lotto di fatturazione risulta chiuso con successo ma contiene documenti in errore. | Avvisa lo sviluppo indicando il lotto: non avrebbe dovuto chiudersi così. Non riaprirlo e non correggere i documenti prima della verifica. |
| `dbops.vw_ddt_emessi_senza_scarico` | SVILUPPO | Alcune bolle emesse non hanno scaricato la merce dal magazzino, quindi la giacenza è sbagliata. | Non correggere la giacenza a mano: avvisa lo sviluppo indicando le bolle elencate. |
| `dbops.vw_resi_confermati_senza_carico` | SVILUPPO | Alcuni resi confermati non hanno ricaricato la merce in magazzino, quindi la giacenza non vede la merce tornata. | Non correggere la giacenza a mano: avvisa lo sviluppo indicando i resi elencati. |
| `dbops.vw_emittenti_regime_non_confermato` | AMMINISTRATORE | Per alcune aziende emittenti nessuno ha confermato il regime fiscale: le fatture potrebbero uscire con un'IVA sbagliata. | Apri l'azienda emittente, verifica il regime fiscale e salvalo: il salvataggio lo conferma. |
| `dbops.vw_credenziali_da_sanare` | AMMINISTRATORE | Ci sono credenziali di accesso senza nessuna veste, oppure usate sia da una persona sia da un processo automatico. | Dalla lista Operatori dai una veste alla credenziale o cancellala. Se è usata anche da un processo, separa le due vesti su credenziali diverse. |

### 5.2 Natura REGISTRO e LAVORAZIONE — devono calare

| Vista | Chi | Significato | Azione |
| --- | --- | --- | --- |
| `dbops.vw_riferimenti_morti_da_sanare` | SVILUPPO | Nel database ci sono funzioni che richiamano oggetti che non esistono più: falliranno quando verranno eseguite. | Avvisa lo sviluppo. |
| `dbops.vw_af_senza_giro` | AMMINISTRATORE | Ci sono attività fatturabili che nessun giro di fatturazione ha ancora preso in carico: se restano così, non verranno fatturate. | Lancia il giro di fatturazione che le comprende. Se il numero non cala da un giro all'altro, avvisa lo sviluppo. |
| `dbops.vw_eventi_non_dichiarati` | SVILUPPO | L'applicazione ha registrato eventi con un codice che il catalogo degli eventi non conosce. | Avvisa lo sviluppo: il codice va aggiunto al catalogo. |
| `dbops.vw_fk_con_indice_missing_policy` | SVILUPPO | Manutenzione del database: alcuni collegamenti fra tabelle vanno portati sotto la gestione automatica degli indici. | Nessuna urgenza: lo sviluppo lancia la procedura che li registra. |
| `dbops.vw_indici_ridondanti_prefisso` | SVILUPPO | Manutenzione del database: ci sono indici inutili, perché già coperti da altri. | Nessuna urgenza: lo sviluppo li rimuove con una modifica al database. |
| `dbops.vw_duplicate_indexes` | SVILUPPO | Manutenzione del database: ci sono indici duplicati. | Nessuna urgenza: lo sviluppo li rimuove con una modifica al database. |
| `dbops.vw_run_senza_attore` | SVILUPPO | Alcune attività programmate non registrano chi le ha eseguite. | Nessuna urgenza: molte si sistemano da sole alla prossima corsa notturna, quelle che restano le sistema lo sviluppo. |
| `dbops.vw_fk_senza_indice` | SVILUPPO | Manutenzione del database: alcuni collegamenti fra tabelle non hanno un indice. Li sistema l'automazione al prossimo aggiornamento del database. | Nessuna azione. Se restano dopo un aggiornamento, avvisa lo sviluppo. |
| `dbops.vw_magazzino_movimenti_senza_costo` | AMMINISTRATORE | Ci sono carichi di magazzino registrati senza costo, quindi il valore medio degli articoli si abbassa. | Controlla i carichi indicati: dove il costo è noto, indicalo nei carichi successivi. |
| `dbops.vw_codici_errore_forme_condizione` | SVILUPPO | Strumento di analisi per lo sviluppo: il numero non indica un problema. | Nessuna azione. |

### 5.3 Natura CANCELLO — fermati dai controlli di rilascio

| Vista | Chi | Significato | Azione |
| --- | --- | --- | --- |
| `dbops.vw_codici_errore_da_dichiarare` | SVILUPPO | Misura per lo sviluppo, verificata ai controlli di rilascio: il numero cresce con ogni codice d'errore nuovo e non indica un problema. | Nessuna azione. |
| `dbops.vw_bersagli_non_dichiarati` | SVILUPPO | Il programma usa un tipo di collegamento che il catalogo non conosce: un messaggio porterebbe a una schermata che non esiste. | Avvisa lo sviluppo: di solito lo ferma il controllo di rilascio, quindi la modifica è arrivata senza passarci. |
| `dbops.vw_punti_primo_motivo` | SVILUPPO | Misura per lo sviluppo, verificata ai controlli di rilascio: il numero non indica un problema. | Nessuna azione. |
| `dbops.vw_audit_log_scrittori_fuori_perimetro` | SVILUPPO | Una funzione di un'area di lavoro scrive nel registro tecnico delle esecuzioni, che non deve contenere dati aziendali. | Avvisa lo sviluppo: di solito lo ferma il controllo di rilascio, quindi la modifica è arrivata senza passarci. |
| `dbops.vw_stati_check_da_sanare` | SVILUPPO | Uno stato previsto dal database non viene mai scritto da nessuno, oppure il registro degli stati ha una voce non più necessaria. | Avvisa lo sviluppo: di solito lo ferma il controllo di rilascio, quindi la modifica è arrivata senza passarci. |
| `dbops.vw_punti_canale_campo` | SVILUPPO | Misura per lo sviluppo, verificata ai controlli di rilascio: il numero non indica un problema. | Nessuna azione. |
| `dbops.vw_magazzino_dipendenze_inverse` | SVILUPPO | Il magazzino dipende da una parte dell'applicazione da cui non deve dipendere. | Avvisa lo sviluppo: di solito lo ferma il controllo di rilascio, quindi la modifica è arrivata senza passarci. |

### 5.4 Natura INVENTARIO — nessun testo

Le nove viste `INVENTARIO` (`vw_trigger_functions`, `vw_processi_programmazione`,
`vw_processi_roster`, `vw_catalogo_oggetti`, `vw_function_list`,
`vw_non_editable_fields`, `vw_diag_v_clienti_links`, `vw_stati_check_scrittori`,
`vw_funzioni_check_codici`) non si accendono: niente riga di testo e
`chi_agisce` NULL. Se un giorno si volesse spiegare *a cosa servono*, sarebbe una
terza domanda («cos'è»), non l'azione.

## 6. Dopo la consegna: BE/FE (dev/backend-tid)

| Dove | Cosa |
| --- | --- |
| `apps/core/db/presidi_repository.py` | `_COLONNE_CATALOGO` legge `chi_agisce` e, con un `LEFT JOIN` su `dbops.presidi_testi`, `significato` e `azione`. La lingua si sceglie come per `config.messaggi_errore`, con ripiego su `it`. `RigaPresidio` prende i tre campi. Mirror dichiarato di `CHI_AGISCE` accanto a `NATURE`, presidiato in `test_presidi_catalogo.py` contro il `CHECK` vero (`db_e2e.valori_check`), come gli altri tre |
| `apps/core/services/presidi_digest.py` | `VocePresidio` prende `significato`, `azione`, `chi_agisce`. Nel digest, sotto ogni presidio acceso, **prima** significato e azione, **poi** la nota tecnica. Raggruppamento per `chi_agisce`: prima quello che si spegne dall'applicazione |
| `PresidiProcessiPanel.vue` / `PresidioChip.vue` | La riga accesa mostra **prima** l'azione, poi il significato, poi un badge col *chi* (`AMMINISTRATORE` = «Puoi sistemarlo tu», `SISTEMISTA` = «Da segnalare a chi gestisce il server», `SVILUPPO` = «Da segnalare allo sviluppo», chiavi i18n `amministrazione.processi.chi_agisce.*`). La descrizione tecnica di oggi resta, chiusa, sotto «Dettaglio tecnico». Senza testo (presidio vecchio, lingua mancante) si ripiega sulla descrizione di oggi, mai sul vuoto |
| Test | BE: proiezione dei tre campi e ripiego senza testo. FE: spec del chip con azione prima e descrizione chiusa; badge per ciascuno dei tre valori |

## 7. Rilievo per il team DB (non blocca il brief)

Quattro viste sono **misure larghe per costruzione**: il loro conteggio non
dice un difetto, eppure il pannello lo mostra come un numero da guardare.

* `vw_codici_errore_forme_condizione` (`LAVORAZIONE`): la `nota` dice che un
  `count(*)` qui «è un numero senza significato»;
* `vw_codici_errore_da_dichiarare` (`CANCELLO`): «il suo numero non è il debito»;
* `vw_punti_primo_motivo` e `vw_punti_canale_campo` (`CANCELLO`): misure su cui
  un cancello (pgTAP o test del backend) applica una regola, ma che non devono
  restare vuote.

Una misura il cui numero non vuol dire niente non è `LAVORAZIONE` né
`CANCELLO` nel senso del pannello: o è `INVENTARIO`, o la natura che il
pannello mostra va separata dalla natura che il cancello usa. La decisione
spetta al team DB e a Tid (D-4); intanto il §5 dà loro il testo onesto.

## 8. Consegna DB

*(da compilare dal team DB: changeSet, correzioni ai testi del §5 col motivo,
esito pgTAP)*
