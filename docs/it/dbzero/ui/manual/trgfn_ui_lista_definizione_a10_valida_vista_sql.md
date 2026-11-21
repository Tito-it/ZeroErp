## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_definizione_a10_valida_vista_sql`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista che dichiara la vista
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — le colonne che si riverificano
>
> Approfondimento viste:
>
> * [dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano) — ciò che il guard non vede: il DDL sulla vista, il migrate
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo) — la domanda «la relazione esiste, e ha il campo?»
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — il controllo gemello sulle colonne
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — il migrate riconosciuto come proprietario
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — la lista registrata prima della sua vista

---

### 🎯 Scopo Principale

Il trigger verifica, quando una lista si scrive, che la relazione dichiarata in `vista_sql` esista
nello schema `schema_dati` della lista; e, quando l'applicazione cambia la vista o riaccende la
lista, che le colonne della lista vi trovino ancora il loro campo. Un nome sbagliato si ferma al
salvataggio invece che alla prima apertura della lista.

---

### Quando controlla

Parte alla nascita della lista e quando cambiano `vista_sql`, `schema_dati` o `attivo`. Non
controlla una lista senza vista dichiarata (legge i dati da una funzione o dal backend), né una
lista spenta: così una lista si registra spenta prima che la sua vista esista, e il controllo parte
quando la si accende.

---

### Che cosa vale come vista vera

Una vista, una vista materializzata, una tabella o una tabella partizionata con quel nome nello
schema della lista, chiesta a [fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo).
Il nome si scrive senza schema; un'omonima in un altro schema non conta (`comuni` esiste in `config`
e in `storico`).

---

### ⭐ Le colonne si riverificano, per l'applicazione

Quando chi scrive non è il proprietario della tabella (l'applicazione, dalla pagina tecnica), un
cambio di vista o di schema su una lista accesa, e la riaccensione di una lista, si rifiutano se una
colonna `VISTA` della lista, accesa o spenta, ha un campo che la relazione non ha. La frase nomina le
colonne. Le colonne `LINEAGE` non leggono la vista e non contano.

Il migrate resta fuori: il CSV delle definizioni si carica prima di quello delle colonne, e un
cambio di vista fatto nel seed insieme alle colonne si fermerebbe a metà. Il seed lo giudicano il
pgTAP del catalogo e il presidio
[vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano).

---

### ⚠️ Che cosa oggi non copre

* **Una vista cancellata, rinominata o privata di una colonna dopo non si vede**: il controllo
  guarda la riga quando si scrive. La vede il presidio, che confronta ogni lista accesa con la sua
  relazione.

---

### Codici errore

* `E_UI_VISTA_SQL_NON_TROVATA` — la relazione non c'è nello schema della lista. La frase porta il nome
  qualificato.
* `E_UI_LISTA_COLONNE_ORFANE` — l'applicazione cambia vista o riaccende la lista, e una colonna
  resterebbe senza il suo campo. La frase porta la lista, la relazione e le colonne.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — una vista che esiste solo in un
  altro schema è rifiutata, la vista nel suo schema passa; ogni lista accesa del catalogo ha la sua
  vista.
* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — il cambio di vista e la riaccensione che lasciano una
  colonna orfana, la frase che la nomina, la tabella partizionata.

---

### Note di migrazione

* 2026-05-06 — nasce, col catalogo delle liste.
* 2026-09-27 — la relazione si cerca nello schema della lista, e il trigger parte anche sul cambio di
  `schema_dati`: prima bastava un'omonima in qualunque schema.
* 2026-11-21 — la relazione dal building block, partizionate comprese; per l'applicazione, cambio di
  vista e riaccensione riverificano le colonne.

---

{% include-markdown "signature-core.md" %}
