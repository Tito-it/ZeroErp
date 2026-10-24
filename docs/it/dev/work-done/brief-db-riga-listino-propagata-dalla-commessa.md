# Brief DB — La riga di listino che ha dato il prezzo a una commessa non si tocca più

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-08. **A chi:** team DB
> (`dev/db-tid`); poi BE (§5), che **attende** la consegna DB.
> **Origine:** L0 di [piano-be-type-checker.md](../work-done/piano-be-type-checker.md) §4.4.
> Riscrivendo riallinea e sblocca del prezzo di una riga di commessa, la
> provenienza del prezzo è diventata un insieme unico (building block
> `apps/vendite/services/prezzo_riga_commessa.py`). `listino_riga_id` ne è rimasta
> **fuori**, perché scriverla cambia il comportamento dei listini e il push non
> la può passare.
> **Decisione:** di Tid, 2026-10-08 — una riga di listino che ha dato il prezzo
> a una riga di commessa **diventa immutabile** (è «propagata»).
> **Stato:** ✅ **chiuso il 2026-10-09.** R-1, R-2, R-5 applicati a DB, pgTAP
> verdi; R-3 e R-4 decisi (§6); BE fatto lo stesso giorno (§7). Debito aperto in
> un brief a parte:
> [brief-db-coerenza-listino-della-riga-di-commessa](brief-db-coerenza-listino-della-riga-di-commessa.md).

## 1. La regola

Il prezzo di una riga di commessa deve restare **riproducibile**: la riga di
listino da cui viene non si modifica né si cancella finché una riga a valle la
cita. È la regola che `vendite.trgfn_listini_righe_guard_stato` scrive già per le
versioni `ATTIVA` («ammessa solo se la riga non è propagata a valle»), ed è la
ragione dell'eccezione N6 (rettifica controllata solo su righe non propagate).

Il guard c'è. Manca chi **scrive** il legame.

## 2. Che cosa dice oggi il DB (contratto, letto dalla doc auto-generata)

| Sede | Che cosa fa | Con la regola |
| --- | --- | --- |
| `vendite.trgfn_listini_righe_guard_stato` | su versione `ATTIVA` blocca UPDATE e DELETE di una riga se `EXISTS` una `commesse_attivita` o una `attivita_fatturabili` con `listino_riga_id = OLD.id` (`E_RIGA_LISTINO_PROPAGATA`) | ✅ è la regola |
| `vendite.fn_upsert_commessa_attivita` (madre del push) | ha `p_listino_versione_id`, **non** ha un parametro per `listino_riga_id`: la riga di commessa nasce con la colonna `NULL` | 🔴 nessun push può scrivere il legame |
| `vendite.fn_batch_upsert_commessa_attivita` | legge dal JSON `listino_versione_id` e lo passa alla madre; `listino_riga_id` no | 🔴 idem |
| `vendite.fn_emit_attivita_fatturabili_da_commessa` | copia su `attivita_fatturabili` gli otto campi di audit del prezzo (`prezzo_base_snapshot`, `origine_prezzo`, …), **non** `listino_riga_id` | 🔴 il legame non arriva nemmeno a valle |
| `vendite.fn_resolve_prezzo_listino_v2[_esito]`, stadio BUNDLE | il prezzo viene da `listini_righe_componenti` (`v_bundle_riga_id`), ma l'id di quella riga **non è restituito**; `listino_riga_id` resta `NULL` | 🟡 vedi §3 R-4 |

Risultato: oggi **nessun percorso** scrive `listino_riga_id` su una riga di
commessa o di attività fatturabile. Per il guard dei listini una riga usata da
una commessa non risulta mai «propagata», e la rettifica N6
(`ListiniRepository.check_riga_propagata` lato BE) la lascia modificare.

