# Brief DB — Revisione dello schema `catalogo`: la documentazione, i difetti di codice, i doppioni

## ⏭️ Chi riparte — aggiornato al 2026-11-11 (giro 5 applicato, 5-A e 5-B, §17.7)

**Riparte: Tid**, col via al giro 5-bis della sessione DB (la segnalazione 3 del giro BE, §15.10-bis.3) e il commit del
giro 5. Il giro 5 (`20261112-01` … `-24`) è applicato su dbdev e scratch, con i pgTAP come app verdi (§17.7); con lui si
chiude D-C di `brief-db-articoli-obsoleto-dal`. I giri G1-G2 (`20261111-69` … `-73`,
§15.11.1), Q34 (`-74` … `-76`, §15.11.2) e 4 (`-77` … `-80`, §16) sono applicati su dbdev e scratch, con i pgTAP come
app verdi, e committati con il giro BE del giro 2-bis (`651160401e`, `ea4b8da3e8`). Restano da guardare le scelte dentro i giri 4, 2-bis, 3, 2 e 1 (§16.2, §15.7, §14.2, §14.6,
§13.3, §10.3). In parallelo il **team BE**: BE21-BE25 fatte (§15.10-bis); restano BE21-a … f (§15.11.1, §15.11.2) e
BE26-BE28 (§16.4). Alla **sessione DB** una segnalazione del giro BE, il codice nel batch delle commesse (§15.10-bis.3,
punto 3); i punti 1 e 2 sono diventati G1 e G2.
## ⏭️ Chi riparte — aggiornato al 2026-11-11 (giro BE dei giri G1-G2, Q34 e 4 fatto, da committare, §16.5)

