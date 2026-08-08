# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: le `ui_action` che NON seguono il default della loro classe.
#        Il default copre 482 codici su 658; qui stanno i 176 che se ne
#        discostano, ognuno con la ragione per cui lo fa.
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
    "E_ARTICOLO_NON_COMPOSITO": "highlight_form_fields",  # classe DATO_ERRATO
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
    "E_COERENZA_ID": "highlight_form_fields",  # classe DATO_ERRATO
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
    # ⚠️ La guard e' `attivo IS NOT TRUE`, che copre DUE casi: conto
    # disattivato e conto inesistente (SELECT INTO -> NULL). Il 400 con
    # il campo evidenziato e' corretto in entrambi; un 404 sarebbe
    # giusto solo nel secondo e svuoterebbe la pagina nel primo.
    "E_CONTO_BANCARIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO": "highlight_form_fields",  # classe NON_ESEGUIBILE
    "E_CONTRATTO_CLASSE_TIPO_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONTRATTO_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
    # Guard Profilo A contratti: in stati post-DRAFT (ATTIVO/CESSATO)
    # le modifiche sono limitate o vietate. La testata ammette solo
    # `valido_al` e `meta` in ATTIVO; CESSATO immutabile. Le sotto
    # -entita' (righe override, utility 1:1) sono CRUD-able solo in
    # DRAFT. Per modifiche sostanziali post-DRAFT serve creare un
    # nuovo contratto (eventualmente con parent_contratto_id).
    "E_CONTRATTO_NON_MODIFICABILE": "show_toast_error",  # classe CONFLITTO_STATO
    #   Stessa forma dei due sopra, trovati dalla lente
    #   `scripts/sql/check_messaggio_vs_condizione.sql` dopo che i primi due
    #   erano stati chiusi. Tutti e tre `show_error_banner`: sono scritture
    #   che falliscono (successione contratto, init componenti di riga), non
    #   pagine da svuotare.
    "E_CONTRATTO_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "E_CONTRATTO_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    # Guard DB transizione stato contratti (trgfn_contratti_a10_guard_
    # transizione_stato, landed 2026-04-26). Rifiuta transizioni non
    # ammesse: DRAFT->ATTIVO consentita; ATTIVO->CESSATO consentita
    # SOLO con valido_al < CURRENT_DATE; CESSATO terminale; altre vietate.
    # Il service applicativo ha la stessa regola fail-safe data-driven:
    # se l'utente sceglie data futura nel dialog "Cessa contratto", il
    # service NON chiama update_stato (cessazione programmata) — il job
    # notturno applica CESSATO quando la data scade. Questo trigger
    # interviene su bypass del service (UPDATE diretto via psql).
    "E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI": "highlight_form_fields",  # classe DATO_ERRATO
    "E_CORE_PROFILE_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_CORE_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
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
    "E_DDT_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
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
    # -- Vendite: giri di fatturazione (handler coda lavori) ------------
    "E_FATTURAZIONE_GIRO_PAYLOAD": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FATTURAZIONE_NUMERA_PAYLOAD": "highlight_form_fields",  # classe DATO_ERRATO
    # <- FLUSSI_ESITO_NON_AMMESSO  (vivo)
    "E_FLUSSI_ESITO_NON_AMMESSO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FLUSSO_ID_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FLUSSO_ID_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FLUSSO_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FORMA_GIURIDICA_PAESE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_FORNITORE_ID_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
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
    "E_GENERATE_FATTURE_RIGHE_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    # anagrafiche.trgfn_gestori_guard: il lookup su soggetti_ruoli non
    # da' nessuna riga (`v_soggetto_id IS NULL`).
    "E_GESTORE_SOGGETTO_RUOLO_MANCANTE": "show_error_banner",  # classe NON_TROVATO
    "E_GROUP_ATTIVITA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IDEMPOTENCY_IN_PROGRESS": "show_retry_dialog",  # classe CONFLITTO_STATO
    "E_IDEMPOTENCY_KEY_REQUIRED": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IDENTITA_NON_ATTIVA": "redirect_login",  # classe NON_AUTENTICATO
    "E_ID_FISCALI_DIVERSI": "highlight_form_fields",  # classe DATO_ERRATO
    # Indirizzi documento (BB _indirizzi_documento_helpers, 5 domini):
    # sollevato da script.fn_snapshot_indirizzo (flusso picker) quando
    # origine_indirizzo_id non esiste piu' in anagrafiche.indirizzi.
    "E_INDIRIZZO_SNAPSHOT_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_INVALID_ID": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IVA_CONTO_ACQ_ERR": "highlight_form_fields",  # classe DATO_ERRATO
    "E_IVA_CONTO_VEN_ERR": "highlight_form_fields",  # classe DATO_ERRATO
    "E_JWT_SENZA_IDENTITA": "redirect_login",  # classe NON_AUTENTICATO
    "E_LISTINO_TIPOLOGIA_UTILITY": "highlight_form_fields",  # classe DATO_ERRATO
    # config.trgfn_toponomastica_normalize: NEW.stato_id e' NULL e
    # nemmeno il default per parametro risolve. E' un errore di
    # COMPILAZIONE: l'operatore ha un campo da correggere e la pagina
    # non deve svuotarsi — la ragione per cui il codice andava spezzato.
    "E_NAZIONE_NON_TROVATA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTA_CHECK_VIOLATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTA_FK": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTA_RIGA_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
    # Codici cross-area: il service in apps/core/ scrive su qualunque partizione
    # di vendite.note (PREVENTIVO/CONTRATTO/ORDINE/DDT/FATTURA/ATTIVITAFT) e in
    # prospettiva su tabelle note di altri schemi che adotteranno lo stesso pattern.
    "E_NOTA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_NOTE_TARGET_ID": "highlight_form_fields",  # classe DATO_ERRATO
    "E_OFFERTA_ECCEZIONE_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_OFFERTA_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
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
    # Sollevati da trgfn_<dominio>_guard_emittente_ba quando
    # emittente_fiscale_id diverge da fn_get_emittente_fiscale_pk(BA)
    # (skip se BA NULL). Ordini/contratti esistevano gia' (mai registrati:
    # gap sanato); DDT/preventivi/offerte aggiunti dal DB team 2026-07-13
    # (brief emittente-user-e-etichetta-soggetto).
    "E_ORDINE_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
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
    "E_PIPELINE_SCOPE_INCOMPLETE": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PIPELINE_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    # <- PIVA_NON_VALIDA  (vivo)
    "E_PIVA_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PIVA_OBBLIGATORIA": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PRATICA_ID_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
    # -- Vendite: parametri di collegamento pratica/flusso --------------
    "E_PRATICA_ID_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PRATICA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_PREVENTIVO_RIGA_NON_TROVATA": "show_error_banner",  # classe NON_TROVATO
    "E_PREV_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe CONFLITTO_STATO
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
    # i campi modificabili. Pattern simmetrico a Profilo A contratti
    # (E_CONTRATTO_NON_MODIFICABILE) ma data-driven invece che stato-driven.
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
    "E_RESET_LOTTO_FATTURA_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_RESET_LOTTO_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    # ⚠️ SESTA DI SEI GUARDIE IDENTICHE, e fino al 2026-08-08 era l'unica senza
    # override — segnalato dal team DB collaudando il campo da correggere.
    # `emittente_fiscale_id` e' un campo del form in tutti e sei i documenti
    # (preventivi, offerte, ordini, contratti, DDT, resi): il valore in
    # conflitto l'ha scelto l'operatore, quindi si evidenzia il campo. E' il
    # criterio di api.md — «400 · highlight quando il valore l'ha scelto lui in
    # un form», l'analogo di `E_ID_FISCALI_DIVERSI`.
    #
    # ⚠️ E LA FAMIGLIA RESTA DISALLINEATA SULL'ALTRA META', che non e' nostra:
    # i cinque gemelli hanno classe `CONFLITTO_STATO` (409) mentre questo ha
    # `DATO_ERRATO` (400). **Ha ragione questo**: il conflitto non e' fra righe
    # che l'operatore non ha scelto — e' il valore che ha appena messo nel form.
    # I cinque vanno spostati a `DATO_ERRATO` **a catalogo**: la classe e' un
    # dato del DB, non si corregge qui (o il controllo di divergenza va rosso).
    "E_RESO_EMITTENTE_BA_INCOERENTE": "highlight_form_fields",  # classe DATO_ERRATO
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
    "E_RIGA_COMMESSA_GIA_ANNULLATA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_RISORSA_UMANA_SOGGETTO_MISMATCH": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SEARCH_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SESSIONE_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # §8.4.3/§8.4.4/§8.4.5: endpoint shop rispondono 501 finche' PR-C
    # non porta il MVP. Codice dedicato (non E_TASK_NOT_IMPLEMENTED
    # che e' del dominio pipeline fatturazione).
    "E_SHOP_NON_DISPONIBILE": "show_info_banner",  # classe NON_DISPONIBILE
    "E_SOGGETTO_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    "E_SOGGETTO_NULL": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SORG_FORMATO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SORG_KEY_MISSING": "highlight_form_fields",  # classe DATO_ERRATO
    "E_SORG_NORM_NON_RISOLTA": "highlight_form_fields",  # classe DATO_ERRATO
    # Guard sorgente polimorfa: la riga referenziata non esiste nella
    # tabella target.
    "E_SORG_NOT_FOUND": "show_error_banner",  # classe NON_TROVATO
    # Copre due condizioni (esito non verdetto / codice inesistente), ma
    # entrambe si correggono nello stesso campo della configurazione.
    "E_STATO_DOC_ESITO_NON_VERDETTO": "highlight_form_fields",  # classe DATO_ERRATO
    "E_STATO_SORGENTE_PARAM_INVALIDO": "highlight_form_fields",  # classe DATO_ERRATO
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
    # Trovato il 2026-08-05 mentre si aggiungevano i gemelli: sfugge al
    # guardrail `test_error_codes_declared_guardrail` perche' quello guarda
    # i kwarg `code=`/`error_code=`, e qui il codice sta dentro una tupla.
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
    "E_VENDITE_RIGA_GIA_PROPAGATA": "show_toast_error",  # classe CONFLITTO_STATO
    "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO": "show_toast_error",  # classe CONFLITTO_STATO
    "E_VENDITE_VALIDATION": "highlight_form_fields",  # classe DATO_ERRATO
    "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA": "show_toast_error",  # classe CONFLITTO_STATO
    # Guard DB defense-in-depth: rifiuta la transizione manuale
    # ATTIVA -> CHIUSA (brief-db-listini-stato-chiusa-sync). La chiusura
    # si esegue via PATCH valido_al; lo stato CHIUSA viene poi sincronizzato
    # dal job notturno a finestra scaduta. Policy speculare a quella
    # applicativa nel service listini_service._validate_versione_state_transition.
    "E_VERSIONE_STATO_TRANSIZIONE_INVALIDA": "show_toast_error",  # classe CONFLITTO_STATO
    "FLUSSI_ESITO_NON_AMMESSO": "highlight_form_fields",  # classe DATO_ERRATO
    "PIVA_NON_VALIDA": "highlight_form_fields",  # classe DATO_ERRATO
    "PREV_STATO_CORRENTE_NON_TROVATO": "show_error_banner",  # classe NON_TROVATO
    "TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO": "highlight_form_fields",  # classe DATO_ERRATO
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO": "highlight_form_fields",  # classe DATO_ERRATO
}
