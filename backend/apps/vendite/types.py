# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `TypedDict` e alias condivisi del dominio vendite — le righe che i
#        repository restituiscono e la pipeline si passa. Servono a togliere
#        le chiavi «magiche» dalle firme e a far vedere al type checker cosa
#        un payload porta davvero.
# ------------------------------------------------------------

from datetime import date

from typing import Any, TypeAlias, TypedDict

# Tipi condivisi pipeline vendite per ridurre chiavi "magiche" e firma duplicate.

LottoPipelineMeta: TypeAlias = dict[str, Any]


class PipelineStepLogMeta(TypedDict):
    ordine: int | None
    dry_run: bool


# Chiave di raggruppamento delle attivita' fatturabili in riga di fattura.
# Serializzata in `fatture_righe.meta.group_key` come traccia dell'aggregazione.
# `prezzo_unitario` e' una STRINGA canonica e non un float: il prezzo e' cio' che
# rende l'aggregazione un'identita' esatta (somma(qi*p) = p*somma(qi)), e
# raggruppare su un float la renderebbe approssimata.
# `visibilita_componenti` e' uscita dal modello il 2026-07-28: non era la regola
# di esposizione dei kit (quella e' `articoli_componenti.esposizione_in_fattura`) e
# non aveva alcun consumatore vivo.
class GroupAttivitaKey(TypedDict):
    articolo_id: str  # uuid (catalogo.articoli.id)
    dest_billing_account_id: int
    uom_id: int | None
    prezzo_unitario: str | None
    iva_id: int | None
    competenza_dal: str | None
    competenza_al: str | None
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str
    # ── Rettifica (nota di credito) ──────────────────────────────────────────
    # La riga di fattura che questa riga rettifica. `None` su tutto cio' che
    # non e' una rettifica, che e' il caso normale.
    #
    # ⭐ STA NELLA CHIAVE, e non e' un campo informativo: e' cio' che impedisce
    # a due rettifiche di righe di fattura DIVERSE di fondersi in una riga sola
    # — che sarebbe una riga «gemella di nessuna» (brief nota di credito
    # §12.6). Due rettifiche della STESSA riga di fattura restano invece
    # aggregabili: la riga prodotta e' comunque la gemella di quella, e il
    # tetto per riga di fattura lo tiene il guard DB.
    fattura_riga_rettificata_id: int | None
    # Copiato dalla riga rettificata, mai ricalcolato (N-1). Entra nella chiave
    # per la stessa ragione del prezzo: se la chiave prendesse un valore e la
    # INSERT ne scrivesse un altro, le due meta' si annullerebbero in silenzio.
    sconto_percentuale: str | None
    # ── L'atto ───────────────────────────────────────────────────────────────
    # ⛔ IL CONTRATTO STA NELLA CHIAVE, e la sua assenza era un difetto vivo:
    # due attivita' di contratti DIVERSI collassavano nella stessa riga di
    # fattura. Su quella riga aggregata nessuna domanda per atto ha una
    # risposta — a partire dal CIG, che la FatturaPA vuole per blocco
    # `DatiContratto` con `RiferimentoNumeroLinea` a puntare le sue righe.
    #
    # ⭐ E non sposta nessun raggruppamento esistente: fuori da un contratto il
    # valore e' `None` per tutte le attivita', quindi si spezzano SOLO le righe
    # che oggi mescolano davvero due atti.
    #
    # ⚠️ `None` anche su una RETTIFICA, ed e' voluto: l'identita' di una riga di
    # nota di credito e' la riga di fattura che rettifica — `fattura_riga_
    # rettificata_id`, che e' strettamente piu' specifico del contratto. Dare
    # peso anche al contratto dell'attivita' potrebbe spezzare due rettifiche
    # della STESSA riga, cioe' rompere in silenzio l'invariante «due rettifiche
    # della stessa riga restano aggregabili». Quando `vendite.fatture_atti`
    # dara' alla riga di fattura una sede per l'atto, la rettifica lo
    # copiera' da li' come gia' fa con prezzo, sconto e IVA (N-1).
    contratto_id: int | None


class AnnullaLottoDaDraftResult(TypedDict):
    updated_lotti: int
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int


class RiportaLottoADraftResult(TypedDict):
    # Esito del ritorno a bozza (Fase 6). Simmetrico ad
    # `AnnullaLottoDaDraftResult` piu' `riemesse_attivita`: il contatore delle
    # `commesse_attivita` riportate a NON_EMESSA, che e' l'effetto senza il
    # quale il lotto ripartirebbe senza niente da emettere.
    updated_lotti: int
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int
    riemesse_attivita: int
    # Task run chiusi ad ANNULLATO (changeset 20260803-12). E' il contatore che
    # rende il ritorno a bozza EFFICACE: finche' i task run restavano
    # COMPLETATO, `fn_resolve_lotto_task_execution_mode` rispondeva SKIP e il
    # lotto riaperto rilanciava a vuoto. Su TUTTI gli step, non solo DRAFT —
    # annullare la sola bozza avrebbe spostato lo SKIP un passo piu' avanti.
    annullati_task_run: int


class EliminaFatturaDaLottoResult(TypedDict):
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int
    # Quarto contatore (DB 2026-08-04, slice 6-B): tenuto separato dal primo
    # di proposito — «attivita' sbloccate» e «attivita' di commessa tornate
    # NON_EMESSA» sono fatti diversi per il cockpit, un totale unico li
    # confonderebbe. Stessa forma delle due sorelle sul lotto intero.
    riemesse_attivita: int


class LottoSegnalazioniSummary(TypedDict):
    fatture_critical_count: int
    fatture_warning_count: int
    lotto_critical_count: int
    lotto_warning_count: int
    lotto_info_count: int
    fatture_stato_esecuzione_errore_count: int
    # ═══ I TRE NUMERI DEL BANNER (2026-09-08) ═══
    # ⭐ I sei qui sopra contano SEGNALAZIONI; questi contano GESTI. Un documento
    # con tre critiche resta UN documento, e il gesto che l'operatore ha davanti
    # e' uno solo: «togli questo dal giro». «3 segnalazioni bloccanti» e' un
    # numero vero che descrive la cosa sbagliata.
    documenti_bloccanti_count: int
    # Il DENOMINATORE, e viene dagli ESITI — non dal perimetro, che sui giri di
    # massa e' vuoto e direbbe «su 0» su meta' dei lotti.
    documenti_presi_in_carico_count: int
    # ⛔ Le critiche che un documento NON ce l'hanno, e non e' un di piu': senza,
    # un lotto fermo per un emittente non risolto direbbe «0 documenti su 4» —
    # cioe' che non c'e' niente da fare mentre il giro e' bloccato.
    # ⚠️ I tre descrivono il canale LOTTO. Gli altri due parlano per FATTURA, e
    # una bozza puo' coprire piu' documenti: non si sommano a questi.
    critiche_giro_count: int
    # ═══ IL DECIMO NUMERO (2026-09-12, D2 del brief «il rilancio dello step non
    # rivede le proprie commesse») — e questo ENTRA NEL VERDETTO ═══
    # I documenti presi in carico il cui ULTIMO fatto registrato
    # (`fatturazione_lotti_esiti`) e' `ERRORE`. Un esito e' un fatto su un
    # documento preso in carico: un lotto `COMPLETATO` con un documento il cui
    # ultimo fatto e' `ERRORE` si dichiara a posto per SOTTRAZIONE — il runner
    # ritira le proprie bandiere all'avvio di ogni rerun, e se il giro non
    # rivede quel documento nessuno le rialza. Sette lotti usciti cosi' prima
    # del 12-09 (fatto datato, §4 D2 del brief).
    # ⭐ `ESCLUSO` non conta: e' la via d'uscita, la dichiarazione dell'operatore
    # che quel documento non fa piu' parte del giro.
    # ⚠️ Si SOVRAPPONE ai tre qui sopra: un documento con una critica viva ha
    # anche l'esito `ERRORE`. Non si somma a `documenti_bloccanti_count`: il caso
    # che aggiunge e' quello con ZERO critiche vive, ed e' l'unico che prima
    # non vedeva nessuno.
    esiti_stato_esecuzione_errore_count: int
    # ═══ L'UNDICESIMA COLONNA (2026-09-19, D-V1 di Tid: «la regola va a DB») —
    # IL VERDETTO ═══
    # `fermo` = (fatture_critical + lotto_critical) > 0 OR
    #           fatture_stato_esecuzione_errore > 0 OR
    #           esiti_stato_esecuzione_errore > 0
    # — ma la formula vive in `vendite.vw_lotti_segnalazioni_summary`, la sede
    # unica letta anche dal presidio `dbops.vw_lotti_fermi_da_guardare`, e qui
    # si TRASPORTA. Fino a quel giorno `LottoSegnalazioniService` la ricalcolava
    # dai tre addendi: due sedi per lo stesso verdetto, e la divergenza sarebbe
    # stata muta — un banner verde su un lotto che il digest chiama fermo.
    # ⚠️ I dieci conteggi sopra restano per la FRASE del banner, non per la
    # decisione. Su un lotto fuori perimetro: zeri e `fermo = false`.
    fermo: bool