**Riparte: Tid**, col via al giro 5 (§7). I giri G1-G2 (`20261111-69` … `-73`, §15.11.1), Q34 (`-74` … `-76`,
§15.11.2) e 4 (`-77` … `-80`, §16) sono applicati su dbdev e scratch, con i pgTAP come app verdi. Da committare: Q34 e 4,
e il giro BE del giro 2-bis (§15.10-bis, su `dev/backend-tid`). Restano da guardare le scelte dentro i giri 4, 2-bis, 3, 2 e 1 (§16.2, §15.7, §14.2, §14.6,
§13.3, §10.3). Il **team BE** ha chiuso le sue voci: BE21-BE25 (§15.10-bis, committate) e BE21-a … f, BE26-BE28 (§16.5,
2026-11-11, **da committare** su `dev/backend-tid`). Alla **sessione DB** la segnalazione del batch delle commesse
(§15.10-bis.3, punto 3), le due nuove di §16.5.3 e la **Q35** (§16.6, un kit non si spegne più); a **Tid** una scelta di §16.5.3 e la Q35.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Censimento in sola lettura dei 37 oggetti: doc, codice, metadati, doppioni, pgTAP | §1-§5 | — |
| 2 | ✅ Tid | Le decisioni Q1-Q14, tutte come da proposta (2026-11-08) | §6 | 1 |
| 3 | ✅ Tid | Il via al giro 0 (2026-11-08) | §7 | 1 |
| 4 | ✅ sessione DB | Giro 0: le 35 pagine `manual/` allo standard, il blocco comune delle note, la doc fuori schema | §9 | 3 |
| 4-bis | ✅ sessione DB, su richiesta di Tid | Commit del giro 0 (2026-11-08) | §9.5 | 4 |
| 5 | ✅ Tid | Via al giro 1, dal `20261110-62` (2026-11-09) | §10 | 2 |
| 5-bis | ✅ sessione DB | Giro 1 (la distinta): `20261110-62` … `-71`, due codici, pgTAP; provato sullo scratch | §10 | 5 |
| 5-ter | ✅ Tid | Apply del giro 1 su dbdev e scratch; pgTAP come app verdi (2026-11-09) | §10.6 | 5-bis |
| 5-quater | ✅ Tid | Commit del giro 1 (`eef662024d`, 2026-11-09) | §10.6 | 5-ter |
| 5-quinquies | ✅ sessione DB | Censimento del giro 1-bis in sola lettura: i lettori della distinta, il piano | §11 | 5-quater |
| 5-sexies | ✅ Tid | Q15-Q18 come da proposta; via al giro 1-bis dal `-85` (2026-11-09) | §11.4 | 5-quinquies |
| 5-septies | ✅ sessione DB | Giro 1-bis: nove changeSet, CSV dei codici, pgTAP, doc; provato sullo scratch | §11.7, §11.8 | 5-sexies |
| 5-octies | ✅ Tid | Apply del giro 1-bis su dbdev e scratch, pgTAP come app verdi (2026-11-09) | §11.9 | 5-septies |
| 5-nonies | ✅ sessione DB, su richiesta di Tid | Commit del giro 1-bis (2026-11-09) | §11.9 | 5-octies |
| 5-decies | ✅ Tid | Via al giro 2, dal `20261111-01` (2026-11-09) | §13 | 5-nonies |
| 5-undecies | ✅ sessione DB | Giro 2 (le unità): tredici changeSet, sei codici, pgTAP, doc; provato sullo scratch | §13 | 5-decies |
| 5-duodecies | ✅ Tid | La riga di prova corretta; apply del giro 2 su dbdev e scratch, pgTAP come app verdi (2026-11-09) | §13.6 | 5-undecies |
| 5-terdecies | ✅ sessione DB, su richiesta di Tid | Commit del giro 2 (2026-11-09) | §13.6 | 5-duodecies |
| 5-quaterdecies | ✅ Tid | Via al giro 3, dal `20261111-25` (2026-11-09) | §14 | 5-terdecies |
| 5-quindecies | ✅ sessione DB | Giro 3: tredici changeSet, quattro codici, tre pgTAP nuovi, doc; provato sullo scratch | §14 | 5-quaterdecies |
| 5-sexdecies | ✅ Tid | Apply del giro 3 su dbdev e scratch, pgTAP come app verdi (2026-11-10) | §14.9 | 5-quindecies |
| 5-septdecies | ✅ sessione DB, su richiesta di Tid | Commit del giro 3 (2026-11-10) | §14.9 | 5-sexdecies |
| 5-octodecies | ✅ Tid | Numeri del giro 2-bis dal `20261111-47` (l'altra sessione finisce al `-46`); Q26 (2026-11-10) | §15 | 5-septdecies |
| 5-octodecies-bis | **Tid** ⏭️ | Q27 ✅ (rifiuto, 2026-11-10); il via ai giri 4-5; le scelte di §14.2, §14.6, §13.3, §10.3 da guardare | §7, §15 | 5-octodecies |
| 5-novodecies | ✅ sessione DB | Giro 2-bis: D24-D27 (Q23-Q31), `20261111-47` … `-65`, sei codici, quattro eccezioni ATTIVO, tre pgTAP nuovi, doc; provato sullo scratch | §15.6-§15.9 | 5-octodecies-bis |
| 5-vicies | ✅ Tid | Apply del giro 2-bis su dbdev e scratch, pgTAP come app verdi (2026-11-11) | §15.10 | 5-novodecies |
| 5-unvicies | ✅ sessione DB, su richiesta di Tid | Commit del giro 2-bis (2026-11-11) | §15.10 | 5-vicies |
| 5-vicies-bis | ✅ sessione DB | Verifica del lavoro BE dopo il giro 2-bis: il giro BE del giro 3 non lascia niente al DB; il giro 2-bis lascia G1 e G2 | §15.11 | 5-unvicies |
| 5-vicies-ter | ✅ Tid | Q32 e Q33; il campo del lock, opzione (a); via e numeri dal `-69` (2026-11-11) | §15.11 | 5-vicies-bis |
| 5-vicies-quater | ✅ sessione DB | Giro G1-G2: `20261111-69` … `-73`, quattro CSV, un pgTAP nuovo e tre riallineati, doc; provato sullo scratch | §15.11.1 | 5-vicies-ter |
| 5-vicies-quinquies | **Tid** ✅ | Apply del giro G1-G2 su dbdev e scratch, **poi subito la convergenza del lock**; pgTAP come app; commit — fatto l'11-11: migrate e convergenza applicati, pgTAP verdi | §15.11.1 | 5-vicies-quater |
| 5-vicies-sexies | ✅ sessione DB | Giro Q34 (la riga base sempre attiva): `-74` … `-76`, il messaggio, i pgTAP, le pagine `manual/`; provato sullo scratch | §15.11.2 | 5-vicies-quinquies |
| 5-vicies-septies | ✅ Tid | Apply del giro Q34 su dbdev e scratch, pgTAP come app verdi (2026-11-11) | §15.11.2 | 5-vicies-sexies |
| 6 | ✅ sessione DB | Giro 4, le note (D16, R6, Q12): `20261111-77` … `-80`, due righe di eccezione ATTIVO, un pgTAP nuovo, pagine `manual/`; provato sullo scratch (via e numeri di Tid, dal `-77`) | §16 | 5-vicies-septies |
| 6-bis | ✅ Tid | Apply del giro 4 su dbdev e scratch, pgTAP come app verdi (2026-11-11); commit su richiesta, con il giro Q34 | §16.4 | 6 |
| 6-ter | ✅ sessione DB | Giro 5: il censimento sul vivo, l'elenco chiuso e le proposte (via di Tid, 2026-11-11) | §17 | 6-bis |
| 6-quater | ✅ Tid | Le quattro scelte di §17.3 (2026-11-11); numeri `20261112-01` … `-30` (il `20261111-81` e oltre sono dell'altra sessione) | §17.3 | 6-ter |
| 6-quinquies | ✅ sessione DB | Giro 5-B, i `COALESCE`: `20261112-01` … `-14`; provato sullo scratch | §17.5 | 6-quater |
| 6-sexies | ✅ sessione DB | Giro 5-A: `20261112-15` … `-24` (il `-22` … `-24` riportano tre `%TYPE` che la 5-B aveva ricopiato sciolti), la nota di un lock nel CSV, un pgTAP nuovo (il presidio dei COMMENT di catalogo) e due riscritti, doc; provato sullo scratch | §17.6 | 6-quater |
| 6-septies | ✅ Tid | Apply del giro 5 (`20261112-01` … `-24`) su dbdev e scratch, pgTAP come app verdi (2026-11-11); commit su richiesta | §17.7 | 6-sexies |
| 6-septies-bis | ✅ sessione DB | Verifica sul vivo dopo l'apply: i 26 oggetti commentati dal cantiere `obsoleto_dal` (D-C, §3.3.1) puliti su dbdev e scratch; D-C chiuso anche nell'altro brief (2026-11-11) | §17.7 | 6-septies |
| 6-octies | **Tid** ⏭️, poi sessione DB | Giro 5-bis: il codice nel risultato di `vendite.fn_batch_upsert_commessa_attivita` (segnalazione 3); aspetta il via | §15.10-bis.3, §17.3 | 6-septies |
| 7 | ✅ team BE | BE8-BE12 (giro 1) e BE13-BE15 (giro 1-bis), fatte il 2026-11-09 (`9f540bea72`, PR #77) | §11.10 | — |
| 7-bis | ✅ team BE (committato, `ff93395d5e`, PR #84) | La doc API di BE9 e BE11 (`api_catalogo.md`); BE19 e BE20 del giro 3 e BE4 (campo di `E_PARAMETRO_INVALIDO`). BE1-BE4 e BE16-BE18 del giro 2 erano già fatti (PR #81) | §13.5, §14.10 | — |
| 7-ter-bis | — | Assorbita in 7-septies, con la rinumerazione di §15 (BE19-BE21 → BE21-BE23) | §15 | — |
| 7-ter | ✅ Tid | Il legame con prezzi bundle: (b) con conferma dell'operatore, tutti e due i diritti, avviso sul prezzo del kit (Q19-Q22, 2026-11-09) | §11.10.1 | — |
| 7-quater | ✅ Tid | La chiusura del legame coi prezzi va nel giro 3 (2026-11-09) | §14 | 7-ter |
| 7-quinquies | ✅ team BE | Giro BE del giro 2: BE1-BE4, BE16-BE18 (BE4 resta aperta per D19); committato (`2af6d986f5`, PR #81) | §13.7 | — |
| 7-sexies | ✅ Tid | Le tre domande di §13.7.3: Q23 bloccato, Q24 per tutto il periodo, Q25 in questo brief (2026-11-10) | §6, §15 | 7-quinquies |
| 7-septies | ✅ team BE (2026-11-11, da committare su `dev/backend-tid`) | BE21-BE25 del giro 2-bis: la parte di BE21 che non dipende da G1 e G2 (codice, policy, test del rifiuto, campi fermi dichiarati come gap) | §15.10-bis, §15.4, §15.9 | 5-vicies |
| 7-novies | **team BE** ⏭️ | BE26-BE28 del giro 4 (le note di catalogo: testo e àncora rifiutati dal DB, la nota che non tiene acceso il bersaglio, `user_*` text) | §16.4 | 6-bis |
| 7-octies | **team BE** ⏭️ | Il resto di BE21, a giro G1-G2 applicato: BE21-a … BE21-d (il form da `vw_non_editable_fields`, `_NON_EDITABLE_DB_GAPS` ritirato, le azioni di riga dalle due viste, la lista delle conversioni sulla vista nuova), e BE21-e … f del giro Q34 (il drawer della conversione, la riga base che non si spegne) | §15.11.1, §15.11.2 | 5-vicies-septies |
| 7-decies | sessione DB | Le segnalazioni del giro BE: 1 e 2 ✅ (sono G1 e G2, §15.11.1); la 3 è il giro 5-bis (passo 6-octies) | §15.10-bis.3 | 7-septies |
| 7-undecies | **team BE** ⏭️ | BE29 del giro 5: la voce di `uq_articoli_componenti_prodotto_componente_from` in `catalogo_service.py` si toglie | §17.3 | 6-septies |
| 8 | sessione DB | Pagine `manual/` riallineate a ogni difetto chiuso, insieme al COMMENT; brief in `work-done/` | §7, §8 | 6 |

**Decisioni aperte di Tid:** le scelte dentro i giri 2-bis (§15.7), 3 (§14.2, §14.6), 2
(§13.3) e 1 (§10.3), da guardare; il via al giro 5-bis. Le quattro del giro 5 (§17.3) sono prese. **Committati** i giri
G1-G2, Q34 e 4, e il giro BE del giro 2-bis (2026-11-11). **Da committare:** il giro 5, applicato (§17.7).
| 7-novies | ✅ team BE (2026-11-11, da committare su `dev/backend-tid`) | BE26-BE28 del giro 4: le note di catalogo passano dal BB delle note (opzione A di Tid), la copia di `catalogo_service` è ritirata | §16.5 | 6-bis |
| 7-octies | ✅ team BE (2026-11-11, da committare su `dev/backend-tid`) | BE21-a … f: `_NON_EDITABLE_DB_GAPS` ritirato, capability delle due viste nei form, conversioni sulla vista nuova, ripiego della riga base | §16.5 | 5-vicies-septies |
| 7-undecies | sessione DB ⏭️ | Le due segnalazioni del giro BE dei giri G1-G2, Q34 e 4: il **ritiro** di `E_CATALOGO_NOTA_NOT_FOUND` (deciso da Tid, 2026-11-11; poi il BE rigenera la policy); la proiezione delle note di vendita senza vista | §16.5.3 | 7-novies |
| 7-terdecies | ✅ team BE (2026-11-11, da committare su `dev/backend-tid`) | Verifica critica del giro BE: un 500 sul filtro di riga, i presidi sulla copia delle note, il campo `note` del dettaglio ritirato, la regola del 2 nei form delle unità | §16.5.4 | 7-novies |
| 7-duodecies | **Tid** ⏭️ | `seq` di una nota: il BB lo vuole ≥ 1, il CHECK del DB ammette 0 | §16.5.3 | 7-novies |
| 7-decies | sessione DB ⏭️ | Le segnalazioni del giro BE: 1 e 2 ✅ (sono G1 e G2, §15.11.1); resta la 3, il codice nel risultato del batch delle commesse | §15.10-bis.3 | 7-septies |
| 7-quaterdecies | sessione DB ⏭️ | **Q35**: un kit con la distinta non si spegne più (legame sempre attivo dopo il ritiro della PATCH, nessuna eccezione ATTIVO su `articoli_componenti`). Proposta (a) eccezione come Q31, previa verifica del lato componente; la scelta è di Tid. Presidio: i due smoke rossi `catalogo-phase3` e `preventivi-componenti` | §16.6 | — |
| 8 | sessione DB | Pagine `manual/` riallineate a ogni difetto chiuso, insieme al COMMENT; brief in `work-done/` | §7, §8 | 6 |

**Decisioni aperte di Tid:** le scelte dentro i giri 2-bis (§15.7), 3 (§14.2, §14.6), 2
(§13.3) e 1 (§10.3), da guardare; `seq` delle note (§16.5.3, punto 3); **Q35**, lo spegnimento di un kit (§16.6). **Da committare** il giro BE di §16.5. **Committato** il giro G1-G2 (2026-11-11), con questo brief. **Da committare**: i giri Q34 (§15.11.2) e 4 (§16), applicati. **Da committare** anche il giro BE del giro 2-bis (§15.10-bis), su `dev/backend-tid`.
⚠️ **Numerazione:** il giro 1 ha preso `20261110-62` … `-71`, il giro 1-bis `-85` … `-93`, il giro 3 `20261111-25` … `-37` (dati da Tid). Messaggi
d'errore: il giro 1-bis non ne aggiunge; ne riscrive due righe.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-08. **A chi:** Tid e team DB; §5 al team BE.
> **Origine:** richiesta di Tid del 2026-11-08: una revisione di `catalogo` sullo stile di
> [brief-db-revisione-dbops](../work-done/brief-db-revisione-dbops.md). Si parte dalla documentazione da riportare allo
> standard, poi si guarda che cosa è obsoleto, che cosa non è fatto come descritto (e quindi forse non
> funziona), che cosa si può cancellare e dove la regola del 2 trova doppioni.
> **Metodo:** quattro revisori in sola lettura (articoli; distinta; unità di misura e note; trasversale)
> sui corpi di `pg_get_functiondef`, su `pg_trigger`/`pg_constraint`/`obj_description` di dbdev e sulle
> schede auto-generate. Chi scrive il brief ha ricontrollato sul corpo D1, D2, D3, D4 e D7 (✔︎).
> **Brief vicini verificati:**
> * [brief-db-articoli-obsoleto-dal](brief-db-articoli-obsoleto-dal.md): il suo **D-C** riscrive i COMMENT di quel
>   cantiere (`obsoleto_dal`, `fn_articoli_ammessi`, `trgfn_articoli_componenti_guard_componente`,
>   `vw_articoli_dettaglio.e_obsoleto`). Si sovrappone a M3: chi lo fa lo decide Tid (Q11). ✅ Deciso: tutto qui, nel
>   giro 5, anche gli oggetti fuori `catalogo` (Tid, 2026-11-11; elenco chiuso in §3.3.1).
> * [brief-db-revisione-dbops](../work-done/brief-db-revisione-dbops.md): il suo **D28** (le `condition_expr` di
>   `lock_columns_conditional` ricopiano gli `EXISTS` del guard flags) tocca gli stessi predicati di D9. D28 resta
>   lì; il giro 1 di qui va fatto **dopo** o **con** D28, perché cambia la finestra del predicato che D28 estrae.
> * [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md): tocca `trgfn_articoli_guard_onere_natura`,
>   `vw_articoli_dettaglio` (`causale_onere_id`, `e_onere`) e `fn_articolo_righe_vive_non_ammesse`. Qui non si
>   rifà niente di quel cantiere: si toccano solo i metadati (M3) e l'etichetta dei flag (R5).
> * `analisi-db-magazzino-carico-e-scarico` (analisi, non brief): tocca `requires_lotto`, quindi Q4.
> * Nessun brief aperto tratta il fattore delle unità di misura (D2, D3, D12-D15) né l'immutabilità della
>   distinta (D1, D9).

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/<schema>/…`) o da
`pg_get_functiondef`, non dagli YAML. Prima di scrivere un changeSet si riverifica sulla scheda del giorno.

## 1. Il perimetro

Lo schema `catalogo`: 9 tabelle (`articoli`, `articoli_componenti`, `articoli_uom_operativa`, `unita_misura`,
`uom_tipi`, `unita_misura_conversioni`, `note` partizionata con `note_articoli` e `note_articoli_componenti`), 5
viste, 23 funzioni. Il database e la doc auto-generata coincidono: ogni oggetto ha la scheda e la pagina `manual/`.

Ci sono anche i difetti di altri schemi trovati leggendo i chiamanti. Il caso principale è
`script.trgfn_qta_from_operativa`, che è l'unico lettore operativo di `articoli_uom_operativa`.

Ogni difetto si regge sul modello. Dove compare un numero, è un fatto datato al 2026-11-08.

## 2. I difetti di codice

Forma compatta: **fatto** · **correzione** · **presidio**. Classi come nel brief `dbops`:

* **A**: contraddice un contratto deciso, oppure è sbagliato ogni volta che il ramo si percorre.
* **B**: un caso che il modello ammette (un NULL, una data futura, una riga chiusa) e che non è gestito.
* **C**: pulizia e metadati.

| Classe | Difetti |
| --- | --- |
| **A** | D1, D2, D3, D4, D5, D6, D7, D8 |
| **B** | D9, D10, D11, D12, D13, D14, D15, D16, D17, D18, D19, D20, D22 |
| **C** | D21, §2.4 (rami irraggiungibili), §3 (metadati), §2.6 (pgTAP deboli) |

### 2.1 Classe A

#### D1 ✔︎ — La distinta non è immutabile su `prodotto_id`

* **Fatto.** `trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt` scatta `BEFORE DELETE OR UPDATE OF
  coeff_qta, componente_id, obbligatorio, esposizione_in_fattura, valido_dal, valido_al`. `prodotto_id` non è
  né nella lista né nel confronto del corpo. Il modello lo dichiara immutabile
  (`dev/manual/modello-componenti-bom.md:38`). Una riga di distinta passa quindi sotto un altro padre, e le righe
  `*_righe_componenti` che la puntano (cinque FK in vendite, più la temporale del listino) restano legate a un
  altro kit, in silenzio. Gli unici a scattare su `UPDATE OF prodotto_id` sono i guard di regola (composito,
  solo componente, componente), e non giudicano l'immutabilità. `valido_al` sta nella lista, ma il corpo non lo
  confronta: fa scattare il trigger per niente.
* **Correzione.** `prodotto_id` entra nella lista e nel confronto `IS DISTINCT FROM`; `valido_al` esce dalla lista,
  se Q1 non decide altrimenti.
* **Presidio.** In `catalogo/test-articoli-componenti-immutabilita.sql`: `SET prodotto_id = <altro composito>` →
  `E_BOM_MODIFICA_VIETATA`.

#### D2 ✔︎ — Il fattore di conversione ha due sedi, e quella che conta usa 1 quando non sa

* **Fatto.** `script.trgfn_qta_from_operativa`, montato sulle righe di vendita, cerca solo la mappatura
  dell'articolo in `articoli_uom_operativa`; poi fa `v_factor_map := COALESCE(v_factor_map, 1)`. Prendiamo una
  riga in un'unità operativa diversa dalla base, senza mappatura (o con la mappatura spenta, o fuori validità):
  la quantità base diventa `qta_operativa × 1`, senza errore. Le conversioni globali di
  `unita_misura_conversioni` non le legge mai. `catalogo.fn_get_uom_factor` ha la regola completa (mappatura,
  poi conversione diretta, poi inversa, altrimenti NULL), ma nel DB non la chiama nessuno: la usano solo due
  wrapper BE che a loro volta non hanno chiamanti. Sono due copie della stessa regola, già in disaccordo
  (regola del 2), e la copia che conta è quella sbagliata. Contraddice `manual/unita_misura_conversioni.md`:
  «fallback quando non esiste conversione articolo-specifica».
* **Correzione.** Il trigger prende il fattore da `catalogo.fn_get_uom_factor`. Con NULL solleva un codice
  registrato (`E_UOM_MISSING` esiste già; Q7). `fn_get_uom_base` resta il solo lettore di `articoli.uom_id`.
* **Presidio.** pgTAP su `vendite.ordini_righe`: articolo con base G, riga in KG senza mappatura. Con la
  conversione globale KG→G = 1000, la quantità vale 1000 × qta; senza conversione, la riga è rifiutata.

#### D3 ✔︎ — Le regole di input dell'unità operativa sono promesse senza esecutore

* **Fatto.** `trgfn_qta_from_operativa` legge `max_decimals` in `v_max_dec` e poi non lo usa. `rounding_mode` non
  lo legge nessuna funzione: il calcolo arrotonda sempre con `ROUND(…, 6)`. Il COMMENT di `require_lot` dice «se
  TRUE richiede lotto nei documenti», ma la colonna non ha lettori; la regola vera del lotto è
  `articoli.requires_lotto`. Sono due flag con lo stesso significato, e uno dei due è inerte. COMMENT e
  `manual/articoli_uom_operativa.md:24,30` dicono che le regole vengono applicate.
* **Correzione.** Q4: applicarle, con un codice per i decimali, oppure ritirare le colonne (e `require_lot` in
  ogni caso, a favore di `requires_lotto`).
* **Presidio.** Con `max_decimals = 0` e `qta_operativa = 2.5` la riga è rifiutata (se applicate); altrimenti
  il presidio è che le colonne non ci sono più.

#### D4 ✔︎ — Con un legame attivo, l'IVA di un kit e dei suoi componenti non si cambia più

* **Fatto.** `trgfn_articoli_guard_iva_bom_attiva` è `BEFORE UPDATE OF iva_id`, riga per riga e non
  differibile. Confronta `NEW.iva_id` con l'IVA **attuale** dell'articolo collegato. Se si aggiorna prima il
  padre, i figli hanno ancora la vecchia; se prima un figlio, il padre ha ancora la vecchia. Nemmeno un UPDATE
  unico passa: la prima riga elaborata vede le altre col valore vecchio. Il filtro è il solo `ac.attivo = TRUE`,
  senza `validita`, quindi contano anche i legami chiusi. Col modello «chiudi e inserisci» quei legami restano
  attivi, e `trgfn_prevent_deactivate_if_children` impedisce di spegnerli appena una riga di documento li cita.
  Contraddice `manual/articoli.md` («`iva_id` libera, l'aliquota cambia per legge»), e la procedura della pagina
  del guard («prima i partner, poi l'articolo») non si può eseguire.
* **Correzione.** L'invariante si controlla a fine transazione (constraint trigger `DEFERRABLE INITIALLY
  DEFERRED`), oppure con un verbo che cambia l'IVA del kit intero (Q6). La finestra diventa «legami da oggi in
  poi», come il check 3 del guard flags (D9).
* **Presidio.** In una transazione si cambia l'IVA di un kit e di tutti i componenti: passa. Un legame chiuso
  ieri non blocca. Cambiare solo il padre: rifiutato al COMMIT.

#### D5 — `trgfn_articoli_guard_listino_se_composito`: il rimedio suggerito non funziona, e la porta lo contraddice

* **Fatto.** L'errore suggerisce di «disattivare le righe listino prima di rendere composito». Però
  `fn_articolo_usato` conta `vendite.listini_righe` in qualunque stato, quindi dopo la disattivazione scatta
  `trgfn_articoli_guard_struttura_se_usato` (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`). Fuori dalla porta
  amministratore il guard è assorbito dal guard «usato»: scatta prima solo per l'ordine alfabetico dei nomi.
  Dentro la porta (`fn_articolo_correggi_struttura`) blocca anche le righe di una versione `CHIUSA`, mentre
  `fn_articolo_righe_vive_non_ammesse` le esclude per contratto («un documento chiuso non blocca»). È una terza
  copia della regola (R4), già divergente.
* **Correzione.** Si ritira il guard (Q5): la regola vive lato riga (`fn_check_articolo_riga_su_contesto`) e,
  per la porta, in `righe_vive`.
* **Presidio.** Correzione a composito di un articolo con righe solo in una versione chiusa → passa. Oggi nessun
  pgTAP prova il lato articolo.

#### D6 — I due guard di tipologia sollevano un errore tecnico e registrano il trigger al posto della funzione

* **Fatto.** `trgfn_uom_conversioni_guard_tipo` e `trgfn_unita_misura_guard_tipo_update` sollevano `E_GENERICO`
  (classe TECNICO, messaggio `%s`) con una frase libera. Un errore di dato arriva quindi all'operatore come
  errore tecnico. Inoltre passano `TG_NAME` come nome della funzione, così in `error_log` c'è il trigger e i
  consumatori cercati dal nome della funzione non lo trovano.
* **Correzione.** Due codici registrati (per esempio `E_UOM_CONVERSIONE_TIPO_DIVERSO`, `E_UOM_TIPO_IN_USO`), il
  nome qualificato della funzione, `EXISTS` al posto di `COUNT(*)`.
* **Presidio.** `throws_ok` sui codici nuovi. `trgfn_unita_misura_guard_tipo_update` oggi non ha nessun test.

#### D7 ✔︎ — Un articolo creato non attivo non si salva

* **Fatto.** `trgfn_articoli_seed_uom_base` scrive la riga base sempre con `attivo = TRUE`. Il constraint
  trigger generato `…_articoli_require_attivo_ins_upd` di `articoli_uom_operativa` pretende un padre attivo. Il
  modello ammette `INSERT articoli (attivo = false)`, e l'insert fallisce al COMMIT con
  `E_ATTIVO_PADRE_NON_ATTIVO`. È verificato sui corpi, non eseguito: va provato prima di scrivere il giro.
* **Correzione.** `attivo := NEW.attivo`.
* **Presidio.** pgTAP con `SET CONSTRAINTS ALL IMMEDIATE`: l'articolo non attivo nasce, con la sua riga base
  spenta.

#### D8 — Cambiare unità su una riga lascia il fattore della vecchia

* **Fatto.** Su un UPDATE che cambia `uom_operativa_id` senza toccare `factor_to_base`, il trigger usa
  `COALESCE(NEW.factor_to_base, …)`. `NEW.factor_to_base` ha ancora il fattore della unità precedente (da
  CARTONE ×6 a PZ, il fattore resta 6). Nessun lock impedisce il cambio di unità. Verificato sul corpo; da
  vedere se il BE azzera il fattore (§5, BE3).
* **Correzione.** Se l'unità cambia e il fattore non è stato toccato, il fattore si ricalcola.
* **Presidio.** UPDATE che cambia solo l'unità: la quantità segue il fattore nuovo.

### 2.2 Classe B

#### D9 — «Distinta in vigore» ha più finestre, e i guard non ri-giudicano i ritorni in vigore

* **Fatto.** Le definizioni oggi sono quattro:
  * `fn_articolo_padre_di_distinta_in_vigore` e `…componente_di_distinta_in_vigore`: `attivo` e
    `validita @> fn_data_operativa()`;
  * `fn_articolo_primo_padre_da_oggi`: `validita && [oggi,∞)`;
  * il guard IVA: solo `attivo` (D4);
  * `script.fn_check_articolo_riga_su_contesto`: `COALESCE(ac.attivo, TRUE)`, senza validità.

  Ne nascono tre varchi:
  * **Padre con distinta solo futura.** Il check 1 di `trgfn_articoli_guard_flags_struttura_bom_attiva` guarda
    solo «in vigore oggi», quindi un padre con legami solo futuri passa `is_composito` (o `requires_serial`) a
    false. Il check 3, sul componente, include invece il futuro.
  * **Riattivazione o arrivo di `valido_dal`.** `guard_is_composito` e `guard_solo_componente` scattano solo su
    `INSERT OR UPDATE OF prodotto_id`, non su `attivo`/`valido_*`.
  * **Riapertura di un legame chiuso.** `guard_componente` scatta su `UPDATE OF componente_id, prodotto_id,
    attivo`, non su `valido_al`. Dopo che il componente è diventato composito o obsoleto, `SET valido_al = NULL`
    passa. Ne esce una distinta a due livelli, o con un componente obsoleto, o con un padre non composito.

  La distinta a un livello di `modello-componenti-bom.md` §9.2 regge solo finché questi varchi restano chiusi.
* **Correzione.** Una finestra sola, «da oggi in poi», per tutti i guard che proteggono la struttura (il BB di
  R2). I motivi sul padre vanno nella check `ARTICOLO` condivisa (R3), giudicata anche su `attivo`, `valido_dal`
  e `valido_al`. Con D28 del brief `dbops` (vedi testata).
* **Presidio.** Tre casi costruiti in `test-distinta-predicati-guard-e-form-v1`:
  * padre con sola distinta futura che smette di essere composito → rifiutato;
  * riattivazione di un legame con padre non composito → `E_ARTICOLO_NON_COMPOSITO`;
  * riapertura di un legame il cui componente è diventato composito → `E_BOM_COMPONENTE_COMPOSITO`.

#### D10 — `valido_al` si sposta in ogni direzione

* **Fatto.** Il trigger d'immutabilità ammette qualunque `valido_al ≥ valido_dal`: la chiusura retroattiva e la
  riapertura a NULL. La pagina del trigger dice «protegge la storia da correzioni retroattive», e il modello
  «garantisce ricostruzione storica». La capability della vista (`data_min_chiusura = valido_dal`) offre la
  chiusura nel passato.
* **Correzione.** Q1. Se la regola è «si chiude, non si riapre né si retrodata»: vietati `data → NULL` e
  `valido_al < fn_data_operativa()` sui legami già in vigore, con `data_min_chiusura` allineata.

#### D11 — Un articolo può essere composito e solo componente insieme

* **Fatto.** Nessun CHECK esclude `is_composito AND is_solo_componente`. Un articolo così è inerte: non fa da
  padre (guard solo componente) e non fa da componente (un livello). Il check 2 del guard flags protegge il lato
  componente, ma il lato padre, quello della regola di `guard_solo_componente`, non lo protegge nessun guard
  sull'articolo.
* **Correzione.** Q2: un CHECK `NOT (is_composito AND is_solo_componente)`. Con il CHECK, `guard_solo_componente`
  diventa superfluo e si ritira (R3).

#### D12 — La riga base di `articoli_uom_operativa` non è protetta

* **Fatto.** Nessun CHECK impone `NOT is_base OR factor_to_base = 1`; c'è solo l'indice unico parziale
  `uq_artuomop_one_base`. Nel BE la regola è parziale: `catalogo_service.py:844` controlla solo se il payload ha
  insieme `is_base` e il fattore. `uom_id`, `is_base` e `factor_to_base` sono fra le colonne scrivibili. Il
  DELETE della riga base lo vieta solo il FE (capability `puo_eliminarsi`). Così si ottiene un articolo senza
  base, con la base su un'unità diversa da `articoli.uom_id`, o con fattore diverso da 1, e quel fattore D2 lo
  usa nel calcolo.
* **Correzione.** Il CHECK, più un guard che sulla riga base vieta UPDATE di `uom_id`/`is_base`/`factor_to_base`
  e il DELETE, ma lascia passare il CASCADE dalla cancellazione dell'articolo.
* **Presidio.** `throws_ok` per i tre UPDATE e per il DELETE; `lives_ok` per la cancellazione dell'articolo.

#### D13 — `articoli_uom_operativa`: date di validità con un UNIQUE senza tempo

* **Fatto.** Ci sono `valido_dal`/`valido_al`/`validita`, ma anche `UNIQUE (articolo_id, uom_id)`. Il pattern
  «chiudi e inserisci» non si può applicare. La validità vuol dire solo «fuori dalla finestra non c'è
  mappatura», e lì si ricade in D2.
* **Correzione.** Q3: `UNIQUE … WITHOUT OVERLAPS` (come la distinta), oppure si ritira la validità.

#### D14 — Le due direzioni della stessa conversione possono contraddirsi

* **Fatto.** `uq_uom_conv_no_overlap` vale per la coppia orientata. A→B = 10 e B→A = 0,2 convivono attive, e
  `fn_get_uom_factor` prende la diretta senza dire niente.
* **Correzione.** Un'esclusione sulla coppia non orientata (`LEAST`/`GREATEST` più la validità): una
  conversione per coppia, l'inversa la calcola la funzione.
* **Presidio.** Con A→B in vigore, l'inserimento di B→A è rifiutato.

#### D15 — Due transazioni possono far nascere una conversione fra tipologie diverse (sospetto)

* **Fatto.** T1 cambia `tipo_uom_id` di un'unità e conta zero conversioni. T2 inserisce una conversione e il suo
  guard legge il tipo vecchio: la FK prende `KEY SHARE`, che è compatibile col `NO KEY UPDATE` di T1. Nessuna
  delle due aspetta l'altra.
* **Correzione.** Il guard delle conversioni legge le unità con `FOR SHARE`.
* **Presidio.** Prova a due sessioni.

#### D16 — Le note di catalogo non hanno la forma delle note degli altri schemi

* **Fatto.**
  * Manca `chk_note_testo_non_vuoto`, che vendite e acquisti hanno.
  * `anchor_tipo = 'RIGA'` è ammesso, con un `target_riga_id` senza FK né `trgfn_note_validate_generic`, mentre
    su un'anagrafica «riga» non ha significato.
  * `user_*` è `varchar(80)` invece di `text`, e manca `tx_id`.
  * La FK `target_tipo → config.tipi_entita` ammette codici senza partizione, e lì l'errore esce grezzo.
  * La partizione non ha `attivo`, quindi il `block_deact` generato impedisce di disattivare un articolo che ha
    una nota (verificare se è voluto).
* **Correzione.** Il CHECK sul testo; `anchor_tipo = 'DOCUMENTO' AND target_riga_id IS NULL` sulle partizioni di
  catalogo; Q12 per `tx_id`, `user_*` e il caso `block_deact`.
* **Presidio.** `throws_ok` per il testo vuoto e per l'àncora `RIGA`.

#### D17 — `unita_misura.conta_dal_calendario` non è legato alla tipologia TEMPO (sospetto)

* **Fatto.** Il modello ammette un'unità di massa che conta i giorni dal calendario.
* **Correzione.** Un guard sulla tipologia, o un CHECK attraverso il tipo.

#### D18 — `fn_articolo_usato` non guarda a quale colonna punta la FK

* **Fatto.** Filtra `confrelid` e `array_length(conkey) = 1`, poi confronta la colonna con l'`uuid`
  dell'articolo. Una FK verso `uq_articoli_codice`, che il modello ammette, fallisce con un errore di tipo, e con
  lei guard e form. Una FK composita viene saltata in silenzio, contro il «fail-closed» del COMMENT.
* **Correzione.** Si filtra `confkey` sulla colonna `id`. Una FK verso un'altra chiave si conta confrontando il
  valore di quella chiave, non si salta.
* **Presidio.** Tabella in `pg_temp` con una FK verso `articoli(codice)`: il predicato risponde true, senza
  errore.

#### D19 — `fn_articolo_correggi_struttura`: un JSON nullo o del tipo sbagliato esce come errore grezzo

* **Fatto.** `jsonb_populate_record`: `{"natura_vendita_id": null}` → 23502; `"forse"` su un boolean → 22P02.
  Nessuno dei due è un codice registrato.
* **Correzione.** Tipo e NOT NULL delle chiavi si validano prima di scrivere, con `E_PARAMETRO_INVALIDO`.
* **Presidio.** `null` su una colonna NOT NULL → `E_PARAMETRO_INVALIDO`.

#### D20 — `fn_articolo_colonne_struttura` lega la porta alle regole del form (sospetto)

* **Fatto.** Legge le regole `enabled` di `lock_columns_conditional` confrontando `condition_expr` come testo.
  Se si spegne una regola del form, il guard continua a bloccare la colonna, ma il verbo la rifiuta
  (`E_PARAMETRO_INVALIDO`): la colonna non si corregge più da nessuna parte. Il pgTAP
  `test-articolo-colonne-struttura-v1` lo presidia, ma è un presidio, non una garanzia del modello.
* **Correzione.** Q10. Si chiude con D28 del brief `dbops`, se il predicato diventa una funzione che leggono
  guard, form e porta.

#### D22 — Il fattore della mappatura si sceglie alla data di oggi, non alla data del documento

* **Fatto** (emerso nel giro 0). `trgfn_qta_from_operativa` filtra la mappatura dell'articolo con
  `fn_data_operativa()`, non con la data del documento. Con D13 risolto, cioè con le mappature versionate,
  una riga scritta oggi su un documento datato in un altro periodo prende il fattore di oggi. Una volta
  fotografato sulla riga, il fattore non cambia più. Va pesato insieme a D13 (Q13).
* **Correzione.** Se la mappatura si versiona, il fattore si legge alla data del documento.

### 2.3 La stessa regola scritta più volte (regola del 2)

| # | Regola | Dove sono le copie | Correzione |
| --- | --- | --- | --- |
| R1 | **Il fattore di conversione** | `catalogo.fn_get_uom_factor` contro `script.trgfn_qta_from_operativa` (D2); il trigger rilegge anche `articoli.uom_id` invece di `fn_get_uom_base` | Una sede, `fn_get_uom_factor`; il trigger la chiama |
| R2 | **La distinta di un padre alla data** | Il filtro `attivo + validita @> D` è riscritto a mano nei 5 `vendite.fn_*_riga_componenti_init`, nei 5 `*_preview`, in `script.trgfn_componenti_guard_coerenza_bom` e in `script.trgfn_listini_righe_comp_guard_coerenza_bom`. `vw_articoli_dettaglio.has_componenti_alla_data` ricopia `fn_articolo_padre_di_distinta_in_vigore`. Il guard IVA e `fn_check_articolo_riga_su_contesto` hanno ognuno la sua finestra (D9) | Un BB di catalogo parametrico per data (l'insieme dei legami del padre a D), e un predicato «da oggi in poi» per i guard. ⚠️ Tocca le funzioni di tutti i documenti di vendita: serve l'ok di Tid (Q8). Prima di usarlo nella vista si cronometra |
| R3 | **Il padre ha il flag giusto** | `trgfn_articoli_componenti_guard_is_composito` e `…_guard_solo_componente` hanno la stessa forma: leggono un flag di `prodotto_id` e sollevano. Il lato componente sta già nella check `ARTICOLO` (`fn_check_articolo_riga`); `script.trgfn_componenti_guard_coerenza_bom` ricontrolla a mano «padre `is_composito`» | I due motivi sul padre entrano nella check `ARTICOLO`; i due trgfn si ritirano nello stesso giro (Q5). Chiude anche D9 per il lato padre |
| R4 | **Il composito non sta in listino** | `trgfn_articoli_guard_listino_se_composito`, il motivo `E_LISTINO_RIGA_COMPOSITO_VIETATO` della check lato riga, `fn_articolo_righe_vive_non_ammesse` | Si ritira il guard (D5) |
| R5 | **L'etichetta leggibile dei flag** | Il `CASE` di `trgfn_articoli_guard_struttura_se_usato` e quello di `trgfn_articoli_guard_onere_natura` | Una funzione `catalogo.fn_articolo_flag_etichetta`, o un vocabolario, se le copie restano due |
| R6 | **La proiezione di una nota** | `vw_articoli_note` e `vw_articoli_componenti_note`: stesse 19 colonne di nota, stile e lingua. `script.fn_get_note` non serve, perché vuole un `target_id bigint` | Una vista base su `catalogo.note`, con le due viste sottili sopra |
| R7 | **Le FK ripetute come `*_ref_id`** | `vw_articoli_dettaglio`: `uom_ref_id`, `tipologia_ref_id`, `gruppo_ref_id`, `spesa_ref_id`, `iva_ref_id` duplicano le FK | Richiesta al BE (§5, BE5) |
| R8 | **«È composito», deciso fuori dal DB** | `backend/apps/vendite/services/offerte_service.py:1178,1209,1273`, `frontend/src/vendite/_shared/righe/RigheEccezioniDrawer.vue:668` (sospetto) | Richiesta al BE (§5, BE6): verificare se ricopiano una regola che il DB ha già |

⚠️ Le tre `fn_articolo_*_di_distinta_in_vigore` / `primo_padre_da_oggi` **non** sono copie: dicono tre cose
diverse (padre in vigore, componente in vigore, componente da oggi con il codice del padre). Restano.

### 2.4 Che cosa si può cancellare

| Oggetto | Perché | Condizione |
| --- | --- | --- |
| `trgfn_articoli_guard_listino_se_composito` e il suo trigger | D5, R4 | Q5 |
| `trgfn_articoli_componenti_guard_is_composito`, `…_guard_solo_componente` e i trigger | R3 (e D11 per il secondo) | Q5, Q2 |
| `uq_articoli_componenti_prodotto_componente_from` | Implicato da `uq_articoli_componenti_no_overlap`: `valido_dal` è NOT NULL, e due righe con lo stesso inizio si sovrappongono sempre | Nessuna; `uq_articoli_componenti_id_temporal` resta, perché regge la FK temporale |
| `ix_uom_tipi_codice_interno_upper`, `ix_artuomop_art_isbase` | Accanto a `uq_uom_tipi_codice_interno` (con `trgfn_codice_maiuscolo`) e all'unico parziale `uq_artuomop_one_base` (sospetto) | Verificare che nessuna query usi la forma `upper()` |
| `uom_tipi.codice` o `codice_interno` | Stessi valori, stessi COMMENT; il lock sta solo su `codice_interno` | Q9 |
| `articoli_uom_operativa.require_lot` (e forse `max_decimals`, `rounding_mode`) | D3 | Q4 |
| La FK semplice di `vendite.listini_righe_componenti` verso `articoli_componenti` | Implicata dalla FK temporale `PERIOD` (sospetto, fuori schema) | Verificare i lettori di `pg_constraint` |
| I wrapper BE `get_uom_base`/`get_uom_factor` (`catalogo_uom_repository.py:230-241`) | Senza chiamanti | Restano se D2 non li fa diventare utili: §5, BE2 |
| Rami irraggiungibili | `COALESCE` su colonne NOT NULL (`is_composito`, `attivo`, nei guard flags, listino, componente e in 10 `vendite.fn_*_componenti_*`); `TG_OP` e `prodotto_id IS NULL` in `guard_is_composito`/`solo_componente`; il ramo fail-open su `tipo_uom_id` NULL in `guard_tipo` (NOT NULL con FK); `v_factor > 0` e `LIMIT 1` su chiave UNIQUE in `fn_get_uom_factor`; `p_campi IS NULL OR` ripetuto nel verbo | Nello stesso giro che apre l'oggetto |

Nessuna funzione o vista è senza lettori: ognuna ha un chiamante nel DB, nel BE o in `ui.lista_definizione`.
Le colonne `is_sell_uom`, `is_purchase_uom`, `is_logistic_uom` e `gtin` sono dati d'anagrafica letti solo dal
CRUD: restano, ma il COMMENT non deve promettere un comportamento.

### 2.5 Codici errore

* Tutti i codici sollevati dalla distinta e dagli articoli sono registrati. `E_BOM_VALIDO_AL_INVALIDO`, ritirato,
  non è più sollevato.
* Codici generici al posto di codici registrati: D6.
* Errori grezzi: D19, e la FK delle note (D16).
* La nota di `E_BOM_MODIFICA_VIETATA` (`codici_errore.csv:78`) nomina solo il trigger d'immutabilità, ma lo
  solleva anche il guard flags (check 1 e 2).
* `fn_riattiva_articolo` (commento nel corpo e pagina) cita `E_PARENT_INACTIVE`, che non esiste: il codice vero
  è `E_ATTIVO_PADRE_NON_ATTIVO`, e arriva al COMMIT (trigger differito).
* L'area di log è disomogenea: `'database'` nei trigger della distinta, nel check 1-2 e in `fn_riattiva_articolo`,
  `'catalogo'` altrove. I guard IVA e listino passano `NULL::uuid` invece di `NEW.tx_id`.

#### D21 — Con `iva_id` NULL il messaggio del guard IVA esce col segnaposto vuoto

`iva_id` è nullable: il `SELECT … INTO` non trova righe e il `COALESCE(…, '—')` non scatta. Si chiude con D4.

### 2.6 Le fixture e i test pgTAP

`db/pgtap/catalogo` ha 25 file; nessuna riga di catalogo è nelle baseline dei rossi.

* **Senza presidio:** D1, D2, D3, D4 (legami chiusi), D5 lato articolo, D6 (`guard_tipo_update` non ha nessun
  test), D7, D8, D9, D11, D12, D16.
* **Deboli:**
  * `test-articoli-componenti-solo-componente.sql:77` usa `throws_ok(…, NULL, NULL)`: passa con qualunque errore
    e non lega `E_ARTICOLO_SOLO_COMPONENTE`.
  * `test-articoli-natura-vendita-notnull-default-v1.sql:49-53` conta i NULL di una colonna NOT NULL su tutta la
    popolazione: è tautologico, e in CI passa a vuoto.
  * `test-vw-articoli-dettaglio-e-onere-v1.sql:56-62` (test 3) itera su tutto il catalogo. I casi 1 e 2 sono
    costruiti: il test 3 si dichiara presidio o si toglie.
  * Le fixture che clonano «il primo articolo esistente» (`test-articoli-componenti-solo-componente.sql:52`,
    `ORDER BY a.id LIMIT 1`) dipendono dal seed. Vanno sui builder.

## 3. I metadati

Nessuno cambia il comportamento, ma ognuno dice una cosa falsa a chi legge. Si correggono con un changeSet nuovo,
nel giro che apre l'oggetto, oppure nel giro 5.

### 3.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `trgfn_articoli_guard_flags_struttura_bom_attiva` | «Lato articolo di `trgfn_articoli_componenti_guard_un_livello`»: non esiste. Il lato legame è `guard_componente` |
| M2 | COMMENT `vw_articoli_dettaglio` | «`requires_lotto` senza lock né fra i `non_editable_fields`»: falso, lo spegne una regola di `lock_columns_conditional` con `fn_articolo_usato`. «Non escono finché il BE non le nomina»: il BE le proietta già (`catalogo_repository.py:170,215-229`). Cita «ui.lista_definizione 26» per id |
| M3 | COMMENT `articoli.natura_vendita_id` | «NULL = non ancora classificato; a regime NOT NULL»: è già `NOT NULL DEFAULT 1` |
| M4 | COMMENT `articoli_componenti.id`, `.attivo` | «sequence `articoli_componenti_id_seq`»: è `uuid DEFAULT uuidv7()`. «del articolo» |
| M5 | COMMENT `articoli_uom_operativa.require_lot`, `.max_decimals`, `.rounding_mode` | Promettono un comportamento che nessuno applica (D3) |
| M6 | COMMENT `fn_get_uom_base` | «Senza UoM base»: `articoli.uom_id` è NOT NULL |
| M7 | COMMENT `magazzino.note` | Dice che `script.fn_get_note` legge anche le note di catalogo: falso, per via dell'uuid |
| M8 | Nota di `automation_lock_columns` su `catalogo.articoli.uom_id` | Cita `trg_articoli_a10_protect_uom_id_upd`, che non esiste più (oggi è `trg_articoli_a10_lock_columns_upd`); il codice `E_CODICE_NON_MODIFICABILE` è usato per un'unità di misura |

### 3.2 Senza COMMENT

* `vw_articoli_uom_operativa_dettaglio`: niente, né sulla vista né sulle colonne.
* Colonne delle altre 4 viste, di `note`, `note_articoli`, `note_articoli_componenti`, e tutte le colonne di
  `unita_misura_conversioni`; le 4 colonne d'audit di `uom_tipi`.
* I trigger dei guard di catalogo, tranne `trg_articoli_a10_guard_onere_natura_ins_upd` e
  `trg_articoli_componenti_a10_guard_is_composito_ins_upd`.

### 3.3 Marcatori di revisione, nomi di brief, id nei COMMENT (`linee-guida-sql.md` §5d)

* **Funzioni.** 11 su 23: `fn_articoli_ammessi`, `fn_articolo_colonne_struttura`, `fn_articolo_correggi_struttura`,
  `fn_articolo_righe_vive_non_ammesse`, `fn_articolo_usato`, `trgfn_articoli_componenti_block_modifica_struttura`,
  `trgfn_articoli_componenti_guard_componente`, `trgfn_articoli_guard_iva_bom_attiva`,
  `trgfn_articoli_guard_listino_se_composito`, `trgfn_articoli_guard_onere_natura`,
  `trgfn_articoli_guard_struttura_se_usato`.
* **Viste e tabelle.** 4 viste su 5 (`vw_articoli_componenti_dettaglio`, `vw_articoli_componenti_note`,
  `vw_articoli_dettaglio`, `vw_articoli_note`) e la tabella `note`.
* **Colonne.**
  * `articoli`: `causale_onere_id`, `gestito_a_magazzino`, `modo_approvvigionamento_id`, `note_target_tipo`,
    `obsoleto_dal`, `requires_lotto`;
  * `articoli_componenti`: `esposizione_in_fattura`, `note_target_tipo`, `validita`;
  * `validita` di `articoli_uom_operativa` e di `unita_misura_conversioni`;
  * `note.target_tipo`, `unita_misura.conta_dal_calendario`;
  * in `vw_articoli_dettaglio`: `causale_onere_id`, `e_obsoleto`, `e_onere`, `obsoleto_dal`.
* **Id di messaggio invece della chiave naturale** (§6b): «(387)», «(445)», «(446)» nei guard.
* **Cronaca nei corpi**: `-- rev 2026-10-19 (20261019-98…)` in `guard_onere_natura`, `Rev 20261002-61` in
  `block_modifica_struttura`, il nome di un brief in `guard_componente`.

Una parte coincide con D-C di `brief-db-articoli-obsoleto-dal` (Q11).

#### 3.3.1 D-C: i COMMENT del cantiere `obsoleto_dal`, anche fuori `catalogo` (Tid, 2026-11-11)

✅ **Tid, 2026-11-11, Q11 precisata (opzione a):** il giro 5 riscrive **tutti** i COMMENT nati da
`brief-db-articoli-obsoleto-dal`, anche quelli fuori dallo schema `catalogo`. D-C si chiude qui per intero: là non
resta un changeSet di COMMENT.

Fonte: i 13 changeSet di quel cantiere che scrivono un `COMMENT ON` (`20261105-01` … `-04`, `-06`, `-09` … `-13`,
`20261106-01` … `-03`; `-05`, `-07`, `-08` e `-14` non ne scrivono), poi `obj_description` / `col_description` su
dbdev, letti il 2026-11-11. Sono 26 oggetti. 16 sono già puliti, perché un giro successivo li ha riscritti: le colonne
`sorgente_*` di vendite (`brief-db-sorgente-documento-e-riga`), le due check e il guard della distinta (giri 1 e
1-bis di qui), `fn_e_obsoleto` e il guard generico di `dbops`. **L'elenco chiuso da riscrivere è questo:**

| Schema | Oggetto | Già in §3.3 |
| --- | --- | --- |
| `catalogo` | colonna `articoli.obsoleto_dal` | sì |
| `catalogo` | vista `vw_articoli_dettaglio` e le colonne `obsoleto_dal`, `e_obsoleto` | sì |
| `catalogo` | `fn_articoli_ammessi` | sì |
| `acquisti` | colonna `ddt_righe.sorgente_tipo_id` | **no** |
| `script` | `trgfn_righe_guard_articolo_ammesso` | **no** |
| `vendite` | `fn_clona_versione_listino` | **no** |
| `vendite` | trigger `trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd` | **no** |
| `vendite` | trigger `trg_listini_kit_a10_articoli_require_non_obsoleto_ins_upd` | **no** |

* Il COMMENT si riscrive **intero**, secondo `linee-guida-sql` §5d, anche dove il marcatore viene da un altro brief
  (`trgfn_righe_guard_articolo_ammesso` cita anche `brief-db-articoli-ammessi-per-documento` e i suoi changeSet).
* Prima di scrivere il giro si **rilegge** la tabella sul vivo: un giro intermedio può aver già ripulito un oggetto.
* Il controllo di testo su `obj_description` del giro 5 copre anche questi cinque oggetti fuori schema.
* ⚠️ Fuori da D-C: i rimandi al brief **nei corpi** (`-- … (brief-db-articoli-obsoleto-dal §3)` in
  `fn_check_articolo_riga_su_contesto`, in `trgfn_righe_guard_articolo_ammesso`). D-C riguarda il COMMENT. Si toccano
  solo se un giro riscrive comunque quella funzione: non si apre un `CREATE OR REPLACE` per un commento.

## 4. La documentazione

### 4.1 Le 35 pagine `manual/`

Nessuna passa la verifica di `standard-guide.md` §«Verifica di una pagina `manual/`». Il giro 0 le riscrive tutte
allo standard. La pagina descrive il comportamento di **oggi**, difetti compresi (come in `dbops`), e si riallinea
quando il difetto si chiude.

**Gli scostamenti comuni** (quasi tutte le pagine):
* manca «Ultimo aggiornamento»;
* «Vedi anche» con righe senza `>`, bullet `•`, etichette mancanti, link a `manual/` invece che alle schede;
* il primo paragrafo dello Scopo è un marcatore (`(latest review …)`, `(rev …)`, `(nasce …, brief …)`), e così
  finisce come descrizione dell'oggetto nell'indice dello schema (`catalogo/index.md`);
* nomi di brief, «Lotto», «Fase», id di changeSet nel corpo;
* blocchi `sql`, `json` o `python`, elenchi di colonne o di trigger agganciati ricopiati, sezioni «Best practice».

**Le pagine da rifare da capo** (formato vecchio: titolo `#`, otto o nove `##`, niente Scopo Principale, quindi
nessuna descrizione nell'indice): `unita_misura`, `uom_tipi`, `unita_misura_conversioni`,
`trgfn_articoli_guard_flags_struttura_bom_attiva`, `trgfn_articoli_guard_iva_bom_attiva`,
`trgfn_articoli_guard_listino_se_composito` (le ultime tre anche senza firma). Senza firma anche
`articoli_uom_operativa`.

**Il contenuto falso oggi**, da correggere nella riscrittura:

| Pagina | Che cosa |
| --- | --- |
| `articoli.md` | `voce_utility` non esiste; «tutte le FK ON UPDATE CASCADE» (falso per `uom_id` e `causale_onere_id`); «consigliato proteggere il codice», «valuta un trigger uppercase» (esistono lock e `trgfn_codice_maiuscolo`); «`requires_lotto` fuori dal registro»; destinazione `ORDINE` (oggi `ORDINE_VENDITA`); una sezione `🔄 rev` dopo la firma |
| `vw_articoli_dettaglio.md` | `ORDINE/COMMESSA/CONTRATTO`; «senza il lock BoM», «il BE non le nomina» (come M2) |
| `articoli_componenti.md` | `EXCLUDE USING gist` e `ix_…_no_overlap_gist`: oggi c'è `uq_articoli_componenti_no_overlap … WITHOUT OVERLAPS`; «`valido_al > valido_dal`»: è ammesso `=`; «i REQUIRE non sono generati»: li genera la regola ATTIVO; il controllo su `is_composito` chiamato «vincolo applicativo opzionale» (è un trigger); un id per numero |
| `vw_articoli_componenti_dettaglio.md` | `valid_from`/`valid_to` non esistono (`valido_dal`/`valido_al`); mancano `esposizione_*` e le capability |
| `trgfn_articoli_componenti_block_modifica_struttura.md` | `ex_articoli_componenti_no_overlap` e `chk_articoli_componenti_valid_dates` non esistono; `validita` fra i campi bloccati (è generata); «protegge da correzioni retroattive» (D10); non dice che `prodotto_id` è libero (D1) |
| `trgfn_articoli_componenti_guard_is_composito.md`, `…_guard_solo_componente.md` | Esempi con `valid_from`; «nessun effetto se NULL» (la colonna è NOT NULL) |
| `trgfn_articoli_componenti_guard_componente.md` | «L'IVA non cambia, la tiene il lato articolo»: vero per l'IVA, falso per composito e obsoleto (D9). Manca «Codici errore» |
| `trgfn_articoli_guard_flags_struttura_bom_attiva.md` | «Padre e figlio in BoM diverse» contro il livello unico |
| `trgfn_articoli_guard_iva_bom_attiva.md` | La procedura «prima i partner» (D4) |
| `trgfn_articoli_guard_listino_se_composito.md` | «Simmetrico di `trgfn_listini_righe_guard_no_composito`», ritirato; il rimedio suggerito (D5) |
| `fn_articolo_righe_vive_non_ammesse.md`, `fn_articolo_correggi_struttura.md` | Citano `fn_check_articolo_riga`: dal 2026-10-21 il corpo usa `fn_check_riga_documento_su_contesto`. «Il backend lo espone nel giro BE/FE»: lo espone già |
| `fn_articoli_ammessi.md` | Firma in un blocco sql |
| `fn_articolo_*_di_distinta_in_vigore.md`, `fn_articolo_primo_padre_da_oggi.md` | Id di changeSet nelle Note di migrazione |
| `fn_riattiva_articolo.md` | `E_PARENT_INACTIVE` (§2.5); «13+ relazioni», un conteggio; `()` nel titolo |
| `note_articoli.md`, `note_articoli_componenti.md` | «Partizione di `vendite.note`»: il padre è `catalogo.note`; ipotizza `ON DELETE RESTRICT`, ma la FK è `CASCADE`; conteggi di righe. Tace il `block_deact` (D16) |
| `uom_tipi.md` | `VALUTA` non è nel seed; «conversioni SMC↔KWH/MJ già presenti»: il CSV è vuoto; chiama `codice` l'identificativo stabile, ma il codice bloccato è `codice_interno` |
| `unita_misura.md` | Non nomina `conta_dal_calendario` |
| `unita_misura_conversioni.md` | Il fallback della funzione non è usato da nessuno (D2); `valido_dal` è NOT NULL |
| `articoli_uom_operativa.md` | Le regole di input applicate (D3); «`factor_to_base = 1` sulla base» non è un vincolo (D12); «Migliorie» stantie (l'indice unico parziale c'è) |
| `trgfn_uom_conversioni_guard_tipo.md` | «Resta scoperta l'unità senza tipologia»: `tipo_uom_id` è NOT NULL con FK |
| `trgfn_unita_misura_guard_tipo_update.md` | I consumatori si cercano dal nome della funzione, ma in `error_log` c'è il trigger (D6) |
| `trgfn_articoli_seed_uom_base.md` | Il caso «riga già esistente» non capita all'INSERT di un id nuovo; tace D7 e D12 |
| `fn_get_uom_base.md` | «Senza UoM base» (M6) |

**Il blocco comune delle note.** Manca un `catalogo/_note-partizioni.md` sul modello di
`magazzino/_note-partizioni.md`. Le due pagine delle partizioni diventano cornice, Scopo e include, più la sola
specificità (chiave uuid, il legame della distinta).

### 4.2 Doc fuori schema

| File | Correzione |
| --- | --- |
| `guide/gestione-listini.md:383` | `ex_articoli_componenti_no_overlap` «exclusion constraint» → `uq_articoli_componenti_no_overlap`, `UNIQUE … WITHOUT OVERLAPS` |
| `guide/gestione-listini.md:374` | I campi immutabili senza `prodotto_id`: si allinea con D1 |
| `guide/gestione-listini.md:380-381` | «Chiudi con `valido_al = oggi`, poi la nuova con `valido_dal = oggi`»: con `validita` `'[]'` le due righe si sovrappongono sul giorno, e il vincolo le rifiuta. Va verificata, poi corretta (la nuova parte da domani, o la vecchia chiude ieri) |
| `dev/manual/modello-componenti-bom.md` | §9.2 «un livello, i cicli non si costruiscono»: vero solo a D9 chiuso; `partecipa_qta`/`esposto_in_fattura` come cronaca (stanno già nel changelog delle decisioni). Link a `manual/` alle righe 128, 328, 330, 467 |
| `dbzero/script/manual/trgfn_righe_guard_articolo_ammesso.md:31,57`, `fn_articolo_riga_contesto.md:7`, `fn_check_articolo_riga.md:9,19`, `fn_check_articolo_riga_su_contesto.md:9,45`, `trgfn_listini_righe_comp_guard_coerenza_bom.md:15`; `dbzero/vendite/manual/promo_articoli.md:65` | Link `/dbzero/catalogo/manual/…` ripuntati alle schede |

## 5. Ricadute su BE e FE

Da girare al team quando il giro DB corrispondente è applicato.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | 2 | `fn_delete_uom_operativa` (`catalogo_service.py:1700`) cancella anche la riga base: col guard di D12 il DB rifiuta. Il servizio non la offre più, e il controllo parziale di `:844` si ritira (lo fa il DB) |
| BE2 | 2 | `get_uom_base`/`get_uom_factor` (`catalogo_uom_repository.py:230-241`) non hanno chiamanti: si ritirano, a meno che non servano al form |
| BE3 | 2 | Verificare se il servizio delle righe azzera `factor_to_base` quando cambia l'unità (D8). Dopo il giro non serve più |
| BE4 | 2, 3 | I codici nuovi (D2, D6, eventualmente D3) nella mappa degli errori e nell'i18n; `E_PARAMETRO_INVALIDO` da `fn_articolo_correggi_struttura` (D19) |
| BE5 | 5 | Se la vista perde i `*_ref_id` (R7), la proiezione del repository li prende dalle FK |
| BE6 | — | `offerte_service.py:1178,1209,1273` e `RigheEccezioniDrawer.vue:668` decidono su `is_composito`: verificare se ricopiano una regola del DB (R8) |
| BE7 | 3 | Se il cambio d'IVA diventa un verbo del kit (Q6), il form dell'articolo lo chiama |
| BE16 | 2 | Q4 ritira `rounding_mode` e `require_lot`: il lookup `GET /api/v1/catalogo/lookup/rounding-modes/` (`api_catalogo.md` §2.3, `_ROUNDING_MODE_VALIDI` in `catalogo_service`) e i campi del form dell'unità operativa si ritirano nello stesso giro BE |
| BE8 ✅ (2026-11-09) | 1 | I due codici nuovi `E_BOM_CHIUSURA_RETROATTIVA` (DATO_ERRATO, campo `valido_al`) ed `E_BOM_LEGAME_CHIUSO` (CONFLITTO_STATO, campo `valido_al`): mappa degli errori generata (`error_policies_generated.py`) e i18n. `E_ARTICOLO_NON_COMPOSITO` ora porta `campo = prodotto_id` e un bersaglio `ARTICOLO` |
| BE9 ✅ (2026-11-09), doc ⏭️ | 1 | «Chiudi riga» della distinta: `data_min_chiusura` è ieri (non più `valido_dal`); il datepicker la legge dalla vista, nessun calcolo nel FE. ⏭️ **Resta la doc** (verificato il 2026-11-09 dopo `9f540bea72`): `docs/it/backend/catalogo/manual/api_catalogo.md:601` dice ancora «`valido_dal` se chiudibile», e §4.3 (`valido_al` «unico campo modificabile») non dice che la fine non cambia i giorni passati e che una fine già passata non si tocca |
| BE10 ✅ (2026-11-09) | 1 | Il form dell'articolo: `is_composito` e `is_solo_componente` insieme li rifiuta ora un CHECK (23514, `chk_articoli_composito_non_solo_componente`). Il form spegne l'uno quando l'altro è acceso, e il servizio mappa il vincolo a un messaggio |
| BE11 ✅ (2026-11-09), doc ⏭️ | 1 | `catalogo_bom_repository.delete_componente` (`:270`) non può mai riuscire: il trigger d'immutabilità rifiuta ogni DELETE. Si ritira con il suo endpoint, oppure diventa «chiudi». ⏭️ **Resta la doc**: l'endpoint è ritirato, ma `api_catalogo.md` §4.4 «Elimina componente» documenta ancora il `DELETE` |
| BE12 ✅ (2026-11-09) | 1 | Il picker degli articoli ammessi per la distinta (`catalogo.fn_articoli_ammessi` con `ARTICOLO`) su un padre non composito solleva `E_ARTICOLO_NON_COMPOSITO` invece di restituire una lista vuota: il FE apre il picker solo con `puo_gestire_bom` |

## 6. Le decisioni di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q1 ✅ | D10: un legame di distinta si può chiudere nel passato, o riaprire? | No a tutte e due, per i legami già in vigore: si chiude da oggi in poi, e una riapertura è una riga nuova — **✅ Tid, 2026-11-08: come da proposta** |
| Q2 ✅ | D11: CHECK `NOT (is_composito AND is_solo_componente)`? | Sì, e `guard_solo_componente` si ritira — **✅ Tid, 2026-11-08: come da proposta** |
| Q3 ✅ | D13: la mappatura dell'unità operativa si versiona? | Sì, `UNIQUE … WITHOUT OVERLAPS` come la distinta; altrimenti si ritirano le date — **✅ Tid, 2026-11-08: versionata, UNIQUE WITHOUT OVERLAPS** |
| Q4 ✅ | D3: `max_decimals`, `rounding_mode`, `require_lot` | `max_decimals` si applica (codice nuovo); `rounding_mode` e `require_lot` si ritirano (il lotto è `articoli.requires_lotto`) — **✅ Tid, 2026-11-08: come da proposta** |
| Q5 ✅ | R3, R4, D5: si ritirano `guard_listino_se_composito`, `guard_is_composito`, `guard_solo_componente`, e i motivi sul padre vanno nella check `ARTICOLO`? | Sì — **✅ Tid, 2026-11-08: come da proposta** |
| Q6 ✅ | D4: cambio d'IVA di un kit con un constraint trigger differito, o con un verbo? | Constraint trigger differito: non cambia il contratto del BE — **✅ Tid, 2026-11-08: come da proposta** |
| Q7 ✅ | D2: senza mappatura né conversione, la riga si rifiuta? | Sì, `E_UOM_MISSING` — **✅ Tid, 2026-11-08: come da proposta** |
| Q8 ✅ | R2: il BB «distinta alla data» tocca le funzioni di tutti i documenti di vendita. Si fa qui, in un giro a parte, o in un brief di vendite? | Qui, giro 1-bis, dopo il giro 1 e insieme a D28 di `dbops` — **✅ Tid, 2026-11-08: come da proposta, ok alla famiglia dei documenti di vendita** |
| Q9 ✅ | `uom_tipi`: `codice` o `codice_interno`? | Resta `codice_interno` (bloccato); `codice` si ritira, se il BE non lo espone come etichetta — **✅ Tid, 2026-11-08: come da proposta** |
| Q10 ✅ | D20: la porta amministratore deve dipendere dalle regole del form? | No: le colonne strutturali si dichiarano in un posto, che leggono guard, form e porta (con D28) — **✅ Tid, 2026-11-08: come da proposta** |
| Q11 ✅ | M3 e D-C di `brief-db-articoli-obsoleto-dal`: chi riscrive i COMMENT? | Tutti qui, nel giro 5; D-C si chiude rimandando qui — **✅ Tid, 2026-11-08: tutti qui; D-C di brief-db-articoli-obsoleto-dal si chiude rimandando qui**. ✅ **Tid, 2026-11-11: «tutti» vale anche fuori `catalogo`**; l'elenco chiuso è in §3.3.1 |
| Q12 ✅ | D16: le note di catalogo prendono `tx_id` e `user_* text` come le altre? E un articolo con una nota si deve poter disattivare? | Sì alla forma comune; sì alla disattivazione (la nota non è un figlio vivo: va esclusa dal `block_deact`) — **✅ Tid, 2026-11-08: come da proposta** |
| Q13 ✅ | D22: il fattore della mappatura si legge alla data del documento? | Sì, se Q3 versiona la mappatura; altrimenti la domanda cade — **✅ Tid, 2026-11-08: il fattore si legge alla data del documento** |
| Q14 ✅ | §2.4: si ritirano gli indici che ripetono un vincolo? | `uq_articoli_componenti_prodotto_componente_from` sì; `ix_uom_tipi_codice_interno_upper` e `ix_artuomop_art_isbase` solo dopo la verifica dei lettori e dei piani — **✅ Tid, 2026-11-08: come da proposta** |
| Q23 ✅ | D24 (§13.7.3, domanda 1): il fattore di una mappatura già scritta si cambia sul posto? | No: **bloccato**. Un fattore nuovo è una riga nuova (chiudi e inserisci, Q3) — **✅ Tid, 2026-11-10** |
| Q24 ✅ | D25 (§13.7.3, domanda 2): l'unità della riga di listino deve valere alla decorrenza della versione o per tutto il suo periodo? | **Per tutto il periodo** della versione, regola a DB — **✅ Tid, 2026-11-10** |
| Q25 ✅ | D26 (§13.7.3, domanda 3): il fattore 1 per difetto delle commesse va in un brief nuovo? | No, **in questo brief** — **✅ Tid, 2026-11-10** |
| Q26 ✅ | D24 (§15.1): con il fattore si bloccano anche `uom_id` e le date della mappatura? | Sì: `uom_id` bloccato; le date come Q1 (si chiude da oggi in poi, `valido_dal` di una mappatura in vigore non si sposta) — **✅ Tid, 2026-11-10** |
| Q27 ✅ | D25 (§15.2): il terzo lato, il catalogo che cambia sotto un listino vivo | (a) **rifiuto**: una mappatura o una conversione generale non si chiude né si spegne se una versione ATTIVA ne usa l'unità oltre la nuova fine; giudizio a fine transazione (chiudi e inserisci); listini di altre aziende contati, non nominati. Scartate (b) avviso e conferma (la riga di listino non ha un periodo suo) e (c) presidio a valle (contraddice Q24) — **✅ Tid, 2026-11-10** |
| Q28 ✅ | D24, D27 (§15.5): lo spegnimento e la cancellazione di una mappatura o di una conversione riscrivono il passato come il fattore | Ammessi solo se non ha giorni passati (comincia oggi o dopo: quella inserita per errore); una già in vigore si chiude — **✅ Tid, 2026-11-10** |
| Q29 ✅ | D27 (§15.5): le conversioni generali hanno lo stesso difetto di D24 | Stesse regole della mappatura (Q23, Q26, Q28), nello stesso giro — **✅ Tid, 2026-11-10** |
| Q30 ✅ | D26 (§15.5): il fattore delle commesse senza «1 per difetto» | La regola del giro 2 per le righe dei documenti: senza fattore, `fn_get_uom_factor` alla data dell'attività; senza neanche quello, `E_UOM_MISSING`. Via il default 1 dalle due colonne, dal parametro e dalle tre funzioni; la regola in un trigger sulla tabella — **✅ Tid, 2026-11-10** |
| Q31 ✅ | D24, D27 (§15.7): con Q28 una mappatura o una conversione con giorni passati non si spegne più, e il block dell'automazione ATTIVO impedisce di spegnere l'articolo o l'unità finché ne hanno una attiva: un articolo o un'unità con una storia non si spegnerebbero mai | (a) **eccezione**: le FK `articoli_uom_operativa.articolo_id`, `.uom_id` e `unita_misura_conversioni.uom_from_id`, `.uom_to_id` in `dbops.automazione_attivo_eccezioni`, come la nota di Q12: la mappatura è storia, non un figlio vivo. Scartata (b) spegnerle insieme al padre nella stessa transazione (più codice, e la riaccensione resta a parte) — **✅ Tid, 2026-11-10** (proposta per la mappatura; la sessione DB l'ha estesa alle conversioni, §15.7 punto 1) |

| Q32 ✅ | G1 (§15.11): la regola 1 di `trgfn_uom_guard_storia` (unità, articolo, fattore, inizio: mai) passa a `script.trgfn_lock_columns`, registrata in `automation_lock_columns`, così entra in `vw_non_editable_fields`? | Sì. Il guard tiene le regole 2 e 3; il BE ritira `_NON_EDITABLE_DB_GAPS`; la frase di `E_UOM_STORIA_IMMUTABILE` si riscrive sulla colonna — **✅ Tid, 2026-11-11: come da proposta** |
| Q33 ✅ | G2 (§15.11): la capability della mappatura (oggi `puo_eliminarsi` dice il falso) e quella della conversione generale | Un BB di catalogo sulle regole 2 e 3, letto da `vw_articoli_uom_operativa_dettaglio` e da una vista nuova `vw_unita_misura_conversioni_dettaglio`, che diventa la `vista_sql` di `catalogo.conversioni_uom` — **✅ Tid, 2026-11-11: come da proposta** |
| Q35 ⏭️ | §16.6: col ritiro della PATCH il legame di distinta resta attivo per sempre, e il BLOCK su `articoli_componenti` impedisce di spegnere un kit (e un componente) con una storia | (a) **eccezione**, la forma di Q31: `articoli_componenti.prodotto_id` e `.componente_id` in `automazione_attivo_eccezioni`, dopo la verifica del lato componente (§16.6.3). Scartabile (b), un verbo «spegni legame» — **proposta, da decidere: Tid** |

## 7. I giri, nell'ordine in cui si fanno

Per gravità; i lavori sugli stessi oggetti vanno insieme, così ogni oggetto si apre una volta sola. Ogni giro
comprende changeSet, pgTAP del presidio, COMMENT e pagine `manual/` riallineati, poi l'apply di Tid e il via al
giro dopo.

| Giro | Classe | Contenuto | Perché insieme |
| --- | --- | --- | --- |
| 0 | doc | §4: le 35 pagine, il blocco comune delle note, la doc fuori schema | Non tocca il DB; descrive l'oggi e rende leggibili i giri dopo |
| 1 | A + B | **La distinta.** D1, D9, D10 (Q1), D11 (Q2), R3 (Q5); pgTAP di §2.6 sulla distinta | Gli stessi trigger di `articoli_componenti` e il guard flags. Dopo D28 di `dbops`, o con D28 |
| 1-bis | B | **Il BB della distinta alla data** (R2, Q8) | Tocca vendite e `script`: un giro a parte, con l'ok di Tid |
| 2 | A + B | **Le quantità e le unità.** D2 (Q7), D3 (Q4), D8, D12, D13 (Q3), D22 (Q13), D14, D15, D6, D17; BE1-BE4 | `trgfn_qta_from_operativa`, `articoli_uom_operativa` e i due guard di tipologia |
| 2-bis | A + B | **Le tre decisioni del giro BE.** D24 (Q23), D25 (Q24), D26 (Q25); BE21-BE23 (§15) | Nascono dal giro BE del giro 2; tocca anche `vendite` (listini, commesse) |
| 3 | A + B | **I guard degli articoli.** D4 (Q6) + D21, D5 (R4), D7, D18, D19, D20 (Q10), R5 | Gli oggetti di `catalogo.articoli` |
| 4 | B | **Le note.** D16 (Q12), R6 | Tabella `note`, partizioni e due viste |
| 5 | C | **Pulizia e metadati.** §3 (Q11), con D-C di `brief-db-articoli-obsoleto-dal` anche fuori `catalogo` (§3.3.1), §2.4 (indici ridondanti, rami irraggiungibili, `uom_tipi.codice` con Q9), §2.5, pgTAP deboli di §2.6, R7 | Quello che nessun giro precedente ha già aperto |

## 8. Alla chiusura

* Ogni pagina `manual/` toccata passa la verifica di `standard-guide.md`, e la sua data è aggiornata.
* I pgTAP nuovi costruiscono i propri soggetti: nessuno itera su ciò che c'è.
* Il brief va in `work-done/` quando tutti i giri sono applicati e le ricadute BE sono chiuse o passate a un
  brief BE.

## 9. Giro 0 — la documentazione, 2026-11-08

Scritto dalla sessione DB su via di Tid, con quattro agenti per area (articoli, distinta e doc fuori schema, unità
di misura, note). Le pagine descrivono il comportamento di oggi, letto dai corpi (`pg_get_functiondef`), da
`pg_trigger`/`pg_constraint` di dbdev e dalle schede auto-generate. I difetti di §2 sono scritti al presente,
in una sezione «⚠️ Che cosa oggi non copre», senza rimandi a questo brief. Si chiudono pagina per pagina con il
giro che li corregge.

### 9.1 Che cosa è scritto

* **Le 35 pagine `docs/it/dbzero/catalogo/manual/`.** Tutte riscritte nella cornice dello standard. Le sei in
  formato vecchio sono rifatte da capo. Le falsità di §4.1 sono tolte.
* **Il blocco comune `docs/it/dbzero/catalogo/_note-partizioni.md`** (nuovo). È incluso dalle due partizioni.
* **Doc fuori schema.**
  * `guide/gestione-listini.md` §5.3: la procedura «chiudi e versiona» ora funziona. La vecchia versione chiude
    all'ultimo giorno e la nuova parte dal giorno dopo, perché `validita` comprende i due estremi. Il nome del
    vincolo è corretto.
  * `dev/manual/modello-componenti-bom.md`: link ripuntati alle schede.
  * `script/manual/`: `trgfn_righe_guard_articolo_ammesso`, `fn_articolo_riga_contesto`, `fn_check_articolo_riga`,
    `fn_check_articolo_riga_su_contesto` e `trgfn_listini_righe_comp_guard_coerenza_bom`.
  * `vendite/manual/promo_articoli`.
  * Su questi file sono cambiati solo i link verso `/dbzero/catalogo/manual/` e la data. Erano puliti in
    `git status`.

### 9.2 Le verifiche

Su tutte le 35 pagine, i sei controlli di `standard-guide.md` §«Verifica di una pagina `manual/`» passano:
* nessuna etichetta senza `>`;
* uno Scopo Principale che non comincia con `(`;
* marcatori solo nelle Note di migrazione;
* un solo `##`;
* firma in fondo e nessun link `/dbzero/…` morto;
* nessun blocco di codice.

In più: nessun id di changeSet, nessun link a `/dbzero/…/manual/`, data all'8 novembre 2026. La build della doc
non è stata lanciata, quindi l'include del blocco comune non è provato al rendering.

### 9.3 Fatti emersi nella riscrittura

* **Un legame di distinta non si cancella mai.** `trgfn_articoli_componenti_block_modifica_struttura` rifiuta ogni
  DELETE (`E_BOM_MODIFICA_VIETATA`). Con il `block_deact` della nota, un legame annotato si può solo chiudere con
  `valido_al`. È coerente con «chiudi e inserisci»: un fatto, non un difetto. Ora è scritto nelle pagine.
* **D22**, nuovo (§2.2): il fattore della mappatura si sceglie alla data di oggi.
* **D7 resta da eseguire.** L'articolo creato non attivo è descritto nelle pagine come difetto. L'affermazione si
  regge sui corpi, ma non è stata provata.

### 9.4 Residuo

* Le date delle Note di migrazione vengono dalle pagine vecchie, dagli header dei pgTAP e da `git log -S`, non da
  un controllo changeSet per changeSet.
* La pagina d'esempio `dbops/manual/fn_resolve_scope.md` ha ancora un id di changeSet nelle Note di migrazione,
  contro lo standard. È fuori perimetro: la sistema il brief `dbops`.

### 9.5 Commit (2026-11-08)

* Una parte del giro 0 è finita nel commit `ecd35e08cf` di un'altra sessione DB: le tre pagine delle note
  (`note`, `note_articoli`, `note_articoli_componenti`), i link di `script/manual`, `promo_articoli` e
  `modello-componenti-bom`. Quel commit include il blocco comune, ma non lo contiene.
* Il resto è in un commit di questo cantiere: le altre 32 pagine `manual/`, il blocco
  `_note-partizioni.md`, `guide/gestione-listini.md` e questo brief.
* Le schede auto-generate di `catalogo` modificate nel working tree (`tabelle/`, `funzioni/`, `index*.md`)
  sono di altre sessioni e restano fuori.

## 10. Giro 1 — la distinta, 2026-11-09

Via di Tid il 2026-11-09, coi numeri dal `20261110-62`. Difetti del giro: D1, D9, D10 (Q1), D11 (Q2), R3 (Q5). D28 del
brief `dbops` è già chiuso (giro 10a): il giro parte dai suoi predicati.

### 10.1 Che cosa è scritto

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261110-62` | `catalogo.fn_articolo_padre_di_distinta_da_oggi`: padre di una distinta in vigore o futura, la stessa finestra del lato componente |
| `20_code/catalogo/20261110-63` | Guard flags: il check 1 chiede il predicato da oggi (D9); area di log `catalogo`; COMMENT secondo §5d |
| `20_code/script/20261110-64` | `script.fn_articolo_riga_contesto`: la testata della distinta è un composito, altrimenti `E_ARTICOLO_NON_COMPOSITO` (Q5). Sede unica della regola del padre |
| `20_code/catalogo/20261110-65` | `trgfn_articoli_componenti_guard_componente` e il suo trigger: `UPDATE OF` anche `valido_al`; giudica la riattivazione e l'allungamento della fine; la chiusura no (D9) |
| `20_code/catalogo/20261110-66` | `trgfn_articoli_componenti_block_modifica_struttura` e il suo trigger: `prodotto_id` immutabile (D1); la fine non cambia i giorni già passati (Q1, D10) |
| `20_code/catalogo/20261110-67` | Ritirati `trgfn_articoli_componenti_guard_is_composito` e `…_guard_solo_componente`, coi trigger (R3, Q5) |
| `20_code/catalogo/20261110-68` | `vw_articoli_componenti_dettaglio`: `data_min_chiusura` = la più tarda fra `valido_dal` e ieri (Q1) |
| `80_data/changelog/20261110-69` | `lock_columns_conditional`: le regole 1-2 del form chiamano il predicato da oggi, come il guard |
| `90_end/20261110-70` | Ritirata `catalogo.fn_articolo_padre_di_distinta_in_vigore` (dopo le regole del form) |
| `90_end/20261110-71` | CHECK `chk_articoli_composito_non_solo_componente` su `catalogo.articoli` (Q2) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_BOM_CHIUSURA_RETROATTIVA` (1462), `E_BOM_LEGAME_CHIUSO` (1463); note e causa di `E_BOM_MODIFICA_VIETATA` riscritte |

`%TYPE` in firma, `DECLARE` e nelle firme di `COMMENT`/`DROP`; i corpi di partenza da `pg_get_functiondef` su dbdev;
rollback = corpi, COMMENT e trigger di prima.

### 10.2 La forma della regola di Q1

Q1 (Tid, 2026-11-08) dice: la fine di un legame in vigore non si sposta nel passato e non si toglie. Scritta sul
modello, la regola è **«la fine non cambia i giorni già passati»**, al giorno aziendale:

* una fine **già passata** non si tocca più: né spostata, né tolta (`E_BOM_LEGAME_CHIUSO`). Per rimettere il componente
  si inserisce un legame nuovo;
* le altre fini vanno **a vuoto o da ieri in avanti** (`E_BOM_CHIUSURA_RETROATTIVA`, con la prima data ammessa);
* **chiudere a ieri** è ammesso, perché la storia resta com'era, ed è il modo di far valere da oggi la versione nuova
  (la `validita` comprende i due estremi);
* **togliere una fine futura** è ammesso, perché il passato non cambia; lo giudica il guard del legame come composizione
  nuova (componente ritirato o composito, padre non composito).

### 10.3 Le scelte dentro il giro (da guardare, Tid)

1. **Il padre non composito è un controllo del documento, non un motivo.** L'ho messo in `fn_articolo_riga_contesto`,
   come il padre mancante, e non fra i motivi del componente. Ne segue che il picker della distinta su un padre non
   composito solleva invece di proporre una lista vuota (BE12). In compenso la regola ha una sede sola, ed è il lato
   documento della stessa check che già giudicava il componente.
2. **Il check 2 del guard flags non cambia finestra.** Resta «componente di una distinta in vigore»: D9 parla
   del padre, e la regola del check 2 (un componente non cambia `is_solo_componente`) è sospetta di suo (§2.2, D11).
   Il suo predicato `fn_articolo_componente_di_distinta_in_vigore` resta.
3. **Una fine prima di `valido_dal` resta alla regola del periodo.** Il trigger d'immutabilità non la giudica, così
   l'operatore legge la frase della regola del periodo, come prima.
4. **L'area di log `database` diventa `catalogo`** nei corpi che il giro riscrive (guard flags, immutabilità), e
   l'immutabilità registra il `tx_id` della riga.

### 10.4 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di Liquibase, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** Le dieci `changes` in ordine di fase e numero, con le `preConditions` come asserzioni
  dopo i changeSet precedenti, più le righe nuove dei CSV: passano tutte in una transazione. Dopo il `ROLLBACK` lo
  scratch è com'era (il predicato vecchio c'è, il nuovo no). Le `preConditions` lette anche su dbdev, prima: stesse
  risposte dello scratch.
* **I pgTAP che toccano gli oggetti del giro**: tutti quelli di `catalogo/`, più quelli che nominano la distinta, la
  check, le regole del form o il picker, cioè 73 file, con e senza l'estratto in testa.
  * Verdi con l'estratto, tranne `catalogo/test-articolo-usato-struttura-v1` test 17, rosso uguale anche senza: il file
    stesso lo dichiara «rosso da owner, verde come app».
  * Cambiati nel giro, perché asserivano la regola di prima: `catalogo/test-distinta-predicati-guard-e-form-v1` (il
    predicato nuovo, un padre con distinta solo futura), `catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1`
    (la prima fine è ieri), `vendite/test-fatture-righe-kit-qta-periodo-v1` test 21 (`prodotto_id` fra i campi bloccati),
    `catalogo/test-vw-articoli-dettaglio-bom-capability-v1` (la fixture costruiva un kit solo componente),
    `catalogo/test-articoli-componenti-solo-componente` (riscritto sulle due sedi della regola).
  * ⚠️ `catalogo/test-articoli-componenti-guard-attivo-composito` cercava per nome il guard ritirato: senza correzione il
    caso «padre non composito» sarebbe diventato uno skip verde. Ora cerca il guard del legame.
  * Nuovo: `catalogo/test-distinta-storia-e-ritorni-v1` (15 test: padre immutabile, le regole della fine, riattivazione
    e allungamento giudicati, padre con distinta solo futura, la capability della vista). Senza l'estratto: 9 rossi
    su 15, cioè prova davvero la regola nuova.
  * Commenti che nominavano il guard ritirato in sette pgTAP: ripuntati alla check della distinta.
* **Deadlock.** Una prima corsa ha incontrato una corsa pgTAP di un'altra sessione sullo scratch: sei file in
  deadlock. Rilanciati a scratch libero, verdi.
* **Non provato:** la corsa come app (la fa Tid dopo l'apply), e il migrate vero (pgjdbc, ordine reale).

### 10.5 Doc

Pagine `manual/` riallineate al giro: cancellate quelle dei tre oggetti ritirati, creata quella del predicato nuovo,
aggiornate le pagine della distinta, del guard flags, degli articoli, del contesto e della check, la guida dei listini
§5.3 e il modello della distinta. Le sezioni «⚠️ Che cosa oggi non copre» perdono i punti che il giro chiude. La scheda
auto-generata del predicato nuovo nasce alla rigenerazione della doc, dopo l'apply.

### 10.6 Chiusura (2026-11-09)

* **Applicato** da Tid su dbdev e sullo scratch: `20261110-62` … `-71` e le due righe nuove dei CSV dei codici. Su dbdev
  i dieci changeSet sono nel `databasechangelog` (letto il 2026-11-09). pgTAP come app verdi.
* **Da committare** (il giro 1 intero):
  * i changeSet `20_code/catalogo/20261110-62`, `-63`, `-65` … `-68`, `20_code/script/20261110-64`,
    `80_data/changelog/20261110-69`, `90_end/20261110-70`, `-71`;
  * `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (solo le righe di questo giro);
  * i pgTAP: `catalogo/test-distinta-storia-e-ritorni-v1.sql` (nuovo), `test-articoli-componenti-solo-componente.sql`,
    `test-distinta-predicati-guard-e-form-v1.sql`, `test-vw-articoli-componenti-dettaglio-capabilities-v1.sql`,
    `test-vw-articoli-dettaglio-bom-capability-v1.sql`, `test-articoli-componenti-guard-attivo-composito.sql`,
    `test-articoli-componenti-immutabilita.sql`, `vendite/test-fatture-righe-kit-qta-periodo-v1.sql`, e i commenti
    in `vendite/test-righe-e-componenti-le-altre-famiglie-v1.sql`, `vendite/test-righe-e-componenti-debiti-residui-v1.sql`,
    `vendite/test-componenti-propaga-qta-da-operativa-v1.sql`, `vendite/test-ddt-componenti-senza-prezzo-v1.sql`,
    `script/test-fn-check-prezzi-autorizzati-v1.sql`, `dbops/test-fn-non-editable-fields-conditional.sql`;
  * `scripts/guardrail_pgtap_preambolo.py`: la soglia dei `throws_ok` senza discriminante da 110 a 109;
  * la doc di §10.5 (le pagine `manual/` di `catalogo`, `script/manual/fn_articolo_riga_contesto.md` e
    `fn_check_articolo_riga.md`, `dbops/manual/fn_non_editable_fields.md` e `lock_columns_conditional.md`,
    `guide/gestione-listini.md`, `dev/manual/modello-componenti-bom.md`), con le tre pagine cancellate;
  * questo brief e `brief-db-articoli-obsoleto-dal` (il rimando di D-C).
* ⚠️ Nel working tree ci sono file di altre sessioni (fra cui i `fk_index_policy_*.csv` cancellati, schede auto-generate e
  pagine `dbops/manual/`): non entrano nel commit del giro.
* **Doc auto-generata:** alla prossima rigenerazione nasce la scheda di `catalogo.fn_articolo_padre_di_distinta_da_oggi`
  e spariscono quelle dei tre oggetti ritirati. Fino ad allora tre pagine `manual/` hanno un link a una scheda che non
  c'è ancora.
* **Il giro 1 è chiuso** per la parte DB. Restano BE8-BE12 al team BE e le scelte di §10.3 da guardare.
* **Committato** da Tid il 2026-11-09: `eef662024d`.

## 11. Giro 1-bis — il BB della distinta alla data: il censimento e il piano, 2026-11-09

Il giro chiude R2 (Q8). Questa sezione è stata scritta **in sola lettura**, prima del via: nessun changeSet, nessun pgTAP.
I corpi vengono da `pg_get_functiondef` e `pg_get_viewdef` su dbdev, letti il 2026-11-09, dopo l'apply del giro 1.

### 11.1 Chi legge la distinta, e che cosa chiede

R2 elencava i 5 `*_riga_componenti_init`, i 5 `*_preview`, i due guard di coerenza e la vista. Il censimento ha preso
tutte le funzioni e le viste che nominano `catalogo.articoli_componenti`. Le domande che fanno sono di quattro forme, e
solo la prima è R2:

| Forma | Chi la fa | Filtro oggi | Nel giro |
| --- | --- | --- | --- |
| **L'insieme dei legami di un padre alla data D** | `vendite.fn_{preventivo,ordine,ddt,contratto}_riga_componenti_init`, `fn_offerta_eccezione_componenti_init` e i cinque `_preview` gemelli | `prodotto_id = padre AND COALESCE(attivo, TRUE) AND validita @> D`, ricopiato dieci volte | ✅ chiamano il BB |
| | `catalogo.vw_articoli_dettaglio.has_componenti_alla_data` | `EXISTS (… validita @> fn_data_operativa() AND attivo)`: è il BB a oggi | ✅ `EXISTS` sul BB, cronometrata |
| | ⚠️ BE `vendite/db/listini_repository.py` `list_bundle_preview` (`:1238`) | lo stesso filtro, scritto in Python | ➡️ BE13 (§11.6) |
| **Questo legame sta nella distinta del padre alla data D?** | `script.trgfn_componenti_guard_coerenza_bom`, sulle cinque tabelle `*_righe_componenti` dei documenti | il guard 2 legge il legame per `id` e `prodotto_id`; il guard 4 chiede `validita @> D` e **non guarda `attivo`** | ✅ il guard 4 chiede il BB (Q16) |
| **Il kit ha una distinta?** (senza data) | `script.fn_check_articolo_riga_su_contesto`, motivo `KIT_SENZA_COMPONENTI`, scritto due volte nello stesso corpo | `COALESCE(attivo, TRUE)`, nessuna validità | Q15 |
| | `catalogo.trgfn_articoli_guard_iva_bom_attiva` | solo `attivo` | ⛔ giro 3 (D4) |
| **Altro** (non è la distinta del catalogo alla data) | `fn_espandi_listino_versione`, `fn_contratto_kit_componenti`, `fn_documento_righe_preview`: leggono la distinta **del listino** o del documento e vanno sul legame solo per gli attributi. `fn_clona_versione_listino`: sovrapposizione del legame con il periodo della versione. `trgfn_listini_righe_comp_guard_coerenza_bom`: il periodo sta alla FK temporale. `trgfn_componenti_check_prezzo_obbligatorio`, `…_guard_obbligatorio`: leggono `obbligatorio` per `id`. I tre predicati di catalogo, il trigger d'immutabilità e il guard del legame | — | restano |

Fatti emersi:

* **Il guard dei documenti non guarda `attivo`.** Un componente di documento può puntare un legame spento, mentre gli
  init non lo scriverebbero mai. È una seconda risposta alla stessa domanda, e diverge già.
* **Rami irraggiungibili.** `COALESCE(ac.attivo, TRUE)` nei dieci init e preview (`attivo` è NOT NULL). Lo skip del guard
  4 con `v_data_rif IS NULL`: la colonna data delle cinque testate (`data`, e `validita_dal` per l'offerta) è NOT NULL.
  Si tolgono nello stesso giro, perché il giro apre quegli oggetti (§2.4).
* **Il futuro consumatore.** `analisi-simmetria-ordini-acquisto` (D-9, chiusa) prevede in `acquisti` i gemelli di
  `fn_ordine_riga_componenti_init` e `_preview`. Con il BB nascono senza copiare il filtro.
* **Fuori perimetro**, come osservazione: i cinque init sono gemelli interi, non solo nel filtro (il commento nel corpo
  lo dice: «Gemello di `fn_contratto_riga_componenti_init`»). Unirli è un altro tema. Il giro tocca solo il filtro.

### 11.2 Il BB

`catalogo.fn_distinta_alla_data(p_prodotto_id, p_data) RETURNS TABLE(id, componente_id, coeff_qta, obbligatorio,
esposizione_in_fattura)`, `LANGUAGE sql STABLE`, `BEGIN ATOMIC` (le dipendenze stanno in `pg_depend`, come i tre predicati
di catalogo). Risponde: i legami **attivi** del padre la cui `validita` contiene `p_data`.

* Con `p_data` NULL **non** risponde «la distinta di oggi»: risponde zero righe. Chi vuole oggi passa
  `fn_data_operativa()`, come la vista. Un NULL che vale «oggi» renderebbe la data implicita (Regola zero: un parametro
  non è un filtro nascosto).
* ⚠️ **Non `SETOF catalogo.articoli_componenti`**, come proposto nel censimento. Provato sullo scratch in `BEGIN …
  ROLLBACK`: una `BEGIN ATOMIC` che restituisce la riga della tabella muore («troppe poche colonne») appena la tabella
  prende una colonna. Con le colonne nominate l'`ADD COLUMN` non la tocca. Le colonne sono quelle di struttura che i
  chiamanti leggono; il resto si legge per `id`.
* **Espansione nel chiamante, provata:** con la data passata come colonna, parametro o chiamata diretta, `EXPLAIN` non ha
  `Function Scan`. Con la data in una sottoquery (`(SELECT script.fn_data_operativa())`) invece no.
* **La vista, cronometrata su dbdev** (811 articoli, letto il 2026-11-09, in `BEGIN … ROLLBACK`). Con
  `fn_data_operativa()` passata direttamente, la colonna costava circa 3,4 volte tanto (6,7 ms contro 2,0 ms), perché il
  giorno aziendale si ricalcola per ogni legame. Con il giorno calcolato una volta, in una sottoquery recintata
  (`CROSS JOIN (SELECT script.fn_data_operativa() AS data_operativa OFFSET 0) oggi`), il tempo torna quello di prima
  (2,0 ms). Stessi valori su tutti gli articoli.
* Il predicato «da oggi in poi» per i guard **c'è già**: `fn_articolo_padre_di_distinta_da_oggi` (giro 1). Il giro
  1-bis non ne fa un secondo.

### 11.3 Che cosa cambia nei chiamanti

| Oggetto | Cambio | Comportamento |
| --- | --- | --- |
| 5 init + 5 preview | `FROM catalogo.fn_distinta_alla_data(padre, p_data_riferimento) ac JOIN catalogo.articoli a …` al posto del filtro; via il `COALESCE` | Uguale |
| `vw_articoli_dettaglio` | `has_componenti_alla_data` = `EXISTS (SELECT 1 FROM catalogo.fn_distinta_alla_data(a.id, oggi.data_operativa))`, con il giorno in una sottoquery recintata (§11.2) | Uguale; la vista oggi non ha opzioni (`reloptions` vuoto, letto il 2026-11-09): il `CREATE OR REPLACE` non ne perde |
| `script.trgfn_componenti_guard_coerenza_bom` | Il guard 4 chiede se il legame è nell'insieme del BB alla data della testata; via lo skip su data NULL | **Cambia** (Q16): un legame spento è rifiutato dal guard con `E_DOC_COMPONENTE_BOM_NON_VALIDA`. Prima lo rifiutava comunque, a fine istruzione, il vincolo differito generato `…_a10_articoli_componenti_…` (`dbops.trgfn_child_requires_active_parent`, `E_ATTIVO_PADRE_NON_ATTIVO`): il rifiuto non è nuovo, lo sono il momento e il codice |
| `script.fn_check_articolo_riga_su_contesto` | Solo se Q15 dice di cambiare la finestra; le due copie del motivo nello stesso corpo diventano una | Secondo Q15 |

### 11.4 Le decisioni di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q15 ✅ | Il motivo `KIT_SENZA_COMPONENTI` della check guarda «almeno un legame attivo, in qualunque periodo». Un kit con la distinta tutta chiusa nel passato passa la check, e poi l'init lo rifiuta a ogni data da oggi in poi. La check non ha la data del documento. Che finestra prende? | **«Da oggi in poi»** (`fn_articolo_padre_di_distinta_da_oggi`), la stessa del guard flags (D9, «una finestra sola per i guard»). Il caso del documento con data passata resta all'init, alla sua data, come dice già il commento del corpo. ⚠️ Un kit con la sola distinta passata non si propone più nel picker — **✅ Tid, 2026-11-09: come da proposta** |
| Q16 ✅ | Il guard dei componenti di documento deve rifiutare un legame spento? | **Sì.** «Il legame sta nella distinta alla data» è una regola sola, e la risponde il BB. Oggi un legame citato da un documento non si spegne (`trgfn_prevent_deactivate_if_children`), quindi le righe esistenti non sono toccate. Il guard scatta su ogni UPDATE della riga componente: va provato che un UPDATE di prezzo su una riga valida passi — **✅ Tid, 2026-11-09: come da proposta** |
| Q17 ✅ | Il guard 1 di `trgfn_componenti_guard_coerenza_bom` («la riga padre è un composito», `E_DOC_RIGA_NON_COMPOSITO`). R3 lo contava come copia della regola del padre | **Resta.** Giudica la riga del **documento**, non la testata della distinta: dopo il giro 1 la regola del padre della distinta ha la sua sede in `fn_articolo_riga_contesto`. Sono due domande diverse. R3 si corregge così — **✅ Tid, 2026-11-09: come da proposta** |
| Q18 ✅ | ChangeSet: uno per documento (init e preview insieme) o uno per funzione? | **Uno per documento**: è lo stesso cambio sullo stesso documento, e il rollback rimette i due corpi insieme. Totale in §11.5 — **✅ Tid, 2026-11-09: come da proposta** |

### 11.5 I changeSet

Nove (Q15 cambia la finestra). Il BB prende il numero più basso, perché la vista lo chiama al CREATE.

| # | Fase / schema | Che cosa |
| --- | --- | --- |
| 1 | `20_code/catalogo` | `fn_distinta_alla_data`; COMMENT in un secondo `- sql:` (pgjdbc e `BEGIN ATOMIC`) |
| 2-6 | `20_code/vendite` | Preventivo, ordine, DDT, contratto, eccezione d'offerta: init e preview |
| 7 | `20_code/script` | `trgfn_componenti_guard_coerenza_bom` (Q16) |
| 8 | `20_code/catalogo` | `vw_articoli_dettaglio.has_componenti_alla_data` |
| 9 | `20_code/script` | `fn_check_articolo_riga_su_contesto` (solo con Q15) |

Corpi di partenza da `pg_get_functiondef`/`pg_get_viewdef` del giorno, `%TYPE` in firma e `DECLARE`, rollback = corpi di
prima. Prima di riscrivere `vw_articoli_dettaglio` si confronta il suo corpo col brief vicino
`brief-db-addebito-trasporto-ordine`, che tocca la stessa vista (`causale_onere_id`, `e_onere`).

**pgTAP previsti:**

* nuovo `catalogo/test-distinta-alla-data-v1`: un kit costruito con legami passati, in vigore, futuri e spenti; il BB a
  più date (compresi i due estremi chiusi della `validita`) e con `p_data` NULL; init e preview di un documento seguono
  il BB; il guard rifiuta il legame spento e lascia passare l'UPDATE di prezzo; Q15, se cambia;
* un presidio statico: nessun corpo di `vendite`/`script` ripete `articoli_componenti` con `validita @>` su
  `prodotto_id`. Così la copia non rientra;
* i pgTAP esistenti che toccano init, preview, guard e vista, con e senza l'SQL estratto in testa (come al §10.4).

### 11.6 Ricadute su BE e FE

| # | Che cosa |
| --- | --- |
| BE13 ✅ (2026-11-09) | `listini_repository.list_bundle_preview` (`:1238`) ricopia il filtro della distinta alla data: legge da `catalogo.fn_distinta_alla_data(%s, %s)` e tiene il `LEFT JOIN` sui prezzi del listino |
| BE14 ✅ (2026-11-09) | Un kit con la sola distinta passata non compare più fra gli articoli ammessi (Q15). Il FE non ha niente da fare: legge i motivi dalla check |
| BE15 ✅ (2026-11-09) | Il messaggio di `E_ARTICOLO_KIT_SENZA_COMPONENTI` cambia («non ha componenti in vigore da oggi in poi»): va allineata la frase di riserva in `backend/apps/core/services/error_messages_fallback.py:82`, e l'i18n se la ripete |

### 11.7 Che cosa è scritto (2026-11-09)

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261110-85` | `catalogo.fn_distinta_alla_data`, il BB (§11.2) |
| `20_code/vendite/20261110-86` … `-90` | Preventivo, ordine, DDT, contratto, eccezione d'offerta: init e preview leggono la distinta dal BB. Cambia solo il `FROM`: via il filtro e il `COALESCE` su `attivo` |
| `20_code/script/20261110-91` | `trgfn_componenti_guard_coerenza_bom`: il guard 4 chiede il BB (Q16); via lo skip con la data NULL; COMMENT, punto (4) |
| `20_code/catalogo/20261110-92` | `vw_articoli_dettaglio.has_componenti_alla_data` dal BB, col giorno calcolato una volta (§11.2). Colonne, ordine e COMMENT invariati |
| `20_code/script/20261110-93` | `fn_check_articolo_riga_su_contesto`: `KIT_SENZA_COMPONENTI` con `fn_articolo_padre_di_distinta_da_oggi` (Q15), un motivo costruito una volta e aggiunto dai due rami. COMMENT di questa funzione e di `fn_check_articolo_riga` riscritti secondo §5d |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_ARTICOLO_KIT_SENZA_COMPONENTI`: messaggio, causa e nota sulla finestra nuova. `E_DOC_COMPONENTE_BOM_NON_VALIDA`: causa e nota col legame spento |

I corpi di partenza vengono da `pg_get_functiondef` e `pg_get_viewdef` (`search_path = pg_catalog`) su dbdev, letti il
2026-11-09. Un generatore li ha cambiati con sostituzioni che dovevano trovare **esattamente un** punto, altrimenti si
fermava. Il rollback è il corpo di prima, con i COMMENT di prima dove cambiano.

**Residuo, non toccato:** negli init restano `COALESCE(v_is_composito, FALSE)` e `COALESCE(v_comp.obbligatorio, TRUE)`
su valori che non possono essere NULL, e i marcatori `rev …` nei commenti dei corpi. Va col giro 5 (§2.4). Nella check
anche il motivo `SOLO_COMPONENTE` è scritto in più rami: anche questo è giro 5.

### 11.8 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** I nove changeSet, con le `preConditions` trasformate in asserzioni, passano in una
  transazione.
* **Il pgTAP nuovo** `catalogo/test-distinta-alla-data-v1` (17 test): verde con l'estratto. Con il solo BB e i chiamanti
  di prima sono rossi esattamente i tre test dei cambi (11 legame spento, 14 kit con la sola distinta passata, 17 il
  presidio). Gli altri sono uguali per costruzione. Il presidio 17, sullo scratch di oggi, trova le undici copie: i dieci
  init e preview e la vista.
* **I pgTAP che toccano gli oggetti del giro** (55 file: init, preview, guard, check, picker, vista, componenti delle
  righe) con e senza l'estratto: stesse risposte, a parte il file nuovo. L'unico rosso,
  `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1` test 2, è uguale senza l'estratto ed è già nelle due
  baseline (`ASSERZIONE`).
* **Cambiato:** `catalogo/test-articoli-ammessi-picker-v1` test 24 cercava la frase vecchia del messaggio del kit; ora
  cerca quella nuova. Era verde nella prova solo perché l'estratto non ricarica i CSV: provato con la riga del messaggio
  aggiornata a mano nella stessa transazione, 26/26.
* **Guardrail:** `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch`,
  `sql_letterali`, `timestamp_senza_fuso` verdi; `pgtap_preambolo` segnala solo un file dell'altra sessione
  (`dbops/test-presidi-codici-corpo-leggibile-v1`). La soglia dei `throws_ok` senza discriminante resta 109: il test nuovo
  usa `throws_like`.
* **Non provato:** la corsa come app (la fa Tid dopo l'apply), il caricamento dei CSV e il migrate vero (pgjdbc). Il
  COMMENT del BB è in un `- sql:` separato dalla `BEGIN ATOMIC`, come vuole pgjdbc.

### 11.9 Doc e chiusura

* **Doc:** nuova `catalogo/manual/fn_distinta_alla_data.md`. Aggiornate `catalogo/manual/vw_articoli_dettaglio.md` (tolto
  il punto «riscrive la regola a mano») e `fn_articolo_padre_di_distinta_da_oggi.md` (il terzo lettore), poi
  `script/manual/trgfn_componenti_guard_coerenza_bom.md`, `fn_check_articolo_riga.md` e
  `fn_check_articolo_riga_su_contesto.md`. Nelle sei pagine `vendite/manual/` degli init e del preview del preventivo è
  cambiata solo la frase sul filtro: sono in formato vecchio, senza data, e restano così. La scheda auto-generata del BB
  nasce alla rigenerazione della doc dopo l'apply: fino ad allora i link `/dbzero/catalogo/funzioni/fn_distinta_alla_data`
  non hanno una pagina.
* **Da committare** (il giro 1-bis):
  * `20_code/catalogo/20261110-85`, `-92`; `20_code/vendite/20261110-86` … `-90`; `20_code/script/20261110-91`, `-93`;
  * `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (solo le quattro righe di questo giro: i due file hanno
    anche modifiche dell'altra sessione);
  * i pgTAP `catalogo/test-distinta-alla-data-v1.sql` (nuovo) e `catalogo/test-articoli-ammessi-picker-v1.sql`;
  * la doc del punto sopra e questo brief.
* **Numeri:** mentre il giro si scriveva, un file dell'altra sessione aveva anche lui il `-85`; è stato spostato al `-99`,
  poi Tid l'ha rinumerato `-94`. Nessun numero del giorno `20261110` è doppio.
* **Applicato** da Tid su dbdev e sullo scratch, pgTAP come app verdi (2026-11-09). **Committato** lo stesso giorno, con le
  schede auto-generate rigenerate dei soli oggetti del giro; delle modifiche dell'altra sessione ai due CSV non è entrato
  niente.

### 11.10 Il giro BE dei giri 1 e 1-bis (team BE, 2026-11-09, `9f540bea72`, PR #77)

> Scritta dal team BE nel suo commit; il merge `909e048c32` l'aveva persa, ripristinata dalla sessione DB il 2026-11-09.

* **BE8, BE15.** `error_policies_generated.py` rigenerato: `E_BOM_CHIUSURA_RETROATTIVA` (DATO_ERRATO),
  `E_BOM_LEGAME_CHIUSO` (CONFLITTO_STATO), più `E_CONTATTI_SOGGETTO_OBBLIGATORIO` del giro 12 di `dbops`; le altre
  differenze sono solo note. Ripieghi senza segnaposto per i tre codici nuovi; quello di
  `E_ARTICOLO_KIT_SENZA_COMPONENTI` ora dice «in vigore da oggi in poi». L'i18n FE non ripete nessuna delle frasi.
* **BE13.** `list_bundle_preview` legge da `catalogo.fn_distinta_alla_data(padre, data)`, col `LEFT JOIN` sui prezzi
  della versione; il filtro ricopiato è uscito. Prova sul DB vero:
  `vendite/tests/db/test_listino_kit_periodicita_db.py` test 8 (un legame futuro, una data prima della distinta).
  ⚠️ Un legame che ha prezzi bundle non si chiude: lo vieta la FK temporale
  `fk_listrighe_comp_articoli_comp_temporal`. Il team BE lo legge come modello, non come difetto; il test usa un legame
  futuro. La domanda è in §11.10.1.
* **BE11** (decisione di Tid, 2026-11-09: si ritira). Tolti il `DELETE` di
  `/catalogo/articoli/<id>/componenti/<comp_id>/`, `fn_delete_componente`, `CatalogoBomRepository.delete_componente`,
  `deleteArticoloComponente` del FE (senza chiamanti) e il loro test. Un legame si chiude con la PATCH su `valido_al`.
* **BE10.** Il CHECK `chk_articoli_composito_non_solo_componente` passa da `map_integrity_error` (che sostituisce il
  traduttore locale a testo degli articoli, compreso il duplicato del codice, ora col campo `codice`): 400
  `E_CATALOGO_VALIDATION` con la frase, senza campo (è la coppia a essere incoerente). Provato sul DB vero. Il form
  spegne l'interruttore dell'uno finché l'altro è acceso, col perché; nessun valore cambia da solo.
* **BE12.** Nel drawer dell'articolo la sezione della distinta (e «Gestisci distinta») la apre `puo_gestire_bom` del
  dettaglio, non il `form.is_composito` non ancora salvato. La lista lo faceva già.
* **BE9.** La data la legge già la vista; corretti i tre commenti di `ArticoloBomDrawer.vue` che dicevano
  «= `valido_dal`».
* **BE14.** Niente da fare.
* ⏭️ **Resta al team BE** (verifica della sessione DB, 2026-11-09): la doc API di BE9 e BE11 in
  `docs/it/backend/catalogo/manual/api_catalogo.md` (riga 601 e §4.4), vedi §5. Nessuna richiesta al DB nel commit.

#### 11.10.1 Per Tid: il legame con prezzi bundle non si chiude

`listini_righe_componenti` ha la FK temporale `fk_listrighe_comp_articoli_comp_temporal` (`articolo_componente_id`,
`PERIOD validita`) verso `articoli_componenti`: il periodo del prezzo bundle sta dentro quello del legame. Chiudere un
legame (giro 1: la fine da ieri in poi) mentre una riga di prezzo resta aperta oltre quella data si rifiuta, quindi prima
vanno chiusi i prezzi del componente in **tutte** le versioni di listino che lo prezzano. Sul modello la regola è
coerente (un prezzo non sopravvive al componente), ma incontra l'immutabilità della versione: fuori dalla BOZZA
`vendite.trgfn_listini_righe_comp_guard_immutabilita_v5` rifiuta l'UPDATE di `valido_al` e il DELETE, e lascia solo
`attivo = false`, che la FK temporale non guarda (letto dal corpo il 2026-11-09). Quindi un legame prezzato da una
versione non in bozza, con la riga di prezzo aperta oltre la data di chiusura, **non si chiude finché quella versione
esiste**: la fonte (la distinta) resta ferma per colpa di chi la legge (il listino).
Le strade: (a) è voluto, si chiude o sostituisce prima la versione di listino (ma la fine della versione non accorcia le
date delle sue righe: andrebbe verificato che basti); (b) il verbo di chiusura del legame chiude anche i prezzi bundle
aperti oltre quella data, in tutte le versioni, con conferma, come eccezione dichiarata all'immutabilità (la fine segue
la fonte, il prezzo non cambia); (c) altro, per esempio la FK sostituita da un giudizio alla data dei lettori.
Proposta della sessione DB: (b), perché la distinta è la fonte e `fn_distinta_alla_data` già ignora il componente fuori
distinta.

**Decisioni di Tid (2026-11-09): (b), con la conferma esplicita dell'operatore.**

* **Q19 — Che cosa si chiude.** Solo le righe di `listini_righe_componenti` del legame chiuso (`articolo_componente_id`)
  la cui fine va oltre la data di chiusura, in ogni versione che le prezza: prendono la stessa `valido_al` del legame.
  Né la versione né le altre righe si toccano; prezzo e IVA restano quelli. L'eccezione all'immutabilità della versione
  è di una colonna (la fine) e di una porta sola (il verbo di chiusura del legame).
* **Q20 — Mai in silenzio.** Lo schema dell'annullo con legami (D29, `E_DOC_ANNULLO_CON_LEGAMI`): al primo tentativo il
  verbo non chiude niente e risponde con un avviso e l'elenco delle righe di prezzo coinvolte (listino, versione, prezzo,
  fine che prenderebbero); l'operatore conferma richiamando il verbo con la dichiarazione delle righe viste; il DB
  chiude legame e prezzi nella stessa transazione, e rifiuta se l'elenco non è più quello dichiarato.
* **Q21 — Chi può.** Il verbo pretende **tutti e due** i diritti: la gestione della distinta e la modifica dei listini
  (guard nella prima riga del verbo). Chi non può toccare un listino non lo tocca nemmeno dalla distinta.
* **Q22 — Il prezzo del kit.** Il prezzo del padre è sempre la somma dei suoi componenti (non ha riga in
  `listini_righe`: `vendite/manual/listini_righe_componenti.md`), quindi da quella data il kit in quel listino scende del
  prezzo del componente tolto. Non blocca: lo dice la finestra di conferma, versione per versione.

Ricadute BE (al giro che la prende): il codice d'avviso nuovo nella mappa e la finestra di conferma, sul modello di quella
comune dell'annullo; la PATCH su `valido_al` del legame passa la dichiarazione. Il giro che la prende lo sceglie Tid.

## 12. Verifica di coerenza con guide e documenti, 2026-11-09

Richiesta di Tid dopo il giro 1-bis: c'è qualche guida o documento che contraddice i giri 1 e 1-bis, o il giro 2 che
viene? Ho cercato le regole una per una (non le parole), in `guide/`, `dev/manual/`, `backend/*/manual/`,
`dev/frontend/` e nelle pagine `manual/` di `vendite`, `script`, `magazzino` e `acquisti`. Ho escluso `work-done/`, che è
storia.

**Contraddizioni vere, corrette nello stesso giorno:**

* `dbzero/script/manual/trgfn_componenti_guard_obbligatorio.md`: per togliere un componente obbligatorio diceva di
  «disattivare la riga BoM o cambiarne il flag `obbligatorio`». Il database rifiuta tutte e due le cose: `obbligatorio` è
  un campo di struttura, e un legame citato da un documento non si spegne. Ora dice «chiudi il legame e inseriscine uno
  nuovo».
* `guide/gestione-ordini.md`, `gestione-ddt.md`, `gestione-preventivi.md`, `gestione-offerte-commerciali.md`: «kit senza
  componenti» ora è «kit senza componenti in vigore da oggi in poi» (Q15). Prima non era falso, ma era impreciso.

**Contraddizioni nella doc del backend** (`docs/it/backend/`, sede del team BE): `api_catalogo.md` su
`data_min_chiusura`, sulle regole della fine (§4.3) e sul `DELETE` (§4.4). Sono aggiunte a BE9 e BE11 (§5).

**Nessuna contraddizione** con:

* `linee-guida-sql.md` §7b (validità, `'[]'`), `dev/manual/modello-componenti-bom.md` (già riallineato nel giro 1) e
  `guide/gestione-listini.md` §5.3;
* il fermo dei temi trasversali sui documenti di vendita (`.codex/PROJECT_CONTEXT.md`): il giro 1-bis tocca tutti i
  documenti, ma lo fa con un building block comune, ed è il caso ammesso. Tid ha dato l'ok in Q8.

**Per il giro 2** (le unità): nessuna guida promette il «fattore 1 quando manca la conversione». Però le guide che
descrivono la quantità operativa (`gestione-preventivi.md` §2.2, `gestione-contratti.md`, `gestione-ordini.md`,
`gestione-ddt.md`) dicono solo «fattore fotografato sulla riga». Col giro 2 vanno completate con tre regole: il fattore
viene dalla mappatura dell'articolo o dalla conversione generale, alla data del documento, e senza nessuna delle due la
riga si rifiuta (Q7, Q13). `api_catalogo.md` documenta il lookup dei modi di arrotondamento, che Q4 ritira: è BE16.

## 13. Giro 2 — le unità di misura, 2026-11-09

Via di Tid il 2026-11-09, coi numeri dal `20261111-01`. Difetti del giro: D2 (Q7), D3 (Q4), D6, D8, D12, D13 (Q3), D14,
D15, D17, D22 (Q13); in più D7, che era del giro 3 ma vive nella funzione che questo giro apre, e D23, nuovo (§13.2).

### 13.1 Che cosa è scritto

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261111-01` | `trgfn_articoli_seed_uom_base`: la riga base nasce attiva o spenta come l'articolo (D7), senza `ON CONFLICT` (nominava il vincolo che `-02` sostituisce) |
| `00_schema/catalogo/20261111-02` | `articoli_uom_operativa`: `UNIQUE (articolo_id, uom_id, validita WITHOUT OVERLAPS)` al posto di quello senza tempo (D13); `chk_articoli_uom_operativa_base_fissa`, cioè riga base con fattore 1 e senza date (D12); ritirate `rounding_mode` e `require_lot` (D3, Q4); COMMENT di tabella e colonne |
| `20_code/catalogo/20261111-03` | `vw_articoli_uom_operativa_dettaglio` ricreata senza le due colonne, col GRANT e un COMMENT |
| `20_code/catalogo/20261111-04` | `trgfn_articoli_uom_operativa_guard_base` (nuovo) e il suo trigger: la riga base non cambia unità né articolo, non smette di essere la base, non si toglie, e non se ne crea una su un'altra unità (`E_UOM_RIGA_BASE_IMMUTABILE`). La cancellazione dell'articolo la porta via (D12) |
| `20_code/catalogo/20261111-05` | `fn_uom_operativa_alla_data` (nuovo, BB): la mappatura di un'unità per un articolo alla data, col fattore e le regole della quantità |
| `20_code/catalogo/20261111-06` | `fn_get_uom_factor(articolo, unità, data)`: base, mappatura alla data, conversione generale nei due versi; NULL senza data. Firma nuova (R1, D22) |
| `20_code/script/20261111-07` | `trgfn_qta_from_operativa`: fattore della riga, altrimenti `fn_get_uom_factor` alla data del documento; senza fattore `E_UOM_MISSING` (D2, Q7); `max_decimals` applicato (`E_QTA_OPERATIVA_DECIMALI`, D3); un UPDATE che cambia solo l'unità rilegge il fattore (D8) |
| `20_code/vendite/20261111-08` | I sei montaggi del trigger prendono la testata e la sua data (argomenti [2]-[4]) |
| `00_schema/vendite/20261111-09` | `factor_to_base` di `ordini_righe`, `ddt_righe`, `resi_righe` senza `DEFAULT 1` (D23) |
| `00_schema/catalogo/20261111-10` | `unita_misura_conversioni`: `ex_unita_misura_conversioni_coppia_no_overlap`, una conversione per coppia non orientata e periodo, al posto di `uq_uom_conv_no_overlap` (D14) |
| `20_code/catalogo/20261111-11` | `trgfn_uom_conversioni_guard_tipo`: `E_UOM_CONVERSIONE_TIPO_DIVERSO`, il nome della funzione nel log, le unità lette `FOR SHARE` (D6, D15) |
| `20_code/catalogo/20261111-12` | `trgfn_unita_misura_guard_tipo` (nuovo) al posto di `trgfn_unita_misura_guard_tipo_update`, ritirato col suo trigger: `E_UOM_TIPO_IN_USO` (D6) e `E_UOM_CALENDARIO_NON_TEMPO` (D17) |
| `80_data/changelog/20261111-13` | Ritirato il parametro `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE` (anche da `parameters.csv`) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_UOM_MISSING` riscritto («l'unità … non si converte nell'unità base … alla data …»); nuovi `E_QTA_OPERATIVA_DECIMALI`, `E_UOM_RIGA_BASE_IMMUTABILE`, `E_UOM_CONVERSIONE_TIPO_DIVERSO`, `E_UOM_TIPO_IN_USO`, `E_UOM_CALENDARIO_NON_TEMPO` (id 1466-1470) |

Corpi di partenza da `pg_get_functiondef`, `pg_get_viewdef` (`search_path = pg_catalog`) e `pg_get_triggerdef` su dbdev,
2026-11-09; rollback = gli oggetti di prima. I COMMENT nuovi o riscritti seguono §5d.

### 13.2 Fatti emersi

* **D23, nuovo: il `DEFAULT 1` del fattore.** Su `ordini_righe`, `ddt_righe` e `resi_righe` `factor_to_base` è NOT NULL
  con `DEFAULT 1`. Il default si applica prima dei trigger BEFORE: una riga inserita senza fattore arrivava al trigger
  con 1 già scritto, e la mappatura non si leggeva mai. È la regola di D2 («quando non so, 1») su altre tre tabelle. Il
  NOT NULL resta, perché lo soddisfa il trigger.
* **La data del documento.** Il trigger è montato su sei tabelle di righe, ognuna con la sua testata. In un BEFORE INSERT
  la riga non esiste ancora, quindi i risolutori per id (`script.fn_get_testata_id_di_riga`) non servono. Il montaggio
  dichiara tabella, colonna FK e colonna data, come fa il guard dei componenti di documento. L'offerta usa la decorrenza
  (`validita_dal`).
* **Le commesse non calcolano la quantità**: `commesse_attivita` la riceve dal documento sorgente, col suo fattore. Non
  c'è un trigger da cambiare, e restano fuori dal giro.
* **Il backend ha una copia della regola «unità ammessa per l'articolo»** (`listini_repository.py:968`: base o mappatura,
  senza le conversioni generali). È BE17.
* **`fn_get_uom_factor` aveva solo chiamanti BE** (due wrapper senza chiamanti): con la firma nuova smettono di
  funzionare. BE2 li ritira.

### 13.3 Le scelte dentro il giro (da guardare, Tid)

1. **`E_UOM_MISSING` riusato (Q7), con la frase riscritta.** Il suo secondo uso nel trigger non poteva scattare
   (`articolo_id` e `catalogo.articoli.uom_id` sono NOT NULL), quindi il codice ora ha un significato solo: «manca la
   conversione». La frase vecchia era tecnica («Unità misura mancante.(%s %s)»).
2. **D7 anticipato dal giro 3.** La funzione si apriva comunque per D13. Il fix è una riga.
3. **La riga base vale sempre**: il CHECK vieta anche le date sulla riga base, non solo il fattore diverso da 1. Una
   base con validità lascerebbe l'articolo senza base fuori dal periodo.
4. **Un guard solo per la tipologia di un'unità** (in uso nelle conversioni; TEMPO se si conta dal calendario): sono
   regole della stessa colonna. Per questo cambia nome (`_guard_tipo` invece di `_guard_tipo_update`).
5. **Il fattore scritto sulla riga si rispetta** anche all'INSERT: è la fotografia che i documenti derivati copiano dalla
   sorgente (ordine da preventivo, bolla da ordine). Il trigger non lo ricontrolla contro la mappatura.
6. **La conversione generale spenta occupa il periodo**: l'EXCLUDE non filtra `attivo`, come il vincolo che sostituisce.
7. **Testata che non si vede: il trigger non decide.** Il trigger gira prima della RLS e legge la testata con i diritti di
   chi scrive. Se non la vede (documento di un altro perimetro) o non c'è, la data è NULL e il trigger esce senza
   calcolare: rifiutano la RLS o la FK, che vengono dopo. La prima versione sollevava `E_UOM_MISSING` («… alla data —»),
   e i sei `rls/test-rls-*-satelliti` lo hanno visto (§13.4).
8. **L'unità base vale 1 anche senza data**: il suo fattore non dipende dal giorno. Per le altre unità
   `fn_get_uom_factor` senza data risponde NULL.

### 13.4 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** I tredici changeSet, con le `preConditions` come asserzioni, passano in una transazione.
  Nella prova sono state aggiunte a mano anche le righe nuove dei CSV dei codici, che nel migrate vero carica il mirror.
* **Il pgTAP nuovo** `catalogo/test-uom-fattore-e-regole-v1` (31 test): verde con l'estratto. Senza, la fixture muore al
  primo passo, sulla mappatura versionata che il vincolo di prima rifiuta (D13).
* **I pgTAP che toccano unità e quantità** (221 file) con e senza l'estratto. La prima corsa ha trovato:
  * i sei `rls/test-rls-*-satelliti`: la scrittura su un documento altrui si fermava sul trigger della quantità invece
    che sulla RLS. Corretto nel trigger (§13.3, scelta 7): verdi;
  * cambiati nel giro perché asserivano la regola di prima: `catalogo/test-fn-get-uom` (la firma con la data),
    `catalogo/test-articoli-vincoli-note-uom-overlap` 17-18 (il doppione è 23P01 del vincolo temporale; la seconda riga
    base la rifiuta il guard), `script/test-trgfn-guard-date-validita-v1` (le date stavano sulla riga base: ora su una
    mappatura costruita), `config/test-parameters-uom-defaults-cascade-v1` (la cascata degli override provata su
    `MAX_DECIMALS`, il parametro di `rounding_mode` è ritirato), `dbops/test-anti-overlap-enforcement-gate-v1` (i vincoli
    temporali nuovi);
  * seconda corsa, con le correzioni: rispetto alla corsa senza estratto cambiano solo i quattro file che provano le regole
    nuove (verdi con l'estratto, rossi o fermi senza). Tutti gli altri rossi sono uguali con e senza: quelli già noti
    alle baseline.
* **D15, a due sessioni.** Il guard nuovo non si può provare a due sessioni senza applicarlo, quindi si è provato il
  meccanismo su una riga vera di `catalogo.unita_misura`, sempre in `ROLLBACK`. Con un `UPDATE` della riga in volo, una
  lettura `FOR SHARE` aspetta (`lock_timeout` di 2 s scaduto: 2054 ms); nel verso opposto, lo stesso. Una lettura
  semplice, come quella del guard di prima, passa subito (38 ms).
* **Guardrail** verdi; `pgtap_preambolo` segnala solo un file dell'altra sessione.
* **Non provato:** la corsa come app, il caricamento dei CSV, il migrate vero (pgjdbc).
* **Dopo l'apply (Tid, 2026-11-09), come app:** `catalogo/test-articoli-vincoli-note-uom-overlap` arrivava a 20/20 e poi
  moriva nel cleanup in coda, una `DELETE` delle righe di unità operativa dell'articolo, riga base compresa, che il guard
  nuovo rifiuta. Nella prova come owner l'esito dei test non lo mostrava: il rosso era dopo l'ultimo `ok`. Tolta la `DELETE`,
  come quelle della distinta nel 2026-08: il file finisce in `ROLLBACK`, che toglie tutto. Nessun altro pgTAP cancella
  righe di unità operativa fuori da un'asserzione.
* **Dopo l'apply, su dbdev:** `catalogo/test-fn-get-uom` sceglieva tre unità fra quelle esistenti e ci scriveva delle
  conversioni; su dbdev fra due di loro c'è già una conversione nel verso opposto, che il vincolo nuovo (una per coppia)
  non lascia affiancare. Sullo scratch era verde perché la conversione non c'è: misurava la macchina. Ora il test
  costruisce le sue unità. Verde su dbdev e scratch; gli altri due pgTAP che scrivono conversioni le costruiscono già.
* **Chiusura:** Tid, 2026-11-09 — migrate applicato su dbdev e scratch, pgTAP come app verdi.
* **Trovato dopo la chiusura (Tid, 2026-11-09):** `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1` moriva prima
  del `plan` con `E_UOM_MISSING` («PZ non si converte in SMC per ART_TEST_FALLBACK»). La fixture dava a tutte le righe la
  prima unità attiva del catalogo, qualunque fosse l'articolo; prima del giro 2 il trigger lo lasciava passare, ora la
  riga FISSA senza fattore alla data si rifiuta (D2, Q7): la regola è giusta, la fixture misurava la macchina. Le baseline lo
  davano già rosso (`ASSERZIONE`, test 2), e quel rosso ha nascosto il nuovo nella corsa del giro. Corretto il pgTAP: ogni
  riga usa l'unità base del suo articolo (`catalogo.fn_get_uom_base`, fattore 1 a ogni data). Censiti gli altri pgTAP che
  prendono «la prima unità attiva» e stanno in baseline: solo `vendite/test-offerta-righe-espanse`, che la usa sulle sole
  righe di listino, dove il trigger non passa. Da rilanciare (Tid).

### 13.5 Ricadute su BE e FE

| # | Che cosa |
| --- | --- |
| BE1-BE4 ✅ (2026-11-09, §13.7; BE4 resta aperta per D19, giro 3) | Come in §5, ora sul giro applicato. BE4: i sei codici di §13.1 nella mappa degli errori generata e nell'i18n; `E_UOM_MISSING` ha una frase nuova |
| BE16 ✅ (2026-11-09) | `rounding_mode` e `require_lot` non ci sono più: il form e il servizio delle unità operative (`ArticoloUomForm.vue`, `RoundingModeSelect.vue`, `catalogo_service`, il lookup `rounding-modes` di `api_catalogo.md` §2.3) non le scrivono e non le leggono più. Fino ad allora un salvataggio che le nomina fallisce |
| BE17 ✅ (2026-11-09) | `listini_repository.py:968` (`uom_compatibile`) ricopia «l'unità vale per l'articolo» senza le conversioni generali: legge `catalogo.fn_get_uom_factor(articolo, unità, data) IS NOT NULL` |
| BE18 ✅ (2026-11-09) | Le mappature si versionano: «cambiare il fattore» di un'unità operativa diventa «chiudi e inserisci», e due periodi sovrapposti li rifiuta `uq_articoli_uom_operativa_no_overlap` (23P01). Anche una conversione generale nei due versi sovrapposta (`ex_unita_misura_conversioni_coppia_no_overlap`, 23P01): il servizio mappa i due vincoli a un messaggio |

### 13.6 Chiusura

* ⚠️ **Prima dell'apply su dbdev**: la riga base dell'articolo di prova `ART_TEST_BASE` (`catalogo.articoli_uom_operativa`
  id 9001) ha `valido_dal = 2026-01-01`, e `chk_articoli_uom_operativa_base_fissa` farebbe fallire `-02`. Va corretta a
  mano (`valido_dal` a NULL). Sullo scratch non ci sono righe così (letto il 2026-11-09). Come fatto datato: su dbdev 20
  articoli di prova non hanno nessuna riga base; il fattore della loro unità base resta 1, e il guard nuovo non lo
  cambia.
* **Doc** (scritta il 2026-11-09): nuove `catalogo/manual/fn_uom_operativa_alla_data.md`,
  `trgfn_articoli_uom_operativa_guard_base.md`, `trgfn_unita_misura_guard_tipo.md`; cancellata
  `trgfn_unita_misura_guard_tipo_update.md`; aggiornate in `catalogo/manual/` `fn_get_uom_factor`, `fn_get_uom_base`,
  `articoli_uom_operativa`, `unita_misura_conversioni`, `unita_misura`, `uom_tipi`, `trgfn_uom_conversioni_guard_tipo`,
  `trgfn_articoli_seed_uom_base`, `vw_articoli_uom_operativa_dettaglio`, `articoli`; riscritta allo standard
  `script/manual/trgfn_qta_from_operativa.md`; nelle guide `gestione-preventivi`, `gestione-ordini`, `gestione-ddt`,
  `gestione-contratti` la regola del fattore. Le schede auto-generate dei tre oggetti nuovi nascono dopo l'apply.
  ⚠️ Trovata e lasciata: `guide/gestione-contratti.md` (verso la riga 141) dice ancora che con la fonte «derivata dai
  componenti» la quantità la scrive il sistema, ma quella fonte è ritirata dal 2026-10-21. Va col giro 5.
* **Committato** (2026-11-09, su richiesta di Tid): i tredici changeSet; `codici_errore.csv`, `messaggi_errore.csv` e `parameters.csv` (solo le righe di
  questo giro); i pgTAP `catalogo/test-uom-fattore-e-regole-v1.sql` (nuovo), `catalogo/test-fn-get-uom.sql`,
  `config/test-parameters-uom-defaults-cascade-v1.sql`, `dbops/test-anti-overlap-enforcement-gate-v1.sql`,
  `catalogo/test-articoli-vincoli-note-uom-overlap.sql`, `script/test-trgfn-guard-date-validita-v1.sql`; la doc del punto
  sopra; la verifica di coerenza di §12 con le sue correzioni;
  questo brief.

### 13.7 Giro BE del giro 2 (team BE, 2026-11-09, da committare su `dev/backend-tid`)

#### 13.7.1 Che cosa è fatto

| # | Che cosa |
| --- | --- |
| BE16 | `rounding_mode` e `require_lot` fuori da repository (scrittura e proiezione), service, schema OpenAPI e form. Ritirati il lookup `GET /catalogo/lookup/rounding-modes/` (view, rotta, `fn_list_uom_rounding_modes`, `_ROUNDING_MODE_*`), `lookupUomRoundingModes` e `RoundingModeSelect.vue` (file cancellato, nel piano approvato da Tid), le chiavi i18n e il parametro letto dal form. Una PATCH o una POST che li nomina è un 400. `api_catalogo.md` §2.3 e §3.2 riscritti |
| BE1 | `is_base` **non si scrive più**: fuori dalla whitelist di repository e service (400 se arriva). La riga base nasce con l'articolo e il guard rifiuta ogni altra strada, quindi offrirla voleva dire offrire solo un rifiuto. Ritirato il controllo parziale di `:844`; il CHECK `chk_articoli_uom_operativa_base_fissa` ha la sua frase (`_UOM_OPERATIVA_CHECK`). La DELETE della riga base riceve `E_UOM_RIGA_BASE_IMMUTABILE` dal DB, intatto fino al middleware |
| BE1, form | ⚠️ **Difetto trovato nel form**: un `watch` ricavava `is_base` dal fattore (`fattore 1 → base`). Un'unità con fattore 1 che base non è (una confezione da uno, un sinonimo) finiva marcata base, e col guard nuovo il salvataggio veniva rifiutato. Ritirato: il form mostra «Base» in sola lettura sulla riga base, e lì spegne fattore e date (il CHECK) |
| BE2 | Ritirati `get_uom_base` / `get_uom_factor` del repository: nessun chiamante, e il secondo chiamava la firma vecchia |
| BE3 | Verificato: nessun service delle righe azzera `factor_to_base` al cambio d'unità. `contratti_service` accetta `factor_to_base: null`, che il trigger ora riempie alla data (D8). Niente da ritirare |
| BE4 | Policy rigenerata (`genera_error_policies`: le sole sette voci dei giri, nessun codice del DB oltre git) e ripieghi senza `%s` per i sei codici di §13.1 e per `E_SOGGETTO_ID_FISCALE_IMMUTABILE`; `E_UOM_MISSING` riscritto. Il FE non ha i18n per codice: la frase arriva dal DB |
| BE17 | `get_articolo_uom_validation` legge `catalogo.fn_get_uom_factor(articolo, unità, data) IS NOT NULL` alla **decorrenza della versione** (`listini_versioni.valido_dal`, NOT NULL); il rifiuto accende `uom_id` |
| BE18 | `_UOM_OPERATIVA_UNIQUE` su `uq_articoli_uom_operativa_no_overlap` (frase «chiudere quella in vigore prima di aprirne una nuova», senza campo). Le conversioni passano dal BB `map_integrity_error` per nome (`ex_unita_misura_conversioni_coppia_no_overlap`, `chk_uom_conv_no_self`, le due FK col campo): via il riconoscimento dal testo («overlap», «foreign») e il ramo `E_GENERICO` della tipologia, che ora ha il suo codice |

#### 13.7.2 Le prove

* **Sul DB vero** (`ZEROERP_TEST_DB_E2E=1`, casi costruiti, transazione annullata):
  `catalogo/tests/db/test_vincoli_catalogo_db` da 3 a 8 test (mappatura doppia e versionata, chiudi e inserisci, riga base
  fissa, riga base che non si toglie, conversione nel verso opposto, tipologie diverse);
  `vendite/tests/db/test_listino_uom_compatibile_db` (nuovo, 4 test: base, nessuna conversione, conversione generale,
  mappatura chiusa prima della decorrenza: gli ultimi due sono i casi che la copia vecchia sbagliava).
* Test unitari: `test_catalogo_service` (rounding ritirati; 4 nuovi), `test_catalogo_api`, `test_listini_service`.
* **Suite backend intera sul DB vero** (7221 test): tre rossi, tutti fixture che scrivevano ciò che i giri 1 e 2 ora
  rifiutano, corretti nello stesso giro. `catalogo/tests/db/test_articoli_ammessi_db` 1 e 2 aprivano il picker della
  distinta su un padre non composito (BE12); il test 1 per di più leggeva «un articolo attivo qualunque», una popolazione:
  ora il padre composito si costruisce. `core/tests/db/test_date_validita_guard_comune_db` 7 metteva le date sulla riga
  base: ora su una mappatura costruita, come il pgTAP gemello. Rilanciati: verdi.
* `genera_error_policies --check` pulito, presidi delle policy verdi, ruff, mypy (0 rilievi), vitest 1104/1104, build FE.

#### 13.7.3 Domande per Tid — ✅ risposte il 2026-11-10 (Q23-Q25, §6): il lavoro è in §15

1. **Il fattore di una mappatura si cambia sul posto?** Il DB lo lascia fare (nessun lock su `factor_to_base` delle righe
   non base), e il form lo lascia modificabile. Col modello «chiudi e inserisci» (D13, Q3) il cambio sul posto riscrive il
   passato di `fn_uom_operativa_alla_data`. Se il fattore di una mappatura va fermato, serve il lock a DB (o la riga in
   `lock_columns_conditional`, con il suo guard): allora il form lo spegne da `non_editable_fields`, senza copia.
2. **BE17, la data.** La compatibilità della riga di listino si chiede alla decorrenza della versione. Una mappatura che
   comincia dopo la decorrenza, o che finisce durante la versione, non è vista: è il giorno da cui il prezzo vale. Se la
   regola deve essere «per tutto il periodo della versione», va scritta a DB.
3. **Fuori dal giro, da guardare:** `commesse_repository._map_pushable_row` mette `factor_to_base = 1` quando la riga
   sorgente lo ha NULL. Le colonne nullable sono quelle di `contratti_righe`, `preventivi_righe`,
   `offerte_commerciali_eccezioni`, e lì NULL vuol dire «quantità già nella base», quindi 1 è giusto. È però la forma di
   D2 («quando non so, 1») in un posto del backend, e `commesse_attivita.factor_to_base` ha ancora `DEFAULT 1` (la forma
   di D23). §13.2 tiene le commesse fuori dal giro: lo segnalo, non lo tocco.

## 14. Giro 3 — i guard degli articoli e la chiusura del legame coi prezzi, 2026-11-09

Via di Tid il 2026-11-09, numeri dal `20261111-25`; dentro il giro anche Q19-Q22 (§11.10.1, 7-quater). Due parti:
**A**, la chiusura del legame coi prezzi bundle (scritta e provata, §14.1-§14.4); **B**, i difetti del giro come da §7
(D4 + D21, D5, D18, D19, D20, R5: §14.5).

### 14.1 Parte A — che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261111-25` | `vendite.fn_prezzi_legame_oltre_la_fine(legame, fine)`: i prezzi bundle oltre la fine, con l'esito (`CHIUDE`, `TOGLIE`, `BLOCCA`), `importo_per_kit` e `nel_perimetro`. `SECURITY DEFINER`, `BEGIN ATOMIC`: fuori perimetro esce solo che il prezzo c'è |
| `20_code/script/20261111-26` | `script.fn_check_legame_distinta_chiudibile`: i due motivi che vietano (`E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE`, `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI`) |
| `20_code/vendite/20261111-27` | `vendite.trgfn_listini_righe_comp_guard_immutabilita_v5`: la porta della chiusura del legame (GUC `zeroerp.legame_distinta_chiudi` = id del legame, col proprietario), sulla sola `valido_al` e solo per accorciarla |
| `20_code/catalogo/20261111-28` | `catalogo.trgfn_articoli_componenti_block_modifica_struttura`: una fine che lascia fuori dei prezzi, prima ciò che vieta, poi l'avviso `E_BOM_CHIUSURA_CON_PREZZI` (prima moriva sulla FK temporale con un 23503 grezzo) |
| `20_code/catalogo/20261111-29` | `catalogo.fn_chiudi_legame_distinta(legame, fine, prezzi_confermati)`: il verbo (permesso, blocco, ciò che vieta, permesso sui listini, conferma, prezzi, legame) |

Codici nuovi (`codici_errore.csv`, `messaggi_errore.csv`, id `1471` … `1474`): `E_BOM_CHIUSURA_CON_PREZZI`
(CONFLITTO_STATO), `E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE` (CONFLITTO_STATO), `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI`
(DATO_ERRATO), `E_BOM_LEGAME_NOT_FOUND` (NON_TROVATO).

### 14.2 Le scelte dentro la parte A (da guardare, Tid)

1. **Prezzi in listini di un'altra azienda: la chiusura si rifiuta.** Fatto emerso nel censimento: la distinta è comune
   a tutte le aziende, i listini hanno la RLS per emittente. Q19 diceva «in ogni versione che le prezza»; la lettura
   che ne dà Q21 («chi non può toccare un listino non lo tocca nemmeno dalla distinta») è il rifiuto, col numero dei
   prezzi e senza dire quali. Lo sblocca chi vede quei listini.
2. **Prezzi di una versione non in bozza che cominciano dopo la fine: la chiusura si rifiuta** e dice la prima fine
   ammessa (l'inizio più tardo). Non si accorciano (periodo vuoto) e non si cancellano (la versione non è in bozza). In
   bozza invece si tolgono, e la finestra lo dice (esito `TOGLIE`).
3. **Il diritto sui listini si chiede solo se ci sono prezzi da toccare.** Un legame senza prezzi chiede solo quello
   sul catalogo, e nessuna conferma. I due diritti sono il livello TUTTO su `catalogo.articolo` e su `vendite.listino`
   (gli oggetti che il backend usa per gli stessi endpoint), dal guard `script.fn_guard_livello`.
4. **La conferma è un conteggio**, come l'annullo con legami (`p_prezzi_confermati`): il verbo blocca legame e prezzi
   `FOR UPDATE` e la confronta col numero di adesso.
5. **L'avviso parte anche dall'UPDATE diretto** (il PATCH di oggi su `valido_al`): il guard della distinta è il primo
   tentativo, il verbo è la conferma. Così il contratto del backend cambia poco: sull'avviso apre la finestra, alla
   conferma chiama il verbo.
6. **`importo_per_kit` = prezzo per il coefficiente del legame**: quanto il componente pesa su un kit, al prezzo della
   riga. È la cifra che la finestra mostra per versione (Q22).

### 14.3 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

* Tutte e cinque compilano; le preCondition tornano (`0`, `1`, `1`, `2`, `3`). `plpgsql_check` non segnala niente
  sulle quattro plpgsql.
* pgTAP nuovo `catalogo/test-chiudi-legame-con-prezzi-v1.sql` (21 test), col seed delle sole quattro righe dei codici:
  **20/21**. Il test 10 («la porta senza il proprietario non apre») è rosso da owner per costruzione, perché la
  porta si apre proprio al proprietario: è dichiarato nel file, verde atteso come app.
* Regressione: 53 pgTAP che nominano `articoli_componenti`, `listini_righe_componenti` o un `E_BOM_`, più 14 presidi
  trasversali (riferimenti morti, `search_path` delle DEFINER, catalogo dei messaggi, codici, bersagli, COMMENT al
  presente…), ciascuno senza e con l'SQL estratto: tutti uguali, tranne `script/test-rubinetto-primo-motivo-v1`
  test 5, il conteggio esatto delle funzioni che chiamano l'helper del primo motivo: da 48 a 50 (il guard e il verbo),
  aggiornato con la nota. ⚠️ Fino all'apply quel test è rosso sullo scratch (vede 48).

### 14.4 Parte A — doc e ricadute

* **Doc:** nuove `catalogo/manual/fn_chiudi_legame_distinta.md`, `vendite/manual/fn_prezzi_legame_oltre_la_fine.md`,
  `script/manual/fn_check_legame_distinta_chiudibile.md`; aggiornate
  `catalogo/manual/trgfn_articoli_componenti_block_modifica_struttura.md` e
  `vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5.md`. Le schede auto-generate dei tre oggetti nuovi
  nascono dopo l'apply.
* **BE19** (al team BE, dopo l'apply): «Chiudi riga» della distinta. Il PATCH su `valido_al` resta il primo tentativo;
  sull'avviso `E_BOM_CHIUSURA_CON_PREZZI` (CONFLITTO_STATO, campo `valido_al`, contesto `prezzi` e `versioni`) il FE apre
  una finestra di conferma che elenca i prezzi da `vendite.fn_prezzi_legame_oltre_la_fine(legame, fine)` (listino,
  versione, stato, inizio, fine, prezzo, `importo_per_kit`, esito: «si chiude» / «si toglie»), e alla conferma il BE
  chiama `catalogo.fn_chiudi_legame_distinta(legame, fine, numero di prezzi visti)`. I quattro codici nuovi nella mappa
  generata e nei ripieghi. `E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE` e `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI` sono rifiuti sul
  campo, senza finestra.

### 14.5 Parte B — che cosa è scritto

| changeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261111-30` | D4 + D21 (Q6): `trgfn_articoli_guard_iva_bom_attiva` diventa un CONSTRAINT TRIGGER `AFTER UPDATE OF iva_id`, `DEFERRABLE INITIALLY DEFERRED`, `WHEN` l'IVA cambia; giudica l'IVA di adesso dell'articolo e dei partner sui legami attivi da oggi in poi; aliquota vuota «—»; il contesto porta `campo` e il `tx_id` |
| `20_code/catalogo/20261111-31` | D5 (R4, Q5): si ritirano `trgfn_articoli_guard_listino_se_composito` e il suo trigger |
| `20_code/catalogo/20261111-32` | D18: `fn_articolo_usato` confronta ogni FK sulla chiave a cui punta (su `id` come prima; verso un'altra chiave o composita col join sull'articolo; la colonna PERIOD fuori) |
| `20_code/catalogo/20261111-33` | R5: `catalogo.fn_articolo_flag_etichetta(colonna)`, il nome leggibile delle otto colonne strutturali |
| `20_code/catalogo/20261111-34` | D20 (Q10): `fn_articolo_colonne_struttura` è la dichiarazione (costante, `IMMUTABLE`), non legge più le regole del form |
| `20_code/catalogo/20261111-35` | D20, R5: il guard dell'uso cerca la prima colonna cambiata nella dichiarazione, l'etichetta dal BB |
| `20_code/catalogo/20261111-36` | R5: il guard degli oneri prende l'etichetta dal BB; COMMENT al presente |
| `20_code/catalogo/20261111-37` | D19: la porta della struttura valida NOT NULL e tipo di ogni valore prima di scrivere (`E_PARAMETRO_INVALIDO` col nome leggibile); COMMENT al presente |

Nessun codice nuovo nella parte B.

### 14.6 Le scelte dentro la parte B (da guardare, Tid)

1. **D20: la dichiarazione è una funzione costante**, e le regole del form restano righe di
   `dbops.lock_columns_conditional`, confrontate col pgTAP. Il form non può leggere una funzione per colonna (il
   registro è per colonna), quindi «un posto» vuol dire: la porta e il guard leggono la dichiarazione, l'elenco
   `UPDATE OF` e il form sono copie presidiate. Una regola del form spenta ora non tocca la porta.
2. **D4: «legami da oggi in poi»** è scritto nel guard come `validita && [oggi, ∞)`. Le tre funzioni di D28
   (`fn_articolo_*_di_distinta_*`) rispondono un boolean e non danno i partner con la loro IVA: per questo il filtro
   resta nella query, come in `fn_check_articolo_riga`.
3. **D4, i pgTAP:** girano con i vincoli `IMMEDIATE`, quindi lì il guard scatta a fine istruzione. Il cambio in due
   istruzioni si prova differendo il solo vincolo (`SET CONSTRAINTS catalogo.trg_articoli_a10_guard_iva_bom_attiva_upd`,
   col nome qualificato).
4. **D19: la frase di `E_PARAMETRO_INVALIDO` porta il nome leggibile** («gestito a lotti»), non il nome della
   colonna, che resta nel contesto (`campo`). La frase della colonna estranea («non correggibili da qui: …») non è
   del giro e resta com'è.
5. **D5:** il codice `E_LISTINO_RIGA_COMPOSITO_VIETATO` resta: lo solleva il lato riga.

### 14.7 Le prove della parte B

* SQL estratto `-30` … `-37` sopra quello della parte A: compila, preCondition tutte come attese, `plpgsql_check`
  pulito sulle cinque plpgsql toccate.
* pgTAP nuovi: `catalogo/test-iva-kit-a-fine-transazione-v1.sql` (7/7) e `catalogo/test-articolo-usato-chiave-fk-v1.sql`
  (3/3, dichiarato `pgtap-runner: owner`: crea una tabella con una FK verso il codice, e una tabella temporanea non
  può avere una FK verso una permanente).
* Riscritto `catalogo/test-articolo-colonne-struttura-v1.sql` (13/13): 10-12 rovesciati (presidiavano proprio il
  legame fra porta e form che Q10 ritira), il 4 chiede che il guard legga la dichiarazione, l'8 diventa
  `E_PARAMETRO_INVALIDO`, nuovo l'8-bis (NOT NULL).
* Regressione con A + B: tutti i pgTAP di `catalogo`, quelli che scrivono `catalogo.articoli` o nominano i codici e
  le funzioni del giro, la lista della parte A e i 14 presidi trasversali: **88 uguali** con e senza; diverge solo il
  rubinetto, che col conteggio aggiornato passa da rosso a verde.

### 14.8 Doc, ricadute, chiusura

* **Doc (parte B):** nuova `catalogo/manual/fn_articolo_flag_etichetta.md`; cancellata
  `catalogo/manual/trgfn_articoli_guard_listino_se_composito.md` (oggetto ritirato); aggiornate
  `fn_articolo_colonne_struttura`, `fn_articolo_correggi_struttura`, `fn_articolo_usato`,
  `trgfn_articoli_guard_iva_bom_attiva`, `trgfn_articoli_guard_struttura_se_usato`,
  `trgfn_articoli_guard_onere_natura`, `articoli` (sezioni «che cosa oggi non copre» chiuse, note di migrazione).
  Gli indici `catalogo/index.md` e `index.ci.md` nominano ancora il guard ritirato: sono generati, si allineano alla
  rigenerazione dopo l'apply.
* **BE7 → BE20** (al team BE, dopo l'apply): il rifiuto `E_BOM_IVA_DISCORDANTE` arriva **a fine transazione**. In
  autocommit è l'UPDATE stesso; dentro un `transaction.atomic()` arriva all'uscita del blocco, non sull'istruzione:
  il servizio dell'articolo lo mappa lì. Il form può ora cambiare l'IVA di un kit e dei suoi componenti in una
  transazione.
* **BE4** (già in §5): `E_PARAMETRO_INVALIDO` dalla correzione della struttura ha ora il `campo` nel contesto.
* **Da committare:** i tredici changeSet `20261111-25` … `-37`; le quattro righe nuove dei due CSV dei codici; i
  pgTAP nuovi `catalogo/test-chiudi-legame-con-prezzi-v1`, `test-iva-kit-a-fine-transazione-v1`,
  `test-articolo-usato-chiave-fk-v1`; i pgTAP toccati `catalogo/test-articolo-colonne-struttura-v1` e
  `script/test-rubinetto-primo-motivo-v1`; la doc di §14.4 e §14.8; questo brief.
* **Prima dell'apply:** niente da correggere a mano. Dopo: i pgTAP come app (il test 10 di
  `test-chiudi-legame-con-prezzi-v1` verde solo così), la rigenerazione delle schede dei sei oggetti nuovi o
  ritirati.

### 14.9 Apply e commit, 2026-11-10

* Tid ha applicato il giro 3 su dbdev e scratch; i pgTAP come app sono verdi, compreso il test 10 di
  `test-chiudi-legame-con-prezzi-v1` e il rubinetto col conteggio 50.
* Corretto prima della corsa: `test-articolo-usato-chiave-fk-v1` dichiarava `pgtap-runner: owner` senza la riga
  `pgtap-runner-motivo`, che `scripts/testpgtap.sh` pretende.
* Commit del giro 3 su `dev/db-tid` (2026-11-10), coi file di §14.8. Restano: la rigenerazione delle schede
  auto-generate (indici di `catalogo` col guard ritirato), BE19 e BE20 al team BE.
* CI-Validate rossa sul push (2026-11-10), controllo i18n: le due `reason_key` di
  `script.fn_check_legame_distinta_chiudibile` (`catalogo.distinta.azione_reason.prezzi_altre_aziende`,
  `….prezzi_dopo_la_fine`) non erano nei locales. Andavano chieste al FE nello stesso giro (linee-guida-sql §12.3);
  aggiunte dalla sessione DB in `frontend/src/locales/it.json` ed `en.json`, accanto a
  `catalogo.distinta.componente_reason.*`. Il team BE/FE ne riveda il testo con BE19.

## 15. Giro 2-bis — le tre decisioni del giro BE, 2026-11-10

Le tre domande di §13.7.3 hanno risposta (Q23-Q25, §6). Diventano D24-D26: lavoro **DB**, con le ricadute BE in §15.4.
Numeri dal `20261111-47` (Tid, 2026-11-10). Q26-Q31 decise (§6); via allo sviluppo (Tid, 2026-11-10). D27 nasce dal censimento (§15.5).

> ⚠️ **Rinumerato dalla sessione DB il 2026-11-10.** Scritto dal team BE come §14, Q19-Q21 e BE19-BE21 mentre il
> giro 3 (§14) usava già §14, Q19-Q22 (§11.10.1) e BE19-BE20: qui diventano §15, Q23-Q25 e BE21-BE23. D24-D26 restano.

### 15.1 D24 — Il fattore di una mappatura si cambia sul posto (Q23: bloccato)

* **Fatto.** `articoli_uom_operativa` non ha lock su `factor_to_base` delle righe non base: un UPDATE lo cambia, e
  `fn_uom_operativa_alla_data` / `fn_get_uom_factor` rispondono il valore nuovo **anche per le date passate**. Il modello
  di Q3 (versionata, chiudi e inserisci) ha già la strada per cambiare il fattore: la riga nuova.
* **Correzione.** Il fattore di una mappatura scritta non si cambia: `script.trgfn_lock_columns`, con un codice suo
  (proposta: `E_UOM_FATTORE_IMMUTABILE`, la frase dice «chiudere la mappatura e aprirne una nuova»). La riga base è già
  ferma dal CHECK `chk_articoli_uom_operativa_base_fissa`: il lock non la cambia.
* **Da guardare nella stessa colonna di ragionamento (proposta della sessione DB, poi Tid):**
  * **`uom_id`** oggi non è bloccato neppure lui: cambiare l'unità di una mappatura sul posto riscrive il passato come il
    fattore. Proposta: bloccato insieme, stesso codice o uno gemello.
  * **Le date.** `valido_al` resta modificabile, perché chiudere è la strada. Spostare `valido_dal`, o chiudere nel
    passato una mappatura già in vigore, riscrive il passato come il fattore: è la stessa domanda di Q1 per la distinta.
    Proposta: la stessa risposta di Q1.
* **Prova (pgTAP):** UPDATE del fattore su una mappatura costruita → il codice; chiudi e inserisci → passa; la riga base
  resta del CHECK.

### 15.2 D25 — L'unità della riga di listino deve valere per tutto il periodo della versione (Q24)

* **Fatto.** Oggi la regola sta solo nel backend (BE17, §13.7.1), alla **decorrenza** della versione: una mappatura che
  finisce durante la versione passa, e da quel giorno il listino dà un prezzo in un'unità che per l'articolo non si
  converte. Una regola del modello non sta nel backend.
* **Correzione.** Regola a DB: l'unità della riga è convertibile per l'articolo **in ogni giorno** del periodo della
  versione (`valido_dal` … `valido_al`; `valido_al` NULL vuol dire «senza fine»). «Convertibile» è quello che dice
  `catalogo.fn_get_uom_factor` (base, mappatura dell'articolo, conversione generale): la regola si scrive **sul BB del
  periodo**, non come copia — la sessione DB valuta se serve un BB «unità convertibile per tutto il periodo», da
  `fn_get_uom_factor` o accanto a lui (regola del 2: lo leggono il guard del listino e, oggi, il backend).
* **Tutte e due le direzioni (simmetria).** La regola si rompe da tre lati, e ognuno va presidiato:
  1. la riga di listino scritta o cambiata (il guard della riga);
  2. il periodo della versione allungato o riaperto (`valido_al` spostato o tolto);
  3. il catalogo che cambia sotto: una mappatura chiusa, una conversione generale chiusa o spenta, mentre un listino
     vivo la usa.
  Il terzo lato è il più facile da dimenticare: va deciso se rifiutare la chiusura o no, e la sessione DB lo propone a
  Tid con le alternative.
* **Prova (pgTAP):** i tre lati, con articolo, unità, mappature e versione costruiti; versione senza fine; unità base
  sempre valida.

### 15.3 D26 — Le commesse: il fattore 1 per difetto (Q25)

* **Fatto.** `commesse_attivita.factor_to_base` ha `DEFAULT 1`: la forma di D23, che il giro 2 ha tolto da `ordini_righe`,
  `ddt_righe` e `resi_righe`. In più il backend (`vendite/db/commesse_repository.py`, `_map_pushable_row`) scrive 1 quando
  la riga sorgente ha il fattore NULL. Oggi è giusto, perché NULL sulla sorgente vuol dire «quantità già nella base»; ma
  se arriva una riga senza fattore in un'unità che base non è, l'1 la fa passare come se lo fosse (3 cartoni → 3 pezzi),
  senza rifiuto. È D2 («quando non so, 1»).
* **Correzione (DB).** Via il `DEFAULT 1`. La regola «senza fattore la quantità è nella base» si scrive a DB, in un posto:
  una riga di `commesse_attivita` senza fattore prende 1 **solo se** l'unità è la base dell'articolo, altrimenti si
  rifiuta (codice del giro 2, `E_UOM_MISSING`, se il significato coincide; la sessione DB lo verifica). La sessione DB
  censisce prima chi scrive in `commesse_attivita` (push dal documento sorgente e altre porte), perché ognuno lo
  attraversa.
* **Prova (pgTAP):** riga senza fattore nella base → 1; riga senza fattore in un'altra unità → il rifiuto; riga col
  fattore → quello scritto, come la fotografia di §13.3 punto 5.

### 15.4 Ricadute su BE e FE (team BE, quando il giro è applicato)

| # | Che cosa |
| --- | --- |
| BE21 | D24: il lock entra in `vw_non_editable_fields`. Verificare che il dettaglio delle unità operative passi `non_editable_fields` al form (la prop `nonEditableFields` di `ArticoloUomForm.vue` c'è; va provato chi la riempie). Policy e ripiego del codice nuovo. Test sul DB vero: UPDATE del fattore → il codice col campo |
| BE22 | D25: `ListiniRepository.get_articolo_uom_validation` (BE17) si ritira, o legge il BB del periodo se ne nasce uno. Il rifiuto del guard arriva col campo `uom_id`. Policy e ripiego dei codici nuovi. `test_listino_uom_compatibile_db` riscritto sui tre lati |
| BE23 | D26: `_map_pushable_row` smette di scrivere 1: il NULL passa al DB, che decide. Il test delle commesse prova il rifiuto per una riga senza fattore fuori dalla base |

### 15.5 Censimento in sola lettura (sessione DB, 2026-11-10, scratch `zeroerp_ruoli` col giro 3 applicato)

**Le fonti del fattore.** `catalogo.fn_get_uom_factor(articolo, unità, data)`: 1 per l'unità base a ogni data; poi la
mappatura dell'articolo alla data (`fn_uom_operativa_alla_data`, `attivo` e `validita @> data`); poi la conversione
generale alla data, nei due versi (`attivo` e `validita @> data`). L'unità base dell'articolo (`articoli.uom_id`) è già
bloccata (`trgfn_lock_columns`): non c'è un quarto lato.

**D24 — le porte della mappatura oggi.** `articoli_uom_operativa` ha il guard della riga base, la regola del periodo e
nient'altro: `factor_to_base`, `uom_id`, `valido_dal`, `attivo` si cambiano sul posto, e la riga si cancella. Il BE le
usa tutte: `catalogo_uom_repository.update_uom_operativa` e `delete_uom_operativa`. Fuori da Q23 e Q26 restano due
porte che riscrivono il passato nello stesso modo: lo **spegnimento** (`attivo = false`: `fn_uom_operativa_alla_data` non
la vede più, a nessuna data) e la **cancellazione**.

**Le conversioni generali hanno lo stesso difetto.** `unita_misura_conversioni` non ha lock: il BE ne aggiorna sul
posto `fattore`, `valido_dal`, `valido_al`, `attivo` (`CONVERSIONI_UPDATE_COLUMNS`). Cambiare il fattore di «cartone →
pezzo» riscrive il passato di tutti gli articoli che non hanno una mappatura loro.

**D25 — i tre lati.**

1. *La riga.* `listini_righe` ha `articolo_id`, `uom_id` e `listino_versione_id` già bloccati
   (`E_LISTINO_RIGA_IDENTITA_IMMUTABILE`). Restano l'INSERT, in BOZZA e in ATTIVA (la rettifica), e la riaccensione
   (`attivo` da false a true). Nessun guard di unità oggi.
2. *Il periodo.* `valido_dal` e `valido_al` si cambiano in BOZZA; in ATTIVA solo `valido_al`, e solo dalla porta dei
   verbi (`zeroerp.listino_versione_fine`); in CHIUSA niente. In più, l'attivazione
   (`script.fn_check_versione_listino_attivabile`): una BOZZA scritta bene si può rompere sotto, dal catalogo, prima di
   essere attivata (il terzo lato conta solo le ATTIVE, Q27). Va un motivo nuovo lì.
3. *Il catalogo.* Mappatura e conversione: chiusura, spegnimento, cancellazione; giudizio a fine transazione.

Le righe bundle (`listini_righe_componenti`) non hanno un'unità: fuori.

**D26 — chi scrive il fattore.** Il «quando non so, 1» non è in un posto, è in cinque:

| Dove | Che cosa |
| --- | --- |
| `commesse_attivita.factor_to_base` | `NOT NULL DEFAULT 1` |
| `attivita_fatturabili.factor_to_base` | `NOT NULL DEFAULT 1`. L'unico writer, `fn_emit_attivita_fatturabili_da_commessa`, copia il fattore della commessa: il default non serve a nessuno |
| `vendite.fn_upsert_commessa_attivita` | parametro `p_factor_to_base DEFAULT 1` e `COALESCE(p_factor_to_base, 1)` nell'INSERT |
| `vendite.fn_aggiungi_onere_commessa` | passa `p_factor_to_base => 1`, a qualunque unità |
| `vendite.fn_accredita_riga_reso` | `COALESCE(v_cmp.factor_to_base, 1)` |
| BE `commesse_repository._map_pushable_row` | `Decimal(1)` se la sorgente non ha il fattore (BE23) |

`commesse_attivita` non ha `script.trgfn_qta_from_operativa`: la quantità base (`quantita`, NOT NULL) la porta chi
scrive, e il fattore è una fotografia. La regola del giro 2 per le righe dei documenti è già scritta in quel trigger:
senza fattore, `fn_get_uom_factor` alla data del documento; senza neanche quello, `E_UOM_MISSING`.

### 15.6 Che cosa è scritto (sessione DB, 2026-11-10)

Diciannove changeSet, `20261111-47` … `-65`; nulla applicato.

| # | Schema | Che cosa |
| --- | --- | --- |
| `-47` | catalogo | **BB nuovo** `fn_uom_fonti_conversione(articolo, unità)`: le fonti del fattore coi loro periodi (base, mappatura, conversione generale nei due versi), con la priorità. È la regola del 2: la leggono le due letture qui sotto e i lettori di periodo di D25 |
| `-48`, `-49` | catalogo | `fn_uom_operativa_alla_data` e `fn_get_uom_factor` leggono il BB; il comportamento non cambia |
| `-50` | catalogo | `fn_uom_primo_giorno_non_convertibile(articolo, unità, periodo)`: il primo giorno del periodo senza una fonte, per differenza di multirange |
| `-51` | catalogo | `fn_uom_conversione_nome`: il nome leggibile di una mappatura o di una conversione, per i messaggi |
| `-52` | catalogo | **D24, D27** `trgfn_uom_guard_storia`, montato sulle due tabelle: identità (unità, articolo, fattore, inizio) mai (`E_UOM_STORIA_IMMUTABILE`); la fine non prima di ieri (`…_CHIUSURA_RETROATTIVA`) e non su una già finita (`…_CHIUSA`); spegnere, riaccendere, cancellare solo senza giorni passati (`…_IN_VIGORE`). La riga base resta del suo guard |
| `-53` | vendite | lettore DEFINER `fn_listini_attivi_uom_non_convertibili`: le righe delle versioni ATTIVE scoperte da un cambio di catalogo, con `nel_perimetro` (Q27: le altre aziende contate, non nominate) |
| `-54` | catalogo | **D25 terzo lato** `trgfn_uom_guard_listini_attivi`, constraint trigger differiti su chiusura, spegnimento e cancellazione (`E_UOM_CHIUSURA_CON_LISTINI_ATTIVI`) |
| `-55`, `-56` | vendite | **D25 primo lato**: il lettore della riga e il guard della riga di listino, su INSERT e riaccensione (`E_LISTINO_UOM_NON_CONVERTIBILE`, campo `uom_id`) |
| `-57` | vendite | **D25 secondo lato**: il guard del periodo della versione, quando il periodo nuovo non sta dentro il vecchio |
| `-58` | script | `fn_check_versione_listino_attivabile`, motivo 4: una bozza rotta dal catalogo non si attiva (`reason_key` `vendite.listini.azione_reason.uom_non_convertibile`, nei locales) |
| `-59`, `-60` | script | **BB nuovo** `fn_fattore_uom_alla_data` (fattore o `E_UOM_MISSING`, con porta e campo del chiamante); `trgfn_qta_from_operativa` lo usa al posto della sua copia |
| `-61` | vendite | **D26** `trgfn_attivita_fattore_alla_data` su `commesse_attivita` e `attivita_fatturabili`: il fattore scritto si rispetta, senza lo legge alla data dell'attività, senza neanche quello `E_UOM_MISSING` |
| `-62` | vendite (00_schema) | via il `DEFAULT 1` dalle due colonne |
| `-63` … `-65` | vendite | `fn_upsert_commessa_attivita` (`p_factor_to_base DEFAULT NULL`), `fn_aggiungi_onere_commessa`, `fn_accredita_riga_reso`: nessun 1 al posto del fattore |

Fuori dai changeSet:

* **Codici**: sei nuovi, id 1475-1480 (`E_UOM_STORIA_IMMUTABILE`, `…_CHIUSA`, `…_CHIUSURA_RETROATTIVA`, `…_IN_VIGORE`,
  `E_LISTINO_UOM_NON_CONVERTIBILE`, `E_UOM_CHIUSURA_CON_LISTINI_ATTIVI`), e la nota di `E_UOM_MISSING` aggiornata.
* **Q31**: quattro righe in `80_data/sql/dbops/automazione_attivo_eccezioni.csv`. Il mirror le carica al migrate;
  i trigger già generati li toglie il motore in testa al giro successivo (§15.10).
* **Locales**: `vendite.listini.azione_reason.uom_non_convertibile` in `it.json` ed `en.json`. Il FE ne riveda il
  testo con BE22.

### 15.7 Le scelte dentro il giro (da guardare, Tid)

1. **Q31 esteso alle conversioni generali.** Nel proporre Q31 avevo scritto che le conversioni non bloccano lo
   spegnimento delle unità: era sbagliato. Lo scratch ha il block su `uom_from_id` e su `uom_to_id`, e con Q29 il
   problema è identico. Le due FK sono in eccezione con lo stesso motivo. Se preferisci tenerle legate, si tolgono
   due righe dal CSV prima dell'apply.
2. **D26 anche su `attivita_fatturabili`.** Q30 nominava le due colonne. Il trigger è montato su tutte e due:
   l'emissione copia il fattore, ma senza il trigger il default tolto lascerebbe un NOT NULL secco come rifiuto.
3. **L'inizio di una mappatura futura è fermo anch'esso.** Q26 diceva «di una mappatura in vigore». Il guard tratta
   l'inizio come identità, come il fattore. Una mappatura futura sbagliata si cancella e si riscrive: si può, perché
   non ha giorni passati.
4. **La riaccensione di una mappatura con giorni passati è rifiutata**, come lo spegnimento (Q28). Riaccenderla
   cambierebbe il fattore delle date passate.
5. **Un INSERT con `valido_dal` passato non è giudicato.** Scrivere oggi una mappatura che vale da un mese è una
   correzione del passato. Oggi passa, come per la distinta (giro 1). Se va chiuso, è un giro a parte.
6. **Il cambio dell'id di un'unità in cascata (`ON UPDATE CASCADE`) è rifiutato** dal guard della storia, perché
   cambia l'unità della riga. Gli id non si cambiano, quindi non ha effetti pratici; è annotato qui.
7. **Le righe che cancellano l'articolo o l'unità passano**: il guard lascia andare la riga se il padre non c'è più
   (la cascata).

### 15.8 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

**Compilazione.** I diciannove changeSet compilano, e i rollback rimettono i corpi vivi.

**Q31.** Le quattro righe del registro, con `fn_ritira_attivo_eccezioni()`, ritirano otto trigger. Dopo, un
articolo con una mappatura chiusa si spegne e si riaccende, e un'unità con mappature si spegne, con le mappature
intatte.

**pgTAP nuovi**, tutti verdi:

* `catalogo/test-uom-storia-v1`: 21/21;
* `vendite/test-listino-uom-periodo-v1`: 18/18, su due aziende;
* `vendite/test-commesse-attivita-fattore-alla-data-v1`: 7/7.

**Regressione.** 269 file pgTAP, ognuno corso senza e con il giro: il seed dei codici, l'SQL estratto e le righe di
Q31. Diverge solo dove ci si aspetta:

* `dbops/test-punti-canale-campo-v1`: rosso senza il giro (la voce nuova) e verde con.
* `catalogo/test-fn-riattiva-articolo-v1`: senza il giro muore allo spegnimento, perché ora conta su Q31; con il
  giro resta rosso il test 1, rosso anche prima. Il file è nel cantiere dell'altra sessione (la frase senza tabella,
  S-BE-1). La sessione DB ha cambiato solo il figlio che blocca, da mappatura a descrizione aggiuntiva, con una nota
  datata.

Diciotto file sono rossi allo stesso modo con e senza il giro: preesistenti sullo scratch, nessuno toccato dal giro.

**Le fixture corrette nella regressione** (27 file, con nota datata 2026-11-10):

* quasi tutte scrivevano un'unità a caso accanto a un articolo a caso, e passavano grazie all'1 per difetto: ora
  usano l'unità della base, o una mappatura per la seconda unità;
* in più, i test che spegnevano o spostavano mappature (`test-fn-get-uom`, `test-uom-fattore-e-regole-v1`,
  `test-trgfn-guard-date-validita-v1`) e il test 29 di `test-attivita-fatturabili` (fattore 1 esplicito).

**Guardrail.** Verdi sui diciannove YAML: COMMENT al presente, letterali SQL, timestamp senza fuso, DDL su trigger
generati, preCondition su seed, runOnChange, GRANT batch, preambolo pgTAP, v1 congelato, i18n.

### 15.9 Doc e ricadute

**Pagine `manual/`.**

* Nuove, undici:
  * catalogo: `fn_uom_fonti_conversione`, `fn_uom_primo_giorno_non_convertibile`, `fn_uom_conversione_nome`,
    `trgfn_uom_guard_storia`, `trgfn_uom_guard_listini_attivi`;
  * vendite: `fn_listini_attivi_uom_non_convertibili`, `fn_listino_versione_riga_uom_non_convertibile`,
    `trgfn_listini_righe_guard_uom_periodo`, `trgfn_listini_versioni_guard_uom_periodo`,
    `trgfn_attivita_fattore_alla_data`;
  * script: `fn_fattore_uom_alla_data`.
* Riallineate:
  * catalogo: `articoli_uom_operativa`, `unita_misura_conversioni`, `fn_get_uom_factor`, `fn_uom_operativa_alla_data`;
  * script: `trgfn_qta_from_operativa`, `fn_check_versione_listino_attivabile`;
  * vendite: `commesse_attivita`, `attivita_fatturabili`, `listini_righe`, `listini_versioni`,
    `fn_upsert_commessa_attivita`, `fn_aggiungi_onere_commessa`, `fn_accredita_riga_reso`;
  * dbops: `automazione_attivo_eccezioni`;
  * la guida `automazione-db.md` (§4.2, la tabella delle eccezioni).
* Da rigenerare dopo l'apply: le schede auto-generate.

**Debito documentale notato, fuori giro.** La tabella delle eccezioni, nella pagina `manual/` e nella guida, non
elencava le sedici righe di `ui` del giro 7-bis di brief-db-revisione-dbops.

**Ricadute BE e FE**, oltre a §15.4:

| # | Che cosa |
| --- | --- |
| BE21 | In più: `delete_uom_operativa` e lo spegnimento di una mappatura in vigore ora sono rifiutati (`E_UOM_STORIA_IN_VIGORE`). L'interfaccia propone la chiusura. Lo stesso vale per le conversioni generali (`CONVERSIONI_UPDATE_COLUMNS`): fattore, unità e inizio non si cambiano più |
| BE22 | Il rifiuto della riga ha campo `uom_id`. Quello del periodo ha campo `valido_al` o `valido_dal`. Quello del catalogo arriva al commit, con codice `E_UOM_CHIUSURA_CON_LISTINI_ATTIVI`. Il motivo 4 di attivazione ha la sua `reason_key` |
| BE23 | `fn_upsert_commessa_attivita` ha `p_factor_to_base` vuoto per difetto: il backend non deve più passare 1 |
| BE24 | Q31: articolo e unità si spengono anche con mappature e conversioni. Se il backend spegneva le mappature prima dell'articolo, quel passo va tolto: ora, su una mappatura in vigore, sarebbe rifiutato |
| BE25 | Policy e ripiego dei sei codici nuovi |

### 15.10 Apply e commit

* **Apply (Tid)**: il migrate su dbdev e scratch. Poi la **convergenza dell'automazione ATTIVO**
  (`dbops.fn_run_automations_attivo`, o il job serale). È lei che toglie i quattro block e i quattro require delle FK
  in eccezione. Fino ad allora `test-uom-storia-v1` (test 19-21) e `test-automazione-attivo-eccezioni-v1` (test 9)
  restano rossi.
* **Presidio rosso fino all'apply**: `test-punti-canale-campo-v1` sullo scratch, perché la voce è passata a
  `script.fn_fattore_uom_alla_data`.
* **Commit** su richiesta di Tid, dopo l'apply.

**Esito (2026-11-11).** Tid ha applicato il giro 2-bis su dbdev e scratch, e i pgTAP come app sono verdi. Il commit
è su `dev/db-tid`, coi file del giro. I file dell'altra sessione (`20261111-40` … `-46`, il bersaglio del guard ATTIVO,
brief-db-revisione-dbops) restano fuori; i cinque file che le due sessioni hanno toccato tutte e due
(`messaggi_errore.csv`, `test-fn-riattiva-articolo-v1`, i due indici di `script`, `automazione-db.md`) entrano interi,
anche con le righe dell'altra sessione (decisione di Tid). Restano al team BE le voci BE21-BE25.
### 15.10-bis Giro BE del giro 2-bis (team BE, 2026-11-11, da committare su `dev/backend-tid`)

Fatto nell'ordine BE25 → BE23 → BE22 → BE21 + BE24, a giro 2-bis applicato su dbdev (verificato sul catalogo dei
changeSet e degli oggetti, 2026-11-11).

#### 15.10-bis.1 Che cosa è cambiato

| # | Che cosa | Dove |
| --- | --- | --- |
| BE25 ✅ | I sei codici nella policy generata (`genera_error_policies`: il catalogo dei codici del DB coincide col CSV in git, classe per classe) e nel ripiego, con frasi senza `%s` | `error_policies_generated.py`, `error_messages_fallback.py` |
| BE23 ✅ | `_map_pushable_row` passa il fattore com'è, anche NULL: lo decide `vendite.trgfn_attivita_fattore_alla_data`. `PushableRow.factor_to_base` è `Decimal \| None` | `commesse_repository.py` |
| BE22 ✅ | Ritirati `_validate_riga_articolo_uom` e `ListiniRepository.get_articolo_uom_validation`: articolo attivo, unità attiva e unità convertibile li giudica il DB (famiglia ATTIVO su `articolo_id` e `uom_id`, guard del periodo). La copia guardava la sola decorrenza. Il testo della `reason_key` `uom_non_convertibile` dice «rifare quel prezzo in un'altra unità» al posto di «cambiare l'unità»: l'unità di una riga è ferma (lock) | `listini_service.py`, `listini_repository.py`, i due locales |
| BE21 ✅ | Unità, fattore e inizio di mappature e conversioni entrano nei gap dichiarati di `_NON_EDITABLE_DB_GAPS` (vedi §15.10-bis.3, punto 1); il form delle unità operative e il drawer delle conversioni li spengono da `non_editable_fields`. Le whitelist di scrittura (`CONVERSIONI_UPDATE_COLUMNS`, quella delle unità operative) **non** si stringono: sarebbero una seconda sede della regola del guard. Il form rimanda i campi fermi invariati, e il guard giudica il cambiamento, non la presenza (provato) | `catalogo_service.py`, `ArticoloUomForm.vue`, `ConversioneUomDrawer.vue` |
| BE24 ✅ | Niente da togliere: né il backend né il frontend spengono le mappature prima dell'articolo o dell'unità | — |

#### 15.10-bis.2 Le prove

* Nuovi, sul DB vero: `vendite/tests/db/test_commessa_fattore_senza_db.py` (3: il binding del NULL; senza fattore nella
  base vale 1; fuori dalla base il rifiuto), `catalogo/tests/db/test_uom_storia_db.py` (5: la chiusura col form intero
  passa; fattore della mappatura e della conversione fermi; una mappatura in vigore non si cancella, una futura sì).
* Riscritto `vendite/tests/db/test_listino_uom_compatibile_db.py` sui **tre lati** (6): unità base, senza conversione,
  conversione generale senza fine, mappatura che finisce dentro la versione (il caso che la copia BE lasciava
  passare), periodo allungato oltre la mappatura, mappatura chiusa sotto un listino ATTIVO (differito, con
  `SET CONSTRAINTS … IMMEDIATE`).
* Riallineati: `test_scritture_dinamiche_db` (la conversione si chiude, non cambia fattore: era rosso dal giro 2-bis),
  i due test dei gap in `test_catalogo_service`, i test di `test_listini_service` che mockavano il metodo ritirato.
* FE: `ArticoloUomForm.spec.js` nuovo (2).
* Suite `apps.catalogo` + `apps.vendite` col DB vero: 2859 test verdi. Vitest `src/catalogo` + `src/vendite` 228,
  `src/core` 653, verdi. ruff, mypy, `genera_error_policies --check`, `check_i18n_keys` puliti.

#### 15.10-bis.3 Alla sessione DB: tre segnalazioni

1. **`dbops.vw_non_editable_fields` non vede `catalogo.trgfn_uom_guard_storia`.** La vista legge i soli
   `trgfn_lock_columns` (`vw_lock_columns_vivi`); il guard della storia ferma unità, fattore e inizio, e le sue colonne
   sono già scritte nei suoi argomenti. Fino ad allora il backend le dichiara come gap
   (`_NON_EDITABLE_DB_GAPS`), che si tolgono quando la vista le legge. Il brief diceva «il lock entra in
   `vw_non_editable_fields`» (BE21): con il guard al posto del lock non è entrato.
2. **`catalogo.vw_articoli_uom_operativa_dettaglio.puo_eliminarsi`** è falsa solo sulla riga base. Una mappatura con
   giorni passati ora non si cancella (`E_UOM_STORIA_IN_VIGORE`), ma la capability la dice cancellabile: il pulsante
   resta acceso e il rifiuto arriva dopo il clic, con la frase giusta («si chiude»). Proposta: la capability legge la
   stessa regola del guard, con un motivo suo. Lo stesso vale per lo spegnimento (`attivo`), se una capability lo
   dichiara.
3. **`vendite.fn_batch_upsert_commessa_attivita`** riporta per ogni riga rifiutata la sola frase (`error`), senza il
   codice: un rifiuto `E_UOM_MISSING` dal push si riconosce solo dal testo. Non è del giro 2-bis, è emerso nel test di
   BE23.

**Esito delle segnalazioni** (fusione col ramo DB, 2026-11-11): la 1 e la 2 sono G1 e G2 di §15.11, scritte e applicate
(§15.11.1); le ricadute sul BE sono BE21-a … f (passo 7-octies). La 3 resta aperta (passo 7-decies).

### 15.11 Verifica del lavoro BE e delle sue ricadute sul DB (sessione DB, 2026-11-11)

**Il lavoro BE committato.** Dopo il giro 2-bis l'unico commit BE è `ff93395d5e` (PR #84), cioè il giro BE del
giro 3 (§14.10). BE21-BE25 non sono ancora su nessun ramo.

* **Il giro BE del giro 3 non lascia niente al DB.**
  * Il PATCH del legame è stato ritirato (§14.10.3). Nessun oggetto DB serviva solo a lui:
    `vw_articoli_componenti_dettaglio` pubblica solo la capability della chiusura, e `ui` non ha azioni di riga
    sulla lista `catalogo.articolo_componenti`.
  * L'override `confirm_and_retry` di `E_BOM_CHIUSURA_CON_PREZZI` è una scelta d'interfaccia scritta a mano, ed è
    voluta (`error_ui_overrides.py`). Il DB non la porta.
  * §14.10.4 (le sigle doppie) era già chiusa dalla rinumerazione in testa a §15.
* **Il giro 2-bis lascia due buchi nel contratto che BE21 legge.** Sono buchi del DB, non del BE.

**G1 — Le colonne ferme della storia non escono in `non_editable_fields`.** BE21 dice «il lock entra in
`vw_non_editable_fields`», ma il giro 2-bis non ha messo un lock: la regola 1 di `catalogo.trgfn_uom_guard_storia`
(unità, articolo, fattore, inizio: mai) è un lock **incondizionato** scritto dentro un guard.
`dbops.vw_lock_columns_vivi` riconosce solo i trigger su `script.trgfn_lock_columns`, quindi il form non lo vede.
Il BE colma questo genere di buco a mano, in `_NON_EDITABLE_DB_GAPS` (`catalogo_service.py:113`), e già oggi ci
tiene `articoli_uom_operativa.uom_id` e `unita_misura_conversioni.uom_from_id`/`uom_to_id`. Con il giro 2-bis
quella lista dovrebbe crescere: `factor_to_base` e `valido_dal` da una parte, `fattore` e `valido_dal`
dall'altra. Diventerebbe una seconda sede di una regola del DB (regola del 2), e lo stesso commento del BE dice
che queste voci si tolgono quando il DB le dichiara.

* **Proposta.** La regola 1 passa a `script.trgfn_lock_columns`. Le colonne si registrano in
  `dbops.automation_lock_columns`, col codice `E_UOM_STORIA_IMMUTABILE`, e il guard della storia tiene solo le
  regole 2 e 3 (attivazione e cancellazione, la fine). Il form legge tutto da `vw_non_editable_fields`, e il BE
  ritira le due voci di `_NON_EDITABLE_DB_GAPS`.
* **Da pesare.**
  * Il messaggio di `E_UOM_STORIA_IMMUTABILE` ha un `%s` per il nome della conversione, mentre
    `trgfn_lock_columns` passa la colonna. La frase va riscritta sulla colonna, oppure serve un codice gemello.
  * Si perde il bersaglio `ARTICOLO` del contesto.
  * Il lock vale anche sulla riga base. Lì unità e fattore sono già fermi, e `valido_dal` non conta, perché
    `fn_get_uom_factor` dà 1 alla base a ogni data.
  * Va riverificato il ramo «il padre non c'è più» del guard, cioè l'`ON UPDATE CASCADE` di §15.7 punto 6: un
    lock rifiuta allo stesso modo.
* **Alternativa scartata.** Far riconoscere a `vw_lock_columns_vivi` anche il guard della storia: la vista
  smetterebbe di dire «i trigger di lock» e comincerebbe a dire «i trigger che conosco».

**G2 — La capability della mappatura dice il falso, e quella della conversione non c'è.**

* In `vw_articoli_uom_operativa_dettaglio`, `puo_eliminarsi` è `NOT is_base`. Dal giro 2-bis il guard rifiuta la
  cancellazione e lo spegnimento di ogni mappatura con giorni passati (`E_UOM_STORIA_IN_VIGORE`). Il FE offre
  quindi «elimina» su righe che il DB rifiuta.
* BE21 vuole che l'interfaccia «proponga la chiusura», ma la vista non ha `puo_chiudersi`, `data_min_chiusura`,
  `data_default_chiusura` né il motivo. Se li calcolasse il FE, sarebbe una copia del guard.
* `unita_misura_conversioni` ha le stesse regole, ma non ha una vista: la lista `catalogo.conversioni_uom` ha
  `vista_sql` NULL, e il repository legge la tabella.
* **Proposta.** La capability la calcola **un** BB di catalogo, sulle regole 2 e 3 del guard: si può cancellare,
  si può spegnere, si può chiudere, la prima fine ammessa (la più tarda fra `valido_dal` e ieri), la fine di
  difetto, il motivo. Lo leggono `vw_articoli_uom_operativa_dettaglio` e una vista nuova
  `vw_unita_misura_conversioni_dettaglio`, che diventa la `vista_sql` della lista. Il guard e il BB devono dire
  la stessa cosa. Si sceglie nel giro se il guard legge il BB, oppure se un pgTAP li confronta su righe costruite.
* **Vicino da guardare.** `vw_articoli_componenti_dettaglio` ha la stessa forma per la distinta. Le regole però
  non coincidono: un legame con una fine futura non si sposta più, una mappatura sì. Quindi non è una copia da
  estrarre; si verifica nel giro.

**Il piano del giro (Q32 e Q33 decise il 2026-11-11; censimento in sola lettura).**

* **G1.**
  * Otto righe in `80_data/sql/dbops/automation_lock_columns.csv`, col codice `E_UOM_STORIA_IMMUTABILE`:
    `articoli_uom_operativa` (`articolo_id`, `uom_id`, `factor_to_base`, `valido_dal`) e
    `unita_misura_conversioni` (`uom_from_id`, `uom_to_id`, `fattore`, `valido_dal`). Sono le colonne che oggi il
    guard riceve in `TG_ARGV` (`20261111-52`). Il trigger lo genera l'automazione, alla convergenza, come per Q31.
  * Un changeSet nuovo per `trgfn_uom_guard_storia`, senza la regola 1 e senza argomenti, e i due trigger rimontati.
    ⚠️ C'è una finestra fra il migrate e la convergenza in cui le colonne non le blocca nessuno. Il guard nuovo
    non deve uscire prima del lock: o si toglie la regola 1 a convergenza fatta, o la si tiene finché il lock è
    vivo.
  * La frase di `E_UOM_STORIA_IMMUTABILE` va riscritta sul `%s` che passa `trgfn_lock_columns`, cioè la colonna.
* **✅ Il campo: (a), Tid, 2026-11-11.** `trgfn_lock_columns` mette la colonna nel contesto con la chiave `column`, non
  `campo`. Registra anche `'database'` come area e `TG_NAME` (il trigger) come funzione. Il guard di oggi manda
  `campo`. Spostando la regola, il rifiuto perde il campo che BE21 vuole evidenziare. Le strade:
  * **(a)** `trgfn_lock_columns` aggiunge `campo` (uguale a `column`). Tocca il BB di tutti i lock, e quindi il
    canale del campo di ogni codice di lock (`E_CODICE_NON_MODIFICABILE` e gli altri) e i suoi presidi;
  * **(b)** si accetta il rifiuto senza campo. Il form mostra il lucchetto prima, quindi l'errore arriva solo da
    chi scrive senza passare dal form.
* **G2.**
  * Un BB `catalogo.fn_uom_conversione_capability(valido_dal, valido_al, attivo)`, che rende `puo_eliminarsi`,
    `puo_spegnersi`, `puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura` e il motivo, sulle regole 2 e 3
    del guard.
  * Il guard lo legge per le regole 2 e 3, così le due risposte non possono divergere.
  * `vw_articoli_uom_operativa_dettaglio` lo proietta; sulla riga base `puo_eliminarsi` resta falso, col suo motivo.
  * Nasce `vw_unita_misura_conversioni_dettaglio`, con i codici delle due unità, e diventa la `vista_sql` della
    lista 22 `catalogo.conversioni_uom` (CSV `ui.lista_definizione`).
* pgTAP: `test-uom-storia-v1` riallineato (la regola 1 dal lock, il campo secondo la scelta); un test nuovo per la
  capability, con le righe costruite (futura, in vigore, finita, base), che confronta BB e guard.

**Ricadute su BE21.** Con G1 il BE ritira le voci di `_NON_EDITABLE_DB_GAPS` invece di aggiungerne. Con G2 il FE
legge la capability dalla vista, per la mappatura e per la conversione. Finché G1 e G2 non sono applicati, BE21 è
fattibile solo a metà: il codice, la policy e i test del rifiuto sì; il form e le azioni di riga no. BE22-BE25 non
dipendono da G1 e G2.

#### 15.11.1 Che cosa è scritto (sessione DB, 2026-11-11; via e numeri di Tid: dal `-69`, opzione a)

Cinque changeSet, `20261111-69` … `-73`; nulla applicato. Il `-68` è dell'altra sessione.

| # | Schema | Che cosa |
| --- | --- | --- |
| `-69` | script | `trgfn_lock_columns`: il contesto del rifiuto porta anche `campo` (= la colonna), accanto a `column`, `old_value` e `new_value`. Vale per tutti i lock (opzione a) |
| `-70` | catalogo | **BB nuovo** `fn_uom_conversione_capability(valido_dal, valido_al)`: `puo_eliminarsi`, `puo_cambiare_attivo`, `puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura` e i due motivi (`UOM_STORIA_IN_VIGORE`, `UOM_STORIA_CHIUSA`). LANGUAGE sql STABLE, `BEGIN ATOMIC`: nelle viste si espande in LATERAL |
| `-71` | catalogo | `trgfn_uom_guard_storia` senza la regola 1 e senza argomenti; le regole 2 e 3 le giudica il BB. I due trigger rimontati su `UPDATE OF attivo, valido_al OR DELETE` |
| `-72` | catalogo | `vw_articoli_uom_operativa_dettaglio`: la capability dal BB, le colonne della chiusura in coda. Sulla riga base: `UOM_BASE_NON_ELIMINABILE`, e attivo e fine non si offrono (motivo `UOM_BASE`) |
| `-73` | catalogo | **Vista nuova** `vw_unita_misura_conversioni_dettaglio`: le colonne della tabella, codice e descrizione delle due unità, la capability del BB. Solo SELECT |

Fuori dai changeSet:

* **`dbops/automation_lock_columns.csv`**: otto righe col codice `E_UOM_STORIA_IMMUTABILE`, le quattro colonne di
  ogni tabella. Il trigger `trg_<tabella>_a10_lock_columns_upd` lo genera l'automazione.
* **`config/messaggi_errore.csv`**: la frase di `E_UOM_STORIA_IMMUTABILE` parla della colonna («Il campo %s di
  una conversione già scritta non si cambia sul posto…»). **`config/codici_errore.csv`**: la nota dice chi lo
  solleva ora, e il contesto nuovo.
* **`ui/lista_definizione.csv`**: la lista 22 `catalogo.conversioni_uom` ha `vista_sql =
  vw_unita_misura_conversioni_dettaglio`.

**Le scelte dentro il giro (da guardare, Tid).**

1. **La riga base nella vista delle mappature**: attivo e fine non si offrono (`UOM_BASE`). La fine la rifiuta già il
   CHECK della base; l'attivo, dal giro Q34, il guard della base (§15.11.2).
2. **Il lock vale anche sulla riga base.** Lì unità e fattore erano già fermi (guard della base e CHECK); in più
   diventano fermi `articolo_id` e `valido_dal`, che nessuno scrive. Sul fattore della base, un UPDATE ora lo
   rifiuta il lock (`E_UOM_STORIA_IMMUTABILE`), perché i trigger BEFORE scattano prima del CHECK. Il CHECK resta la
   regola della base, e vale anche per un INSERT.
3. **Il trigger del guard ora scatta solo su `attivo` e `valido_al`.** Prima scattava su ogni UPDATE, perché la
   regola 1 guardava tutte le colonne.
4. **Fra migrate e convergenza** le quattro colonne non le blocca nessuno, su dbdev (vedi l'apply qui sotto). In
   CI la passata `ci_apply` genera il lock nello stesso giro.

**Le risposte di Tid (2026-11-11).**

* **Scelta 2** e **scelta 3**: restano come sono.
* **Scelta 4, corretta.** Su dbdev la finestra non c'è: il migrate di Tid (`liquibase5.sh` dalla cartella `db/`)
  gira senza `--contexts`, quindi esegue anche il `runAlways` `90_end/ci_apply/20260926-10`, che fa `CALL` delle
  procedure strutturali in ordine di `dbops.processi.ci_ordine` (il lock a 60). La convergenza del lock sta già
  dentro il migrate, come in CI e sullo scratch (`ci-local.sh --ci-apply`). Il passo 2 dell'apply qui sotto era
  superfluo. `CALL maintenance.proc_automations_lock_columns_job()` resta il modo di lanciarla da sola, e il job
  delle 21:00 la ripete. Chi vuole il lock anche da un migrate con contesti ristretti lo scrive come changeSet
  `90_end` «provision-lock» (il precedente è `20261020-12`).
* **Scelta 1: sì, nel DB.** Guardando il guard della base per scriverla, la regola si divide in due.
  * **La fine c'è già.** Il CHECK `chk_articoli_uom_operativa_base_fissa` vuole sulla base `valido_dal` e
    `valido_al` vuoti: chiudere la base il DB lo rifiuta già (23514). Il `motivo_non_chiudibile = UOM_BASE` della
    vista lo anticipa. Da correggere solo la frase della scelta 1 («il guard sulla base non dice niente»).
  * **L'attivo è una domanda di modello: Q34, qui sotto.**

**Q34 — L'attivo della riga base.** ✅ **Tid, 2026-11-11: (a).** Il giro è in §15.11.2. La storia delle decisioni:

* **D7 (giro 2).** La riga base nasceva sempre attiva, e il REQUIRE verso l'articolo rompeva il COMMIT di un
  articolo creato spento. La correzione: la base nasce attiva o spenta **come l'articolo** (`20261111-01`).
* **Q31 (giro 2-bis).** Il legame ATTIVO fra mappatura e articolo è in eccezione: «l'articolo si spegne e si
  riaccende con le sue mappature intatte». Il REQUIRE che aveva motivato D7 non c'è più.

**L'attivo della base non è indifferente.** `catalogo.fn_uom_operativa_alla_data` legge la mappatura con
`o.attivo IS TRUE`, la base compresa, e da lì `script.trgfn_qta_from_operativa` prende `qty_step`,
`max_decimals`, `forbid_fraction`. Una base spenta toglie le regole della quantità all'unità base dell'articolo; il
fattore no, perché `fn_uom_fonti_conversione` lo dà dall'articolo (priorità 0) senza leggere la riga. Quindi oggi
un articolo nato spento, e poi acceso, ha la base spenta e perde quelle regole finché qualcuno non la riaccende.
Vietare nel DB di cambiare l'attivo della base, con il seed di oggi, lo renderebbe per sempre. Le due strade
coerenti:

* **(a), proposta.** La base è sempre attiva: il seed torna a scrivere `attivo = TRUE` (D7 non serve più dopo
  Q31), il guard della base rifiuta un UPDATE di `attivo` (`UPDATE OF … attivo`), e le basi spente oggi si
  riaccendono con un backfill. È la stessa idea della fine: la base non ha stati, vale 1 sempre.
* **(b).** La base segue l'articolo: un trigger sull'articolo copia `attivo` sulla sua base, e a mano non si
  cambia. Le regole della quantità sull'unità base seguono l'accensione dell'articolo. Un pezzo di
  propagazione in più, e una riga che si spegne per conto d'altri: la mappatura spenta oggi vuol dire «non vale»,
  e l'articolo spento lo fermano già i REQUIRE dei documenti (Q31).

**Le prove** (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, con le
`preConditions` come asserzioni, le righe di seed nuove e la convergenza simulata con
`dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['catalogo'], false)`, in `BEGIN … ROLLBACK`).

* **Compilazione.** I cinque changeSet compilano e le `preConditions` passano. La convergenza crea solo i due
  trigger attesi: `trg_articoli_uom_operativa_a10_lock_columns_upd` e
  `trg_unita_misura_conversioni_a10_lock_columns_upd`, coi quattro argomenti ciascuno. I rollback, in ordine
  inverso, rimettono i corpi vivi (il guard con `TG_NARGS`, il lock senza `campo`, il BB tolto). Lo scratch è
  rimasto intatto.
* **pgTAP nuovo** `catalogo/test-uom-conversione-capability-v1`: 16/16. Le risposte del BB sono costruite sulle
  date; le due viste dicono quello che dice il BB; riga per riga, il guard fa quello che il BB dice
  (cancellazione, spegnimento, chiusura alla data minima e un giorno prima); la lista legge la vista con tutte le
  sue colonne.
* **Riallineati**, con nota datata:
  * `catalogo/test-uom-storia-v1`: 24/24 (21 + 3 nuovi: il campo del rifiuto, le otto colonne in
    `vw_non_editable_fields`, il montaggio del guard). Senza il giro, i tre nuovi sono rossi;
  * `catalogo/test-vw-articoli-uom-operativa-dettaglio-capability-v1`: 8/8. La riga secondaria senza inizio era
    «eliminabile» ed è in vigore da sempre: ora comincia oggi, e una terza riga in vigore prova il rifiuto;
  * `catalogo/test-uom-fattore-e-regole-v1`: 31/31. Il test 19 (fattore della base → CHECK) prova il CHECK con
    l'override di manutenzione del lock acceso, perché senza il lock parlerebbe prima (scelta 2).
* **Regressione**, ogni file senza e con il giro, identica salvo i tre file qui sopra: in catalogo
  `test-fn-get-uom`, `test-articoli-vincoli-note-uom-overlap`, `test-articoli-componenti-guard-attivo-composito`,
  `test-articoli-seed-uom-base-lock`, `test-uom-tipi-global-conversioni-v1`, `test-articoli-ammessi-picker-v1`,
  `test-fn-riattiva-articolo-v1`; in dbops `test-lock-columns-convergenza`,
  `test-non-editable-fields-dal-lock-vivo-v1`, `test-punti-canale-campo-v1`,
  `test-marcatori-automazione-senza-esecutore-v1`, `test-anti-overlap-enforcement-gate-v1`,
  `test-riferimenti-morti-v1`; in script `test-trgfn-guard-date-validita-v1`,
  `test-catalogo-messaggi-errore-completo`; in ui `test-lista-colonna-campo-sorgente-in-vista-v1`,
  `test-fn-resolve-lista-config`, `test-ui-nell-ambito-v1`; in vendite `test-listino-uom-periodo-v1`,
  `test-commesse-attivita-fattore-alla-data-v1`. Tutti verdi.
* **Guardrail** (pre-commit sui file del giro): verdi.

**Doc.**

* Pagine `manual/` nuove: `catalogo/fn_uom_conversione_capability`, `catalogo/vw_unita_misura_conversioni_dettaglio`.
* Riallineate: `catalogo/trgfn_uom_guard_storia`, `catalogo/vw_articoli_uom_operativa_dettaglio`,
  `catalogo/articoli_uom_operativa`, `catalogo/unita_misura_conversioni`, `script/trgfn_lock_columns` (solo il
  contesto e la data).
* Da rigenerare dopo l'apply: le schede auto-generate.
* **Debito documentale notato, fuori giro**: la pagina `manual/` di `script.trgfn_lock_columns` è nel formato
  vecchio (niente «Vedi anche» allo standard, blocco `sql` d'esempio, slogan in coda). Non l'ho riscritta: non è di
  catalogo.

**Apply (Tid).**

1. Il migrate su dbdev e scratch.
2. **Subito dopo**, la convergenza del lock: `CALL maintenance.proc_automations_lock_columns_job()`, oppure il
   job delle 21:00. Fino ad allora le quattro colonne di ogni tabella non le blocca nessuno, e sono rossi
   `test-uom-storia-v1` (test 1-4, 14, 22, 23) e `test-lock-columns-convergenza` (il registro chiede due lock che
   non ci sono).
3. I pgTAP come app.
4. Il commit su richiesta.

**Esito (2026-11-11).** Tid ha applicato il giro G1-G2 su dbdev e scratch, con la convergenza del lock subito dopo,
e i pgTAP come app sono verdi. Il commit è su `dev/db-tid`, coi file del giro e questo brief.

**Ricadute su BE e FE, a giro applicato** (aggiornano BE21, §15.4 e §15.9):

| # | Che cosa |
| --- | --- |
| BE21-a | `_NON_EDITABLE_DB_GAPS` (`catalogo_service.py:113`) si ritira: le colonne di mappatura e conversione arrivano da `vw_non_editable_fields`. Il rifiuto `E_UOM_STORIA_IMMUTABILE` porta il campo (`COLUMN`) |
| BE21-b | Le unità di un articolo: le azioni di riga leggono `puo_eliminarsi`, `puo_cambiare_attivo`, `puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura` e i motivi dalla vista. Il motivo nuovo `UOM_STORIA_IN_VIGORE` (e `UOM_STORIA_CHIUSA`, `UOM_BASE`) va nei locales |
| BE21-c | Le conversioni generali: il repository (`list_conversioni`, `catalogo_repository.py:789`) legge `catalogo.vw_unita_misura_conversioni_dettaglio`, che è ora la `vista_sql` della lista 22, con le stesse azioni di riga |
| BE21-d | Su tutti i codici di lock il contesto ha ora anche `campo`: se il backend ricavava il campo da `column`, quel ripiego si può togliere |

#### 15.11.2 Il giro Q34: la riga base sempre attiva (2026-11-11)

**Che cosa è scritto.**

| # | Livello | Che cosa |
| --- | --- | --- |
| `20_code/catalogo/20261111-74` | seed | `trgfn_articoli_seed_uom_base`: la riga base nasce con `attivo = TRUE`, anche sotto un articolo spento. Annulla la correzione di D7, che Q31 ha reso inutile |
| `20_code/catalogo/20261111-75` | guard | `trgfn_articoli_uom_operativa_guard_base`: rifiuta lo spegnimento della base e una base nuova spenta (`E_UOM_RIGA_BASE_IMMUTABILE`, campo `attivo`). La riaccensione passa. Il trigger si rimonta con `attivo` in `UPDATE OF` |
| `80_data/changelog/20261111-76` | backfill | Le basi spente si riaccendono. Passa il guard, perché riaccende. Idempotente; la `preCondition` vuole il trigger rimontato da `-75` |

Fuori dai changeSet: `config/messaggi_errore.csv` (la frase dice «non si cambia, non si spegne e non si toglie») e
`config/codici_errore.csv` (la nota col campo `attivo`).

**I pgTAP.**

* `catalogo/test-uom-fattore-e-regole-v1` (plan 34): 25b ora vuole la base attiva sotto l'articolo spento; nuovi 25c
  (la base non si spegne), 25d (il campo è `attivo`), 25e (una base nuova spenta è rifiutata). I test 20-22 seguono la
  frase nuova.
* `catalogo/test-articoli-ammessi-picker-v1`, `catalogo/test-articoli-componenti-guard-attivo-composito`: spegnevano la
  riga base prima dell'articolo, l'ordine «figli prima del padre» di prima di Q31. Il passo è tolto: dopo Q31 non serve,
  dopo Q34 fallirebbe.
* `catalogo/test-fn-get-uom` (test 8): spegneva tutte le mappature dell'articolo, la base compresa; ora solo quelle che
  non sono la base, che è ciò che il test vuole provare.

**Le prove** (scratch `zeroerp_ruoli`, come owner, SQL estratto dai YAML, in `BEGIN … ROLLBACK`).

* I tre changeSet compilano e le `preConditions` passano; il trigger rimontato ha `attivo` in `UPDATE OF`.
* Una base spenta a mano (trigger disattivato nella transazione) si riaccende con l'UPDATE del backfill: il guard la
  lascia passare. I rollback, in ordine inverso, rimettono il corpo di D7 e il trigger di prima.
* Regressione sui 21 pgTAP che toccano `articoli_uom_operativa` o la riga base: identici senza e con il giro, tutti
  verdi. Le eccezioni sono `test-uom-fattore-e-regole-v1`, rosso senza il giro (7 test) perché è già scritto sul modello
  nuovo e verde con il giro, e `vendite/test-refactor-qta-operativa-preventivi-v1`, rosso **uguale** senza e con (5
  test, dal 6): la sua fixture cerca fra i dati dello scratch un preventivo DRAFT e un articolo, e non li trova. Non è
  di questo giro.

**Apply (Tid).** Il migrate su dbdev e scratch, i pgTAP come app, il commit su richiesta. Nessuna convergenza a parte.

**Esito (2026-11-11).** Tid ha applicato il giro Q34 su dbdev e scratch (`-74`, `-75`, `-76` in `databasechangelog` di
`zeroerp` e `zeroerp_ruoli`), e i pgTAP come app sono verdi.

**La nota del BE del 2026-11-11** («pulsanti che il DB rifiuta») la chiude già il giro G1-G2, applicato:

* `puo_eliminarsi` e `motivo_non_eliminabile` seguono la regola della storia (`UOM_STORIA_IN_VIGORE`) in
  `vw_articoli_uom_operativa_dettaglio` (`-72`);
* `puo_cambiare_attivo`, `puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura`, `motivo_non_chiudibile` ci sono
  nella vista della mappatura e nella vista nuova delle conversioni, `vw_unita_misura_conversioni_dettaglio` (`-73`);
* fattore, unità, articolo e inizio li dichiara `vw_non_editable_fields` (lock di colonna, `-69` e il registro):
  `_NON_EDITABLE_DB_GAPS` si ritira. La regola della data **non** è in `non_editable_fields`, come chiede la nota.

Restano le voci BE21-a … d (§15.11.1), più due:

| # | Che cosa |
| --- | --- |
| BE21-e | Anche il **drawer** di una conversione (il dettaglio, non solo la lista) legge `vw_unita_misura_conversioni_dettaglio`, per spegnere l'interruttore attivo con il motivo |
| BE21-f | Riga base: un PATCH di `attivo` ora lo rifiuta il DB (`E_UOM_RIGA_BASE_IMMUTABILE`, campo `attivo`); il form la legge già da `puo_cambiare_attivo = false`. La frase di ripiego in `error_messages_fallback.py` può seguire quella nuova («non si cambia, non si spegne e non si toglie») |

### 14.10 Giro BE del giro 3 (team BE, 2026-11-10, da committare su `dev/backend-tid`)

#### 14.10.1 Che cosa è fatto

| # | Che cosa |
| --- | --- |
| codici ✅ | Policy rigenerata (`manage.py genera_error_policies`: entrano i soli quattro codici del giro, più una `note` aggiornata a catalogo) e i quattro ripieghi senza `%s` in `error_messages_fallback.py`. `E_BOM_CHIUSURA_CON_PREZZI` ha l'override `confirm_and_retry` in `error_ui_overrides.py`, come `E_DOC_ANNULLO_CON_LEGAMI`: col banner della classe il legame di un kit prezzato non si chiuderebbe mai |
| BE19 ✅ | La chiusura passa dal **verbo**: `POST …/componenti/<id>/chiudi/` (`catalogo.fn_chiudi_legame_distinta`) e `GET …/componenti/<id>/chiusura/?valido_al=` (`vendite.fn_prezzi_legame_oltre_la_fine`, coi prezzi e il numero da dichiarare). Il service controlla solo che il legame sia dell'articolo del percorso e la forma dei due campi. FE: «Chiudi riga» e lo step 1 di «Duplica versione» hanno una sede, `chiudiLegame` in `ArticoloBomDrawer.vue`, su `useForzaturaConfermata`; la finestra nuova è `ChiusuraLegamePrezziDialog.vue`. Il wrapper FE del PATCH (`updateArticoloComponente`) è ritirato: non aveva più consumatori |
| BE20 ✅ | Nessun codice da cambiare. Il rifiuto al COMMIT del PATCH dell'articolo lo rende il traduttore generale, con codice, `400` e campo `iva_id`: l'ha provato il test sul DB vero |
| BE4 ✅ | `E_PARAMETRO_INVALIDO` della correzione di struttura arriva col campo = la colonna. Anche qui nessun codice: la prova è sul DB vero |
| doc ✅ | `api_catalogo.md`: §4.1 (`data_min_chiusura` è la più tarda fra `valido_dal` e ieri, BE9), §4.3 (le regole della fine), §4.4 (il `DELETE` ritirato, BE11), §4.5 nuovo (la chiusura coi prezzi), §1.4 (l'IVA a fine transazione), §1.6-bis (il campo di D19). Catalogo BB FE: `ArticoloBomDrawer` fra i consumatori di `useForzaturaConfermata` |
| i18n ✅ | Le due `reason_key` della sessione DB rilette: il testo va bene così. Nuovo il blocco `catalogo.chiusura_prezzi.*` della finestra |

#### 14.10.2 Le prove

* `apps/catalogo/tests/db/test_chiusura_legame_prezzi_db.py`, sette test sul DB vero col mondo costruito: la
  finestra, il rifiuto confermabile (409, `confirm_and_retry`, campo `valido_al`), la conferma giusta, quella che
  non corrisponde, il legame di un altro articolo, la dichiarazione non intera, il legame senza prezzi.
* `apps/catalogo/tests/db/test_errori_articolo_giro3_db.py`, tre test: BE20 (il rifiuto al giudizio del vincolo, e
  kit più componente nella stessa transazione che passano) e BE4.
* `ChiusuraLegamePrezziDialog.spec.js`, cinque test. Suite `apps.catalogo` + `apps.core` verde (2189 test), vitest
  `src/catalogo` verde, `check_i18n_keys` pulito, build FE verde.

#### 14.10.3 Il PATCH del legame — ritirato (decisione di Tid, 2026-11-10)

Il §14.4 diceva «il PATCH su `valido_al` resta il primo tentativo». Il FE invece chiude **sempre dal verbo**, perché
`useForzaturaConfermata` ripete la **stessa** chiamata con la dichiarazione, e il PATCH non sa portarla. Su un legame
senza prezzi il verbo chiude al primo colpo, come il PATCH. Restato nell'API, il PATCH era una seconda strada per la
stessa scrittura, e su un legame con prezzi riceveva l'avviso senza poterlo confermare.

✅ **Tid ha accettato di toglierlo** (2026-11-10). Ritirati: la rotta `…/componenti/<id>/` (view
`ApiArticoloComponenteDetail`, schema `CatalogoComponentePatchRequest`), `fn_update_componente`, il ramo `for_update`
di `_extract_componente_payload`, `CatalogoBomRepository.update_componente` e i loro test (`api_catalogo.md` §4.3).
⚠️ Il PATCH accettava anche `meta` e `attivo` di un legame: nessun consumatore li usava, e un legame non ha più una
scrittura oltre alla fine. Se servisse annotare un legame, è un verbo nuovo, non il ritorno del PATCH.

#### 14.10.4 Alla sessione DB: le sigle doppie

Questo brief ha due sezioni numerate «§14», «Giro 2-bis» e «Giro 3». Ognuna definisce un BE19 e un BE20 con un
significato diverso (D24/D25 nella prima, la chiusura coi prezzi e l'IVA differita nella seconda), e la prima ha anche
un BE21. Chi legge «BE20 fatto» non sa quale dei due. Proposta: rinumerare il giro 2-bis (§15, e BE22-BE24).

## 16. Giro 4 — le note di catalogo (D16, R6, Q12), 2026-11-11

Via di Tid il 2026-11-11, numeri dal `20261111-77`.

### 16.1 Che cosa è scritto

| # | Fase | Che cosa |
| --- | --- | --- |
| `00_schema/catalogo/20261111-77` | DDL | `catalogo.note`: `chk_note_testo_non_vuoto` (lo stesso di vendite e acquisti), `chk_note_catalogo_ancora_documento` (`anchor_tipo = 'DOCUMENTO' AND target_riga_id IS NULL`), `user_insert` e `user_update` a `text`, `tx_id uuid`, con i COMMENT. Sul padre, scendono sulle due partizioni. Toglie le due viste delle note, che leggono `user_*` |
| `20_code/catalogo/20261111-78` | vista | **R6.** `catalogo.vw_note`: la proiezione della nota (16 colonne `nota_*`, 3 `stile_*`, 4 `lingua_*`) su `catalogo.note`, scritta una volta. Solo SELECT |
| `20_code/catalogo/20261111-79` | vista | `vw_articoli_note` sopra `vw_note` per `nota_target_tipo = 'ARTICOLO'`: stesse colonne, stesso ordine, GRANT di prima |
| `20_code/catalogo/20261111-80` | vista | `vw_articoli_componenti_note` sopra `vw_note` per `'ARTICOLO_COMPONENTE'`: stesse colonne, stesso ordine, GRANT di prima |

Fuori dai changeSet: **`dbops/automazione_attivo_eccezioni.csv`**, due righe (`note_articoli.target_id`,
`note_articoli_componenti.target_id`) col motivo di Q12. La convergenza dell'automazione ATTIVO, che gira dentro il
migrate, toglie i due block su articolo e legame e i due require sulle partizioni.

### 16.2 Le scelte dentro il giro (da guardare, Tid)

1. **Il CHECK dell'àncora è nuovo, sul padre.** `chk_note_anchor_tipo` resta com'è, perché è comune alle note di tutti
   gli schemi; il vincolo nuovo dice in più che a catalogo l'àncora è solo DOCUMENTO. Le colonne `anchor_tipo` e
   `target_riga_id` restano, per la forma comune.
2. **`posizione` non si restringe.** In vendite, con l'àncora DOCUMENTO la posizione è HEADER, FOOTER o SEZIONE; qui
   `BEFORE` e `AFTER` dicono dove va la nota dell'articolo rispetto alla riga del documento in cui l'articolo compare.
3. **Con l'eccezione se ne va anche il require**, non solo il block: una nota si scrive anche su un articolo spento.
   È la forma di Q31, e l'eccezione toglie i due insieme.
4. **`vw_note` non espone `tx_id`**: è correlazione tecnica con l'audit. Le due viste vecchie non l'avevano.
5. **Fuori dal giro: il codice senza partizione** (D16, quarto punto). La FK verso `config.tipi_entita` ammette
   ogni codice, e un codice senza partizione fallisce con l'errore di routing di PostgreSQL. La correzione decisa per
   D16 non lo copre; vale anche per vendite e acquisti, quindi non è di questo brief. Resta nel «Che cosa oggi non
   copre» della pagina delle partizioni.

### 16.3 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in `BEGIN … ROLLBACK`)

* **Compilazione.** I quattro changeSet compilano e le `preConditions` passano. Con le due righe di eccezione e la
  convergenza simulata (`CALL maintenance.proc_automations_tx_id_job()` e `…_attivo_job()`) nascono
  `trg_note_articoli_gen_tx_id_ins_upd` e `trg_note_articoli_componenti_gen_tx_id_ins_upd`, e se ne vanno i due block
  e i due require. I tipi e i CHECK sulle partizioni sono quelli attesi.
* **Rollback**, in ordine inverso: le due viste tornano con lo stesso `pg_get_viewdef` (md5 uguale), `user_*` torna
  `varchar(80)`. I trigger tolti dall'eccezione non tornano: per riaverli si toglie la riga dal CSV e si riconverge.
* **La partizione si sceglie ancora**: l'EXPLAIN di `vw_articoli_note` filtrato per articolo legge solo
  `note_articoli` (su dbdev, dentro una transazione annullata).
* **Le righe** (fatto datato, non motivo): nessuna nota di dbdev viola i due CHECK (11 note, 2026-11-11).
* **pgTAP nuovo** `catalogo/test-note-catalogo-forma-v1` (plan 12): testo vuoto e àncora RIGA rifiutati, la forma
  delle colonne, `tx_id` scritto, l'articolo con una nota che si spegne, la nota su un articolo spento, nessun block
  né require, le due viste sopra `vw_note` con le colonne di prima.
* **Regressione** sui 30 pgTAP che nominano le note di catalogo, le eccezioni ATTIVO o `config.tipi_entita`: identici
  senza e con il giro. Due erano rossi già prima, uguali, e non sono di questo giro: `script/test-vw-giornale-entita`
  muore in fixture (`p_tipo_doc_fiscale_id obbligatorio`), `ui/test-lista-definizione-perimetro-emittente-v1` test 4
  (riceve il CHECK `chk_ui_lista_definizione_perimetro_coerente` invece del guard, P0001).

### 16.4 Apply e ricadute

**Apply (Tid).** Il migrate su dbdev e scratch: la convergenza di `TX_ID` e `ATTIVO` è dentro il migrate. Poi i pgTAP
come app, e il commit su richiesta, insieme al giro Q34.

**Ricadute su BE e FE:**

| # | Che cosa |
| --- | --- |
| BE26 | Una nota di catalogo senza testo, o ancorata a una riga, ora la rifiuta il DB con un 23514 grezzo. Il form delle note di articolo e di legame non offre l'àncora RIGA e chiede il testo; il ripiego del 23514 la dice in parole |
| BE27 | Un articolo o un legame con delle note ora si spegne, e su un oggetto spento una nota si scrive: se il FE avvisava «togli prima le note» o bloccava la nota su un oggetto spento, quel ramo si toglie |
| BE28 | `nota_user_insert` e `nota_user_update` delle due viste sono ora `text`: nessuna ricaduta attesa, da verificare nei serializer |

**Esito (2026-11-11).** Tid ha applicato il giro 4 su dbdev e scratch (`-77` … `-80` in `databasechangelog` di
`zeroerp` e `zeroerp_ruoli`), e i pgTAP come app sono verdi. Su tutti e due i database la convergenza ha tolto i block
e i require fra le note e i loro bersagli (nessun trigger rimasto).

**Doc.** Riallineate le pagine `manual/` di `note`, delle due partizioni (solo la data), delle due viste e il blocco
comune `_note-partizioni.md`; nuova `vw_note.md`. Le schede auto-generate nascono alla rigenerazione dopo l'apply.

## 17. Giro 5 — pulizia e metadati: il censimento sul vivo, 2026-11-11

Via di Tid il 2026-11-11. §2.4, §2.5, §2.6 e §3 sono del 2026-11-08: i giri 1-4 ne hanno chiuso una parte. Qui
l'elenco riletto su dbdev (`obj_description`, `col_description`, `pg_get_functiondef`, `pg_index`,
`pg_stat_user_indexes`, il 2026-11-11), con quello che resta e la proposta.

### 17.1 Già chiuso dai giri precedenti

* **M1** (il COMMENT del guard flags non nomina più `guard_un_livello`), **M5** (`require_lot` e `rounding_mode`
  ritirati, `max_decimals` applicato: giro 2), **M7** (il COMMENT di `magazzino.note` è corretto).
* **R1-R6**: chiuse nei giri 1-4 (`fn_articolo_flag_etichetta` è R5, `vw_note` è R6).
* La nota di `E_BOM_MODIFICA_VIETATA` nomina già il guard flags (§2.5).
* `test-articoli-componenti-solo-componente.sql` è già sui builder, e lega il codice (§2.6).
* `fn_get_uom_factor`: `v_factor > 0` e `LIMIT 1` su chiave unica non ci sono più (giro 2).
* Funzioni, viste e tabelle di `catalogo` hanno tutte un COMMENT.

### 17.2 L'elenco chiuso del giro 5

**A. Indici e vincoli (§2.4, Q14, Q9)**

| Oggetto | Esito del censimento | Proposta |
| --- | --- | --- |
| `uq_articoli_componenti_prodotto_componente_from` | Implicato da `uq_articoli_componenti_no_overlap`; 0 scansioni. Lo nomina il BE (`catalogo_service.py:1187`, la frase del 23505) | **Si ritira** (Q14). Ricaduta BE29 |
| `ix_uom_tipi_codice_interno_upper` | 0 scansioni; nessun corpo del DB usa `upper(codice_interno)`; il BE cerca su `codice` | **Si ritira** (Q14) |
| `ix_artuomop_art_isbase` | 7190 scansioni: è l'unico btree che comincia da `articolo_id` (la FK verso l'articolo, le letture per articolo). L'indice parziale `uq_artuomop_one_base` serve solo la riga base | **Resta**: la condizione di Q14 non tiene |
| `uom_tipi.codice` | Il BE lo usa come etichetta (`tipo_uom_codice`), per l'ordinamento e per la ricerca; è la colonna di `CODICE_MAIUSCOLO`. `codice_interno` è quella bloccata | **Resta**: la condizione di Q9 non tiene. I due COMMENT, oggi uguali, si riscrivono distinti |
| FK semplice `listini_righe_componenti_articolo_componente_id_fkey` | Implicata dalla FK temporale, ma è la FK da cui l'automazione ATTIVO deriva il block su `articoli_componenti` e il require sulle righe di listino (letti da `pg_constraint`) | **Resta**: toglierla spegne due trigger alla convergenza |

**B. Rami irraggiungibili e codici (§2.4, §2.5)**

* `fn_get_uom_base`: `LIMIT 1` su chiave primaria; il commento e il COMMENT dicono «senza UoM», ma `articoli.uom_id`
  è NOT NULL (M6). Si toglie il `LIMIT 1` e si corregge il commento.
* `fn_articolo_correggi_struttura`: `p_campi IS NULL OR` ripetuto (due volte) dopo il guard che rifiuta `p_campi` NULL.
* `trgfn_unita_misura_guard_tipo`, `trgfn_uom_conversioni_guard_tipo`: passano `NULL::uuid` invece di `NEW.tx_id`.
  Il ramo che lascia passare `tipo_uom_id` NULL (NOT NULL con FK) si toglie nello stesso `CREATE OR REPLACE`.
* `fn_riattiva_articolo`: area di log `'database'` (le altre funzioni di catalogo usano `'catalogo'`); il commento
  del corpo cita `E_PARENT_*`, il COMMENT cita «(404)» e `trgfn_prevent_deactivate_if_children` per la
  disattivazione (che oggi ha le eccezioni ATTIVO e nessun figlio di storia). Il codice vero è
  `E_ATTIVO_PADRE_NON_ATTIVO`, al COMMIT.
* `trgfn_articoli_guard_iva_bom_attiva`: due `LIMIT 1`, da rileggere (se stanno dentro un `EXISTS` o su chiave
  unica, si tolgono).

**C. Metadati (§3)**

* **Dicono il falso:** M2 (`vw_articoli_dettaglio`: «ui.lista_definizione 26» per id, `requires_lotto` «senza lock»),
  M3 (`articoli.natura_vendita_id`: «a regime NOT NULL»), M4 (`articoli_componenti.id`: «sequence»; `.attivo`:
  «del articolo»), M6 (`fn_get_uom_base`), M8 (la nota di `automation_lock_columns` su `articoli.uom_id` cita
  `trg_articoli_a10_protect_uom_id_upd`, che non esiste: si riscrive la nota, che è un CSV).
* **Marcatori e nomi di brief** (§3.3, riletto): i COMMENT di `fn_articoli_ammessi`, `fn_articolo_righe_vive_non_ammesse`,
  `fn_riattiva_articolo`; della vista `vw_articoli_dettaglio` e delle sue colonne `causale_onere_id`, `e_onere`,
  `obsoleto_dal`, `e_obsoleto`; delle colonne `articoli.causale_onere_id`, `.gestito_a_magazzino`,
  `.modo_approvvigionamento_id`, `.note_target_tipo`, `.obsoleto_dal`, `.requires_lotto`,
  `articoli_componenti.esposizione_in_fattura`, `.note_target_tipo`, `.validita`, `unita_misura_conversioni.validita`,
  `note.target_tipo`, `unita_misura.conta_dal_calendario`; del trigger `trg_articoli_a10_guard_onere_natura_ins_upd`.
  Nei corpi: `fn_articoli_ammessi`, `fn_articolo_righe_vive_non_ammesse`, `fn_riattiva_articolo` (si aprono comunque).
* **D-C, fuori schema** (§3.3.1, riletto): tutti e cinque ancora da riscrivere (`acquisti.ddt_righe.sorgente_tipo_id`,
  `script.trgfn_righe_guard_articolo_ammesso`, `vendite.fn_clona_versione_listino`, i due trigger di `vendite`).
* **Senza COMMENT** (§3.2): le colonne di `note` (13), di `unita_misura_conversioni` (12), le quattro d'audit di
  `uom_tipi`; i 13 trigger scritti a mano dei guard di catalogo (gli altri 103 senza COMMENT sono trigger delle
  automazioni, che non ne scrivono in nessuno schema); le colonne delle sette viste (vedi la scelta 3).
* **Il presidio**: `catalogo` e i cinque oggetti di D-C entrano in `dbops/test-comment-al-presente-v1.sql` (i COMMENT
  della famiglia sono riscritti: `linee-guida-sql` §5d).

**D. pgTAP deboli (§2.6)**

* `test-articoli-natura-vendita-notnull-default-v1.sql`: il test 2 conta i NULL di una colonna NOT NULL su tutto il
  catalogo (tautologico) e la fixture prende «il primo articolo» (`ORDER BY id LIMIT 1`): si riscrivono sui builder.
* `test-vw-articoli-dettaglio-e-onere-v1.sql`: il test 3 itera su tutto il catalogo; i casi 1 e 2 sono costruiti. Si
  toglie, o si riscrive su un articolo costruito.

**E. Doc**

* `guide/gestione-contratti.md:142`: «quando è *derivata dai componenti* la scrive il sistema»: quella fonte è
  ritirata (§13.6). Si toglie la frase.
* Le pagine `manual/` degli oggetti che il giro riapre.

### 17.3 Le scelte (Tid)

✅ **Tid, 2026-11-11:** 1 → giro 5-bis a parte; 2 → **si tolgono ora** (contro la proposta: solo i `COALESCE` davvero
irraggiungibili, funzione per funzione, §17.4); 3 → solo le colonne calcolate; 4 → solo la nota.

1. **La segnalazione 3 del giro BE** (§15.10-bis.3, passo 7-decies: il codice nel risultato di
   `vendite.fn_batch_upsert_commessa_attivita`). È l'unico lavoro DB ancora aperto del brief, ma tocca `vendite` e un
   contratto col BE. Proposta: **un giro a parte, 5-bis**, dopo il giro 5, per non mescolare un cambio di contratto
   con la pulizia.
2. **I `COALESCE` su valori NOT NULL nelle funzioni di `vendite`** (18 funzioni, residuo del giro 1-bis). Non sono
   tutti irraggiungibili: dopo un `SELECT … INTO` senza righe la variabile è NULL. Proposta: **restano**; si toccano
   quando un giro riapre quelle funzioni (`linee-guida-sql` §5d: non si apre un `CREATE OR REPLACE` per un commento).
3. **I COMMENT delle colonne delle viste** (~200 colonne in sette viste). Proposta: **solo le colonne che la vista
   calcola** (capability, motivi, `e_*`, `has_*`, le etichette decodificate); una colonna copiata dalla tabella ha il
   COMMENT della tabella.
4. **Il codice del lock su `articoli.uom_id`** (`E_CODICE_NON_MODIFICABILE`, «il valore interno della colonna %s»).
   Proposta: **resta**, si riscrive solo la nota; un codice nuovo cambierebbe il contratto col BE per una frase che
   resta vera.

**Numeri (Tid, 2026-11-11):** `20261112-01` … `-30`. Il `20261111-81` e i seguenti sono dell'altra sessione
(brief-db-revisione-dbops), aperta in parallelo.

**Ricadute su BE e FE (quando il giro è applicato):**

| # | Che cosa |
| --- | --- |
| BE29 | `catalogo_service.py:1187` mappa `uq_articoli_componenti_prodotto_componente_from`, che si ritira: la voce si toglie. La sovrapposizione la dice già `uq_articoli_componenti_no_overlap` (23P01) |

### 17.4 Il giro, in due parti

**5-A — catalogo, D-C, pgTAP, doc** (§17.2 A-E), senza i `COALESCE` di `vendite`. Il `LIMIT 1` del guard IVA resta:
sta dopo un `ORDER BY a.codice` e prende il primo articolo in conflitto, non una chiave unica. I corpi di
`fn_articoli_ammessi` e `fn_articolo_righe_vive_non_ammesse` non si riaprono: il giro riscrive solo il loro COMMENT
(§3.3.1, ultimo punto).

**5-B — i `COALESCE` su valori che non possono essere NULL** (scelta 2). Censiti uno per uno sul corpo vivo:

| Funzione | `COALESCE` | Perché non può essere NULL | Esito |
| --- | --- | --- | --- |
| `vendite.fn_contratti_addebiti_maturati` | 3 su `contratti_righe.attivo` | Colonna NOT NULL | si toglie |
| `vendite.fn_{contratto,ddt,ordine,preventivo}_riga_componenti_init` | 2 ciascuna: `v_is_composito`, `v_comp.obbligatorio` | Il primo viene da un JOIN con l'articolo, dopo il `NOT FOUND` che solleva; il secondo da `articoli_componenti.obbligatorio`, NOT NULL | si tolgono |
| `vendite.fn_offerta_eccezione_componenti_init` | 2, gli stessi | `articolo_id` dell'eccezione è NOT NULL con FK, e l'eccezione è già trovata | si tolgono |
| `vendite.fn_documento_righe_preview` | 3 su `e.attivo` | `fn_documento_righe_eccezione` lo prende da due colonne NOT NULL | si tolgono |
| `vendite.fn_genera_ddt_da_ordine` | 1 su `ordini_righe_componenti.attivo` | NOT NULL | si toglie |
| `vendite.fn_offerta_righe_espanse` | 3 su `offerte_commerciali_eccezioni.attivo` | NOT NULL | si tolgono |
| `vendite.fn_push_preventivo_a_ordine` | 1 su `preventivi_righe_componenti.attivo` | NOT NULL | si toglie |
| `vendite.fn_resolve_prezzo_listino_v2_esito` | 1 su `contratti_righe.attivo` | NOT NULL | si toglie |
| `vendite.fn_resolve_lotto_utility_emittente` | 1 su `v_emittente_attivo` | Viene da `SELECT EXISTS (…)`, mai NULL | si toglie |
| `script.trgfn_componenti_guard_obbligatorio` | 1 su `v_obbligatorio` | BEFORE UPDATE su `OLD.articolo_componente_id`: la FK della riga vecchia regge, il legame c'è | si toglie |
| `script.trgfn_listini_righe_comp_guard_coerenza_bom` | 1 su `v_ac_attivo` | Il ramo `NOT FOUND` è già prima, nello stesso `IF` | si toglie |
| `script.fn_check_riga_magazzino` | 2 | L'articolo si cerca per parametro: può non esserci | **resta** |
| `script.trgfn_componenti_check_prezzo_obbligatorio` | 1 | BEFORE INSERT su `NEW.articolo_componente_id`: la FK si controlla dopo, il legame può non esserci | **resta** |
| `script.trgfn_componenti_guard_coerenza_bom` | 1 | Legge la riga padre per `EXECUTE`, in un BEFORE: può non esserci | **resta** |
| `vendite.fn_crea_famiglia_documento` | 1 su `p_attivo` | È un parametro | **resta** |

Il resto del corpo non si tocca: un `COALESCE` su un valore che non può essere NULL si sostituisce col valore
(`COALESCE(x, TRUE) IS TRUE` → `x`, `NOT COALESCE(v, FALSE)` → `NOT v`).

### 17.5 Giro 5-B — che cosa è scritto e le prove (2026-11-11)

Quattordici changeSet di `20_code`, uno per funzione, `20261112-01` … `-14` (dodici in `vendite/`, due in `script/`), con
le sostituzioni della tabella di §17.4 e nient'altro.

* **La dichiarazione viene dallo YAML, il corpo dall'oggetto vivo.** `pg_get_functiondef` scioglie i `%TYPE` di firma e
  `RETURNS` e non scrive `SECURITY INVOKER`: la firma è quella dell'ultimo YAML che la dichiara, il corpo quello di
  dbdev. Per i cinque init dei componenti l'ultimo YAML (giro 1-bis, `20261110-86` … `-90`) aveva già la firma sciolta:
  la dichiarazione viene dal changeSet precedente, che ha i `%TYPE` (`20261029-42`, `20260819-17`, `20260513-30`,
  `20260513-29`, `20261029-43`). Così questi changeSet **riportano i `%TYPE`** che il giro 1-bis aveva perso.
  ⚠️ Non tutti: tre `%TYPE` erano persi già **prima** della fonte, e il giro 5-B li ha ricopiati sciolti. Sono
  `p_emittente_sr_id` del contratto e dell'offerta (sciolti in agosto, `20260807-02`/`-03`) e le due colonne del
  `RETURNS TABLE` di `fn_resolve_lotto_utility_emittente` (sciolte a marzo, `20260331-22`). Li ha trovati un confronto
  con **tutta** la storia di ogni funzione, dopo l'apply: tornano col `-22` … `-24` (§17.6).
  `SECURITY INVOKER` si aggiunge dove la dichiarazione non lo scriveva: il comportamento non cambia, è il default.
* **Rollback**: la stessa dichiarazione col corpo di partenza.
* **Prova di compilazione** (scratch `zeroerp_ruoli`, come owner, `BEGIN … ROLLBACK`): per ogni changeSet il corpo
  vivo dello scratch è uguale a quello di dbdev; il forward ricompilato dà esattamente il corpo atteso
  (`pg_get_functiondef` uguale), e il rollback ridà esattamente l'oggetto di oggi.
* **Regressione** sui 76 pgTAP che nominano le quattordici funzioni, i loro trigger o le tabelle dei componenti:
  identici senza e con il giro. Quattro erano rossi già prima, uguali, e non sono di questo giro: tre test «serve il
  proprietario» (`catalogo/test-chiudi-legame-con-prezzi-v1` 11, `vendite/test-annullo-documento-con-legami-v1` 30,
  `vendite/test-ddt-righe-evase-dall-ordine-v1` 43) falliscono perché la prova gira come owner; in
  `vendite/test-offerta-righe-espanse` i test 6-8 ricevono NULL.
* **Doc:** nessuna pagina cambia, perché il comportamento è lo stesso.

### 17.6 Giro 5-A — che cosa è scritto e le prove (2026-11-11)

| # | Fase | Che cosa |
| --- | --- | --- |
| `00_schema/catalogo/20261112-15` | DDL | Via `uq_articoli_componenti_prodotto_componente_from` e `ix_uom_tipi_codice_interno_upper` (Q14). Il rollback li rimette, col COMMENT del vincolo |
| `00_schema/catalogo/20261112-16` | COMMENT | Le colonne delle tabelle: riscritte al presente (M3, M4, §3.3), nuove (`unita_misura_conversioni`, l'audit di `uom_tipi`, `note` e le due partizioni), `codice` e `codice_interno` di `uom_tipi` distinti; e la FK `fk_cat_note_target_tipo`, che nominava un brief (l'ha trovata il presidio nuovo) |
| `20_code/catalogo/20261112-17` | funzione | `fn_get_uom_base`: via il `LIMIT 1` su chiave primaria, COMMENT al presente (M6); la firma ora è ancorata (`%TYPE`), non lo era mai stata |
| `20_code/catalogo/20261112-18` | funzione | `fn_articolo_correggi_struttura`: via il secondo `p_campi IS NULL OR`. La firma riprende i `%TYPE` che il giro 3 (`20261111-37`) aveva sciolto |
| `20_code/catalogo/20261112-19` | funzione | `fn_riattiva_articolo`: area di log `catalogo`; il commento del corpo e il COMMENT nominano `E_ATTIVO_PADRE_NON_ATTIVO` al COMMIT e le funzioni di `dbops` dell'automazione ATTIVO (§2.5) |
| `20_code/catalogo/20261112-20` | COMMENT | `fn_articoli_ammessi`, `fn_articolo_righe_vive_non_ammesse`, `vw_articoli_dettaglio` (M2) e le sue colonne; le colonne calcolate delle sette viste (scelta 3); i trigger dei guard scritti a mano, e quello del guard onere/natura riscritto |
| `20_code/catalogo/20261112-21` | COMMENT | D-C fuori schema (§3.3.1): `acquisti.ddt_righe.sorgente_tipo_id`, `script.trgfn_righe_guard_articolo_ammesso`, `vendite.fn_clona_versione_listino`, i due trigger OBSOLETO di vendite. D-C è chiuso |
| `20_code/vendite/20261112-22` | funzione | `fn_resolve_lotto_utility_emittente`: le due colonne del `RETURNS TABLE` tornano col `%TYPE` del `20260222-06` |
| `20_code/vendite/20261112-23` | funzione | `fn_contratto_riga_componenti_init`: `p_emittente_sr_id` torna `anagrafiche.soggetti_ruoli.id%TYPE` (`20260605-07`) |
| `20_code/vendite/20261112-24` | funzione | `fn_offerta_eccezione_componenti_init`: `p_emittente_sr_id` torna `anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE` (`20260605-06`) |

**`-22` … `-24`: i `%TYPE` che la 5-B aveva ricopiato sciolti** (§17.5). Il `-12`, il `-02` e il `-06` erano già
applicati: non si toccano, e la dichiarazione torna in un changeSet nuovo. Il corpo è quello della 5-B e i tipi risolti
sono gli stessi, quindi l'oggetto compilato è identico. Cambia la fonte che il prossimo changeSet della funzione
ricopierà. Prova: preCondition 1; `pg_get_functiondef`, COMMENT e ACL uguali prima, dopo il forward e dopo il rollback.
`p_data_riferimento` dei cinque init resta `date` dal `20260512`, anche nelle firme scritte col `%TYPE`: è la data
alla quale si legge la distinta, non una colonna del documento.

Fuori dai changeSet: la nota della riga `catalogo.articoli.uom_id` in `dbops/automation_lock_columns.csv` (M8: nomina il
trigger vivo, il codice resta, scelta 4). Il CSV si ricarica con l'upsert `runOnChange` del `20260110-15`.

**Caduti dal censimento** (§17.2 B), riletti sul corpo: i due guard della tipologia passano `NULL::uuid` perché
`unita_misura` e `unita_misura_conversioni` non hanno `tx_id`; i loro rami «parla la FK» scattano davvero (BEFORE, la FK
si giudica dopo). Restano com'erano.

**pgTAP:**

* Nuovo `catalogo/test-comment-al-presente-catalogo-v1` (plan 5): lo stesso presidio di `dbops`, su `catalogo` e sui
  cinque oggetti di D-C. In un file suo, non dentro `dbops/test-comment-al-presente-v1`, che è dell'altra sessione aperta.
* `test-articoli-natura-vendita-notnull-default-v1`: il test 2 non conta più i NULL di tutto il catalogo, prova il
  rifiuto di una natura NULL esplicita (23502); la fixture è un articolo del builder, in una tabella temporanea sua (nel
  `WHERE` il builder girava una volta per riga).
* `test-vw-articoli-dettaglio-e-onere-v1`: il test 3 non itera sul catalogo; toglie la causale all'articolo costruito e
  ne guarda `e_onere`.

**Prove** (scratch `zeroerp_ruoli`, come owner, `BEGIN … ROLLBACK`): per ogni changeSet la preCondition passa, il
forward cambia lo stato, i tre corpi ricompilati sono esattamente quelli attesi, e il rollback riporta lo stato di prima
(md5 uguale su COMMENT di `catalogo`, `acquisti`, `script`, `vendite`, corpi, indici e vincoli di `catalogo`). Il
guardrail CI dei COMMENT è pulito sui 24 changeSet. Regressione sui 70 pgTAP di `catalogo` e su quelli che nominano gli
oggetti toccati o leggono i COMMENT: identici senza e con il giro, tranne il presidio nuovo, che è rosso senza (3 su 5) e
verde con. I rossi di prima restano uguali: test «serve il proprietario» (la prova gira da owner) e alcuni di
`magazzino` e `vendite` che non toccano il giro.

**Doc:** `manual/` di `uom_tipi`, `fn_get_uom_base`, `fn_riattiva_articolo`; `guide/gestione-contratti.md` (via la fonte
«derivata dai componenti», ritirata: la CHECK della riga ammette la quantità solo con la fonte FISSA).

### 17.7 Apply del giro 5 (2026-11-11)

✅ **Applicato da Tid il 2026-11-11** su dbdev e sullo scratch, 5-B e 5-A (`20261112-01` … `-24`, tutti `EXECUTED` in
`databasechangelog` su tutti e due), con i pgTAP come app verdi.

**Verifica sul vivo, lo stesso giorno** (come app, in sola lettura): `obj_description` / `col_description` dei 26 oggetti
che i changeSet del cantiere `obsoleto_dal` avevano commentato (§3.3.1), su dbdev e sullo scratch. Nessuno porta più
nomi di brief, marcatori `rev`, id di changeSet, sigle di decisione o id di messaggio. Compresi i dieci dell'elenco
chiuso, che erano sporchi prima del giro. ⇒ **D-C di `brief-db-articoli-obsoleto-dal` è chiuso.**

**Da committare:** il giro 5 (5-B e 5-A), con questo brief.
### 16.5 Giro BE dei giri G1-G2, Q34 e 4 (team BE, 2026-11-11, da committare su `dev/backend-tid`)

Fatto a giri applicati su dbdev (verificato sul DB: le otto colonne in `vw_non_editable_fields`, le due viste con la
capability, `catalogo.vw_note`). Il push DB `a9f6d0a23` («Fix DB per CI») cambia solo tre COMMENT: nessuna ricaduta.

#### 16.5.1 Che cosa è cambiato

| # | Che cosa | Dove |
| --- | --- | --- |
| BE21-a ✅ | `_NON_EDITABLE_DB_GAPS` e `_non_editable_fields_catalogo` ritirati: i service chiamano il BB `compute_non_editable_fields` senza gap. Il rifiuto `E_UOM_STORIA_IMMUTABILE` porta il campo (provato sul DB vero) | `catalogo_service.py` |
| BE21-b ✅ | Le unità di un articolo trasportano tutta la capability della vista (`puo_cambiare_attivo`, `puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura`, `motivo_non_chiudibile`). Il form spegne interruttore e data di fine col motivo, la fine parte da `data_min_chiusura`, e i campi spenti non vanno nel PATCH. Locales: `motivo_uom_storia_in_vigore`, `motivo_uom_storia_chiusa`, `motivo_uom_base`; `motivo_uom_base_non_eliminabile` riscritta («non si elimina e non si spegne») | `catalogo_uom_repository.py`, `ArticoloUomForm.vue`, `ArticoloUomDrawer.vue`, i due locales |
| BE21-c ✅ | `list_conversioni` legge `vw_unita_misura_conversioni_dettaglio`: proiezione, ricerca e ordinamento sulle colonne della vista, con la capability. La lista 22 non ha colonna azioni: le azioni stanno nel drawer | `catalogo_repository.py` |
| BE21-d ✅ | Niente da togliere: il backend non ricavava il campo da `column` | — |
| BE21-e ✅ | `get_conversione` legge la stessa vista; il drawer spegne interruttore e fine col motivo, come il form delle unità | `catalogo_repository.py`, `ConversioneUomDrawer.vue` |
| BE21-f ✅ | Ripiego di `E_UOM_RIGA_BASE_IMMUTABILE` allineato («non si cambia, non si spegne e non si toglie»); policy rigenerata (cambia solo la nota del codice, il CSV in git e il DB coincidono) | `error_messages_fallback.py`, `error_policies_generated.py` |
| BE26 ✅ | **Opzione A di Tid.** Le note di catalogo passano dal BB delle note (`make_note_views` + `PartitionedNoteService` + `PartitionedNoteRepository`), generalizzato: chiave del padre UUID (`target_id_uuid`), sede senza righe (l'àncora `RIGA` è 400 col campo, in creazione e in modifica), lista senza perimetro (`perimetro_emittente=False`), cancello del padre annidato (`cancello_padre`: il legame dev'essere dell'articolo, su ogni verbo). I vincoli di `catalogo.note` entrano nelle mappe del service. ⛔ Ritirati: la copia di `catalogo_service` (`_extract_nota_payload`, `_translate_nota_integrity_error`, `_resolve_single_nota`, le sei `fn_*nota*`), le tre view di `catalogo/api/views.py`, la rotta `/api/v1/catalogo/note/<id>/` e l'opzione `detailBase` di `makeNotesApi`. Il dettaglio di una nota sta ora sotto il padre | `apps/core/{db,services,api}/partitioned_note_*`, `catalogo/db/note_repositories.py`, `catalogo/api/note_views.py`, `catalogo/api/urls.py`, `frontend/src/core/api/notes.js`, `frontend/src/catalogo/api/catalogo.js` |
| BE27 ✅ | Niente da togliere: né il BE né il FE avvisavano «togli prima le note» o bloccavano la nota su un oggetto spento. Provato sul DB vero: un articolo con una nota si spegne, e la nota si scrive | — |
| BE28 ✅ | Nessuna ricaduta: il backend passa `user_*` com'è | — |

Regola del 2 lato FE (ok Tid, 2026-11-11): la lettura della capability delle conversioni è un helper di catalogo,
`src/catalogo/utils/capabilityConversioneUom.js`, usato dal form delle unità e dal drawer delle conversioni.
⚠️ Fail-closed: una riga senza capability non si spegne e non si chiude.

#### 16.5.2 Le prove

* Sul DB vero: `catalogo/tests/db/test_note_catalogo_db.py` nuovo (6: il giro intero con la chiave UUID, l'àncora
  RIGA, il testo vuoto, la nota di un altro articolo, l'articolo con note che si spegne, il padre che non c'è);
  `test_uom_storia_db.py` +5 (i campi fermi dal DB, il campo del rifiuto, la capability della mappatura e della
  conversione in lista e nel dettaglio, la riga base che non si spegne); `test_note_vincoli_mappati_db` e
  `test_note_confini_partizione_db` estesi a `catalogo.note`.
* Riallineati: `test_catalogo_api` (le rotte nuove, il cancello del legame su quattro verbi, nessun cancello di
  perimetro), `test_catalogo_service` (via i test delle note e i gap), `test_partitioned_note_service` (+3, la sede
  senza righe), `test_lista_proiezione_campo_sorgente` (la lista 22 esce: ha la vista), `test_ordinamento_liste`,
  `test_error_manager`, `test_catalogo_oggetti_rotte`.
* FE: `capabilityConversioneUom.spec.js` nuovo (5), `ArticoloUomForm.spec.js` +3, `ConversioneUomDrawer.spec.js` +1.
* Suite `apps.core` + `apps.catalogo` + `apps.vendite` col DB vero: 4895 test verdi. Vitest `src/catalogo` +
  `src/core`: 708 verdi. ruff, mypy a cricchetto, `genera_error_policies --check`, lint e cancelli FE,
  `check_i18n_keys` puliti.

#### 16.5.3 Segnalazioni

1. **Alla sessione DB — ritirare `E_CATALOGO_NOTA_NOT_FOUND`** (✅ deciso da Tid, 2026-11-11). Non lo solleva più
   nessuno: le note di catalogo rispondono coi codici del BB (`E_NOTA_NOT_FOUND`, `E_NOTA_PARENT_NOT_FOUND`), e
   nessun file Python lo nomina fuori dalla policy generata e dal ripiego. Da togliere: la riga di
   `config/codici_errore.csv` e quella di `config/messaggi_errore.csv` (`80_data`, dal CSV e non con un `UPDATE`,
   §11.2 di linee-guida-sql), più il codice in `work-in-progress/allegati/codici-errore-classe-note.csv`. **Dopo l'apply** il
   team BE rigenera `error_policies_generated.py` e toglie la voce da `error_messages_fallback.py`, nello stesso giro
   (mai rigenerare col DB avanti rispetto a git).
2. **Alla sessione DB — la proiezione delle note.** Il BB backend legge le partizioni con la sua proiezione
   (`_SELECT_COLUMNS`, stile e lingua in LEFT JOIN), per `vendite.note` e ora per `catalogo.note`. A catalogo la
   stessa proiezione è `catalogo.vw_note` (R6); a vendite una vista così non c'è. Con una `vendite.vw_note` gemella
   il BB potrebbe leggere la vista della sede in tutte e due, e la proiezione starebbe solo nel DB. Da valutare:
   oggi sono due sedi della stessa forma.
3. **A Tid — `seq` di una nota.** Il BB lo vuole ≥ 1 (`optional_smallint(min_val=1)`), il CHECK `chk_note_seq_pos`
   delle due madri ammette 0, e la vecchia copia di catalogo ammetteva 0. Con le note di catalogo sul BB, uno 0 ora
   è un 400 anche lì. Le strade: il BB si allinea al DB (≥ 0), o il DB stringe il CHECK (> 0). Non ho toccato niente.
4. **Fatto, non difetto:** `data_default_chiusura` viaggia nelle righe ma il FE non la usa ancora: per mappature e
   conversioni la fine si sceglie nel form, e il DatePicker di PrimeVue non ha una data proposta. Serve il giorno in
   cui ci sarà un'azione «Chiudi» di riga, come per la distinta.

#### 16.5.4 Verifica critica del giro BE (team BE, 2026-11-11, da committare su `dev/backend-tid`)

Una revisione del codice di §16.5, con le correzioni e le due decisioni di Tid del giorno.

| # | Che cosa | Dove |
| --- | --- | --- |
| V1 ✅ | **Un 500.** `GET …/note/?target_riga_id=<intero>` su una nota di catalogo arrivava al DB come `uuid = integer` (provato sul DB vero: `ProgrammingError`). Ora è 400 `E_NOTA_VALIDATION` col campo `target_riga_id`. La regola «niente note di riga in una sede senza righe» ha una sede sola, `_require_riga_ammessa`, per la scrittura e per la lettura; il controllo in `crea_nota` era irraggiungibile e se n'è andato. Test nuovo in `test_partitioned_note_service` | `partitioned_note_service.py` |
| V2 ✅ | **Presidi sul percorso sbagliato.** In `CatalogoBomRepository` restava la copia delle note (lista, pagina, dettaglio, risoluzione, scrittura, cancellazione e costanti), letta solo dai test: `test_lista_proiezione_campo_sorgente` (le due voci `catalogo.note`) e `test_ricerca_full_db` provavano la copia, e sarebbero stati verdi col BB rotto. Copia ritirata; i due presidi ora eseguono `NOTE_REPO_ARTICOLO` / `NOTE_REPO_ARTICOLO_COMPONENTE`. In `test_scritture_dinamiche_db` i casi delle note se ne vanno: le scritture del BB le presidia `test_scritture_email_note_db` | `catalogo_bom_repository.py`, i tre test |
| V3 ✅ | **Il campo `note` del dettaglio articolo è ritirato** (decisione di Tid): era una terza lettura delle note, e nessun lettore la usava. Le note si leggono dalla loro lista. Doc in `api_catalogo.md` | `catalogo_service.fn_get_articolo` |
| V4 ✅ | **Regola del 2 lato FE** (ok Tid): la frase del motivo e il «campo fermo nel PATCH» erano ricopiati identici nei due form; ora sono `fraseMotivoUom` e `fermoDallaCapability` nell'helper della capability (+2 test). Catalogo BB FE aggiornato | `capabilityConversioneUom.js`, `ArticoloUomForm.vue`, `ConversioneUomDrawer.vue` |
| V5 ✅ | Codice morto: `_extract_enum_string` di `catalogo_service` (lo usava la sola copia delle note) | `catalogo_service.py` |
| V6 ✅ | **Presidio delle proiezioni riaperto sulle conversioni.** La lista 22 era uscita da `test_lista_proiezione_campo_sorgente` perché «ha la vista», ma il repository la legge con la SUA proiezione (`_CONVERSIONE_COLONNE`): è il caso di `_ALTRE_QUERY`, come le UoM operative. Ora c'è; provato rosso togliendo una colonna dalla proiezione | `core/tests/db/test_lista_proiezione_campo_sorgente.py` |
| V7 ✅ | **Lo schema OpenAPI delle note di catalogo non promette più `target_riga_id`** (ok Tid): filtro e campo sarebbero sempre un 400. `make_note_views` ha `supporta_righe` (default `True`), che le note di catalogo prendono dal repository (`repo.supports_riga`). Test `NoteCatalogoSchemaTests` sullo schema generato, provato rosso senza la correzione; le note di vendita li tengono | `core/api/partitioned_note_views.py`, `catalogo/api/note_views.py` |

Prove: `apps.catalogo`, `apps.vendite`, `apps.core`, `apps.ui`, `apps.ai_assistant` col DB vero
(`ZEROERP_TEST_DB_E2E=1`) verdi; vitest `src/catalogo` + `src/core` verdi; ruff, mypy, eslint, `check_i18n_keys`,
`check_classi_morte` e `gen_indice_bb.py --check` puliti.

### 16.6 Q35 — Un kit con la distinta non si spegne più (team BE → sessione DB, 2026-11-11)

**Chi scrive:** team BE (`dev/backend-tid`), dal giro degli smoke. **A chi:** sessione DB. Via di Tid alla domanda,
2026-11-11; la scelta fra le strade è di Tid.

#### 16.6.1 Il fatto

Due decisioni, giuste ognuna per conto suo, si incrociano.

* **Il ritiro della PATCH del legame** (§14.10.3, ✅ Tid 2026-11-10): «un legame non ha più una scrittura oltre alla
  fine». `articoli_componenti.attivo` non lo cambia più nessuno: un legame nasce attivo e resta attivo, chiuso o no.
  Lo diceva già D4 (§2, «col modello "chiudi e inserisci" quei legami restano attivi»), ma solo per il guard IVA.
* **Q31** ha messo in `dbops.automazione_attivo_eccezioni` la mappatura e la conversione («è storia, non un figlio
  vivo: un articolo con una storia non si spegnerebbe mai»), e Q12 le note. **La distinta no**: il CSV
  (`80_data/sql/dbops/automazione_attivo_eccezioni.csv`, verificato il 2026-11-11) non ha righe per
  `articoli_componenti`.

**Quindi:** il BLOCK generato su `articoli_componenti.prodotto_id` (e, per costruzione, su `.componente_id`) impedisce
per sempre di spegnere un articolo che è stato kit, e, salvo verifica, un articolo che è stato componente di una
distinta qualsiasi. È lo stesso difetto che Q31 ha chiuso per le mappature.

**Visto da:** `smoke-test-catalogo-phase3.sh` (passo 17, spegnere il padre) e `smoke-test-preventivi-componenti.sh`
(pulizia, spegnere il composito): tutti e due `409 E_ATTIVO_BLOCK_CHILDREN_ACTIVE` sulla distinta, dopo che il
legame è stato chiuso col verbo. I due rossi restano **apposta**: sono il presidio di questa domanda, non della
fixture.

⚠️ Anche il motivo della riga `note_articoli_componenti.target_id` del CSV (giro 4) dice «il legame di distinta si
spegne e si riaccende con le sue note»: dal ritiro della PATCH non è più vero.

#### 16.6.2 La domanda

**Q35.** Un articolo che ha (o ha avuto) una distinta, da padre o da componente, si deve poter spegnere?

* **(a) Eccezione, la forma di Q31 (proposta).** `articoli_componenti.prodotto_id` e `.componente_id` in
  `automazione_attivo_eccezioni`: il legame è storia («chiudi e inserisci»), non un figlio vivo. Il kit si spegne e
  si riaccende con la distinta intatta; una riga di documento su un kit o un componente spento la fermano già i
  REQUIRE del documento verso l'articolo. Il motivo della riga delle note del legame si riscrive.
* **(b) Un verbo «spegni legame».** Il brief lo ammette (§14.10.3: «se servisse… è un verbo nuovo»). Rimette in vita
  uno stato del legame che la chiusura rende inutile, e il kit si spegnerebbe solo dopo aver spento tutta la sua
  storia a mano: è la (b) scartata in Q31.

#### 16.6.3 Da verificare con (a), alla sessione DB

1. **Il lato componente.** Con l'eccezione se ne va anche il REQUIRE, non solo il BLOCK (§16, punto 3 del giro 4).
   Va visto chi rifiuta oggi, oltre all'automazione ATTIVO: un legame **nuovo** verso un componente spento o sotto un
   padre spento (`fn_check_articolo_riga` lato componente, la check `ARTICOLO` di R3); un componente spento con un
   legame **in vigore** (l'init dei componenti di documento, il BB della distinta alla data, il picker). Se uno di
   questi si reggeva solo sul REQUIRE generato, va scritto prima dell'eccezione.
2. **I legami già attivi** non cambiano: nessun backfill.
3. **I pgTAP** che spegnevano la distinta o l'articolo nell'ordine «figli prima del padre» (come per Q34).

#### 16.6.4 Ricadute sul BE e sugli smoke

* **BE:** nessuna con (a). Il servizio di disattivazione non spegne figli. Con (b), un verbo e una rotta nuovi.
* **Smoke già riallineati** (team BE, 2026-11-11, da committare su `dev/backend-tid`), sul modello deciso:
  `catalogo-crud` (Q34: la base non si spegne, 409 `E_UOM_RIGA_BASE_IMMUTABILE`; Q31: l'articolo si spegne con la base
  accesa), `catalogo-phase3` (la chiusura dal verbo `…/chiudi/`; le rotte note del BB; via gli spegnimenti di legami e
  basi), `preventivi-componenti` (pulizia: legame chiuso col verbo, base non toccata). Dopo l'apply di (a) i due
  smoke rossi tornano verdi **senza modifiche**: è la prova del giro.

