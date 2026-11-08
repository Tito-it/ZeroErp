# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il messaggio da mostrare all'operatore QUANDO QUELLO DEL DATABASE NON
#        E' ARRIVATO. Non e' una copia di `config.messaggi_errore`: e' la
#        variante SENZA SEGNAPOSTO. Misurato sui 656 codici confrontabili: i
#        messaggi a catalogo che contengono `%s` sono 371 (56%), quelli qui
#        dentro ZERO. Il catalogo ha i buchi che `script.fn_log_and_raise_error`
#        riempie a runtime; questi sono quelli che si mostrano quando quegli
#        argomenti non ci sono (brief §11).
# Note: ⚠️ Il nome dice cosa sono. Il giorno in cui il catalogo portera' una
#        seconda variante argument-free — servirebbe per 371 codici, non e'
#        «spostare 659 stringhe» — questo file si CANCELLA. E' il motivo per cui
#        sta da solo e non dentro gli override di interfaccia (brief §14.2).
#        ⚠️ Gli apostrofi qui NON si raddoppiano: questo e' Python, non una cella
#        di CSV letta da Liquibase. (E il team DB ha verificato il 2026-08-07 che
#        non andavano raddoppiati nemmeno li': il raddoppio in
#        `messaggi_errore.csv` e' un residuo, non una convenzione.)
# ------------------------------------------------------------