class LottoSegnalazioneRow(TypedDict):
    # Una segnalazione del lotto, nella forma in cui si LEGGE — i conteggi del
    # riepilogo dicono quante sono, questa dice cosa sono.
    # Sorgente: `vendite.fn_list_lotto_segnalazioni` (L2), che unisce le due
    # origini e compone gia' documento e importo.
    #
    # ⚠️ I nomi sono quelli che il seed della lista 47 dichiara come
    # `campo_sorgente`: se divergono, la colonna si spunta a catalogo e resta
    # vuota a video.
    #
    # `riga_key`: chiave di riga per il rendering. Serve perche' `data_ora` NON
    # e' univoco — misurato, sei segnalazioni con lo stesso microsecondo — e il
    # solo `id` nemmeno, dato che le due origini hanno sequenze indipendenti.
    riga_key: str
    origine: str              # 'FATTURA' | 'LOTTO'
    data_ora: str | None
    livello: str              # 'C' | 'W' | 'I'
    messaggio: str | None
    error_code: str | None
    fase: str | None          # solo origine LOTTO
    fattura_id: int | None
    documento_display: str | None   # NULL sulle righe LOTTO
    importo: str | None             # NULL sulle righe LOTTO
    disabilitato: bool        # ritirata: e' il filtro, non la colonna
    # ⭐ La segnalazione appartiene all'ULTIMA corsa di pipeline (D-6): un job
    # contiene piu' step e uno step piu' task, e senza questo flag una
    # segnalazione di tre giri fa si legge come se fosse di adesso.
    job_corrente: bool
    # ⭐ IL BERSAGLIO: su QUALE cosa l'errore punta — `[{"type", "id"}]`, gli
    # stessi nomi dell'envelope, cosi' la scheda e il toast disegnano il gesto
    # con un resolver solo. `None` = nessuna destinazione, che e' il caso
    # normale (e oggi tutte le righe di origine `LOTTO`).
    # ⛔ Da non confondere con `fattura_id`: quello e' il documento che ha
    # FALLITO, questo e' dove l'operatore deve andare. Sul caso collaudato sono
    # due fatture diverse.
    target: list[dict[str, str]] | None
    # ⭐ DI QUALE DOCUMENTO parla la segnalazione (brief-db-uscita-documento-dal-giro
    # §4.1). ⚠️ `None` = e' del GIRO — emittente non risolto, configurazione
    # mancante — e NON e' un buco: e' la meta' sana del vocabolario. Le due
    # famiglie hanno vie d'uscita diverse, e questa colonna e' cio' che le separa.
    # ⛔ Sul ramo FATTURA e' sempre `None`: una bozza puo' coprire piu' documenti,
    # quindi una segnalazione appesa alla fattura non ne nomina uno.
    gruppo_key: str | None
    # ⭐ Il motivo del pulsante spento, dalla `fn_check_*` — la stessa con cui il
    # database rifiuta. ⚠️ `None` su una riga CON documento = azione ammessa; su
    # una riga del giro non significa niente, perche' li' non e' stato chiesto.
    uscita_blocco_reason: str | None
    uscita_blocco_reason_key: str | None
    # ⭐ IL DOCUMENTO COME LO LEGGE UNA PERSONA: `ORD0036004` invece di
    # `ORDINE_VENDITA:<uuid>`. ⛔ Non sostituisce `gruppo_key`, che resta e serve
    # al PULSANTE: i due hanno destinatari diversi, e l'unico che si vede e'
    # questo (la colonna della chiave e' spenta a catalogo, D-7).
    # ⚠️ `None` = la segnalazione e' del GIRO — lo stesso NULL di `gruppo_key`,
    # non un'identita' che non si e' risolta.
    riferimento: str | None


class LottoTaskRunRow(TypedDict):
    id: int
    lotto_id: int
    pipeline_id: int | None
    stato_doc_fiscale_id: int | None
    task_code: str
    fase: str | None
    tentativo: int
    task_stato: str
    started_at: str | None
    ended_at: str | None
    error_code: str | None
    error_message: str | None
    meta: dict[str, Any]
    giro_corrente: bool


class LottoFattureRow(TypedDict):
    id: int
    lotto_id: int
    fattura_id: int
    stato_sdi_id: int | None
    stato_sdi_descrizione: str | None
    stato_doc_fiscale_id: int | None
    stato_doc_fiscale_descrizione: str | None
    stato_doc_fiscale_codice: str | None
    stato_esecuzione: str
    numero: int | None
    serie: str | None
    data: str | None
    billing_account_id: int
    totale_doc: str | None
    totale_a_pagare: str | None
    soggetto_id: int
    ragione_sociale_completa: str | None
    id_fiscale_univoco_cf_piva: str | None
    # ⭐ Il numero documento composto dalla SEDE UNICA
    # (`vendite.fn_numero_documento_fattura`, 20260829-15): `numero - serie`,
    # senza anno. NULL se non ancora numerata — il ripiego lo sceglie chi rende.
    numero_documento: str | None
    # Natura del documento (FATTURA | NOTA_CREDITO | NOTA_DEBITO): un lotto ne
    # puo' contenere di diverse, quindi «N fatture» e' «N documenti».
    natura_doc_codice_interno: str | None
    natura_doc_descrizione: str | None
    # ⭐ L'ULTIMA segnalazione VIVA della fattura, DALLE PIU' GRAVI (D-6):
    # tutti i livelli, non solo i critici, e a parita' vince la gravita' prima
    # della data. NULL quando non ce n'e'. `stato_esecuzione` dice CHE la riga
    # e' fallita; questi dicono perche', quando e con quale codice —
    # l'informazione che prima viveva solo nel toast del momento.
    # ⚠️ I nomi sono quelli che il seed dichiara come `campo_sorgente`: se
    # divergono, la colonna si spunta a catalogo e resta vuota a video.
    errore_codice: str | None
    errore_messaggio: str | None
    errore_quando: str | None
    # ⚠️ Fuori dal seed, ma nel payload: senza il livello il frontend non puo'
    # distinguere un avviso da un errore e mostrerebbe l'icona rossa su
    # entrambi. Stesso ruolo di `natura_doc_codice`.
    errore_livello: str | None
    # ⭐ IL BERSAGLIO dell'errore: su QUALE cosa, per disegnare un gesto invece
    # di far ricopiare un id a mano. Forma `[{"type": ..., "id": ...}]`, gli
    # stessi nomi dell'envelope. NULL quando l'errore non ne porta — che e' il
    # caso normale, non un difetto.
    errore_bersagli: list[dict[str, str]] | None
    # ⭐ CAPABILITY DI RIGA — «questa fattura si puo' riportare in
    # lavorazione?» (F5, 2026-08-31). Permesso => nascondi, stato =>
    # disabilita COL MOTIVO: qui e' sempre il secondo caso.
    # ⛔ La terna e' coerente per costruzione — motivo e chiave si ricavano dal
    # nome del flag — e il flag si DERIVA dal motivo (`reason IS NULL`), non si
    # calcola a parte. Il nome dice QUALE verbo blocca: su questa riga puo'
    # nascerne un secondo, e un `blocco_reason` generico li confonderebbe.
    # ⚠️ `reason` e' il codice MACCHINA del primo motivo, `reason_key` la
    # CHIAVE i18n: il testo non viaggia mai nel payload.
    can_reset_fattura: bool
    can_reset_fattura_reason: str | None
    can_reset_fattura_reason_key: str | None


class LottoGruppoRow(TypedDict):
    # UN DOCUMENTO PRESO IN CARICO DA UN LOTTO, e com'e' andato
    # (`vendite.fatturazione_lotti_gruppi`, brief-db-esito-gruppo-lotto).
    #
    # ⭐ PERCHE' NON E' `LottoFattureRow`. Quella riga si aggancia a
    # `fattura_id`: descrive un documento che una fattura l'ha prodotta. Un
    # documento che cade PRIMA — al pull delle attivita' dalla commessa — non
    # ha nessuna fattura a cui appendersi, e finora non compariva da nessuna
    # parte. Questa e' la grana in cui esiste comunque.
    # ⚠️ Le due NON sono in corrispondenza 1:1 nemmeno quando tutto va bene:
    # `fn_build_fattura_key` puo' raccogliere piu' gruppi nello stesso
    # documento. Sono due domande diverse, non due viste della stessa.
    #
    # ⭐ LA RIGA E' L'UNIONE DI DUE FATTI (rev 2026-09-07): il PERIMETRO
    # (`fatturazione_lotti_gruppi` — che cosa il lotto doveva lavorare, e lo
    # dichiarano i soli giri mirati) e l'ESITO (`fatturazione_lotti_esiti` —
    # com'e' andata, e c'e' su entrambi i tipi di giro). Nessuno dei due da solo
    # risponde: il primo lascia muti i giri di massa, il secondo perde i
    # documenti dichiarati e non ancora tentati.
    # ⛔ Per questo NON c'e' un `id`: la riga non e' una riga di tabella. La
    # chiave e' il DOCUMENTO dentro il lotto, cioe' `gruppo_key`.
    # La chiave di dominio del gruppo, `<sorgente>:<uid>` oppure
    # `MAN:<commessa>`. E' anche il RIPIEGO a video quando l'identita' non si
    # risolve piu': una riga senza nome e' peggio di una riga con la chiave.
    gruppo_key: str
    # Vocabolario chiuso `PENDING` · `RUNNING` · `COMPLETED` · `ERRORE`,
    # identico a quello delle fatture del lotto (D-2 del brief): due colonne
    # che rispondono alla stessa domanda a due livelli non possono parlare due
    # lingue.
    # ⚠️ `None` = «nessuno l'ha detto» — il documento e' nel perimetro ma non e'
    # stato tentato, oppure il giro e' anteriore al tracciamento. NON e' «andato
    # bene», e chi rende deve tenerli distinti.
    # ⭐ Sulla tabella degli esiti la colonna e' NOT NULL apposta: la riga NASCE
    # quando qualcuno lo dice, quindi il non-detto e' l'ASSENZA della riga.
    # Il `None` qui viene dalla LEFT JOIN, non da uno stato di mezzo.
    stato_esecuzione: str | None
    errore_codice: str | None
    errore_messaggio: str | None
    errore_quando: str | None
    # ═══ L'IDENTITA', risolta dalla vista di competenza sul mese del lotto ═══
    # ⚠️ Tutte opzionali, e il caso vuoto e' reale: il lavoro di quel gruppo
    # puo' essere stato preso da un altro giro o essere uscito dal mese, e
    # allora la vista non lo espone piu'. La riga resta — con il suo esito e la
    # sua chiave — perche' e' proprio quella per cui questa lista esiste.
    riferimento: str | None
    tipo_gruppo: str | None
    documento_apribile: bool | None
    documento_id: int | None
    # ⭐ LA COMMESSA DA CORREGGERE: nel caso vero il fallimento non era un
    # difetto del programma ma un dato mancante sulla commessa, e senza questo
    # id l'operatore sa di avere un problema e non sa dove andare.
    # ⚠️ Valorizzata SOLO quando il gruppo ne ha una sola. La chiave di un
    # gruppo-documento non contiene la commessa, quindi due commesse sullo
    # stesso documento sono ammesse per costruzione: `commesse_n` dice quante
    # sono, e offrirne una a caso sarebbe una scommessa travestita da regola.
    commessa_id: int | None
    commessa_codice: str | None
    commesse_n: int
    # ═══ L'USCITA DAL GIRO (brief-db-uscita-documento-dal-giro, 2026-09-08) ═══
    # ⭐ `None` su tutte e tre finche' il documento e' dentro. Il motivo lo
    # scrive l'operatore ed e' OBBLIGATORIO (D-5): su una riga `ESCLUSO` c'e'
    # sempre. Il timbro (`uscita_quando`/`uscita_da`) lo mette un trigger dalla
    # GUC, non il chiamante — e non riusa `data_update`/`user_update`, che
    # qualunque aggiornamento successivo riscriverebbe.
    uscita_motivo: str | None
    uscita_quando: str | None
    uscita_da: str | None
    # ⭐ IL MOTIVO DEL PULSANTE SPENTO, prodotto da
    # `script.fn_check_documento_escludibile_da_giro` — la STESSA funzione che
    # la madre chiama per rifiutare. ⚠️ `None` = azione AMMESSA.
    # ⛔ Il TESTO non viaggia: viaggia la chiave i18n (§12.5.5).
    uscita_blocco_reason: str | None
    uscita_blocco_reason_key: str | None
    # ⭐ Quanti ALTRI documenti verrebbero via insieme, perche' condividono la
    # bozza (D-2b). Va detto PRIMA, nella conferma — non e' un motivo che
    # rifiuta.
    # ⚠️ `None` NON e' `0`: significa «non e' stato chiesto», perche' l'azione
    # su quella riga e' bloccata e la conferma non si aprirebbe mai.
    n_trascinati: int | None


