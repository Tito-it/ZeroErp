# Brief DB — Cambio di natura del soggetto: conferma della perdita e pulizia dei dati non congrui

## ⏭️ Chi riparte — aggiornato al 2026-11-15

⚠️ **Il modello è cambiato il 2026-11-14 (§0, D-5 e D-6 di Tid):** il cambio di natura **non pulisce
niente**. Rifiuta ed elenca i motivi, e il giro lo fa l'operatore a mano. Il titolo del file («conferma
della perdita e pulizia») è quello d'origine e non si rinomina, per non rompere i rimandi.

**Riparte: nessuno — brief chiuso e archiviato il 2026-11-15.** DB fatto e committato (giri 1-3,
`da62f3a1d`); BE/FE fatto (K-1 … K-8, §6.0-bis), rivisto e provato in app da Tid. Resta il solo
commit del lato BE/FE.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ FE | La chiave i18n `config.tipi_entita.ricevuta` in `it.json` e `en.json` (2026-11-15) | §0, «Richiesta al FE» | — |
| 2 | Tid | ✅ Giro 1 applicato, pgTAP verdi (2026-11-14) | — | — |
| 3 | Tid | ✅ pgTAP del giro 2 verdi come applicazione (2026-11-14) | — | — |
| 3-bis | ✅ FE | Le dieci chiavi `cambio_natura_blocco` del giro 2 (2026-11-15) | §0, «Giro 2, fatto» | — |
| 3-ter | Tid | ✅ Giro 3 applicato, pgTAP verdi (2026-11-14) | — | — |
| 3-quater | DB | ✅ Richiesta BE/FE scritta (§6.0) | — | — |
| 4 | ✅ BE/FE | Le nature in modifica dalla regola DB, il pulsante o la natura spenti con i motivi, via il «flag nascosto a `N`» (2026-11-15, §6.0-bis) | §0 | 3 |
| 5 | ✅ Tid | Archiviazione in `work-done/` (2026-11-15, su richiesta di Tid, dalla sessione BE) | — | 4 |

Decisioni aperte di Tid: nessuna. Debito: nessuno. Lavoro fatto da committare: il lato BE/FE
(§6.0-bis) e questo brief archiviato; i giri DB sono nel commit `da62f3a1d`.

**Brief vicini verificati (2026-11-14):** nessuno sugli stessi oggetti.
[brief-db-fornitore-privato-indirizzi](brief-db-fornitore-privato-indirizzi.md) tocca gli indirizzi
obbligatori del **ruolo** `FO`, non il cambio di natura; i residui del brief dati fiscali (registro dei
residui aperti) sono complementari e non si sovrappongono.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** revisione del lato BE/FE di
> [brief-db-dati-fiscali-e-societari-del-soggetto](brief-db-dati-fiscali-e-societari-del-soggetto.md)
> (§9), e la decisione di Tid del 2026-10-11: «andrebbe richiesta la conferma di perdita dati e
> poi si puliscono quelli non congrui».
> **Stato:** ✅ chiuso il 2026-11-15. ⚠️ Modello rivisto da Tid il 2026-11-14 (§0): le decisioni di pulizia del
> §3 (D-0, D-1, D-3, D-4) e i §4.2-4.3, §5, §6 sono **superati**. Nessuna domanda aperta.

## 0. Il modello rivisto (Tid, 2026-11-14) — ⭐ si parte da qui

Origine: la discussione sulla riverifica. Tid: «non dobbiamo abilitare nessuna cancellazione delle
informazioni con trigger collegati o funzioni, il giro deve essere fatto manualmente»; «poter correggere
la P.IVA non significa che l'amministratore possa cambiare la natura se ci sono informazioni collegate».
⚠️ **Revoca** D-0 e D-1 del 2026-10-11 e D-3 e D-4 di oggi (la pulizia confermata).

| # | Decisione |
| --- | --- |
| **D-5** | Il cambio di natura **non pulisce mai niente**: nessun trigger e nessuna funzione cancella, chiude o azzera dati per farlo passare. Il DB **rifiuta** il cambio ed **elenca tutti i motivi**; l'operatore li toglie **a mano**, con gli strumenti che già esistono, e poi il cambio passa. Vale **anche per il SUPER_ADMIN**: il suo diritto di correggere CF e P.IVA non si estende al cambio di natura. |
| **D-6** | Alcuni motivi **non si tolgono** e bloccano il cambio per tutti: i **documenti intestati al soggetto** (preventivi, ordini, DDT, contratti, fatture…), ma **solo** se il cambio tocca l'**identità fiscale**, cioè fa nascere o sparire la P.IVA (DI ↔ PR). Fra nature che tengono P.IVA e CF (SC ↔ SP, una trasformazione di società: l'ente resta lo stesso) i documenti non bloccano. |
| **D-7** | *(Q-5)* I dati societari si tolgono con un'azione **manuale** «Elimina i dati societari», nella loro sezione, **separata** dal cambio di natura: la usa l'operatore, con un gesto suo. Il cambio di natura non la chiama. ⚠️ ~~La riga eliminata resta nello storico~~: solo se la riga ha `storicizza = true` (Q-10). |
| **D-8** | *(Q-6)* Per D-6 il documento blocca in **qualunque ruolo** in cui porta l'identità del soggetto: controparte, ma anche emittente, vettore, agente, reseller, responsabile. La regola prende **ogni** FK della testata verso le tabelle ponte del §0.1, senza classificare le colonne. |
| **D-9** | *(Q-7)* `shop.ricevute` si **registra** in `config.sorgenti` come testata `DOCUMENTO`: entra da sola nella regola di D-6 e in ogni altra regola derivata dal registro. Niente eccezioni scritte a mano nella regola. |
| **D-10** | *(Q-8)* Prima di registrarla, `shop.ricevute` si **allinea** alla grammatica dei documenti: `id bigint` identity e `uid uuid` (il valore di oggi), come `vendite.resi`. Giro 1 di questo brief. |
| **D-11** | *(Q-9)* Il cambio fra **macro-tipologie diverse** lo vieta il **DB**, per ogni strada: è il primo motivo della regola (`E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA`), non più una regola del solo BE. |
| **D-12** | *(Q-10)* L'eliminazione dei dati societari lascia **sempre** traccia nello storico: `anagrafiche.dati_societari` ha `storicizza` sempre acceso (DEFAULT true, NOT NULL, righe esistenti accese) ed è nel registro `config.storico_set_storicizza`. |

**I giri** (decisi il 2026-11-14):

| Giro | Che cosa | Stato |
| --- | --- | --- |
| **1** | La ricevuta nella grammatica (D-10) e registrata come sorgente (D-9): chiave, storico, `config.sorgenti`, `config.tipi_entita`, `trgfn_sorgente_in_uscita`. Richiesta al FE: la chiave i18n dell'etichetta | ✅ applicato da Tid il 2026-11-14, pgTAP verdi. ⏳ Il commit aspetta la chiave i18n del FE |
| **2** | La regola dei motivi, la regola dei documenti (D-6, D-8, derivata dal registro), i cambi ammessi a DB, il guard al cambio, i codici d'errore | ✅ applicato da Tid il 2026-11-14 (`-60 … -68` e il catalogo); pgTAP verdi come applicazione |
| **3** | Il verbo manuale «elimina i dati societari» (D-7), e lo storico sempre acceso (D-12) | ✅ applicato da Tid il 2026-11-14, pgTAP verdi |
| **4** | Richiesta BE/FE | ✅ scritta il 2026-11-14 (§6.0, K-1 … K-8) |

**Giro 1, vincoli trovati in progettazione (2026-11-14):**

