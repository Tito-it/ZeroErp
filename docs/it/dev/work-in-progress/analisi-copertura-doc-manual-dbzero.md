# Copertura documentazione manuale `docs/it/dbzero` — il buco misurato

> Analisi del 2026-08-21 — **misura**, non piano approvato.
> Riguarda solo `docs/it/dbzero/<schema>/manual/`: la doc concettuale scritta a mano
> che si affianca a quella auto-generata da `scripts/gen_db_docs.py`.
>
> ### 📌 Stato al 2026-08-21
>
> **Fascia A chiusa** — scritti i 35 manuali delle trigger function (§4, fascia A).
> Il buco passa da **247 a 212** oggetti, copertura da **80,7 % a 83,4 %**.
>
> ⚠️ **I 35 file esistono ma non sono ancora inclusi.** Il tag `include-markdown` lo
> scrive `gen_db_docs.py` quando rigenera l'auto-gen: finché non gira, le pagine
> `<schema>/funzioni/trgfn_*.md` non mostrano il testo manuale e gli `index.ci.md`
> non elencano quelle funzioni. Ripetendo oggi il comando di misura di §1 si
> otterrebbero ancora 247: è atteso, e sparisce alla prima rigenerazione.

---

## 1. Come è stata fatta la misura

`scripts/gen_db_docs.py` scrive in testa a ogni file auto-generato un tag `include-markdown`
che punta a `it/dbzero/<schema>/manual/<nome>.md` — **solo se quel file manuale esiste già**
(funzione `include_manual`, righe 54-58). Quindi:

> **un documento auto-generato che NON comincia con il tag `include-markdown` è
> esattamente un oggetto senza doc manuale.**

Il conteggio è quello, su tutti i `.md` in `<schema>/tabelle|views|funzioni`:

```bash
cd docs/it/dbzero
find . -path './*/tabelle/*.md' -o -path './*/views/*.md' -o -path './*/funzioni/*.md' \
  | while read -r f; do head -3 "$f" | grep -q 'include-markdown' || echo "$f"; done
```

Le date di comparsa citate più sotto vengono da `git log --diff-filter=A` sul file auto-generato.

## 2. Perché il buco non si vede

Non produce nessun errore di build, e nemmeno un warning. Produce due effetti silenziosi:

1. In `<schema>/index.md` l'oggetto **c'è**, ma come link nudo, senza la riga di descrizione
   (`- [fn_accoda_stampe_lotto](funzioni/fn_accoda_stampe_lotto.md)` e basta).
2. In `<schema>/index.ci.md` — l'indice «solo contenuti manuali» — l'oggetto **non compare
   affatto**. Chi consulta quell'indice non sa che l'oggetto esiste.

Non esiste oggi nessun guardrail CI su questa copertura (`scripts/` ha solo
`guardrail_no_db_migrate.py`, `guardrail_pgtap_preambolo.py`, `guardrail_run_on_change.py`).

## 3. I numeri

- **1278** documenti auto-generati (tabelle + views + funzioni) su 16 cartelle schema
  popolate (`contabilita`, `preventivi`, `public`, `tools`, `topology` sono vuote).
- **247** senza doc manuale alla misura iniziale → copertura **80,7 %**.
  Dopo la fascia A: **212** → **83,4 %**.
- Ripartizione per tipo alla misura iniziale: **155 tabelle**, **73 funzioni**, **19 viste**.
  Le 35 funzioni della fascia A sono ora scritte: restano **38 funzioni**.
- **0** casi di tag `include-markdown` che punta a un file manuale mancante: il buco è
  sempre e solo «manuale mai scritto», mai «manuale cancellato».
- **5** file manuali orfani (§5).