class LottoListRow(TypedDict):
    id: int
    codice: str
    competenza_mese: str | None
    tipo_lotto: str
    utility_id: int | None
    utility_descrizione: str | None
    stato_lotto: str
    stato_operativo: str
    stato_doc_fiscale_id: int | None
    stato_doc_fiscale_descrizione: str | None
    # Codice stabile (codice_interno) dello stato doc fiscale: i gate FE usano
    # SEMPRE il codice, mai la descrizione display (lezione B-4). Es. 'EMESSA'
    # abilita «Rendi definitive» (C-4).
    stato_doc_fiscale_codice: str | None
    tipo_doc_fiscale_id: int
    tipo_doc_fiscale_descrizione: str | None
    area_geografica_id: int | None
    area_geografica_descrizione: str | None
    emittente_soggetto_ruolo_id: int | None
    # La PK dell'emittente (2026-09-27): il lasciapassare del cancello di
    # perimetro per le liste aperte dal drawer del lotto, che lo chiedono come
    # `emittente_fiscale_id`. ⚠️ Non e' `emittente_soggetto_ruolo_id`.
    emittente_fiscale_id: int | None
    # ⭐ Le `action_key` dei passaggi manuali che l'operatore della sessione puo'
    # fare dallo stato del lotto (`script.fn_doc_azioni_permesse`, §15.14): il
    # kebab propone un verbo di stato solo se compare qui. Il permesso, non il
    # verdetto: le precondizioni restano del dettaglio.
    azioni_permesse: list[str]
    # Si ristampa da qui? Lo stesso predicato del gate di `ristampa_lotto`
    # (`STATO_DEFINITIVA`): il kebab lo legge invece di confrontare il codice.
    ristampabile: bool
    data_insert: str | None
    user_insert: str
    # Ragione sociale dell'emittente (P-4, Fase E). ⚠️ La ragione sociale e non
    # `emittente_soggetto_ruolo_id`, che pure c'e' due righe sopra: un id a
    # video non dichiara l'emittente, sposta l'ambiguita' di un passo.
    emittente_ragione_sociale: str | None
    # ⭐ C'e' almeno UN documento in errore grave nel dettaglio del lotto: basta
    # uno ad accendere la spia sulla riga di lista. SE, non quanti — il numero
    # e il motivo stanno nel drawer, scheda «Segnalazioni».
    # Quanti documenti contiene il lotto e quanto valgono. ⚠️ `totale_documenti`
    # e' una STRINGA: un totale fiscale non passa da un binario a virgola
    # mobile. Zero e' un totale valido (lotto senza documenti), non un vuoto.
    n_fatture: int
    totale_documenti: str
    # ⭐ Quanti documenti il lotto ha PRESO IN CARICO e quanti sono ANDATI A
    # BUON FINE (2026-09-12) — contati sugli ESITI (`fatturazione_lotti_esiti`),
    # non sulle fatture: le fatture spariscono con l'annullo e possono essere
    # meno dei presi anche a giro riuscito (fusioni). `ESCLUSO` non conta fra i
    # presi: e' la dichiarazione dell'operatore che il documento e' uscito dal
    # giro. Il client mostra `completati/presi` SOLO quando differiscono: su un
    # lotto senza esiti (giri precedenti al 07-09) sono zero e zero.
    n_presi_in_carico: int
    n_esiti_completati: int
    ha_errori_gravi: bool
    # ⭐ Lotto riportato in lavorazione e step non ancora rifatto. Non e' uno
    # stato: e' un SEGNALE di un giro solo (`vendite.fatturazione_lotti.riaperto_il`,
    # spento dal runner appena lo onora). Esiste per la presentazione — sul
    # lotto riaperto la prossima esecuzione RIFA' lo step corrente invece di
    # avanzare, e il lotto resta in DRAFT.
    riaperto: bool
    # ⭐ La data documento DICHIARATA sul lotto (brief numerazione, DB-4).
    # ⚠️ `None` non vuol dire «nessuna data»: vuol dire «nessuna dichiarazione»,
    # e allora la data la decide la politica del registro
    # (`OGGI` o `FINE_MESE_COMPETENZA`) quando la testata nasce. Le due cose non
    # vanno confuse a video — un vuoto qui e' «non deciso», non «assente».
    data_documento: str | None
    # ⭐ Lo stato fiscale del lotto CONGELA il documento
    # (`config.stati_doc_fiscale.congela_fiscale`): e' la soglia oltre la quale
    # la pipeline non ha piu' niente da fare, qualunque sia l'esito dell'ultimo
    # giro. Non e' un codice: e' la PROPRIETA' che decide, cosi' uno stato nuovo
    # a catalogo entra nel gate senza toccare il frontend.
    # ⚠️ `None` = il lotto non ha uno stato fiscale (il JOIN e' LEFT). Vale
    # «non lo so», e chi legge deve essere fail-closed.
    stato_congela_fiscale: bool | None


class EsitoMarcaturaGruppi(TypedDict):
    """Consuntivo di `vendite.fn_segna_esito_gruppo_lotto` (changeSet `-20`).

    ⭐ TRE numeri e non uno, ed e' la ragione per cui la firma e' cambiata: lo
    zero del marcatore aveva tre cause diverse e ne raccontava una sola.

    ⚠️ Prima la funzione tornava un `integer`. Chi legge per posizione o si
    aspetta uno scalare NON fallisce in modo utile: `SELECT fn(...)` su una
    `RETURNS TABLE` a tre colonne consegna una tupla.
    """

    # Documenti che hanno ricevuto l'esito: il caso normale.
    marcati: int
    # ⭐ Documenti SALTATI perche' gia' usciti dal giro. `> 0` non e' un
    # difetto: e' il motivo per cui il verbo «togli dal giro» esiste, e prima
    # del `-18` era il caso che faceva CADERE l'intero statement — quindi
    # lasciava senza esito anche i documenti SANI della stessa commessa.
    usciti: int
    # ⚠️ Documenti che esistono ma non appartengono al perimetro di QUESTO
    # lotto. Non nasce da questo difetto: c'era gia', nascosto nello stesso
    # zero. `> 0` resta sospetto e va detto.
    fuori_perimetro: int


class EsclusioneDocumentoDaGiroResult(TypedDict):
    """Consuntivo di `vendite.fn_escludi_documento_da_giro`.

    ⚠️ I due numeri che l'operatore NON si aspetta sono `fatture_cancellate` e
    `gruppi_riaperti`: una bozza puo' coprire piu' documenti, quindi togliere A
    puo' portare via anche B — che torna «da emettere» e si fattura al giro
    dopo. Chi non li mostra li nasconde (D-2b del brief).
    ⭐ `gruppi_riaperti` porta le CHIAVI e non solo il conteggio: la conferma
    deve poterli NOMINARE, e un numero da solo non si verifica.
    """

    lotto_id: int
    gruppo_escluso: str
    # Bozze pre-fiscali cancellate. Puo' essere 0: un documento caduto al pull
    # una fattura non l'ha mai avuta.
    fatture_cancellate: int
    # Attivita' di commessa tornate NON_EMESSA e quindi rifatturabili.
    attivita_riemesse: int
    # I documenti TRASCINATI dalla cancellazione della bozza condivisa: tornano
    # a `PENDING`, non a `ESCLUSO` — non sono usciti da niente.
    gruppi_riaperti: list[str]
    n_gruppi_riaperti: int


class EsitoDataDocumento(TypedDict):
    """Esito di `vendite.fn_imposta_data_documento_lotto`.

    ⚠️ I tre numeri non sono decorazione: `saltate_numerate` e
    `rate_rigenerate` sono le due conseguenze che chi dichiara la data NON si
    aspetta — un lotto numerato a meta' e delle scadenze che si sono spostate.
    Chi non le mostra le nasconde.
    """

    # Fatture del lotto a cui la data e' stata riscritta.
    aggiornate: int
    # Fatture gia' numerate, che non si toccano: contate, non fatte fallire.
    saltate_numerate: int
    # Piani rate rigenerati sulla data nuova (solo dove un piano esisteva gia').
    rate_rigenerate: int


class CommessaEmitResult(TypedDict):
    total_candidate: int
    inserted_rows: int
    updated_rows: int


class CommessaEmittibileLane(TypedDict):
    # Terna (emittente, tipo_doc_fiscale, utility) con lavoro pronto da fatturare, prodotta
    # da vendite.fn_list_emittibili_lane (discovery del driver batch). `competenza_mese`
    # è la competenza (max delle righe candidate) con cui creare il lotto; le righe con
    # tipo_doc_fiscale NULL sono escluse a monte dalla funzione DB (il lotto la richiede
    # NOT NULL). utility_id è NOT NULL a monte (commesse.utility_id) → mai NULL. emittente
    # può essere NULL (commesse senza emittente, non fatturabili).
    emittente_soggetto_ruolo_id: int | None
    tipo_doc_fiscale_id: int
    utility_id: int
    competenza_mese: date
    total_candidate: int
    # QUALI gruppi fatturabili la terna copre (rev DB 2026-08-15, brief
    # emittibilità §5): chiavi da fn_build_gruppo_fatturabile_key, calcolate
    # SEMPRE dalla funzione (mai NULL «perché non calcolato»). È il dato che
    # rende parlante l'emissione PARZIALE: richiesti − union(coperti) = chi
    # resta fuori, senza ricostruire la chiave a valle.
    gruppi_coperti: list[str]


