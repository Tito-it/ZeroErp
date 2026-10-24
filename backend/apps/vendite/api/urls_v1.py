# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Rotte canoniche `/api/v1/vendite/*`. Una APIView esplicita per
#        endpoint: nessun router DRF automatico, nessun CRUD generato.
# ------------------------------------------------------------

from django.urls import include, path

from apps.vendite.api.views import (
    ApiGiornale,
    ApiGiornaleExport,
    ApiCommessaAttivita,
    ApiCommessaRegistro,
    ApiCommessaAttivitaAnnulla,
    ApiCommessaAttivitaApprova,
    ApiCommessaAttivitaExport,
    ApiCommessaAttivitaRiallineaPrezzo,
    ApiCommessaAttivitaSbloccaPrezzo,
    ApiCommessaAttivitaVariazionePrezzoEccezionale,
    ApiCommessaOneri,
    ApiCommessePushLog,
    ApiCommessaDetail,
    ApiCommessaStato,
    ApiEscludiDocumentiDaGiro,
    ApiFatturazioneApprovaCompetenza,
    ApiFatturazioneFinestraNumerazione,
    ApiFatturazioneEsiti,
    ApiFatturazioneNumera,
    ApiFatturazioneNumeraLotto,
    ApiFatturazioneRistampaLotto,
    ApiFatturazioneRun,
    ApiFatturazioneRunStato,
    ApiLottiExportView,
    ApiLottiList,
    ApiLottiMensile,
    ApiLottoDetail,
    ApiLottoFattureList,
    ApiLottoGruppiExport,
    ApiLottoGruppiList,
    ApiLottoGiornale,
    ApiLottoFattureExport,
    ApiLottoTaskRunsExport,
    ApiLottoSegnalazioniExport,
    ApiLottoSegnalazioniRows,
    ApiLottoSegnalazioniSummary,
    ApiLottoTaskRuns,
    ApiResetLottoDraft,
    ApiResetLottoFatturaDraft,
    ApiRiportaLottoADraft,
    ApiRunCommessePush,
    ApiRunLottoPipeline,
    ApiRunLottoPipelineUntilDone,
)
from apps.vendite.api.legami_views import ApiCommessaLegami
from apps.vendite.api.lineage_views import ApiCommessaPassaggi
from apps.vendite.api.views_approvazioni_prezzo import (
    ApprovaPrezzoContrattoView,
    ApprovaPrezzoOffertaView,
    ApprovaPrezzoView,
    ApprovazioniPrezzoCodaView,
    RifiutaPrezzoContrattoView,
    RifiutaPrezzoOffertaView,
    RifiutaPrezzoView,
)
from apps.vendite.api.views_dashboard_backlog import (
    ApiDashboardBacklog,
    ApiDashboardBacklogDocumenti,
    ApiDashboardBacklogDocumentiExport,
)
from apps.vendite.api.views_dashboard_competenza import (
    ApiDashboardCompetenza,
    ApiDashboardCompetenzaAttivita,
    ApiDashboardCompetenzaCommesse,
    ApiDashboardCompetenzaResidui,
    ApiDashboardCompetenzaResiduiExport,
    ApiAttivitaRiportaDaEmettere,
    ApiAttivitaRiportabili,
    ApiDashboardCompetenzaCommesseExport,
    ApiDashboardCompetenzaErrori,
    ApiDashboardCompetenzaErroriExport,
    ApiDashboardCompetenzaGruppi,
    ApiDashboardCompetenzaGruppiExport,
)
from apps.vendite.api.views_dashboard_aperto import (
    ApiDashboardAperto,
    ApiDashboardApertoDocumenti,
    ApiDashboardApertoDocumentiExport,
)
from apps.vendite.api.views_fondi_fattura import (
    ApiFondiFatturaDaDecidere,
    ApiFondiFatturaDaDecidereExport,
    ApiFondoFatturaDelete,
)
from apps.vendite.api.views_lookups import (
    ApiAmbitiContrattoLookup,
    ApiListiniSelezionabiliLookup,
    ApiTipiVariazioneContrattoLookup,
    ApiTipiVariazionePromoLookup,
)
from apps.vendite.api.views_iva import IvaResolveView
from apps.vendite.api.views_pricing import (
    PricingDiagnoseView,
    PricingLimitiUtenteView,
    PricingResolveView,
)
from apps.vendite.api.views_promo_articoli import (
    PromoArticoliDetailView,
    PromoArticoliView,
)