| Schema | tabelle | views | funzioni | mancanti | tot autogen | copertura |
|---|---:|---:|---:|---:|---:|---:|
| `storico` | 102 | — | — | **102** | 111 | 8% |
| `magazzino` | 25 | 4 | 2 | **31** | 32 | 3% |
| `vendite` | — | 5 | 21 | **26** | 375 | 93% |
| `dbops` | 5 | 4 | 16 | **25** | 116 | 78% |
| `script` | — | — | 15 | **15** | 154 | 90% |
| `config` | 11 | 2 | 1 | **14** | 139 | 90% |
| `anagrafiche` | 2 | 4 | 6 | **12** | 139 | 91% |
| `acquisti` | 6 | — | 2 | **8** | 11 | 27% |
| `pratiche` | — | — | 7 | **7** | 96 | 93% |
| `catalogo` | 2 | — | 3 | **5** | 27 | 81% |
| `maintenance` | 1 | — | — | **1** | 19 | 95% |
| `pagamenti` | 1 | — | — | **1** | 17 | 94% |

In tabella solo gli schemi con almeno un buco: `documenti` (21), `ui` (19) e `shop` (2)
sono al 100 %.

Il buco non è un arretrato di un periodo: le date di comparsa si distribuiscono su tutta la
storia del repo, con **30 oggetti nati nel solo agosto 2026** (presidio codici errore,
riferimenti morti, accrediti resi, guard immutabilità).

---

## 4. Le fasce, in ordine di quanto costa non averle

### ✅ Fascia A — regole di business non descritte da nessuna parte (35 trigger function) — **CHIUSA 2026-08-21**

Sono i `trgfn_*`: guard di transizione, default, snapshot, normalizzazioni. Il corpo SQL è
nell'auto-gen, ma **il perché** (quale regola di dominio difendono, quale codice errore
sollevano, che cosa rompe toglierli) non era scritto. Era la fascia che valeva di più.

**Tutti e 35 i manuali sono stati scritti.** Ogni pagina riporta: scopo di dominio, aggancio
esatto (trigger, timing, `UPDATE OF`, clausola `WHEN`), regole applicate, tabella dei codici
errore e le trappole emerse leggendo il codice. Elenco sotto, per riferimento.

Le trappole ricorrenti trovate scrivendo — utili di per sé, indipendentemente dalla doc:

* **La condizione che rende il guard corretto sta spesso nel `WHEN` del trigger, non nella
  funzione.** Vale per `trgfn_unita_misura_guard_tipo_update`,
  `trgfn_sospensioni_giornale_riattivazione`,
  `trgfn_contratti_righe_guard_esclusione_figlio_bundle`. Riagganciare la funzione altrove
  senza copiare il `WHEN` cambia il comportamento in silenzio.
* **L'ordine alfabetico dei `BEFORE ROW` decide quale errore vede l'utente.** Su
  `vendite.preventivi` `guard_annullamento` parla prima di `guard_transizione`; sui
  `gen_codice`, `gen_codice` gira prima di `lock_columns`.
* **Due `E_GENERICO` nello schema `catalogo`** (`trgfn_unita_misura_guard_tipo_update`,
  `trgfn_uom_conversioni_guard_tipo`) e **una `RAISE EXCEPTION` diretta**
  (`trgfn_event_log_append_only`, che quindi non registra nulla in `error_log`).
* **Tre presidi che il database non ha**, scoperti confrontando tabelle gemelle:
  `vendite.offerte_commerciali.codice` senza `lock_columns` (un `UPDATE` che lo azzera ne
  rigenera uno nuovo), `vendite.preventivi_righe.natura_vendita_id` modificabile a mano
  aggirando l'ereditarietà, `anagrafiche.vettori.codice` `NOT NULL` senza nessun generatore.
* **`trgfn_vettori_normalize` è un no-op** e il suo `COMMENT` rimanda a un `sistema_codici`
  che per i vettori non ha nessuna riga.