# codice -> messaggio di ripiego, senza segnaposto.
USER_MESSAGE_FALLBACK: dict[str, str] = {
    "CF_NON_VALIDO": "Codice fiscale non valido.",
    "CODICE_NON_MODIFICABILE": "Il codice interno non e' modificabile.",
    "DEFINIZIONE_BOZZA_ESISTENTE": "Esiste gia' una bozza di edizione per questo scope (tipo prestazione + emittente).",
    "DEFINIZIONE_NON_PUBBLICABILE": "La bozza non e' pubblicabile: servono almeno uno step attivo e nessun ciclo di prerequisiti.",
    "DEFINIZIONE_NON_TROVATA": "Nessuna definizione di workflow pubblicata per questo tipo.",
    "DEFINIZIONE_NO_PUBBLICATA": "Nuova versione non ammessa: manca un'edizione pubblicata da cui derivare.",
    "DEFINIZIONE_PUBBLICATA_IMMUTABILE": "Edizione non modificabile nello stato corrente.",
    "DEFINIZIONE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato dell'edizione non ammessa.",
    "ERRORE_PARAMETRI": "Parametri obbligatori mancanti o non validi.",
    "ERRORE_PARAMETRI_TABELLA": "Parametro non trovato nella tabella di configurazione.",
    "E_ACCESSO_RISERVATO_ADMIN": "Accesso riservato agli amministratori.",
    "E_ACCESSO_RISERVATO_PORTALE": "Accesso riservato agli utenti portale.",
    "E_ACCESSO_RISERVATO_SHOP": "Accesso riservato ai clienti shop.",
    "E_ACCREDITO_ANNULLO_INCOMPLETO": "Annullo dell'accredito interrotto: alcune rettifiche non sono visibili nel perimetro corrente. Ripetere con un utente che veda l'intero accredito.",
    "E_ACCREDITO_ANNULLO_NON_AMMESSO": "Accredito non annullabile: una o piu' rettifiche sono gia' emesse. Se il documento non e' ancora numerato la strada e' il reset del lotto, che pero' rigenera la nota di credito al giro successivo.",
    "E_ACCREDITO_ATTIVITA_NON_FATTURATA": "La merce resa non risulta mai finita in una fattura: non c'e' un prezzo da cui accreditare.",
    "E_ACCREDITO_GIA_ESEGUITO": "Accredito gia' registrato per questa riga di reso.",
    "E_ACCREDITO_KIT_NON_MISURABILE": "Articolo composito senza coefficienti: la quantita' da accreditare non e' calcolabile.",
    "E_ACCREDITO_KIT_SENZA_PADRE": "Il kit da accreditare non dichiara l'articolo padre dei suoi componenti: la nota di credito non si puo' comporre. Il difetto e' sul documento di origine.",
    "E_ACCREDITO_MOTIVO_OBBLIGATORIO": "Motivo obbligatorio per annullare l'accredito.",
    "E_ACCREDITO_NON_IN_CODA": "Nessun accredito dovuto per questa riga di reso.",
    "E_ACCREDITO_NON_TROVATO": "Nessun accredito da annullare per questa riga di reso: non e' mai stato accreditato, oppure e' gia' stato annullato.",
    "E_ACCREDITO_QUOTA_NON_COPERTA": "Le righe di fattura non coprono tutto l'accredito dovuto: l'accredito non si esegue a meta'.",
    "E_ACCREDITO_SEGMENT_DUPLICATO": "Accredito non creato per una modifica concorrente. Riprovare.",
    "E_ACCREDITO_SENZA_SPEDIZIONE": "Accredito senza spedizione a monte: anomalia tecnica.",
    "E_ADMIN_CF_DUPLICATO": "Codice fiscale gia' presente in anagrafica.",
    "E_ADMIN_EMAIL_DUPLICATA": "Email gia' in uso.",
    "E_ADMIN_PIVA_DUPLICATA": "Partita IVA gia' presente in anagrafica.",
    "E_ADMIN_ULTIMO": "Impossibile disabilitare l'ultimo amministratore.",
    "E_ADMIN_UO_NON_TROVATA": "Unita' organizzativa non valida o non attiva.",
    "E_ADMIN_USERNAME_DUPLICATO": "Username gia' in uso.",
    "E_ADMIN_VALIDAZIONE": "Parametri non validi.",
    "E_AI_DISABLED": "Funzionalita' assistente AI non attiva.",
    "E_AI_PROVIDER_ERROR": "Errore nella comunicazione con il provider AI.",
    "E_AI_PROVIDER_UNKNOWN": "Provider AI non riconosciuto.",
    "E_AI_QUERY_EMPTY": "Il messaggio non puo' essere vuoto.",
    "E_AI_QUERY_TOO_LONG": "Il messaggio supera la lunghezza massima consentita.",
    "E_AI_TOOL_DENIED": "Non hai i permessi per questo strumento AI.",
    "E_AI_TOOL_NOT_FOUND": "Strumento AI richiesto non disponibile.",
    "E_ALBERO_EMITTENTE_MISTO": "Il billing account e il suo parent appartengono a emittenti fiscali diversi: un singolo albero non puo' attraversare due emittenti.",
    "E_ALLEGATO_INSERT": "Errore durante l'inserimento dell'allegato.",
    "E_ALLEGATO_NOT_FOUND": "Allegato non trovato.",
    "E_AMBIENTE_IMMUTABILE": "L'ambiente di questa installazione non si cambia: si sceglie una volta, quando il database nasce.",
    "E_AMM_OPERATORE_NOT_FOUND": "Operatore non trovato.",
    "E_AMM_SCOPE_NON_AMMESSO": "Scope emittenti non ammesso per la richiesta.",
    "E_AMM_UTENTE_NOT_FOUND": "Utente non trovato.",
    "E_AMM_VALIDAZIONE": "Parametri amministrazione non validi.",
    "E_ANAG_CONTO_NOT_FOUND": "Conto bancario non trovato nel registro.",
    "E_ANAG_CONTO_SOGGETTO_NOT_FOUND": "Associazione conto bancario non trovata.",
    "E_ANAG_DUPLICATO": "Record gia' esistente.",
    "E_ANAG_FK": "Riferimento non valido: l'entita' indicata non esiste.",
    "E_ANAG_MATRICE_OVERLAP": "Esiste gia' una riga attiva che si sovrappone per questa combinazione di dimensioni nel periodo indicato.",
    "E_ANAG_NOT_FOUND": "Record non trovato.",
    "E_ANAG_VALIDAZIONE": "Parametri anagrafiche non validi.",
    "E_APPROVAZIONE_PREZZO_NON_AMMESSA": "Operazione di approvazione prezzo non ammessa nello stato corrente.",
    "E_ARGOMENTI_A_COPPIE": "Trigger configurato con argomenti non a coppie.",
    "E_ARTICOLO_ESCLUSO_DA_CONTRATTO": "L'articolo e' stato escluso dal contratto e non puo' essere venduto a questo cliente.",
    "E_ARTICOLO_KIT_SENZA_COMPONENTI": "Il kit non ha nessun componente: non puo' stare in una riga di documento. Completare la sua distinta o scegliere un altro articolo.",
    "E_ARTICOLO_MISMATCH": "Riga ordine e riga DDT hanno articoli diversi.",
    "E_ARTICOLO_NON_COMPOSITO": "L'articolo indicato non e' composito: non puo' avere una distinta base.",
    "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C": "Articolo non negoziato sul contratto in modalita' C.",
    "E_ARTICOLO_NOT_FOUND": "Articolo non trovato.",
    "E_ARTICOLO_OBSOLETO": "L'articolo e' ritirato: non si puo' scegliere per una riga nuova.",
    "E_ARTICOLO_ONERE_NATURA_MERCE": "Un articolo-onere non puo' avere una natura da merce: la merce va in ordine e in bolla, un onere si scrive in commessa.",
    "E_ARTICOLO_ONERE_STRUTTURA": "Un articolo-onere e' un addebito, non un bene: non si gestisce a magazzino, non ha componenti, lotti o matricole.",
    "E_ARTICOLO_SENZA_EROGAZIONE": "L'articolo non ha nessuna erogazione ammessa: non puo' stare in un'offerta o in un contratto.",
    "E_ARTICOLO_SOLO_COMPONENTE": "Articolo utilizzabile solo come componente: non inseribile come riga autonoma.",
    "E_ARTICOLO_STRUTTURA_RIGHE_APERTE": "La correzione dell'articolo non si puo' fare: renderebbe non valide righe di documenti non ancora chiusi.",
    "E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE": "Articolo incompatibile con la tipologia del listino.",
    "E_ARTICOLO_TIPOLOGIA_MANCANTE": "Articolo privo di tipologia listino: non ammesso in listino tipizzato.",
    "E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE": "L'articolo e' gia' usato in documenti, listini o magazzino: questa caratteristica non si puo' piu' cambiare.",
    "E_ATTIVAZIONE": "Errore attivazione account.",
    "E_ATTIVAZIONE_PORTALE": "Errore attivazione account portale.",
    "E_ATTIVAZIONE_SHOP": "Errore attivazione account shop.",
    "E_ATTIVAZIONE_SHOP_CROSS": "Errore attivazione veste shop dal profilo portale.",
    "E_ATTIVITA_ANCORA_IN_FATTURA": "Il lavoro selezionato e' gia' dentro una fattura: non si riporta da emettere. Se la fattura va rifatta si agisce sulla fattura — «Elimina dal lotto» per quel documento, oppure «Riporta in lavorazione» sull'intero lotto.",
    "E_ATTIVITA_CONTRATTO_INCOERENTE": "Il contratto indicato come provenienza del prezzo non e' del cliente della commessa: segnalalo, non e' una situazione che dipende dai tuoi dati.",
    "E_ATTIVITA_FATTURABILE_NON_TROVATA": "Attivita' selezionate non piu' disponibili: l'elenco che stai guardando e' cambiato. Aggiornalo e riprova.",
    "E_ATTIVITA_GIA_DA_EMETTERE": "Il lavoro selezionato e' gia' da emettere: non c'e' niente da riportare indietro. Il prossimo giro di fatturazione lo prendera' da solo.",
    "E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE": "La quantita` dell`attivita` fatturabile deve specchiare quella della commessa: modifica non consentita.",
    "E_ATTIVITA_KIT_SENZA_PADRE": "Componente di kit senza articolo padre: correggere il documento di origine.",
    "E_ATTIVITA_IN_LAVORAZIONE": "Il lavoro selezionato e' dentro un giro di fatturazione ancora in corso: non e' un residuo, e liberarlo da qui lo farebbe prendere da due giri insieme. Si aspetta che il lotto finisca.",
    "E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO": "Il prezzo della riga cita un listino di un'altra azienda: una riga usa solo i listini dell'azienda della sua commessa.",
    "E_ATTIVITA_LISTINO_RIGA_INCOERENTE": "La riga di listino citata per il prezzo non corrisponde alla riga: articolo, unita' di misura o versione del listino sono diversi.",
    "E_ATTIVITA_LISTINO_VERSIONE_BOZZA": "Il prezzo della riga cita una versione di listino ancora in bozza: i prezzi di una bozza non si usano.",
    "E_ATTIVITA_LOTTO_NOT_FOUND": "Lotto attivita non trovato.",
    "E_ATTIVITA_PIPELINE": "Errore nella pipeline attivita fatturabili.",
    "E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA": "Nessuna attivita' selezionata: la richiesta di riporto e' arrivata vuota. Riselezionare le righe e riprovare.",
    "E_ATTIVITA_VALIDATION": "Parametri pipeline attivita non validi.",
    "E_ATTIVO_BLOCK": "Generazione della regola di automazione ATTIVO_block fallita.",
    "E_ATTIVO_BLOCK_ARGS": "Configurazione trigger di protezione non valida.",
    # ⚠️ La parola «attivi» qui era FALSA dal 2026-08-20 (changeSet 20260820-08):
    # questo e' il ramo delle tabelle figlie che NON hanno una colonna attivo —
    # li' le righe si tolgono, non si disattivano. Il ramo gemello
    # (`..._ACTIVE`) e' quello dove «attive» significa qualcosa.
    "E_ATTIVO_BLOCK_CHILDREN_ACTIVE": "Non si puo' disattivare: ci sono ancora righe collegate attive.",
    "E_ATTIVO_BLOCK_CHILDREN_EXIST": "Non si puo' disattivare: ci sono ancora righe collegate.",
    "E_ATTIVO_BLOCK_FKCOL_NOT_FOUND": "Configurazione trigger di protezione non valida.",
    "E_ATTIVO_BLOCK_REF_NULL": "Colonna di riferimento nulla nel guard di disattivazione.",
    "E_ATTIVO_PADRE_NON_ATTIVO": "La riga a cui si collega non e' attiva: non vi si puo' collegare una riga attiva.",
    # Dal 2026-11-07 lo solleva solo il generatore (brief-db-revisione-dbops D46):
    # il trigger dice E_ATTIVO_PADRE_NON_ATTIVO, E_PADRE_INESISTENTE ed
    # E_TRIGGER_ARGOMENTI_INVALIDI. «Trigger configurato male» non e' piu' suo.
    "E_ATTIVO_REQUIRE": "Generazione della regola di automazione ATTIVO_require fallita.",
    "E_AUDIT_SNAPSHOT_NON_TROVATO": "Snapshot audit non trovato.",
    "E_AUDIT_SOURCE_NON_TROVATO": "Sorgente audit non valida.",
    "E_AUDIT_SUMMARY_PARAM_NON_VALIDO": "Parametri audit non validi.",
    "E_AUDIT_UPDATE": "Generazione del trigger di audit fallita.",
    "E_AUTHENTICATION_FAILED": "Autenticazione fallita.",
    "E_AUTH_USER_SOGGETTO_CON_PIVA": "Un operatore non puo' essere associato a un soggetto con partita IVA.",
    "E_AUTH_USER_SOGGETTO_SENZA_CF": "Il soggetto non ha codice fiscale: non ammesso come operatore.",
    "E_AUTH_CHIAMATA_NON_VALIDA": "Chiamata non valida a una funzione della credenziale.",
    "E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA": "Errore configurazione automazione chiusura. Contattare l'amministratore di sistema.",
    "E_BATCH_ARRAY_DISALLINEATI": "Errore interno nella generazione delle righe.",
    "E_BA_ADMIN_GLOBALE_VIETATO": "Per creare un cliente serve un emittente fiscale su cui lavorare: scegli l'emittente in alto (con «Tutti gli emittenti» non si sa a quale associarlo).",
    # ⚠️ La frase NON nomina piu' «fatture o commesse»: dal 2026-08-31 la storia
    #    e' qualunque documento gia' NUMERATO su un registro — DDT, ordini e resi
    #    compresi — e si deriva da `vendite.famiglie_documento`. Una frase che ne
    #    nomina due manderebbe a cercare fatture a un cliente bloccato da un DDT.
    #    QUALI documenti bloccano lo dice il messaggio del catalogo, che li elenca;
    #    questo e' il ripiego di quando quegli argomenti non sono arrivati, quindi
    #    dice la regola e non l'elenco.
    "E_BA_EMITTENTE_CON_STORIA": "Il cliente ha gia' documenti numerati con l'emittente attuale: non si puo' spostare su un altro emittente. Se il cliente e' passato davvero all'altro emittente, si apre presso di lui una fornitura nuova; i documenti gia' emessi restano con chi li ha emessi.",
    "E_BA_ISTANZA_IMMUTABILE": "Un billing account appartiene per sempre alla sua fornitura e al suo cliente: per un'altra istanza, utility o cliente se ne crea uno nuovo.",
    "E_BA_SOGGETTO_INCOERENTE_ISTANZA": "Soggetto del billing account diverso da quello dell'istanza utility.",
    "E_BILLING_ACCOUNT_UTILITY_NULL": "Billing account senza utility associata.",
    "E_BOM_COMPONENTE_COMPOSITO": "Il componente e' a sua volta un articolo composito: una distinta contiene solo articoli semplici.",
    "E_BOM_COMPONENTE_DIVENTA_COMPOSITO": "L'articolo e' un componente di una distinta: non puo' diventare composito.",
    "E_BOM_COMPONENTE_PADRE": "L'articolo non puo' essere componente della propria distinta.",
    "E_BOM_IVA_DISCORDANTE": "Le aliquote IVA di articolo padre e componenti della distinta devono coincidere.",
    "E_BOM_MODIFICA_VIETATA": "Struttura BoM immutabile: i campi di struttura non sono modificabili. Per correggere, chiudere la riga e inserirne una nuova versione.",
    "E_BOM_VALIDO_AL_INVALIDO": "Data di chiusura non valida: deve essere uguale o successiva alla data di inizio della riga.",
    "E_CAMBIO_PASSWORD_RICHIESTO": "Prima di continuare e' necessario cambiare la password.",
    "E_CAMPO_NON_AMMESSO": "Un campo inviato non si puo' scrivere con questa operazione.",
    "E_CANALE_ORIGINE_IMMUTABILE": "Il canale origine non e' modificabile dopo l'inserimento.",
    "E_CAPITALE_SOCIALE_NON_AMMESSO": "Per questa forma giuridica il capitale sociale non si indica.",
    "E_CAPITALE_SOCIALE_OBBLIGATORIO": "Per questa forma giuridica il capitale sociale e' obbligatorio.",
    "E_CATALOGO_ARTICOLO_NOT_FOUND": "Articolo non trovato.",
    "E_CATALOGO_COMPONENTE_NOT_FOUND": "Componente non trovato.",
    "E_CATALOGO_CONV_NOT_FOUND": "Conversione unita' di misura non trovata.",
    "E_CATALOGO_NOTA_NOT_FOUND": "Nota non trovata.",
    "E_CATALOGO_OBSOLETO_NUOVA_ISTANZA": "Voce di catalogo obsoleta: non selezionabile per nuove istanze.",
    "E_CATALOGO_UOM_NOT_FOUND": "UoM operativa non trovata.",
    "E_CATALOGO_UOM_TIPO_NOT_FOUND": "Tipologia UoM non trovata.",
    "E_CATALOGO_VALIDATION": "Parametri catalogo non validi.",
    "E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO": "Il listino scelto e' di un'altra azienda: a una categoria di clienti si assegna solo un listino dell'azienda indicata sulla riga.",
    "E_CATEGORIA_LISTINO_NON_MAPPATA": "Categoria cliente non mappata a listino per la quadrupla indicata.",
    "E_CATEGORIA_LISTINO_UTILITY_DIVERSA": "Il listino scelto e' di un'altra utility: a una categoria di clienti si assegna solo un listino della utility della riga.",
    "E_CENTRO_NON_ABILITATO_COMPENSAZIONE": "Il centro di riscossione indicato non e' abilitato alle compensazioni.",
    "E_CF_NON_VALIDO": "Codice fiscale non valido.",
    "E_CF_OBBLIGATORIO": "Codice fiscale obbligatorio.",
    "E_CHANGE_PASSWORD": "Errore cambio password.",
    "E_CHIUDE_LOTTO_SINGLETON": "Un solo stato puo' avere il flag chiude_lotto attivo.",
    "E_CLIENTE_DATA_CHIUSURA_IMMUTABILE": "Il cliente e' chiuso: la data di chiusura non si cambia piu'.",
    "E_CLIENTE_FORNITURA_IMMUTABILE": "Un cliente appartiene per sempre alla sua fornitura: per un'altra fornitura si crea un cliente nuovo, per un nuovo intestatario si usa il subentro.",
    "E_CLIENTE_NON_ATTIVO": "Il cliente non e' in stato attivo.",
    "E_CLIENTE_NON_TROVATO": "Cliente non trovato.",
    "E_CLIENTE_PA_NON_AMMESSO": "Questo tipo soggetto non puo' essere una Pubblica Amministrazione.",
    "E_CLIENTE_STATO_SENZA_DATA": "Lo stato scelto per il cliente richiede la sua data.",
    "E_CLIENTE_STATO_TRANSIZIONE_INVALIDA": "Il cliente non puo' passare allo stato richiesto.",
    "E_CLIENTE_STESSA_CHIAVE": "Per questo soggetto, servizio e azienda esiste gia' un cliente attivo nello stesso periodo.",
    "E_CLIENTE_UTILITY_MISMATCH_BA": "Utility non coerente con il billing account del cliente.",
    # ⚠️ SENZA segnaposto, mentre il messaggio a catalogo ha un `%s` con lo
    # STATO della riga: è proprio quando gli argomenti non arrivano che il
    # segnaposto finirebbe a video in chiaro.
    "E_CODA_ARCHIVIAZIONE_NON_AMMESSA": (
        "La riga della coda sta ancora lavorando: si mette via solo quando ha "
        "finito."
    ),
    "E_CODA_CHIAVE_ALTRUI": "Un lavoro con la stessa chiave è già in coda per un'altra azienda.",
    "E_CODA_HANDLER_NON_REGISTRATO": "Tipo di lavoro non cablato nel sistema.",
    "E_CODA_IDENTITA_NON_ATTIVA": "Identità operatore non più attiva: lavoro non eseguibile.",
    "E_CODA_JOB_STANTIO": "Esecuzione interrotta (worker morto o kill): recuperata dal reaper.",
    "E_CODA_LAVORO_SENZA_EMITTENTE": (
        "Il lavoro non si accoda: un lavoro per conto di un operatore "
        "appartiene a un'azienda, e la richiesta non ne indica una."
    ),
    "E_CODA_SCOPE_ALTRUI": (
        "Il lavoro non si accoda: è intestato a un'altra persona o a un'azienda "
        "che chi lo chiede non gestisce."
    ),
    "E_CODA_SCOPE_OPERATORE_INVALIDO": "Lavoro accodato con scope operatore incompleto.",
    "E_CODICE": "Codice di configurazione non trovato.",
    "E_CODICE_MAIUSCOLO": "Automazione del codice in maiuscolo fallita su una tabella.",
    "E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO": "Il codice, salvato in maiuscolo, supera la lunghezza ammessa.",
    "E_CODICE_NON_MODIFICABILE": "Il codice interno non e' modificabile.",
    "E_COD_INT_RUOLO": "Tipo ruolo non trovato per il codice indicato.",
    "E_COERENZA_ID": "Valore non coerente con il riferimento indicato.",
    "E_COLONNA_NON_MODIFICABILE": "Colonna non modificabile.",
    "E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE": "Annullamento non consentito: la commessa ha righe gia` emesse.",
    "E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO": "La chiave della riga di commessa non nomina il documento di origine.",
    "E_COMMESSA_ATTIVITA_GIA_EMESSA":"Riga commessa gia' emessa: modifica non consentita.",
    "E_COMMESSA_ATTIVITA_NON_COERENTE": "Attivita' non coerente con la commessa.",
    "E_COMMESSA_ATTIVITA_NOT_FOUND": "Attivita` commessa non trovata.",
    "E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE": "Il prezzo di una rettifica di nota di credito e' immutabile: e' copiato dalla riga di fattura che rettifica.",
    "E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE": "Riga di commessa gia` emessa: la quantita` non si modifica. Correggere aggiungendo una riga nuova.",
    "E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO": "Tipo documento fiscale obbligatorio sulla riga emittibile.",
    "E_COMMESSA_CHIAVE_IMMUTABILE": "Commessa con attivita' collegate: la chiave non e' piu' modificabile.",
    "E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI": "Chiusura non consentita: restano righe approvate non ancora emesse.",
    "E_COMMESSA_EMITTENTE_BA_INCOERENTE": "L'azienda indicata sulla commessa non e' quella del cliente: anomalia tecnica.",
    "E_COMMESSA_EMITTENTE_MANCANTE": "Commessa senza emittente fiscale: fatturazione non possibile.",
    "E_COMMESSA_NESSUNA_RIGA_APPROVATA": "Nessuna riga approvata: impossibile passare a PRONTA_FATTURAZIONE.",
    "E_COMMESSA_NON_MODIFICABILE": "La commessa non e' in uno stato modificabile.",
    "E_COMMESSA_NON_TROVATA": "Commessa non trovata.",
    "E_COMMESSA_NOT_FOUND": "Commessa non trovata.",
    "E_COMMESSA_PUSH_LOG_NOT_FOUND": "Push log commesse non trovato.",
    "E_COMMESSA_PUSH_PARZIALE_VIETATO": "Push fallito: nessuna riga inviata.",
    "E_COMMESSA_PUSH_RUN_NON_APERTO": "Il giro di push non e' aperto: non esiste, oppure e' gia' stato chiuso.",
    "E_COMMESSA_PUSH_RUN_STATO_NON_FINALE": "Un giro di push si chiude con un esito: completato, parziale o errore.",
    "E_COMMESSA_ROOT_CONFLITTO": "Conflitto: commessa root gia' esistente per questa sorgente.",
    "E_COMMESSA_SORGENTE_ALTRA_COMMESSA": "Il documento e' gia' in un'altra commessa aperta: un documento puo' stare in una sola commessa aperta alla volta.",
    "E_COMMESSA_SORGENTE_EMITTENTE_MISTO": "Una commessa non puo' aggregare documenti di emittenti fiscali diversi: anomalia tecnica.",
    "E_COMMESSA_SORGENTE_SCONOSCIUTA": "Sorgente commessa sconosciuta.",
    "E_COMMESSA_STATO_TRANSIZIONE_INVALIDA": "Transizione di stato della commessa non ammessa dallo stato attuale.",
    "E_COMMESSA_VALIDATION": "Parametri commessa non validi.",
    "E_COMPONENTE_PREZZO_PENDENTE": "Impossibile emettere: componenti con approvazione prezzo in corso (PENDING).",
    "E_COMUNE_NON_TROVATO": "Il comune indicato non esiste.",
    "E_CONFIG_MANCANTE": "Configurazione mancante nel sistema.",
    "E_CONFIG_MATRICE_DUPLICATA": "Esiste gia' una riga matrice per questa coppia utility/tipo ruolo.",
    "E_CONFIG_MATRICE_FK": "Utility o tipo ruolo inesistente.",
    "E_CONFIG_MATRICE_NOT_FOUND": "Riga matrice utilities/ruoli non trovata.",
    "E_CONFIG_VALIDATION": "Parametri di configurazione non validi.",
    # ⚠️ SENZA `%s`: il ripiego serve proprio quando il messaggio del
    #    catalogo (che porta i suoi argomenti) non e' disponibile — un
    #    segnaposto qui resterebbe a video come tale.
    "E_CONTABILE_CORREZIONE_NON_REGISTRATA": "La distinta non e' registrata: finche' non ha prodotto movimenti non c'e' niente da correggere.",
    "E_CONTABILE_GIA_CORRETTA": "Questa distinta ha gia' la sua correzione: aprila e lavora li'.",
    # Distinta numerata sul registro (2026-09-17): il catalogo nomina canale e
    # sigle con tre `%s`; qui la frase senza argomenti.
    "E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE": "Il canale di incasso scelto e' di un altro emittente: scegliere un canale dell'emittente indicato, oppure cambiare emittente.",
    "E_CONTABILE_EMITTENTE_OBBLIGATORIO": "Per aprire una distinta senza canale bisogna indicare l'emittente.",
    "E_CONTABILE_ANNULLO_NON_MANUALE": "La distinta contabile non si annulla da qui: non e' stata compilata a mano.",
    "E_CONTABILE_CENTRO_ENTE_INCOERENTE": "Il centro di riscossione della testata non e' quello dell'ente di incasso indicato.",
    "E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE": "La distinta contabile ha ancora righe pronte da registrare: non si puo' chiudere.",
    "E_CONTABILE_DATI_OBBLIGATORI": "Per aprire una distinta contabile mancano dei dati obbligatori.",
    "E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE": "La distinta contabile e' cambiata da quando e' stata dichiarata: righe o totale non corrispondono piu'.",
    "E_CONTABILE_NON_REGISTRABILE": "La distinta contabile non e' registrabile: si registra solo una distinta validata.",
    "E_CONTABILE_NON_TROVATA": "Distinta contabile non trovata.",
    "E_CONTABILE_RIAPERTURA_NON_MANUALE": "La distinta contabile non si riapre: non e' stata compilata a mano.",
    "E_CONTABILE_SISTEMAZIONE_CON_LOTTO": "La distinta contabile e' nata da una sistemazione: non si collega a un lotto di fatturazione.",
    "E_CONTABILE_STATO_NON_CONFIGURATO": "Stato contabile non configurato: non esiste, oppure non e' attivo.",
    "E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA": "Il totale dichiarato sulla distinta contabile non quadra con la somma delle sue righe.",
    "E_CONTABILE_TRANSIZIONE_NON_AMMESSA": "La distinta contabile non puo' passare a quello stato.",
    "E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE": "La distinta contabile ha righe che nessuno ha ancora lavorato: si valida solo quando ogni riga e' stata guardata.",
    "E_CONTATTO_INCOMPLETO": "Contatto incompleto: hai inserito qualche dato ma mancano i campi obbligatori (nominativo e tipo contatto). Completa il contatto oppure svuota tutti i campi.",
    "E_CONTO_BANCARIO": "Il conto bancario indicato non e' utilizzabile.",
    "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO": "L'articolo e' gia' presente nel listino del documento: usare OVERRIDE per modificarne il prezzo, non AGGIUNTA.",
    "E_CONTRATTO_ANNULLATO_CON_FATTURE": "Impossibile annullare il contratto: esistono attivita' gia' fatturate. Per chiudere il contratto usa la cessazione (stato CESSATO con data di fine validita').",
    "E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO": "Impossibile attivare il contratto: il listino di riferimento non ha una versione in vigore oggi.",
    "E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE": "Modifica del listino bloccata: ci sono righe gia' caricate contro questo contesto pricing. Elimina prima le righe oppure annulla il contratto e creane uno nuovo.",
    "E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE": "Il contratto e' ATTIVO: listino, versione listino, variazione globale ed eccezioni sono congelati. Per modifiche sostanziali creare un nuovo contratto.",
    "E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE": "Categoria cliente congelata alla creazione del contratto: non modificabile.",
    "E_CONTRATTO_CESSAZIONE_SENZA_DATA": "Per cessare il contratto serve la data di fine.",
    "E_CONTRATTO_CLASSE_TIPO_INCOERENTE": "La classe utenza scelta non appartiene al tipo utenza indicato.",
    "E_CONTRATTO_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente selezionato.",
    "E_CONTRATTO_EMITTENTE_NON_RISOLTO": "Nessun emittente fiscale attivo: selezionalo in alto o indicalo nella richiesta.",
    "E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE": "Un articolo escluso non si modifica: l'esclusione si puo' solo togliere.",
    "E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA": "L'articolo e' un componente di un bundle: l'esclusione si applica al bundle padre, non al singolo componente. Per un bundle parziale crea un nuovo bundle in catalogo.",
    "E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI": "Impossibile rimuovere il listino di riferimento dal contratto: rimuovi prima le eccezioni OVERRIDE/ESCLUSIONE associate o sostituiscile con AGGIUNTA.",
    "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE": "Contratto senza listino di riferimento: aggiungere almeno un'AGGIUNTA con prezzo valorizzato prima di attivare.",
    "E_CONTRATTO_NON_MODIFICABILE": "Modifica non consentita: il contratto e' in uno stato che limita le operazioni. Per modifiche sostanziali creare un nuovo contratto.",
    "E_CONTRATTO_NON_TROVATO": "Contratto non trovato.",
    "E_CONTRATTO_OVERLAP_ESISTENTE": "Il periodo si sovrappone a un contratto gia' vincolante per lo stesso cliente e punto di fornitura: cambia le date o chiudi prima quel contratto.",
    "E_CONTRATTO_RIGA_NON_TROVATA": "Riga contratto non trovata.",
    "E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA": "Transizione stato contratto non consentita. Per cessare un contratto utilizzare il pulsante Cessa che gestisce automaticamente la data e la transizione.",
    "E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE": "Il tipo di una riga non si cambia: eliminare la riga e crearne una nuova del tipo voluto.",
    "E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA": "Date di successione del contratto non valide.",
    "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI": "Per questa utility tipo e classe utenza non vanno valorizzati.",
    "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI": "Per questa utility tipo e classe utenza sono obbligatori.",
    "E_CONTRATTO_VALIDO_AL_RETROATTIVO": "Cessazione contratto non ammessa con data retroattiva. La data di fine validita' deve essere oggi o futura.",
    "E_CORE_PROFILE_NOT_FOUND": "Profilo utente non trovato.",
    "E_CORE_VALIDATION": "Parametri non validi.",
    "E_CREDENZIALE_ALTRA_PERSONA": "L'email appartiene all'accesso di un'altra persona.",
    "E_CREDENZIALE_BLOCCATA": "Accesso bloccato dall'amministratore.",
    "E_CREDENZIALE_CON_STORIA": "Questa credenziale ha gia' lasciato traccia nell'applicazione: non si elimina.",
    "E_CREDENZIALE_CON_VESTI": "Questa credenziale ha delle vesti: non si elimina.",
    "E_CREDENZIALE_DA_CONFERMARE": "L'email appartiene gia' a un accesso: confermare quale usare.",
    "E_CREDENZIALE_DI_SISTEMA": "Le credenziali di sistema non si modificano da qui.",
    "E_CREDENZIALE_EMAIL_AMBIGUA": "Piu' accessi registrati con la stessa email.",
    "E_CREDENZIALE_GIA_OPERATORE": "L'email appartiene gia' a un operatore.",
    "E_CREDENZIALE_MOTIVO_OBBLIGATORIO": "Indicare il motivo del blocco.",
    "E_CREDENZIALE_NON_TROVATA": "Credenziale non trovata.",
    "E_CREDENZIALE_PERSONA_E_SISTEMA": "Un accesso non puo' essere insieme di una persona e di un processo automatico: usare un'altra email.",
    "E_CREDENZIALE_STORIA_NON_VERIFICABILE": "Non e' possibile verificare se questa credenziale ha una storia: non si elimina.",
    "E_DATABASE": "Errore durante l'operazione database.",
    "E_DATABASE_RETRYABLE": "Conflitto transazionale, riprovare l'operazione.",
    "E_DATA_AL_MINORE_DAL": "La data 'al' non puo' essere anteriore alla data 'dal'.",
    "E_DATA_APERTURA": "Cliente attivo senza data di apertura.",
    "E_DATA_CESSAZIONE_INVALIDA": "Data di cessazione precedente alla data di attivazione.",
    "E_DATA_CHIUSURA": "Data di chiusura anteriore alla data di attivazione.",
    "E_DATA_ERRATA": "Data errata o mancante.",
    "E_DATA_FINE_NON_MAGGIORE_DI_INIZIO": "La data finale deve essere successiva alla data iniziale.",
    "E_DATE_VALIDITA": "Automazione del guard sulle date di validita' fallita: il trigger non e' stato montato. Non dipende dai dati: segnalalo a chi mantiene il database.",
    "E_DATI_DI_SVILUPPO_IN_PRODUZIONE": "I dati di sviluppo (utenti e soggetti di prova) non si creano in un'installazione di produzione.",
    "E_DATI_SOCIETARI_CODICE_SDI_MANCANTE": "Hai scelto di inviare la fattura elettronica con il codice SDI, ma il codice manca.",
    "E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO": "Il codice destinatario SDI non e' valido: 7 caratteri, lettere maiuscole e cifre (6 per una pubblica amministrazione).",
    "E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE": "Hai scelto di inviare la fattura elettronica via PEC, ma la PEC manca.",
    "E_DATI_SOCIETARI_REQUIRED_MANCANTI": "Dati societari obbligatori mancanti per questo tipo soggetto.",
    "E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO": "Soggetto non trovato.",
    "E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO": "Policy dati societari non configurata per questo tipo soggetto.",
    "E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO": "Per questo tipo soggetto i dati societari non sono previsti.",
    "E_DATO_FISCALE_SENZA_TIPO_SOGGETTO": "Per indicare un regime fiscale o un titolo IVA serve prima il tipo soggetto.",
    "E_DBOPS_CHIAMATA_NON_VALIDA": "Chiamata non valida a una funzione di amministrazione del database.",
    "E_DB_ROLE_UNSAFE": "Errore interno di sicurezza sessione.",
    # brief-db-ddt-righe-evase-dall-ordine (2026-10-11): la riga evasa dall'ordine
    # o dal reso, il suo legame e l'annullo della bolla che li porta.
    "E_DDT_ANNULLO_CON_LEGAMI": "La bolla ha righe che vengono da un ordine o da un reso: annullandola, quelle quantita' tornano da spedire. Serve una conferma.",
    "E_DDT_EMISSIONE_SOLO_ONERI": "La bolla ha solo oneri e nessuna merce: non si emette. Un addebito senza merce si fa in commessa.",
    "E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO": "Il legame di una riga di DDT con la sua origine non si scrive direttamente: la quantita' si corregge col verbo, il legame si toglie con la riga.",
    "E_DDT_ONERE_NON_FATTURABILE": "Sulla bolla c'e' un onere che non verrebbe mai fatturato: se l'ordine si fattura alla conferma, l'onere va sull'ordine.",
    "E_DDT_RIGA_EVASA_FERMA": "La riga viene da un ordine o da un reso: articolo, unita' di misura e quantita' non si cambiano dalla riga.",
    "E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI": "La riga e' legata a piu' righe d'origine: la quantita' evasa non si puo' correggere da sola.",
    "E_DDT_RIGA_NON_EVASA": "La riga non viene da un ordine o da un reso: la sua quantita' si modifica dalla riga.",
    "E_DDT_CAUSALE_IMMUTABILE": "La causale di trasporto si sceglie solo in bozza: dopo l'emissione la bolla e' quella.",
    "E_DDT_CAUSALE_OBBLIGATORIA": "Causale di trasporto obbligatoria per emettere il DDT.",
    "E_DDT_CLIENTE_IMMUTABILE": "Il cliente della bolla si sceglie solo in bozza: se e' sbagliato, annulla la bolla e creane una nuova.",
    "E_DDT_CLIENTE_OBBLIGATORIO": "La causale della bolla manda la merce a un cliente: scegli il billing account prima di emetterla.",
    "E_DDT_EMISSIONE_SENZA_RIGHE": "DDT senza righe attive: impossibile emettere.",
    "E_DDT_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente selezionato.",
    "E_DDT_MAGAZZINO_IMMUTABILE": "Il magazzino della bolla si sceglie solo in bozza: dopo l'emissione la merce e' gia' uscita da li'.",
    "E_DDT_MAGAZZINO_INCOERENTE": "Magazzino non valido per questa bolla: deve essere dell'azienda che la emette, e diverso dalla partenza se e' l'arrivo di un trasferimento.",
    "E_DDT_MAGAZZINO_OBBLIGATORIO": "La bolla non indica il magazzino: senza, la merce non ha da dove uscire (o dove entrare).",
    "E_DDT_NESSUNA_RIGA": "Il DDT non ha righe eleggibili per l'operazione.",
    "E_DDT_NIENTE_DA_EVADERE": "Nessuna quantita' residua da evadere sull'ordine.",
    "E_DDT_NOT_FOUND": "DDT non trovato.",
    "E_DDT_ORDINE_NOT_FOUND": "Ordine di origine non trovato.",
    "E_DDT_ORDINE_STATO_NON_EVADIBILE": "L'ordine non e' in uno stato che consente l'evasione (genera DDT).",
    "E_DDT_PRELIEVI_INCOMPLETI": "I prelievi di una riga della bolla non coprono la quantita': indicare da quale lotto, seriale o ubicazione esce la merce.",
    "E_DDT_PRELIEVO_INCOERENTE": "Prelievo non valido: si preleva l'articolo della riga se e' gestito a magazzino, altrimenti i componenti gestiti del suo kit.",
    "E_DDT_PREZZO_NON_RISOLVIBILE": "Causale fatturabile ma una riga del DDT non ha un prezzo risolvibile (proprio o ereditato dall'ordine).",
    "E_DDT_RIGA_IVA_MANCANTE": "Una riga del DDT ha un prezzo ma nessuna aliquota IVA: sceglila, oppure togli il prezzo se la merce non si valorizza.",
    "E_DDT_RIGA_NON_TROVATA": "Riga DDT non trovata.",
    # Ritirato il 2026-10-25 (porta comune, E_DOC_STATO_SOLO_DAL_VERBO): resta per il diario.
    "E_DDT_RIGA_ONERE_NON_CORREGGIBILE": "La riga e' un addebito: la correzione della quantita' evasa vale solo per la merce.",
    "E_DDT_STATO_SOLO_DA_VERBO": "La bolla muove merce: il cambio di stato si fa solo dall'operazione della bolla, che registra i movimenti di magazzino.",
    "E_DDT_STATO_TRANSIZIONE": "Operazione non ammessa nello stato corrente del DDT.",
    "E_DDT_TRASPORTO_NON_DOVUTO": "La bolla addebita il trasporto al cliente, ma in porto assegnato o con addebito a terzi il cliente non lo deve.",
    "E_DDT_VALIDAZIONE": "Parametri DDT non validi.",
    "E_DEFAULT_CONTATTO_MISSING": "Contatto principale obbligatorio.",
    "E_DEFAULT_ERRATO": "Nessun valore di default configurato per il parametro.",
    "E_DEFINIZIONE_BOZZA_ESISTENTE": "Esiste gia' una bozza di edizione per questo scope (tipo prestazione + emittente).",
    "E_DEFINIZIONE_NON_PUBBLICABILE": "La bozza non e' pubblicabile: servono almeno uno step attivo e nessun ciclo di prerequisiti.",
    "E_DEFINIZIONE_NON_TROVATA": "Nessuna definizione di workflow pubblicata per questo tipo.",
    "E_DEFINIZIONE_NOT_FOUND": "Edizione di workflow o step non trovato.",
    "E_DEFINIZIONE_NO_PUBBLICATA": "Nuova versione non ammessa: manca un'edizione pubblicata da cui derivare.",
    "E_DEFINIZIONE_PUBBLICATA_IMMUTABILE": "Edizione non modificabile nello stato corrente.",
    "E_DEFINIZIONE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato dell'edizione non ammessa.",
    "E_DELETE_BLOCK": "Generazione del trigger di blocco cancellazione fallita.",
    "E_DELETE_BLOCKED_FUL": "Cancellazione bloccata: esistono legami fulfillment.",
    "E_DELETE_CONTRATTO_CON_SUCCESSIVI": "Il contratto e' il precedente di altri contratti: non si puo' eliminare.",
    "E_DELETE_DOC_CON_RIGHE": "Il documento ha ancora del contenuto (righe, eccezioni, attivita' o documenti collegati): si puo' eliminare solo una bozza vuota.",
    "E_DELETE_DOC_NON_BOZZA": "Il documento non e' piu' in bozza: si puo' eliminare solo finche' e' in bozza.",
    "E_DELETE_NOT_ALLOWED": "Cancellazione non permessa su questi dati.",
    "E_DELETE_RIGA_DOC_NON_BOZZA": "Il documento non e' piu' in bozza: le sue righe si possono togliere solo finche' e' in bozza.",
    "E_DELETE_RIGA_DOC_REFERENZIATA": "Questa riga e' gia' stata usata in un reso o in una riconsegna: non si puo' togliere.",
    "E_DIAGNOSTICA_NON_REGISTRATA": "Una scrittura di diagnosi non e' andata a buon fine: il lavoro e' proseguito lo stesso.",
    "E_DISSOCIAZIONE_PARENT_CON_ATTIVITA": "Parent non rimovibile: esistono attivita' non fatturate sul billing account.",
    # brief-db-annullo-documento-con-legami (2026-10-11): l'avviso unico
    # dell'annullo di un documento con legami (bolla, ordine, preventivo,
    # contratto). Sostituisce E_DDT_ANNULLO_CON_LEGAMI, che resta per il diario.
    "E_DOC_ANNULLO_CON_LEGAMI": "Annullando il documento si riaprono i suoi legami con altri documenti: quantita' da spedire, righe da ordinare o da mandare in commessa, accrediti di reso, l'offerta da cui nasce o la revisione precedente di un'offerta. Serve una conferma.",
    "E_DOC_CLIENTE_DIVERSO_DA_BA": "Il cliente o la utility non corrispondono al billing account del documento: lasciali vuoti, li mette il billing account.",
    "E_DOC_CLIENTE_DIVERSO_DA_SORGENTE": "Il cliente deve essere quello del documento da cui nasce.",
    "E_DOC_DATA_OLTRE_CONSEGNA_RIGHE": "La data del documento non puo' andare oltre una data di consegna gia' scritta su una riga.",
    "E_DOC_EMITTENTE_BA_INCOERENTE": "L'azienda che emette il documento non e' quella del cliente: lasciala vuota, la mette il billing account.",
    "E_DOC_EMITTENTE_FUORI_BOZZA": "L'azienda che emette il documento si sceglie solo in bozza: se e' sbagliata, annulla il documento e creane uno nuovo.",
    # brief-db-testata-dopo-emissione (fase 2, 2026-10-10): la testata dopo la
    # bozza, un codice per famiglia di colonne. Il lock e' il BB di testata.
    "E_DOC_EMITTENTE_IMMUTABILE": "L'azienda che emette il documento si sceglie alla creazione e non si cambia, nemmeno in bozza.",
    "E_DOC_GIA_NELLO_STATO": "Il documento e' gia' nello stato chiesto: non c'e' niente da cambiare.",
    "E_DOC_IDENTITA_FUORI_BOZZA": "Data, valuta e numerazione del documento si scelgono solo in bozza.",
    "E_DOC_CONDIZIONI_FUORI_BOZZA": "In questo stato le condizioni commerciali del documento non si cambiano piu': annulla il documento e rifallo, oppure creane una nuova revisione.",
    "E_DOC_CLIENTE_FUORI_BOZZA": "Il cliente del documento si sceglie solo in bozza: se e' sbagliato, annulla il documento e creane uno nuovo.",
    "E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE": "La data di consegna e' anteriore alla data del documento.",
    "E_DOC_SORGENTE_FUORI_BOZZA": "Il documento da cui nasce si sceglie solo in bozza.",
    # brief-modello-documento-vendita §4-bis (2026-10-24): un documento nasce solo
    # nel suo stato iniziale. TECNICO: nessuna maschera crea un documento gia' avanti.
    "E_DOC_STATO_INIZIALE_NON_VALIDO": "Un documento nuovo nasce solo nel suo stato iniziale: segnalalo all'assistenza.",
    # brief-modello-documento-vendita §7 (2026-10-25): lo stato di un documento sul
    # modello si scrive solo dal suo verbo, e i passaggi di processo li fa solo il
    # verbo che ne e' la causa. Due codici TECNICI: nessuna maschera li provoca.
    "E_DOC_STATO_SOLO_DAL_VERBO": "Lo stato del documento si cambia solo dalle sue operazioni (emetti, conferma, annulla...), non con una modifica diretta: segnalalo all'assistenza.",
    "E_DOC_PASSAGGIO_DI_PROCESSO": "Questo passaggio di stato lo fa il sistema, come conseguenza di un'altra operazione: non si chiede a mano.",
    # brief-db-indirizzi-documento-seguono-il-cliente (2026-10-12): la scheda di
    # fornitura segue la coppia della testata. Due codici TECNICI.
    "E_DOC_FORNITURA_FUORI_TESTATA": "La scheda di fornitura indicata non e' della fornitura del documento: segnalalo all'assistenza.",
    "E_DOC_FORNITURA_PARAMETRO_MANCANTE": "Una funzione della scheda di fornitura e' stata chiamata senza il dato che le serve: segnalalo all'assistenza.",
    "E_DOC_CHIUSO": "Il documento e' chiuso, e non si modifica piu'.",
    # brief-db-testata-dopo-emissione (giro R-DB, 2026-10-11): i satelliti del
    # documento (indirizzi, fornitura) solo in bozza; il listino sotto le righe.
    "E_DOC_DATI_COLLEGATI_NON_BOZZA": "Il documento non e' piu' in bozza: indirizzi e fornitura si cambiano solo finche' e' in bozza.",
    "E_DOC_LISTINO_CAMBIO_CON_RIGHE": "Il listino del documento non si cambia: ci sono righe caricate con quello attuale. Elimina prima le righe.",
    "E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI": "Il listino del documento non si toglie: ci sono eccezioni di prezzo o di esclusione che dipendono da quello. Rimuovile prima.",
    "E_DOC_LISTINO_EMITTENTE_DIVERSO": "Il listino scelto e' di un'altra azienda: il documento puo' usare solo un listino della sua azienda emittente.",
    "E_DOC_LISTINO_UTILITY_DIVERSA": "Il listino scelto e' di un'altra utility: il documento puo' usare solo un listino della sua utility.",
    "E_DOCUMENTI_ASSET_DELETE_BLOCKED": "Eliminazione asset non consentita. Disattivare l'asset impostando valido_al.",
    "E_DOCUMENTI_ASSET_FILE_IMMUTABILE": "File asset immutabile: storage_key/sha256/file_size/mime/file_name non modificabili. Crea un nuovo asset.",
    "E_DOCUMENTI_DENIED": "Operazione documentale non consentita.",
    "E_DOCUMENTI_GENERATO_COERENZA": "Incoerenza nei riferimenti del documento generato.",
    "E_DOCUMENTI_GENERATO_DELETE_BLOCKED": "Documento generato non eliminabile: la tabella e' append-only per audit.",
    "E_DOCUMENTI_GENERATO_FILE_IMMUTABILE": "File del documento generato immutabile dopo il salvataggio. Rigenera il documento.",
    "E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE": "Snapshot del documento generato immutabile: i dati di generazione sono congelati.",
    "E_DOCUMENTI_NOT_FOUND": "Documento o template non trovato.",
    "E_DOCUMENTI_PERSONALIZZA_NON_STANDARD": "Si personalizza solo un modello standard: questo e' gia' il modello di un'azienda.",
    "E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO": "Parametro non valido per la pubblicazione della versione template.",
    "E_DOCUMENTI_RENDER_FAILED": "Generazione PDF documento fallita.",
    "E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO": "Parametro non valido per la scelta del modello di stampa.",
    "E_DOCUMENTI_STORAGE_FAILED": "Errore lettura/scrittura file documento.",
    "E_DOCUMENTI_TEMPLATE_AMBIGUO": "La sorgente produce piu' tipi di documento: per scegliere il modello di stampa va indicato il tipo.",
    "E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA": "La versione indicata come origine non e' una versione del modello standard dello stesso documento.",
    "E_DOCUMENTI_TEMPLATE_NON_COERENTE": "Il modello di stampa indicato non e' adatto a questo documento.",
    "E_DOCUMENTI_TEMPLATE_NON_RISOLTO": "Nessun modello di stampa per questo documento: ne' uno dell'azienda ne' quello standard.",
    "E_DOCUMENTI_TEMPLATE_NON_STAMPABILE": "Il modello di stampa indicato oggi non puo' stampare: e' disattivato o non ha una versione pubblicata valida oggi.",
    "E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO": "L'azienda ha modelli di stampa suoi per questo documento, ma nessuno e' segnato come predefinito.",
    "E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA": "Il modello standard non si modifica dall'applicazione: per cambiarlo, personalizzalo per la tua azienda.",
    "E_DOCUMENTI_VALIDATION": "Parametri documento non validi.",
    "E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO": "Il documento non si puo' generare: un valore numerico non e' un numero.",
    # Il catalogo porta la frase con quattro `%s` (versione, template, le due
    # forme) e l'altra con uno (che cosa manca); qui le frasi senza argomenti.
    "E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA": "La versione del template legge i dati in una forma diversa da quella in cui il sistema li prepara: il documento non si stampa con questa versione.",
    "E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE": "Non si puo' verificare che il template legga i dati del documento.",
    "E_DOCUMENTI_VERSIONE_DELETE_BLOCKED": "Eliminazione versione non consentita: stato non BOZZA o gia' usata da documenti generati.",
    "E_DOCUMENTI_VERSIONE_NOT_FOUND": "Versione template documento non trovata.",
    "E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO": "La data del documento e' anteriore a quella dell'ultimo numero gia' emesso su questo registro: la sequenza di un sezionale segue il tempo, e il numero successivo non puo' portare una data precedente.",
    "E_DOCUMENTI_VERSIONE_OVERLAP": "Le date di validita' si sovrappongono con un'altra versione PUBBLICATA attiva del template. Chiudi quella esistente prima di pubblicare la nuova.",
    "E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE": "Versione PUBBLICATA non modificabile. Crea o clona una nuova versione BOZZA.",
    "E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO": "La versione template non e' in uno stato pubblicabile.",
    "E_DOC_COMPONENTE_BOM_NON_VALIDA": "Riga BoM non valida alla data del documento.",
    "E_DOC_COMPONENTE_ID_INCOERENTE": "Componente non coerente con la riga di distinta base indicata.",
    "E_DOC_COMPONENTE_LISTINO_MANCANTE": "Listino non configurato per uno dei componenti esposti in fattura. Configura il listino del componente prima di creare la riga.",
    "E_DOC_COMPONENTE_NON_BOM": "Il componente non appartiene alla distinta base dell'articolo padre.",
    "E_DOC_COMPONENTE_OBBLIGATORIO": "Componente obbligatorio: non puo' essere disattivato dalla riga documento.",
    "E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO": "Componente obbligatorio: il prezzo deve essere diverso da zero.",
    "E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE": "Impossibile emettere: componenti senza prezzo valorizzato.",
    "E_DOC_COMPOSITO_BOM_VUOTA": "Articolo composito senza componenti validi alla data: distinta scaduta o assente.",
    "E_DOC_PREZZO_PENDENTE": "Non si puo' procedere: ci sono prezzi ancora in attesa di approvazione.",
    "E_DOC_PREZZO_RIFIUTATO": "Non si puo' procedere: ci sono prezzi rifiutati dal responsabile.",
    "E_DOC_RIGA_NON_COMPOSITO": "L'articolo della riga non e' composito: impossibile aggiungere componenti.",
    "E_DOC_RIGA_NON_AMMESSA": "Una riga del documento non e' piu' ammessa: aprirla e correggerla secondo il motivo indicato (articolo, erogazione o fonte della quantita'), oppure toglierla.",
    "E_DOC_RIGHE_LOCK_MONTAGGIO": "Il controllo «si tocca solo in bozza» del documento (righe o testata) e' configurato male nel database: segnalalo, non e' una situazione che dipende dai tuoi dati.",
    "E_DOC_SORGENTE_NON_TROVATA": "Il documento da cui nasce non esiste o non e' visibile.",
    "E_DOC_TIPO_NON_GESTITO": "Tipo di documento non gestito dal controllo di cancellazione: segnalalo, non e' una situazione che dipende dai tuoi dati.",
    "E_DOC_UTILITY_IMMUTABILE": "La utility del documento si sceglie alla creazione e non si cambia, nemmeno in bozza.",
    "E_EMAIL": "Errore configurazione email.",
    "E_EMAIL_ACCOUNT_NON_CONFIGURATO": "Nessun account email configurato.",
    "E_EMAIL_ACCOUNT_NOT_FOUND": "Account email non trovato.",
    "E_EMAIL_ADMIN": "Operazione sulla configurazione email non riuscita.",
    "E_EMAIL_ALLEGATI_LIMITE": "La mail ha gia' il numero massimo di allegati: togline uno per aggiungerne un altro.",
    "E_EMAIL_ALLEGATO_FILE_MANCANTE": "File dell'allegato non disponibile.",
    "E_EMAIL_ALLEGATO_NON_BOZZA": (
        "La mail non e' piu' in bozza: i suoi allegati si possono aggiungere, "
        "modificare o togliere solo finche' e' in bozza."
    ),
    "E_EMAIL_ALLEGATO_NOT_FOUND": "Allegato non trovato.",
    "E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO": "Percorso dell'allegato non valido.",
    "E_EMAIL_BOZZA_NOT_FOUND": "Bozza non trovata.",
    "E_EMAIL_LOG_INESISTENTE": (
        "Impossibile registrare l'esito dell'invio: l'email indicata non esiste."
    ),
    "E_EMAIL_LOG_NON_DI_SISTEMA": (
        "Impossibile registrare l'esito dell'invio: l'email indicata non e' di "
        "sistema. Va chiusa dal perimetro a cui appartiene, non da questa porta."
    ),
    "E_EMAIL_LOG_NOT_FOUND": "Log email non trovato.",
    "E_EMAIL_NON_BOZZA": "Questa mail non e' piu' in bozza: non si puo' piu' modificare, inviare o annullare.",
    "E_EMAIL_OP": "Operazione email non riuscita.",
    "E_EMAIL_TEMPLATE_NON_CONFIGURATO": "Nessun template email configurato per questo invio.",
    "E_EMAIL_TEMPLATE_NOT_FOUND": "Template email non trovato.",
    "E_EMITTENTE_ATTIVO_NON_VALIDO": "Emittente non selezionabile: inesistente, disattivato o fuori dal tuo perimetro.",
    "E_EMITTENTE_ATTIVO_TOKEN": "Refresh token richiesto per applicare il cambio di emittente.",
    "E_EMITTENTE_CODICE_FORMA_NON_VALIDA": "Sigla dell'emittente non valida: sono ammesse solo lettere maiuscole e cifre, da 2 a 10 caratteri. La sigla entra nel codice delle commesse, che si legge separandolo sui trattini.",
    "E_EMITTENTE_DEFAULT_MISSING": "Emittente fiscale default non configurato.",
    "E_EMITTENTE_DEFAULT_SINGLETON": "Un solo emittente fiscale puo' essere impostato come default.",
    "E_EMITTENTE_DISATTIVAZIONE_BLOCCATA": "Impossibile disattivare l'emittente fiscale: esistono entita' collegate.",
    "E_EMITTENTE_MODI_INVALIDO": "Il registro dei modi dell'emittente non si puo' usare: descrive una strada che il database non ha.",
    "E_EMITTENTE_MODI_NON_SCRIVIBILE": "Il registro dei modi dell'emittente non si modifica dall'applicazione.",
    "E_EMITTENTE_NON_MODIFICABILE": "L'emittente fiscale di un operatore e' immutabile. Per cambiare l'associazione disattivare l'utente e crearne uno nuovo per l'altro emittente.",
    # BB emittente di default (2026-09-17): sostituisce E_ORDINE_/E_PREV_/
    # E_CONTRATTO_EMITTENTE_NON_RISOLTO, che restano qui perche' ritirati, non
    # cancellati. Stessa frase dei ripieghi delle sorelle.
    "E_EMITTENTE_NON_RISOLTO": "Nessun emittente fiscale attivo: selezionalo in alto o indicalo nella richiesta.",
    "E_EMITTENTE_REGIME_CONFERMA_DERIVATA": "La conferma del regime fiscale la scrive il database. Per confermare il regime si scrive il regime, anche con lo stesso valore.",
    "E_ENTE_INCASSO_CONTO_NON_DI_INCASSO": "Il conto indicato per questo canale di incasso non e' un conto di incasso.",
    "E_ENTE_INCASSO_NON_TROVATO": "Il canale di incasso indicato non esiste, oppure appartiene a un emittente fuori dal tuo perimetro.",
    "E_ENTE_INCASSO_PSP_NON_CENSITO": "Il soggetto-ruolo ha il ruolo PSP ma non risulta censito e attivo fra i PSP.",
    "E_ENTE_INCASSO_PSP_RUOLO_NON_PSP": "Il soggetto-ruolo indicato non ha il ruolo PSP: non puo' essere il prestatore di un ente di incasso di tipo PSP.",
    "E_ENTE_INCASSO_PSP_SOGGETTO_RUOLO_OBBLIGATORIO": "L'ente di incasso e' di tipo PSP: il soggetto-ruolo del prestatore di servizi di pagamento e' obbligatorio.",
    "E_ENTE_INCASSO_SENZA_CENTRO": "Ente di incasso non utilizzabile: non esiste, oppure non ha un centro di riscossione configurato.",
    "E_ERRORE_PARAMETRI": "Parametri obbligatori mancanti o non validi.",
    "E_ERRORE_PARAMETRI_TABELLA": "Parametro non trovato nella tabella di configurazione.",
    "E_ETICHETTA_DI_PROVA_IMMUTABILE": "Un'etichetta di prova non si cambia e non si toglie.",
    "E_EVENTO_DOCUMENTO_DELETE_VIETATA": "Eliminazione eventi documento non consentita: timeline append-only.",
    "E_EVENTO_DOCUMENTO_UPDATE_VIETATA": "Modifica eventi documento non consentita: timeline append-only.",
    "E_EVENT_LOG_ENTITY_TYPE_IGNOTO": "Il giornale non sa dove collocare un evento di questo tipo di entita'.",
    "E_EVENT_LOG_SCOPE_NON_RISOLTO": "L'evento non si lega a nessun emittente: il giornale non registra righe senza perimetro.",
    "E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE": "Le colonne che dicono dove vive il documento non si cambiano su una famiglia che ha gia' dei registri: quei registri ne portano dentro la forma.",
    "E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE": "La famiglia di documento dichiara un riferimento che non esiste: correggi il campo indicato.",
    "E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA": "La famiglia dichiara una colonna della serie che sul documento non distingue il numero: nessun vincolo di unicita' le tiene insieme, quindi la serie aprirebbe un contatore che collide con numeri gia' emessi.",
    "E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA": "La tabella dei documenti di questa sorgente e' gia' numerata da un'altra famiglia attiva: si spegne prima quella, oppure si sceglie un'altra sorgente.",
    "E_FATTURAZIONE_GIRO_NESSUN_LOTTO": "Nessun lotto da fatturare nel perimetro indicato.",
    "E_FATTURAZIONE_GIRO_PAYLOAD": "Parametri del giro di fatturazione non validi.",
    "E_FATTURAZIONE_MIRATA_TRONCATA": "Emissione mirata troppo ampia: nessun lotto è stato creato. Selezionare meno gruppi e rilanciare.",
    "E_FATTURAZIONE_NUMERA_PAYLOAD": "Parametri della numerazione non validi.",
    "E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO": "La data del documento e' anteriore a quella dell'ultimo numero gia' emesso su questo registro: la sequenza di un sezionale segue il tempo, e il numero successivo non puo' portare una data precedente.",
    "E_FATTURA_DATA_NON_MODIFICABILE": "La fattura e' gia' numerata: la data del documento non si puo' piu' cambiare.",
    "E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE": "La data del documento e' troppo vecchia perche' sia ancora emettibile su questo registro: fra la data di un documento fiscale e il suo invio c'e' un termine, e quello e' passato. Non e' un problema di sequenza — si rimedia spostando la data in avanti, e il calendario del dialog di numerazione si apre gia' sulla prima data ammessa.",
    "E_FATTURA_EMITTENTE_NON_RISOLTO": "Emittente fiscale non risolvibile per la fattura in coda di stampa.",
    "E_FATTURA_GIA_FISCALE": "La fattura e` oltre lo stato pre-fiscale: non puo` essere tolta dal lotto.",
    "E_FATTURA_GIA_NUMERATA": "La fattura ha gia` un numero: toglierla dal lotto aprirebbe un buco nella numerazione fiscale.",
    "E_FATTURA_NON_ANNULLABILE": "Fattura gia' numerata: l'annullamento non e' ammesso.",
    "E_FATTURA_NON_COLLEGATA_AL_LOTTO": "La fattura non risulta collegata a questo lotto: ricaricare l'elenco.",
    "E_FATTURA_NON_EMETTIBILE_INCOMPLETA": "Fattura non emettibile: documento incompleto (indirizzi, intestazione o sede legale dell'azienda). Completare l'anagrafica e rieseguire lo step DRAFT del lotto, che riscrive indirizzi e intestazione.",
    "E_FATTURA_NON_NUMERABILE_INCOERENTE": "Fattura non numerabile: totali, riepiloghi IVA o piano rate incoerenti. Il dettaglio dei motivi e' nei log della fattura.",
    "E_FATTURA_NON_TROVATA": "Fattura non trovata.",
    "E_FATTURA_NUMERATA_NON_CANCELLABILE": "La fattura ha gia' un numero fiscale: non si puo' cancellare. Ricaricare la pagina; se e' sbagliata, si corregge con una nota di credito.",
    "E_FATTURA_NUMERO_NON_MODIFICABILE": "La fattura ha gia' un numero fiscale: registro, anno, serie e numero non si possono piu' cambiare.",
    "E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE": "La fattura e' su un registro di numerazione che appartiene a un altro emittente: ogni registro e' di un emittente solo, e due partite IVA non possono pescare dalla stessa serie.",
    "E_FATTURA_RETTIFICATA_SENZA_NUMERO": "Numerazione rifiutata: il documento rettifica righe di altri documenti che non risultano ancora numerati. Numerare prima quelli, poi ripetere. Se uno di essi non risulta accessibile e' fuori dal perimetro di chi opera, e va numerato da chi lo gestisce.",
    "E_FATTURA_RIGA_CAPOFILA_INCOERENTE": "Il legame fra una riga di fattura e la sua capofila non e' coerente: la catena deve restare a un solo passaggio, dalla capofila alle sue parti. E' un'anomalia tecnica del documento, non un dato da correggere a mano.",
    "E_FATTURA_RIGA_IVA_MANCANTE": "La fattura non si emette: una riga non ha l'aliquota IVA. Aprire l'articolo della riga e indicarne l'aliquota, poi ripetere l'emissione.",
    "E_FATTURA_RIGA_CONGELATA": "Lo stato della fattura non consente piu' di modificare le righe.",
    "E_FATTURA_SATELLITE_CONGELATO": "Lo stato della fattura non consente piu' di modificare questi dati.",
    "E_FATTURA_SENZA_RIGHE": "Numerazione fiscale rifiutata: il documento non ha righe.",
    "E_FATTURE_PLAFOND_CONSUMATO": "Non si puo' disfare: alcune di queste fatture hanno gia' consumato il plafond di una dichiarazione d'intento. Portare avanti il lotto: il passaggio a definitiva non consuma il plafond due volte.",
    "E_FATTURE_RIGHE_RETTIFICATE": "Non si puo' disfare: su alcune righe di queste fatture e' gia' stato registrato un accredito.",
    "E_FATT_IMMEDIATA_NON_MODIFICABILE": "La fatturazione immediata non e` piu` modificabile: il documento e` gia` stato inviato in commessa. Per fatturare subito questo lavoro usa l'emissione mirata dal cruscotto Competenza.",
    "E_FLUSSI_COMPETENZA_MANCANTE": "Operatore non abilitato per questo tipo di flusso.",
    "E_FLUSSI_ESITO_NON_AMMESSO": "Esito non ammesso per questo step.",
    "E_FLUSSI_ESITO_OBBLIGATORIO": "Esito obbligatorio per completare il flusso.",
    "E_FLUSSI_GIA_ASSEGNATO": "Flusso gia' assegnato a un operatore.",
    "E_FLUSSI_PRESA_CARICO_STATO_ERRATO": "Presa in carico non consentita: il flusso non e' DA_ESEGUIRE.",
    "E_FLUSSI_PRESA_NON_ELIGIBILE": "Presa in carico non consentita: il flusso e' instradato a un altro reparto.",
    "E_FLUSSI_TEMPLATE_FUORI_DEFINIZIONE": "Lo step non appartiene alla definizione della pratica.",
    "E_FLUSSI_TRANSIZIONE_NON_AMMESSA": "Transizione di stato flusso non ammessa.",
    "E_FLUSSO_COMPETENZA_INSERT": "Errore durante l'inserimento della competenza del flusso.",
    "E_FLUSSO_COMPETENZA_NOT_FOUND": "Competenza del flusso non trovata.",
    "E_FLUSSO_ID_INVALIDO": "Flusso non valido.",
    "E_FLUSSO_ID_OBBLIGATORIO": "Flusso obbligatorio.",
    "E_FLUSSO_INSERT": "Errore durante l'inserimento del flusso.",
    "E_FLUSSO_NOT_FOUND": "Flusso non trovato.",
    "E_FLUSSO_OWNERSHIP": "Flusso non appartiene alla pratica indicata.",
    "E_FLUSSO_PRESA_IN_CARICO": "Errore durante la presa in carico del flusso.",
    "E_FLUSSO_VALIDATION": "Parametri flusso non validi.",
    # Fondi fattura (brief-db-fondo-fattura-ricalcolo-e-governo). Il fondo e' un
    # ATTO: si crea una volta e non si ricalcola. ⚠️ Nessuno di questi messaggi
    # parla del SEGNO dell'importo: un fondo negativo e' legittimo — il capo
    # inferiore della banda del minimo esiste apposta per riportare avanti i
    # crediti — e cio' che si vieta e' la mancata corrispondenza col documento.
    "E_FONDO_ATTO_IMMUTABILE": (
        "Il fondo fattura e' gia' stato creato e non si puo' modificare: "
        "importo, fattura di origine, tipo e origine sono definitivi."
    ),
    # ⭐ La soglia e' quella del congelamento fiscale, la STESSA con cui il
    # progetto congela gli altri satelliti della fattura. Non nomina la tabella:
    # e' la ragione per cui non riusa `E_FATTURA_SATELLITE_CONGELATO`, che
    # riceve `TG_TABLE_NAME` nel VARIADIC e la metterebbe a video.
    "E_FONDO_FIGLIA_CONGELATA": (
        "Il fondo e' assegnato a una fattura che non si puo' piu' modificare: "
        "cancellarlo cambierebbe un documento ormai definitivo."
    ),
    "E_FONDO_MOTIVO_OBBLIGATORIO": (
        "Motivo obbligatorio: un fondo creato a mano o annullato deve dire perche'."
    ),
    # ⚠️ Copre i TRE motivi che parlano di DENARO (atto eseguito, riga
    # contabile registrata, distinta chiusa): quale dei tre viaggia nella
    # `cause` del contesto, non nella frase.
    "E_FONDO_NON_CANCELLABILE": (
        "Il fondo non si puo' cancellare perche' il denaro si e' gia' mosso: "
        "l'atto e' stato eseguito, oppure la sua riga contabile e' registrata "
        "o si trova in una distinta chiusa."
    ),
    "E_FONDO_NON_CORRISPONDE_SORGENTE": (
        "Il fondo non corrisponde alla fattura da cui nasce: deve avere lo stesso "
        "segno del totale del documento e non superarlo in valore assoluto."
    ),
    # ⛔ «Non esiste» e «non e' tuo» danno di proposito la STESSA frase: la
    # tabella ha la row security, e distinguerle direbbe a chi e' fuori
    # perimetro che quel fondo c'e'.
    "E_FONDO_NON_TROVATO": (
        "Il fondo fattura non esiste o non e' accessibile."
    ),
    "E_FONDO_SOGLIE_INCOMPLETE": (
        "Le due soglie del minimo si dichiarano insieme: valorizzarle entrambe "
        "oppure lasciarle entrambe vuote."
    ),
    "E_FONDO_STATO_NON_AMMESSO": (
        "Passaggio di stato del fondo non ammesso: un fondo annullato non si riapre."
    ),
    # ⭐ Il rifiuto NOMINA L'ALTERNATIVA invece di dire «non si puo'»: chi legge
    # sta provando a disfare un riporto, e la strada esiste — passa dall'atto
    # che lo ha creato, non dal fondo che ne e' la conseguenza.
    "E_FONDO_TRATTENUTO_DA_SISTEMAZIONE": (
        "Il fondo e' nato da una sistemazione e non si cancella da qui: "
        "si disfa annullando quella sistemazione."
    ),
    "E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO": "La forma giuridica non e' ammessa per questo tipo soggetto.",
    "E_FORMA_GIURIDICA_PAESE": "Forma giuridica non coerente con il paese del soggetto.",
    "E_FORNITORE_BLOCCATO": "Fornitore bloccato: non e' possibile emettere ordini.",
    "E_FORNITORE_ID_INVALIDO": "Identificativo fornitore non valido.",
    "E_FORNITORE_NON_ATTIVO": "Fornitore non attivo.",
    "E_FORNITORE_NON_TROVATO": "Fornitore non trovato.",
    "E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA": "Aliquota ritenuta obbligatoria (> 0) quando ritenuta d'acconto e' attiva.",
    "E_FULFILL_NOT_FOUND": "Riga ordine o riga DDT non trovata: legame fulfillment inesistente.",
    "E_GENERATE_FATTURE_RIGHE_VALIDATION": "Parametri generazione righe non validi.",
    "E_GENERAZIONE_PRATICA": "Errore durante la generazione della pratica dal flusso.",
    "E_GENERAZIONE_TEMPLATE_NON_IN_DEFINIZIONE": "Lo step dichiarato dalla regola non esiste nella definizione della pratica figlia.",
    "E_GENERICO": "Errore non gestito.",
    "E_GESTORE_SINGLETON_VIOLATO": "Esiste gia' un gestore: non e' possibile crearne un secondo.",
    "E_GESTORE_SOGGETTO_RUOLO_MANCANTE": "Il soggetto_ruolo indicato per il gestore non esiste.",
    "E_GIORNALE_QUERY": "Errore durante la lettura del giornale.",
    "E_GROUP_ATTIVITA_INVALID_DATA": "Dati gruppo attivita non validi.",
    "E_GROUP_ATTIVITA_NOT_FOUND": "Gruppo attivita non trovato.",
    "E_GROUP_ATTIVITA_VALIDATION": "Parametri gruppo attivita non validi.",
    "E_GUC_RESET_FAILED": "Errore interno di sicurezza sessione.",
    "E_HANDLER_NON_REGISTRATO": "Handler di flusso non registrato: configurazione incompleta.",
    "E_IDEMPOTENCY_IN_PROGRESS": "L'operazione e' ancora in corso.",
    "E_IDEMPOTENCY_KEY_REQUIRED": "Idempotency-Key obbligatoria per questa operazione.",
    "E_IDEMPOTENCY_KEY_RIUSATA": "La chiave di invio di questa richiesta appartiene a un'altra operazione.",
    "E_IDENTITA_NON_ATTIVA": "Sessione non piu' valida: effettua nuovamente l'accesso.",
    "E_ID_FISCALI_DIVERSI": "Il parent account appartiene a un identificativo fiscale diverso.",
    "E_INDIRIZZO_CAMPO_ALTRA_FORMA": "Per questo indirizzo comune e CAP vengono dall'elenco: localita', codice postale e regione non si compilano.",
    "E_INDIRIZZO_CAP_ALTRO_COMUNE": "Il CAP scelto non e' del comune dell'indirizzo.",
    # brief-db-unicita-civico-indirizzi-dettaglio (2026-10-25): la chiave
    # dell'indirizzo fisico, il «trova o crea» e la modifica per tutti.
    "E_INDIRIZZO_CIVICO_NON_POSITIVO": "Il numero civico deve essere maggiore di zero. Per un indirizzo senza numero civico si lascia vuoto il campo.",
    "E_INDIRIZZO_COMUNE_ALTRO_STATO": "Il comune scelto non e' dello stato dell'indirizzo.",
    "E_INDIRIZZO_DETTAGLIO_DUPLICATO": "Esiste gia' un indirizzo uguale: la modifica ne creerebbe un doppione.",
    "E_INDIRIZZO_DETTAGLIO_NON_RILETTO": "L'indirizzo risulta gia' presente, ma non si riesce a rileggerlo. Riprovare l'operazione.",
    "E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE": "Estensione, palazzina, scala, piano e interno vogliono almeno una lettera o una cifra.",
    # brief-db-indirizzi-documento-seguono-il-cliente (2026-10-11): l'indirizzo
    # preso dall'anagrafica non e' del cliente del documento.
    "E_INDIRIZZO_DOC_NON_DEL_CLIENTE": "Un indirizzo del documento non e' del suo cliente: viene dall'anagrafica di un altro cliente, o di una fornitura diversa. Sceglilo fra quelli del cliente del documento.",
    "E_INDIRIZZO_DOC_OBBLIGATORIO": "Indirizzo obbligatorio mancante: impostare l'indirizzo di consegna prima dell'emissione.",
    "E_INDIRIZZO_FATTURA_MANCANTE": "Alcune fatture non hanno l'indirizzo di fatturazione: vedi i log delle fatture interessate.",
    "E_INDIRIZZO_LIBERO_INCOMPLETO": "Indirizzo incompleto: manca un campo della sua forma (via, stato, e poi comune e CAP oppure la localita').",
    "E_INDIRIZZO_OBBLIGATORIO_MANCANTE": "Indirizzo obbligatorio mancante per questo tipo soggetto.",
    "E_INDIRIZZO_SNAPSHOT_NOT_FOUND": "Indirizzo anagrafico non trovato: ricaricare gli indirizzi del cliente.",
    "E_INDIRIZZO_VIA_NON_RISOLTA": "La via scelta non e' completa nell'elenco delle vie: manca il comune, la provincia o il CAP.",
    "E_INVALID_ID": "ID non valido.",
    "E_INVITO_OPERATORE": "Operatore non invitabile.",
    "E_INVITO_PORTALE": "Invito portale non inviabile.",
    "E_ISTANZA_ALTRO_SOGGETTO": "L'istanza indicata e' di un altro soggetto: qui si puo' indicare solo una fornitura dello stesso soggetto.",
    "E_ISTANZA_EMITTENTI_DIVERSI": "I billing account di un'istanza sono tutti della stessa azienda emittente: questa operazione ne aggancerebbe uno a un'azienda diversa.",
    "E_ISTANZA_SENZA_BA": "Un'istanza nasce e vive insieme al suo billing account: non puo' restarne senza.",
    "E_ISTANZA_SOGGETTO_IMMUTABILE": "Una fornitura appartiene per sempre al suo soggetto: se e' sul soggetto sbagliato si annulla e si ricrea.",
    "E_ISTANZA_UTILITY_SENZA_UTILITY": "Istanza utility senza utility dichiarata: serve almeno un riferimento (billing account, dati precontrattuali, cliente).",
    "E_IVA_CONTO_ACQ_ERR": "Il conto indicato per l'IVA acquisti non e' un conto di tipo Acquisto.",
    "E_IVA_CONTO_VEN_ERR": "Il conto indicato per l'IVA vendite non e' un conto di tipo Vendita.",
    "E_IVA_PAESE_NON_IMPLEMENTATO": "Il trattamento IVA per il paese di questo emittente non e' ancora implementato.",
    "E_IVA_RESOLVE_NON_INVOCABILE": "Risoluzione IVA invocata con un parametro assente o non valido.",
    "E_IVA_TITOLI_AMBIGUI": "Su questa riga ricadono due o piu' titoli IVA del soggetto con la stessa specificita': il trattamento non e' determinabile. Restringere l'ambito di uno dei titoli, o chiuderne uno.",
    "E_IVA_TRATTAMENTO_IMMUTABILE": "Aliquota e natura di un codice IVA non si modificano: cambiarle riscriverebbe il trattamento dei documenti gia' emessi. Per un trattamento diverso si crea un codice nuovo.",
    # ⚠️ SENZA segnaposto: a catalogo il messaggio nomina il tipo di job e il
    # `run_as` chiesto. Qui la frase deve reggere anche a mani vuote.
    "E_JOB_DOMINIO_SENZA_OPERATORE": (
        "Lavoro di dominio accodato senza operatore: un lavoro che tocca i dati "
        "di un'azienda deve girare con l'identita' di chi lo ha chiesto."
    ),
    "E_JOB_ELEMENTI_NON_COMPLETATI": (
        "Il lavoro automatico e' finito, ma alcuni elementi non sono stati completati."
    ),
    "E_JOB_ESITO_CON_SCARTI": "Il lavoro è finito, ma una parte non è riuscita.",
    "E_JOB_NON_ANNULLABILE": "Il lavoro non e` piu` in attesa: annullo non possibile.",
    "E_JOB_NON_RIACCODABILE": "Il lavoro non e` riaccodabile nello stato corrente.",
    "E_JOB_NON_TROVATO": "Lavoro non trovato.",
    "E_JOB_RUN_SALTATA_NON_CHIUDIBILE": "La corsa e' stata saltata e non si puo' chiudere.",
    "E_JOB_TYPE_NON_ATTIVO": "Tipo di job non attivo.",
    "E_JOB_TYPE_NON_TROVATO": "Tipo di job non registrato nel registry.",
    "E_JWT_SENZA_IDENTITA": "Sessione scaduta: effettua nuovamente l'accesso.",
    "E_JWT_SENZA_SID": "La sessione in corso non e' identificabile: esci e rientra per continuare.",
    "E_KIT_QUANTITA_DISOMOGENEE": "Componenti dello stesso kit con quantita diverse: la fattura non e' rappresentabile.",
    "E_LISTINO_CON_STORIA_NON_SPEGNIBILE": "Il listino ha gia' avuto una versione attiva: non si spegne con l'interruttore. Si spegne mettendo la fine validita' alla sua versione.",
    "E_LISTINO_COMPONENTE_COERENZA_BOM": "Riga listino componenti incoerente con la distinta base.",
    "E_LISTINO_KIT_NON_COMPOSITO": "L'articolo non e' un kit: la periodicita' a parte sul listino si indica solo per un articolo composito. Indicarla sulla riga di listino dell'articolo.",
    "E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA": "Fuori dalla bozza una quota fissa non puo' restare senza periodicita': indicarne un'altra al posto di quella di oggi, o fare una versione nuova del listino.",
    "E_LISTINO_RIGA_COMPOSITO_VIETATO": "Articolo composito: il prezzo diretto non e' ammesso, usare i componenti.",
    "E_LISTINO_RIGA_COMP_BOM_INCOERENTE": "Prezzo bundle riferito a un componente non presente nella distinta base del padre composito.",
    "E_LISTINO_RIGA_IDENTITA_IMMUTABILE": "Una riga di listino non cambia articolo, unita' di misura o versione.",
    "E_LISTINO_TIPOLOGIA_UTILITY": "Combinazione utility / tipologia non ammessa per questo listino.",
    "E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE": "Fuori dalla bozza questo campo della versione di listino non si cambia: di una versione attiva si cambia solo la fine validita', di una chiusa niente.",
    "E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI": "La versione di listino e' chiusa: le sue date di validita' non si possono piu' modificare.",
    "E_LISTINO_VERSIONE_CITATA": "La versione di listino e' gia' usata da altri documenti: non si puo' eliminare. Toglierla dai documenti che la usano, oppure lasciarla in bozza.",
    "E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE": "La nuova versione non puo' cominciare prima della versione da cui si copia: scegliere una decorrenza uguale o successiva.",
    "E_LISTINO_VERSIONE_FINE_NEL_PASSATO": "La fine della versione di listino non puo' essere prima di oggi: scegliere oggi o una data futura.",
    "E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO": "La fine di una versione di listino attiva si cambia solo da «Chiudi» o dall'attivazione di una versione successiva.",
    "E_LISTINO_VERSIONE_NON_ATTIVA": "Listino senza versione attiva alla data del documento. Verificare le versioni del listino o la data di riferimento.",
    "E_LISTINO_VERSIONE_NON_CHIUDIBILE": "Si chiude solo una versione di listino attiva: di una bozza si modificano le date, una chiusa non cambia piu'.",
    "E_LISTINO_VERSIONE_NON_ELIMINABILE": "Si elimina solo una versione di listino in bozza: una versione attiva o chiusa e' stata usata per i prezzi.",
    "E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA": "La versione di listino ha una quota fissa senza periodicita': non si attiva. Indicare la periodicita' sulla riga dell'articolo (o del kit) e ripetere.",
    "E_LISTINO_VERSIONE_SENZA_RIGHE": "La versione di listino non ha prezzi: non si attiva. Aggiungere almeno una riga, o un composito col prezzo bundle.",
    "E_LISTINO_VERSIONE_SPENTA": "La versione di listino e' spenta: non si attiva. Riaccenderla, o attivarne un'altra.",
    "E_LOCK_COLUMNS": "Automazione delle colonne di lock fallita.",
    "E_LOGIN_ATTESA": "Troppi tentativi non riusciti: riprovare fra qualche secondo.",
    "E_LOGOUT_NO_TOKEN": "Token di refresh richiesto per il logout.",
    "E_LOOKUP_STRUTTURA_TABELLA_INVALIDA": "Configurazione lookup non valida: la tabella richiesta non e' compatibile col formato lookup standard. Contattare l'amministratore.",
    "E_LOTTO_COMPLETATO_NON_GUADAGNATO": "Il lotto non puo` risultare completato: ha documenti in errore o segnalazioni critiche aperte, oppure e` annullato. Sistema o togli dal giro i documenti in errore e rilancia il giro, che chiude il lotto da se`.",
    "E_LOTTO_DOC_GIA_USCITO": "Il documento e` gia` stato tolto da questo giro: ricarica il lotto per vedere l'elenco aggiornato.",
    "E_LOTTO_DOC_NON_IN_ERRORE": "Dal giro si tolgono solo i documenti che hanno fallito, e questo non e` in errore. Se non deve essere fatturato in questo giro: annulla il lotto e rigeneralo senza di lui.",
    "E_LOTTO_DOC_SENZA_ESITO": "Il documento non risulta lavorato da questo giro: l'elenco a video potrebbe essere invecchiato, oppure il documento appartiene a un altro lotto.",
    "E_LOTTO_DOC_USCITA_IRREVERSIBILE": "Un documento uscito da un giro non vi rientra. Per fatturare tutto in un lotto solo si annulla il lotto, si corregge il documento e si rigenera il giro.",
    "E_LOTTO_FATTURE_NON_PRE_FISCALI": "Il lotto contiene fatture oltre lo stato pre-fiscale: non possono essere eliminate.",
    "E_LOTTO_FATTURE_NUMERATE": "Il lotto contiene fatture gia` numerate: l'operazione aprirebbe un buco nella numerazione fiscale.",
    "E_LOTTO_FATTURE_STATO_INCOERENTE": "Fatture con stato fiscale diverso da quello del lotto.",
    "E_LOTTO_NON_ANNULLABILE": "Il lotto non e` in stato BOZZA: l'annullamento non e` applicabile. Da EMESSA la via d'uscita e` «Riporta in bozza».",
    "E_LOTTO_NON_NUMERABILE": "Il lotto non e` in stato EMESSA: numerazione non applicabile.",
    "E_LOTTO_NON_PRE_FISCALE": "Il lotto e` oltre lo stato pre-fiscale: non si possono piu` togliere fatture.",
    "E_LOTTO_NON_RIPORTABILE_A_DRAFT": "Il lotto e` oltre lo stato pre-fiscale: non puo` tornare in bozza.",
    "E_LOTTO_NON_RISTAMPABILE": "Il lotto non e` definitivo: la ristampa massiva richiede fatture numerate (Rendi definitive).",
    "E_LOTTO_NON_RIUTILIZZABILE": "Lotto non riutilizzabile.",
    "E_LOTTO_NON_TROVATO": "Lotto non trovato.",
    "E_LOTTO_PARAMETRO_NON_COERENTE": "Parametri lotto non coerenti.",
    # Magazzino — 29 codici, in ordine alfabetico. Due sono del Lotto 1
    # (brief-db-magazzino-lotto-1-terreno-vuoto §4.7, §4.9: i guard del terreno
    # vuoto, `MOVIMENTO_VERSO_INCOERENTE` e `TRASFERIMENTO_EMITTENTI_DIVERSI`),
    # ventisette del Lotto 2 (brief-db-magazzino-lotto-2-motore §4.10, id
    # 1075-1101: la primitiva `fn_scrivi_movimento`, le due check condivise, i
    # documenti interni). A catalogo portano codici di articolo, magazzino,
    # lotto e seriale, quantita' e stati: qui la frase senza. La forma segue
    # la classe — sui TECNICO chiude con «segnalare al supporto» (il lettore e'
    # chi sviluppa), sui DATO_ERRATO nomina il campo da correggere, sui
    # CONFLITTO_STATO dice di rileggere lo stato.
    "E_MAG_ARTICOLO_NON_GESTITO": (
        "L'articolo non e' gestito a magazzino, oppure non e' attivo: nessun "
        "movimento si puo' registrare. Attivare «gestito a magazzino» nella "
        "sua scheda, oppure togliere la riga dal documento."
    ),
    "E_MAG_ASSET_DI_ALTRO_ARTICOLO": (
        "Il seriale indicato non e' dell'articolo della riga, oppure non e' "
        "piu' attivo: scegliere un seriale attivo dell'articolo, o correggere "
        "l'articolo."
    ),
    "E_MAG_ASSET_DI_ALTRO_EMITTENTE": (
        "Il seriale indicato non appartiene all'emittente del magazzino: "
        "scegliere un seriale dell'emittente del magazzino, oppure un "
        "magazzino dello stesso emittente del seriale."
    ),
    "E_MAG_ASSET_POSIZIONE_INCOERENTE": (
        "Il seriale non puo' fare questo movimento: a registro risulta gia' "
        "dentro un magazzino (non puo' entrare di nuovo) oppure non risulta "
        "in questo (non puo' uscirne). Verificare dove si trova nel registro "
        "dei movimenti e registrare prima il movimento mancante."
    ),
    "E_MAGAZZINO_VALIDATION": "Richiesta di magazzino non valida.",
    "E_MAG_BLOCCO_GIA_CHIUSO": "Il blocco e' gia' stato liberato.",
    "E_MAG_BLOCCO_NON_TROVATO": "Blocco non trovato.",
    "E_MAG_CHIAMATA_NON_VALIDA": (
        "Chiamata non valida a una funzione di magazzino: un valore che "
        "nessuna interfaccia produce. Non c'e' niente da correggere a video: "
        "segnalare al supporto citando il request_id."
    ),
    "E_MAG_COSTO_NON_AMMESSO": (
        "Costo unitario non ammesso su questo movimento: lo decide il "
        "registro (uno storno va al costo dell'originale, l'entrata di un "
        "trasferimento al costo dell'uscita gemella, ogni uscita alla media "
        "corrente). Segnalare al supporto citando il request_id."
    ),
    "E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE": (
        "Il magazzino di un inventario o di una rettifica non si cambia: il "
        "documento nasce dentro il suo magazzino. Se il magazzino e' "
        "sbagliato, annullare il documento e aprirne uno nuovo in quello "
        "giusto."
    ),
    "E_MAG_DOCUMENTO_NON_ELIMINABILE": (
        "Il documento non si puo' eliminare: solo una bozza si elimina. Per "
        "chiudere un documento confermato, annullarlo; un documento "
        "registrato si corregge con una rettifica. Rileggere lo stato."
    ),
    "E_MAG_DOCUMENTO_NON_TROVATO": (
        "Documento di magazzino non trovato: non esiste, oppure non e' "
        "accessibile con i permessi di chi sta operando. Verificare "
        "l'identificativo e l'emittente selezionato."
    ),
    "E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE": (
        "Il documento non si porta a registrato con un aggiornamento diretto "
        "dello stato: ci passa solo l'operazione di registrazione, che scrive "
        "i movimenti. Segnalare al supporto citando il request_id."
    ),
    "E_MAG_DOCUMENTO_RIGA_NON_TROVATA": (
        "La riga non fa parte di questo documento: non esiste, oppure e' di "
        "un altro documento. Riaprire il documento per vedere le righe che "
        "ci sono adesso."
    ),
    "E_MAG_DOCUMENTO_RIGHE_CONGELATE": (
        "Le righe del documento non si modificano piu': si scrivono solo in "
        "bozza. Per correggere un documento confermato riportarlo in bozza o "
        "annullarlo e rifarlo; uno registrato si corregge con una rettifica. "
        "Rileggere lo stato."
    ),
    "E_MAG_DOCUMENTO_SENZA_RIGHE": (
        "Il documento non ha righe: niente da registrare. Aggiungere le "
        "righe (riportandolo in bozza, se serve) e ripetere, oppure "
        "annullarlo."
    ),
    "E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA": (
        "Il passaggio di stato richiesto non e' ammesso dallo stato in cui il "
        "documento si trova: la registrazione parte da un documento "
        "confermato, una bozza va prima confermata, un documento registrato o "
        "annullato non cambia piu'. Rileggere lo stato."
    ),
    "E_MAG_GEMELLA_NON_TROVATA": (
        "L'entrata di un trasferimento non trova l'uscita gemella da cui "
        "ereditare il costo: ordine delle due scritture invertito, oppure "
        "identificativo sbagliato. Segnalare al supporto citando il "
        "request_id."
    ),
    "E_MAG_GIACENZA_INSUFFICIENTE": (
        "Giacenza insufficiente: la quantita' in uscita e' maggiore di quella "
        "che il registro da' come presente per l'articolo (o per il lotto o "
        "il seriale indicati). Ridurre la quantita', scegliere un altro lotto "
        "o magazzino, oppure registrare prima il carico mancante."
    ),
    "E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA": (
        "L'articolo e' gia' contato in questa posizione dell'inventario: due "
        "letture della stessa posizione non sono due fatti. Modificare la riga "
        "che c'e' gia'; se la merce e' davvero diversa, e' la posizione a "
        "essere diversa (ubicazione, lotto o seriale)."
    ),
    "E_MAG_LOTTO_DI_ALTRO_ARTICOLO": (
        "Il lotto indicato non e' dell'articolo della riga, oppure non e' "
        "piu' attivo: scegliere un lotto attivo dell'articolo, o correggere "
        "l'articolo."
    ),
    "E_MAG_LOTTO_NON_AMMESSO": (
        "L'articolo non si movimenta per lotti: il lotto sulla riga non va "
        "indicato. Toglierlo, oppure attivare «per lotti» nella scheda "
        "dell'articolo prima di registrare."
    ),
    "E_MAG_LOTTO_NON_TROVATO": (
        "Lotto non trovato: non esiste. Verificare l'identificativo del lotto."
    ),
    "E_MAG_LOTTO_OBBLIGATORIO": (
        "L'articolo si movimenta per lotti: indicare il lotto sulla riga "
        "(crearlo prima, se e' nuovo)."
    ),
    "E_MAG_MAGAZZINO_CON_GIACENZA": (
        "Il magazzino ha gia' movimenti a registro: l'uso delle ubicazioni "
        "si decide prima del primo carico e non si cambia piu'. Se serve un "
        "magazzino organizzato diversamente, crearne uno nuovo e trasferirci "
        "la merce."
    ),
    "E_MAG_MAGAZZINO_NON_TROVATO": (
        "Magazzino non trovato: non esiste, oppure non e' accessibile con i "
        "permessi di chi sta operando. Verificare l'identificativo del "
        "magazzino e l'emittente selezionato."
    ),
    "E_MAG_MAGAZZINO_NON_VALIDO": (
        "Magazzino inesistente o non attivo: le operazioni lo leggono dalla "
        "testata del documento, quindi un valore che non risolve e' un "
        "difetto del programma. Segnalare al supporto citando il request_id."
    ),
    "E_MAG_MERCE_BLOCCATA": (
        "La merce c'e', ma una parte e' gia' promessa ad altri: la quantita' "
        "libera non copre l'uscita richiesta. Ridurre la quantita' alla parte "
        "disponibile, oppure attendere che il blocco venga chiuso."
    ),
    "E_MAG_MOVIMENTO_GIA_REGISTRATO": (
        "Questa operazione ha gia' registrato il movimento: rilancio o doppio "
        "click. Non c'e' niente da ripetere, aggiornare la vista per vederlo."
    ),
    "E_MAG_MOVIMENTO_VERSO_INCOERENTE": (
        "Movimento di magazzino con verso incoerente: la quantita' non ha il "
        "segno della causale (entrata positiva, uscita negativa) oppure vale "
        "zero. Non e' un dato da correggere nel form: segnalare al supporto."
    ),
    "E_MAG_SERIALE_NON_AMMESSO": (
        "L'articolo non si movimenta per seriale: il seriale sulla riga non "
        "va indicato. Toglierlo, oppure attivare «per seriale» nella scheda "
        "dell'articolo prima di registrare."
    ),
    "E_MAG_SERIALE_OBBLIGATORIO": (
        "L'articolo si movimenta per seriale: indicare il seriale sulla riga "
        "(registrare prima l'asset, se e' nuovo), con quantita' 1."
    ),
    "E_MAG_STORNO_INCOERENTE": (
        "Storno incoerente col movimento originale: articolo o magazzino "
        "diversi, quantita' non opposta, causale non di storno, sorgente "
        "diversa, oppure originale inesistente. Segnalare al supporto "
        "citando il request_id."
    ),
    "E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI": (
        "Il magazzino di destinazione non appartiene allo stesso emittente "
        "fiscale del magazzino di origine, oppure non e' visibile nel tuo "
        "perimetro: un trasferimento sposta merce solo fra magazzini dello "
        "stesso emittente."
    ),
    "E_MAG_TRASFERIMENTO_STESSA_POSIZIONE": "In un trasferimento dentro lo stesso magazzino partenza e arrivo coincidono: servono due ubicazioni diverse.",
    "E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO": (
        "L'ubicazione indicata non e' del magazzino del documento, oppure "
        "non e' piu' attiva: scegliere un'ubicazione attiva di quel "
        "magazzino."
    ),
    "E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE": (
        "Il magazzino di un'ubicazione non si cambia: l'ubicazione nasce "
        "dentro il suo magazzino. Disattivarla e crearne una nel magazzino "
        "giusto."
    ),
    "E_MAG_UBICAZIONE_NON_AMMESSA": (
        "Il magazzino non usa le ubicazioni: l'ubicazione sulla riga non va "
        "indicata. Toglierla; l'uso delle ubicazioni si decide nella scheda "
        "del magazzino prima del primo movimento."
    ),
    "E_MAG_UBICAZIONE_NON_TROVATA": (
        "Ubicazione non trovata: non esiste, non e' del magazzino indicato, "
        "oppure il magazzino non e' accessibile con i permessi di chi sta "
        "operando. Verificare ubicazione, magazzino ed emittente selezionato."
    ),
    "E_MAG_UBICAZIONE_OBBLIGATORIA": (
        "Il magazzino usa le ubicazioni: indicare sulla riga in quale "
        "ubicazione (un'ubicazione attiva di quel magazzino)."
    ),
    "E_MAG_UBICAZIONE_PADRE_CICLICO": (
        "L'ubicazione non puo' avere quel padre: sarebbe un ciclo nella "
        "gerarchia (il padre e' l'ubicazione stessa o una sua discendente). "
        "Scegliere un padre che non stia sotto questa, o lasciarlo vuoto."
    ),
    "E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO": (
        "L'ubicazione padre non appartiene a questo magazzino, oppure non e' "
        "visibile con i permessi di chi sta operando: scegliere un padre "
        "dello stesso magazzino, o lasciarlo vuoto."
    ),
    # ⭐ `E_MESSAGGIO_NON_DEFINITO` — RINOMINATO dal team DB il 2026-08-07 (era
    # `MESSAGGIO_NON_DEFINITO`, senza prefisso). E' l'ULTIMA riga del registro dei
    # codici fuori convenzione `dbops.messaggi_errore_codici_legacy`, che con
    # questa va a zero e si droppa.
    #
    # ⚠️ La rinomina e' arrivata poche ore dopo la prima generazione, e i due
    # presidi l'hanno vista lo stesso giorno: il controllo di divergenza ha
    # mostrato il diff, il cancello del terzo lato ha detto che
    # `script.fn_log_error_only` nominava un codice senza policy. Il rimedio e'
    # stato **rigenerare** — cioe' esattamente il flusso per cui sono stati
    # costruiti. Qui resta la sola riga a mano: il messaggio.
    "E_MERGE_FIGLIA_SOTTO_RLS": "La fusione non puo' ripuntare una tabella di cui chi la lancia vede solo una parte.",
    "E_MERGE_ORIGINE_UGUALE_DESTINAZIONE": "Origine e destinazione della fusione coincidono: devono essere due righe diverse.",
    "E_MERGE_RIGHE_DOPPIE": "La fusione si ferma: alcune righe diventerebbero doppie di righe che la destinazione ha gia'.",
    "E_MESSAGGIO_NON_DEFINITO": "Messaggio di errore non definito a catalogo.",
    # ⚠️ Tolto il 2026-08-07 con la prima generazione (B-5):
    # `E_W_TXID_NOT_REGISTERED` era il gemello col prefisso `E_` di un codice che
    # a catalogo sta SENZA. Era irraggiungibile: il codice arriva dal campo
    # strutturato `CONSTRAINT`, che porta il nome esatto del catalogo, e il
    # ripiego a regex sul testo cerca `\bE_[A-Z]...` — quindi il nome senza
    # prefisso da li' non passa comunque, e quello CON prefisso non lo scrive
    # nessuno.
    #
    # ⛔ E `W_TXID_NOT_REGISTERED` NON VA RINOMINATO IN `E_W_...` (ne' in `E_`).
    # La `W` e' un'altra FAMIGLIA, non un prefisso sbagliato: quel codice si
    # scrive nel diario (`fn_log_error_only`) e non si solleva mai. La regola di
    # naming e' `^[EW]_` proprio per questo, e il cantiere precedente aveva gia'
    # rifiutato la rinomina una volta.
    # ⚠️ La rinomina di `MESSAGGIO_NON_DEFINITO` qui sopra NON e' un precedente:
    # quello era un `E_` a cui mancava il prefisso, questo e' un `W_` a cui il
    # prefisso spetta.
    #
    # ⛔ E `W_TXID_NOT_REGISTERED` NON VA RINOMINATO IN `E_W_...` (ne' in `E_`).
    # La `W` e' un'altra FAMIGLIA, non un prefisso sbagliato: quel codice si
    # scrive nel diario (`fn_log_error_only`) e non si solleva mai. La regola di
    # naming e' `^[EW]_` proprio per questo, e il cantiere precedente aveva gia'
    # rifiutato la rinomina una volta.
    "E_MOVIMENTO_RIFERIMENTO_INCOERENTE": "Il movimento non e' coerente con la riga contabile a cui fa riferimento.",
    "E_NAZIONE_NON_TROVATA": "Nazione non indicata e nessun default configurato.",
    "E_NOTA_CHECK_VIOLATION": "Valore non ammesso per anchor_tipo, posizione, seq o testo.",
    "E_NOTA_DUPLICATO": "Nota gia' esistente (violato vincolo di univocita').",
    "E_NOTA_FK": "Riferimento non valido: stile, lingua o riga non esistenti.",
    "E_NOTA_INSERT": "Errore durante l'inserimento della nota.",
    "E_NOTA_NOT_FOUND": "Nota non trovata.",
    "E_NOTA_PARENT_NOT_FOUND": "Documento di riferimento non trovato.",
    "E_NOTA_RIGA_INCOERENTE": "La riga indicata non appartiene al documento.",
    "E_NOTA_VALIDATION": "Dati nota non validi.",
    "E_NOTE_CONFIG": "Configurazione del trigger note errata: tabella inesistente.",
    "E_NOTE_RIGA_MISMATCH": "La riga indicata non appartiene al documento della nota.",
    "E_NOTE_TARGET_ID": "Riga di destinazione mancante per una nota ancorata alla riga.",
    "E_NOT_AUTHENTICATED": "Non autenticato.",
    "E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI": "L'offerta ha generato un contratto o un ordine non annullato: per annullarla, annullare prima quel documento.",
    "E_OFFERTA_CONTRATTO_GIA_GENERATO": "Questa offerta ha già generato un contratto.",
    "E_OFFERTA_ECCEZIONE_NON_TROVATA": "Eccezione offerta non trovata.",
    "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO": "Impossibile emettere l'offerta: il listino di riferimento non ha una versione in vigore oggi.",
    "E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA": "Impossibile emettere: la versione di listino non è attiva.",
    "E_OFFERTA_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente selezionato.",
    "E_OFFERTA_MOTIVAZIONE_NON_AMMESSA": "Per questo passaggio dell'offerta non si indica una motivazione: si indica solo per rifiutarla o annullarla.",
    "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA": "Per rifiutare o annullare l'offerta serve una motivazione.",
    "E_OFFERTA_NON_TROVATA": "Offerta non trovata.",
    "E_OFFERTA_ORDINE_GIA_GENERATO": "Questa offerta ha già generato un ordine.",
    "E_OFFERTA_PUSH_STATO_NON_AMMESSO": "Push a contratto non ammesso: l'offerta deve essere ACCETTATA.",
    "E_OFFERTA_REVISIONE_CATENA_IMMUTABILE": "La catena delle revisioni di un'offerta non si cambia: ogni revisione resta legata all'offerta da cui e' nata.",
    "E_OFFERTA_REVISIONE_PADRE_NON_TROVATO": "L'offerta da cui dovrebbe nascere la revisione non esiste o non e' visibile: la revisione non si puo' creare.",
    "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO": "Revisione non ammessa nello stato corrente dell'offerta.",
    "E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA": "L'offerta non può uscire dal superamento: esiste ancora una revisione viva su questo documento. Va prima annullata quella.",
    "E_OFFERTA_TRANSIZIONE_NON_AMMESSA": "Transizione di stato non ammessa per l'offerta.",
    "E_ONERE_ARTICOLO_MANCANTE": "Articolo-onere non valido: inesistente, non attivo o senza causale associata.",
    "E_ONERE_CAUSALE_NON_VALIDA": "Causale onere non valida o non attiva.",
    "E_ONERE_IMPORTO_NON_VALIDO": "Importo onere non valido: deve essere maggiore di zero.",
    "E_ONERE_SEGMENT_DUPLICATO": "Onere non creato per una modifica concorrente. Riprovare.",
    "E_OPERATORE_SCOPE_MULTI_NON_AMMESSO": "Scope operatore multiplo non ammesso: un operatore ha un solo emittente.",
    "E_OPERATORE_SCOPE_PARAM_NON_VALIDO": "Parametri scope operatore non validi.",
    "E_ORDINE_CONFERMA_SENZA_RIGHE": "Ordine senza righe: impossibile confermare.",
    "E_ORDINE_CONFERMA_SOLO_ONERI": "L'ordine ha solo oneri e nessuna merce: non si puo' confermare.",
    "E_ORDINE_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente selezionato.",
    "E_ORDINE_EMITTENTE_NON_RISOLTO": "Nessun emittente fiscale attivo: selezionalo in alto o indicalo nella richiesta.",
    "E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA": "La merce di questa riga e' gia' partita con un DDT: la data di consegna confermata non si cambia piu'.",
    "E_ORDINE_RIGA_IVA_MANCANTE": "Una riga dell'ordine ha un prezzo ma nessuna aliquota IVA: sceglila, oppure togli il prezzo se la merce non si valorizza.",
    "E_ORDINE_RIGA_NON_TROVATA": "Riga ordine non trovata.",
    "E_ORDINE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato dell'ordine non ammessa dallo stato attuale.",
    "E_ORD_ANNULLA_CON_DDT": "L'ordine ha gia' DDT collegati: la merce e' uscita, per riportarla dentro si registra un reso.",
    "E_ORD_ANNULLA_IN_COMMESSA": "L'ordine e' gia' stato inviato a fatturazione: annulla prima le attivita' in commessa.",
    "E_ORD_CLIENTE_IMMUTABILE": "Cliente immutabile dopo la creazione: per cambiare cliente crea un nuovo ordine.",
    "E_ORD_FUL_ONERE_NON_INTERO": "Un onere passa intero nella prima bolla: non si evade a pezzi. Per addebitarne una parte, correggerlo sull'ordine.",
    "E_ORD_NESSUNA_RIGA": "L'ordine non ha righe eleggibili per l'operazione.",
    "E_ORD_NOT_FOUND": "Ordine non trovato.",
    "E_ORD_OFFERTA_GIA_CONVERTITA": "Un ordine è già stato generato da questa offerta.",
    "E_ORD_ORIGINE_NON_CONVERTIBILE": "Il documento di origine non è in uno stato che consente di generare un ordine.",
    "E_ORD_STATO_TRANSIZIONE": "Operazione non ammessa nello stato corrente dell'ordine.",
    "E_ORD_VALIDAZIONE": "Parametri ordine non validi.",
    "E_OUTBOX": "Errore gestione bozza email.",
    "E_PADRE_INESISTENTE": "La riga a cui si collega non esiste.",
    "E_PAGAMENTI_CHIAMATA_NON_VALIDA": "Chiamata non valida al modulo pagamenti: e' un difetto del programma, non un dato da correggere.",
    "E_PAGAMENTI_VALIDATION": "Parametri non validi.",
    "E_PANNELLO_CAMPO_NON_AMMESSO": "Un campo non si puo' salvare da qui.",
    "E_PANNELLO_DATI_VUOTI": "Non c'e' nessun campo da salvare.",
    "E_PANNELLO_RIGA_NON_TROVATA": "La riga non esiste piu'.",
    "E_PANNELLO_TABELLA_NON_AMMESSA": "Tabella non gestita dal pannello di configurazione.",
    "E_PARAMETER_DEFAULT_VALUE_INVALID": "Valore di default parametro non valido: deve esistere nella tabella di catalogo associata.",
    "E_PARAMETER_NOT_FOUND": "Parametro di sistema non trovato.",
    "E_PARAMETER_OVERRIDE_NON_AMMESSO": "Questo parametro vale per tutti e non si personalizza: lo stabilisce la configurazione del sistema, per cambiarlo ci si rivolge all'amministratore.",
    "E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO": "Il parametro ha una personalizzazione che non va bene per la forma nuova del valore: correggerla o toglierla prima di cambiare il tipo.",
    "E_PARAMETER_OVERRIDE_PRESENTI": "Il parametro ha ancora personalizzazioni: non puo' diventare uguale per tutti.",
    "E_PARAMETER_OVERRIDE_VALUE_INVALID": "Override parametro non valido: il valore deve esistere nella tabella di catalogo associata.",
    "E_PARAMETER_VALIDATION": "Valore parametro non valido.",
    "E_PARAMETER_VALORE_NON_CONFORME": "Il valore del parametro non ha la forma richiesta (un numero intero, un si'/no, una data...).",
    "E_PARAMETRI_TABELLA": "Il valore indicato non corrisponde a nessun record.",
    "E_PARAMETRO_INVALIDO": "Parametro obbligatorio mancante o non valido.",
    "E_PARENT_NON_RAGGIUNGIBILE": "Il parent account indicato non e' utilizzabile: non esiste, oppure non rientra nel tuo perimetro.",
    "E_PARENT_SELF": "Il parent account non puo' essere il record stesso.",
    "E_PARENT_SOGGETTO_DIVERSO": "Il parent account appartiene a un soggetto diverso e manca il codice fiscale per verificarlo.",
    "E_PDP_OBBLIGATORIO": "Piano dati precontrattuali obbligatorio.",
    "E_PDP_UTILITY_MISMATCH": "Utility non coerente con il piano dati precontrattuali.",
    "E_PERMESSO_NEGATO": "Non hai i permessi per questa operazione.",
    "E_PERMISSION_DENIED": "Permesso negato.",
    "E_PIPELINE": "Errore nella pipeline di fatturazione.",
    "E_PIPELINE_DOMINIO": "Errore dominio pipeline.",
    "E_PIPELINE_DOMINIO_NOT_FOUND": "Dominio pipeline non trovato.",
    "E_PIPELINE_DRIVER_MAX_ITER": "Pipeline interrotta: superato il numero massimo di iterazioni.",
    "E_PIPELINE_LOTTO_CRITICAL": "Lotto bloccato per segnalazioni critiche o documenti in errore.",
    "E_PIPELINE_LOTTO_IN_ESECUZIONE": "Lotto gia' in esecuzione.",
    "E_PIPELINE_LOTTO_NOT_FOUND": "Lotto non trovato.",
    "E_PIPELINE_MARK_ERROR": "Errore marcatura pipeline.",
    "E_PIPELINE_NOT_FOUND": "Configurazione pipeline non trovata.",
    "E_PIPELINE_SCOPE_INCOMPLETE": "Scope pipeline incompleto.",
    "E_PIPELINE_STATO_LOTTO": "Stato lotto non compatibile con l'operazione.",
    "E_PIPELINE_TASK": "Errore task pipeline.",
    "E_PIPELINE_TASK_HANDLER_NOT_FOUND": "Handler task non trovato.",
    "E_PIPELINE_VALIDATION": "Parametri pipeline non validi.",
    "E_PIVA_NON_VALIDA": "Partita IVA non valida.",
    "E_PIVA_OBBLIGATORIA": "Partita IVA obbligatoria.",
    "E_PRATICA_ID_INVALIDO": "Pratica non valida.",
    "E_PRATICA_ID_OBBLIGATORIO": "Pratica obbligatoria.",
    "E_PRATICA_INSERT": "Errore durante l'inserimento della pratica.",
    "E_PRATICA_NOT_FOUND": "Pratica non trovata.",
    "E_PRATICA_QUERY": "Errore durante la lettura delle pratiche.",
    "E_PRATICA_SORGENTE_TIPO_INVALIDO": "Codice sorgente non presente in configurazione.",
    "E_PRATICA_VALIDATION": "Parametri pratica non validi.",
    "E_PRATICHE_BA_NON_COERENTE": "Il billing account non appartiene al ruolo della pratica.",
    "E_PRATICHE_CHIUSURA_FLUSSI_APERTI": "Impossibile chiudere la pratica: ci sono flussi ancora aperti. Completali o annullali, poi riprova.",
    "E_PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI": "Impossibile chiudere la pratica: flussi obbligatori non completati.",
    "E_PRATICHE_CHIUSURA_FLUSSO_PREMATURO": "Impossibile completare il flusso di chiusura: restano altri flussi obbligatori da completare.",
    "E_PRATICHE_FLUSSO_NON_RIPETIBILE": "Il flusso non e' ripetibile in questa pratica.",
    "E_PRATICHE_ISTANZA_NON_COERENTE": "L'istanza non appartiene al soggetto indicato.",
    "E_PRATICHE_ISTANZA_SENZA_SOGGETTO": "L'istanza utility richiede anche il soggetto.",
    "E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI": "Indicare una sola lente di contesto: ruolo soggetto, istanza utility o solo interne.",
    "E_PRATICHE_PIN_IMMUTABILE": "L'edizione di workflow pinnata dalla pratica e' immutabile.",
    "E_PRATICHE_PREREQUISITI_NON_SODDISFATTI": "Flusso non ancora eseguibile: prerequisiti non soddisfatti.",
    "E_PRATICHE_RUOLO_NON_COERENTE": "Il ruolo non appartiene al soggetto indicato.",
    "E_PRATICHE_RUOLO_SENZA_SOGGETTO": "Il ruolo richiede anche il soggetto.",
    "E_PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE": "Aggancio sorgente incoerente: il flusso appartiene a un'altra pratica.",
    "E_PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE": "Impossibile modificare il flusso: la pratica e' in stato terminale.",
    "E_PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO": "Impossibile creare un flusso: la pratica e' in stato terminale.",
    "E_PRATICHE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato pratica non ammessa.",
    # ⚠️ Il messaggio a catalogo NOMINA la vista con un `%s`: qui la frase deve
    #    reggere senza, perche' il ripiego serve proprio quando gli argomenti
    #    non sono arrivati — e un `%s` a video sarebbe la cosa peggiore da
    #    mostrare in un caso gia' tecnico.
    "E_PRESIDIO_NON_A_CATALOGO": "Vista di presidio non dichiarata nel catalogo dbops.presidi, oppure spenta o ritirata. Non e' un errore di dati: segnalalo a chi mantiene il catalogo.",
    "E_PREVENTIVO_RIGA_NON_TROVATA": "Riga preventivo non trovata.",
    "E_PREV_ANNULLA_COMMESSA_EMESSA": "Righe del preventivo gia' fatturate in commessa: l'annullamento non e' ammesso. Storna le attivita' emesse dal lato fatturazione, oppure crea una revisione del preventivo.",
    "E_PREV_COMPONENTE_NOT_FOUND": "Componente preventivo non trovato.",
    "E_PREV_EMISSIONE_VALIDITA_SCADUTA": "La validita' del preventivo e' gia' finita: scrivi in «Valido al» una data da oggi in poi, poi emettilo.",
    "E_PREV_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente selezionato.",
    "E_PREV_EMITTENTE_NON_RISOLTO": "Operatore senza emittente fiscale assegnato: specificare l'emittente esplicitamente nel payload.",
    "E_PREV_GIA_IN_COMMESSA": "Preventivo gia' inviato a fatturazione.",
    "E_PREV_NESSUNA_RIGA": "Nessuna riga attiva nel preventivo.",
    "E_PREV_NESSUNA_RIGA_ATTIVA": "Preventivo senza righe attive: serve almeno una riga per emettere.",
    "E_PREV_NOT_FOUND": "Preventivo non trovato.",
    "E_PREV_ORDINE_GIA_GENERATO": "Il preventivo ha gia' generato un ordine: annulla prima l'ordine collegato.",
    "E_PREV_PRATICA_STATO": "Stato preventivo non ammette generazione pratica.",
    "E_PREV_REVISIONE_ATTIVA": "Esiste gia' una revisione attiva per questo preventivo.",
    "E_PREV_REVISIONE_BOZZA_ESISTENTE": "Esiste gia' una revisione in BOZZA per questo preventivo. Completa o annulla la BOZZA esistente prima di crearne una nuova.",
    "E_PREV_REVISIONE_STATO_NON_AMMESSO": "Revisione ammessa solo da un preventivo emesso o scaduto.",
    "E_PREV_RIGA_IVA_MANCANTE": "Una riga del preventivo ha un prezzo ma nessuna aliquota IVA: sceglila, oppure togli il prezzo se la merce non si valorizza.",
    "E_PREV_RIGA_NATURA_IMMUTABILE": "La natura di vendita della riga non e' modificabile: e' ereditata dall'articolo.",
    "E_PREV_RIGA_NOT_FOUND": "Riga preventivo non trovata.",
    "E_PREV_STATO_CORRENTE_NON_TROVATO": "Stato corrente del preventivo non trovato.",
    "E_PREV_STATO_NON_MODIFICABILE": "Preventivo non modificabile nello stato corrente.",
    "E_PREV_STATO_TRANSIZIONE": "Transizione di stato preventivo non ammessa.",
    "E_PREV_TRANSIZIONE_NON_AMMESSA": "Transizione non ammessa dallo stato corrente del preventivo: ricarica il documento e usa una delle azioni proposte.",
    "E_PREV_UTILITY_ISTANZA_INCOERENTE": "Utility non coerente con l'istanza selezionata.",
    "E_PREV_VALIDAZIONE": "Parametri preventivo non validi.",
    "E_PREV_VALIDITA_SCADUTA": "La validita' del preventivo e' finita: non si puo' piu' accettare. Crea una revisione con una nuova data di validita'.",
    "E_PREZZO_LISTINO_AMBIGUO": "Piu' prezzi trovati per lo stesso articolo/listino.",
    "E_PREZZO_LISTINO_NON_TROVATO": "Nessun prezzo listino risolto per l'articolo richiesto.",
    "E_PREZZO_LISTINO_RIGA_NON_TROVATA": "Riga listino non trovata per articolo/uom alla data.",
    "E_PREZZO_LISTINO_VERSIONE_BOZZA": "La versione del listino e' ancora in bozza: i suoi prezzi non si usano finche' non e' attiva.",
    "E_PRICING_MAGGIORAZIONE_ECCESSIVA": "Variazione prezzo oltre il limite consentito per il tuo ruolo. Richiedi approvazione o rientra nel limite ammesso.",
    "E_PRICING_OVERRIDE_NON_AUTORIZZATO": "Modifica manuale del prezzo non autorizzata. Usa il prezzo suggerito dal listino o richiedi l'autorizzazione al responsabile.",
    "E_PRICING_SCONTO_ECCESSIVO": "Variazione prezzo oltre il limite consentito per il tuo ruolo. Richiedi approvazione o rientra nel limite ammesso.",
    # «Esegui ora» su una sveglia (brief-db-avvio-manuale-di-un-processo §9):
    # i tre motivi del predicato e i due esiti dell'handler. A catalogo portano
    # unit, id del lavoro, secondi ed exit code: qui la frase senza.
    "E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO": "Per accendere o spegnere a mano un processo automatico serve un motivo.",
    "E_PROCESSO_AVVIO_FALLITO": (
        "Il comando della sveglia e' uscito con un errore: il dettaglio e' nel "
        "giornale del processo eseguito."
    ),
    "E_PROCESSO_AVVIO_GIA_IN_CODA": (
        "Un avvio di questa sveglia e' gia' in coda: attendi che finisca prima "
        "di chiederne un altro."
    ),
    "E_PROCESSO_AVVIO_TROPPO_LUNGO": (
        "Il comando della sveglia non e' finito entro il tempo massimo: e' troppo "
        "lungo per «Esegui ora» ed e' stato interrotto."
    ),
    "E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE": (
        "Questo processo automatico non si puo' accendere a mano in un'installazione di produzione."
    ),
    "E_PROCESSO_NON_ELEGGIBILE_UTENTE_TECNICO": (
        "Questo processo non puo' avere un utente tecnico: ne serve uno solo ai "
        "processi che fanno il lavoro di un'azienda senza che nessuno li avvii."
    ),
    "E_PROCESSO_NON_SPEGNIBILE": "Questo processo automatico non si puo' spegnere.",
    "E_PROCESSO_NON_TROVATO": (
        "Il processo indicato non esiste nel registro dei processi automatici."
    ),
    "E_PROCESSO_SENZA_SVEGLIA": "Questo processo automatico non ha una sveglia da accendere o spegnere.",
    "E_PROCESSO_SVEGLIA_NON_ABILITATA": (
        "Il processo e' spento su questa installazione: il comando non parte "
        "ne' dalla sveglia ne' a mano. Riaccendilo prima di eseguirlo."
    ),
    "E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO": (
        "La sveglia non e' avviabile a mano: e' un servizio sempre acceso oppure "
        "un comando dichiarato non candidato a «Esegui ora»."
    ),
    "E_PROFILO_ACCESSO_BINDING_INCOERENTE": "Binding non coerente con il tipo del profilo di accesso.",
    "E_PROFILO_ACCESSO_NON_TROVATO": "Profilo di accesso non trovato.",
    "E_PROFILO_ACCESSO_TIPO_NON_GESTITO": "Tipo profilo non gestito dal guard di coerenza bindings: regola mancante.",
    "E_PROFILO_ULTIMO_SUPER_ADMIN": "Operazione vietata: non resterebbe nessun amministratore (SUPER_ADMIN) attivo e senza data di fine.",
    "E_PROMO_ARTICOLO_SOLO_COMPONENTE": "L'articolo si vende solo dentro un kit: una promo su di lui non si applicherebbe mai. Mettere la promo sul kit.",
    "E_PROMO_INIZIATA_CAMPI_RISTRETTI": "Promo gia' iniziata: solo descrizione e data fine sono modificabili. Per cambiare prezzo o periodo, chiudere questa promo (data fine = oggi) e crearne una nuova.",
    "E_PROMO_RETROATTIVA": "Le date della promo non possono essere retroattive: valido_dal deve essere successivo a oggi e valido_al non puo' essere antecedente a oggi.",
    "E_PROMO_SCADUTA_IMMUTABILE": "Promo scaduta: non modificabile. Per riproporla creare una nuova promo.",
    "E_PROVINCIA_SIGLA_NON_VALIDA": "La sigla della provincia non e' valida: per una provincia italiana due lettere maiuscole, per le altre lettere maiuscole e cifre, al massimo dieci.",
    "E_PULL_COMMESSA": "Errore pull commessa.",
    "E_PULL_COMMESSA_ALL_FAILED": "Tutti i pull commessa falliti.",
    "E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO": "Il filtro righe vale solo sul push di un singolo preventivo.",
    "E_PUSH_SORGENTE_ID_INVALIDO": "Identificativo sorgente non valido: deve essere maggiore di zero.",
    "E_QTA_MISSING": "Quantita' nulla o mancante.",
    "E_QTA_NON_POSITIVA": "La quantita' deve essere positiva.",
    "E_QTA_OPERATIVA_NON_INTERA": "La quantita' operativa deve essere un numero intero.",
    "E_QTA_OPER_STEP_INVALIDO": "Quantita' operativa non compatibile con lo step previsto.",
    "E_QTA_SUPERA_RESIDUO": "La quantita' da evadere supera il residuo disponibile sull'ordine.",
    "E_QUERY_FAILED": "Errore di esecuzione della query sulla tabella indicata.",
    "E_QUERY_FAILED_SCHEMA_TABLE": "Interrogazione fallita sulla tabella indicata.",
    "E_RADICE_DI_PROVA_SENZA_ETICHETTA": "Esiste gia' un dato con lo stesso nome di un dato di prova, ma non e' stato creato come dato di prova: il provisioning di sviluppo non lo adotta.",
    "E_RATA_NON_TROVATA": "La rata non esiste o non e' accessibile.",
    "E_REA_NON_AMMESSO": "Per questa forma giuridica l'iscrizione al REA non si indica.",
    "E_REA_OBBLIGATORIO": "Per questa forma giuridica l'iscrizione al REA e' obbligatoria.",
    "E_RECONCILE_AMBIGUO": "Riconciliazione sorgente ambigua: piu' candidati.",
    "E_REGISTRO_COPPIA_GIA_COPERTA": "Questa azienda numera gia' questo tipo di documento su un altro registro: un documento si numera su un registro solo.",
    "E_REGISTRO_FORMA_NUMERO_IMMUTABILE":"La forma del numero non si puo' piu' cambiare: questo sezionale ha gia' consegnato dei numeri, e il contatore non riparte quando la forma cambia.",
    "E_REGISTRO_SERIE_NON_AMMESSA": "I documenti di questa famiglia non registrano la serie: il sezionale non puo' portarne una, o il contatore ripartirebbe da 1 su numeri gia' emessi.",
    "E_REPARTO_SENZA_PROFILO": "Il reparto non ha ancora un profilo permessi configurato.",
    "E_RESELLER_DISATTIVAZIONE_BLOCCATA": "Impossibile disattivare il reseller: esistono entita' collegate.",
    "E_RESET_LOTTO_FATTURA_VALIDATION": "Parametri reset fattura non validi.",
    "E_RESET_LOTTO_VALIDATION": "Parametri reset lotto non validi.",
    "E_RESET_PASSWORD": "Errore reset password.",
    "E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA": "L'accredito supera la quantita' fatturata dalla riga di fattura indicata.",
    "E_RESO_ANNULLO_CON_ACCREDITO": "Il reso ha un accredito registrato: annullare prima l'accredito sulla riga, poi il reso.",
    "E_RESO_ANNULLO_CON_RICONSEGNE": "Il reso e' gia' stato ri-spedito: non e' annullabile.",
    "E_RESO_DA_DDT_TRASFERIMENTO": "Una bolla di trasferimento fra depositi non genera un reso: la merce e' rimasta nostra.",
    "E_RESO_DDT_NON_CONSEGNATO": "Il DDT sorgente non e' in stato CONSEGNATO: reso non ammesso.",
    "E_RESO_EMITTENTE_BA_INCOERENTE": "Emittente fiscale non coerente col cliente del reso.",
    "E_RESO_MAGAZZINO_IMMUTABILE": "Il magazzino di rientro si sceglie solo in bozza: dopo la conferma la merce e' gia' entrata li'.",
    "E_RESO_MAGAZZINO_INCOERENTE": "Il magazzino indicato non appartiene all'azienda del reso.",
    "E_RESO_MAGAZZINO_OBBLIGATORIO": "Il reso non indica il magazzino in cui rientra la merce.",
    "E_RESO_NESSUNA_RICONSEGNA_PENDENTE": "Nessuna riga di ri-consegna pendente da ri-spedire per questo reso.",
    "E_RESO_NON_CONFERMATO": "Confermare il reso prima di generare la ri-spedizione.",
    "E_RESO_NOT_FOUND": "Reso non trovato.",
    "E_RESO_ORIGINE_INCOERENTE": "Il riferimento all'ordine sul reso non corrisponde a quello della riga DDT resa.",
    "E_RESO_QTA_SUPERA_CONSEGNATO": "La quantita' resa supera la quantita' consegnata residua della riga DDT.",
    "E_RESO_RICONSEGNA_SUPERA_RESO": "La quantita' ri-spedita supera la quantita' resa da ri-consegnare.",
    "E_RESO_RICONSEGNA_TIPO_NON_VALIDO": "Ri-spedizione ammessa solo su righe reso di tipo ri-consegna.",
    "E_RESO_RIENTRI_INCOMPLETI": "I rientri di una riga del reso non coprono la quantita': indicare quali lotti o seriali rientrano, e dove.",
    "E_RESO_RIENTRO_INCOERENTE": "Rientro non valido: si rende la merce uscita con la riga di bolla da cui viene la riga di reso.",
    "E_RESO_RIENTRO_OLTRE_USCITO": "Da un lotto o seriale rientrerebbe piu' merce di quanta ne era uscita, contando anche gli altri resi della bolla.",
    "E_RESO_RIGA_ONERE": "La riga e' un addebito, non merce: non si puo' rendere.",
    "E_RESO_RINUNCIA_ACCREDITO_ESEGUITO": "Rinuncia non piu' riapribile: l'accredito della quota e' gia' stato eseguito. Per riaprirla si deve prima annullare l'accredito.",
    "E_RESO_RINUNCIA_SUPERA_RESO": "La quantita' dichiarata definitiva supera la quantita' resa ancora da ri-consegnare.",
    "E_RESO_SENZA_RIGHE": "Il reso non ha righe: aggiungere almeno una riga prima della conferma.",
    "E_RESO_STATO_NON_ANNULLABILE": "Il reso non e' in uno stato che ammette l'annullo.",
    "E_RESO_STATO_NON_CONFERMABILE": "Il reso non e' in bozza: non e' confermabile.",
    # Ritirato il 2026-10-25 (porta comune, E_DOC_STATO_SOLO_DAL_VERBO): resta per il diario.
    "E_RESO_STATO_SOLO_DA_VERBO": "Il reso fa rientrare merce: il cambio di stato si fa solo dall'operazione del reso, che registra i movimenti di magazzino.",
    "E_RESO_STATO_TRANSIZIONE": "Operazione non ammessa nello stato corrente del reso.",
    "E_RESO_VALIDAZIONE": "Parametri reso non validi.",
    "E_RIGA_CANONE_SENZA_PERIODICITA": "Manca la periodicita': una riga a canone deve dire ogni quanto si addebita.",
    "E_RIGA_COMMESSA_GIA_ANNULLATA": "La riga era gia` stata annullata.",
    "E_RIGA_COMMESSA_GIA_EMESSA": "Riga gia` entrata nella catena di fatturazione: la correzione passa dalla nota di credito.",
    "E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO": "Motivo obbligatorio per annullare la riga.",
    "E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE": "L'annullamento di riga vale solo per gli oneri di commessa. Una rettifica di nota di credito si disfa con «Annulla l'accredito» sulla riga del reso.",
    "E_RIGA_COMMESSA_NON_MANUALE": "La riga nasce da un documento e non si annulla qui: il rimedio e` sul documento sorgente.",
    "E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO": "L'abbinamento della riga contabile e' incompleto: mancano dei dati per portarla a quello stato.",
    "E_RIGA_CONTABILE_CAPIENZA_SUPERATA": "L'importo non rientra in quanto resta da regolare sulla rata.",
    "E_RIGA_CONTABILE_DISTINTA_ANNULLATA": "La distinta contabile e' annullata: le sue righe si leggono soltanto.",
    "E_RIGA_CONTABILE_DISTINTA_FINALE": "La distinta contabile e' in uno stato finale: non accetta altre righe, e quelle che ha non si lavorano piu'.",
    "E_RIGA_CONTABILE_DISTINTA_NON_MANUALE": "La distinta contabile non e' compilata a mano: le sue righe non si eliminano da qui.",
    "E_RIGA_CONTABILE_DISTINTA_VALIDATA": "La distinta contabile e' validata: le sue righe non si aggiungono, non si modificano e non si eliminano finche' non torna in bozza.",
    "E_RIGA_CONTABILE_NON_TROVATA": "Riga contabile non trovata.",
    "E_RIGA_CONTABILE_RATA_INCOERENTE": "La rata non appartiene alla fattura di questa riga contabile.",
    "E_RIGA_CONTABILE_SENZA_ABBINAMENTO": "La riga contabile non e' registrabile: manca l'abbinamento a una fattura e a un billing account.",
    "E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA": "La distinta contabile non e' registrata: una riga si registra in ritardo solo sotto una distinta gia' registrata.",
    "E_RIGA_CONTABILE_TARDIVA_STATO": "La riga contabile non e' sospesa: in ritardo si registra solo una riga sospesa.",
    "E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA": "La riga contabile non puo' passare a quello stato.",
    "E_RIGA_DOC_NON_BOZZA": "Il documento non e' piu' in bozza: le sue righe si possono aggiungere, modificare o togliere solo finche' e' in bozza.",
    "E_RIGA_ECCEZIONE_FUORI_LISTINO": "L'articolo non e' nel listino del documento: un prezzo diverso o un'esclusione si applicano solo a un articolo del listino.",
    "E_RIGA_ECCEZIONE_SENZA_LISTINO": "Il documento non ha un listino in vigore: un prezzo diverso o un'esclusione si applicano solo a un articolo del listino.",
    "E_RIGA_EROGAZIONE_FUORI_PERIMETRO": "Questo articolo non si eroga così: scegliere un'erogazione e una fonte della quantità fra quelle che l'articolo ammette.",
    "E_RIGA_EROGAZIONE_OBBLIGATORIA": "Manca il tipo di erogazione: una riga che si fattura deve dire se e' un canone, una tantum, a ore o a consumo.",
    "E_RIGA_ESCLUSIONE_CON_DATI": "Un articolo escluso non porta prezzo, quantita' ne' erogazione: questi dati restano vuoti.",
    "E_RIGA_GIA_FATTURATA": "Riga gia' fatturata.",
    "E_RIGA_LISTINO_PROPAGATA": "Riga listino gia' propagata a valle: operazione non ammessa.",
    "E_RIGA_LISTINO_VERSIONE_CHIUSA": "Modifica righe listino non consentita: la versione non e' in stato BOZZA.",
    "E_RIGA_NATURA_NON_AMMESSA": "In un ordine o in una bolla vanno solo merci e articoli-onere: questo articolo non e' ne' una merce ne' un onere.",
    "E_RIGA_NATURA_VENDITA_IMMUTABILE": "La natura di vendita della riga non e' modificabile: la riga la riceve dall'articolo, o dal documento da cui nasce.",
    "E_RIGA_ONERE_DATA_CONSEGNA": "Un onere non porta date di consegna: lasciarle vuote sulla sua riga.",
    "E_RIGA_PREZZO_PENDENTE": "La riga e' in attesa di approvazione: solo lo stato di approvazione e i campi audit sono modificabili.",
    "E_RIGA_QUANTITA_CON_FONTE_A_VALLE": "Con questa fonte la quantita' non si indica sulla riga: arriva a valle, periodo per periodo. Svuotare la quantita', o scegliere la fonte fissa.",
    "E_RIGA_TIPOLOGIA_FUORI_UTILITY": "Questo articolo appartiene a una tipologia che la utility del documento non prevede.",
    "E_RISORSA_UMANA_GIA_PRESENTE": "Questa persona e' gia' una risorsa umana.",
    "E_RISORSA_UMANA_IDENTITA_ATTIVA": "Non si puo' disattivare la risorsa umana: l'utente ha ancora un'identita' operatore attiva.",
    "E_RISORSA_UMANA_SOGGETTO_MISMATCH": "Il soggetto collegato alla risorsa umana non e' un gestore.",
    "E_RITIRO_SORGENTE_PARAMETRO_MANCANTE": "Ritiro delle righe di commessa non eseguibile: la richiesta e' arrivata senza uno dei dati obbligatori (tipo del documento di origine, sua chiave, motivo).",
    "E_RUOLO_ALTRO_SOGGETTO": "Il ruolo indicato e' di un altro soggetto: un contatto puo' stare solo su un ruolo del suo soggetto.",
    "E_RUOLO_APPLICATIVO_NON_GESTITO": "Ruolo applicativo non gestito dal guard di coerenza: regola mancante.",
    "E_RUOLO_APPLICATIVO_RITIRATO": "Il ruolo applicativo DISABILITATO non e' piu' un tipo di veste: una veste si spegne con attivo = false.",
    "E_RUOLO_NATURA_NON_AMMESSA": "Tipo soggetto non ammesso per questo ruolo.",
    "E_RUOLO_NATURA_TIPO_DET_NULL": "Tipo soggetto dettaglio non configurato: ruolo non assegnabile.",
    "E_RUOLO_RICHIEDE_PIVA": "Il ruolo richiede un soggetto con partita IVA valorizzata.",
    "E_SCADENZE_BASE_NON_PRONTA": "Totale a pagare non calcolato: impossibile ripartire il piano rate.",
    "E_SCADENZE_FATTURA_BLOCCATA": "Lo stato della fattura non consente di rigenerare il piano rate.",
    "E_SCADENZE_LOTTO_PARZIALE": "Piano rate non generato per alcune fatture: vedi i log delle fatture interessate.",
    "E_SCADENZE_TERMINE_INVALIDO": "Regola di ripartizione del termine di pagamento non valida.",
    "E_SCADENZE_TERMINE_MANCANTE": "Termine di pagamento non valorizzato in testata.",
    "E_SCOPE_EMITTENTE": "Accesso negato per scope emittente fiscale.",
    # ⚠️ Il FRATELLO di sopra nega a un utente NOTO un emittente fuori perimetro;
    # questo dice che un utente non c'e' affatto. Le due frasi vanno tenute
    # distinte: sono due guasti diversi, e confonderli manda a cercare un
    # permesso dove manca un'identita'.
    "E_SCOPE_SENZA_UTENTE": (
        "Scrittura senza un utente in sessione su una tabella con perimetro "
        "emittente: il processo non dichiara chi agisce."
    ),
    "E_SCRIPT_CHIAMATA_NON_VALIDA": "Chiamata non valida a una funzione del database: anomalia tecnica.",
    "E_SCRITTURA_IN_LETTURA": "Modifica dati non permessa.",
    "E_SEARCH_NOT_FOUND": "Nessun risultato trovato.",
    "E_SEARCH_VALIDATION": "Parametri ricerca non validi.",
    "E_SEQUENZA_NON_CONFIGURATA": "Sequenza di numerazione non configurata.",
    "E_SESSIONE_NOT_FOUND": "Sessione non trovata o gia' revocata.",
    "E_SESSIONE_REVOCA_CORRENTE": "Non puoi revocare la sessione corrente. Usa il logout.",
    # Il catalogo nomina il tipo soggetto col `%s`; qui la frase senza.
    "E_SESSO_NON_AMMESSO": "Il sesso non si indica per questo tipo soggetto.",
    "E_SESSO_OBBLIGATORIO": "Il sesso e' obbligatorio per questo tipo soggetto: indicare M, F oppure X se non si puo' stabilire.",
    "E_SHOP_NON_DISPONIBILE": "Shop non ancora disponibile. In arrivo con PR-C.",
    "E_SHOP_RICEVUTA_BA_CANALE_INVALIDO": "Il billing account collegato alla ricevuta non e' di canale SHOP.",
    # ⭐ Anche qui il rifiuto nomina l'alternativa. Il varco CONFERMATA ->
    # ANNULLATA e' aperto per il solo RIPORTO, perche' e' l'unica destinazione
    # che lascia dietro un fondo: le altre due lasciano una distinta, e quella
    # si corregge con la correzione guidata.
    "E_SISTEMAZIONE_ANNULLO_NON_AMMESSO": (
        "Un rimborso o una compensazione gia' confermati non si annullano: "
        "si correggono con la correzione guidata sulla loro distinta."
    ),
    "E_SISTEMAZIONE_DOCUMENTI_INCOERENTI": "La sistemazione non ha i documenti che le servono per il suo tipo.",
    "E_SISTEMAZIONE_DOCUMENTI_NON_ABBINABILI": "Il documento non si puo' abbinare a questa sistemazione: e' di un altro cliente o di un'altra azienda.",
    "E_SISTEMAZIONE_ECCEDENZA_INSUFFICIENTE": "L'eccedenza sulla fattura non basta per la sistemazione richiesta.",
    "E_SISTEMAZIONE_IMMUTABILE": "Sistemazione non modificabile nello stato corrente: un atto eseguito non si modifica.",
    "E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO": "Motivo obbligatorio per questa operazione sulla sistemazione.",
    "E_SISTEMAZIONE_NON_CONFERMABILE": "Si conferma solo una sistemazione in bozza.",
    "E_SISTEMAZIONE_NON_TROVATA": "La sistemazione non esiste o non e' accessibile.",
    "E_SISTEMAZIONE_RIPORTO_NON_POSSIBILE": "La fattura non ha i dati che servono per un riporto.",
    "E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato della sistemazione non ammessa.",
    "E_SNAPSHOT_CLOSE_ERROR": "Storicizzazione: errore nella chiusura dello snapshot.",
    "E_SNAPSHOT_FINAL_INSERT_ERROR": "Storicizzazione: errore nell'inserimento dello snapshot finale.",
    "E_SNAPSHOT_ID_NOT_FOUND": "Storicizzazione: impossibile determinare l'identificativo del record.",
    "E_SNAPSHOT_INIT_INSERT_ERROR": "Storicizzazione: errore nell'inserimento dello snapshot iniziale.",
    "E_SOGGETTI_RUOLI": "Relazione soggetto/ruolo non valida.",
    "E_SOGGETTI_RUOLI_RACE": "Anomalia di concorrenza sull'assegnazione del ruolo.",
    "E_SOGGETTO_CREAZIONE_NATURA_ERRATA": "Il tipo soggetto non si crea da questo percorso.",
    "E_SOGGETTO_NOT_FOUND": "Soggetto non trovato.",
    "E_SOGGETTO_NO_CONTATTI": "Il soggetto deve avere almeno un contatto.",
    "E_SOGGETTO_NULL": "Soggetto mancante per il ruolo indicato.",
    "E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE": "Un ruolo appartiene per sempre al suo soggetto: se e' sul soggetto sbagliato si ritira e si ricrea.",
    "E_SOGGETTO_RUOLO_NON_TROVATO": "Il ruolo del soggetto non esiste.",
    "E_SORGENTE_CON_RIGHE_EMESSE": "Il documento ha righe di commessa gia' emesse: non si puo' chiudere finche' ci sono. Si recuperano prima dalla dashboard di competenza, casella «Emesse non fatturate», col verbo «Riporta da emettere»; fatto questo il documento si chiude e il ritiro le prende insieme alle altre.",
    "E_SORG_CHIAVE_NON_CONFORME": "La provenienza non e' scritta con la chiave che il suo tipo richiede.",
    "E_SORG_CONF": "Configurazione sorgente mancante o non attiva.",
    "E_SORG_DETTAGLIO_NON_DELLA_RIGA": "Il dettaglio indicato non appartiene alla riga del documento di origine.",
    "E_SORG_EMITTENTE_NON_RISOLTO": "Impossibile stabilire chi emette il documento di origine: anomalia tecnica.",
    "E_SORG_FORMATO": "Chiave sorgente in formato non valido per il tipo indicato.",
    "E_SORG_KEYSEL": "Selettore di chiave sorgente non supportato.",
    "E_SORG_KEY_MISSING": "Chiave sorgente mancante.",
    "E_SORG_LIVELLO_MANCANTE": "La provenienza non arriva fino al livello che la tabella richiede.",
    "E_SORG_LIVELLO_NON_PREVISTO": "La provenienza indica un livello che il suo tipo non prevede.",
    "E_SORG_NORM_NON_RISOLTA": "Chiave sorgente non traducibile per il tipo indicato.",
    "E_SORG_NOT_FOUND": "Riferimento sorgente non trovato nella tabella target.",
    "E_SORG_ORIGINE_REFERENZIATA": "Non si puo' cancellare: altre registrazioni dichiarano di nascere da qui.",
    "E_SORG_RIGA_NON_DEL_DOCUMENTO": "La riga indicata non e' una riga del documento di origine.",
    "E_SOSPENSIONE_DATA_FINE": "La data di riattivazione deve essere successiva all'inizio della sospensione.",
    "E_SOSPENSIONE_DATA_FUTURA": "La data della sospensione non puo' essere nel futuro.",
    "E_SOSPENSIONE_INSERT": "Errore durante l'inserimento della sospensione.",
    "E_SOSPENSIONE_NOT_FOUND": "Sospensione non trovata o gia' chiusa.",
    "E_SOSPENSIONE_OVERLAP": "Esiste gia' una sospensione che copre questo periodo per la stessa pratica o lo stesso flusso.",
    "E_SOSPENSIONI_FLUSSO_NON_COERENTE": "Il flusso non appartiene alla pratica della sospensione.",
    "E_SPLIT_PAYMENT_NON_AMMESSO": "Questo tipo soggetto non puo' essere in split payment.",
    "E_SQL_READ_TABLE": "Errore in lettura sulla tabella indicata.",
    "E_STAMPA_JOB_STANTIO": "Render interrotto (worker morto o kill): recuperato dal reaper.",
    "E_STATISTICHE_MANCANTI": "Dopo l'aggiornamento delle statistiche restano tabelle senza statistiche.",
    "E_STATO_DDT_TRANSIZIONE_NON_VALIDA": "Transizione di stato non ammessa per il DDT.",
    "E_STATO_DOC_ESITO_NON_VERDETTO": "L'esito indicato non e' un verdetto: non ammesso come proiezione.",
    "E_STATO_ISO2_AMBIGUO": "Il codice dello stato indica piu' stati dell'elenco: il sistema non puo' scegliere da solo.",
    "E_STATO_RESO_TRANSIZIONE_NON_VALIDA": "Transizione di stato non ammessa per il reso.",
    "E_STATO_SORGENTE_PARAM_INVALIDO": "Parametri sorgente non validi.",
    "E_STATO_WORKFLOW_NON_TROVATO": "Stato di destinazione non trovato o non attivo.",
    "E_STORICO_FK_COL_ASSENTE": "Automazione di storico: la colonna di collegamento non esiste nella tabella storica.",
    "E_STORICO_PARENT_PK_NOT_FOUND": "Impossibile determinare la chiave primaria della tabella padre.",
    "E_STORICO_PROVISION": "Generazione della tabella di storico fallita.",
    "E_STORICO_SCOPE_CATENA_CICLICA": (
        "La mappa del perimetro dello storico gira in cerchio: la catena dei "
        "padri non termina."
    ),
    "E_STORICO_UD": "Automazione di storicizzazione fallita.",
    "E_STRADARIO_NON_TROVATO": "La via indicata non esiste nello stradario.",
    "E_STRADARIO_SOPPRESSO": "La via e' soppressa: e' gia' stata fusa in un'altra e non si puo' piu' fondere.",
    "E_TABELLA_OP_NON_CONSENTITA": "Operazione non consentita su questa tabella.",
    "E_TASK": "Errore esecuzione task.",
    "E_TASK_FATTURA": "Errore task fattura.",
    "E_TASK_IMPLEMENTATION_NOT_FOUND": "Implementazione task non trovata.",
    "E_TASK_NOT_ALLOWED": "Task pipeline non autorizzato.",
    "E_TASK_NOT_IMPLEMENTED": "Task pipeline non implementato.",
    "E_TASK_RESET_REQUIRED": "Reset necessario prima di rieseguire.",
    "E_TEMPLATE_CODICE_DUPLICATO": "Codice gia' usato da un altro step della definizione.",
    "E_TEMPLATE_DEFINIZIONE_CONGELATA": "Edizione per-emittente gia' emessa: la struttura non e' piu' modificabile (solo la descrizione e' correggibile).",
    "E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA": "Modalita' esito AUTOMATICO ammessa solo su step a direzione INTERNA.",
    "E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO": "Uno step DOMINIO non ammette esito default: l'esito lo calcola il dominio.",
    "E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO": "Esito default non valido: AUTOMATICO/CONTESTUALE richiedono un verdetto.",
    "E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO": "Esito default obbligatorio per la modalita' esito scelta.",
    "E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER": "Conflitto sullo step: ammesso solo uno fra avanzamento su proiezione e handler eventi.",
    "E_TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO": "Avanzamento su proiezione non ammesso su uno step DOMINIO.",
    "E_TIPI_RUOLI_ENTITA_INVALIDA": "Configurazione tipo ruolo non valida.",
    # Scorporato da `E_ERRORE_PARAMETRI` dal team DB il 2026-08-08, dopo la
    # misura del §10.1: 3 dei suoi punti dicevano 400 dove serve 500. E' un
    # difetto di MONTAGGIO del trigger — se ne accorge chi lo installa, mai
    # l'operatore — quindi il messaggio non gli chiede di correggere niente.
    "E_TIPO_RUOLO_NON_RICERCABILE": "Questo tipo ruolo non si cerca nella ricerca universale.",
    "E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI": "Il nuovo tipo soggetto non ammette un titolo IVA ancora in vigore: chiudere prima il titolo.",
    "E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA": "Il nuovo tipo soggetto non ammette la forma giuridica: cambiare anche la forma.",
    "E_TITOLO_IVA_AMBITO_NON_AMMESSO": "Questo titolo IVA vale per tutte le merci: non ammette un elenco di voci. Togli le voci, oppure dichiara il titolo ristretto.",
    "E_TITOLO_IVA_AMBITO_SOVRAPPOSTO": "Esiste gia' un titolo IVA dello stesso tipo, valido nello stesso periodo, che copre la stessa merce allo stesso livello.",
    "E_TITOLO_IVA_AMMISSIONE_IN_USO": "Il titolo IVA non si puo' ritirare per questo tipo soggetto: ci sono titoli in vigore che lo usano.",
    "E_TITOLO_IVA_ANNULLO_INCOERENTE": "La riga di annullo non corrisponde al movimento di plafond che dichiara di annullare: titolo diverso, oppure importo che non ne e' l'opposto esatto.",
    # ⛔ NON ENUMERA I MOTIVI, ed e' deliberato: `fn_check_annullo_movimento_titolo_iva`
    #    ne nomina CINQUE (non trovato, non e' una forzatura, e' gia' un annullo,
    #    gia' annullato, plafond negativo) e nominarne tre manderebbe a cercare
    #    la causa sbagliata. Il motivo puntuale viaggia gia' come capability di
    #    riga (`annullo_blocco_codice` + la sua chiave i18n) ed e' li' che si
    #    legge. Stessa ragione per cui il messaggio a catalogo dice soltanto
    #    «non si puo' annullare».
    "E_TITOLO_IVA_ANNULLO_NON_AMMESSO": "Questo movimento di plafond non si puo' annullare nello stato in cui si trova. Il motivo puntuale e' sulla riga del registro, nel drawer del titolo IVA.",
    "E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA": "Consumo di plafond chiesto a una data fuori dalla validita' del titolo.",
    "E_TITOLO_IVA_CONSUMO_NON_INVOCABILE": "Consumo di plafond invocato senza i dati necessari, o su un titolo che non esiste.",
    "E_TITOLO_IVA_MOVIMENTO_IMMUTABILE": "Il registro dei movimenti di plafond IVA e' append-only: una riga scritta non si modifica e non si cancella. Per correggere si registra un annullo.",
    "E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO": "Questo titolo IVA non e' ammesso per il tipo soggetto.",
    "E_TITOLO_IVA_PLAFOND_MANCANTE": "Questo tipo di titolo ha un tetto che si consuma: indica il plafond.",
    "E_TITOLO_IVA_PLAFOND_NON_AMMESSO": "Questo tipo di titolo non ha un tetto da consumare: il plafond non si indica.",
    "E_TITOLO_IVA_UTILIZZATO_NEGATIVO": "Il consumo del titolo scenderebbe sotto zero: non e' un valore possibile.",
    "E_TOTP_CODICE_NON_VALIDO": "Codice non valido.",
    "E_TOTP_CONFIGURAZIONE_RICHIESTA": "Prima di continuare e' necessario configurare il secondo fattore di autenticazione.",
    "E_TOTP_DEVICE_ASSENTE": "Il secondo fattore non e' attivo per questo accesso.",
    "E_TOTP_DEVICE_GIA_ATTIVO": "Il secondo fattore e' gia' attivo per questo accesso.",
    "E_TOTP_MOTIVO_OBBLIGATORIO": "Indicare il motivo della disattivazione.",
    "E_TOTP_PASSO_GIA_USATO": "Codice gia' usato: attendere il prossimo codice.",
    "E_TOTP_PASSWORD_NON_VALIDA": "Password non corretta.",
    "E_TOTP_RECOVERY_NON_VALIDO": "Codice di recupero non valido o gia' usato.",
    "E_TOTP_SFIDA_NON_VALIDA": "La verifica e' scaduta: accedere di nuovo con la password.",
    "E_TRIGGER_ARGOMENTI_INVALIDI": "Trigger montato con argomenti non validi.",
    "E_TIPO_FONDO_NOT_FOUND": "Tipo fondo non trovato.",
    "E_TIPO_INDIRIZZO": "Tipo indirizzo non ammesso per questo documento.",
    "E_TIPO_INDIRIZZO_NON_PERMESSO": "Tipo indirizzo non permesso per questo tipo di ruolo.",
    "E_TIPO_INDIRIZZO_NON_TROVATO": "Il tipo di indirizzo non esiste.",
    "E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO": "Tipo indirizzo non permesso per questo tipo di soggetto.",
    "E_TIPO_RUOLO_NON_TROVATO": "Tipo ruolo non trovato.",
    "E_TOKEN": "Token non valido, scaduto o gia' utilizzato.",
    "E_TXID_GENERATION": "Generazione del tx_id fallita.",
    "E_TX_ID": "Generazione del trigger tx_id fallita.",
    "E_UI_CAMPO_SORGENTE_NON_TROVATO": "Campo sorgente colonna non trovato nella vista SQL.",
    "E_UI_CHIAMATA_NON_VALIDA": "Chiamata non valida alla configurazione della lista: il contesto della richiesta non corrisponde all'utente.",
    "E_UI_COLONNA_IN_USO": "La colonna e' in uso (preferenze utente, preset o permessi). Disattivala con attivo=false invece di eliminarla.",
    "E_UI_COLONNA_NON_TROVATA": "Colonna lista non trovata.",
    "E_UI_COLONNA_VALIDAZIONE": "Colonna lista non valida.",
    "E_UI_DASHBOARD_NON_TROVATA": "Dashboard non trovata.",
    "E_UI_DEFINIZIONE_IN_USO": "La definizione lista e' in uso (preferenze utente, colonne o preset). Disattivala con attivo=false invece di eliminarla.",
    "E_UI_DEFINIZIONE_NON_TROVATA": "Definizione lista non trovata.",
    "E_UI_DEFINIZIONE_VALIDAZIONE": "Definizione lista non valida.",
    "E_UI_EXPORT_FAILED": "Generazione export non riuscita.",
    "E_UI_EXPORT_FORMAT_INVALID": "Formato export non supportato (ammessi: csv, xlsx).",
    "E_UI_EXPORT_LIMIT_EXCEEDED": "L'export supera il limite di righe consentito. Raffina i filtri e riprova.",
    "E_UI_GENERIC_FAILED": "Errore configurazione lista.",
    "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE": "Questa lista non dice da quale emittente arriva ogni riga: scegli un emittente per entrare.",
    "E_UI_LISTA_NON_TROVATA": "Lista non trovata.",
    "E_UI_MISURA_PAGINA_DEFAULT_MANCANTE": "Manca la misura di default delle righe per pagina: anomalia di catalogo.",
    "E_UI_MISURA_PAGINA_NON_AMMESSA": "La misura di righe per pagina non e' fra quelle ammesse.",
    "E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE": "Il flag multi_emittente di una lista non si imposta dall'applicazione: si dichiara dal seed, insieme al lavoro che lo rende vero.",
    "E_UI_PERMESSO_NON_TROVATO": "Permesso colonna non trovato.",
    "E_UI_PERMESSO_VALIDAZIONE": "Permesso colonna non valido.",
    "E_UI_PREFERENZA_NON_TROVATA": "Preferenza utente non trovata per questa lista.",
    "E_UI_PREFERENZA_VALIDAZIONE": "Preferenza lista non valida.",
    "E_UI_PRESET_NON_TROVATO": "Preset lista non trovato.",
    "E_UI_PRESET_VALIDAZIONE": "Preset lista non valido.",
    "E_UI_VISTA_SQL_NON_TROVATA": "Vista SQL della lista non trovata nel database.",
    "E_UOM_MISMATCH": "Riga ordine e riga DDT hanno unita' di misura diverse.",
    "E_UOM_MISSING": "Unita' di misura mancante.",
    "E_UPDATE_NOT_ALLOWED": "Modifica non permessa su questa riga.",
    "E_USER_DISABILITATO": "Utente disabilitato. Contattare l'amministratore.",
    "E_USER_EMITTENTE_DELETE_VIETATO": "Eliminazione vietata: l'associazione utente-emittente puo' essere rimossa solo come parte della disattivazione utente.",
    "E_UTENTE_BLOCCATO": "Troppi tentativi non riusciti da questa postazione: riprovare fra qualche minuto.",
    "E_UTENTE_DISABILITATO": "Account disabilitato. Contattare l'amministratore.",
    "E_UTENTE_NON_ATTIVO": "Account non ancora attivo.",
    "E_UTENTE_SCADUTO": "Account scaduto. Contattare l'amministratore.",
    "E_UTENTE_TECNICO_DA_RIATTIVARE": (
        "Per questo processo e quell'azienda un utente tecnico esiste gia', ma e' "
        "spento: va riattivato, non creato di nuovo."
    ),
    "E_UTENTE_TECNICO_EMITTENTE_NON_VALIDO": (
        "Azienda emittente inesistente o non attiva: un utente tecnico nasce PER "
        "un'azienda, e senza non potrebbe fare niente."
    ),
    "E_UTENTE_TECNICO_GIA_ESISTE": (
        "Il processo ha gia' un utente tecnico attivo per quell'azienda."
    ),
    "E_UTENTE_TECNICO_NON_TROVATO": (
        "Non esiste un utente tecnico da riattivare per questo processo e "
        "quell'azienda: va creato."
    ),
    "E_UTENTE_TECNICO_PROFILO_VIETATO": (
        "Profilo di accesso non utilizzabile per un utente tecnico."
    ),
    "E_UTILITY_RUOLO_NON_AMMESSO": "Tipo ruolo non ammesso per questa utility.",
    "E_VALIDATION_INPUT": "Parametro di input non valido.",
    "E_VALIDAZIONE": "Validazione fallita.",
    "E_VALORE_MANCANTE": "Valore obbligatorio mancante.",
    # ── I tre «progettati mai cablati» del push preventivo, arrivati col
    # catalogo alla prima generazione. Nessuna funzione li solleva ancora
    # (`push_preventivo_handler.md` è un documento di disegno): il messaggio è la
    # variante senza segnaposto di quello a catalogo, scritta ora perché il
    # giorno in cui qualcuno li caglierà non sia anche il giorno in cui si scopre
    # che non hanno una frase.
    "E_VENDITA_COMPETENZA_RICHIESTA": "Competenza di fatturazione richiesta per la modalita' DIFFERITA.",
    "E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA": "Modalita' di fatturazione non valida.",
    "E_VENDITA_PREVENTIVO_GIA_PUSHATO": "Preventivo gia' pushato a commessa.",
    "E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE": "Nessuna riga merce da portare a ordine.",
    "E_VENDITA_PREVENTIVO_NON_COLLEGATO": "Il preventivo non e' collegato a una pratica: azione non disponibile.",
    "E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO": "Il preventivo non e' in stato ACCETTATO: impossibile generare un ordine.",
    "E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA": "Articolo a servizio ricorrente: usare l'offerta commerciale, non il preventivo.",
    "E_VENDITA_SMISTAMENTO_NON_ESEGUITO": "Esegui lo smistamento della merce (genera ordine) prima di completare lo step.",
    "E_VENDITE_CHIAMATA_NON_VALIDA": "Chiamata non valida a una funzione di vendite: parametro obbligatorio mancante o fuori intervallo.",
    "E_VENDITE_CONTRATTO_OVERLAP": "Esiste gia' un contratto sovrapposto per questo cliente/istanza/utility/ambito nel periodo indicato.",
    "E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA": "Impossibile calcolare la previsione delle fatture da emettere.",
    "E_VENDITE_DUPLICATO": "Record gia' esistente (violato vincolo di univocita').",
    "E_VENDITE_FK": "Riferimento non valido: l'entita' indicata non esiste.",
    "E_VENDITE_LISTINO_ASSOCIAZIONE_NOT_FOUND": "Associazione listino non trovata.",
    "E_VENDITE_LISTINO_NOT_FOUND": "Listino non trovato.",
    "E_VENDITE_LISTINO_RIGA_COMP_OVERLAP": "Esiste gia' un prezzo bundle attivo sovrapposto per questo componente nel periodo indicato. Disattiva o chiudi quello esistente prima di salvare il nuovo prezzo.",
    "E_VENDITE_LISTINO_RIGA_NOT_FOUND": "Riga listino non trovata.",
    "E_VENDITE_LISTINO_VERSIONE_NOT_FOUND": "Versione listino non trovata.",
    "E_VENDITE_LISTINO_VERSIONE_OVERLAP": "Esiste gia' una versione ATTIVA sovrapposta per il listino. Chiudi la vecchia (valido_al = nuova_valido_dal - 1) e poi attiva la nuova: la nuova decorrenza deve essere almeno 1 giorno dopo l'inizio della precedente.",
    "E_VENDITE_NOT_FOUND": "Record vendite non trovato.",
    "E_VENDITE_PRICING_ESITO_ASSENTE": "Errore interno del calcolo prezzi: il resolver non ha restituito un esito. Segnalare all'assistenza.",
    "E_VENDITE_PRICING_FAILED": "Impossibile risolvere il prezzo listino.",
    "E_VENDITE_PROMO_OVERLAP": "Esiste gia' una promo attiva per questo (articolo, unita' di misura) nel periodo indicato.",
    "E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA": "Riallineamento richiede conferma: la versione listino e` cambiata.",
    "E_VENDITE_RIGA_GIA_PROPAGATA": "Riga gia` propagata in commessa o fatturabile. Usare clone versione.",
    "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO": "Sblocco prezzo non ammesso: il prezzo non e` bloccato.",
    "E_VENDITE_VALIDATION": "Parametri non validi.",
    "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA": "Operazione prezzo non ammessa sullo stato corrente.",
    "E_VERSIONE_STATO_TRANSIZIONE_INVALIDA": "Chiusura versione non consentita via cambio stato. Per chiudere impostare valido_al (PATCH); la chiusura avviene automaticamente a finestra scaduta.",
    "E_VESTE_NON_ATTIVA": "Non hai accesso a questo canale.",
    "FLUSSI_COMPETENZA_MANCANTE": "Operatore non abilitato per questo tipo di flusso.",
    "FLUSSI_ESITO_NON_AMMESSO": "Esito non ammesso per questo step.",
    "FLUSSI_ESITO_OBBLIGATORIO": "Esito obbligatorio per completare il flusso.",
    "FLUSSI_GIA_ASSEGNATO": "Flusso gia' assegnato a un operatore.",
    "FLUSSI_PRESA_CARICO_STATO_ERRATO": "Presa in carico non consentita: il flusso non e' DA_ESEGUIRE.",
    "FLUSSI_PRESA_NON_ELIGIBILE": "Presa in carico non consentita: il flusso e' instradato a un altro reparto.",
    "FLUSSI_TEMPLATE_FUORI_DEFINIZIONE": "Lo step non appartiene alla definizione della pratica.",
    "FLUSSI_TRANSIZIONE_NON_AMMESSA": "Transizione di stato flusso non ammessa.",
    "GENERAZIONE_TEMPLATE_NON_IN_DEFINIZIONE": "Lo step dichiarato dalla regola non esiste nella definizione della pratica figlia.",
    "PIVA_NON_VALIDA": "Partita IVA non valida.",
    "PRATICHE_CHIUSURA_FLUSSI_APERTI": "Impossibile chiudere la pratica: ci sono flussi ancora aperti. Completali o annullali, poi riprova.",
    "PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI": "Impossibile chiudere la pratica: flussi obbligatori non completati.",
    "PRATICHE_CHIUSURA_FLUSSO_PREMATURO": "Impossibile completare il flusso di chiusura: restano altri flussi obbligatori da completare.",
    "PRATICHE_FLUSSO_NON_RIPETIBILE": "Il flusso non e' ripetibile in questa pratica.",
    "PRATICHE_ISTANZA_NON_COERENTE": "L'istanza non appartiene al soggetto indicato.",
    "PRATICHE_ISTANZA_SENZA_SOGGETTO": "L'istanza utility richiede anche il soggetto.",
    "PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI": "Indicare una sola lente di contesto: ruolo soggetto, istanza utility o solo interne.",
    "PRATICHE_PIN_IMMUTABILE": "L'edizione di workflow pinnata dalla pratica e' immutabile.",
    "PRATICHE_PREREQUISITI_NON_SODDISFATTI": "Flusso non ancora eseguibile: prerequisiti non soddisfatti.",
    "PRATICHE_RUOLO_NON_COERENTE": "Il ruolo non appartiene al soggetto indicato.",
    "PRATICHE_RUOLO_SENZA_SOGGETTO": "Il ruolo richiede anche il soggetto.",
    "PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE": "Aggancio sorgente incoerente: il flusso appartiene a un'altra pratica.",
    "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE": "Impossibile modificare il flusso: la pratica e' in stato terminale.",
    "PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO": "Impossibile creare un flusso: la pratica e' in stato terminale.",
    "PRATICHE_TRANSIZIONE_NON_AMMESSA": "Transizione di stato pratica non ammessa.",
    "PREV_NESSUNA_RIGA_ATTIVA": "Preventivo senza righe attive: serve almeno una riga per emettere.",
    "PREV_REVISIONE_BOZZA_ESISTENTE": "Esiste gia' una revisione in BOZZA per questo preventivo. Completa o annulla la BOZZA esistente prima di crearne una nuova.",
    "PREV_REVISIONE_STATO_NON_AMMESSO": "Revisione ammessa solo da preventivo EMESSO.",
    "PREV_STATO_CORRENTE_NON_TROVATO": "Stato corrente del preventivo non trovato.",
    "PREV_TRANSIZIONE_NON_AMMESSA": "Transizione del preventivo non ammessa.",
    "SEQUENZA_NON_CONFIGURATA": "Sequenza di numerazione non configurata.",
    "SOSPENSIONI_FLUSSO_NON_COERENTE": "Il flusso non appartiene alla pratica indicata.",
    "TEMPLATE_DEFINIZIONE_CONGELATA": "Edizione per-emittente gia' emessa: la struttura non e' piu' modificabile (solo la descrizione e' correggibile).",
    "TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA": "Modalita' esito AUTOMATICO ammessa solo su step a direzione INTERNA.",
    "TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO": "Uno step DOMINIO non ammette esito default: l'esito lo calcola il dominio.",
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO": "Esito default non valido: AUTOMATICO/CONTESTUALE richiedono un verdetto.",
    "TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO": "Esito default obbligatorio per la modalita' esito scelta.",
    "TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER": "Conflitto sullo step: ammesso solo uno fra avanzamento su proiezione e handler eventi.",
    "TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO": "Avanzamento su proiezione non ammesso su uno step DOMINIO.",
    # ⚠️ I due `W_` qui sotto NON hanno una entry in `config.messaggi_errore`, ed
    # e' una decisione del team DB (L1 del cantiere liste drawer lotto): quei
    # punti scrivono la frase direttamente in `vendite.fatture_log.messaggio` e
    # non passano da `script.fn_log_and_raise_error`, quindi un messaggio a
    # catalogo sarebbe una seconda copia della stessa frase che nessuno compone.
    # Il ripiego serve lo stesso — il cancello del terzo lato lo pretende per
    # ogni codice VIVO — e vale come l'unica frase che il backend sa dire se
    # quel codice arrivasse comunque da un percorso non previsto.
    # 📌 Sono AVVISI: si registrano e il giro prosegue. Un `W_` sollevato
    # sarebbe un 500, ed e' esattamente cio' che non devono fare.
    "W_BERSAGLIO_MALFORMATO": "Avviso tecnico - il bersaglio dell'errore non e' utilizzabile: l'errore parte lo stesso, ma senza l'indicazione di quale cosa riguardi.",
    "W_FONDO_ESEGUITO_NON_RESETTABILE": "Fondo gia' eseguito: non si azzera, e la riga resta com'e'.",
    "W_FONDO_FIGLIA_CONGELATA": "Fondo non azzerato: la fattura che lo ha ricevuto non si puo' piu' modificare, e la riga resta com'e'.",
    "W_FONDO_MINIMO_NON_RIPRISTINABILE": "Minimo del fondo non ripristinabile: la quota resta come e'.",
    "W_FONDO_RIGA_CONTABILE_NON_AGGIORNABILE": "Riga contabile non aggiornabile: il fondo resta legato a quella che c'e'.",
    "W_FONDO_TRATTENUTO_DA_SISTEMAZIONE": "Fondo non azzerato: una sistemazione lo trattiene, e si disfa annullando quella.",
    "W_MESSAGGIO_ARITA": "Messaggio di errore con segnaposti non valorizzati: anomalia tecnica di catalogo.",
    "W_SCADENZE_TOTALE_NEGATIVO": "Totale a pagare negativo: nessun piano rate generato.",
    "W_TXID_BYPASS_PARAMETRO_ASSENTE": "Avviso - il parametro del bypass del tx_id non e' valorizzato: il bypass resta spento.",
    "W_TXID_NOT_REGISTERED": "Transazione non registrata: anomalia tecnica di tracciamento.",
}