⚠️ Il backend può già scrivere la colonna con una `UPDATE` dal riallineamento,
ma non lo fa apposta: scriverla da un percorso solo sarebbe un'asimmetria (una
riga di listino «propagata» solo se qualcuno ha premuto «riallinea»).

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **La madre del push riceve la riga di listino.** `fn_upsert_commessa_attivita` acquista `p_listino_riga_id bigint DEFAULT NULL` e la scrive (INSERT e ramo `ON CONFLICT DO UPDATE`, come `listino_versione_id`). ⚠️ La firma si **sostituisce**, non si affianca: un overload con un parametro in più e `DEFAULT` renderebbe ambigue le chiamate esistenti (`fn(T)` + `fn(T, U DEFAULT NULL)`). Allineare `fn_batch_upsert_commessa_attivita` (chiave JSON `listino_riga_id`) e il builder `dbops.fn_pgtap_crea_commessa_attivita`, se il team DB lo ritiene. |
| **R-2** | **Il legame arriva a valle.** `fn_emit_attivita_fatturabili_da_commessa` copia `listino_riga_id` insieme agli otto campi di audit che già copia. |
| **R-3** | **Che cosa vuol dire «propagata» quando il prezzo cambia** — da decidere. Oggi il guard guarda il riferimento **attuale**: se un riallineamento sposta la riga di commessa dalla riga di listino R1 alla R2, R1 torna modificabile (a meno che un'attività fatturabile già in fattura la citi ancora). Il prezzo vecchio resta nel diario della riga (`meta.riallineamenti`), ma senza l'id della riga di listino. Due letture possibili: «propagata = citata **adesso**» (com'è) oppure «propagata = citata **almeno una volta**» (serve un registro, o la storia). Il BE propone la prima, ma è una decisione sul modello. |
| **R-4** | **Il kit (stadio BUNDLE).** Il prezzo di un componente dentro un kit viene da `listini_righe_componenti`, che ha il suo guard (`trgfn_listini_righe_comp_guard_immutabilita_v5`) ma nessun legame con la commessa. La stessa regola vale per quella riga? Se sì, servono l'id della riga bundle in uscita dal resolver, una colonna su `commesse_attivita` (e `attivita_fatturabili`) e il guard che la guarda. Se no, va scritto perché. |
| **R-5** | **pgTAP.** Il caso costruito: una riga di commessa nata dal push con la riga di listino; UPDATE e DELETE della riga di listino su versione `ATTIVA` → `E_RIGA_LISTINO_PROPAGATA`; la stessa riga di listino **non** citata → modificabile. E per R-2: l'attività fatturabile emessa porta la riga di listino. |

## 4. Fuori da questo brief

- **Il recupero delle righe esistenti.** Il progetto non è in produzione: le
  righe di commessa già scritte restano senza riga di listino. Nessuna
  migrazione di dati.
- **Le altre famiglie di riga** (righe di onere, rettifiche da reso): non vengono
  dal listino (`fn_aggiungi_onere_commessa` passa `p_listino_versione_id = NULL`;
  le rettifiche citano la fattura). Restano con la colonna `NULL`.

## 5. Ricaduta BE (dopo la consegna DB)

1. `listino_riga_id` entra nella provenienza: `COLONNE_PROVENIENZA_PREZZO` in
   `apps/vendite/db/commesse_repository.py` (sede unica) e
   `provenienza_da_resolver` nel building block. Da lì lo prendono il push
   (`CommessaAttivitaInput` → `batch_upsert_attivita`) e riallinea/sblocca
   (`update_attivita_prezzo`, su commessa e attività fatturabile).
2. La variazione eccezionale lo azzera con il resto della provenienza da listino:
   un prezzo scritto a mano non viene da una riga di listino.
3. Test sul DB vero: la rettifica N6 di una riga di listino usata da una
   commessa risponde `E_RIGA_LISTINO_PROPAGATA` (oggi passa).
4. Se R-4 è sì: il kit, con la sua colonna, nello stesso giro.

## 6. Esito DB (2026-10-09, `dev/db-tid`)

### 6.1 Decisioni

* **D-1 (R-3) — «propagata» = citata ADESSO**, cioè com'è oggi il guard. Quello che
  deve restare riproducibile è il prezzo **fatturato**, e con R-2 lo garantisce
  l'attività fatturabile emessa, che cita la riga di listino e la blocca. Dopo un
  riallineamento la riga di commessa ha un prezzo nuovo e non dipende più dalla
  riga vecchia. «Citata almeno una volta» richiederebbe un registro per proteggere
  un prezzo che nessun documento porta. **Per il BE (facoltativo):** scrivere l'id
  della riga di listino nella voce di `meta.riallineamenti`, così la storia del
  prezzo resta leggibile.
* **D-2 (R-4) — il kit: nessun legame nuovo.** Il guard dei componenti
  (`trgfn_listini_righe_comp_guard_immutabilita_v5`) è più severo di quello delle
  righe: DELETE sempre bloccato, UPDATE di prezzo, IVA e validità bloccato in ogni
  versione non in `BOZZA`, senza l'eccezione N6. Un componente che ha dato un
  prezzo da una versione `ATTIVA` o `CHIUSA` è già immutabile. Non servono una
  colonna nuova né un guard. Il §5.4 del BE quindi non scatta.
  ⚠️ Vale per le versioni `ATTIVA`/`CHIUSA`. Il **percorso rapido** del resolver
  (`p_listino_versione_id_preferito`) non guarda lo stato della versione, quindi un
  prezzo può venire da una `BOZZA`, dove righe e componenti restano modificabili
  per scelta. Riguarda righe e kit allo stesso modo, ed è finito in D-3.
* **D-3 — la coerenza del legame va in un brief a parte.** Nessuna regola dice che
  la riga di listino citata sia della versione citata, che il listino sia
  dell'emittente della commessa e che la versione sia in vigore. Senza la regola
  sull'emittente, il guard dei listini (INVOKER, sotto RLS) può non vedere una
  commessa di un altro emittente e giudicare la riga «non propagata». Un controllo
  nella sola madre lascerebbe scoperti l'`UPDATE` diretto del BE e l'emissione:
  la sede giusta è un trigger della tabella. →
  [brief-db-coerenza-listino-della-riga-di-commessa](brief-db-coerenza-listino-della-riga-di-commessa.md).
* **Builder `dbops.fn_pgtap_crea_commessa_attivita`: non toccato.** Costruisce
  un'attività senza listino, e così deve restare: il listino è il caso del test.
  Il pgTAP di R-5 chiama la madre direttamente.

### 6.2 Cosa è stato scritto

| File | Che cosa |
| --- | --- |
| `20_code/vendite/20261009-04-update-fn-upsert-commessa-attivita-listino-riga` | R-1: `p_listino_riga_id` in coda (`DEFAULT NULL`), scritto in INSERT e `ON CONFLICT`. DROP + CREATE: un parametro in più con DEFAULT creerebbe un overload ambiguo. Firma con i `%TYPE` dal 20260818-29, corpo dall'oggetto vivo |
| `20_code/vendite/20261009-05-update-fn-batch-upsert-commessa-attivita-listino-riga` | R-1: la chiave JSON `listino_riga_id`, facoltativa, passata alla madre |
| `20_code/vendite/20261009-06-update-fn-emit-attivita-propaga-listino-riga` | R-2: l'emissione copia `listino_riga_id` su `attivita_fatturabili` (INSERT e UPDATE) |
| `80_data/changelog/20261009-07-upsert-fk-index-policy-riga-listino-propagata` + `sql/dbops/fk_index_policy_riga_listino_propagata.csv` | gli indici delle due FK su `listino_riga_id`, da `false` a `true`, **parziali** `IS NOT NULL` (linee-guida-sql §8.4). Con la colonna popolata, il guard la interroga a ogni modifica di una riga di listino `ATTIVA`, e così fa il controllo FK al DELETE |
| `db/pgtap/vendite/test-riga-listino-propagata-dalla-commessa-v1.sql` | R-5, 9 test (sotto) |

**Chiamanti della madre: nessuno toccato.** Censiti sul nome: tre funzioni DB, il
builder pgTAP, il backend e i pgTAP. Passano tutti argomenti **nominali**, quindi
il parametro in coda non sposta nessuno.

**pgTAP di R-5:**
1. c'è una sola madre, ed ha il parametro;
2. il push scrive R1;
3. UPDATE di R1 → `E_RIGA_LISTINO_PROPAGATA`;
4. DELETE di R1 → `E_RIGA_LISTINO_PROPAGATA`;
5. una riga non citata resta modificabile;
6. il re-push dal **batch** sullo stesso segmento porta la commessa su R2 (ramo
   `ON CONFLICT`);
7. R1 torna modificabile (D-1);
8. l'emissione porta R2 sull'attività fatturabile;
9. R2 ora è bloccata.

I rifiuti si asseriscono sul **codice**, letto dal `CONSTRAINT_NAME`
dell'eccezione, e non su un P0001 qualunque.

### 6.3 Prova pre-apply

Fatta su un **cluster PG18 usa-e-getta**: clone del catalogo di dbdev
(`pg_dump -s` come app, dati con `--enable-row-security`) con i ruoli veri. L'SQL
è **estratto** dagli YAML ed eseguito da `titodb`, i test girano come
`zeroerp_app`.

* **Applicazione:** i tre changeSet passano. Resta **una** sola madre, e i grant
  all'app si ripristinano dai default privileges.
* **pgTAP nuovo:** 9/9 dopo; prima si ferma alla prima chiamata, perché il
  parametro non esiste.
* **Mutazioni:** senza `-05` cade il test 6 (e a cascata l'8 e il 9); senza `-06`
  cade l'8.
* **Regressione:** 75 pgTAP che nominano le tre funzioni, il builder o
  `listini_righe`, prima e dopo sugli stessi file: **362 ok / 29 not ok in
  entrambi**, stessi nomi dei rossi. ⚠️ Sul clone arrivano in fondo solo **22 file
  su 75**: gli altri pescano un billing account dai dati, che sotto RLS il clone
  non ha. Si fermano allo **stesso** errore prima e dopo, quindi il confronto non
  dice niente su quelle asserzioni. La corsa che conta resta quella di Tid su dbdev.
* **`plpgsql_check`** sulle tre funzioni: zero errori. Sul batch restano i due
  avvisi preesistenti sulla variabile `i`, identici a prima.
* **`-07`:** l'upsert del CSV e `CALL dbops.apply_fk_index_policy()` (in ROLLBACK)
  creano i due indici parziali, e `dbops.vw_fk_senza_indice` non elenca più le due
  FK.

### 6.4 Per il BE (§5)

* la chiave del payload del batch è **`listino_riga_id`**;
* il parametro della madre è **`p_listino_riga_id`**;

### 6.5 Applicato (2026-10-09, Tid)

Su dev, `-04`…`-07` risultano `EXECUTED` in `databasechangelog`. C'è una sola
`fn_upsert_commessa_attivita`, i due indici parziali esistono e i pgTAP sono verdi.
Lato DB questo brief è chiuso. Resta aperto per il §5 (BE); il debito D-3 vive nel
suo brief.

## 7. Esito BE (2026-10-09, `dev/backend-tid`)

Il §5 punto per punto. Il §5.4 non scatta (D-2).

| § | Che cosa | Dove |
| --- | --- | --- |
| 5.1 | `listino_riga_id` entra nella provenienza: `COLONNE_PROVENIENZA_PREZZO` (sede unica) e `provenienza_da_resolver`. Il push lo passa (`CommessaAttivitaInput.listino_riga_id` → chiave JSON `listino_riga_id` del batch, `p_listino_riga_id` della madre nella porta singola); riallinea e sblocca lo scrivono con `update_attivita_prezzo`, sulla riga di commessa **e** sull'attività fatturabile non ancora in fattura | `apps/vendite/db/commesse_repository.py`, `apps/vendite/services/prezzo_riga_commessa.py`, `apps/vendite/services/commesse_source_handlers.py` |
| 5.2 | La variazione eccezionale lo azzera con il resto (`provenienza_manuale`): la riga di listino, non più citata, torna modificabile | `apps/vendite/services/commesse_service.py` |
| D-1, facoltativo | Il diario porta la riga di listino: `listino_riga_id_precedente` / `_nuovo` in `meta.riallineamenti`, `listino_riga_id_riferimento` in `meta.variazioni_eccezionali` | `apps/vendite/services/commesse_service.py` |
| 5.3 | Test sul DB vero, mondo costruito (`test_prezzo_riga_commessa_db.py`, 4 e 5): la rettifica N6 passa finché nessuno cita la riga; dopo il riallineamento è rifiutata, e lo è anche l'`UPDATE` diretto della riga di listino (`E_RIGA_LISTINO_PROPAGATA`, letto dal `CONSTRAINT_NAME`); dopo la variazione a mano torna rettificabile. Il push dal batch scrive la riga di listino | `apps/vendite/tests/db/test_prezzo_riga_commessa_db.py` |

**Prove.** Suite `apps.vendite` con `ZEROERP_TEST_DB_E2E=1` su dev: 2343 ok.
**Mutazioni:** togliendo la chiave del batch cade il test 5; togliendo la colonna
dall'`UPDATE` del riallineamento cade il 4. ruff e mypy puliti sui file toccati.

**La rettifica N6 risponde con il codice del DB (ok Tid 2026-10-09).**
`fn_rettifica_controllata_riga` ricontrollava in Python la regola del guard
(`ListiniRepository.check_riga_propagata`) e rifiutava con un codice suo,
`E_VENDITE_RIGA_GIA_PROPAGATA`. Il controllo è stato tolto: il service scrive, il
guard rifiuta con `E_RIGA_LISTINO_PROPAGATA` (o `E_RIGA_LISTINO_VERSIONE_CHIUSA`) e
`ErrorManager.raise_from_database_error` porta il codice al chiamante. Il test 4
lo prova sul DB vero. L'override UI (toast) è passato al codice del DB. Il ritiro
del codice vecchio dal catalogo è chiesto al team DB:
[brief-db-ritiro-codice-riga-gia-propagata](brief-db-ritiro-codice-riga-gia-propagata.md).
