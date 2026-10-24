# Piano BE/FE — magazzino, Lotti 3 e 3-bis (bolla e reso muovono la merce)

## ⏭️ Chi riparte — aggiornato al 2026-10-14

**Riparte: Tid**, col collaudo a video:
[collaudo-in-app-magazzino-bolla-e-reso](collaudo-in-app-magazzino-bolla-e-reso.md). Il lato BE/FE e' fatto;
i due brief DB del Lotto 3 e del 3-bis sono **chiusi e archiviati** (2026-10-14), e quel che restava
loro sta qui, al §5. Questo piano e' l'unico documento aperto dei due lotti.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | SQL delle azioni `emetti_ddt` e `conferma_reso` sui profili, su dbdev (2026-10-12) | §2 | — |
| 2 | ✅ sessione BE | **A1** — ogni cambio di stato della bolla dal verbo (Lotto 3 R-1) | §3 | — |
| 3 | ✅ sessione BE | **A2** — magazzino sulla testata di bolla e reso (Lotto 3 R-2a, 3-bis R-1a) | §3 | A1 |
| 4 | Tid | collaudo del blocco A: una bolla che muove merce si emette, senza scelte | §4 | 1, 3 |
| 5 | ✅ sessione BE | **B1** — i prelievi della bolla (Lotto 3 R-2b) | §3 | A2 |
| 6 | ✅ sessione BE · ✅ team DB | **B2** — i rientri del reso (3-bis R-1b) ✅; R-1c ✅: [brief-db-reso-motivi-conferma-con-valori](../work-done/brief-db-reso-motivi-conferma-con-valori.md) applicato e archiviato (2026-10-14), BE/FE senza codice; il tooltip coi numeri si collauda al §5.3/§5.7 del collaudo | §3 | B1 |
| 7 | Tid | collaudo del blocco B: lotti, seriali, ubicazioni, reso e storno | §4 | 6 |
| 8 | ✅ sessione BE | **C1** — blocchi dalla scheda disponibilità (Lotto 3 R-5) | §3 | — |
| 9 | ✅ sessione BE | **C2** — offerta: cliente in bozza, fornitura, codici delle eccezioni; commenti superati | §3 | — |
| 10 | Tid | collaudo del blocco C, poi archiviazione dei due brief e di questo piano | — | 8, 9 |

**Decisioni aperte di Tid:** nessuna (2026-10-12: SQL delle azioni preparato qui; lookup dei magazzini
filtrato sull'emittente del documento; cliente dell'offerta modificabile in bozza; gli endpoint
`…/contratti/<id>/utility/` **restano**, li usera' R-FE-3 di brief-db-indirizzi-documento-seguono-il-cliente;
il piano procede per blocchi, senza passaggi intermedi: non siamo in produzione).
**Da committare:** niente: A1…C2, la revisione e il BB `SezioneMerceDocumento` sono in git dal 2026-10-13.

> **Chi scrive:** sessione BE, 2026-10-12, su decisione di Tid. **Origine:** §6 del
> [brief del Lotto 3](../work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md) (R-1…R-5) e §6 del
> [brief del 3-bis](../work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md) (R-1…R-5), il cui lato DB e'
> applicato e verde dal 28/29-09. Piu' i residui trovati rileggendo la modifica dei documenti (§3, C2).

---

## 1. Dove siamo (letto il 2026-10-12)

| Richiesta | Stato |
| --- | --- |
| Lotto 3 R-3, 3-bis R-2 — codici, ripieghi, chiavi i18n dei motivi | ✅ fatti |
| Lotto 3 R-4, 3-bis R-3 — azioni nell'editor profili | ✅ l'elenco si legge da `config.azioni_processo` |
| 3-bis R-4 — madri del reso con l'utente impostato | ✅ (`jwt_audit_authentication` imposta `app.current_user_id`) |
| Lotto 3 R-1 — cambio di stato dal verbo | ❌ solo l'annullo passa da `fn_cambia_stato_ddt`; `ddt_repository.update_stato` fa l'`UPDATE` diretto, che la porta del registro rifiuta (`E_DDT_STATO_SOLO_DA_VERBO`) su una bolla che muove merce |
| Lotto 3 R-2a, 3-bis R-1a — magazzino sulla testata | ❌ ne' letto ne' scritto dal BE, nessun campo a video; il motivo «La bolla non indica il magazzino di partenza» compare, e l'operatore non ha dove correggerlo |
| Lotto 3 R-2b, 3-bis R-1b — prelievi e rientri | ❌ |
| Lotto 3 R-2c — motivi fisici sull'azione «Emetti» | ✅ arrivano con i `valori` |
| 3-bis R-1c — motivi sull'azione «Conferma» del reso | ⚠️ difetto DB: `fn_available_actions_reso` passa `reason_key` senza `reasons`/`valori`; le frasi con `{0}` escono vuote |
| Lotto 3 R-5 — blocchi | ❌ c'e' solo la lettura (`DisponibilitaBlocchiPopover`) |
| 3-bis R-5 — commenti di `resi_service` | ⚠️ codice gia' giusto (`E_RIGA_DOC_NON_BOZZA`), commenti superati |

