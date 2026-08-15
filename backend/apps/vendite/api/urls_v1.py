from django.urls import include, path

from apps.vendite.api.views import (
    ApiCommessaAttivita,
    ApiCommessaAttivitaAnnulla,
    ApiCommessaAttivitaApprova,
    ApiCommessaAttivitaRiallineaPrezzo,
    ApiCommessaAttivitaSbloccaPrezzo,
    ApiCommessaAttivitaVariazionePrezzoEccezionale,
    ApiCommessaOneri,
    ApiCommessePushLog,
    ApiCommessaStato,
    ApiFatturazioneApprovaCompetenza,
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
    ApiLottoSegnalazioniSummary,
    ApiLottoTaskRuns,
    ApiResetLottoDraft,
    ApiResetLottoFatturaDraft,
    ApiRiportaLottoADraft,
    ApiRunCommessePush,
    ApiRunLottoPipeline,
    ApiRunLottoPipelineUntilDone,
)
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
from apps.vendite.api.views_lookups import (
    ApiAmbitiContrattoLookup,
    ApiListiniSelezionabiliContrattoLookup,
    ApiTipiVariazioneContrattoLookup,
    ApiTipiVariazionePromoLookup,
)
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
    # Pricing v5 diagnostico: resolver 3 stadi (PROMO/CONTRATTO/CATEGORIA).
    path("pricing/resolve/", PricingResolveView.as_view(), name="vendite-pricing-resolve"),
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
    # Genealogia/lineage commessa (Fase C): sorgenti che l'hanno generata
    # (indietro) + fatture a valle (avanti). Consumato dal drawer leggero
    # aperto dalle tappe COMMESSA dei pannelli "Passaggi" dei documenti.
    path(
        "commesse/<int:commessa_id>/passaggi/",
        ApiCommessaPassaggi.as_view(),
        name="vendite-commessa-passaggi",
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
    path(
        "commesse/<int:commessa_id>/attivita/",
        ApiCommessaAttivita.as_view(),
        name="vendite-commessa-attivita",
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
    # Lookup dinamico listini selezionabili come riferimento contrattuale
    # (filtra per esistenza di una versione ATTIVA — decisione 2026-05-18
    # §4.4 refactor-contratti-modalita). Sostituisce LookupSelect generico
    # `rel=vendite.listini` nel ContrattoDrawer.
    path(
        "lookup/listini-selezionabili-contratto/",
        ApiListiniSelezionabiliContrattoLookup.as_view(),
        name="vendite-lookup-listini-selezionabili-contratto",
    ),
]
