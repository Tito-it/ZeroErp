from django.urls import path

from apps.vendite.api.views_listini import (
    ApiListiniAlertScadenze,
    ApiListiniTipologiePerUtility,
    ApiListinoDetail,
    ApiListinoVersioneApplicaVariazione,
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
    path("alert-scadenze/", ApiListiniAlertScadenze.as_view(), name="vendite-listini-alert-scadenze"),
    path("tipologie-per-utility/", ApiListiniTipologiePerUtility.as_view(), name="vendite-listini-tipologie-per-utility"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/<int:riga_id>/rettifica-controllata/", ApiListinoVersioneRigaRettificaControllata.as_view(), name="vendite-listino-versione-riga-rettifica-controllata"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/<int:riga_id>/", ApiListinoVersioneRigaDetail.as_view(), name="vendite-listino-versione-riga-detail"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/", ApiListinoVersioneRigheList.as_view(), name="vendite-listino-versione-righe-list"),
    path("<int:listino_id>/versioni/<int:ver_id>/applica-variazione/", ApiListinoVersioneApplicaVariazione.as_view(), name="vendite-listino-versione-applica-variazione"),
    path("<int:listino_id>/versioni/<int:ver_id>/stato/", ApiListinoVersioneStato.as_view(), name="vendite-listino-versione-stato"),
    path("<int:listino_id>/versioni/<int:src_ver_id>/clona/", ApiListinoVersioneClona.as_view(), name="vendite-listino-versione-clona"),
    path("<int:listino_id>/versioni/<int:ver_id>/", ApiListinoVersioneDetail.as_view(), name="vendite-listino-versione-detail"),
    path("<int:listino_id>/versioni/", ApiListinoVersioniList.as_view(), name="vendite-listino-versioni-list"),
    path("<int:listino_id>/", ApiListinoDetail.as_view(), name="vendite-listino-detail"),
    path("", ApiListiniList.as_view(), name="vendite-listini-list"),
]
