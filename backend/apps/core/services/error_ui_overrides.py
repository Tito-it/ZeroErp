# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: le `ui_action` che NON seguono il default della loro classe.
#        Qui stanno quelle che se ne discostano (il numero lo dice `len`, non
#        questo commento), ognuna con la ragione per cui lo fa.
# Note: ⚠️ Questo file e' SCRITTO A MANO e non va generato. Le voci non sono
#        dati, sono decisioni con una motivazione: un CSV non porta un paragrafo,
#        e i paragrafi qui sotto sono il ragionamento del cantiere del terzo lato
#        (brief §14.2). Cambia quando cambia una scelta di interfaccia.
#        ⚠️ Su `DATO_ERRATO` il default non e' una maggioranza: e' 117 contro
#        117. Il discriminante vero non e' la classe ma DOVE manca il dato — sul
#        form che l'operatore sta compilando (`highlight_form_fields`) o
#        sull'entita' collegata (`show_error_banner`) — ed e' un'informazione che
#        la classe non porta e non puo' portare. Il default scelto e' il banner
#        perche' e' il piu' prudente: promettere un campo da evidenziare che non
#        esiste e' peggio del contrario.
#        ⚠️ Lo stesso vale, con piu' forza, su `NON_AUTENTICATO`: due
#        `redirect_login` contro due banner. Li' un default sbagliato butta
#        l'operatore fuori dall'applicazione, quindi i due `redirect_login` sono
#        override espliciti e il default resta il banner.
# ------------------------------------------------------------