* La shadow `storico.ricevute` la crea il framework delle automazioni (`dbops.fn_ensure_storico_table`,
  in `ci_apply`), con la colonna `ricevute_id` **del tipo della PK della madre**, e «se c'è già non la
  tocca». Su un DB da zero nasce dopo il cambio, quindi già `bigint`; su un DB che l'ha già, resta
  `uuid` e il trigger di storico, al primo UPDATE o DELETE di una ricevuta, scriverebbe un `bigint` in
  una colonna `uuid`. Serve un changeSet **condizionale** («se la shadow c'è»), separato, che porti
  `ricevute_id` a `bigint`: i valori vecchi si traducono passando da `shop.ricevute.uid`, che conserva
  il vecchio `id`; lo `snapshot` jsonb conserva comunque la riga intera.
* La policy `rls_shop_ricevute_self_ownership` legge solo `soggetto_ruolo_id`: il cambio di chiave non
  la tocca.
* Nessuna FK punta a `shop.ricevute`: la PK si sostituisce senza toccare altre tabelle.
* Il trigger del lato «in uscita» **non si scrive**: lo monta `dbops.fn_sorgente_converge_uscita`,
  che `90_end` lancia a ogni migrazione dopo i seed, leggendo il catalogo (linee-guida-trigger, «I
  trigger generati»).

**Giro 1, fatto (2026-11-14):**

| Pezzo | File |
| --- | --- |
| La chiave: `id` → `uid` (UNIQUE `uq_shop_ricevute_uid`), nuova `id bigint` identity BY DEFAULT come PK; `storico.ricevute.ricevute_id` a `bigint` dove la shadow esiste già (`ALTER … TYPE … USING` una funzione in `pg_temp`: nessun trigger di riga, la storia non si riscrive; si ferma se una riga di storico non ha più la sua ricevuta) | `00_schema/shop/20261114-59-alter-ricevute-chiave-della-grammatica-documenti-mctit.yaml` |
| La sorgente `RICEVUTA` (id 30, `DOCUMENTO`, `CATALOGO`, `key_selector = id`, non apribile, `label_selector = numero`) | `80_data/sql/config/sorgenti.csv` |
| L'entità `RICEVUTA` (`is_sorgente`, `etichetta_key = config.tipi_entita.ricevuta`) | `80_data/sql/config/tipi_entita.csv` |
| Il pgTAP (11 asserzioni) | `db/pgtap/shop/test-ricevute-nella-grammatica-documenti-v1.sql` |

Prova (`scripts/prova_changeset.py --pgtap`, scratch, 2026-11-14): estratto eseguito per intero, catalogo
identico dopo il `ROLLBACK`; pgTAP senza estratto 2 ok / 9 rossi, con l'estratto 6 ok / 5 rossi. I 5
rossi sono 7-11, che leggono il seed e il montaggio di `90_end`: diventano verdi con l'apply. Il test 6
(il tipo della shadow uguale a quello della PK) ha confrontato davvero: sullo scratch la shadow c'era,
in `uuid`. **Mutazione**: lo stesso changeSet senza il blocco dello storico fa diventare rosso il 6.
⛔ **Non provati:** il percorso con una ricevuta vera (nessuna fixture sa creare un billing account del
canale SHOP, dichiarato in testa al pgTAP) e il `rollback` del changeSet (la prova estrae solo i
`changes`).

**Giro 2, progetto (2026-11-14):**

*Due famiglie di motivi.* I dati **della riga** del soggetto (flag PA e split payment, P.IVA) l'operatore
li corregge **nello stesso salvataggio** della natura: la regola li giudica sui valori **proposti**
(`NEW`), come vuole un `BEFORE ROW` (linee-guida-trigger, «che cosa vede il trigger»). Gli **altri
dati** (documenti, titoli, dati societari, indirizzi) stanno in altre tabelle e si tolgono prima, in
un altro posto. Forma giuridica, sesso e indirizzi obbligatori restano ai guard che esistono (D-2,
SCEGLI/COMPLETA): giudicano lo stato finale e non sono motivi di questa regola.

| Motivo | Codice | Quando |
| --- | --- | --- |
| natura di un'altra macro-tipologia | `E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA` (nuovo) | `tipo_soggetto_id` diverso. È la regola che oggi sta nel BE (`tipi_modificabili_ids`) |
| identità fiscale che cambia, con documenti | `E_CAMBIO_NATURA_CON_DOCUMENTI` (nuovo) | la P.IVA nasce o sparisce (`formato_piva = NON_APPLICABILE` da una parte sola) e il soggetto compare in un documento, in qualunque ruolo (D-6, D-8) |
| P.IVA proposta su una natura `NON_APPLICABILE` | `E_CAMBIO_NATURA_PIVA_NON_APPLICABILE` (nuovo) | svuotarla resta del SUPER_ADMIN (`trgfn_soggetti_guard_id_fiscale_immutabile`) |
| flag PA o split payment proposti a `S` e non ammessi | `E_CLIENTE_PA_NON_AMMESSO`, `E_SPLIT_PAYMENT_NON_AMMESSO` (esistenti) | il predicato esce in un building block, letto anche da `trgfn_soggetti_guard_regime_pa` (regola del 2) |
| titolo IVA vigente non ammesso, visibile | `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI` (esistente) | assorbe `trgfn_soggetti_guard_titoli_iva_ammessi`, che si **ritira** nello stesso giro |
| titolo IVA vigente non ammesso, di un altro emittente | `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI` (nuovo) | quanti non li vede chi agisce: totale (DEFINER) meno visibili (sotto la RLS di chi agisce). Nessuna copia del predicato della policy |
| riga di dati societari, natura nuova `NONE` | `E_CAMBIO_NATURA_CON_DATI_SOCIETARI` (nuovo) | si toglie con l'azione manuale di D-7 (giro 3) |
| indirizzo di un tipo che la natura nuova non ammette | `E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI` (nuovo) | la matrice `tipi_soggetto_dettaglio_tipi_indirizzo`, col suo «fallback permissivo» (natura senza righe di matrice = tutto ammesso) |

*Gli oggetti.*

1. `anagrafiche.fn_soggetto_primo_documento(p_soggetto_id)` — `SECURITY DEFINER` (i documenti hanno la
   RLS): il codice della prima sorgente `DOCUMENTO` del catalogo che nomina il soggetto, o `NULL`. Tabelle
   da `config.fn_sorgente_tabella`, colonne dalle FK verso le tabelle ponte del §0.1, identificatori da
   `%I` e valori da `USING`. Riceve solo il soggetto: nessun nome di tabella o colonna dal chiamante.
   Gemella di `anagrafiche.fn_ba_ha_storia_emittente`.
2. Il predicato dei flag: un building block letto dal guard del regime PA e dalla regola.
3. `anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id, p_tipo_soggetto_dettaglio_id,
   p_partita_iva, p_cliente_pa, p_split_payment)` — check pura, `RETURNS jsonb`, l'array **ordinato** dei
   motivi `{codice, reason, reason_key, dettaglio, valori}` (forma di
   `script.fn_check_annullo_movimento_titolo_iva`). INVOKER: conta i titoli sotto la RLS di chi agisce.
4. Il guard `trg_soggetti_a10_guard_cambio_natura_upd`, `BEFORE UPDATE … WHEN (OLD.tipo_soggetto_dettaglio_id
   IS DISTINCT FROM NEW.tipo_soggetto_dettaglio_id)`, che solleva il primo motivo con
   `script.fn_raise_primo_motivo_se_presente`. In ordine alfabetico parla **prima** degli altri guard
   `a10` della tabella (`guard_cambio…` < `guard_cf_piva…`).
5. Il picker (§12.6): una funzione di lettura che, per ogni natura di dettaglio, risponde se è ammessa e
   col primo motivo, leggendo **la stessa check**. Il BE la leggerà al posto di `tipi_modificabili_ids`
   (giro 4).

*Le chiavi i18n.* Ogni `reason_key` è una chiave emessa dal DB: entra nella richiesta al FE del giro 2,
prima del commit (`check-i18n-keys`).

**Giro 2, fatto (2026-11-14):** `20_code/anagrafiche/20261114-60 … -68` (oggetti 1-5 sopra, più i due
predicati e i due guard che li leggono), sei codici nuovi in `codici_errore.csv` e le loro frasi in
`messaggi_errore.csv` (id 1484-1489), riscritte le note di `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` e
`E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI`. Applicato da Tid su dbdev e sullo scratch.

*pgTAP:*

| File | Che cosa | Prova sullo scratch, da proprietario |
| --- | --- | --- |
| `anagrafiche/test-cambio-natura-soggetto-v1.sql` (nuovo, 17) | la regola, il guard, il picker, il ritiro; casi costruiti, una natura PG senza P.IVA fabbricata | 17/17 |
| `anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql` | 3: il lettore DEFINER nuovo; 15: il titolo di un altro emittente esce col codice nuovo (D-4) | verde salvo 14-15, rossi **da proprietario per costruzione** (la RLS non c'è): ⏳ da vedere come applicazione |
| `anagrafiche/test-soggetti-regime-pa-v1.sql` | 8-9: il flag che non si porta dietro, dentro la famiglia ENC con una natura fabbricata (D-11) | 15/15 |
| `anagrafiche/test-fn-scrivi-dati-societari-v1.sql` | 16-17: la forma al COMMIT su SC → SP (SRL rifiutata, SNC passa) (D-11) | invariato, 1 rosso già presente prima |

Identici con e senza il giro 2: `test-soggetti-split-payment-cliente-pa`, `vendite/test-fatture-righe-esigibilita-split`,
`test-soggetti-id-fiscale-immutabile-v1`, `test-soggetti-sesso-policy-v1`, `test-billing-account-guard-cf-confrontabile-v1`
(1 rosso già presente prima).
⛔ **Non provati, e dichiarati in testa al test nuovo:** il motivo degli indirizzi su righe vere (provato
il predicato sui valori), la ditta individuale dentro un documento (nessuna fixture crea un cliente
persona fisica: il ramo dei documenti lo prova la società). La mutazione del test nuovo non è stata
fatta: il giro era già applicato.

**Giro 3, fatto (2026-11-14):**

| Pezzo | File |
| --- | --- |
| Lo storico sempre acceso: `storicizza` DEFAULT true, righe esistenti accese (storico e guard del tipo soggetto sospesi, cercati per funzione; audit acceso), NOT NULL | `00_schema/anagrafiche/20261114-70-alter-dati-societari-storicizza-sempre-mctit.yaml` |
| La check `anagrafiche.fn_check_elimina_dati_societari` e il verbo `anagrafiche.fn_elimina_dati_societari` (DEFINER, `FOR UPDATE` sul soggetto, EXECUTE solo all'app) | `20_code/anagrafiche/20261114-69-create-fn-elimina-dati-societari-mctit.yaml` |
| La tabella nel registro dello storico (`insert_manuale = true`; ⚠️ `80_data/sql/config/storico_set_storicizza.csv` non è un mirror, nessun changeSet lo carica) | `80_data/changelog/20261114-71-register-dati-societari-storicizza-mctit.yaml` |
| Il codice `E_DATI_SOCIETARI_NON_ELIMINABILI` (frase 1490) | `codici_errore.csv`, `messaggi_errore.csv` |
| Il pgTAP (14) | `db/pgtap/anagrafiche/test-fn-elimina-dati-societari-v1.sql` |

Prova sullo scratch, nell'ordine di esecuzione (-70, -69, -71): estratto per intero, catalogo identico;
pgTAP 13/14, l'unico rosso è il 5, che asserisce la frase del codice nuovo (arriva col CSV all'apply). Il
test 10 (lo storico conserva la cancellazione) è rosso senza -70/-71 e verde con: è la sua controprova.
Chiave i18n in più per il FE: `anagrafiche.soggetti.dati_societari_elimina_blocco.natura_li_richiede`.

*Richiesta al FE — le chiavi emesse dal giro 2* (`it.json` e `en.json`, sotto
`anagrafiche.soggetti.cambio_natura_blocco`): `altra_macro_tipologia`, `con_documenti`,
`piva_non_applicabile`, `cliente_pa`, `split_payment`, `titoli_iva`, `titoli_iva_altri_emittenti`,
`dati_societari`, `indirizzi`, `senza_natura_con_titoli_iva`. ⚠️ `check-i18n-keys` oggi non le vede
(legge la doc auto-generata, non ancora rigenerata): alla rigenerazione diventano rosse.

**⏭️ Richiesta al FE, prima del commit DB** — senza, il pre-commit (`check-i18n-keys`) rifiuta il
commit: la chiave è emessa dal DB e manca dai locales.

| File | Chiave | Valore |
| --- | --- | --- |
| `frontend/src/locales/it.json` | `config.tipi_entita.ricevuta` | «Ricevuta» |
| `frontend/src/locales/en.json` | `config.tipi_entita.ricevuta` | «Receipt» |

Accanto alla voce `email` di `config.tipi_entita`, che è il precedente. ⚠️ Lo stesso hook segnala anche
due chiavi **non di questo giro**, già mancanti: `vendite.ddt.genera_reso_reason.non_consegnato` e
`vendite.ddt.genera_reso_reason.trasferimento` (da `script.fn_check_ddt_rendibile`).

**I motivi, rivisti sul §2:**

| Motivo | Chi lo toglie, e come |
| --- | --- |
| `cliente_pa` / `split_payment` a `S` non ammessi | L'operatore, nel form: il flag a `N`. ⛔ Sparisce il «flag nascosto a `N`» del FE (`SoggettoDrawer.vue`), che è una pulizia silenziosa |
| titolo IVA vigente non ammesso, del proprio emittente | L'operatore, chiudendolo nel drawer dei titoli |
| titolo IVA vigente non ammesso, di **un altro emittente** | Non l'operatore, che non lo vede: il motivo dice che esiste (senza dettagli) e che deve intervenire chi lo vede (SUPER_ADMIN o l'altro emittente). Lettura `SECURITY DEFINER`, come `fn_titolo_iva_non_ammesso_del_soggetto` |
| indirizzo di un tipo che la natura nuova non ammette (Q-3) | L'operatore, eliminandolo dagli indirizzi del soggetto |
| riga di dati societari, natura nuova `NONE` | L'operatore, con l'azione manuale «Elimina i dati societari» (D-7): un verbo DB **suo**, `SECURITY DEFINER` come `fn_scrivi_dati_societari`, così B-5 resta vero. ⚠️ Il verbo rifiuta quando la natura **attuale** ha `dati_societari_policy = REQUIRED` (una SC non resta senza la riga): il guard differito `trgfn_soggetti_guard_dati_societari_required` scatta solo sugli UPDATE di `soggetti`, non sulla cancellazione della riga |
| P.IVA scritta, natura nuova `NON_APPLICABILE` (DI → PR, Q-4) | Solo il SUPER_ADMIN, svuotandola a mano (`trgfn_soggetti_guard_id_fiscale_immutabile`). E se il soggetto ha documenti, il cambio è comunque bloccato (D-6) |
| documenti intestati al soggetto, cambio DI ↔ PR | Nessuno (D-6): definitivo |
| forma giuridica non ammessa, sesso o P.IVA mancanti, indirizzi obbligatori della natura nuova | Non sono dati da togliere ma da **dare** (SCEGLI / COMPLETA del §2, D-2): l'operatore li dà nello stesso salvataggio, i guard che esistono giudicano lo stato finale |

**Conseguenze per il progetto DB** (le scelte tecniche restano del team DB):

1. **Una regola sola dei motivi**, che alimenta sia la natura o il pulsante spenti con il motivo sia
   il rifiuto (lo schema di `script.fn_check_annullo_movimento_titolo_iva`). Elenca **tutti** i
   motivi, non il primo; per i titoli parte da `fn_titolo_iva_non_ammesso_del_soggetto`,
   generalizzata (§4.1).
2. **Il guard al cambio** su `anagrafiche.soggetti` legge quella regola: un `UPDATE` di
   `tipo_soggetto_dettaglio_id` con motivi aperti si rifiuta, da qualunque strada arrivi. Nessun
   verbo con `conferma_pulizia`, nessun verbo che cancelli (i vecchi §4.2-4.3 cadono).
3. **I cambi ammessi diventano una regola del DB.** Oggi le nature proposte in modifica le calcola
   il BE (`soggetti_repository.get_soggetto`: «stessa macro-tipologia»). Con D-6 la regola dipende
   dai dati collegati: la scrive il DB, e il BE la legge.
4. **Da censire prima di scrivere**: quali tabelle contano come «documento intestato al soggetto»
   per D-6. È un elenco chiuso che va scritto nel brief prima del changeSet. → Fatto: §0.1.

### 0.1 Censimento per D-6 — quali documenti, e per quale colonna (2026-11-14)

Letto dalla **struttura** (`pg_constraint` e seed `80_data` di `config.sorgenti`, su dbdev il
2026-11-14), non dalle righe.

**La sede dell'elenco esiste già: `config.sorgenti`.** Ogni testata di documento è una riga con
`categoria = 'DOCUMENTO'` e la sua `target_table`, che `config.fn_sorgente_tabella` legge. È la stessa
forma della regola gemella del **cambio emittente del billing account**
(`anagrafiche.fn_ba_ha_storia_emittente`, `SECURITY DEFINER`): «si blocca se c'è anche un solo
documento numerato», con le famiglie **derivate** da `vendite.famiglie_documento`, così che il
documento che nascerà domani entri nella regola il giorno in cui si registra, senza un elenco
parallelo che resti indietro. ⚠️ `famiglie_documento` non basta qui: censisce solo le famiglie
**numerate** (fattura, DDT, ordine, commessa, reso, distinta), non preventivi, offerte, contratti e
acquisti. La sede per D-6 è `config.sorgenti`.

**La colonna che lega il documento al soggetto si deriva da `pg_constraint`**, non si dichiara: le FK
della `target_table` verso una delle cinque tabelle **ponte**, che arrivano tutte al soggetto:

| Ponte | Arriva al soggetto per |
| --- | --- |
| `anagrafiche.soggetti` | è il soggetto |
| `anagrafiche.soggetti_ruoli` | `soggetto_id` |
| `anagrafiche.billing_account` | `soggetto_ruolo_id` → `soggetti_ruoli` |
| `anagrafiche.emittenti_fiscali` | `soggetto_ruolo_id` → `soggetti_ruoli` |
| `anagrafiche.risorse_umane` | `soggetto_id` (e `soggetto_ruolo_id`) |

**Le testate di oggi e le loro colonne verso il soggetto** (fotografia della struttura, 2026-11-14):

| Sorgente | Tabella | Colonne verso il soggetto |
| --- | --- | --- |
| `PREVENTIVO` | `vendite.preventivi` | `billing_account_id`, `emittente_fiscale_id` |
| `OFFERTA_COMMERCIALE` | `vendite.offerte_commerciali` | `billing_account_id`, `emittente_fiscale_id` |
| `CONTRATTO` | `vendite.contratti` | `billing_account_id`, `emittente_fiscale_id` |
| `ORDINE_VENDITA` | `vendite.ordini` | `billing_account_id`, `soggetto_ruolo_id`, `agente_soggetto_ruolo_id`, `emittente_fiscale_id` |
| `DDT_VENDITA` | `vendite.ddt` | `billing_account_id`, `destinatario_` / `mittente_` / `vettore_soggetto_ruolo_id`, `emittente_fiscale_id` |
| `RESO_VENDITA` | `vendite.resi` | `billing_account_id`, `destinatario_soggetto_ruolo_id`, `emittente_fiscale_id` |
| `FATTURA` | `vendite.fatture` | `billing_account_id`, `emittente_` / `reseller_soggetto_ruolo_id` |
| `COMMESSA` | `vendite.commesse` | `billing_account_id`, `emittente_soggetto_ruolo_id`, `responsabile_risorsa_umana_id` |
| `ATTIVITA_CONSUMI` | `vendite.attivita_consumi` | `billing_account_id` |
| `ORDINE_ACQUISTO` | `acquisti.ordini` | `soggetto_ruolo_id` |
| `DDT_ACQUISTO` | `acquisti.ddt` | `destinatario_` / `mittente_soggetto_ruolo_id` |
| `DISTINTA_INCASSO` | `pagamenti.vendite_contabili` | `emittente_soggetto_ruolo_id` |
| `EMAIL` | `config.email_outbox` | `emittente_fiscale_id` |
| `INVENTARIO`, `RETTIFICA`, `TRASFERIMENTO` | `magazzino.*` | nessuna: non contribuiscono |

`EVENTO_ASSET` ha `categoria = 'EVENTO'`: non è un documento, resta fuori.

**Tabelle che puntano al soggetto ma non sono testate del registro:** `shop.ricevute` (⚠️ un
**documento fiscale** B2C, con numerazione sua: Q-7), `vendite.listini` (solo l'emittente),
`pagamenti.sistemazioni`, `pagamenti.sepa_mandati`, `pagamenti.vendite_movimenti`,
`pratiche.pratiche`, `magazzino.movimenti_attesi`, `magazzino.assets`, le tabelle `*_indirizzi` dei
documenti (figlie: il documento ha già la sua colonna). Le righe `*_righe` non portano un soggetto
loro, salvo `vendite.fatture_righe.dest_billing_account_id`.

**Due domande per Tid prima del progetto:** Q-6 (in quale **ruolo** il soggetto deve comparire perché
il documento blocchi) e Q-7 (`shop.ricevute`), al §7.

## 1. Il caso

In modifica il drawer del soggetto offre le nature di dettaglio della **stessa macro-tipologia**
(`tipi_modificabili_ids`: PR ↔ DI, SC ↔ SP, …). Dal 2026-10-10 il cambio arriva al DB, e i guard
del brief dati fiscali giudicano la natura nuova contro i dati che il soggetto ha già. I guard
fanno il loro mestiere — **rifiutano** — ma per una parte dei casi l'operatore non ha una via
d'uscita:

* **Ditta individuale con dati societari → privato.** `PR` ha `dati_societari_policy = NONE`, la
  riga c'è. Al COMMIT `trgfn_soggetti_guard_forma_giuridica_natura` rifiuta
  (`E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA`, campo `forma_giuridica_id`), su una sezione che
  il form per un privato **non mostra**. E l'applicazione non può togliere la riga: dal
  `20261011-04` non ha `DELETE` su `anagrafiche.dati_societari` (B-5: scrive solo il verbo), e un
  verbo che cancelli non esiste. **Vicolo cieco.**
* **Titoli IVA vigenti non ammessi dalla natura nuova.** Rifiuto
  `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI`: l'operatore deve andare a chiudere i titoli uno
  per uno in un altro drawer, e solo dopo cambiare la natura.
* **Flag PA / split payment a `S` non ammessi.** Oggi il FE li manda a `N` **senza dirlo** (§9.1
  del brief dati fiscali): una perdita silenziosa, proprio quella che la decisione di Tid esclude.

## 2. Cosa diventa non congruo (dal contratto, non dai dati)

> ⚠️ *2026-11-14:* l'esito **PULISCI** di questa tabella è superato da D-5 (§0): quei dati restano
> motivi di rifiuto, che l'operatore toglie a mano. SCEGLI e COMPLETA restano validi.

| Dato | Regola (sede) | Al cambio di natura |
| --- | --- | --- |
| `cliente_pa`, `split_payment` a `S` | `cliente_pa_ammesso` / `split_payment_ammesso` (`trgfn_soggetti_guard_regime_pa`) | **PULISCI**: a `N` |
| riga `dati_societari`, natura nuova `NONE` | `dati_societari_policy` | **PULISCI**: la riga si toglie (lo storico la conserva: `trg_dati_societari_z90_storico_upd_dlt`) |
| forma giuridica non ammessa, natura nuova `OPTIONAL`/`REQUIRED` | `fn_forma_giuridica_ammessa` | **SCEGLI**: forma nuova nello stesso salvataggio (§3, D-2) |
| titoli IVA vigenti non ammessi | `fn_titolo_iva_ammesso` (`trgfn_soggetti_guard_titoli_iva_ammessi`) | **PULISCI**: si chiudono (§3, D-1) |
| sesso mancante, natura nuova `REQUIRED` (DI → PR) | `sesso_policy` | **COMPLETA**: il form lo chiede |
| indirizzi obbligatori della natura nuova | `tipi_soggetto_dettaglio_tipi_indirizzo` | **COMPLETA**: l'operatore li aggiunge |
| indirizzi di un tipo che la natura nuova **non ammette** (es. `SEDELEG` di una DI → PR) | `tipi_soggetto_dettaglio_tipi_indirizzo` | ⚠️ **buco confermato il 2026-11-14**, esito da decidere (§7, Q-3) |
| partita IVA scritta, natura nuova con `formato_piva = NON_APPLICABILE` (DI → PR) | `config.tipi_soggetto_dettaglio.formato_piva` | ⚠️ **da decidere** (§7, Q-4) — riga aggiunta il 2026-11-14 |
| partita IVA mancante, natura nuova con `piva_obbligatoria` (PR → DI) | `trgfn_soggetti_guard_cf_piva_obbligatori` | **COMPLETA**: il form la chiede (un campo vuoto si può riempire anche col guard di immutabilità) |
| ruoli | `tipi_ruoli_nature_ammesse`, per **macro-tipologia** | invariato: il cambio resta nella stessa macro-tipologia |

Tre esiti diversi, e vanno tenuti distinti: **PULISCI** (il dato si perde, ci vuole la conferma),
**SCEGLI** / **COMPLETA** (manca qualcosa che solo l'operatore può dare: non c'è niente da pulire,
il guard rifiuta col campo finché non lo dà).

## 3. Decisioni di Tid (2026-10-11)

> ⚠️ *Superate il 2026-11-14 da D-5 e D-6 (§0):* D-0, D-1, D-3, D-4, e la seconda frase di D-2
> («la riga si toglie se la natura nuova ha `NONE`»). Resta valida la prima parte di D-2: la forma
> non ammessa non si pulisce, l'operatore ne sceglie una ammessa nello stesso salvataggio.

| # | Decisione |
| --- | --- |
| **D-0** | Il cambio di natura che **perde dati** chiede una **conferma esplicita**, che elenca cosa si perde. Confermato, i dati non congrui **si puliscono** nella stessa transazione del cambio. |
| **D-1** | I **titoli IVA** vigenti non ammessi **si chiudono** (non si cancellano): `valido_al` = il giorno prima del cambio. La storia resta. |
| **D-2** | **Forma giuridica** non ammessa ma natura nuova con i dati societari: **non si pulisce**, l'operatore sceglie una forma ammessa nello stesso salvataggio (la forma è NOT NULL, C-2, e REA e capitale ne dipendono). La riga si toglie **solo** se la natura nuova ha `dati_societari_policy = NONE`. |
| **D-3** | *(2026-11-14, Q-1)* Un titolo IVA non ammesso che **non è ancora cominciato** (`valido_dal` dal giorno del cambio in poi) **si cancella**: non ha mai valso, e chiuderlo alla sua data d'inizio registrerebbe un giorno di validità falso. Eccezione a D-1, che resta per i titoli già cominciati. |
| **D-4** | *(2026-11-14, Q-2)* Se fra i titoli da chiudere o cancellare ce n'è anche uno solo di un **altro emittente**, il cambio di natura **si rifiuta** a chi non è SUPER_ADMIN, e il messaggio dice che l'intervento lo deve fare un SUPER_ADMIN. Nessun dettaglio dei titoli altrui (solo che esistono). Per il SUPER_ADMIN valgono D-0, D-1 e D-3 su tutti i titoli. |

## 4. Proposta per il team DB

> ⚠️ *Superata il 2026-11-14 (§0):* cadono i punti 2 e 3 (il verbo con `conferma_pulizia` e
> `fn_elimina_dati_societari`). Il punto 1 resta, con i motivi del §0 al posto degli esiti `PULISCI`;
> il punto 4 è deciso dal §0.2 (il guard al cambio, da qualunque strada); il punto 5 resta.

Le scelte tecniche sono del team DB; quello che conta è che **anteprima e pulizia leggano una
regola sola** (lo stesso principio di `script.fn_check_annullo_movimento_titolo_iva`, che
alimenta sia il pulsante spento sia il rifiuto).

1. **La regola: `anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id uuid,
   p_tipo_soggetto_dettaglio_id bigint)`**, `RETURNS TABLE(voce, esito, campo, dettaglio jsonb)`,
   con `esito` in `PULISCI` / `SCEGLI` / `COMPLETA`. Una riga per dato del §2. Legge i predicati
   che esistono già (`fn_forma_giuridica_ammessa`, `fn_titolo_iva_ammesso`, le colonne della
   natura), non ne riscrive.
   ⚠️ *Nota del 2026-11-14:* per i titoli IVA esiste già
   `anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(p_soggetto_id, p_tipo_soggetto_dettaglio_id)`,
   `SECURITY DEFINER` (la RLS per emittente nasconderebbe i titoli degli altri), letta da
   `trgfn_soggetti_guard_titoli_iva_ammessi`. Restituisce **solo il primo** tipo non ammesso;
   l'anteprima vuole l'elenco (o almeno il conteggio, Q-2). Perché guard e anteprima leggano una
   regola sola, la voce dei titoli parte da lì (generalizzata, con il guard che la segue), non da
   una seconda query su `fn_titolo_iva_ammesso`.
2. **Il verbo: `anagrafiche.fn_cambia_natura_soggetto(p_soggetto_id, p_tipo_soggetto_dettaglio_id,
   p_conferma_pulizia boolean)`**:
   * con voci `PULISCI` e `p_conferma_pulizia = false` → rifiuto con un **codice nuovo**
     (proposta `E_CAMBIO_NATURA_RICHIEDE_CONFERMA`, `CONFLITTO_STATO`, campo
     `tipo_soggetto_dettaglio_id`, l'elenco delle voci nel contesto). È il presidio di D-0 **a DB**:
     nessun chiamante cambia natura perdendo dati senza averlo detto;
   * confermato → applica le pulizie, **poi** aggiorna la natura;
   * le voci `SCEGLI` / `COMPLETA` le lascia ai guard che già esistono (forma al COMMIT, sesso,
     indirizzi): il verbo non le anticipa.
3. **Togliere la riga dei dati societari**: un verbo `fn_elimina_dati_societari(p_soggetto_id)`,
   chiamato da `fn_cambia_natura_soggetto`, così B-5 resta vero («una porta per operazione», e
   nessun `DELETE` all'app).
4. **L'UPDATE diretto di `tipo_soggetto_dettaglio_id`**: se il cambio deve passare solo dal verbo
   (come i dati societari con B-5) lo decide il team DB. Senza un presidio, un `UPDATE` diretto
   salta la conferma; i guard restano comunque.
5. **L'ordine con i dati societari** non cambia (§8.3 del brief dati fiscali): nella stessa
   transazione prima la natura (ora: il verbo), poi `fn_scrivi_dati_societari`, e il guard
   differito giudica lo stato finale.

## 5. Prove attese

> ⚠️ *Superate il 2026-11-14 (§0):* le prove «riga tolta con conferma» e «titolo chiuso al giorno
> prima» non esistono più. Le prove nuove: per ogni motivo del §0, il cambio rifiutato col motivo, e
> che passa dopo che il motivo è stato tolto a mano; DI → PR con un documento intestato, rifiutato
> anche al SUPER_ADMIN; SC → SP con documenti, che passa; il titolo di un altro emittente, che compare
> come motivo senza dettagli. Casi **costruiti** nel pgTAP; la nota sul flag qui sotto resta.

pgTAP che **costruiscono** i casi (non che li cercano nel seed): DI con dati societari → PR
(rifiuto senza conferma, riga tolta con conferma, storico scritto); DI con titolo `INTENTO`
vigente → PR (titolo chiuso al giorno prima); SC con `split_payment = 'S'` → natura senza split
(flag a `N`); SC (SRL) → SP senza forma nuova (rifiuto al COMMIT sul campo) e con la SNC (passa).

⚠️ *Nota del 2026-11-14, dal contratto (seed `80_data` di `config.tipi_soggetto_dettaglio` e i suoi
CHECK):* nel catalogo di oggi nessun cambio **dentro la stessa macro-tipologia** porta un flag da
ammesso a non ammesso: `cliente_pa_ammesso` è vero solo per `ENC`, unica natura della sua
macro-tipologia; `SC` e `SP` ammettono entrambe lo split; `chk_tipi_soggetto_dettaglio_regime_pa_natura`
li vieta alle persone fisiche. La voce resta (il catalogo è un CSV, il modello ammette il caso), ma il
pgTAP del flag deve **fabbricarsi** in transazione una natura di dettaglio `PG` senza split: «SC →
natura senza split» non si costruisce con le nature del seed.

## 6. Richieste a BE/FE (dopo il DB)

### 6.0 ⭐ La richiesta in vigore (giro 4, 2026-11-14) — il DB è fatto e applicato

Il modello è quello del §0: il cambio di natura **non pulisce niente**, il DB rifiuta ed elenca i
motivi, e l'operatore li toglie a mano. Ciò che il BE/FE deve fare, in elenco chiuso:

| # | Chi | Che cosa | Dove |
| --- | --- | --- | --- |
| K-1 | FE | Le **dodici chiavi i18n** emesse dal DB, in `it.json` e `en.json`: `config.tipi_entita.ricevuta`; sotto `anagrafiche.soggetti.cambio_natura_blocco`: `altra_macro_tipologia`, `con_documenti`, `piva_non_applicabile`, `cliente_pa`, `split_payment`, `titoli_iva`, `titoli_iva_altri_emittenti`, `dati_societari`, `indirizzi`, `senza_natura_con_titoli_iva`; `anagrafiche.soggetti.dati_societari_elimina_blocco.natura_li_richiede`. ⛔ **Sblocca il commit DB**: senza, `check-i18n-keys` lo rifiuta | `frontend/src/locales/it.json`, `frontend/src/locales/en.json` |
| K-2 | BE | Rigenerare le policy d'errore: sette codici nuovi (`E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA`, `_CON_DOCUMENTI`, `_PIVA_NON_APPLICABILE`, `_TITOLI_ALTRI_EMITTENTI`, `_CON_DATI_SOCIETARI`, `_INDIRIZZI_NON_AMMESSI`, `E_DATI_SOCIETARI_NON_ELIMINABILI`) | `manage.py genera_error_policies` → `backend/apps/core/services/error_policies_generated.py` |
| K-3 | BE | Le nature proponibili in modifica dal DB: `anagrafiche.fn_nature_proponibili_soggetto(soggetto_id)` (`tipo_soggetto_dettaglio_id`, `ammessa`, `motivo_codice`, `motivi`) al posto della regola «stessa macro-tipologia» calcolata nel BE (`tipi_modificabili_ids`); una natura non ammessa resta nell'elenco col suo motivo | `backend/apps/anagrafiche/db/soggetti_repository.py` (`get_soggetto`), e il suo contratto in uscita |
| K-4 | BE | Il PATCH del soggetto resta un `UPDATE` diretto: il guard `trg_soggetti_a10_guard_cambio_natura_upd` lo giudica. Il rifiuto porta nel contesto il `campo` e **tutti** i `motivi` (`script.fn_raise_primo_motivo_se_presente`): il BE li passa al FE, non solo il primo | `backend/apps/anagrafiche/services/soggetti_service.py` (aggiornamento del soggetto) |
| K-5 | BE | Un endpoint per l'**eliminazione manuale dei dati societari**: `anagrafiche.fn_elimina_dati_societari(soggetto_id)` (vero = eliminata, falso = niente da eliminare); per spegnere l'azione, `anagrafiche.fn_check_elimina_dati_societari(soggetto_id)` | `backend/apps/anagrafiche/api/views_soggetti.py`, `soggetti_service.py` |
| K-6 | FE | ⛔ Sparisce il «flag nascosto a `N`»: `cliente_pa` e `split_payment` non si forzano più a `N` quando la natura non li ammette. Se il DB rifiuta col motivo del flag, il campo si mostra e l'operatore lo porta a `N` lui | `frontend/src/anagrafiche/components/SoggettoDrawer.vue` (righe 398-399 al 2026-11-14) |
| K-7 | FE | La tendina della natura dalle nature proponibili (K-3): le non ammesse spente col motivo. Al salvataggio rifiutato, i motivi elencati tutti; quelli sui campi della riga (`partita_iva`, `cliente_pa`, `split_payment`) accendono il campo | `SoggettoDrawer.vue` |
| K-8 | FE | Nella sezione dei dati societari, l'azione «Elimina i dati societari» (K-5), con conferma esplicita; spenta col motivo quando la natura li richiede | il drawer o la sezione dei dati societari del soggetto |

⚠️ La P.IVA scritta su una ditta che diventa privato la svuota solo un SUPER_ADMIN
(`E_SOGGETTO_ID_FISCALE_IMMUTABILE`); con documenti intestati il cambio non si fa per nessuno (D-6).
I pezzi di §6 qui sotto restano come storia.

### 6.0-bis Esito BE/FE (sessione BE, 2026-11-15)

K-1 … K-8 fatti, da provare in app e da committare. Una sola deviazione dalla lettera, decisa da Tid:

* **K-4 — l'elenco dei motivi non arriva dal rifiuto, ma da un endpoint.** Il contesto che
  `script.fn_raise_primo_motivo_se_presente` compone (con `motivi`) finisce in `dbops.error_log`, non
  nell'eccezione: PostgreSQL consegna al BE codice, messaggio, campo e bersaglio, e l'envelope d'errore
  non ha un canale per una lista. *Decisione di Tid (2026-11-15):* `POST
  soggetti/<id>/cambio-natura/motivi/` (lettura in POST come `valida-cf-piva`, per non mettere la P.IVA
  nell'URL), che chiama `fn_check_cambio_natura_soggetto` coi valori proposti — chiave assente = il
  valore salvato. Il PATCH resta un `UPDATE` diretto giudicato dal guard; il drawer chiede i motivi al
  cambio della natura e dopo un rifiuto. Stesso schema di `magazzino/righe/motivi/`.
* **K-3:** `get_soggetto` porta `nature_proponibili` (da `fn_nature_proponibili_soggetto`);
  `tipi_modificabili_ids` è ritirata con il ripiego sulla natura del form. Nella tendina una natura è
  **spenta** solo se ha un motivo che non si toglie dal form; i motivi su `partita_iva`, `cliente_pa`,
  `split_payment` la lasciano scegliere e accendono il campo.
* **K-5/K-8:** `DELETE soggetti/<id>/dati-societari/` sul verbo; nel dettaglio la terna
  `can_elimina_dati_societari` (+ `_reason`, `_reason_key`, `_dettaglio`, famiglia 1 di api.md). La
  sezione dei dati societari resta visibile quando la natura scelta non li prevede ma il soggetto li ha.
* **K-2:** policy rigenerate (sette codici, nessuna classe spostata) e i sette messaggi di ripiego.
* Prove: `apps/anagrafiche/tests/db/test_cambio_natura_soggetto_db.py` (7, DB vero),
  `frontend/src/anagrafiche/composables/cambioNatura.spec.js` (10).
* *Revisione (2026-11-15):* l'endpoint dei motivi rifiuta una natura inesistente (400 col campo):
  la check risponde `[]` («parla la FK» del PATCH), che lì avrebbe detto «il cambio passa». Nel
  drawer il campo P.IVA si mostra anche quando la natura scelta non ne ha ma un motivo lo indica
  (come i flag, K-6); e un motivo su un campo che chi agisce non può scrivere (`non_editable_fields`:
  la P.IVA la svuota solo un amministratore) spegne la natura come gli altri. Se la richiesta dei
  motivi fallisce, il drawer lo dice invece di mostrare un elenco vuoto (decisione di Tid,
  2026-11-15); l'avviso alle altre tab dopo l'eliminazione dei dati societari resta com'è per tutte
  le sotto-risorse del soggetto (decisione di Tid, 2026-11-15).

> ⚠️ *Superate il 2026-11-14 (§0):* niente `conferma_pulizia` e niente dialog di conferma. Al loro
> posto: le nature in modifica dalla regola DB dei cambi ammessi, i motivi mostrati all'operatore, e il
> «flag nascosto a `N`» che sparisce. Il dettaglio si riscrive quando il DB è fatto.

* **BE**: `GET soggetti/{id}/cambio-natura/anteprima/?tipo_soggetto_dettaglio_id=` → le voci di
  `fn_check_cambio_natura_soggetto`; nella PATCH, un cambio di natura passa dal verbo, con
  `conferma_pulizia` dal payload.
* **FE**: al salvataggio con la natura cambiata, l'anteprima; con voci `PULISCI` un dialog di
  conferma che **elenca** le perdite, e `conferma_pulizia: true` solo dopo l'ok. Le voci
  `SCEGLI`/`COMPLETA` accendono i campi. ⛔ Sparisce il «flag nascosto parte `N`» di
  `SoggettoDrawer.handleSave`: diventa una pulizia confermata.

## 7. Domande aperte

> ⚠️ *2026-11-14:* Q-1 e Q-2 sono **superate** da D-5 (nessun titolo si chiude o si cancella da
> solo); le loro risposte restano scritte qui sotto come storia. Q-3 è chiusa: l'indirizzo non ammesso
> è un motivo, e l'operatore lo elimina a mano. Q-4 è chiusa: la P.IVA la svuota solo il SUPER_ADMIN, e
> con documenti intestati il cambio DI → PR è bloccato comunque (D-6). Aperta Q-5.

* **Q-5** *(2026-11-14)* — Una DI con dati societari che diventa PR: per D-5 la riga va tolta a mano
  prima del cambio, ma oggi **non c'è modo**. L'app non ha `DELETE` su `anagrafiche.dati_societari`
  (B-5) e un verbo che cancelli non esiste: il vicolo cieco del §1 resta. Decide Tid se esiste un'azione
  manuale «elimina i dati societari», separata dal cambio, oppure se la riga presente è un motivo
  definitivo.
  ✅ *Decisa da Tid il 2026-11-14 (D-7, §0):* l'azione manuale, separata dal cambio.
* **Q-6** *(2026-11-14, dal censimento §0.1)* — Per D-6 il documento blocca il cambio DI ↔ PR solo
  se il soggetto ne è la **controparte** (cliente o fornitore: `billing_account_id`, il cliente
  dell'ordine, destinatario e mittente), oppure in **qualunque ruolo** in cui il documento porta la sua
  identità (anche emittente, vettore, agente, reseller, responsabile di commessa)? Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-8, §0):* **qualunque ruolo**.
* **Q-7** *(2026-11-14, dal censimento §0.1)* — `shop.ricevute` è un documento fiscale ma non ha una
  riga in `config.sorgenti`, quindi una regola derivata dal registro non la vede. La si registra come
  sorgente (e allora entra da sola), o la si aggiunge alla regola a parte? Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-9, §0):* si **registra** come sorgente.
  ⚠️ *Fatto nuovo, stesso giorno, verificando cosa chiede il registro (Q-8):* registrare una sorgente
  vuol dire, sul precedente di `EMAIL` (lotto 0 di brief-db-grammatica-unica-documenti), tre pezzi: la
  riga in `config.sorgenti`, la gemella in `config.tipi_entita` (`is_sorgente`, presidiata da
  `test-grammatica-catalogo-sorgenti-entita-v1.sql`) e `trgfn_sorgente_in_uscita` all'AFTER DELETE. Ma
  la **grammatica** dei documenti vuole `id bigint` (e, facoltativo, `uid uuid`): lo hanno tutte le 17
  testate registrate, e `key_selector` ammette solo `id` o `uid` (`chk_sorgenti_key_selector_values`,
  letto da `script.fn_sorgente_chiave`). `shop.ricevute` ha **`id uuid`** e nessun id numerico: così
  com'è non entra nel registro senza rompere chi lo legge. Struttura del contorno: nessuna FK punta a
  `shop.ricevute`, nessuna funzione DB e nessun codice BE/FE la scrive o la legge (solo il suo guard
  `trgfn_ricevute_guard_ba_canale` e i pgTAP di RLS/postura).
* **Q-8** *(2026-11-14)* — La ricevuta fuori grammatica. (A) La si **allinea** prima alla grammatica
  (`id bigint` più `uid uuid`, come le altre testate) e poi la si registra, in un giro di questo brief:
  oggi costa poco, perché nessuno la scrive e nessuna FK la punta. Tocca lo schema `shop`, e la chiave
  i18n dell'etichetta di `tipi_entita` diventa una richiesta al FE. (B) Resta **fuori**, come residuo
  con un brief suo: si allinea e si registra quando il cantiere dello shop le darà un verbo di
  scrittura, e da quel giorno la regola di D-6 la vede da sola. Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-10, §0):* **(A)**, la si allinea e la si registra nel giro 1.
* **Q-9** *(2026-11-14, dalla prova del giro 2)* — Il cambio fra **macro-tipologie diverse** (es. ente
  non commerciale `ENC` ↔ società di capitali `SC`). Oggi lo vieta solo il BE (`tipi_modificabili_ids`,
  stessa macro-tipologia); il DB lo lascia passare. Il giro 2 lo porta nel DB come primo motivo
  (`E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA`). Dal contratto: i ruoli ammessi dipendono dalla
  macro-tipologia (`config.tipi_ruoli_nature_ammesse`), quindi un cambio fra famiglie può lasciare
  ruoli non ammessi. Quattro pgTAP costruiscono proprio quel cambio per provare altro
  (`test-soggetti-regime-pa-v1.sql` 8-9, `test-fn-scrivi-dati-societari-v1.sql` 16-17) e col giro 2
  diventano rossi. (A) il DB lo vieta, e i quattro test si riscrivono su una coppia della stessa
  famiglia; (B) il DB lo ammette, e il motivo esce dalla regola. Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-11, §0):* **(A)**, il DB lo vieta.
* **Q-10** *(2026-11-14, dal pgTAP del giro 3)* — ⚠️ **Correzione di un fatto del brief.** D-7 dice «la
  riga eliminata resta nello storico», e il §2 lo ripeteva dal brief d'origine. È falso in generale:
  `script.trgfn_storico_generic` scrive solo se la riga ha `storicizza = true` (opt-in per riga), e su
  `anagrafiche.dati_societari` la colonna vale `false` di default; `fn_scrivi_dati_societari` non la
  accende. Quindi l'eliminazione manuale, oggi, **non lascia traccia**. (A) il verbo accende
  `storicizza` sulla riga prima di cancellarla, così l'eliminazione resta sempre nello storico; (B)
  decide il flag della riga, come per ogni altra tabella. Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-12, §0):* **(A)**. ⚠️ In progettazione la forma è cambiata: il verbo
  non può accendere il flag con un `UPDATE`, perché `trgfn_dati_societari_guard_tipo_soggetto` rifiuta
  ogni `UPDATE` della riga incongrua che il verbo deve togliere. La tabella entra invece nel registro
  dello storico, come `anagrafiche.soggetti` e `vendite.fatture`: memoria continua di ogni modifica e
  cancellazione.

* **Q-1** — Un titolo non ammesso con `valido_dal` **dopo** il giorno prima del cambio non si può
  chiudere a quella data (`valido_al < valido_dal`). Si cancella (non ha mai valso) o si chiude a
  `valido_dal`? Da decidere con Tid. Verificare anche i consumi di plafond già registrati dopo la
  data di chiusura.
  ✅ *Decisa da Tid il 2026-11-14 (D-3, §3):* si **cancella**. Resta da confermare il caso con
  consumi di plafond già registrati dopo la data di chiusura (proposta: rifiuto del cambio).
* **Q-2** — I titoli sono per **emittente**, e l'operatore vede solo i suoi (RLS); la natura è
  del **soggetto**. Proposta: si chiudono tutti (la natura non è dell'emittente), e il dialog
  dice «N titoli di altri emittenti» senza dettagli. Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-4, §3):* **rifiuto**, l'intervento è del SUPER_ADMIN (la
  proposta «si chiudono tutti» è scartata). Ricadute per il progetto: l'anteprima deve saper dire
  «titoli di altri emittenti» senza vederli (lettura `SECURITY DEFINER`, come
  `fn_titolo_iva_non_ammesso_del_soggetto`), con un esito che non è né `PULISCI` né
  `SCEGLI`/`COMPLETA`; serve un codice d'errore suo; da verificare in sviluppo che il SUPER_ADMIN
  veda e possa chiudere i titoli di tutti gli emittenti (RLS di `soggetti_titoli_iva`).