class GruppoEsitoGiro(TypedDict):
    # CONSUNTIVO di un giro di fatturazione, un gruppo fatturabile per riga
    # (da `vendite.fn_esito_gruppi_giro`, DB 2026-08-15).
    #
    # ⚠️ È una MISURA, non una previsione: sostituisce `gruppi_non_coperti`,
    # che era calcolato alla discovery e quindi poteva mentire su ciò che è
    # successo dopo (righe prese da un giro concorrente fra discovery e
    # pipeline). La funzione prende SOLO i lotti prodotti: i gruppi richiesti
    # sono già persistiti su `fatturazione_lotti_gruppi`, quindi richiesti e
    # serviti sono entrambi misurati e l'invarianza «richiesti = serviti +
    # non serviti» regge per costruzione.
    #
    # `esito`, tre valori e non due:
    #   SERVITO           almeno un'attività è finita su una fattura di questi lotti;
    #   NON_SERVITO       no, e restano righe da emettere → è il caso su cui si agisce;
    #   FATTURATO_ALTROVE no, ma non resta nulla da emettere: le righe risultano
    #                     fatturate da lotti DIVERSI. Non è un errore — è il
    #                     «lavoro preso da un altro giro» — e va detto diversamente,
    #                     altrimenti viene raccontato come un problema.
    #
    # ⚠️ È una misura VIVA, non un log immutabile: se un lotto torna a DRAFT il
    # consuntivo cambia. È corretto (la fattura non c'è più) ma non deve
    # sorprendere fra sei mesi.
    gruppo_key: str
    # False sul giro di MASSA (nessun perimetro nominale persistito): lì la
    # funzione restituisce i serviti, che è l'unico insieme di riferimento sensato.
    richiesto: bool
    esito: str
    n_attivita_fatturate: int
    n_attivita_residue: int
    lotti_serventi: list[int]
    lotti_altrui: list[int]


class GruppoDiagnosi(TypedDict):
    # Fotografia di un GRUPPO FATTURABILE richiesto da un'emissione mirata che
    # non è stato servito: serve a dire all'operatore PERCHE'. Sono fatti
    # misurati (stato della testata + conteggi righe per stato), non un verdetto:
    # l'ammissibilità resta di `fn_list_emittibili_lane`, unica sede del criterio.
    # I campi della commessa sono NULL quando il gruppo non ha nessuna riga
    # (chiave sconosciuta o già ripulita).
    #
    # Prodotto da `vendite.fn_diagnostica_gruppi_fatturabili` (DB 2026-08-15).
    # ⚠️ La grana è `(gruppo_key, commessa_id)`, non `gruppo_key`: la chiave di
    # un documento sorgente non contiene la commessa, e un documento che
    # alimentasse due commesse dava prima UNA riga con i flag collassati da
    # `bool_or` — cioè «emittibile» perché una delle due lo era.
    gruppo_key: str
    commessa_id: int | None
    commessa_codice: str | None
    # Il codice interno è per la LOGICA, la descrizione è ciò che si scrive
    # nella frase letta dall'operatore (mai il codice interno a video).
    commessa_stato_codice_interno: str | None
    commessa_stato_descrizione: str | None
    commessa_emittibile: bool | None
    n_righe: int
    n_emesse: int
    # Righe fuori gioco per proprio stato: la dashboard le NASCONDE
    # (stato_emissione ANNULLATA / approvazione RIFIUTATA sono esclusi da
    # vw_dash_competenza_attivita), ma qui vanno contate a parte — altrimenti
    # un gruppo «3 emesse + 1 annullata» non risulterebbe mai interamente
    # evaso, e una riga rifiutata verrebbe raccontata come «non ancora
    # approvata», che e' falso.
    n_annullate: int
    n_rifiutate: int
    n_non_approvate: int
    # `n_senza_tipo_doc` e' uscito dal contratto il 2026-08-15: dopo la
    # validazione del CHECK (`20260815-30`) una riga emittibile senza tipo
    # documento non puo' esistere, quindi era un contatore sempre a zero — e
    # un motivo che non puo' accendersi e' un ramo morto anche lato BE.
    n_fuori_competenza: int
    # Righe che soddisfano TUTTE le condizioni di candidatura (approvate, non
    # emesse, con tipo doc, entro il bound di competenza): se > 0 e il gruppo non
    # è entrato in nessuna terna, il blocco è sulla TESTATA (commessa non
    # emittibile) — il caso del 2026-08-03.
    n_pronte: int
    # Le CORSIE (emittente, tipo_doc_fiscale, utility) in cui ricade il lavoro
    # ancora pronto — stesso predicato di `n_pronte`, quindi conteggio ed elenco
    # non possono raccontare due cose diverse (DB rev 2026-08-15b, §11 del brief
    # emittibilità). Lista di dict con le tre chiavi; `[]` — mai None — quando
    # non c'è nulla di pronto: «nessuna corsia» e «non calcolato» devono restare
    # distinguibili.
    #
    # ⚠️ Serve INCROCIATA con le terne FALLITE del giro (che il BE ha negli
    # esiti come fatti): un gruppo la cui corsia si è rotta non è bloccato dal
    # perimetro, si riprova. Senza questo incrocio la diagnosi attribuiva a quel
    # gruppo una causa di perimetro inesistente («verificare emittente e
    # utility», che sono a posto).
    #
    # ⚠️ È un array e non tre campi: `tipo_doc_fiscale_id` sta sulla RIGA, quindi
    # lo stesso gruppo può ricadere su più corsie.
    terne_pronte: list[dict[str, Any]]


class CommessaStatoResult(TypedDict):
    # Stato testata + flag di governance (da vendite.stati_commessa)
    stato_commessa_id: int
    stato_commessa: str
    chiude_commessa: bool
    emittibile: bool
    modificabile: bool
    # Config testata
    policy_fatturazione: str | None
    fatturazione_immediata: bool | None
    priorita_operativa: str | None
    billing_account_id: int | None
    utility_id: int | None
    emittente_soggetto_ruolo_id: int | None
    # Contatori righe commesse_attivita
    total_attivita: int
    total_approvate: int
    total_non_approvate: int
    total_emesse: int
    total_non_emesse: int
    total_prezzo_da_riallineare: int
    last_update: str | None
    # Identificazione testata (brief-db-guard-uscita-commessa D6): codice della
    # COMMESSA (c.codice, non lo stato) + ragione sociale cliente. Il drawer li
    # usa per correlarsi alla lista (che mostra commessa_codice) invece di #<PK>.
    commessa_codice: str | None
    cliente_display: str | None


class CommessaTestataRow(TypedDict):
    # La testata LEGGIBILE della commessa (Blocco C di brief-db-modifiche-certe-
    # ciclo-vendita-e-articolo): cio' che `fn_get_commessa_stato` non espone e
    # `CommesseRepository.get_commessa_testata` legge da `vendite.commesse`.
    descrizione: str | None
    # NOT NULL a DB (default `script.fn_data_operativa()`): mai None.
    data_apertura: date
    responsabile_risorsa_umana_id: int | None
    # Nome della persona da `anagrafiche.vw_risorse_umane_dettaglio`; None
    # senza responsabile.
    responsabile_display: str | None


class CommessaPushLogRow(TypedDict):
    id: int
    run_at: str
    dry_run: bool
    source_types: list[str] | None
    risultato: dict[str, Any] | None
    stato: str
    durata_ms: int | None


# ── Preventivi vendita ──


class PreventivoListRow(TypedDict):
    id: int
    uid: str
    numero: str
    rev: int
    is_attiva: bool
    data: str
    stato_doc_preventivo_id: int
    stato_codice: str
    stato_descrizione: str
    billing_account_id: int | None
    ba_utility_id: int | None
    soggetto_id: str | None
    cliente_denominazione: str | None
    emittente_fiscale_id: int | None
    utility_id: int
    istanza_utility_id: int | None
    totale_imponibile: str | None
    totale_iva: str | None
    totale_documento: str | None
    valuta_id: int | None
    valuta_codice: str | None
    termine_pagamento_id: int | None
    termine_pagamento_descrizione: str | None
    validita_dal: str | None
    validita_al: str | None
    competenza_mese: str | None
    fatturazione_immediata: bool
    storicizza: bool
    data_insert: str | None


class CommessaRegistroEventoRow(TypedDict):
    # Un evento del REGISTRO di una riga di commessa
    # (`vendite.commesse_attivita_log`): risponde a «perche' questa riga e'
    # cosi'» — chi, quando, con quale motivo.
    #
    # ⚠️ `evento` e' a vocabolario APERTO e lo possiede il database: oggi sei
    # valori, domani di piu'. Qui non se ne dichiara nessuno e non si valida —
    # chi rende risolve l'etichetta con ripiego sul codice grezzo, cosi' un
    # evento nuovo si vede invece di sparire.
    id: int
    commessa_attivita_id: int
    evento: str
    # Il payload dell'evento, COM'E'. La forma cambia per evento e appiattirla
    # nel backend vorrebbe dire rifarlo a ogni evento nuovo.
    dettaglio: dict[str, Any]
    # ⭐ Estratto a parte perche' e' l'unica chiave che piu' eventi condividono
    # ed e' la frase che l'operatore sta cercando.
    motivo: str | None
    data_insert: str | None
    user_insert: str | None
    # Contesto della riga: senza, un elenco di eventi non dice SU COSA sono
    # successi. Arrivano dal JOIN che e' anche il cancello di scope.
    segment_key: str | None
    stato_emissione: str | None
    tipo_movimento: str | None
    articolo_codice: str | None
    articolo_descrizione: str | None


