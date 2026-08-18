# Bonifica baseline pgTAP — perimetro `vendite`

> Cantiere aperto il 2026-08-18 · perimetro DB (`dev/db-tid`)
> Registro: [`db/pgtap/baseline-rossi.tsv`](../../../db/pgtap/baseline-rossi.tsv)
> Precedenti chiusi: `work-done/brief-db-pgtap-runner-rls-baseline.md`,
> `work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md`

## Stato

| | inizio 2026-08-18 | ora |
|---|---|---|
| rossi `vendite` | 12 su 189 | **5** |
| registro complessivo | 45 | **38** |
| `dbops`, `pagamenti`, `catalogo` | zero | zero |

## Il principio che ha retto tutto il lavoro

Un rosso di baseline ha tre esiti possibili, non due, e vanno tenuti distinti
perche' solo il primo e' «sistemare un test»:

1. **Riparare** — il soggetto del test e' vivo, e' morta la *scorciatoia* con
   cui la fixture ci arrivava. E' il caso della maggioranza.
2. **Rivoltare** — il test descrive un ramo che nessun percorso attraversa piu'.
   Non si ripara e non si cancella: si riscrive su cio' che accade davvero, e si
   segnala il ramo morto. (Memoria: *un ramo si verifica dal percorso che lo
   attraversa, non dal codice che lo dichiara*.)
3. **Ritirare** — l'oggetto collaudato non esiste piu'. Se al suo posto e'
   subentrato un altro presidio, l'asserzione **si sposta** invece di sparire:
   toglierla e basta lascerebbe scoperto cio' che oggi conta.

## Fatto

### Famiglia C — guard tipo doc su `commesse_attivita` (2 file, RIPARATI)

`test-fn-list-commessa-attivita-v1` (14/14) e
`test-fn-list-commesse-emittibili-fatturazione-immediata-v1` (6/6).

Le fixture creavano righe `APPROVATA + NON_EMESSA` senza
`p_tipo_doc_fiscale_id`. Da `trg_commesse_attivita_a10_guard_tipo_doc_emittibile`
quello stato non e' piu' ammesso: la riga sarebbe invisibile a
`fn_list_emittibili_lane`, cioe' fatturato perso in silenzio. Zero contenuto di
design: si passa il parametro.

### Famiglia B — guard commessa su `attivita_fatturabili` (4 file)

`test-attivita-prezzo-bloccato-v1` (5/5), `test-fatturazione-draft` (6/6),
`test-fatturazione-reset-lotto-draft` (12/12), `test-attivita-fatturabili` (36/36).

⭐ **Il flag `attivita_fatturabili_require_commessa` non c'entrava.**
`commessa_id` e `commessa_attivita_id` sono **NOT NULL** sulla tabella: spegnere
il flag non riaprirebbe il percorso, darebbe `23502` invece di `P0001`. Il guard
arriva prima solo perche' e' un BEFORE ROW. L'attivita' senza commessa non e'
una policy accendibile, e' una colonna.

**La ricetta** (verificata prima di applicarla, sonda in `BEGIN…ROLLBACK`): il
modello NON e' `test-attivita-guardrail-commessa-v1` — che passa da
`fn_get_or_create_commessa` + `fn_link_commessa_sorgente` +
`fn_upsert_commessa_attivita` a 40 parametri e trascina il guard della sorgente
polimorfa — ma **`test-vw-dash-competenza-v1`**: `INSERT` diretti in
`vendite.commesse` e `vendite.commesse_attivita`, `sorgente_tipo_id` a `NULL`.
Non serve il setup di scope emittente per scrivere in `vendite.commesse` come
applicazione.

**Gli strati incontrati**, in ordine, perche' il conteggio dei rossi cala piu'
lentamente del lavoro fatto:

1. la coppia commessa — che **disarma anche**
   `trgfn_attivita_fatturabili_guard_ba_coerenza`, commessa-aware, che fa
   `RETURN NEW` quando `commessa_attivita_id IS NOT NULL`;