- `anagrafiche.trgfn_billing_account_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_fornitori_gen_codice` — dal 2026-03-29
- `anagrafiche.trgfn_istanze_utilities_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_soggetti_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_vettori_guard_ruolo_vettore`
- `anagrafiche.trgfn_vettori_normalize`
- `catalogo.trgfn_articoli_seed_uom_base` — dal 2026-04-07
- `catalogo.trgfn_unita_misura_guard_tipo_update` — dal 2026-04-28
- `catalogo.trgfn_uom_conversioni_guard_tipo` — dal 2026-04-28
- `config.trgfn_stati_doc_guard_esito_verdetto` — dal 2026-07-02
- `pratiche.trgfn_calcoli_tempo_set_periodo` — dal 2026-04-13
- `pratiche.trgfn_flussi_guard_esito_completato` — dal 2026-06-08
- `pratiche.trgfn_pratiche_gen_codice` — dal 2026-03-29
- `pratiche.trgfn_sospensioni_giornale_ins` — dal 2026-03-06
- `pratiche.trgfn_sospensioni_giornale_riattivazione` — dal 2026-03-06
- `pratiche.trgfn_sospensioni_set_periodo` — dal 2026-04-13
- `script.trgfn_righe_default_fonte_qta`
- `vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile` — dal 2026-07-21
- `vendite.trgfn_commesse_attivita_guard_prezzo_rettifica` — dal 2026-08-20
- `vendite.trgfn_commesse_attivita_guard_quantita_immutabile` — dal 2026-07-21
- `vendite.trgfn_contratti_default_valuta` — dal 2026-05-30
- `vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle` — dal 2026-05-16
- `vendite.trgfn_contratti_set_categoria_cliente_snapshot` — dal 2026-04-17
- `vendite.trgfn_contratti_sync_is_abortito_snapshot` — dal 2026-05-21
- `vendite.trgfn_contratti_utilities_guard_tipo_classe` — dal 2026-04-14
- `vendite.trgfn_event_log_append_only` — dal 2026-02-27
- `vendite.trgfn_listini_righe_guard_tipologia` — dal 2026-04-14
- `vendite.trgfn_lotto_fatture_guard_stato_coerente` — dal 2026-07-22
- `vendite.trgfn_offerte_commerciali_default_valuta` — dal 2026-05-30
- `vendite.trgfn_offerte_commerciali_gen_codice` — dal 2026-05-25
- `vendite.trgfn_offerte_commerciali_guard_transizione` — dal 2026-05-24
- `vendite.trgfn_preventivi_default_valuta` — dal 2026-05-30
- `vendite.trgfn_preventivi_guard_annullamento` — dal 2026-08-04
- `vendite.trgfn_preventivi_guard_transizione` — dal 2026-08-05
- `vendite.trgfn_preventivi_righe_set_natura_vendita` — dal 2026-06-08

### Fascia B — verbi, check e madri di dominio (10 funzioni)

- `pratiche.fn_log_evento_dominio` — dal 2026-06-08
- `script.fn_check_commessa_annullabile` — dal 2026-07-24
- `script.fn_check_commessa_chiudibile` — dal 2026-07-24
- `script.fn_check_commessa_pronta_fatturazione` — dal 2026-08-04
- `script.fn_check_ordine_annullabile` — dal 2026-08-04
- `script.fn_check_preventivo_annullabile` — dal 2026-08-04
- `script.fn_disdetta_cliente` — dal 2026-03-01
- `vendite.fn_accoda_stampe_lotto` — dal 2026-07-20
- `vendite.fn_annulla_accredito_riga_reso` — dal 2026-08-18
- `vendite.fn_guard_lotto_fatture_stato_coerente` — dal 2026-07-22

### Fascia C — viste consumate da BE/FE (9 viste)

Viste di lista UI, riepiloghi IVA, liste di lavoro. Chi le consuma ha bisogno di sapere
che cosa garantiscono (scope? snapshot o live?), e quella riga non c'è.

