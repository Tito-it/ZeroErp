## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_child_requires_non_obsolete_parent`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — figlia cablata, verso `pratiche.tipi_prestazione`
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — figlia cablata, verso `pratiche.template_flussi`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la gemella sull'asse `attivo`
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — la selezione che nasconde le voci obsolete
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — l'«oggi» con cui si giudica l'obsolescenza
>
> Guide:
>
> * [Uso di obsoleto](/guide/uso-di-obsoleto) — l'asse `obsoleto_dal`, separato da `attivo`

---

### 🎯 Scopo Principale

Impedisce di **creare** un'istanza, o di **ricollegarla**, verso una voce di catalogo **obsoleta**,
cioè con `obsoleto_dal` raggiunto alla data operativa. Le istanze che puntano già a quella voce
restano, e i loro avanzamenti di stato non si bloccano.

È la difesa in profondità di «la selezione nasconde, il database rifiuta»: la selezione nasconde
le voci obsolete (`dbops.fn_get_lookup_codici` senza obsoleti), questo trigger vieta di usarle
comunque.

---

### ⭐ Un asse diverso da `attivo`

Una voce obsoleta resta `attivo = true`: è ancora un riferimento valido per le istanze che la
usano, ma non si sceglie più per il nuovo. Il require della regola ATTIVO non la ferma, ed è per
questo che serve un trigger suo.

| | Asse `attivo` | Asse `obsoleto_dal` |
| --- | --- | --- |
| Domanda | il riferimento è valido? | si può scegliere per il nuovo? |
| Padre che blocca | spento | `obsoleto_dal` raggiunto |
| Montaggio | generato dal framework | cablato a mano, una relazione alla volta |
| Su un aggiornamento | dipende dalla colonna attivo del figlio | solo se la FK cambia |

---

### Quando il controllo si fa e quando no

* Una FK vuota passa: è facoltativa.
* Su un aggiornamento, se la FK non cambia il controllo non si fa: un cambio di stato di
  un'istanza storica non ripunta il catalogo e non si blocca mai.
* Una voce con `obsoleto_dal` vuoto, o con una data futura (ritiro programmato), si può usare.
* La data si confronta con la **data operativa** (`script.fn_data_operativa`), non con la data
  del server.

⚠️ Un padre che non si trova passa senza errore: il ramo «catalogo non trovato» non scatta mai,
perché il controllo dopo l'interrogazione dinamica guarda un indicatore che quell'interrogazione
non aggiorna. Con la FK vera il caso non si presenta.

---

### Il cablaggio

Un trigger per relazione, `AFTER INSERT OR UPDATE OF` la colonna FK, con gli argomenti: schema e
tabella del catalogo, nome della colonna `obsoleto_dal`, colonna FK del figlio, colonna
referenziata (`id` se manca). Oggi sono cablate `pratiche.pratiche` verso
`pratiche.tipi_prestazione` e `pratiche.flussi` verso `pratiche.template_flussi`. Un catalogo
nuovo è un altro trigger, nessuna logica nuova.

---

### Codici errore

Tutti i rifiuti escono con `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`:

* la voce di catalogo è obsoleta — il caso per cui il codice esiste;
* il trigger è montato con meno di quattro argomenti, o la colonna referenziata, la tabella o la
  colonna `obsoleto_dal` non esistono.

⚠️ I casi di configurazione usano lo stesso codice di dominio, di classe conflitto di stato: chi
li riceve legge «catalogo obsoleto» per un trigger montato male.

---

### Test

* `db/pgtap/pratiche/test-guard-non-obsolete-parent-v1.sql` — su pratiche e flussi: voce
  selezionabile o con ritiro programmato passa, voce obsoleta si rifiuta; un aggiornamento che non
  tocca la FK passa anche quando la voce è diventata obsoleta; il ricollegamento a una voce
  obsoleta si rifiuta; la voce obsoleta resta attiva.

---

### Note di migrazione

* 2026-06-30 — nasce con il cablaggio su pratiche e flussi
  (`brief-db-obsoleto-dal-filtro-lookup-e-guard`).
* 2026-10-09 — «oggi» diventa la data operativa, nel fuso aziendale; prima era la data del server.

---

{% include-markdown "signature-core.md" %}