2. `competenza_dal` / `competenza_al` sono diventate **NOT NULL** e nessuna
   fixture le passava;
3. `trgfn_attivita_fatturabili_normalize` e' commessa-aware (vedi 🔴 sotto);
4. la UNIQUE sulla sorgente non esiste piu' (vedi 🔴 sotto);
5. `vendite.attivita_fatturabili_lotti` e' stata dismessa (vedi 🔴 sotto).

**Trappola evitata su `test-attivita-fatturabili`**:
`uq_attivita_fatturabili_commessa_attivita` e' una UNIQUE piena, 1:1. Le 13
righe hanno **13 attivita' di commessa distinte**, comprese quelle degli INSERT
che devono fallire: condividerne una avrebbe fatto scattare *quella* unique al
posto del `23503`/`23514` atteso — un verde preso dall'indice sbagliato.

**Bonus**: in tre file i riferimenti sceglievano articolo, istanza utility e
billing account da `LIMIT 1` **indipendenti**, senza garanzia che l'istanza
appartenesse a quel BA. Ora il soggetto si sceglie una volta sola.

## 🔴 Tre segnalazioni fuori perimetro test

### 1. Il ramo standard di `trgfn_attivita_fatturabili_normalize` e' codice morto

La funzione e' commessa-aware: quando `commessa_attivita_id IS NOT NULL` fa
`RETURN NEW` in testa e salta **tutto** il blocco delle competenze — «lo
snapshot CA e' gia' completo», dice il suo commento. Essendo quella colonna
NOT NULL, **il ramo standard non e' raggiungibile da nessun percorso**:
normalizzazione di `competenza_mese` al primo del mese, derivazione da
`posticipa_al`, default di `competenza_dal`/`competenza_al`. Due asserzioni di
`test-attivita-fatturabili` lo collaudavano; ora verificano il comportamento
reale (la riga viene **respinta** dal CHECK / dal NOT NULL, perche' il
normalizzatore non copre piu' per chi scrive). Il codice morto resta: e' una
funzione condivisa, va potata in un passaggio suo.

### 2. `lotto_attivita_id` e' una colonna orfana, in due tabelle

`vendite.attivita_fatturabili_lotti` e' stata **dismessa il 2026-08-04** con la
potatura delle attivita' di pipeline morte. Sono rimaste
`attivita_fatturabili.lotto_attivita_id` e `attivita_consumi.lotto_attivita_id`:
**nessuna tabella padre, nessuna FK**. Oggi accettano qualunque numero. O
tornano ad avere un padre o vanno via.

### 3. La UNIQUE su `(sorgente_tipo_id, sorgente_uid)` non esiste piu'

Sulla tabella ci sono solo `pk`, `uq_..._uid` e
`uq_attivita_fatturabili_commessa_attivita`. La chiave si e' spostata sulla
coppia commessa/attivita' — stessa storia gia' registrata da
`test-drop-uq-commesse-attivita-src-uid-partial-v1`. L'asserzione e' stata
**spostata** sulla chiave viva, non tolta.

## `anagrafiche` — 27 rossi a 17 (2026-08-19)

Lo schema col 71% del debito. **Non erano 23 bug: era una premessa decaduta**,
la stessa in tutti i file piu' vecchi della suite:

> «uso un identificativo fisso, e alla prossima corsa cancello e ricomincio»

Oggi un soggetto non si cancella (`dbops.automation_delete_block_ruoli` dal
2026-01-23 su 8 tabelle di ruolo, piu' FK RESTRICT), quindi la «pulizia
d'ingresso» in testa al file falliva e il file moriva **prima della prima
asserzione**. ⛔ E i residui non vanno cancellati: sotto i 16 soggetti di prova
ci sono 37 istanze utility e 16 clienti.

**Il rimedio e' non collidere invece di cancellare.** Dieci file chiusi, **96
asserzioni** che prima non venivano eseguite affatto.

### Gli strati, in ordine di comparsa

Si presentano sempre in quest'ordine, ed e' il motivo per cui il conteggio dei
rossi cala molto piu' lentamente del lavoro fatto:

1. pulizia d'ingresso ormai impossibile (delete-block, FK RESTRICT);
2. identificativo fiscale bruciato da un residuo
   (`uq_soggetto_idstato_id_fiscale_univoco`);
3. colonne diventate NOT NULL dopo la scrittura del test (`competenza_dal/al`,
   `codice_fiscale` sulle PG, `categoria_cliente_id` su billing_account);
4. ⭐ **la finestra differita** — vedi sotto;
5. valori con UNIQUE proprio (REA, codice SDI, PEC, civico normalizzato);
6. `finish()` rimasto dopo il `ROLLBACK` (pgTAP perde la sua temp table).

### ⭐ La finestra differita, che e' la parte che non si indovina

Su `anagrafiche.soggetti` ci sono **tre guard `DEFERRABLE INITIALLY DEFERRED`**
(dati societari, indirizzi, contatti). Sono differiti **apposta**: un soggetto
e' una SAGA — testata, dati societari, indirizzi obbligatori, contatto — e la
completezza ha senso verificarla quando la saga e' finita.

Ma il preambolo obbligatorio dei pgTAP impone `SET CONSTRAINTS ALL IMMEDIATE`
(guardrail in CI), e con IMMEDIATE quei guard scattano sul **primo** INSERT,
cioe' prima che la saga possa esistere. Serve aprire la finestra
(`ALL DEFERRED`) e **richiuderla** (`ALL IMMEDIATE`) a saga completa.

⚠️ La richiusura non e' facoltativa: senza, la chiusura in `ROLLBACK` porta via
i vincoli differiti **non verificati** e il test e' verde per sottrazione.

### Gli helper — `dbops`, non `script`

`20260818-76` e `20260818-77`, cinque funzioni. In `dbops` e non in `script`
non per tassonomia (i permessi sono identici) ma perche' **fabbricano dati di
anagrafica**: una funzione che fa `INSERT INTO anagrafiche.soggetti` dentro lo
schema in cui l'applicazione chiama e' una tentazione che qualcuno raccoglie.

| funzione | cosa fa |
| --- | --- |
| `fn_pgtap_piva_libera()` | P.IVA valida e mai usata |
| `fn_pgtap_piva_libera(p_skip)` | ⚠️ la stessa, saltando le prime N — **serve**: due chiamate nella stessa ISTRUZIONE tornano lo stesso valore, perche' e' l'insert a occupare un identificativo e dentro una sola SELECT non ce n'e' |
| `fn_pgtap_cf_libero()` | codice fiscale valido e libero. Il carattere di controllo non si calcola, si **cerca** provando l'alfabeto e chiedendo a `script.fn_valida_codice_fiscale`: reimplementare l'algoritmo vorrebbe dire tenerne due copie |
| `fn_pgtap_crea_soggetto_pg()` | la saga completa, dentro la finestra differita |
| `fn_pgtap_crea_soggetto_ruolo()` | il layer RUOLO, che ha matrice e guard **suoi** — un indirizzo di soggetto non soddisfa il guard del ruolo |

⭐ Non esisteva niente del genere: gli unici `fn_pgtap_*` impostano il
**contesto** di sessione. `create-cliente.sql` si era scelto un CF a mano, con
un commento che descrive parola per parola questo problema.

### 🔴 Reperti fuori perimetro test

1. **Il gestore del sistema e' un residuo di pgTAP.** In tutto il database c'e'
   un solo `anagrafiche.gestori`: `Gestore Zero ERP - Test pgTAP`, del
   2025-11-25, lasciato dal COMMIT di `create-soggetto-gestori`. E' un
   singleton globale: se qualcosa risolve «il gestore» per valuta o
   `cd_prod_software`, sta leggendo una riga di prova.
2. ✅ **Messaggio d'errore che manda fuori strada — CORRETTO** (`20260819-01`,
   vedi sotto).
3. **`forma_giuridica` non esiste piu'** su `anagrafiche.dati_societari` (oggi
   `forma_giuridica_id`, FK): un test la inseguiva ancora.