- `anagrafiche.vw_clienti_codice_ba` — dal 2026-03-12
- `anagrafiche.vw_clienti_lista` — dal 2026-05-08
- `anagrafiche.vw_fornitori_dettaglio` — dal 2026-03-25
- `anagrafiche.vw_pdp` — dal 2025-12-07
- `vendite.vw_contratti_lista` — dal 2026-06-02
- `vendite.vw_ddt_riepilogo_iva_dettaglio` — dal 2026-07-11
- `vendite.vw_ddt_righe_iva_base` — dal 2026-07-11
- `vendite.vw_lotti_fatture_incoerenti` — dal 2026-07-22
- `vendite.vw_preventivi_riepilogo_iva_dettaglio` — dal 2026-05-02

### Fascia D — tabelle di dominio e vocabolari `config` (13 tabelle)

- `anagrafiche.vettori` — dal 2025-09-05
- `catalogo.note_articoli` — dal 2026-01-13
- `catalogo.note_articoli_componenti` — dal 2026-01-13
- `config.ambiti` — dal 2025-05-23
- `config.aspetti_beni` — dal 2025-09-05
- `config.categoria_accisa` — dal 2025-08-30
- `config.classi_utenze` — dal 2025-08-30
- `config.nature_vendita` — dal 2026-06-08
- `config.tipi_tariffe_ee` — dal 2025-08-30
- `config.tipi_ubicazione` — dal 2025-10-06
- `config.tipi_utenze` — dal 2025-08-30
- `config.user_emittente_attivo` — dal 2026-08-04
- `pagamenti.sepa_mandati` — dal 2025-08-31

### Fascia E — presidio codici errore e riferimenti morti (12 oggetti, tutti agosto 2026)

Infrastruttura nata da poco e già citata in memoria e nei brief. Hanno `COMMENT` ricchi
sull'oggetto: la doc manuale qui è per metà già scritta, va portata in pagina.

- `config.classi_errore` — tabelle · dal 2026-08-07
- `config.codici_errore` — tabelle · dal 2026-08-07
- `config.vw_codici_errore` — views · dal 2026-08-07
- `config.vw_codici_errore_identita` — views · dal 2026-08-07
- `dbops.fn_check_funzioni_riferimenti_morti` — funzioni · dal 2026-08-04
- `dbops.codici_errore_senza_policy` — tabelle · dal 2026-08-05
- `dbops.messaggi_errore_codici_legacy` — tabelle · dal 2026-08-05
- `dbops.riferimenti_morti_esenzioni` — tabelle · dal 2026-08-04
- `dbops.vw_codici_errore_da_dichiarare` — views · dal 2026-08-05
- `dbops.vw_codici_errore_forme_condizione` — views · dal 2026-08-07
- `dbops.vw_riferimenti_morti_da_sanare` — views · dal 2026-08-04
- `dbops.vw_riferimenti_morti_rientrati` — views · dal 2026-08-04

### Fascia F — schema `magazzino` quasi interamente scoperto (31 oggetti, 1 solo manuale esistente)

`magazzino/manual/` contiene **un** file (`assets.md`). Tutto il resto — ledger movimenti,
costo medio, inventari, rettifiche, trasferimenti, ubicazioni, prenotazioni — è senza doc
concettuale. Stessa storia, in scala minore, per `acquisti` (8 oggetti).

