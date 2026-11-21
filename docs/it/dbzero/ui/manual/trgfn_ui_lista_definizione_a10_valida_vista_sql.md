## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_definizione_a10_valida_vista_sql`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista che dichiara la vista
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — il controllo gemello sulle colonne
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — la lista registrata prima della sua vista

---

### 🎯 Scopo Principale

Il trigger verifica, quando una lista si scrive, che la relazione dichiarata in `vista_sql` esista
nello schema `schema_dati` della lista: un nome sbagliato si ferma al salvataggio invece che alla
prima apertura della lista.

---

### Quando controlla

Parte alla nascita della lista e quando cambiano `vista_sql`, `schema_dati` o `attivo`. Non
controlla:

* una lista senza vista dichiarata, che legge i dati da una funzione o dal backend;
* una lista spenta.

Il secondo salto permette di registrare una lista prima che la sua vista esista: la si registra
spenta, e quando la vista c'è la si accende, e il controllo parte in quel momento.

---

### Che cosa vale come vista vera

Una vista, una vista materializzata o una tabella con quel nome nello schema della lista. Il nome si
scrive senza schema; un'omonima in un altro schema non conta (`comuni` esiste in `config` e in
`storico`).

---

### ⚠️ Che cosa oggi non copre

* **Una vista cancellata o rinominata dopo non si vede**: il controllo guarda la riga quando si
  scrive. Il presidio è il pgTAP del catalogo, sulle liste del seed.
* **Cambiare vista non riverifica le colonne** della lista, che restano anche se la vista nuova non
  le ha.
* **Una tabella partizionata è rifiutata**: non è fra i tipi ammessi.
* **Una `vista_sql` vuota su una lista spenta passa**: nessun vincolo rifiuta la stringa vuota, e il
  salto sulle liste spente la lascia entrare.

---

### Codici errore

* `E_UI_VISTA_SQL_NON_TROVATA` — la relazione non c'è nello schema della lista. La frase porta il nome
  qualificato.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — una vista che esiste solo in un
  altro schema è rifiutata, la vista nel suo schema passa; ogni lista accesa del catalogo ha la sua
  vista.

Il salto sulle liste spente, la verifica alla riaccensione e il cambio del solo `schema_dati` non
sono costruiti da nessun test.

---

### Note di migrazione

* 2026-05-06 — nasce, col catalogo delle liste.
* 2026-09-27 — la relazione si cerca nello schema della lista, e il trigger parte anche sul cambio di
  `schema_dati`: prima bastava un'omonima in qualunque schema.

---

{% include-markdown "signature-core.md" %}
