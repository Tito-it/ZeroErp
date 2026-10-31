from django.urls import path

from apps.vendite.api.views_form_defaults import (
    ApiListinoVersioneCloneDefaults,
    ApiListinoVersioneCloseDefaults,
    ApiListinoVersioneNewDefaults,
)
from apps.vendite.api.views_listini import (
    ApiListiniTipologiePerUtility,
    ApiListinoDetail,
    ApiListinoVersioneApplicaVariazione,
    ApiListinoVersioneBundleDetail,
    ApiListinoVersioneChiusura,
    ApiListinoVersioneClona,
    ApiListinoVersioneRigaRettificaControllata,
    ApiListinoVersioneDetail,
    ApiListinoVersioneRigaDetail,
    ApiListinoVersioneRigheList,
    ApiListinoVersioneStato,
    ApiListinoVersioniList,
    ApiListiniList,
)

# F2-BE-13: rimosse rotte `/associazioni/` e `/test-prezzo/` (modello v5
# non usa piu' `listini_associazioni`; il test resolver e' coperto da
# pricing_service.resolve_prezzo su `fn_resolve_prezzo_listino_v2`).
urlpatterns = [
    path("tipologie-per-utility/", ApiListiniTipologiePerUtility.as_view(), name="vendite-listini-tipologie-per-utility"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/<int:riga_id>/rettifica-controllata/", ApiListinoVersioneRigaRettificaControllata.as_view(), name="vendite-listino-versione-riga-rettifica-controllata"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/<int:riga_id>/", ApiListinoVersioneRigaDetail.as_view(), name="vendite-listino-versione-riga-detail"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/", ApiListinoVersioneRigheList.as_view(), name="vendite-listino-versione-righe-list"),
    # Bundle componenti BoM (modello unificato 2026-05-13): prezzi bundle
    # dei figli di un padre composito. Tabella `listini_righe_componenti`.
    path(
        "<int:listino_id>/versioni/<int:ver_id>/bundle/<uuid:padre_id>/",
        ApiListinoVersioneBundleDetail.as_view(),
        name="vendite-listino-versione-bundle-detail",
    ),
    path("<int:listino_id>/versioni/<int:ver_id>/applica-variazione/", ApiListinoVersioneApplicaVariazione.as_view(), name="vendite-listino-versione-applica-variazione"),
    path("<int:listino_id>/versioni/<int:ver_id>/stato/", ApiListinoVersioneStato.as_view(), name="vendite-listino-versione-stato"),
    path("<int:listino_id>/versioni/<int:ver_id>/chiusura/", ApiListinoVersioneChiusura.as_view(), name="vendite-listino-versione-chiusura"),
    # Form-defaults (Fase 2.B5b/c refactor frontend vendite). Specifici PRIMA
    # di clone-defaults/close-defaults per non collidere con il pattern <int:>.
    path(
        "<int:listino_id>/versioni/<int:src_versione_id>/clone-defaults/",
        ApiListinoVersioneCloneDefaults.as_view(),
        name="vendite-listino-versione-clone-defaults",
    ),
    path(
        "<int:listino_id>/versioni/<int:versione_id>/close-defaults/",
        ApiListinoVersioneCloseDefaults.as_view(),
        name="vendite-listino-versione-close-defaults",
    ),
    path("<int:listino_id>/versioni/<int:src_ver_id>/clona/", ApiListinoVersioneClona.as_view(), name="vendite-listino-versione-clona"),
    path("<int:listino_id>/versioni/<int:ver_id>/", ApiListinoVersioneDetail.as_view(), name="vendite-listino-versione-detail"),
    # Form-defaults nuova versione (Fase 2.B5a). Su /versioni/ senza id, prima
    # del path lista che intercetta tutto cio' che non e' un altro path.
    path(
        "<int:listino_id>/versioni/form-defaults/",
        ApiListinoVersioneNewDefaults.as_view(),
        name="vendite-listino-versione-new-defaults",
    ),
    path("<int:listino_id>/versioni/", ApiListinoVersioniList.as_view(), name="vendite-listino-versioni-list"),
    path("<int:listino_id>/", ApiListinoDetail.as_view(), name="vendite-listino-detail"),
    path("", ApiListiniList.as_view(), name="vendite-listini-list"),
]