# codice -> ui_action, quando diversa dal default della classe.
#
# ⛔ SEDICI OVERRIDE `highlight_form_fields` TOLTI IL 2026-09-21 (presidio C2,
#    brief-be-presidio-ui-action-e-canale-campi §3-ter, decisione di Tid):
#      E_CORE_VALIDATION, E_SEARCH_VALIDATION, E_IDEMPOTENCY_KEY_REQUIRED,
#      E_INVALID_ID, E_PIPELINE_VALIDATION, E_FATTURAZIONE_GIRO_PAYLOAD,
#      E_FATTURAZIONE_NUMERA_PAYLOAD, E_GENERATE_FATTURE_RIGHE_VALIDATION,
#      E_GROUP_ATTIVITA_VALIDATION, E_RESET_LOTTO_VALIDATION,
#      E_RESET_LOTTO_FATTURA_VALIDATION, E_NOTA_RIGA_INCOERENTE,
#      E_FLUSSO_ID_OBBLIGATORIO, E_FLUSSO_ID_INVALIDO, E_PRATICA_ID_OBBLIGATORIO,
#      E_PRATICA_ID_INVALIDO (sedici, con questi quattro: query string di GET).
#    Tornano al banner di classe (DATO_ERRATO). La promessa era SBAGLIATA, non
#    il canale: letti tutti i loro siti, nessuno ha un input del form da
#    accendere — parametri di query string e di paginazione, un header
#    (`Idempotency-Key`), `<x>_id deve essere > 0` su parametri di firma
#    (47 siti), stati non configurati, payload di un lavoro in coda letto dal
#    drenatore, legami fra id. `highlight_form_fields` promette un input
#    NELLA PAGINA in cui l'operatore si trova (api.md §Envelope): un nome che
#    non e' il nome di un input non va promesso. A video oggi non cambia
#    niente (nessun consumatore ramifica su questo valore); cambia il
#    contratto, ed e' la finestra in cui riguardare le righe costa zero.
# ⛔ E ALTRI SETTE, la sera dello stesso giorno, dal lato DB (§4-bis.3): i
#    codici a soli siti PL/pgSQL letti uno per uno dal team DB con la stessa
#    regola A/B — dove il guard ha in mano la colonna di un input il DB ha
#    aggiunto `'campo'` al context (30 codici, changeSet 20260921-43…49);
#    dove il nome e' un parametro di firma, un id dall'URL o un'invariante la
#    promessa era sbagliata e l'override esce da qui:
#      E_ARTICOLO_NON_COMPOSITO (`prodotto_id` e' la pagina in cui si sta),
#      E_COERENZA_ID (righe scritte dalla pipeline, non da un form),
#      E_FORNITORE_ID_INVALIDO (`p_fornitore_id` di firma),
#      E_NOTE_TARGET_ID (`target_riga_id`: un legame, non un input),
#      E_SOGGETTO_NULL (parametri di `fn_get_or_create_soggetto_ruolo`),
#      E_SORG_KEY_MISSING (invariante della sorgente polimorfa),
#      E_STATO_SORGENTE_PARAM_INVALIDO (parametri di `fn_stato_sorgente`).
#    Tornano al banner di classe (DATO_ERRATO). Da qui in poi il presidio e'
#    `apps/core/tests/test_ui_action_e_canale_campi.py`: un override
#    `highlight_form_fields` senza un sito che mandi il campo e' rosso.
# ⛔ E TRE, trovati dal presidio appena acceso (§4-ter, ok di Tid 21-09):
#      E_PIPELINE_SCOPE_INCOMPLETE (fatture del lotto senza utility/tipo
#        doc/valuta, o `lock_batch_id` assente: il rimedio non sta su questa
#        pagina),
#      E_SORG_FORMATO, E_SORG_NORM_NON_RISOLTA (chiave della sorgente
#        polimorfa: convenzione del chiamante, come E_SORG_KEY_MISSING).
UI_ACTION_OVERRIDE: dict[str, str] = {
    # ══════════════════════════════════════════════════════════════════
    # Codici DB fuori convenzione `E_*` — registro del debito
    # (brief-db-codice-errore-strutturato §7, decisione Tid 2026-08-05)
    # ══════════════════════════════════════════════════════════════════
    # I 57 codici sotto sono sollevati dalle funzioni PL/pgSQL e sono
    # regolarmente a seed in `config.messaggi_errore`, ma non seguono la
    # convenzione `E_{MODULO}_{TIPO}` di `docs/it/dev/api.md`.
    #
    # PERCHE' VANNO REGISTRATI, E PERCHE' PRIMA del campo strutturato.
    # Finche' il codice si ripescava dal testo dell'eccezione, la regex
    # `\bE_[A-Z][A-Z0-9_]+\b` non li vedeva: si ripiegava su `E_DATABASE`,
    # che e' registrato -> 400. Dal momento in cui il translator legge
    # `diag.constraint_name` questi codici ARRIVANO davvero, e senza una
    # voce qui `resolve()` li manda su `E_GENERICO` -> **500**: un 400 di
    # oggi diventerebbe un errore di server. L'ordine dei due passi non e'
    # indifferente, ed e' questo.
    #
    # Elenco autoritativo: `dbops.messaggi_errore_codici_legacy` (57 righe).
    # E' un REGISTRO DEL DEBITO, non un elenco di eccezioni: deve calare.
    # Il rubinetto e' chiuso a monte dal guardrail CI
    # `scripts/sql/guardrail_codice_errore_strutturato.sql` (controllo B):
    # un codice NUOVO fuori convenzione fa fallire la CI. Rinominarne uno
    # significa toglierlo da li', dal CSV del registro e da qui.
    #
    # STATUS: assegnati con la tassonomia di `api.md` letta sul messaggio a
    # seed, non sul nome — conflitto con lo stato corrente 409, input non
    # valido o incoerente 400, non trovato 404, non abilitato 403,
    # configurazione di sistema 500.
    # `user_message` e' solo il ripiego: essendo codici NON tecnici, il
    # messaggio che l'operatore legge resta quello localizzato del DB, coi
    # segnaposto gia' riempiti.
    # ── Anagrafica / validazioni di campo ──
    "CF_NON_VALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    # Guard di dominio delle edizioni di workflow versionate: marker DB SENZA
    # prefisso E_ (substring stabili del catalogo, mappati in
    # pratiche_service._KNOWN_DB_ERROR_MARKERS). Senza policy esplicita il
    # fallback E_* non li copre → cadrebbero sul 500 generico invece del
    # banner 4xx parlante atteso dall'editor (api.md §Errori).
    "DEFINIZIONE_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    # ⚠️ Il guard e' `NOT EXISTS (... id = %s AND attivo = true)`: copre
    # DUE casi, unita' inesistente e unita' disattivata. Il 404 sarebbe
    # giusto solo nel primo e mentirebbe nel secondo; il 400 col campo
    # evidenziato — «scegline un'altra» — e' corretto in entrambi.
    "E_ADMIN_UO_NON_TROVATA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ADMIN_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_AI_QUERY_EMPTY": "highlight_form_fields",  # classe DATO_ERRATO
    "E_AI_QUERY_TOO_LONG": "highlight_form_fields",  # classe DATO_ERRATO
    "E_AMM_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ANAG_FK": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ANAG_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # ══════════════════════════════════════════════════════════════════
    # TERZO LATO — lotto 5A: i 26 raggiunti dal backend (2026-08-07)
    #   Brief §25. Sono codici con `da_trigger = false`, che NON vuol dire
    #   «non li legge nessuno»: li solleva una funzione che **Django chiama
    #   direttamente**, quindi arrivano all'operatore quanto quelli da
    #   trigger. Il flag serviva a dare un ORDINE alle decisioni (§4), non a
    #   escludere — vedi §24.4, dove questa confusione e' costata una frase
    #   sbagliata nel riassunto.
    # ══════════════════════════════════════════════════════════════════
    # ── 404: la cosa indicata non esiste ──
    "E_ARTICOLO_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ATTIVITA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_AUTH_USER_SOGGETTO_CON_PIVA": "highlight_form_fields",  # classe DATO_ERRATO
    # Errore configurazione automazione chiusura (job pgAgent
    # chiusura_scadenze_daily): scatta quando la lookup di codici
    # interni in config.stati_doc_contratti / stati_doc_versione
    # fallisce (seed mancante o codice rimosso). Errore raro,
    # tipicamente indica problema di consistenza ambiente.
    "E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA": "show_toast_error",  # classe TECNICO
    "E_BA_SOGGETTO_INCOERENTE_ISTANZA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_BOM_VALIDO_AL_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CATALOGO_CONV_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_CATALOGO_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CATEGORIA_LISTINO_NON_MAPPATA": "show_error_banner",  # classe NON_TROVATO
    # ══════════════════════════════════════════════════════════════════
    # Gemelli `E_*` dei codici legacy — blocco TRANSITORIO
    # (brief-be-rinomina-codici-known-markers, 2026-08-05)
    # ══════════════════════════════════════════════════════════════════
    # Il DB sta rinominando i codici fuori convenzione, un lotto per volta:
    # `X` diventa `E_X` e il vecchio resta a catalogo marcato `obsoleto_dal`.
    # Registrare QUI il nome nuovo **prima** che il lotto parta rende
    # l'ordine di rilascio irrilevante: finche' il DB manda il vecchio
    # scatta la voce vecchia, appena manda il nuovo scatta questa. Nessuna
    # finestra in cui l'API risponde con un codice che il DB ha ritirato —
    # che non romperebbe niente e per questo non se ne accorgerebbe nessuno.
    #
    # ⚠️ Ogni voce ha lo **stesso** status del suo vecchio: e' una rinomina,
    # non una revisione. Se uno status va cambiato, si cambia il vecchio e
    # si rigenera questo blocco, cosi' i due non divergono mai.
    #
    # ⚠️ Blocco a scadenza: quando il DB avvisa che un lotto e' applicato,
    # si toglie la voce VECCHIA (non questa) e il codice esce di scena. A
    # registro `dbops.messaggi_errore_codici_legacy` vuoto, restano solo
    # queste e il commento va via con la tabella.
    # <- CF_NON_VALIDO  (vivo)
    "E_CF_NON_VALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CF_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CLIENTE_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    # Il codice ruolo arriva dal CHIAMANTE (`assign_ruolo(soggetto_id,
    # codice_ruolo)`) e non risolve nessuna riga di `config.tipi_ruoli`:
    # e' un riferimento che non esiste, non una configurazione mancante.
    "E_COD_INT_RUOLO": "show_error_banner",  # classe NON_TROVATO
    "E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    # ⚠️ Stessa funzione (`fn_cambia_stato_commessa`) di
    # `E_STATO_WORKFLOW_NON_TROVATO`, che sta gia' a 404: era la prova in
    # casa che «da_trigger = false» non significa irraggiungibile.
    "E_COMMESSA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_COMMESSA_PUSH_PARZIALE_VIETATO": "show_toast_error",  # classe NON_ESEGUIBILE
    "E_COMMESSA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONFIG_MATRICE_FK": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONFIG_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    # Sollevato dal classify centralizzato apps/anagrafiche/services/
    # contatti_service.py::classify_contatto_payload quando il payload
    # contatto inline (in create cliente/fornitore/soggetto) e' parziale
    # (almeno un campo valorizzato, ma mancano nominativo o
    # tipo_contatto_id). Sostituisce il vecchio "silent skip" che
    # faceva perdere dati senza preavviso.
    "E_CONTATTO_INCOMPLETO": "highlight_form_fields",  # classe DATO_ERRATO
    # Il consenso al riuso della credenziale (`20260925-51`, brief
    # brief-db-credenziale-per-email §3, Tid 2026-09-27): e' un rifiuto
    # CONFERMABILE come la capienza superata. La madre ferma la creazione
    # dell'operatore se l'email e' gia' di una credenziale e nessuno l'ha
    # confermata, e la ACCETTA quando il secondo tentativo DICHIARA l'id della
    # credenziale vista (`riusa_auth_user_id`). Col default della classe
    # (banner) l'admin resterebbe fermo su un caso che il modello ammette: il
    # pannello riconosce il comportamento (`useForzaturaConfermata`) e apre il
    # dialog con username e vesti. La classe resta CONFLITTO_STATO (409).
    "E_CREDENZIALE_DA_CONFERMARE": "confirm_and_retry",  # classe CONFLITTO_STATO
    # L'annullo di un documento con legami (brief-db-annullo-documento-con-
    # legami, D-4 di Tid, 2026-10-11): stesso stampo. L'avviso unico di bolla,
    # ordine, preventivo e contratto ferma l'annullo di un documento che ha
    # consumato qualcosa di altri documenti (o nasce da un'offerta), e il verbo
    # del documento (`vendite.fn_annulla_<documento>`) lo ACCETTA quando il
    # secondo tentativo DICHIARA quanti legami l'operatore ha visto
    # (`legami_confermati`). Col banner l'operatore resterebbe fermo su un
    # annullo che il modello ammette: la finestra (`useForzaturaConfermata`)
    # elenca i legami (`GET …/<documento>/<id>/legami/`) e ripete con la
    # dichiarazione. ⛔ Sostituisce `E_DDT_ANNULLO_CON_LEGAMI` (della sola
    # bolla), ritirato lo stesso giorno: il suo override si e' tolto con lui.
    "E_DOC_ANNULLO_CON_LEGAMI": "confirm_and_retry",  # classe CONFLITTO_STATO
    # La chiusura di un legame di distinta che ha prezzi bundle oltre la nuova
    # fine (brief-db-revisione-catalogo, giro 3, Q19-Q22 di Tid, 2026-11-09):
    # stesso stampo. Il verbo `catalogo.fn_chiudi_legame_distinta` ferma la
    # chiusura finche' il secondo tentativo non DICHIARA quanti prezzi
    # l'operatore ha visto (`prezzi_confermati`), e allora chiude o toglie i
    # prezzi insieme al legame. Col banner il legame non si chiuderebbe mai
    # da un kit prezzato: la finestra (`useForzaturaConfermata`) elenca i
    # prezzi (`GET …/componenti/<id>/chiusura/`) e ripete con la dichiarazione.
    "E_BOM_CHIUSURA_CON_PREZZI": "confirm_and_retry",  # classe CONFLITTO_STATO
    # ⚠️ La guard e' `attivo IS NOT TRUE`, che copre DUE casi: conto
    # disattivato e conto inesistente (SELECT INTO -> NULL). Il 400 con
    # il campo evidenziato e' corretto in entrambi; un 404 sarebbe
    # giusto solo nel secondo e svuoterebbe la pagina nel primo.
    "E_CONTO_BANCARIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO": "highlight_form_fields",  # classe NON_ESEGUIBILE
    "E_CONTRATTO_CLASSE_TIPO_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
    #   Stessa forma dei due sopra, trovati dalla lente
    #   `scripts/sql/check_messaggio_vs_condizione.sql` dopo che i primi due
    #   erano stati chiusi. Tutti e tre `show_error_banner`: sono scritture
    #   che falliscono (successione contratto, init componenti di riga), non
    #   pagine da svuotare.
    "E_CONTRATTO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "E_CONTRATTO_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    # Guard DB transizione stato contratti (trgfn_contratti_a10_guard_
    # transizione_stato, landed 2026-04-26): rifiuta le transizioni che la
    # matrice non ammette. Dal 2026-10-26 lo stato lo scrivono solo i verbi
    # (fn_cambia_stato_contratto, fn_cessa_contratto, fn_annulla_contratto);
    # la regola della data di cessazione (obbligatoria, non retroattiva,
    # futura = programmata) sta nel verbo della cessazione, non qui
    # (brief-modello-documento-vendita §11.6).
    "E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CORE_PROFILE_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_DATABASE_RETRYABLE": "show_retry_dialog",  # classe CONFLITTO_STATO
    "E_DATA_AL_MINORE_DAL": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DATA_APERTURA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DATA_CESSAZIONE_INVALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DATA_CHIUSURA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DATA_ERRATA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DATA_FINE_NON_MAGGIORE_DI_INIZIO": "highlight_form_fields",  # classe DATO_ERRATO
    # ══════════════════════════════════════════════════════════════════
    # TERZO LATO — lotto 2 `anagrafiche` (2026-08-06)
    #   Brief: docs/it/dev/work-in-progress/brief-db-be-terzo-lato-presidio-codici.md §14
    #
    #   ⚠️ LA REGOLA CHE SEMBRA CONTRADDIRE IL LOTTO 1, E NON LO FA.
    #   Nel lotto `vendite` i mismatch (articolo/UoM) hanno preso 409; qui i
    #   tre mismatch prendono 400 con il campo evidenziato. La differenza e'
    #   **chi ha scelto il valore in conflitto**: la' erano legami
    #   DDT<->ordine creati dal sistema e l'operatore non aveva un campo da
    #   correggere; qui parent, soggetto e conto li sceglie lui in un form.
    #   409 = «rileggi lo stato», 400+highlight = «correggi quel campo».
    # ══════════════════════════════════════════════════════════════════
    # ── 404: la cosa indicata non esiste ──
    # anagrafiche.trgfn_dati_societari_guard_tipo_soggetto, ramo
    # `IF NOT FOUND` sulla SELECT su anagrafiche.soggetti.
    # ⚠️ Il messaggio a catalogo («Il soggetto richiede dati societari»)
    # descrive un'ALTRA condizione: difetto segnalato al team DB
    # (brief §14.3). Lo status non ne dipende — il ramo che solleva e'
    # inequivocabilmente «il soggetto non esiste».
    "E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    #   `fn_contratto_riga_componenti_init` non era sola: ddt, ordine e
    #   preventivo hanno la stessa funzione con lo stesso `IF NOT FOUND`
    #   raccontato come «parametro non valido». Sfuggite alla prima passata
    #   della lente e trovate al giro dopo (brief §23).
    #   ⚠️ Lezione: quando un difetto sta in una funzione che ha delle
    #   gemelle per dominio, il perimetro non e' la funzione — sono tutte.
    "E_DDT_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_DDT_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # <- DEFINIZIONE_NON_TROVATA  (vivo)
    "E_DEFINIZIONE_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    # Decisioni 30/31/72/76. I codici 410-417 sono riservati agli errori
    # applicativi Fase A (template/asset/versioni); i codici 425-426
    # sono i guard append-only del trigger DB su documenti_generati_eventi.
    "E_DOCUMENTI_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_DOCUMENTI_VERSIONE_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO": "highlight_form_fields",  # classe DATO_ERRATO
    # L'azienda che emette e' quella del cliente: guard emittente <-> BA dei
    # sei documenti di vendita (preventivo, offerta, contratto, ordine, DDT,
    # reso), un codice solo dal BB `script.trgfn_doc_guard_emittente_ba`
    # (brief-db-guard-emittente-ba-unico, D-1 di Tid del 2026-10-10). Prende
    # il posto delle sei voci per documento E_{PREV,OFFERTA,CONTRATTO,ORDINE,
    # DDT,RESO}_EMITTENTE_BA_INCOERENTE, ritirate a catalogo.
    # `emittente_fiscale_id` e' un campo del form in tutti e sei: il valore
    # in conflitto l'ha scelto l'operatore, quindi si evidenzia il campo
    # (api.md, «400 · highlight quando il valore l'ha scelto lui in un
    # form»), e il BB manda `campo` nel contesto. ⚠️ La commessa tiene il suo
    # E_COMMESSA_EMITTENTE_BA_INCOERENTE, TECNICO e senza override: li' nessuno
    # sceglie l'emittente, e il BB non manda `campo`.
    # ⚠️ Il presidio C2 non vede il sito (il codice arriva da TG_ARGV): vedi
    # `_ESENZIONI` in apps/core/tests/test_ui_action_e_canale_campi.py.
    "E_DOC_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
    # ⭐ La sigla dell'emittente: campo, non banner. Il default di
    #    `DATO_ERRATO` esiste perche' «promettere un campo che non esiste e'
    #    peggio del contrario»; qui il campo esiste, si chiama `codice`, e
    #    `anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma` lo NOMINA nel
    #    contesto (`'campo' -> 'codice'`) — non e' una supposizione, e' letto
    #    dalla funzione che solleva.
    # ⚠️ E l'operatore ce l'ha davanti: la sigla si scrive a mano nel drawer
    #    dell'emittente, ed e' immutabile dopo la create — sbagliarla in
    #    silenzio significa codici commessa illeggibili per sempre.
    "E_EMITTENTE_CODICE_FORMA_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    # ⭐ Il codice che in maiuscolo non ci sta piu' nella colonna (automazione
    #    CODICE_MAIUSCOLO: `ß` -> `SS` allunga il testo). Stessa ragione della
    #    voce sopra: il campo esiste, e' il `codice` che l'operatore ha appena
    #    scritto, e `script.trgfn_codice_maiuscolo` lo NOMINA nel contesto
    #    (`'campo' -> 'codice'`, letto dalla funzione il 2026-11-04). Vale per
    #    tutte le tabelle del perimetro: ogni drawer che scrive un codice
    #    lo chiama `codice` (guard `frontend/scripts/check-campo-codice.mjs`).
    "E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO": "highlight_form_fields",  # classe DATO_ERRATO
    # -- Vendite: la data documento e la sequenza del registro ----------
    # ⭐ `DATO_ERRATO` ha come default il banner, e qui e' il caso opposto: il
    #    dato sbagliato E' un campo che l'operatore ha davanti, nel dialog
    #    «Rendi definitive». Non e' una supposizione — il DB lo DICE, e l'ho
    #    letto da una chiamata vera (2026-08-25): `column_name` arriva
    #    valorizzato a `data_documento`. Il default del banner esiste perche'
    #    «promettere un campo che non esiste e' peggio del contrario»; qui il
    #    campo esiste ed e' nominato dalla sorgente.
    # ⚠️ Il messaggio porta gia' la data da cui ripartire («…che porta la data
    #    23/08/2026»): campo acceso + frase che dice il valore giusto.
    "E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO": "highlight_form_fields",  # classe DATO_ERRATO
    # ⭐ Il GEMELLO per i documenti non fiscali (DDT, ordini, resi, commesse),
    #    che dal 2026-08-31 si numerano sugli stessi registri. Stessa scelta e
    #    stessa ragione: `vendite.fn_get_next_progressivo` mette
    #    `'campo' -> 'data_documento'` nel contesto di ENTRAMBI i rami — il
    #    codice lo sceglie la famiglia, il campo da accendere e' lo stesso.
    # ⛔ Divergere qui sarebbe la forma peggiore: lo stesso rifiuto, sullo
    #    stesso campo, che accende l'input su una fattura e mostra un banner su
    #    un DDT.
    "E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO": "highlight_form_fields",  # classe DATO_ERRATO
    # -- Vendite: giri di fatturazione (handler coda lavori) ------------
    # <- FLUSSI_ESITO_NON_AMMESSO  (vivo)
    "E_FLUSSI_ESITO_NON_AMMESSO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FLUSSO_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FORMA_GIURIDICA_PAESE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FORNITORE_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    # Fase 2 refactor anagrafiche (landed 2026-04-27). Trigger DB:
    # anagrafiche.trgfn_fornitori_guard_normalize (raise se
    # ritenuta_acconto=true AND ritenuta_aliquota IS NULL/<=0). Codice
    # seedato in config.messaggi_errore (id 398).
    # Il gemello clienti (E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI) e' stato
    # RITIRATO il 2026-07-31 con la DROP del trigger normalize e delle
    # colonne tipo_gg_scadenza_ft/nr_giorni_scadenza (riforma D-I,
    # piano-db-satelliti 3a.5): le condizioni di pagamento cliente passano
    # da config.termini_pagamento e il guard non e' piu' raggiungibile.
    "E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA": "highlight_form_fields",  # classe DATO_ERRATO
    # ══════════════════════════════════════════════════════════════════
    # TERZO LATO — lotto 1 `vendite` (2026-08-06)
    #   Brief: docs/it/dev/work-in-progress/brief-db-be-terzo-lato-presidio-codici.md §10
    #
    #   Codici che una funzione PL/pgSQL viva puo' sollevare e che finora
    #   non erano dichiarati: prendevano il ripiego 400 di `resolve()`
    #   qualunque fosse la verita'. Ognuno e' stato deciso leggendo il
    #   PUNTO CHE SOLLEVA, non il nome: `..._NON_AMMESSO` e' 409 quando e'
    #   lo stato a non consentirlo e 403 quando manca un diritto, e la
    #   differenza si vede solo nella funzione.
    #
    #   ⚠️ `user_message` qui e' solo il RIPIEGO: il messaggio che
    #   l'operatore legge arriva dal catalogo `config.messaggi_errore` e
    #   vince su questo (ErrorTranslator). Quello che cambia davvero, e per
    #   cui sono stati dichiarati, sono `http_status` e `ui_action`.
    # ══════════════════════════════════════════════════════════════════
    # ── 404: la cosa indicata non esiste ──
    # trgfn_ordini_ful_guard_consistenza: la riga ordine o la riga DDT
    # indicate non danno nessun record. Banner e non empty-state: e' una
    # scrittura che fallisce, non una pagina da svuotare.
    "E_FULFILL_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # anagrafiche.trgfn_gestori_guard: il lookup su soggetti_ruoli non
    # da' nessuna riga (`v_soggetto_id IS NULL`).
    "E_GESTORE_SOGGETTO_RUOLO_MANCANTE": "show_error_banner",  # classe NON_TROVATO
    "E_IDEMPOTENCY_IN_PROGRESS": "show_retry_dialog",  # classe CONFLITTO_STATO
    "E_IDENTITA_NON_ATTIVA": "redirect_login",  # classe NON_AUTENTICATO
    "E_ID_FISCALI_DIVERSI": "highlight_form_fields",  # classe DATO_ERRATO
    # trgfn_indirizzi_dettaglio_guard_chiave (brief-db-unicita-civico-
    # indirizzi-dettaglio, 2026-10-25): il guard dice il campo, ed e' un
    # input del form indirizzo (civico, estensione, palazzina, scala, piano,
    # interno). Il doppione (D6) e la via non risolta (D4) restano al banner:
    # il primo e' l'indirizzo intero, la seconda si corregge nell'elenco vie.
    "E_INDIRIZZO_CIVICO_NON_POSITIVO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE": "highlight_form_fields",  # classe DATO_ERRATO
    # Indirizzi documento (BB _indirizzi_documento_helpers, 5 domini):
    # sollevato da script.fn_snapshot_indirizzo (flusso picker) quando
    # origine_indirizzo_id non esiste piu' in anagrafiche.indirizzi.
    "E_INDIRIZZO_SNAPSHOT_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # Indirizzi, contatti e conti del ruolo con l'istanza (o il ruolo) di un
    # altro soggetto: il DB dice il campo (R-DB-17a, 2026-10-19).
    "E_ISTANZA_ALTRO_SOGGETTO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IVA_CONTO_ACQ_ERR": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IVA_CONTO_VEN_ERR": "highlight_form_fields",  # classe DATO_ERRATO
    "E_JWT_SENZA_IDENTITA": "redirect_login",  # classe NON_AUTENTICATO
    # Stessa scelta del fratello, e per la stessa ragione: il token e'
    # incompleto (manca `sid`) e l'unico rimedio e' un accesso nuovo — un
    # banner lascerebbe l'operatore su una pagina che risponde 401 a ogni
    # gesto. Sul 401 il default e' `show_error_banner` per scelta esplicita:
    # buttare qualcuno fuori dall'applicazione si decide riga per riga.
    "E_JWT_SENZA_SID": "redirect_login",  # classe NON_AUTENTICATO
    "E_LISTINO_TIPOLOGIA_UTILITY": "highlight_form_fields",  # classe DATO_ERRATO
    # config.trgfn_toponomastica_normalize: NEW.stato_id e' NULL e
    # nemmeno il default per parametro risolve. E' un errore di
    # COMPILAZIONE: l'operatore ha un campo da correggere e la pagina
    # non deve svuotarsi — la ragione per cui il codice andava spezzato.
    "E_NAZIONE_NON_TROVATA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTA_CHECK_VIOLATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTA_FK": "highlight_form_fields",  # classe DATO_ERRATO
    # Codici cross-area: il service in apps/core/ scrive su qualunque partizione
    # di vendite.note (PREVENTIVO/CONTRATTO/ORDINE_VENDITA/DDT_VENDITA/
    # OFFERTA_COMMERCIALE/FATTURA/ATTIVITA) e in
    # prospettiva su tabelle note di altri schemi che adotteranno lo stesso pattern.
    "E_NOTA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_OFFERTA_ECCEZIONE_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    #   `E_PARAMETRO_INVALIDO` lo nominano 113 funzioni e per 111 il 400 e'
    #   giusto: la correzione non poteva stare qui, doveva stare nel punto
    #   che solleva. Il team DB ha creato i due codici (changeSet
    #   20260806-22 e -23) e ha tolto anche il valore variadico «offerta non
    #   trovata: ...», che ripeteva meta' della frase autocontraddittoria.
    # vendite.fn_push_offerta_a_contratto, ramo `IF NOT FOUND`.
    # Banner e non empty-state: e' una scrittura che fallisce (push
    # verso contratto), non una pagina da svuotare.
    "E_OFFERTA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_ONERE_ARTICOLO_MANCANTE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ONERE_CAUSALE_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ONERE_IMPORTO_NON_VALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_ORDINE_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_ORD_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # <- EMITTENTE_NON_MODIFICABILE (senza prefisso) RIMOSSO il 2026-08-06.
    #    Il team DB aveva gia' cancellato quel codice dal catalogo il
    #    2026-08-05 (changeSet 20260805-16, con il censimento «funzioni DB: 0
    #    · backend/apps: 0 · frontend: 0»): qui era rimasta la voce orfana.
    #    ⚠️ Non era inerte: dava 409 mentre il gemello vivo
    #    `E_EMITTENTE_NON_MODIFICABILE` dava 400, ed era **l'unica** delle 53
    #    coppie legacy/prefissato a divergere. Due risposte per lo stesso
    #    concetto sopravvivono finche' nessuno confronta le due colonne.
    # ── Parametri di sistema ──
    "E_PARAMETER_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # ⚠️ DECISIONE CONSAPEVOLE (Tid, 2026-08-06). Il nome dice due cose
    # — «parametro non valido O inesistente» — ma l'unico punto che lo
    # solleva oggi e' un NOT FOUND sul billing account indicato
    # (vendite.trgfn_attivita_fatturabili_guard_ba_coerenza), quindi la
    # verita' e' 404. Se un giorno lo si riusa per un parametro
    # MALFORMATO questa policy diventa falsa in silenzio: in quel caso
    # va spezzato in due codici, non corretto qui.
    "E_PARAMETRI_TABELLA": "show_error_banner",  # classe NON_TROVATO
    # --- Validazione parametri (400) ---
    "E_PARAMETRO_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PARENT_SELF": "highlight_form_fields",  # classe DATO_ERRATO
    # <- PIVA_NON_VALIDA  (vivo)
    "E_PIVA_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PIVA_OBBLIGATORIA": "highlight_form_fields",  # classe DATO_ERRATO
    # -- Vendite: parametri di collegamento pratica/flusso --------------
    "E_PRATICA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PREVENTIVO_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    # Codici sollevati dai trigger DB landed su `vendite.preventivi`:
    #   _a10_default_emittente_ins: setta emittente_fiscale_id da GUC
    #     app.current_user_id; raise se utente senza EF e payload non
    #     specifica emittente (caso admin globale).
    #   _a10_guard_utility_istanza_coerenza_ins_upd: verifica coerenza
    #     coppia (istanza_utility_id, utility_id) via fn generica
    #     script.fn_check_utility_istanza_coerenza (BA o IDP o cliente
    #     matching post Strategia C).
    #   istanze_utilities _a90_require_utility_dichiarata (DEFERRED):
    #     ogni nuova istanza deve avere almeno un satellite (BA, IDP,
    #     cliente) entro la transazione.
    #   automation_lock_columns su preventivi.emittente_fiscale_id:
    #     immutabile post-create. Codice senza prefisso E_ perche'
    #     coerente con il pattern lock_columns del DB.
    #   ⚠️ RITIRATO il 2026-09-15 (brief-db-emittente-di-default-un-bb-solo,
    #   D1): le quattro copie di `trgfn_*_default_emittente` sono un BB solo,
    #   `script.trgfn_default_emittente_fiscale`, che solleva
    #   `E_EMITTENTE_NON_RISOLTO`. La voce resta perche' un codice ritirato
    #   continua a risolvere per il diario. ⛔ Il SUCCESSORE NON HA OVERRIDE, ed
    #   e' una decisione (brief §7.2/§11.3): tre codici per la stessa
    #   condizione avevano DUE rese a video (questo evidenziava un campo, le
    #   sorelle ordini/contratti no). Il rimedio e' la combo dell'emittente in
    #   alto, non un campo del form: il banner (default di `DATO_ERRATO`) e' la
    #   resa giusta, e `fields` — quando il DB lo manda — accende comunque
    #   l'input via `campiErrati`.
    "E_PREV_EMITTENTE_NON_RISOLTO": "highlight_form_fields",  # classe DATO_ERRATO
    # <- PREV_STATO_CORRENTE_NON_TROVATO  (ritirato)
    "E_PREV_STATO_CORRENTE_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "E_PREV_UTILITY_ISTANZA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
    "E_PREV_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    #   ⚠️ `show_empty_state` -> `show_error_banner` il 2026-08-06.
    #   Quella ui_action e' pensata per una LISTA che non trova nulla. Questi
    #   tre li solleva solo `vendite.fn_resolve_prezzo_listino_v2`, cioe' la
    #   risoluzione del prezzo di una riga: non c'e' nessuna lista da
    #   svuotare, c'e' una scrittura che fallisce.
    #   Il difetto non nasce dall'handler `P0001` del brief §19.2: e' gia'
    #   vivo oggi sul percorso diretto dell'API pricing, dove questi codici
    #   arrivano al client senza passare dall'handler. Toglierlo lo avrebbe
    #   soltanto reso visibile anche altrove.
    #   Lo status resta 404: la cosa cercata (mappa, prezzo, riga) davvero
    #   non c'e'.
    "E_PREZZO_LISTINO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "E_PREZZO_LISTINO_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_PROFILO_ACCESSO_BINDING_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
    # config.trgfn_profili_accesso_bindings_guard_coerenza, ramo
    # `IF NOT FOUND`. Era il punto in cui il codice **confessava nel
    # commento** di essere stato scelto per quanti %s aveva il
    # messaggio: la forma della stringa di formato aveva deciso la
    # semantica, e da li' era arrivata fino allo status HTTP.
    "E_PROFILO_ACCESSO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "E_PROMO_INIZIATA_CAMPI_RISTRETTI": "show_toast_error",  # classe CONFLITTO_STATO
    # Guard Profilo A promo data-driven (vendite.promo_articoli):
    # le date governano lo stato (FUTURA / INIZIATA / SCADUTA) e vincolano
    # i campi modificabili. Pattern simmetrico al lock di testata dei
    # documenti (`E_DOC_*` fuori bozza) ma data-driven invece che stato-driven.
    # Defense-in-depth: trigger DB applica le stesse regole su bypass via psql.
    "E_PROMO_RETROATTIVA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PROMO_SCADUTA_IMMUTABILE": "show_toast_error",  # classe CONFLITTO_STATO
    "E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PUSH_SORGENTE_ID_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_QTA_MISSING": "highlight_form_fields",  # classe DATO_ERRATO
    #   `highlight_form_fields` dove c'e' davvero un campo da correggere,
    #   `show_error_banner` dove il problema non e' un campo del form.
    "E_QTA_NON_POSITIVA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_QTA_OPERATIVA_NON_INTERA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_QTA_OPER_STEP_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_RESO_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # Annullamento riga MANUALE di commessa (guard DB 564-567,
    # brief-annullamento-righe-manuali-commessa §4d). Quattro codici
    # DISTINTI e non uno generico: ogni causa porta l'operatore a un'azione
    # diversa. In particolare `GIA_ANNULLATA` esiste separato da
    # `GIA_EMESSA` perche' dire «e` entrata nella catena di fatturazione» a
    # chi ha semplicemente cliccato due volte e` FALSO, e lo manda a cercare
    # una fattura che non esiste.
    # 409 sui tre conflitti di stato (non e` un input da correggere, e` un
    # fatto), 400 sul motivo mancante (campo del form).
    # ══════════════════════════════════════════════════════════════════
    # Il rifiuto CONFERMABILE — `confirm_and_retry` (Tid, 2026-08-24, Q-1 del
    # brief BE/FE posting e abbinamento rata)
    # ══════════════════════════════════════════════════════════════════
    # ⭐ Voce NUOVA nel vocabolario delle ui_action, e dice una cosa che nessuna
    # delle altre diceva: *«chiedi conferma e ripeti la stessa richiesta»*.
    # `show_retry_dialog` e' vicina e significa un'altra cosa — RIPROVA, non
    # CONFERMA DI VOLERLO FARE DAVVERO.
    #
    # IL CASO. Arrivano 1.200 su una rata da 1.000. Il database RIFIUTA il primo
    # tentativo con la ragione e i numeri, e ACCETTA il secondo se la riga porta
    # `forzata = true` (D14-d): che un cliente paghi piu' del dovuto e' un fatto
    # del mondo, e il database non lo dichiara impossibile — chiede solo che
    # qualcuno lo dica.
    #
    # PERCHE' SERVE UNA ui_action E NON UN ELENCO DI CODICI NEL FRONTEND. Sul
    # filo HTTP quel rifiuto e' un 409 come tutti gli altri: senza un segnale,
    # l'interfaccia mostrerebbe un banner rosso e l'operatore resterebbe
    # BLOCCATO su un caso che il dominio dichiara ammesso. Un elenco di codici
    # nel frontend costa zero oggi e si dimentica al terzo codice; qui il
    # frontend riconosce la CLASSE DI COMPORTAMENTO e resta cieco ai codici.
    #
    # ⚠️ La classe resta CONFLITTO_STATO (409) ed e' giusta: non c'e' un campo
    # sbagliato da evidenziare — l'importo puo' essere corretto, e' il documento
    # che non ha piu' spazio.
    "E_RIGA_CONTABILE_CAPIENZA_SUPERATA": "confirm_and_retry",  # classe CONFLITTO_STATO
    "E_RIGA_COMMESSA_GIA_ANNULLATA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    # Dal 2026-10-09 e' il codice con cui risponde la rettifica N6 di una riga
    # di listino citata da una commessa: eredita il toast del codice BE che
    # ripeteva la regola del guard (`E_VENDITE_RIGA_GIA_PROPAGATA`, ritirato).
    "E_RIGA_LISTINO_PROPAGATA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_RISORSA_UMANA_SOGGETTO_MISMATCH": "highlight_form_fields",  # classe DATO_ERRATO
    "E_RUOLO_ALTRO_SOGGETTO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SESSIONE_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # §8.4.3/§8.4.4/§8.4.5: endpoint shop rispondono 501 finche' PR-C
    # non porta il MVP. Codice dedicato (non E_TASK_NOT_IMPLEMENTED
    # che e' del dominio pipeline fatturazione).
    "E_SHOP_NON_DISPONIBILE": "show_info_banner",  # classe NON_DISPONIBILE
    "E_SOGGETTO_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # Guard sorgente polimorfa: la riga referenziata non esiste nella
    # tabella target.
    "E_SORG_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # Copre due condizioni (esito non verdetto / codice inesistente), ma
    # entrambe si correggono nello stesso campo della configurazione.
    "E_STATO_DOC_ESITO_NON_VERDETTO": "highlight_form_fields",  # classe DATO_ERRATO
    #   Quel codice ne conteneva due, e per questo era rimasto senza policy:
    #   con 404 la form indirizzi si sarebbe svuotata mentre l'operatore
    #   digita, con 400 il cambio stato avrebbe mentito. Spezzato dal team DB
    #   (changeSet 20260806-09/10/11), ora ognuno puo' dire la sua verita'.
    #   Brief §10.5 e §11.2. Il vecchio codice e' ritirato con `obsoleto_dal`,
    #   non cancellato: regge il diario degli errori gia' accaduti.
    # vendite.fn_cambia_stato_commessa / _preventivo: il codice_interno
    # dello stato di destinazione non da' nessuna riga ATTIVA. La
    # destinazione indicata non esiste.
    "E_STATO_WORKFLOW_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    # Codice inventato dal BE per la violazione UNIQUE
    # `uq_template_flussi_definizione_codice` (marker in
    # `pratiche_service._KNOWN_DB_ERROR_MARKERS`): non e' a catalogo DB.
    # Non era registrato — quindi cadeva sulla scorciatoia «E_* sconosciuto»
    # e un duplicato rispondeva 400 «errore di validazione» invece di 409.
    # Trovato il 2026-08-05 mentre si aggiungevano i gemelli: allora sfuggiva
    # al guardrail `test_error_codes_declared_guardrail`, che guardava i soli
    # kwarg `code=`/`error_code=` (qui il codice sta dentro una tupla). Dal
    # 2026-10-07 il guardrail guarda ogni literal `E_*` (E-2) e lo vede.
    "E_TEMPLATE_CODICE_DUPLICATO": "highlight_form_fields",  # classe CONFLITTO_STATO
    # <- TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA  (ritirato)
    "E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA": "highlight_form_fields",  # classe DATO_ERRATO
    # <- TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO  (ritirato)
    "E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO": "highlight_form_fields",  # classe DATO_ERRATO
    # <- TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO  (ritirato)
    "E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO": "highlight_form_fields",  # classe DATO_ERRATO
    # <- TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO  (ritirato)
    "E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_TIPO_INDIRIZZO_NON_PERMESSO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_TIPO_RUOLO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    # CRUD ui.lista_colonna (DEF-5b T2). E_UI_COLONNA_IN_USO viene
    # sollevato sia da FK RESTRICT (lista_preset_colonna,
    # lista_colonna_permesso) sia dal soft-block applicativo che
    # conta le preferenze utente che referenziano la colonna nel
    # JSONB `configurazione->colonne`.
    "E_UI_COLONNA_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # Blocco F Fase 2 (DEF-5b): CRUD `ui.lista_definizione` e
    # `ui.lista_colonna`. SUPER_ADMIN-only. La cancellazione di una
    # definizione e' bloccata dalle FK RESTRICT (preferenze utente,
    # colonne, preset): il messaggio E_UI_DEFINIZIONE_IN_USO e'
    # mappato dal service via map_integrity_error.
    "E_UI_DEFINIZIONE_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_UI_PERMESSO_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_UI_PREFERENZA_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    # Blocco F (admin CRUD ui.*): codici dedicati per preset e permessi colonna.
    # Le validazioni di scoperto/duplicato vengono mappate via map_integrity_error
    # da nomi vincolo DB (uq_ui_lista_preset_lista_codice, chk_ui_lista_preset_ambito_refs).
    "E_UI_PRESET_VALIDAZIONE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_UOM_MISSING": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VALIDATION_INPUT": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VALORE_MANCANTE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VENDITE_FK": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO": "show_toast_error",  # classe CONFLITTO_STATO
    "E_VENDITE_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA": "show_toast_error",  # classe CONFLITTO_STATO
    # Il guard di transizione della versione di listino rifiuta un passaggio
    # fuori dalla matrice (brief-db-listini-stato-chiusa-sync; dal 2026-10-28
    # legge `config.transizioni_stati_listino_versioni`, giro 12). La chiusura
    # si programma con PATCH valido_al e la scrive il job a finestra scaduta.
    # La copia applicativa (`listini_service._validate_versione_state_transition`)
    # e' ritirata nello stesso giro: la regola e' solo del DB.
    "E_VERSIONE_STATO_TRANSIZIONE_INVALIDA": "show_toast_error",  # classe CONFLITTO_STATO
    "FLUSSI_ESITO_NON_AMMESSO": "highlight_form_fields",  # classe DATO_ERRATO
    "PIVA_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "PREV_STATO_CORRENTE_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
}
