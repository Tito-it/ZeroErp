from django.urls import path

from apps.catalogo.api.views import (
    ApiArticoloComponenteChiudi,
    ApiArticoloComponenteChiusura,
    ApiArticoloComponentiList,
    ApiArticoloComponentiLista,
    ApiArticoloComponentiListaExport,
    ApiArticoliFormDefaults,
    ApiArticoloDisattiva,
    ApiArticoloRiattiva,
    ApiArticoloDetail,
    ApiArticoloNoteList,
    ApiArticoloUomDetail,
    ApiArticoloUomList,
    ApiArticoloUomLookup,
    ApiArticoliList,
    ApiArticoliLookup,
    ApiComponenteNoteList,
    ApiConversioneDetail,
    ApiConversioniList,
    ApiNotaDetail,
    ApiUomTipoDetail,
    ApiUomTipiList,
    ApiUnitaMisuraDetail,
    ApiUnitaMisuraDisattiva,
    ApiUnitaMisuraList,
)

urlpatterns = [
    # Articoli
    path("articoli/lookup/", ApiArticoliLookup.as_view(), name="catalogo-articoli-lookup"),
    path("articoli/form-defaults/", ApiArticoliFormDefaults.as_view(), name="catalogo-articoli-form-defaults"),
    path("articoli/<uuid:articolo_id>/uom/lookup/", ApiArticoloUomLookup.as_view(), name="catalogo-articolo-uom-lookup"),
    path("articoli/<uuid:articolo_id>/uom/<int:uom_op_id>/", ApiArticoloUomDetail.as_view(), name="catalogo-articolo-uom-detail"),
    path("articoli/<uuid:articolo_id>/uom/", ApiArticoloUomList.as_view(), name="catalogo-articolo-uom-list"),
    # La distinta come lista configurabile (lotto C): PRIMA di `<uuid:comp_id>/`,
    # anche se `lista/` non e' un uuid — le rotte letterali in testa.
    path("articoli/<uuid:articolo_id>/componenti/lista/", ApiArticoloComponentiLista.as_view(), name="catalogo-articolo-componenti-lista"),
    path("articoli/<uuid:articolo_id>/componenti/lista/export/", ApiArticoloComponentiListaExport.as_view(), name="catalogo-articolo-componenti-lista-export"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/note/", ApiComponenteNoteList.as_view(), name="catalogo-componente-note-list"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/chiusura/", ApiArticoloComponenteChiusura.as_view(), name="catalogo-articolo-componente-chiusura"),
    path("articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/chiudi/", ApiArticoloComponenteChiudi.as_view(), name="catalogo-articolo-componente-chiudi"),
    path("articoli/<uuid:articolo_id>/componenti/", ApiArticoloComponentiList.as_view(), name="catalogo-articolo-componenti-list"),
    path("articoli/<uuid:articolo_id>/note/", ApiArticoloNoteList.as_view(), name="catalogo-articolo-note-list"),
    path("articoli/<uuid:articolo_id>/disattiva/", ApiArticoloDisattiva.as_view(), name="catalogo-articolo-disattiva"),
    path("articoli/<uuid:articolo_id>/riattiva/", ApiArticoloRiattiva.as_view(), name="catalogo-articolo-riattiva"),
    path("articoli/<uuid:articolo_id>/", ApiArticoloDetail.as_view(), name="catalogo-articolo-detail"),
    path("articoli/", ApiArticoliList.as_view(), name="catalogo-articoli-list"),
    path("note/<int:nota_id>/", ApiNotaDetail.as_view(), name="catalogo-nota-detail"),
    # Tipologie UoM (lookup usa endpoint generico /core/lookup/codici/?rel=catalogo.uom_tipi)
    path("uom-tipi/<int:tipo_id>/", ApiUomTipoDetail.as_view(), name="catalogo-uom-tipo-detail"),
    path("uom-tipi/", ApiUomTipiList.as_view(), name="catalogo-uom-tipi-list"),
    # Unita' di misura (lookup usa endpoint generico /core/lookup/codici/?rel=catalogo.unita_misura)
    path("unita-misura/<int:uom_id>/disattiva/", ApiUnitaMisuraDisattiva.as_view(), name="catalogo-unita-misura-disattiva"),
    path("unita-misura/<int:uom_id>/", ApiUnitaMisuraDetail.as_view(), name="catalogo-unita-misura-detail"),
    path("unita-misura/", ApiUnitaMisuraList.as_view(), name="catalogo-unita-misura-list"),
    # Conversioni UoM
    path("conversioni-uom/<int:conv_id>/", ApiConversioneDetail.as_view(), name="catalogo-conversione-detail"),
    path("conversioni-uom/", ApiConversioniList.as_view(), name="catalogo-conversioni-list"),
]
