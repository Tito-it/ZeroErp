## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_lista`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)
> [config.aspetti_beni](/dbzero/config/tabelle/aspetti_beni)
> [config.modalita_addebito_trasporto](/dbzero/config/tabelle/modalita_addebito_trasporto)
>
> Correlati:
> [vendite.vw_ordini_lista](/dbzero/vendite/views/vw_ordini_lista) (mirror)
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)
> [Configurazione, personalizzazione e responsività delle liste](/guide/configurazione-liste)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

Vista sorgente **canonica e self-contained** per la lista configurabile del DDT
(`<ListaConfigurabile>`). Mirror di `vw_ordini_lista`: pura **denormalizzazione** (JOIN + campi
display), **nessun** filtro/scope/paginazione (restano nel repository BE).

* **`security_invoker = on`**: la vista gira col contesto del chiamante → le policy RLS di
  `vendite.ddt` si applicano (no RLS cosmetica).
* Espone: identificazione (numero/anno/serie/data), stato (`stato_codice_interno`/`stato_descrizione`),
  **destinatario** (soggetto_ruolo NOT NULL) + **mittente**/**vettore** (nullable),
  billing/utility/valuta, **`emittente_fiscale_id` + `emittente_fiscale_codice`** (scope, §15),
  campi **trasporto** (causale, aspetto, modalità addebito, colli/pesi/volume,
  targa, autista, date, tracking) per il PDF, e la **provenienza**: `sorgente_codice_interno` +
  `ordine_origine_numero` (ordine risolto via `sorgente_uid`).
* **Scope emittente**: `emittente_fiscale_id` alimenta il **filtro applicativo** del repository BE
  (`= ANY(script.fn_get_emittenti_scope_pk_ids(auth_user_id))`, defense-in-depth) e la policy RLS
  `rls_ddt_ef_whitelist` su `vendite.ddt` (§15).
* Nomi canonici: `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `ba_codice`,
  `stato_codice_interno`. `numero` è NULL in DRAFT, valorizzato a EMESSO.

La definizione lista + colonne è in `ui.lista_definizione` / `ui.lista_colonna`
(`codice = vendite.ddt`).