---

## 2. Prerequisito: le azioni sui profili (Tid, dbdev)

Dopo A1 ogni passaggio a `EMESSO` (anche di una bolla senza merce) e ogni annullo di una bolla emessa
chiedono `emetti_ddt`; conferma e annullo del reso chiedono gia' oggi `conferma_reso`. Un profilo senza
l'azione riceve `E_PERMESSO_NEGATO` dove prima passava.

**La regola dell'SQL, sul modello:** l'azione si concede ai profili la cui area arriva al livello minimo
che l'azione dichiara — lo stesso confronto con cui il DB la applica (`script.fn_area_consente_azione`,
il tetto d'area). Un profilo che non arriva al tetto non la userebbe comunque. ⛔ `blocca_merce` **non**
si concede qui: e' una capacita' nuova (riservare merce a un cliente), non una che i profili hanno gia';
si concede dall'editor quando serve. Il super admin (l'utente `smoke`) passa senza azioni.
Le righe gia' presenti non si toccano (`DO NOTHING`): un `false` scritto da qualcuno e' una decisione.

```sql
-- 1) Anteprima: chi riceve che cosa.
SELECT p.codice AS profilo, ap.permission_codename AS azione, pa.livello AS livello_area
  FROM config.azioni_processo ap
  JOIN config.profili_accesso_aree pa ON pa.area_id = ap.area_id
  JOIN config.profili_accesso p       ON p.id = pa.profilo_accesso_id AND p.attivo
 WHERE ap.permission_codename IN ('emetti_ddt', 'conferma_reso')
   AND ap.attivo
   AND script.fn_area_consente_azione(pa.livello, ap.livello_minimo_area)
   AND NOT EXISTS (SELECT 1 FROM config.profili_accesso_azioni x
                    WHERE x.profilo_accesso_id = pa.profilo_accesso_id AND x.azione_id = ap.id)
 ORDER BY p.codice, ap.permission_codename;

-- 2) La concessione.
INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT pa.profilo_accesso_id, ap.id, true
  FROM config.azioni_processo ap
  JOIN config.profili_accesso_aree pa ON pa.area_id = ap.area_id
  JOIN config.profili_accesso p       ON p.id = pa.profilo_accesso_id AND p.attivo
 WHERE ap.permission_codename IN ('emetti_ddt', 'conferma_reso')
   AND ap.attivo
   AND script.fn_area_consente_azione(pa.livello, ap.livello_minimo_area)
ON CONFLICT (profilo_accesso_id, azione_id) DO NOTHING;
```

---

## 3. I giri

### Blocco A — una bolla che muove merce si emette

