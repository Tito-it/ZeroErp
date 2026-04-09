from django.urls import path

from apps.vendite.api.views_listini import (
    ApiListinoAssociazioneDetail,
    ApiListinoAssociazioniList,
    ApiListinoDetail,
    ApiListinoTestPrezzo,
    ApiListinoVersioneClona,
    ApiListinoVersioneDetail,
    ApiListinoVersioneRigaDetail,
    ApiListinoVersioneRigheList,
    ApiListinoVersioneStato,
    ApiListinoVersioniList,
    ApiListiniList,
)

urlpatterns = [
    path("test-prezzo/", ApiListinoTestPrezzo.as_view(), name="vendite-listini-test-prezzo"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/<int:riga_id>/", ApiListinoVersioneRigaDetail.as_view(), name="vendite-listino-versione-riga-detail"),
    path("<int:listino_id>/versioni/<int:ver_id>/righe/", ApiListinoVersioneRigheList.as_view(), name="vendite-listino-versione-righe-list"),
    path("<int:listino_id>/versioni/<int:ver_id>/stato/", ApiListinoVersioneStato.as_view(), name="vendite-listino-versione-stato"),
    path("<int:listino_id>/versioni/<int:src_ver_id>/clona/", ApiListinoVersioneClona.as_view(), name="vendite-listino-versione-clona"),
    path("<int:listino_id>/versioni/<int:ver_id>/", ApiListinoVersioneDetail.as_view(), name="vendite-listino-versione-detail"),
    path("<int:listino_id>/versioni/", ApiListinoVersioniList.as_view(), name="vendite-listino-versioni-list"),
    path("<int:listino_id>/associazioni/<int:assoc_id>/", ApiListinoAssociazioneDetail.as_view(), name="vendite-listino-associazione-detail"),
    path("<int:listino_id>/associazioni/", ApiListinoAssociazioniList.as_view(), name="vendite-listino-associazioni-list"),
    path("<int:listino_id>/", ApiListinoDetail.as_view(), name="vendite-listino-detail"),
    path("", ApiListiniList.as_view(), name="vendite-listini-list"),
]