class PreventivoDetailRow(TypedDict):
    id: int
    uid: str
    numero: str
    rev: int
    # ⭐ Tre domande diverse sulla stessa riga: il consumatore SCEGLIE, non deduce.
    # Il perche' di ciascuna, con l'esempio che le distingue, sta accanto all'SQL
    # che le proietta — `PreventiviRepository.get_preventivo`. ⚠️ Non si ricopia
    # qui: due copie di una spiegazione divergono come due copie di codice, e
    # quella accanto alla query e' quella che si legge quando serve.
    is_attiva: bool
    is_superata: bool
    has_next_revision: bool
    data: str
    stato_doc_preventivo_id: int
    stato_codice_interno: str
    stato_codice: str
    stato_descrizione: str
    billing_account_id: int | None
    soggetto_ruolo_id: int | None
    cliente_denominazione: str | None
    utility_id: int
    utility_descrizione: str | None
    istanza_utility_id: int | None
    valuta_id: int | None
    valuta_codice: str | None
    termine_pagamento_id: int | None
    termine_pagamento_descrizione: str | None
    validita_dal: str | None
    validita_al: str | None
    competenza_mese: str | None
    fatturazione_immediata: bool
    totale_imponibile: str | None
    totale_iva: str | None
    totale_documento: str | None
    emittente_fiscale_id: int | None
    emittente_fiscale_codice: str | None
    # Ragione sociale del SOGGETTO emittente (`soggetti.ragione_sociale_completa`),
    # non `emittenti_fiscali.descrizione` (etichetta interna divergente, in via di
    # eliminazione — brief `brief-emittente-ragione-sociale-dal-soggetto.md`).
    # Rinominata da `emittente_fiscale_descrizione` il 2026-08-03 (piano
    # PrimeVue 5, registro), in pari con viste e seed liste.
    emittente_ragione_sociale: str | None
    ba_ha_contratto_attivo: bool
    storicizza: bool
    meta: dict[str, Any]
    data_insert: str | None
    user_insert: str
    data_update: str | None
    user_update: str | None


class PreventivoRigaComponenteRow(TypedDict):
    id: int
    riga_preventivo_id: int
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita: str
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    qta_operativa: str | None
    prezzo_unitario: str
    iva_id: int | None
    iva_codice: str | None
    iva_aliquota: str | None
    origine_prezzo: str
    prezzo_resolver_context: dict[str, Any] | None
    stato_approvazione_prezzo: str | None
    pratica_approvazione_prezzo_id: int | None
    meta: dict[str, Any]
    ordine: int | None
    attivo: bool
    obbligatorio: bool
    esposizione_in_fattura: str  # codice di config.esposizioni_componente


class PreventivoRigaComponentePreviewRow(TypedDict):
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita_componente: str
    uom_id: int | None
    uom_codice: str | None
    iva_id: int | None
    prezzo_suggerito: str | None
    origine_prezzo: str | None
    resolver_error_reason: str | None
    obbligatorio: bool
    esposizione_in_fattura: str  # codice di config.esposizioni_componente


# Componente BoM di riga contratto (modello unificato 2026-05-13). Specchio
# simmetrico di `PreventivoRigaComponenteRow`, differisce solo per FK
# `riga_contratto_id` (vs `riga_preventivo_id`).
class ContrattoRigaComponenteRow(TypedDict):
    id: int
    riga_contratto_id: int
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita: str
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    qta_operativa: str | None
    prezzo_unitario: str
    iva_id: int | None
    iva_codice: str | None
    iva_aliquota: str | None
    origine_prezzo: str
    prezzo_resolver_context: dict[str, Any] | None
    stato_approvazione_prezzo: str | None
    pratica_approvazione_prezzo_id: int | None
    meta: dict[str, Any]
    ordine: int | None
    attivo: bool
    obbligatorio: bool
    esposizione_in_fattura: str  # codice di config.esposizioni_componente


# Aggregato smistamento per ramo (vw_preventivi_smistamento, sostituisce la
# vecchia vw_preventivi_stato_fatturazione — rename DB 2026-06-12,
# brief-db-smistamento-preventivi.md B). `righe_in_commessa` ora conta solo
# attivita' EMESSA (predicato allineato a capability e list-fn).
class PreventivoSmistamentoRow(TypedDict):
    preventivo_id: int
    preventivo_uid: str
    righe_totali: int
    righe_merce: int
    righe_servizi: int
    righe_a_ordine: int
    righe_in_commessa: int
    righe_emesse_af: int
    righe_fatturate: int
    righe_residue: int


# ── Offerte commerciali ──
# Specchio strutturale di Contratto/ContrattoRiga/ContrattoUtility (decisioni
# §5 analisi-offerta-commerciale + brief DB 2026-05-24 step 1-4 atterrati).
# Le date/Decimal sono `str` ISO/serializzati, coerente col pattern preventivi
# e contratti (psycopg ritorna stringhe via row_to_dict).


class OffertaRow(TypedDict):
    id: int
    uid: str
    codice: str
    emittente_fiscale_id: int
    billing_account_id: int
    soggetto_ruolo_id: int
    istanza_utility_id: int
    utility_id: int
    listino_id: int
    listino_versione_id: int | None
    valore_variazione_globale: str | None
    tipo_variazione_globale: str | None
    validita_dal: str
    validita_al: str | None
    stato_doc_offerta_id: int
    revisione_numero: int
    revisione_padre_id: int | None
    data_emissione: str | None
    data_accettazione: str | None
    data_rifiuto: str | None
    data_annullamento: str | None
    motivazione_rifiuto: str | None
    meta: dict[str, Any]
    # Display fields da JOIN. Naming coerente col piano FE+BE rev. f:
    # `billing_account_display` + `utility_display` sono i campi consumati
    # dal drawer/lista (display fields backend, niente lookup client-side).
    stato_codice_interno: str
    stato_descrizione: str
    # Denormalizzazione EF (pattern preventivi): consumati da
    # `EmittenteFiscaleField` in modalita' edit per costruire la option
    # singola del Select disabled senza round-trip aggiuntivo.
    # ⚠️ `emittente_ragione_sociale` porta la RAGIONE SOCIALE del soggetto
    # emittente, non `emittenti_fiscali.descrizione` (vedi PreventivoDetailRow).
    emittente_fiscale_codice: str | None
    emittente_ragione_sociale: str | None
    ba_codice: str | None
    billing_account_display: str | None
    # ID fiscale univoco (CF persona fisica o P.IVA) del soggetto del BA.
    # Esposto via JOIN `anagrafiche.vw_soggetti_ruoli_dettaglio`.
    id_fiscale: str | None
    utility_codice: str | None
    utility_display: str | None
    listino_codice: str | None
    listino_descrizione: str | None
    listino_versione_codice: str | None
    # Riferimento al contratto generato (pattern A idempotenza). NULL se
    # l'offerta non e' ancora stata pushata (o non e' ACCETTATA). Coppia
    # stabile id + numero: il FE puo' linkare al ContrattoDrawer e mostrare
    # il dialog parlante post-E_OFFERTA_CONTRATTO_GIA_GENERATO.
    contratto_id: int | None
    contratto_numero: str | None
    # Capability blob da `script.fn_available_actions_offerta` merged sul
    # detail in `OfferteService.get_offerta` (data-driven 2026-05-26).
    # Il FE consuma questi campi con `useEntityCapabilities` +
    # `mapAvailableActionsToDrawerActions` senza ricalcolare la state
    # machine: la verita' della transizione vive solo in DB.
    # `available_actions` e' lista di dict opachi (key/target_state/label_key/
    # requires_confirm/requires_motivazione) — Any per non vincolare il
    # TypedDict a una sotto-shape che il BE puo' arricchire. Icona e colore
    # non viaggiano: li sceglie il frontend dal `key` (`core/aspettoAzioni.js`).
    available_actions: list[dict[str, Any]]
    can_change_state: bool
    can_edit_testata: bool
    can_edit_eccezioni: bool
    can_edit_utility: bool
    can_create_revisione: bool
    can_push_contratto: bool
    can_push_contratto_reason: str | None
    can_push_contratto_reason_key: str | None
    non_editable_fields: list[str]
    # Audit
    data_insert: str
    user_insert: str
    data_update: str | None
    user_update: str | None


class OffertaEccezioneRow(TypedDict):
    id: int
    offerta_id: int
    articolo_id: str
    articolo_codice: str | None
    articolo_descrizione: str | None
    is_composito: bool
    tipo_eccezione: str
    tipo_erogazione: str | None
    # NULL solo sull'ESCLUSIONE, che non porta dati di fatturazione (2026-10-04).
    fonte_quantita_attesa: str | None
    periodicita: str | None
    generazione_canone: str | None
    prezzo_unitario: str | None
    quantita: str | None
    qta_operativa: str | None
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    ordine: int | None
    attivo: bool
    meta: dict[str, Any]
    componenti: list[dict[str, Any]]


class OffertaEccezioneComponenteRow(TypedDict):
    id: int
    eccezione_offerta_id: int
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita: str
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    qta_operativa: str | None
    prezzo_unitario: str
    iva_id: int | None
    iva_codice: str | None
    iva_aliquota: str | None
    origine_prezzo: str
    prezzo_resolver_context: dict[str, Any] | None
    stato_approvazione_prezzo: str | None
    pratica_approvazione_prezzo_id: int | None
    meta: dict[str, Any]
    ordine: int | None
    attivo: bool
    obbligatorio: bool
    esposizione_in_fattura: str  # codice di config.esposizioni_componente


class OffertaUtilityRow(TypedDict):
    id: int
    offerta_id: int
    istanza_utility_id: int
    utility_id: int
    utility_codice: str | None
    utility_descrizione: str | None
    istanza_dati_precontrattuali_id: int | None
    tipo_utenza_id: int | None
    tipo_utenza_codice: str | None
    tipo_utenza_descrizione: str | None
    classe_utenza_id: int | None
    classe_utenza_codice: str | None
    classe_utenza_descrizione: str | None
    param_1_num: str | None
    param_2_txt: str | None
    meta: dict[str, Any]


class NotaOffertaRow(TypedDict):
    id: int
    offerta_id: int
    eccezione_id: int | None
    autore: str | None
    testo: str
    meta: dict[str, Any]
    data_insert: str
    user_insert: str
    data_update: str | None
    user_update: str | None


class OffertaPushResult(TypedDict):
    # In attesa step 8 brief DB (fn_push_offerta_a_contratto). TypedDict
    # definito per stabilizzare la forma di ritorno futura.
    contratto_id: int
    contratto_codice: str
    sorgente_uid: str


class DashApertoRiepilogoRow(TypedDict):
    # Cella area × fase del serbatoio pre-commessa (vw_dash_aperto_riepilogo v2,
    # stock senza asse temporale — il pivot area/fasi e' del service). Perimetro
    # aperti-non-chiusi lato vista (DL-15): via n_aperti/valore_transitato.
    # valore_totale NULL per le aree a conteggi (OFFERTE/CONTRATTI, DL-11).
    area: str
    fase: str
    n_documenti: int
    valore_totale: str | None