### ✅ Il messaggio che mandava fuori strada — chiuso il 2026-08-19

Due guard **diversi** condividevano `E_TIPO_INDIRIZZO_NON_PERMESSO`:

* `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` — layer RUOLO, legge
  `config.tipi_ruolo_tipi_indirizzo`;
* `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` — layer SOGGETTO, legge
  `config.tipi_soggetto_dettaglio_tipi_indirizzo`.

Il messaggio e' scritto per il primo: *«Tipo indirizzo %s non permesso per
tipo_ruolo_id %s (soggetto_ruolo_id=%s)»*, nota *«Verificare
config.tipi_ruolo_tipi_indirizzo»*.

⚠️ **L'arita' torna** — tre segnaposto, tre valori — quindi niente si rompe e
nessun cancello se ne accorge. Il guasto e' **semantico**: sul layer soggetto
il secondo valore e' un `tipo_soggetto_dettaglio_id` e il terzo un
`soggetto_id`, ma il messaggio li battezza altrimenti e manda a controllare una
tabella dove il problema non c'e' e non ci sara' mai. ⭐ **Un messaggio
plausibile e falso costa piu' di un messaggio assente**: chi lo legge non
sospetta niente e cerca dove gli e' stato detto. E' successo davvero durante
questa bonifica — tre query buttate a inseguire un ruolo «Gestore» che con la
riga in errore non c'entrava nulla.