* **Q-3** — Un indirizzo di tipo che la natura nuova non ammette (la sede legale di una DI che
  diventa PR): c'è un guard? Se no, è un buco del modello da chiudere, e l'esito (pulizia
  confermata o rifiuto) lo decide Tid.
  ✅ *Verificato il 2026-11-14:* il guard c'è **solo dal lato dell'indirizzo**
  (`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`, all'INSERT/UPDATE della riga di indirizzo, con
  `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`). Nessun trigger di `anagrafiche.soggetti` rilegge gli
  indirizzi esistenti quando cambia la natura: il buco è confermato. Resta da decidere l'esito
  (pulizia confermata, cioè una voce `PULISCI`, o rifiuto). Attenzione al «fallback permissivo» del
  guard: una natura **senza** righe di matrice ammette qualunque tipo.
* **Q-4** *(nuova, 2026-11-14)* — Una partita IVA scritta su una natura nuova con
  `formato_piva = NON_APPLICABILE` (DI → PR). Oggi nessun guard la rifiuta: `fn_validate_cf_piva_it`
  con `NON_APPLICABILE` salta la validazione e basta, quindi il privato si tiene la P.IVA della ditta.
  Se è un dato non congruo da pulire (D-0), la pulizia urta
  `trgfn_soggetti_guard_id_fiscale_immutabile` (dal `20261110-96`): una P.IVA scritta si svuota solo
  da SUPER_ADMIN, perché CF e P.IVA sono la chiave d'unicità del soggetto
  (`uq_soggetto_idstato_id_fiscale_univoco`). Le strade: (a) la P.IVA resta, e `NON_APPLICABILE` vuol
  dire solo «non si valida»; (b) voce `PULISCI` e il verbo la svuota anche contro il guard (eccezione
  dentro il verbo); (c) il cambio DI → PR con P.IVA scritta è rifiutato a chi non è SUPER_ADMIN, come
  il cambio della P.IVA stessa. Decide Tid.
  *Fatti aggiunti il 2026-11-14, dalla discussione con Tid («è giusto che una DI diventi PR?»):*
  la DI ha la P.IVA **obbligatoria** nel modello (`piva_obbligatoria = true`, `NUM_11`); la chiave
  d'unicità di una persona fisica è il **codice fiscale** (`id_fiscale_univoco_cf_piva` =
  `UPPER(TRIM(codice_fiscale))` in `fn_crea_soggetto_pf`), quindi la strada «si chiude la ditta e si
  crea un privato nuovo» non esiste: un secondo soggetto con lo stesso CF è rifiutato. E le nature
  ammesse in modifica (`tipi_modificabili_ids`) le calcola il **BE**
  (`soggetti_repository.get_soggetto`: stessa macro-tipologia), non una regola del DB.