class DashApertoDocumentoRow(TypedDict):
    # Riga drill-down del serbatoio pre-commessa (vw_dash_aperto_documenti v2:
    # 4 aree documento, perimetro aperti-non-chiusi — is_transitato IS DISTINCT
    # FROM true AND fase<>CHIUSO, DL-14/15). anzianita_giorni derivata in SELECT
    # (GREATEST(fn_data_operativa() - data_riferimento, 0)) come il gemello Backlog,
    # allinea la lettura al filtro "aperti da oltre N giorni" (DL-17).
    area: str
    documento_id: int
    documento_uid: str | None
    codice: str | None
    cliente_display: str | None
    fase: str | None
    stato_codice_interno: str | None
    stato_codice: str | None
    valore_totale: str | None
    unita_totali: int | None
    anzianita_giorni: int
    motivo_fermo: str | None
    data_riferimento: str | None
    # Ragione sociale dell'emittente (P-4, Fase E del brief
    # perimetro-emittente): colonna di catalogo «disponibile e spenta»,
    # serve a chi ha piu' di un emittente davanti. La chiave e' il
    # `campo_sorgente` dichiarato in `ui.lista_colonna`.
    emittente_ragione_sociale: str | None


class DashCompetenzaMensileRow(TypedDict):
    # Riga aggregata Lente 1 Competenza (vw_dash_competenza_mensile, formato
    # lungo mese × stadio × stato fattura × TIPO MOVIMENTO — il pivot ai 4
    # blocchi e' del service). stato_fattura_* NULL per gli stadi non fatturati.
    # ⚠️ `tipo_movimento` e' entrato nella grana il 2026-08-20 (changeSet
    # 20260820-07) e la cardinalita' e' CAMBIATA: dove un bucket contiene
    # movimenti di natura diversa arrivano piu' righe dove prima ne arrivava
    # una. Chi accumula (i totali) non se ne accorge; chi fa `append` per riga
    # (il breakdown per stato fattura) duplicherebbe la voce.
    competenza_mese: str
    stadio: str
    stato_fattura_codice_interno: str | None
    stato_fattura_codice: str | None
    tipo_movimento: str
    n_attivita: int
    valore: str
    valore_fatturato: str
    n_in_ritardo: int
    valore_in_ritardo: str
    # ⭐ La dimensione arrivata col `20260826-55`: dentro `EMESSA_NON_FATTURATA`
    # distingue il RESIDUO (chiede un'azione) dalle tre situazioni di transito
    # (non chiedono niente). `None` sugli altri stadi.
    motivo_non_fatturata: str | None
    # ⭐ `20260909-67` — LE ATTIVITA' CHE LA CARD NON CONTA PIU'.
    # `n_attivita` e `valore` ESCLUDONO le attivita' trattenute da un lotto
    # ancora in gioco: sono lavoro che l'operatore non puo' prendere, e un
    # numero che le comprende e' una promessa che non si mantiene.
    # ⛔ Questi due non sono decorazione: un numero che cala senza dire di
    # quanto e' un numero che non si sa leggere — «non c'e' niente da fare» e
    # «c'e' lavoro che un giro sta gia' tenendo» si leggerebbero uguali.
    # Stessa forma di `ritirate_count` sul giornale e di `archiviate_count`
    # sulle code.
    n_attivita_trattenute: int
    valore_trattenuto: str


class DashCompetenzaResiduoRow(TypedDict):
    # Riga della lista dei RESIDUI (`ui.lista_definizione` 49) — le attivita'
    # che una fattura non ce l'hanno piu' e che nessun giro riprendera' da solo.
    # E' l'oggetto del verbo «Riporta da emettere».
    #
    # ⚠️ `attivita_fatturabile_id` e' la CHIAVE DEL VERBO e NON e' a catalogo:
    # non si mostra, si passa a `vendite.fn_riporta_attivita_da_emettere`.
    # E' dichiarato opzionale perche' il tipo descrive la vista, dove la colonna
    # e' nullable (il caso `SENZA_ATTIVITA_FATTURABILE`); su questa lista, che
    # filtra `motivo_non_fatturata = 'RESIDUO'`, e' sempre valorizzato — ma
    # dichiararlo `int` qui direbbe una cosa piu' forte di quella che la
    # sorgente garantisce.
    attivita_fatturabile_id: int | None
    commessa_attivita_id: int
    commessa_id: int
    commessa_codice: str | None
    cliente_display: str | None
    articolo_codice: str | None
    articolo_descrizione: str | None
    competenza_mese: str | None
    data_attivita: str | None
    quantita: str | None
    valore: str | None
    # ⛔ Il lotto di PROVENIENZA, non `lotto_id`: quello nasce dalla catena della
    # fattura, e su un residuo la fattura non c'e' — sarebbe NULL proprio sulle
    # righe di questa lista. Il legame vero e' `af.lock_batch_id`.
    lotto_provenienza_id: int | None
    lotto_provenienza_codice: str | None
    motivo_non_fatturata: str | None
    emittente_ragione_sociale: str | None


class DashCompetenzaAttivitaRow(TypedDict):
    # Riga drill-down attivita' Lente 1 (vw_dash_competenza_attivita + decode
    # articolo via JOIN). Campi fattura NULL per gli stadi non fatturati;
    # data_emissione/emessa_in_ritardo NULL se non emessa.
    commessa_attivita_id: int
    commessa_id: int
    commessa_codice: str | None
    cliente_display: str | None
    articolo_id: str | None
    articolo_codice: str | None
    articolo_descrizione: str | None
    data_attivita: str | None
    quantita: str | None
    stadio: str
    stato_approvazione: str | None
    stato_emissione: str | None
    valore: str | None
    data_emissione: str | None
    emessa_in_ritardo: bool | None
    sospesa: bool | None
    posticipa_al: str | None
    fattura_id: int | None
    fattura_anno: int | None
    fattura_serie: str | None
    fattura_numero: int | None
    # Lotto della fattura (NULL fuori dagli stadi con fattura in lotto): abilita
    # l'atterraggio contestuale sul LottoDrawer dal drill-down (B-5).
    lotto_id: int | None
    stato_fattura_codice_interno: str | None
    stato_fattura_codice: str | None
    valore_fatturato: str | None
    fattura_critical: bool


class DashCompetenzaCommessaRow(TypedDict):
    # Riga drill-down AGGREGATA per commessa (DEC-4): una riga per commessa nel
    # perimetro corrente (competenza_mese + stadio + solo_ritardo), invece della
    # grana attivita'. Le n attivita' e gli estremi fattura restano nel drawer.
    commessa_id: int
    commessa_codice: str | None
    cliente_display: str | None
    n_attivita: int
    n_in_ritardo: int
    valore_tot: str | None
    valore_fatturato_tot: str | None
    data_attivita_min: str | None
    data_attivita_max: str | None
    # Emittente della commessa (P-4, Fase E). ⚠️ E' una colonna della
    # COMMESSA, non dell'attivita': per questo entra nel GROUP BY
    # dell'aggregato senza spezzare le righe.
    emittente_ragione_sociale: str | None