**Corretto** con un codice proprio del layer soggetto,
`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` (id messaggio 929), e il guard
che lo usa (`20260819-01`). Il codice vecchio resta al guard dei ruoli, per cui
e' sempre stato giusto: non si generalizza il messaggio a entrambi, perche' uno
buono per due casi non e' preciso per nessuno — e la nota, che e' la parte
utile, dovrebbe sparire.

🔴 **Richiesta al backend**: rigenerare `apps/core/services/error_policies_generated.py`
per il codice nuovo. Si somma a quella gia' aperta per `W_MESSAGGIO_ARITA`.

---

## Restano 5

| file | tipo | nota |
|---|---|---|
| `test-fn-resolve-prezzo-composito-v1` | ERRORE_FIXTURE | ⚠️ **decisione**: il suo CASO B1 (composito con riga di listino propria) e' vietato da `trgfn_listini_righe_guard_no_composito`, quindi il ramo B1 di `fn_resolve_prezzo_composito` e' irraggiungibile. O e' codice morto o il guard e' troppo largo |
| `test-fn-list-preventivi-da-pushare-v1` | ASSERZIONE | 3 asserzioni rosse; probabile causa unica condivisa col -v2 |
| `test-fn-list-preventivi-da-pushare-v2` | ASSERZIONE | 3 asserzioni rosse |
| `test-fn-preventivo-ha-residuo-commessa-v1` | ASSERZIONE | ⭐ si e' sbloccato da solo: era `ERRORE_FIXTURE`, ora gira tutte e 13 e ne fallisce 2 (`PREVENTIVO_NESSUNA_RIGA_COMMESSA`, `PREVENTIVO_SENZA_BILLING_ACCOUNT`) |
| `test-contratti-utilities-snapshot` | ASSERZIONE | serve un billing account la cui istanza/utility non abbia precontrattuali: non ce ne sono piu' (42/42 coperti, UNIQUE su istanza+utility). La fixture deve **crearsi** un'istanza vergine |

## Rientrati per migrazione, non per bonifica

`test-fatture-arrotondamenti-scope` — verde con `20260818-70` (guard sui
parametri di `fn_get_arrotondamento_scope`).
