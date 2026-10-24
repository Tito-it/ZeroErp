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

(rev 2026-08-28)

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
  `ordine_origine_numero`.

> ### ⚠️ La provenienza ha due popolazioni, dal 2026-08-28
>
> `sorgente_codice_interno` non è più solo `ORDINE_VENDITA`: un **DDT di ri-consegna
> standalone** dichiara `RESO_VENDITA`, con l'`uid` del reso in `sorgente_uid`
> ([`fn_genera_ddt_riconsegna`](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)).
> Su quelle righe la lista dice **da dove viene il documento** e lascia
> `ordine_origine_numero` vuoto, perché un ordine non c'è.
>
> ⭐ **Per questo il join a `vendite.ordini` è ora qualificato sul tipo sorgente.**
> Prima traduceva `sorgente_uid` in un ordine **senza guardare che tipo di sorgente
> fosse**: con una sorgente RESO il join non trovava nulla — l'esito giusto — ma ci
> arrivava per **assenza di collisioni fra spazi di uuid**, non per decisione.
>
> > *Un join che risponde bene per una proprietà che nessuno ha dichiarato è un
> > presidio che non c'è.* Costa una condizione, e toglie una domanda a chi legge
> > la vista fra sei mesi.
>
> ⚠️ Per **risolvere** una sorgente qualunque in «id del documento + numero
> leggibile» esiste già
> [`vendite.fn_get_sorgente_documento_ref`](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref),
> che gestisce la chiave polimorfa (`key_selector`) e l'etichetta
> (`label_selector`). Questa vista **non** la chiama — è una lista, e una funzione
> per riga sarebbe N chiamate — ma chi avesse bisogno del numero della sorgente
> generica usi quella, non un secondo join scritto a mano.

* **Scope emittente**: `emittente_fiscale_id` alimenta il **filtro applicativo** del repository BE
  (`= ANY(script.fn_get_emittenti_scope_pk_ids(auth_user_id))`, defense-in-depth) e la policy RLS
  `rls_ddt_ef_whitelist` su `vendite.ddt` (§15).
* Nomi canonici: `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `ba_codice`,
  `stato_codice_interno`. `numero` è NULL in DRAFT, valorizzato a EMESSO.

La definizione lista + colonne è in `ui.lista_definizione` / `ui.lista_colonna`
(`codice = vendite.ddt`).

---

### 🔄 rev 2026-10-11 — la lista non calcola più il grafo

Changeset `20261011-97`. La vista non legge più la sintesi della lineage di tutti
i documenti. Le colonne della frontiera e del transito (`frontiera_*`,
`n_discendenti_attivi`, `is_transitato`) le chiede il backend a
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md) per i soli
documenti della pagina. La pratica (`pratica_id`, `pratica_numero`,
`n_pratiche`) resta qui, filtrabile e ordinabile, e la legge
`pratiche.fn_pratica_del_documento`. Una pagina da 25 righe costava ~320-390 ms,
ora ~8-70 ms più la sintesi delle 25 chiavi (~58 ms) — dbdev, 2026-10-11.