## 8. Diario

| Data | Evento |
| --- | --- |
| 2026-10-11 | Brief aperto dalla revisione BE/FE del brief dati fiscali; decisioni di Tid D-0, D-1, D-2. |
| 2026-11-14 | Riverifica sullo stato di sviluppo (sessione DB). Reggono: tutti gli oggetti citati esistono con il contratto descritto; B-5 vale ancora (`anagrafiche.dati_societari` fra le tabelle in sola lettura per l'app, `90_end/20261011-04` e loop dei grant); le riscritture di `fn_scrivi_dati_societari` (`20261012-02`, `20261025-87`) non toccano D-2; nessuna delle funzioni proposte e nessun codice nuovo esiste; il «flag nascosto a `N`» è ancora in `SoggettoDrawer.vue`. Aggiunti: blocco «Chi riparte», la nota sul BB `fn_titolo_iva_non_ammesso_del_soggetto` (§4.1), la nota sul pgTAP dei flag (§5), l'esito di Q-3 (buco confermato), Q-4 e le due righe della partita IVA nel §2. Decise D-3 (Q-1) e D-4 (Q-2). |
| 2026-11-14 | Tid rivede il modello: D-5 (il cambio non pulisce niente, rifiuta coi motivi, giro manuale; vale anche per il SUPER_ADMIN) e D-6 (i documenti intestati bloccano solo i cambi DI ↔ PR). Revocate D-0, D-1, D-3, D-4; superati §4.2-4.3, §5, §6; Q-1 … Q-4 chiuse o superate. Nuovo §0; aperta Q-5. |
| 2026-11-14 | Q-5 decisa da Tid (D-7): l'eliminazione manuale dei dati societari, separata dal cambio. Nessuna decisione aperta; riparte il team DB, al via di Tid. |
| 2026-11-14 | Via di Tid. Censimento dei documenti per D-6 (§0.1): la sede è `config.sorgenti` (categoria `DOCUMENTO`), le colonne si derivano da `pg_constraint` verso cinque tabelle ponte; la regola gemella è `fn_ba_ha_storia_emittente`. Aperte Q-6 (il ruolo) e Q-7 (`shop.ricevute`, fuori registro). |
| 2026-11-14 | Q-6 decisa da Tid (D-8): qualunque ruolo. Q-7 decisa (D-9): `shop.ricevute` si registra come sorgente. Verificando il registro: la ricevuta ha `id uuid`, fuori dalla grammatica dei documenti (`id bigint`); aperta Q-8. |
| 2026-11-14 | Q-8 decisa da Tid (D-10): la ricevuta si allinea e si registra. Piano dei quattro giri nel §0; giro 1 in progettazione, vincolo dello storico trovato. |
| 2026-11-14 | Giro 1 scritto e provato (`20261114-59`, le righe `RICEVUTA` dei due CSV, il pgTAP): verde la parte di struttura, mutazione rossa come attesa. Da applicare; il commit aspetta la chiave i18n del FE. |
| 2026-11-14 | Tid applica il giro 1: pgTAP verdi. Progetto del giro 2 scritto nel §0. |
| 2026-11-14 | Giro 2 scritto (`20261114-60 … -68`, sei codici e sei frasi nel catalogo) e provato per intero sullo scratch. Fra i pgTAP che cambiano la natura, cinque identici con e senza; tre cambiano: il test 3 dei titoli (lettore ritirato, da riscrivere) e i quattro che costruiscono un cambio fra macro-tipologie: aperta Q-9. Manca il pgTAP della regola. |
| 2026-11-14 | Q-9 decisa (D-11). Tid applica il giro 2 mentre i test si riscrivono: da qui `-60 … -68` sono congelati. Riscritti i tre pgTAP toccati, scritto `test-cambio-natura-soggetto-v1.sql` (17/17 sullo scratch). Trovato: il test 15 dei titoli era verde in prova solo perché da proprietario la RLS non c'è. |
| 2026-11-14 | Tid: migrazione applicata, pgTAP del giro 2 verdi come applicazione (anche 14-15 dei titoli). Parte il giro 3. |
| 2026-11-14 | Giro 3 scritto: `20261114-69` (check e verbo), codice `E_DATI_SOCIETARI_NON_ELIMINABILI` (frase 1490), `test-fn-elimina-dati-societari-v1.sql`. Sullo scratch 10/12: il 5 aspetta la frase dal CSV (atteso); il 10 ha trovato che lo storico scrive solo con `storicizza = true`: aperta Q-10, corretto D-7. Da applicare dopo Q-10. |
| 2026-11-14 | Q-10 decisa (D-12). Il verbo non può accendere il flag (il guard del tipo soggetto rifiuta l'UPDATE della riga incongrua): la tabella entra nel registro dello storico (`-70`, `-71`). Trovato: il CSV del registro non è un mirror. Giro 3 provato, 13/14 (il 14° aspetta la frase). Da applicare. |
| 2026-11-14 | Tid: giro 3 applicato, pgTAP verdi. Scritta la richiesta BE/FE (§6.0, K-1 … K-8). Il lavoro DB del brief è completo. |
| 2026-11-15 | Sessione BE: K-1 … K-8 fatti (§6.0-bis), con la decisione di Tid sull'endpoint dei motivi (K-4). Revisione: natura inesistente rifiutata dall'endpoint, P.IVA visibile quando un motivo la indica, campi bloccati che spengono la natura, avviso se i motivi non si leggono. Prova in app di Tid riuscita. Brief chiuso e archiviato su richiesta di Tid; nessun debito. |
