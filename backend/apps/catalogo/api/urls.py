from django.urls import path

from apps.catalogo.api.views import (
    ApiArticoloComponenteDetail,
    ApiArticoloComponenteDuplicaVersione,
    ApiArticoloComponentiList,
    ApiArticoliFormDefaults,
    ApiArticoloDisattiva,
    ApiArticoloRiattiva,
    ApiArticoloDetail,
    ApiArticoloNoteList,
    ApiArticoloUomDetail,
    ApiArticoloUomList,
    ApiArticoliList,
    ApiArticoliLookup,
    ApiComponenteNoteList,
    ApiConversioneDetail,
    ApiConversioniList,
    ApiNotaDetail,
    ApiUnitaMisuraDetail,
    ApiUnitaMisuraDisattiva,
    ApiUnitaMisuraList,
    ApiUomRoundingModesLookup,
)

urlpatterns = [
    # Articoli
    path("articoli/lookup/", ApiArticoliLookup.as_view(), name="catalogo-articoli-lookup"),
    path("articoli/form-defaults/", ApiArticoliFormDefaults.as_view(), name="catalogo-articoli-form-defaults"),
    path("articoli/<uuid:articolo_id>/uom/<int:uom_op_id>/", ApiArticoloUomDetail.as_view(), name="catalogo-articolo-uom-detail"),
    path("articoli/<uuid:articolo_id>/uom/", ApiArticoloUomList.as_view(), name="catalogo-articolo-uom-list"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/note/", ApiComponenteNoteList.as_view(), name="catalogo-componente-note-list"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/duplica-versione/", ApiArticoloComponenteDuplicaVersione.as_view(), name="catalogo-articolo-componente-duplica-versione"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/", ApiArticoloComponenteDetail.as_view(), name="catalogo-articolo-componente-detail"),
    path("articoli/<uuid:articolo_id>/componenti/", ApiArticoloComponentiList.as_view(), name="catalogo-articolo-componenti-list"),
    path("articoli/<uuid:articolo_id>/note/", ApiArticoloNoteList.as_view(), name="catalogo-articolo-note-list"),
    path("articoli/<uuid:articolo_id>/disattiva/", ApiArticoloDisattiva.as_view(), name="catalogo-articolo-disattiva"),
    path("articoli/<uuid:articolo_id>/riattiva/", ApiArticoloRiattiva.as_view(), name="catalogo-articolo-riattiva"),
    path("articoli/<uuid:articolo_id>/", ApiArticoloDetail.as_view(), name="catalogo-articolo-detail"),
    path("articoli/", ApiArticoliList.as_view(), name="catalogo-articoli-list"),
    path("note/<int:nota_id>/", ApiNotaDetail.as_view(), name="catalogo-nota-detail"),
    # Unita' di misura (lookup usa endpoint generico /core/lookup/codici/?rel=catalogo.unita_misura)
    path("unita-misura/<int:uom_id>/disattiva/", ApiUnitaMisuraDisattiva.as_view(), name="catalogo-unita-misura-disattiva"),
    path("unita-misura/<int:uom_id>/", ApiUnitaMisuraDetail.as_view(), name="catalogo-unita-misura-detail"),
    path("unita-misura/", ApiUnitaMisuraList.as_view(), name="catalogo-unita-misura-list"),
    # Conversioni UoM
    path("conversioni-uom/<int:conv_id>/", ApiConversioneDetail.as_view(), name="catalogo-conversione-detail"),
    path("conversioni-uom/", ApiConversioniList.as_view(), name="catalogo-conversioni-list"),
    # Lookup statici
    path("lookup/rounding-modes/", ApiUomRoundingModesLookup.as_view(), name="catalogo-lookup-rounding-modes"),
]