- `magazzino.fn_get_magazzino_note` — funzioni · dal 2025-10-05
- `magazzino.trgfn_magazzini_normalize` — funzioni
- `magazzino.ambito_causale` — tabelle · dal 2025-10-02
- `magazzino.causali` — tabelle · dal 2025-10-02
- `magazzino.costo_medio` — tabelle · dal 2025-10-05
- `magazzino.eventi_assets` — tabelle · dal 2025-10-02
- `magazzino.inventari` — tabelle · dal 2025-10-05
- `magazzino.inventari_righe` — tabelle · dal 2025-10-05
- `magazzino.magazzini` — tabelle · dal 2025-09-05
- `magazzino.movimenti` — tabelle · dal 2025-10-02
- `magazzino.note` — tabelle · dal 2025-10-05
- `magazzino.note_asset` — tabelle · dal 2025-10-05
- `magazzino.note_costo_medio` — tabelle · dal 2025-10-05
- `magazzino.note_evento_asset` — tabelle · dal 2025-10-05
- `magazzino.note_inventario` — tabelle · dal 2025-10-05
- `magazzino.note_inventario_riga` — tabelle · dal 2025-10-05
- `magazzino.note_movimento` — tabelle · dal 2025-10-05
- `magazzino.note_rettifica` — tabelle · dal 2025-10-05
- `magazzino.note_rettifica_riga` — tabelle · dal 2025-10-05
- `magazzino.note_trasferimento` — tabelle · dal 2025-10-05
- `magazzino.note_trasferimento_riga` — tabelle · dal 2025-10-05
- `magazzino.reservations` — tabelle · dal 2025-10-02
- `magazzino.rettifiche` — tabelle · dal 2025-10-05
- `magazzino.rettifiche_righe` — tabelle · dal 2025-10-05
- `magazzino.trasferimenti` — tabelle · dal 2025-10-05
- `magazzino.trasferimenti_righe` — tabelle · dal 2025-10-05
- `magazzino.ubicazioni` — tabelle · dal 2025-10-06
- `magazzino.vw_costo_medio` — views · dal 2025-10-05
- `magazzino.vw_costo_medio_globale` — views · dal 2025-10-05
- `magazzino.vw_giacenza` — views · dal 2025-10-05
- `magazzino.vw_giacenza_valorizzata` — views · dal 2025-10-05

E `acquisti`:

- `acquisti.fn_get_acquisti_note` — funzioni · dal 2025-10-05
- `acquisti.trgfn_acq_ordini_only_consegna_tipo_con` — funzioni
- `acquisti.ddt` — tabelle · dal 2025-09-17
- `acquisti.ddt_indirizzi` — tabelle · dal 2025-09-17
- `acquisti.ddt_righe` — tabelle · dal 2025-09-17
- `acquisti.ordini` — tabelle · dal 2025-09-17
- `acquisti.ordini_righe` — tabelle · dal 2025-09-17
- `acquisti.ordini_righe_fulfillment` — tabelle · dal 2025-09-17

### Fascia G — fixture pgTAP e utility tecniche (7 + 11)

Qui una pagina per oggetto è sproporzionata: meglio **una pagina sola** per famiglia
(«le fixture pgTAP», «le façade di log») e i manuali dei singoli che ci rimandano.

Fixture pgTAP:

- `dbops.fn_pgtap_cf_libero` — dal 2026-08-19
- `dbops.fn_pgtap_crea_soggetto_pg` — dal 2026-08-19
- `dbops.fn_pgtap_crea_soggetto_ruolo` — dal 2026-08-19
- `dbops.fn_pgtap_piva_libera` — dal 2026-08-19
- `script.fn_pgtap_emittente_operatore` — dal 2026-08-05
- `script.fn_pgtap_emittente_sr_operatore` — dal 2026-08-07
- `script.fn_pgtap_set_contesto_operatore` — dal 2026-08-05

Utility e façade:

- `dbops.fn_admin_merge_comune` — funzioni · dal 2025-05-23
- `dbops.fn_admin_merge_stradario` — funzioni · dal 2025-05-23
- `dbops.fn_col_exists` — funzioni · dal 2025-08-21
- `dbops.fn_list_indices` — funzioni · dal 2025-05-23
- `dbops.fn_normalize_indirizzo` — funzioni · dal 2025-05-23
- `dbops.ai_query_log` — tabelle · dal 2026-03-31
- `script.fn_get_vie_discendenti` — funzioni · dal 2025-05-23
- `script.fn_log` — funzioni · dal 2026-08-07
- `script.fn_norm_testo` — funzioni · dal 2025-09-05
- `script.fn_norm_via` — funzioni · dal 2025-09-05
- `script.log` — funzioni · dal 2025-08-22

### Fascia H — da valutare per rimozione, non per documentazione (9)

