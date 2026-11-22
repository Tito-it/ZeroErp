## 📘 Documentazione Concettuale – Vista `dbops.vw_liste_colonne_campo_orfano`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista e la sua relazione
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — la colonna, il suo campo e la sua origine
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove questa vista è dichiarata
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_sintesi_colonne](/dbzero/vendite/views/vw_documento_lineage_sintesi_colonne) — i nomi che la sintesi della lineage produce
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo) — la domanda «la relazione ha il campo?», la stessa dei guard
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — il meccanismo condiviso

---

### 🎯 Scopo Principale

Il presidio delle colonne di lista che leggono un campo che la loro sorgente non ha. **Deve restare
a zero righe.** Una riga è una colonna che a video resta vuota, o una lista che non si apre.

---

### Perché serve, accanto ai guard

I guard di `ui` giudicano la riga che si scrive: una colonna nuova, un cambio di vista fatto
dall'applicazione. Due cose cambiano sotto di loro senza che nessun trigger scatti:

* una vista che perde una colonna con un DDL;
* una lista cambiata dal migrate, che resta fuori dalla verifica delle colonne perché il seed delle
  definizioni si carica prima di quello delle colonne.

Il pgTAP del catalogo le vede sulle righe del seed; questo presidio le vede su tutte, anche sulle
liste create dall'installazione.

---

### Una riga per caso, con la causa

| Causa | Che cosa vuol dire |
| --- | --- |
| `RELAZIONE_ASSENTE` | una lista accesa dichiara una vista che nel suo schema non c'è (la colonna è vuota) |
| `CAMPO_ASSENTE` | una colonna `VISTA`, accesa o spenta, di una lista accesa ha un campo che la relazione non ha |
| `LINEAGE_NON_DICHIARATA` | una colonna `LINEAGE` sta su una lista che non dichiara `legge_lineage` |
| `LINEAGE_SCONOSCIUTA` | una colonna `LINEAGE` ha un campo che la sintesi della lineage non produce |

Il nome di una colonna `LINEAGE` lo verifica solo questo presidio: il guard delle colonne chiede
soltanto che la lista dichiari la lineage, così il catalogo delle liste non dipende da una vista di
`vendite`. La dipendenza sta qui, in `dbops`.

---

### Nel catalogo dei presidi

Natura `ZERO`, cadenza settimanale, perimetro libero (nessuna tabella in row level security): il
conteggio letto da un programma senza utente è onesto. A spegnerlo è lo sviluppo: la colonna va
corretta o spenta, oppure la vista della lista riallineata.

---

### Test

* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — una colonna tolta con un DDL compare come
  `CAMPO_ASSENTE`, una lista sana non compare.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — la vista ha la sua riga nel catalogo dei presidi.

---

### Note di migrazione

* 2026-11-21 — nasce, col catalogo delle liste che smette di leggere la lineage per nome.

---

{% include-markdown "signature-core.md" %}