class DashCompetenzaGruppoRow(TypedDict):
    # Riga dell'elenco GRUPPI FATTURABILI (vw_dash_competenza_gruppi): l'unita'
    # su cui l'operatore decide nella card «Da emettere» — un documento sorgente
    # OPPURE le righe manuali/oneri di una commessa (che documento non hanno).
    # `gruppo_key` e' la chiave costruita da fn_build_gruppo_fatturabile_key: e'
    # la STESSA che si rimanda al POST di emissione mirata, senza mapping.
    gruppo_key: str
    tipo_gruppo: str
    # «Il documento del gruppo ha una sua pagina» (`config.sorgenti.apribile`):
    # allora `tipo_gruppo` e' il codice della sorgente da cui il frontend apre
    # il documento. NULL sui gruppi SOURCELESS (oneri di commessa). Fino al
    # 2026-10-20 era `area_documento`, il plurale (`ORDINI`…), ritirato col
    # sotto-giro 2d di brief-db-grammatica-unica-documenti (G-6, L2d-1).
    documento_apribile: bool | None
    # Nome leggibile del gruppo. NON nullable, ed e' il CONTRATTO della vista, non
    # una fortuna dei dati: `riferimento` e'
    # `COALESCE(documento_numero, commessa_codice, gruppo_key)` e l'ultimo ramo e'
    # la chiave del gruppo, che esiste sempre. Dichiararlo opzionale legittimava
    # nel frontend una seconda copia della stessa catena di ripiego — tolta il
    # 2026-09-01 (brief-db-riferimento-gruppi-lateral-costosa §9 FE-2).
    # ⚠️ `documento_numero` arriva da vendite.fn_get_sorgente_documento_ref: sui
    # gruppi SOURCELESS (sorgente non `config.sorgenti.apribile`) e' NULL e qui
    # esce il codice commessa — che per quei gruppi E' il riferimento.
    riferimento: str
    commessa_id: int | None
    commessa_codice: str | None
    cliente_display: str | None
    stadio: str | None
    n_attivita: int
    valore: str | None
    ha_oneri: bool
    data_attivita_min: str | None
    data_attivita_max: str | None
    # Id di dominio del documento sorgente, per aprirne il drawer dal kebab
    # della lista (il `riferimento` e' il codice, che non basta: i drawer si
    # aprono per id). NULL sui gruppi SOURCELESS (oneri di commessa), che un
    # documento non ce l'hanno, e sui documenti fuori scope RLS.
    documento_id: int | None
    # Emittibilita' della TESTATA (stati_commessa.emittibile via vista, rev DB
    # 2026-08-04 — brief emittibilita' §3.1): False = la card mostra lavoro che
    # il motore non fatturerebbe. «Segnalare, non nascondere» (decisione Tid):
    # la riga resta in lista, marcata, e il verbo nasce disabilitato col
    # motivo. `commessa_stato_codice_interno` e' il PERCHE' per la LOGICA;
    # `commessa_stato_descrizione` (JOIN sul catalogo) e' il perche' A VIDEO —
    # mai il codice interno nell'interfaccia. Tutti NULL senza commessa.
    commessa_emittibile: bool | None
    commessa_stato_codice_interno: str | None
    commessa_stato_descrizione: str | None
    # Cliente di FATTURAZIONE (padre se c'e', altrimenti se stesso): e' il BA che
    # `fn_build_fattura_key` mette in chiave, non quello della commessa. Colonne
    # di catalogo «disponibili e spente» (D-4): il merge di
    # `ui.fn_resolve_lista_config` le aggiunge al preset con `visibile = FALSE`,
    # chi ne ha bisogno le accende. NULL quando il padre e' fuori scope RLS —
    # il gruppo resta comunque in lista, marcato «non determinabile» (D-5).
    ba_codice_fatturazione: str | None
    id_fiscale: str | None
    # Ragione sociale dell'EMITTENTE della riga (P-4, brief perimetro-emittente
    # passo 6: questa e' la lista pilota). Serve a chi ha piu' di un emittente
    # davanti — cioe' il super admin — che e' l'unico a poter vedere righe di
    # emittenti diversi affiancate: senza, non c'e' nulla a video che dica da
    # dove viene la riga, e da qui parte l'EMISSIONE MIRATA.
    # ⚠️ La ragione sociale e non `emittente_soggetto_ruolo_id`, che pure la
    # vista espone: un id a video non dichiara l'emittente, sposta l'ambiguita'
    # di un passo. Colonna di catalogo «disponibile e spenta» come le due sopra
    # (`ui.lista_colonna` codice `emittente_fiscale`, `campo_sorgente =
    # emittente_ragione_sociale` — si nomina per codice e non per id: il seed
    # puo' rinumerare, e un numero da solo non dice niente a chi legge):
    # ⛔ la CHIAVE qui deve restare identica a quel `campo_sorgente`, o la
    # colonna si spunta e resta vuota — che e' peggio di non averla, perche'
    # SEMBRA la garanzia che il flag `multi_emittente` pretende.
    emittente_ragione_sociale: str | None
    # ═══ Il SEZIONALE che il documento prendera', e la data che portera' ═══
    # (brief-db-registro-e-data-prevista-in-competenza, consegne L5/BE-1).
    #
    # ⭐ Non sono una previsione «parallela»: la vista li calcola con
    # `fn_resolve_registro_documento`, che dal 2026-08-26 e' la STESSA funzione
    # che `fn_build_fattura_key` usa per scrivere la chiave del documento vero.
    # Lista e documento non coincidono perche' due implementazioni si comportano
    # uguale, ma perche' e' un'implementazione sola.
    #
    # `registri_ids` porta TUTTI i sezionali toccati dal gruppo, e non e' una
    # ridondanza di `registro_codice`: la chiave del gruppo non contiene tipo
    # documento ne' natura — che sono colonne di RIGA — quindi un gruppo su piu'
    # sezionali e' ammesso per costruzione, non e' un'anomalia. E' anche l'asse
    # del filtro (D-5): un gruppo multi-sezionale deve comparire sotto ENTRAMBE
    # le voci, e un filtro su `registro_codice` non potrebbe farlo perche' li'
    # e' NULL.
    # ⛔ La lista degli id NON esce nel payload: serve al WHERE del filtro e
    # alla facet, che vivono entrambi nel repository. Esporla obbligherebbe a
    # scegliere se tenere i NULL che `array_agg(DISTINCT)` conserva — con i
    # NULL e' una lista scomoda, senza diverge da `registri_n` che invece li
    # conta, e due numeri che rispondono «quanti sezionali» in modo diverso
    # sono una domanda senza risposta.
    registri_n: int
    # ⚠️ NULL in DUE casi diversi, e il FE deve distinguerli:
    #   · `registri_n > 1` -> il gruppo tocca piu' sezionali: non e' «non lo so»,
    #     e' «sono piu' di uno». La frase la compone il BE (D-4), cosi' esce
    #     anche nell'export, che condivide questa stessa proiezione;
    #   · `registri_n = 0` -> non risolvibile (tipo documento non ancora scelto
    #     su una riga DA_APPROVARE: il CHECK lo pretende solo da approvata e non
    #     emessa). Cella vuota, ed e' onesto.
    registro_codice: str | None
    # Vuota dove il documento ESISTE GIA' (D-9): il join si aggancia su
    # `fattura_riga_id IS NULL`. ⚠️ Il discriminante e' la riga di fattura, non
    # lo stadio — `EMESSA_NON_FATTURATA` un documento non ce l'ha ancora.
    data_documento_prevista: str | None
    # ⭐ D3 (changeSet 20260904-48, brief-residuo-fatturabili-e-bandiere):
    # l'ULTIMO rifiuto del pull su questa commessa in questo mese, e il suo
    # motivo di dominio. `None` = nessun rifiuto noto.
    # ⛔ Non e' una colonna di `vw_dash_competenza_gruppi` ma un JOIN a
    #    `vw_dash_commesse_respinte`: quella vista ha un dipendente e non
    #    saprebbe perdere una colonna in rollback.
    # ⚠️ `respinta_motivo` vale quanto vale cio' che il pull ha scritto in
    #    `meta->>'detail'`: e' il campo che `_PullCommesseRunLogger` riempie
    #    con il motivo di dominio, non con il dump tecnico.
    respinta_il: str | None
    respinta_motivo: str | None
    # ═══ COM'E' ANDATO L'ULTIMO TENTATIVO DI FATTURARE QUESTO DOCUMENTO ═══
    # (changeSet DB `20260906-12`, brief-db-esito-gruppo-lotto R-3).
    #
    # ⭐ IL CASO CHE LE HA FATTE NASCERE. Un lotto prende in carico tre
    # documenti e ne fattura due; il terzo cade al primo passo — prima che una
    # fattura esista — e sparisce dal racconto: non e' nel lotto (non c'e'
    # nessuna fattura a cui appendersi) e qui resta fra quelli da emettere,
    # senza un segno. Sembra fatturabile.
    #
    # ⛔ IL SEGNO NON SPEGNE NIENTE (decisione di Tid, 2026-09-06): `stadio` e
    # `commessa_emittibile` restano quelli di prima. Dice «ci ho provato e non
    # ci sono riuscito», non «non e' fatturabile» — la riga resta selezionabile
    # e il verbo resta acceso, perche' il rimedio e' correggere la commessa e
    # riprovare.
    #
    # ⚠️ `None` = «nessuno l'ha detto», e NON e' «e' andata bene»: e' la verita'
    # di ogni gruppo che nessun giro ha ancora lavorato, e di tutti quelli
    # lavorati prima del 2026-09-06. Chi rende a video deve tenere distinti i
    # due casi, o un documento mai tentato si leggerebbe come uno riuscito.
    #
    # ⚠️ Il legame e' (gruppo, MESE di competenza) e il mese non e' un di piu':
    # senza, il documento di settembre erediterebbe l'errore di agosto.
    # Vocabolario chiuso, identico a quello delle fatture del lotto (D-2):
    # `PENDING` · `RUNNING` · `COMPLETED` · `ERRORE`.
    ultimo_esito: str | None
    ultimo_errore_codice: str | None
    ultimo_errore_messaggio: str | None
    ultimo_errore_quando: str | None
    # In QUALE lotto e' stato tentato. ⚠️ Il codice e non l'id: serve a
    # nominarlo in una frase («ultimo tentativo — lotto LTF-0009578»), non a
    # navigarci. Il giorno in cui servisse il salto, l'id lo deve aggiungere la
    # vista — comporlo qui vorrebbe dire una seconda lettura per una colonna.
    ultimo_lotto_codice: str | None
    # ═══ TRATTENUTO DA UN LOTTO VIVO (brief-db-documento-trattenuto-da-un-lotto-vivo)
    # ⭐ Il VERDETTO, non la materia per dedurlo: «questo documento lo sta
    # trattenendo un lotto ancora vivo, quindi non si offre due volte».
    # ⛔ NON si ricava da `ultimo_esito`: quello risponde giusto per caso —
    # misurato il 2026-09-08, due documenti su tre avevano `COMPLETED` con il
    # lotto ANNULLATO, cioe' erano liberi. Dedurlo avrebbe tenuto bloccato per
    # sempre il contenuto di ogni lotto annullato.
    # ⚠️ `None` = la riga si puo' prendere.
    emissione_blocco_reason: str | None
    emissione_blocco_reason_key: str | None
    # ⭐ Il lotto che trattiene, come BERSAGLIO: la frase dice cosa fare, il
    # bersaglio ci porta senza far ricopiare un codice a mano.
    emissione_blocco_lotto_id: int | None
    emissione_blocco_lotto_codice: str | None
    # ═══ V-1 · IL LOTTO DEL TENTATIVO, CON IL SUO STATO (2026-09-09) ════════
    # ⭐ `ultimo_lotto_codice` qui sopra diceva DOVE si e' tentato, non SE quel
    # tentativo conta ancora: a video un lotto ANNULLATO si leggeva come uno in
    # corso — rilievo di Tid sul collaudo del 09-09, dove la colonna mostrava
    # LTF-0010332 (annullato) su tre righe.
    # ⛔ Il dato NON si toglie: e' l'unica traccia che spieghi perche' il
    # documento e' tornato disponibile. Si aggiunge il fatto che mancava.
    # ⚠️ `ultimo_lotto_pre_fiscale` e' il flag su cui il frontend spegne il
    # GESTO — testo si', pulsante no: un bersaglio verso un lotto che non conta
    # piu' e' un pulsante in un vicolo cieco.
    # ⚠️ Tutte e tre `None` quando nessun giro ha ancora toccato il gruppo.
    ultimo_lotto_id: int | None
    ultimo_lotto_stato: str | None
    ultimo_lotto_pre_fiscale: bool | None


class DashCompetenzaGruppoRegistroRow(TypedDict):
    # Voce del filtro SEZIONALE della lista gruppi (facet, D-5).
    # ⚠️ L'asse e' `registri_ids`, non `registro_codice`: un gruppo che tocca due
    # sezionali va contato sotto ENTRAMBI, e con la seconda colonna sarebbe
    # invisibile a tutte e due le voci (li' e' NULL).
    # ⇒ Conseguenza dichiarata: la somma degli `n_gruppi` delle voci puo'
    # SUPERARE il numero di gruppi del perimetro. Non e' un errore di conteggio,
    # e' cio' che significa «un gruppo sta su due sezionali».
    # `registro_id` NULL = voce dei gruppi con sezionale NON RISOLVIBILE, che e'
    # l'assenza del valore e non un id sentinella (stessa forma della voce
    # «cliente non determinabile» del facet clienti).
    registro_id: int | None
    codice: str | None
    descrizione: str | None
    n_gruppi: int
    n_attivita: int