urlpatterns = [
    path("preventivi/", include("apps.vendite.api.preventivi_urls")),
    path("listini/", include("apps.vendite.api.urls_listini")),
    path("contratti/", include("apps.vendite.api.urls_contratti")),
    path("offerte/", include("apps.vendite.api.urls_offerte")),
    path("ordini/", include("apps.vendite.api.urls_ordini")),
    path("ddt/", include("apps.vendite.api.urls_ddt")),
    path("fatture/", include("apps.vendite.api.urls_fatture")),
    path("resi/", include("apps.vendite.api.urls_resi")),
    # Registri di numerazione: CRUD del sezionale (brief-be-fe-crud-registri-
    # di-numerazione). ⚠️ Il dato e' di vendite, la maschera vive nel drawer
    # dell'emittente fiscale: il permesso resta quello dell'area `vendite`.
    path("registri/", include("apps.vendite.api.urls_registri")),
    # Famiglie di documento: il CRUD della REGOLA che il registro applica
    # (brief-be-fe-crud-registri-di-numerazione §11.10).
    path("famiglie/", include("apps.vendite.api.urls_famiglie")),
    # Pricing v5 diagnostico: resolver 3 stadi (PROMO/CONTRATTO/CATEGORIA).
    path("pricing/resolve/", PricingResolveView.as_view(), name="vendite-pricing-resolve"),
    # ⭐ Gemello del resolver prezzi, e sta qui accanto di proposito: stesso
    #    mestiere (esporre un resolver DB al form), stessa area, stessa forma.
    #    ⛔ Non accetta un imponibile: sui documenti la riga non si spezza, e
    #    il contratto lo impedisce invece di chiederlo per favore.
    path("iva/resolve/", IvaResolveView.as_view(), name="vendite-iva-resolve"),
    # Diagnostica configurazione asset pricing (BA, contratto, matrice, promo)
    # — checklist a stadi + azioni suggerite per UX e supporto.
    path("pricing/diagnose/", PricingDiagnoseView.as_view(), name="vendite-pricing-diagnose"),
    # L2 autorizzazioni prezzi: limiti sconto/maggiorazione per utente corrente.
    path("pricing/limiti-utente/", PricingLimitiUtenteView.as_view(), name="vendite-pricing-limiti-utente"),
    # L3 workflow approvazione prezzo out-of-policy (Sprint E).
    path(
        "righe/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoView.as_view(),
        name="vendite-approva-prezzo",
    ),
    path(
        "righe/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoView.as_view(),
        name="vendite-rifiuta-prezzo",
    ),
    # L3 workflow approvazione prezzo su riga **contratto** (refactor
    # 2026-05-19 BE porting gate riga contratti). Endpoint distinto da
    # `righe/` per evitare ambiguita' su `riga_id` (preventivi e contratti
    # hanno tabelle/sequence indipendenti). Servizio service-side fa
    # dispatch via parametro sorgente='contratto'.
    path(
        "righe-contratto/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoContrattoView.as_view(),
        name="vendite-approva-prezzo-contratto",
    ),
    path(
        "righe-contratto/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoContrattoView.as_view(),
        name="vendite-rifiuta-prezzo-contratto",
    ),
    # L3 workflow approvazione prezzo su **eccezione offerta** (refactor
    # 2026-06-01 gate prezzi offerte). Endpoint distinto: `riga_id` = id
    # eccezione; service dispatch via sorgente='offerta'.
    path(
        "eccezioni-offerta/<int:riga_id>/approva-prezzo/",
        ApprovaPrezzoOffertaView.as_view(),
        name="vendite-approva-prezzo-offerta",
    ),
    path(
        "eccezioni-offerta/<int:riga_id>/rifiuta-prezzo/",
        RifiutaPrezzoOffertaView.as_view(),
        name="vendite-rifiuta-prezzo-offerta",
    ),
    path(
        "approvazioni-prezzo/",
        ApprovazioniPrezzoCodaView.as_view(),
        name="vendite-approvazioni-prezzo-coda",
    ),
    # Promo articoli (STADIO 0 resolver v5). Matrice CRUD admin.
    # Non esposta via /core/lookup/codici/: ha codice ma non e'
    # candidata come tabella config lookup (semantica temporale).
    path("promo-articoli/", PromoArticoliView.as_view(), name="vendite-promo-articoli-list"),
    path("promo-articoli/<int:record_id>/", PromoArticoliDetailView.as_view(), name="vendite-promo-articoli-detail"),
    # Situazione aperta — stock documenti per fase, senza asse temporale
    # (brief-design-fatturazione-due-lenti §6-bis): riepilogo + drill-down.
    # Sostituisce la dashboard fatturazione 5-card (Fase 3, trasformazione).
    path(
        "dashboard-aperto/",
        ApiDashboardAperto.as_view(),
        name="vendite-dashboard-aperto",
    ),
    path(
        "dashboard-aperto/documenti/",
        ApiDashboardApertoDocumenti.as_view(),
        name="vendite-dashboard-aperto-documenti",
    ),
    path(
        "dashboard-aperto/documenti/export/",
        ApiDashboardApertoDocumentiExport.as_view(),
        name="vendite-dashboard-aperto-documenti-export",
    ),
    # Lente 1 Competenza — funnel commessa → fattura per mese di competenza
    # (brief-design-fatturazione-due-lenti §4): aggregata + drill-down + errori.
    path(
        "dashboard-competenza/",
        ApiDashboardCompetenza.as_view(),
        name="vendite-dashboard-competenza",
    ),
    path(
        "dashboard-competenza/attivita/",
        ApiDashboardCompetenzaAttivita.as_view(),
        name="vendite-dashboard-competenza-attivita",
    ),
    path(
        "dashboard-competenza/commesse/",
        ApiDashboardCompetenzaCommesse.as_view(),
        name="vendite-dashboard-competenza-commesse",
    ),
    path(
        "dashboard-competenza/commesse/export/",
        ApiDashboardCompetenzaCommesseExport.as_view(),
        name="vendite-dashboard-competenza-commesse-export",
    ),
    # I RESIDUI: le attivita' che una fattura non ce l'hanno piu' e che nessun
    # giro riprendera' da solo. E' l'elenco su cui agisce «Riporta da emettere»,
    # ed e' una lista sua e non un filtro di `attivita/`: lo stadio
    # EMESSA_NON_FATTURATA contiene tre situazioni e solo questa chiede
    # un'azione.
    path(
        "dashboard-competenza/residui/",
        ApiDashboardCompetenzaResidui.as_view(),
        name="vendite-dashboard-competenza-residui",
    ),
    path(
        "dashboard-competenza/residui/export/",
        ApiDashboardCompetenzaResiduiExport.as_view(),
        name="vendite-dashboard-competenza-residui-export",
    ),
    # Il verbo «Riporta da emettere» e la sua lettura di motivi. ⚠️ Vivono
    # sull'ATTIVITA' e non sotto `dashboard-competenza/`: il cruscotto e' dove
    # oggi si preme il pulsante, ma l'oggetto del verbo e' l'attivita'
    # fatturabile — e domani lo stesso gesto puo' partire da un'altra schermata.
    path(
        "attivita-fatturabili/riporta-da-emettere/",
        ApiAttivitaRiportaDaEmettere.as_view(),
        name="vendite-attivita-riporta-da-emettere",
    ),
    path(
        "attivita-fatturabili/riportabili/",
        ApiAttivitaRiportabili.as_view(),
        name="vendite-attivita-riportabili",
    ),
    # Emissione mirata: l'unita' su cui l'operatore decide nella card «Da
    # emettere» (documento sorgente oppure oneri di commessa). La gruppo_key
    # esposta qui e' quella accettata da fatturazione/run/ (campo `gruppi`).
    path(
        "dashboard-competenza/gruppi/",
        ApiDashboardCompetenzaGruppi.as_view(),
        name="vendite-dashboard-competenza-gruppi",
    ),
    path(
        "dashboard-competenza/gruppi/export/",
        ApiDashboardCompetenzaGruppiExport.as_view(),
        name="vendite-dashboard-competenza-gruppi-export",
    ),
    path(
        "dashboard-competenza/errori/",
        ApiDashboardCompetenzaErrori.as_view(),
        name="vendite-dashboard-competenza-errori",
    ),
    path(
        "dashboard-competenza/errori/export/",
        ApiDashboardCompetenzaErroriExport.as_view(),
        name="vendite-dashboard-competenza-errori-export",
    ),
    # Lente 2 Backlog — non-collegati per anzianita' + classe azionabilita'
    # (brief-design-fatturazione-due-lenti §5): contatori + lista.
    path(
        "dashboard-backlog/",
        ApiDashboardBacklog.as_view(),
        name="vendite-dashboard-backlog",
    ),
    path(
        "dashboard-backlog/documenti/",
        ApiDashboardBacklogDocumenti.as_view(),
        name="vendite-dashboard-backlog-documenti",
    ),
    path(
        "dashboard-backlog/documenti/export/",
        ApiDashboardBacklogDocumentiExport.as_view(),
        name="vendite-dashboard-backlog-documenti-export",
    ),
    # Fondi fattura — l'elenco dei casi che il giro automatico lascia a una
    # persona (D-10). Sola lettura: presenta, non sana.
    path(
        "fondi-fattura/da-decidere/",
        ApiFondiFatturaDaDecidere.as_view(),
        name="vendite-fondi-fattura-da-decidere",
    ),
    # Export CSV/XLSX della stessa lista (colonne dal catalogo
    # `vendite.fondi_fattura_da_decidere`, risolte sulla configurazione
    # dell'operatore).
    path(
        "fondi-fattura/da-decidere/export/",
        ApiFondiFatturaDaDecidereExport.as_view(),
        name="vendite-fondi-fattura-da-decidere-export",
    ),
    # Il verbo (BE-4): il METODO dice l'azione, il path e' la risorsa —
    # `api.md` §Grammatica URL vieta di scriverla nel path. ⚠️ Dichiarata DOPO
    # le due rotte `da-decidere/` di proposito: `<int:...>` non le cattura, ma
    # tenerle sopra rende l'ordine leggibile a chi cerca la lista.
    path(
        "fondi-fattura/<int:fondo_source_id>/",
        ApiFondoFatturaDelete.as_view(),
        name="vendite-fondo-fattura-delete",
    ),
    path("lotti/", ApiLottiList.as_view(), name="vendite-lotti-list"),
    # Export CSV/XLSX della lista (colonne dal catalogo `vendite.lotti`).
    path("lotti/export/", ApiLottiExportView.as_view(), name="vendite-lotti-export"),
    # Aggregato conteggi lotti/mese per la sidebar anno/mese (prima di
    # <int:lotto_id> per chiarezza; "mensile" non è comunque un int).
    path("lotti/mensile/", ApiLottiMensile.as_view(), name="vendite-lotti-mensile"),
    path("lotti/<int:lotto_id>/", ApiLottoDetail.as_view(), name="vendite-lotto-detail"),
    path("pipeline/run/", ApiRunLottoPipeline.as_view(), name="vendite-run-lotto-pipeline"),
    path(
        "pipeline/run-until-done/",
        ApiRunLottoPipelineUntilDone.as_view(),
        name="vendite-run-lotto-pipeline-until-done",
    ),
    path(
        "lotti/<int:lotto_id>/fatture/",
        ApiLottoFattureList.as_view(),
        name="vendite-lotto-fatture-list",
    ),
    # I DOCUMENTI presi in carico dal lotto, con l'esito di ciascuno.
    # ⭐ Non e' un doppione di `fatture/`: quella si aggancia a `fattura_id` e
    # non puo' mostrare un documento caduto PRIMA che una fattura esista — che
    # e' esattamente quello che l'operatore sta cercando quando apre un lotto
    # in ERRORE (brief-db-esito-gruppo-lotto).
    path(
        "lotti/<int:lotto_id>/gruppi/",
        ApiLottoGruppiList.as_view(),
        name="vendite-lotto-gruppi-list",
    ),
    # Il GIORNALE TRASVERSALE (pezzo G dell'osservabilita', 2026-09-19): la
    # Storia di tutte le entita' insieme, filtrata per gravita'. `export/`
    # prima della lista, per convenzione.
    path("giornale/export/", ApiGiornaleExport.as_view(), name="vendite-giornale-export"),
    path("giornale/", ApiGiornale.as_view(), name="vendite-giornale"),
    # La STORIA del lotto (Passo A, seconda meta'): il lotto piu' le sue
    # fatture, righe non-INFO. ⛔ Da non confondere con `segnalazioni/`, che
    # elenca i problemi APERTI: qui c'e' anche cio' che e' andato bene.
    path(
        "lotti/<int:lotto_id>/giornale/",
        ApiLottoGiornale.as_view(),
        name="vendite-lotto-giornale",
    ),
    # Export delle tre liste del drawer lotto. ⚠️ PRIMA delle rotte di elenco:
    # `export/` e' un segmento letterale e non collide, ma le rotte piu'
    # specifiche stanno in testa per convenzione.
    path(
        "lotti/<int:lotto_id>/fatture/export/",
        ApiLottoFattureExport.as_view(),
        name="vendite-lotto-fatture-export",
    ),
    path(
        "lotti/<int:lotto_id>/gruppi/export/",
        ApiLottoGruppiExport.as_view(),
        name="vendite-lotto-gruppi-export",
    ),
    path(
        "lotti/<int:lotto_id>/task-runs/export/",
        ApiLottoTaskRunsExport.as_view(),
        name="vendite-lotto-task-runs-export",
    ),
    path(
        "lotti/<int:lotto_id>/segnalazioni/export/",
        ApiLottoSegnalazioniExport.as_view(),
        name="vendite-lotto-segnalazioni-export",
    ),
    # Elenco PAGINATO delle segnalazioni (BE-4). ⚠️ PRIMA del riepilogo:
    # `rows/` e' un segmento letterale e non collide, ma tenere la rotta piu'
    # specifica in testa evita sorprese se un domani il riepilogo diventasse
    # un pattern piu' permissivo.
    path(
        "lotti/<int:lotto_id>/segnalazioni/rows/",
        ApiLottoSegnalazioniRows.as_view(),
        name="vendite-lotto-segnalazioni-rows",
    ),
    path(
        "lotti/<int:lotto_id>/segnalazioni/",
        ApiLottoSegnalazioniSummary.as_view(),
        name="vendite-lotto-segnalazioni-summary",
    ),
    path(
        "lotti/<int:lotto_id>/task-runs/",
        ApiLottoTaskRuns.as_view(),
        name="vendite-lotto-task-runs",
    ),
    path(
        "lotti/<int:lotto_id>/reset-draft/",
        ApiResetLottoDraft.as_view(),
        name="vendite-reset-lotto-draft",
    ),
    # Fase 6: ritorno a bozza. Vicino a `reset-draft` di proposito — sono i due
    # verbi che disfano il lavoro di un lotto — ma fanno cose opposte: quello
    # CHIUDE il lotto (ANNULLATA), questo lo rimette in lavorazione.
    path(
        "lotti/<int:lotto_id>/riporta-a-draft/",
        ApiRiportaLottoADraft.as_view(),
        name="vendite-lotto-riporta-a-draft",
    ),
    path(
        "lotti/<int:lotto_id>/fatture/<int:fattura_id>/reset-draft/",
        ApiResetLottoFatturaDraft.as_view(),
        name="vendite-reset-lotto-fattura-draft",
    ),
    # ⚠️ La `gruppo_key` viaggia nel BODY e non nel path: e' una chiave di
    #    dominio (`ORDINE:123`, `MAN:45`) e contiene i due punti, che in un
    #    segmento di URL vanno codificati — un contratto che si sbaglia a mano.
    path(
        "lotti/<int:lotto_id>/documenti/escludi/",
        ApiEscludiDocumentiDaGiro.as_view(),
        name="vendite-lotto-documenti-escludi",
    ),
    # --- Commesse ---
    path(
        "commesse/push/run/",
        ApiRunCommessePush.as_view(),
        name="vendite-run-commesse-push",
    ),
    path(
        "commesse/push/<int:push_log_id>/",
        ApiCommessePushLog.as_view(),
        name="vendite-commesse-push-log",
    ),
    path(
        "commesse/<int:commessa_id>/stato/",
        ApiCommessaStato.as_view(),
        name="vendite-commessa-stato",
    ),
    # Testata leggibile (descrizione + responsabile): il solo verbo di
    # scrittura; il dettaglio resta su `/stato/` (rotta storica del drawer).
    path(
        "commesse/<int:commessa_id>/",
        ApiCommessaDetail.as_view(),
        name="vendite-commessa-detail",
    ),
    # Genealogia/lineage commessa (Fase C): sorgenti che l'hanno generata
    # (indietro) + fatture a valle (avanti). Consumato dal drawer leggero
    # aperto dalle tappe COMMESSA dei pannelli "Passaggi" dei documenti.
    path(
        "commesse/<int:commessa_id>/passaggi/",
        ApiCommessaPassaggi.as_view(),
        name="vendite-commessa-passaggi",
    ),
    # Legami della commessa per la finestra di conferma dell'annullo
    # (brief-db-annullo-a-valle-riapre-a-monte D-2): che cosa si riapre a
    # monte e che cosa si annulla.
    path(
        "commesse/<int:commessa_id>/legami/",
        ApiCommessaLegami.as_view(),
        name="vendite-commessa-legami",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/riallinea-prezzo/",
        ApiCommessaAttivitaRiallineaPrezzo.as_view(),
        name="vendite-commessa-attivita-riallinea-prezzo",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/variazione-prezzo-eccezionale/",
        ApiCommessaAttivitaVariazionePrezzoEccezionale.as_view(),
        name="vendite-commessa-attivita-variazione-prezzo",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/sblocca-prezzo/",
        ApiCommessaAttivitaSbloccaPrezzo.as_view(),
        name="vendite-commessa-attivita-sblocca-prezzo",
    ),
    # Annullamento di una riga MANUALE (onere) caricata per errore: non
    # cancella, porta stato_emissione ad ANNULLATA (gia' filtrato da tutte le
    # porte verso fattura e cockpit). Gate `carica_voce_manuale`.
    path(
        "commesse/<int:commessa_id>/attivita/<int:att_id>/annulla/",
        ApiCommessaAttivitaAnnulla.as_view(),
        name="vendite-commessa-attivita-annulla",
    ),
    # Il REGISTRO delle righe: gli eventi che il DB scrive su
    # `commesse_attivita_log`. ⛔ Fino al 2026-08-28 quella tabella si scriveva e
    # non si leggeva da nessuna parte — sei tipi di evento irraggiungibili.
    path(
        "commesse/<int:commessa_id>/registro/",
        ApiCommessaRegistro.as_view(),
        name="vendite-commessa-registro",
    ),
    path(
        "commesse/<int:commessa_id>/attivita/",
        ApiCommessaAttivita.as_view(),
        name="vendite-commessa-attivita",
    ),
    # Export della STESSA lista (DEF-1): colonne, ordine e permessi dal catalogo
    # `vendite.commesse_attivita`, non da un elenco proprio che divergerebbe.
    # ⚠️ PRIMA della rotta `<int:att_id>` sarebbe indifferente (`export` non e'
    # un intero), ma sta qui perche' e' la gemella della lista: si leggono
    # insieme.
    path(
        "commesse/<int:commessa_id>/attivita/export/",
        ApiCommessaAttivitaExport.as_view(),
        name="vendite-commessa-attivita-export",
    ),
    # Porta oneri: POST crea la riga di valore sulla sotto-risorsa `oneri`
    # (nessun verbo nel path — il metodo HTTP dice "crea", api.md §Grammatica).
    path(
        "commesse/<int:commessa_id>/oneri/",
        ApiCommessaOneri.as_view(),
        name="vendite-commessa-oneri",
    ),
    # Azione APPROVA righe (cockpit Fase A, A-1): tutte o selezione righe_ids.
    path(
        "commesse/<int:commessa_id>/attivita/approva/",
        ApiCommessaAttivitaApprova.as_view(),
        name="vendite-commessa-attivita-approva",
    ),
    # --- Fatturazione (cockpit Dashboard Competenza) ---
    # Azione APPROVA massiva per mese di competenza (Fase A, A-2): la popolazione
    # della card DA_APPROVARE (stessa vista del drill-down, scope in-vista).
    path(
        "fatturazione/approva-competenza/",
        ApiFatturazioneApprovaCompetenza.as_view(),
        name="vendite-fatturazione-approva-competenza",
    ),
    # C-4: numerazione «Rendi definitive» di un singolo lotto EMESSA (step
    # DEFINITIVA = numera + accoda stampa). Gate fiscale separato (I-7).
    path(
        "fatturazione/lotti/<int:lotto_id>/numera/",
        ApiFatturazioneNumeraLotto.as_view(),
        name="vendite-fatturazione-numera-lotto",
    ),
    # C-8: ristampa MASSIVA di un lotto DEFINITIVA (accoda in fatture_stampa_coda,
    # drenata dal worker draina_coda_stampa). Accodamento sincrono.
    path(
        "fatturazione/lotti/<int:lotto_id>/ristampa/",
        ApiFatturazioneRistampaLotto.as_view(),
        name="vendite-fatturazione-ristampa-lotto",
    ),
    # BE-5: la FINESTRA DI NUMERAZIONE — con quale data si puo' numerare e da
    # quale data i documenti partono adesso, per un lotto (`?lotto_id=`) o per
    # l'atto su un mese (`?competenza_mese=`).
    # Sola lettura: alimenta il `minDate` del DatePicker di «Rendi definitive».
    path(
        "fatturazione/finestra-numerazione/",
        ApiFatturazioneFinestraNumerazione.as_view(),
        name="vendite-fatturazione-finestra-numerazione",
    ),
    # C-5: esiti dei giri (job_run_log per corsia) + stato coda stampa (scope
    # emittente operatore). Sola lettura.
    path(
        "fatturazione/esiti/",
        ApiFatturazioneEsiti.as_view(),
        name="vendite-fatturazione-esiti",
    ),
    # C-3: giro di fatturazione on-demand (accoda in dbops.coda_lavori, non
    # bloccante) + polling dello stato del job (ownership operatore).
    path(
        "fatturazione/run/",
        ApiFatturazioneRun.as_view(),
        name="vendite-fatturazione-run",
    ),
    path(
        "fatturazione/run/<int:job_id>/",
        ApiFatturazioneRunStato.as_view(),
        name="vendite-fatturazione-run-stato",
    ),
    # C-4: numerazione di perimetro «Rendi definitive competenza» (accoda in
    # dbops.coda_lavori, non bloccante). Polling via fatturazione/run/<job_id>/.
    path(
        "fatturazione/numera/",
        ApiFatturazioneNumera.as_view(),
        name="vendite-fatturazione-numera",
    ),
    # --- Lookup statici (Fase 2 refactor frontend vendite) ---
    path(
        "lookup/tipi-variazione-contratto/",
        ApiTipiVariazioneContrattoLookup.as_view(),
        name="vendite-lookup-tipi-variazione-contratto",
    ),
    path(
        "lookup/tipi-variazione-promo/",
        ApiTipiVariazionePromoLookup.as_view(),
        name="vendite-lookup-tipi-variazione-promo",
    ),
    path(
        "lookup/ambiti-contratto/",
        ApiAmbitiContrattoLookup.as_view(),
        name="vendite-lookup-ambiti-contratto",
    ),
    # I listini che un contratto o un'offerta puo' scegliere, per utility ed
    # emittente del form: la lettura del DB, lo stesso predicato del guard del
    # documento (F-2 di brief-db-offerta-emissione-ed-erogazione).
    path(
        "lookup/listini-selezionabili/",
        ApiListiniSelezionabiliLookup.as_view(),
        name="vendite-lookup-listini-selezionabili",
    ),
]