**A1 — il cambio di stato dal verbo (Lotto 3 R-1).** `DdtRepository.cambia_stato(ddt_id, codice)` →
`SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %s)`, che ritorna i movimenti scritti; via
`update_stato` (l'`UPDATE` diretto) e il suo test. `ddt_service.cambia_stato` ed `emetti` passano dal
verbo; la risposta porta anche i movimenti. La validazione dello stato richiesto resta nel service (un
400 all'API, invece del codice tecnico del verbo). Test riscritti: il service chiama il verbo col
codice. I due test DB che portano una bolla a `EMESSO` con l'`UPDATE` diretto
(`test_resi_create_db`, `test_date_consegna_righe_db`) **restano**: le loro bolle non muovono merce per
costruzione (articolo `fn_pgtap_crea_articolo(…, false)`, non gestito), che e' il caso in cui la porta
del registro non si chiude (D-L3-e, censimento §5-bis del brief); il BB `dbops.fn_pgtap_porta_a_stato`
non copre le bolle. Commenti superati di DDT nello stesso giro.

**A2 — il magazzino sulla testata (Lotto 3 R-2a, 3-bis R-1a).**

* BE: `magazzino_id` (+ `magazzino_arrivo_id` per la bolla) letti nel detail con codice e descrizione,
  scritti in creazione e aggiornamento (whitelist di service e repository). Il default lo mette il DB
  (`trgfn_ddt_default_magazzino`: il predefinito dell'emittente; sul reso, quello della bolla). Le
  regole (stesso emittente, arrivo solo per `TRASFERIMENTO`, arrivo ≠ partenza, immutabili fuori
  bozza) sono dei guard DB: il BE non le ricopia.
* Lookup dei magazzini **filtrato sull'emittente del documento** (decisione di Tid): un magazzino di
  un altro emittente non si propone, invece di farlo rifiutare al salvataggio.
* FE: il campo magazzino sulla testata di bolla e reso — seconda occorrenza dello stesso campo, quindi
  un BB in `src/core/` registrato nel catalogo; arrivo solo con causale `TRASFERIMENTO`; bloccato dalla
  capability come gli altri campi della testata (`CAMPI_FORM_TESTATA_*`).
* 3-bis R-5: i commenti superati di `resi_service`.

### Blocco B — lotti, seriali, ubicazioni

**B1 — i prelievi della bolla (Lotto 3 R-2b).** Endpoint sotto la riga (lista, crea, modifica,
cancella) su `vendite.ddt_righe_prelievi`, piu' la lettura di «quanto va prelevato, quanto e' prelevato,
se e' automatico» da `vendite.fn_ddt_merce_da_movimentare`. Scritture solo in bozza, salvo
`ubicazione_arrivo_id` fino al `CONSEGNATO`: lo decide il guard DB. FE: griglia sotto la riga, coi
lookup di ubicazioni, lotti e seriali gia' usati dai documenti interni del magazzino.
✅ *Fatto cosi'* (2026-10-13): `GET …/ddt/<id>/prelievi/` (la testata — `muove_merce`, i due magazzini con
`usa_ubicazioni` — e le voci con i loro prelievi), `POST …/righe/<riga>/prelievi/`, `PATCH`/`DELETE
…/prelievi/<id>/`; i tre vincoli della tabella tradotti dal service (posizione ripetuta, quantita'). La
griglia e' una **sezione del drawer** sotto le righe (`DdtPrelieviSection` + `DdtPrelievoVoce`), raggruppata
per riga e componente del kit, e non dentro il form della riga: il motivo «prelievi incompleti» e' della
bolla intera, e l'ubicazione di arrivo si completa dopo l'emissione senza riaprire la riga.

**B2 — i rientri del reso (3-bis R-1b, R-1c).** Stessa forma per i rientri (il prelievo d'origine si
sceglie, lotto e seriale si mostrano). R-1c: brief al team DB — `fn_available_actions_reso` deve passare
`reasons` con i `valori`, come `fn_available_actions_ddt`.
✅ *Fatto cosi'* (2026-10-13): `GET …/resi/<id>/rientri/` (testata — `muove_merce`, magazzino con
`usa_ubicazioni` — e voci coi **prelievi d'origine** fra cui scegliere e i loro rientri), `POST
…/righe/<riga>/rientri/`, `PATCH`/`DELETE …/rientri/<id>/`; vincoli tradotti. Sezione «Rientri» nel drawer
del reso (`ResoRientriSection` + `ResoRientroVoce`); con un solo prelievo d'origine la scelta e' gia' fatta.
Lo stile del blocco voce e' una classe sola, `app-voce-merce` in `main.css`, per prelievi e rientri.
R-1c: [brief-db-reso-motivi-conferma-con-valori](../work-done/brief-db-reso-motivi-conferma-con-valori.md) (chiuso il 2026-10-14).

### Blocco C — il resto

**C1 — i blocchi (Lotto 3 R-5).** Due azioni sulla scheda disponibilità (apri, libera) sui verbi
`magazzino.fn_apri_blocco` / `fn_libera_blocco`; il permesso e' `blocca_merce`, applicato dal verbo.
✅ *Fatto cosi'* (2026-10-13): `POST …/magazzino/disponibilita/blocchi/` (apre) e `…/blocchi/<id>/libera/`,
`post_permission = blocca_merce` e Idempotency-Key; il CHECK `per_chi` tradotto col campo `nota` (prima
sarebbe uscito il testo crudo del vincolo). FE: azione di riga «Blocca merce» sulla disponibilita' per
magazzino (`BloccoApriDialog`), «Libera» nel popover dei blocchi sui soli blocchi manuali
(`BloccoLiberaDialog`); icona nuova `MANAGE_ICONS.BLOCCA_MERCE`.

**C2 — offerta e residui.**

* Offerta: il cliente si cambia in bozza, come nel preventivo (il DB lo ammette fino all'emissione);
  la utility segue il cliente e non si sceglie a parte (FK composta `fk_offerte_commerciali_ba_coppia`;
  oggi la tendina resta aperta col cliente fermo, e ogni cambio e' rifiutato).
* Offerta: `aggiorna_offerta` non riscrive la scheda di fornitura che il DB ha appena rifatto per il
  cambio di coppia (R-BE-6 di brief-db-indirizzi-documento-seguono-il-cliente).
* Offerta: eccezioni e componenti fuori bozza rispondono `E_VENDITE_VALIDATION`; gli altri documenti
  usano il BB `richiedi_righe_in_bozza` col codice del DB (`E_RIGA_DOC_NON_BOZZA`).
* Commenti che dicono ancora «testata solo in bozza, lo controlla il backend» (ordini, offerte,
  contratti, `ddtApi.js`, `ContrattoDrawer`), nei file non gia' toccati dai giri sopra.

✅ *Fatto cosi'* (2026-10-13): nel drawer dell'offerta il cliente si sceglie anche in modifica (spento
fuori bozza dalla capability), la utility col cliente scelto e' la sua e si spegne (`CAMPI_FORM_TESTATA_OFFERTA`:
`billing_account_id` al posto di `utility_id`); con un cambio di cliente il form non manda la scheda e il
backend la scarta comunque (`aggiorna_offerta` confronta la coppia attuale, `OfferteRepository.get_coppia`),
e il dettaglio riletto porta la scheda rifatta dal DB (R-BE-6 e R-FE-4 dell'offerta, brief
indirizzi-documento-seguono-il-cliente). Eccezioni e componenti: tolti i cinque pre-check di stato, il
rifiuto arriva dal DB come `E_RIGA_DOC_NON_BOZZA`. Commenti superati corretti in ordini, offerte, contratti,
`ddtApi.js`, `ContrattoDrawer`. ⚠️ Gli endpoint `…/contratti/<id>/utility/` restano (Tid, 2026-10-12): li
usera' R-FE-3 dello stesso brief.

---

## 4. Collaudo

Il copione sta in [collaudo-in-app-magazzino-bolla-e-reso](collaudo-in-app-magazzino-bolla-e-reso.md)
(2026-10-14): l'elenco breve che era qui, per blocchi A, B, C, e' diventato i §1 … §8 di quel documento,
coi dati di partenza (§0) e i casi del modello che l'elenco non aveva (entrata del trasferimento al
consegnato, storni, ri-consegna, causali che non muovono). Si spunta li', non qui.

## 5. I residui dei due brief DB chiusi

Raccolti qui all'archiviazione dei brief del
[Lotto 3](../work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md) e del
[3-bis](../work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md) (2026-10-14): il loro lato DB e'
applicato e verde, le richieste a BE/FE (§6 di entrambi) sono i giri del §3. Restava questo.

| Residuo | Da dove | Chi | Stato |
| --- | --- | --- | --- |
| Motivi della «Conferma» del reso senza i numeri (3-bis R-1c) | 3-bis §6; giro B2 | team DB | ✅ chiuso il 2026-10-14: [brief-db-reso-motivi-conferma-con-valori](../work-done/brief-db-reso-motivi-conferma-con-valori.md); a video al §5.3/§5.7 del collaudo |
| CI da zero (`ci_apply` + suite) che scrive la sua baseline | Lotto 3 e 3-bis, testata | Tid | ⏳ |
| La corsa col runner come app di `magazzino/test-reso-carico-kit-seriali-v1` (14/14 sullo scratch il 29-09) | 3-bis, testata | Tid | ⏳ da confermare: se la suite completa e' girata dopo il 29-09, e' gia' fatta |
| La vista di **lettura** della merce in viaggio (`transfer_uid` con la sola uscita) | Lotto 3, P-13.2 | team DB | ⏸️ nasce col suo lettore: non e' un presidio, la merce in viaggio e' normale. Fino ad allora a video non si vede (collaudo §9) |

Non sono residui, e restano dove sono: la merce presso terzi (D-L3-g), gli eventi asset (D-L2-l), la
ricezione acquisti e il reso a fornitore (Lotto 4), le colonne impegnata / in arrivo (satellite D-17),
i prelievi proposti alla ri-consegna e l'RMA (3-bis §7). Le scritture delle anagrafiche e dei
documenti interni di magazzino dal verbo sono un brief a se':
[brief-db-magazzino-tutte-le-scritture-dal-verbo](brief-db-magazzino-tutte-le-scritture-dal-verbo.md).

## 6. Registro

| Data | Che cosa |
| --- | --- |
| 2026-10-12 | Prima stesura, dalla rilettura dei due brief e del codice BE/FE; decisioni di Tid nel blocco in cima |
| 2026-10-12 | ✅ **A1**: `DdtRepository.cambia_stato` → `vendite.fn_cambia_stato_ddt` (via `update_stato`); la risposta porta `movimenti_scritti`; test DB nuovo `test_ddt_cambia_stato_db` (emissione con merce, senza merce, rifiuto col codice del DB). Commenti superati di DDT corretti |
| 2026-10-13 | ✅ **BB `SezioneMerceDocumento`** (regola del 2, ok Tid): lo scheletro comune delle sezioni Prelievi e Rientri (lettura, visibilita' se muove merce, avviso senza magazzino, voci nello slot) in `vendite/_shared/merce/`; `DdtPrelieviSection` e `ResoRientriSection` restano involucri con lettura, testi e voce. Catalogo FE; spec del BB; vitest 858, build, guard |
| 2026-10-13 | 🔍 **Revisione critica** del codice del piano (su richiesta di Tid). Corretti: voce di prelievo/rientro OLTRE la quantita' letta come «da completare» (e con l'aggiunta ancora aperta) → tre stati, tag «Oltre la riga»; scaffale di arrivo in sola lettura mostrato come tendina vuota → si legge accanto alla posizione; quantita' a video grezze → BB `formatQuantita`/`QTA_MAX_DECIMALI` (regola del 2: ritirata la copia in `FatturaDrawer`); voce del magazzino corrente ricostruita in due form → la compone `MagazzinoDocumentoSelect` (`record` + `campo`); doppia lettura delle sezioni prelievi/rientri alla prima apertura → il drawer rilegge solo una sezione gia' montata. Vitest 854, build, guard |
| 2026-10-13 | ✅ **C2**: offerta (cliente in bozza, utility che segue il cliente, scheda non riscritta al cambio di cliente, rifiuto delle eccezioni dal DB), commenti superati. Prove: test del service (cambio di cliente non riscrive la scheda; stesso cliente come testo la applica; eccezione su emessa = `E_RIGA_DOC_NON_BOZZA`), presidio `campiFormTestata`; Django 4065, vitest 852, build, mypy |
| 2026-10-13 | ✅ **C1**: endpoint di apertura e liberazione dei blocchi, CHECK `per_chi` tradotto; FE «Blocca merce» e «Libera» (catalogo FE). Prove: test DB `magazzino/tests/db/test_blocchi_db` (apri, leggi, libera; seconda liberazione col codice del DB; blocco senza per chi = errore col campo), spec `BloccoApriDialog`; Django, vitest 852, build, mypy |
| 2026-10-13 | ✅ **B2**: endpoint dei rientri (situazione del reso coi prelievi d'origine + CRUD sotto la riga), vincoli tradotti; sezione «Rientri» nel drawer del reso; classe CSS comune `app-voce-merce`. Brief DB R-1c. Prove: test DB (bolla a lotti emessa e consegnata → reso → rientro dal prelievo scelto → conferma: il lotto risale), test del service, spec FE `ResoRientroVoce`; Django 3991, vitest 849, build, mypy |
| 2026-10-13 | ✅ **B1**: endpoint dei prelievi (situazione della bolla + CRUD sotto la riga), vincoli tradotti; sezione «Prelievi» nel drawer della bolla. Prove: test DB (prelievo dal lotto e scarico di quel lotto; rifiuti con il loro codice), test del service (raggruppamento per voce del kit, coercizione, 404), spec FE `DdtPrelievoVoce`; Django 3988, vitest 845, build, mypy |
| 2026-10-12 | ✅ **A2**: magazzino di bolla (partenza, arrivo) e reso (rientro) letti nel dettaglio con le etichette e scritti in creazione e modifica; lookup specializzati `magazzino.magazzini` (`emittente_fiscale_id`) e `config.causali_trasporto` (`causale_magazzino`); BB FE `MagazzinoDocumentoSelect` (regola del 2, catalogo FE), arco `vendite -> magazzino` nel guard dei confini; il form del reso spegne per campo. 3-bis R-5: commenti di `resi_service` corretti. Prove: Django 3985 verdi, DB e2e verdi, vitest 840, guard, build, mypy a cricchetto pulito |
| 2026-10-14 | 📋 **Collaudo scritto e brief DB chiusi** (su richiesta di Tid). Il §4 diventa il copione [collaudo-in-app-magazzino-bolla-e-reso](collaudo-in-app-magazzino-bolla-e-reso.md); i brief DB del Lotto 3 e del 3-bis vanno in `work-done/`, coi residui raccolti al §5. Il brief tutte-le-scritture-dal-verbo resta aperto: e' un'altra materia, con cinque decisioni di Tid |