One-shot di migrazione già consumati, backup, tabelle legacy. Documentarli significa
promuoverli a oggetti di progetto: la domanda giusta è se debbano ancora esistere.

- `anagrafiche._legacy_risorse_umane_auth_user` — tabelle · dal 2026-04-19
- `dbops.fn_cleanup_triggers_suffix_2` — funzioni · dal 2025-09-22
- `dbops.fn_fix_lock_codice_interno_triggers` — funzioni · dal 2025-09-22
- `dbops.fn_fix_triggers_event_tokens` — funzioni · dal 2025-09-22
- `dbops.fn_fix_triggers_events_noorder` — funzioni · dal 2025-09-22
- `dbops.fn_migrate_add_indirizzo_normalizzato` — funzioni · dal 2025-05-23
- `dbops.fn_rename_triggers_by_order` — funzioni · dal 2025-09-22
- `dbops._defaults_backup_usercols` — tabelle · dal 2025-10-08
- `maintenance.test_pgagent_log` — tabelle · dal 2025-08-11

### Fascia I — `storico` (102 tabelle): boilerplate, non prosa

Le 9 pagine `storico/manual/` esistenti sono tutte lo stesso testo con il nome cambiato
(«mantiene la cronologia completa dei record di `X`…»). Per **83** delle 102 mancanti la
tabella-fonte **ha già** una doc manuale da cui derivare il testo: è generazione, non scrittura.

Le altre **19** non hanno fonte documentata (documentare prima la fonte, poi lo storico):

`storico.ambito_causale`, `storico.causali`, `storico.comune_trasformazioni`, `storico.eventi_assets`, `storico.fatturazione_lotti_attivita`, `storico.inventari`, `storico.inventari_righe`, `storico._legacy_risorse_umane_auth_user`, `storico.magazzini`, `storico.movimenti`, `storico.reservations`, `storico.rettifiche`, `storico.rettifiche_righe`, `storico.sepa_mandati`, `storico.stradario_trasformazioni`, `storico.trasferimenti`, `storico.trasferimenti_righe`, `storico.user_emittente_attivo`, `storico.vettori`

---

## 5. Il verso opposto: manuali orfani (5)

File in `manual/` senza nessun auto-generato corrispondente. O l'oggetto è stato rinominato
o rimosso dal DB e la pagina è rimasta, oppure sono pagine tematiche messe nella cartella
sbagliata (`catasto-architettura`, `trigger_business_overview` sembrano il secondo caso).

- `anagrafiche/manual/catasto-architettura.md`
- `anagrafiche/manual/trgfn_emittenti_fiscali_guard_attivo.md`
- `pratiche/manual/trgfn_sospensioni_giornale.md`
- `pratiche/manual/trigger_business_overview.md`
- `public/manual/version_info.md`

---

## 6. Proposta operativa

L'ordine sopra è già la proposta: **A → C → E → B → D → F**, poi decidere su G/H/I.
**A è fatta.** Il prossimo passo è **C** (le 9 viste consumate da BE/FE), che è l'altra
superficie che oggi costa davvero.

Due cose da tenere presenti mentre si scrive:

- ⚠️ **Non toccare mai i file in `tabelle/`, `views/`, `funzioni/`**: si rigenerano e il tag
  `include-markdown` compare da solo alla prima rigenerazione dopo la creazione del manuale.
- ⚠️ I link interni vanno nella forma `/dbzero/<schema>/<tipo>/<nome>` (senza `.md`), come
  nelle pagine esistenti. Il guardrail dei riferimenti morti gira **dopo** `manage.py migrate`.

**Da decidere prima di partire** (non lo decido io):

1. Fascia H: documentare o rimuovere?
2. Fascia I (`storico`): 102 pagine generate da template, oppure **una** pagina di schema e
   nessuna pagina per tabella?
3. Fascia G: pagina-famiglia o pagina per oggetto?
4. Serve un guardrail CI che impedisca al buco di riaprirsi (fallisce se un oggetto nuovo
   di dominio nasce senza manuale)?