class DashCompetenzaGruppoClienteRow(TypedDict):
    # Voce del filtro CLIENTE della lista gruppi (facet). L'asse e'
    # `ba_fatturazione_id`, non la ragione sociale: lo stesso soggetto puo' avere
    # piu' alberi di billing account — anche sotto emittenti diversi — con nome e
    # codice fiscale identici, e quegli alberi finiscono su fatture DIVERSE.
    # Per questo il `ba_codice_fatturazione` sta nell'etichetta a video: e'
    # l'unico dato che li distingue (nome e id fiscale sono uguali per
    # costruzione, lo garantisce il guard padre/figlio).
    # `ba_fatturazione_id` NULL = voce «cliente non determinabile» (padre fuori
    # scope): si mostra, non si nasconde.
    ba_fatturazione_id: int | None
    cliente_display: str | None
    ba_codice_fatturazione: str | None
    id_fiscale: str | None
    n_gruppi: int
    n_attivita: int


class DashCompetenzaGruppoTipoRow(TypedDict):
    # Voce del filtro «tipo documento/sorgente» della lista gruppi, calcolata
    # SUI DATI del perimetro (facet) e non da `config.sorgenti`. Due ragioni:
    # quella tabella contiene sorgenti che non possono mai essere un gruppo
    # fatturabile (i `*_RIGA` con scope ROW_VALIDATOR, FATTURA, RESO_VENDITA) e
    # NON contiene `ONERI_COMMESSA`, che e' un valore sintetico della vista —
    # cioe' proprio il caso che si vuole poter isolare.
    tipo_gruppo: str
    documento_apribile: bool | None
    n_gruppi: int
    n_attivita: int


class DashCompetenzaGruppiRiepilogoRow(TypedDict):
    # Totali di perimetro dell'elenco gruppi: aggregano la vista di dettaglio,
    # quindi non possono divergere da essa. Vengono dal DB e non dal FE di
    # proposito: sommare la pagina corrente mostrerebbe un parziale che sembra
    # un totale.
    # ⚠️ Li calcola `get_dash_competenza_gruppi_accessori`, NON la vista
    # `vw_dash_competenza_gruppi_riepilogo` che questo commento nominava: quella
    # non applicava i filtri dell'operatore, non e' mai stata letta da qui ed e'
    # stata ritirata il 2026-09-09 (`20260909-64`).
    # ⭐ Dal 2026-09-09 i tre totali ESCLUDONO i gruppi trattenuti da un lotto
    # in gioco, e `n_gruppi_trattenuti` dichiara quanti: un numero che cala
    # senza dire di quanto e' un numero che non si sa leggere.
    n_gruppi: int
    n_attivita: int
    valore: str | None
    n_gruppi_oneri: int
    n_gruppi_trattenuti: int


class DashBacklogRiepilogoRow(TypedDict):
    # Riga contatori Lente 2 Backlog (vw_dash_backlog_riepilogo, grana
    # classe × area — il pivot per classe e' del service).
    classe: str
    area: str
    n_documenti: int
    valore_fermo_tot: str | None
    unita_ferme_tot: int
    anzianita_max_giorni: int | None


class DashBacklogDocumentoRow(TypedDict):
    # Riga lista Lente 2 Backlog (vw_dash_backlog_documenti): non-collegati
    # non-verdi per anzianita'. valore_fermo NULL per le aree a conteggi;
    # azione = hint operativo dalla lookup config.motivi_fermo.
    area: str
    competenza_mese: str | None
    documento_id: int
    documento_uid: str | None
    codice: str | None
    cliente_display: str | None
    valore_fermo: str | None
    unita_ferme: int | None
    motivo_fermo: str
    classe: str
    azione: str | None
    data_riferimento: str | None
    anzianita_giorni: int | None
    stato_codice_interno: str | None
    stato_codice: str | None
    fase: str | None
    # Ragione sociale dell'emittente (P-4, Fase E del brief
    # perimetro-emittente): colonna di catalogo «disponibile e spenta»,
    # serve a chi ha piu' di un emittente davanti. La chiave e' il
    # `campo_sorgente` dichiarato in `ui.lista_colonna`.
    emittente_ragione_sociale: str | None


class DashCompetenzaErroreRow(TypedDict):
    # Riga blocco errori Lente 1 (vw_dash_competenza_errori): union
    # TASK_ERRORE (campi fattura NULL) + FATTURA_CRITICA (task_code NULL).
    tipo_evento: str
    competenza_mese: str | None
    lotto_id: int | None
    lotto_codice: str | None
    stato_lotto: str | None
    fattura_id: int | None
    fattura_anno: int | None
    fattura_serie: str | None
    fattura_numero: int | None
    # ⭐ Il numero documento dalla SEDE UNICA (20260829-15): `numero - serie`.
    # ⚠️ Le tre colonne sopra RESTANO: sono ordinabili a catalogo e servono a
    # chi filtra, non a chi legge. Questa serve a chi legge.
    fattura_numero_documento: str | None
    task_code: str | None
    error_code: str | None
    messaggio: str | None
    data_evento: str | None
    # Ragione sociale dell'emittente (P-4, Fase E del brief
    # perimetro-emittente): colonna di catalogo «disponibile e spenta»,
    # serve a chi ha piu' di un emittente davanti. La chiave e' il
    # `campo_sorgente` dichiarato in `ui.lista_colonna`.
    emittente_ragione_sociale: str | None
    # ⭐ D3 (changeSet 20260904-47, brief-residuo-fatturabili-e-bandiere):
    # QUALI commesse ha respinto il giro — una voce per commessa, con il suo
    # motivo — e non solo quante volte c'e' stato un errore. Vuoto sugli
    # eventi FATTURA_CRITICA, che commesse non ne hanno.
    # ⛔ Il badge del calendario continua a contare gli EVENTI: queste due
    #    colonne vivono nel dettaglio. Sommarle al conteggio farebbe di «4»
    #    la somma di tre unita' diverse (task, fatture, commesse).
    commesse_fallite: list[dict[str, Any]]
    n_commesse_fallite: int


class LineageNodoRow(TypedDict):
    # Riga summary di vendite.fn_documento_lineage_sintesi per un documento:
    # nodo + pratica collegata + frontiera forward + contatori genealogia.
    tipo_id: int
    tipo_codice_interno: str
    uid: str
    codice: str | None
    stato_codice_interno: str | None
    stato_codice: str | None
    stato_descrizione: str | None
    fase: str | None
    is_abortito: bool
    pratica_id: int | None
    pratica_numero: str | None
    n_pratiche: int
    frontiera_tipo_id: int | None
    frontiera_tipo_codice_interno: str | None
    frontiera_uid: str | None
    frontiera_codice: str | None
    frontiera_stato_codice_interno: str | None
    frontiera_fase: str | None
    n_discendenti_diretti: int
    n_discendenti_attivi: int
    is_transitato: bool
    n_sorgenti: int
    root_codice: str | None
    # ⭐ Natura del documento fiscale (FATTURA / NOTA_CREDITO / NOTA_DEBITO),
    # dal changeSet 20260821-01. Senza, due nodi FATTURA nati dalla stessa
    # commessa sono indistinguibili — il grafo e' nato quando `FATTURA` era una
    # cosa sola. NULL per tutti i tipi che non sono documenti fiscali.
    # (La descrizione NON si porta: il FE decodifica il codice via i18n come
    # per `tipo_codice_interno` — due sorgenti di etichetta divergerebbero.)
    natura_doc_codice_interno: str | None
    # Natura del nodo FRONTIERA (JOIN alla vista nodi): la frontiera puo'
    # essere una nota di credito — arco G dalla commessa — e senza questa il
    # pannello la etichetta «Fattura».
    frontiera_natura_doc_codice_interno: str | None


class LineagePassaggioRow(TypedDict):
    # Riga del traversal vendite.fn_documento_lineage (pannello "Passaggi"):
    # un arco della catena, con stato/fase del nodo target e flag ramo
    # inverso (arco R DDT->Reso, merce che torna).
    livello: int
    ordine: int
    arco: str
    ruolo: str | None
    from_tipo_id: int
    from_tipo_codice_interno: str | None
    from_uid: str
    from_codice: str | None
    from_stato_codice_interno: str | None
    from_fase: str | None
    from_doc_id: int | None
    to_tipo_id: int
    to_tipo_codice_interno: str | None
    to_uid: str
    to_codice: str | None
    to_stato_codice_interno: str | None
    to_fase: str | None
    to_is_abortito: bool
    to_doc_id: int | None
    is_ramo_inverso: bool
    # Natura dei due estremi (vedi `LineageNodoRow.natura_doc_codice_interno`): e' cio'
    # che permette a una tappa di dire «Nota di credito» invece di «Fattura»
    # per la seconda volta di fila.
    from_natura_doc_codice_interno: str | None
    to_natura_doc_codice_interno: str | None
    # Il LEGAME dell'arco (vendite.fn_documento_lineage_legami, rev 20261013-70):
    # True = ritirato (il documento non porta piu' niente dall'altra parte, che
    # puo' restare viva); False = vivo; None = arco non censito. Vale nei due versi.
    is_legame_ritirato: bool | None


class FondoFatturaDaDecidereRow(TypedDict):
    # Riga di vendite.vw_fondi_fattura_da_decidere: un caso di fondo fattura
    # che chiede una PERSONA. Quattro motivi a vocabolario chiuso
    # (PROPOSTA_SENZA_ATTO, IMPORTO_NON_CORRISPONDENTE, NON_PIU_CAPIENTE,
    # UTILITY_NON_ATTRIBUIBILE): li decodifica il FE con `labelOrCode`.
    #
    # ⚠️ Le colonne dell'ATTO (`fondo_source_id`, `origine`, `stato_atto`,
    # `importo_atto`, `atto_motivo`, `atto_data`) sono valorizzate SOLO sul ramo
    # NON_PIU_CAPIENTE — negli altri tre l'atto non esiste ancora, ed e' il
    # motivo per cui l'elenco lo segnala. Simmetricamente `importo_proposto`
    # esiste solo dove una proposta c'e' (PROPOSTA_SENZA_ATTO).
    motivo: str
    fattura_sorgente_id: int
    anno: int | None
    serie: str | None
    numero: str | None
    data: str | None
    totale_a_pagare: str | None
    billing_account_id: int | None
    utility_id: int | None
    tipo_doc_fiscale_id: int | None
    emittente_soggetto_ruolo_id: int | None
    valuta_id: int | None
    tipo_fondo_fattura_id: int | None
    tipo_fondo_codice_interno: str | None
    fondo_source_id: int | None
    origine: str | None
    stato_atto: str | None
    importo_atto: str | None
    atto_motivo: str | None
    atto_data: str | None
    importo_proposto: str | None
    capienza_attuale: str | None
