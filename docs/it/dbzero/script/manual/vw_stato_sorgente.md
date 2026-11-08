## 📘 Documentazione Concettuale – Vista `script.vw_stato_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi di documento e la loro chiave
>
> Approfondimento viste:
>
> * [vendite.vw_stato_sorgente_preventivo](/dbzero/vendite/views/vw_stato_sorgente_preventivo) — uno dei rami: la forma che ogni resolver di dominio ripete
> * [script.vw_pratica_doc_sorgente](/dbzero/script/views/vw_pratica_doc_sorgente) — il documento più vivo di una pratica, letto da qui
>
> Approfondimento funzioni:
>
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — lo stesso descrittore per un documento solo, con la sentinella
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza e la chiave del documento

---

### 🎯 Scopo Principale

Lo stato di un documento nel vocabolario comune: la union dei resolver di dominio, una riga per
documento con fase, esito e flag terminale. È l'**unica superficie** da cui il motore delle pratiche
legge lo stato di un documento: nessun selettore di resolver, nessun ramo scritto nel motore.

Vive in `script`, fra il motore (`pratiche`) e i domini, perché un dominio nuovo si aggiunga senza
toccare il motore.

---

### I rami: un resolver per dominio

| Ramo | Tipo di documento | Chiave |
| --- | --- | --- |
| `vendite.vw_stato_sorgente_preventivo` | `PREVENTIVO` | uid |
| `vendite.vw_stato_sorgente_offerta` | `OFFERTA_COMMERCIALE` | uid |
| `vendite.vw_stato_sorgente_ordine` | `ORDINE_VENDITA` | id |
| `vendite.vw_stato_sorgente_contratto` | `CONTRATTO` | id |
| `vendite.vw_stato_sorgente_ddt` | `DDT_VENDITA` | id |
| `vendite.vw_stato_sorgente_reso` | `RESO_VENDITA` | id |

Ogni ramo trova il proprio tipo per codice in `config.sorgenti` (mai per id scritto a mano) e dà al
più una riga per documento. Un tipo senza ramo (la commessa, che non ha un ciclo di vita di stati
documentali, o i tipi di magazzino) **non ha righe**: è «non risolto», e
`pratiche.fn_stato_sorgente` risponde con la sentinella `UNKNOWN`. `risolto` è sempre vero sulle
righe della vista: l'assenza della riga è il «non risolto».

---

### La chiave del documento: nativa e in testo

Ogni riga porta la chiave del documento in tre colonne:

* `sorgente_chiave_uuid` — l'uid, valorizzata solo nei rami dei tipi a chiave uid;
* `sorgente_chiave_id` — l'id, valorizzata solo nei rami dei tipi a chiave id;
* `sorgente_uid` — la stessa chiave in **testo**, nella forma canonica (l'uid o l'id scritti come li
  scrive il database).

⭐ **Si cerca sulle chiavi native.** Chi cerca un documento confronta la sua chiave con
`sorgente_chiave_uuid` o con `sorgente_chiave_id`, un ramo per chiave: sotto RLS un confronto fra
uuid o fra interi arriva all'indice di ogni ramo (gli operatori sono `leakproof`), e il ramo
dell'altra specie, con la colonna vuota costante, viene scartato. Il confronto sulla colonna in
testo, invece, non arriva mai all'indice (le conversioni in testo non sono `leakproof`) e
leggerebbe per intero tutte le tabelle dei documenti. È così che la leggono
`pratiche.fn_stato_sorgente`, `script.vw_pratica_doc_sorgente` e `script.vw_flusso_doc_sorgente`.

⚠️ Per lo stesso motivo non si cerca con un OR sulle due chiavi native: l'OR non scende nei rami
della union.

---

### Registrare un dominio nuovo

1. Il dominio dichiara la mappa di fase, esito e terminale sui propri stati documentali e crea il
   resolver `<schema>.vw_stato_sorgente_<tipo>` con le **stesse colonne** e al più una riga per
   documento.
2. ⚠️ Il ramo valorizza la colonna nativa della sua specie di chiave e lascia vuota l'altra: un ramo
   che le lasciasse vuote tutte e due comparirebbe nella vista, ma nessun lettore lo troverebbe mai.
3. Il ramo si aggiunge alla union con un changeSet nuovo; il motore e i lettori non cambiano.

---

### Test

* `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` — le mappe di stato e i rami di preventivo,
  offerta, ordine e contratto.
* `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql` — i rami di bolla e reso, a chiave id; la
  chiave nativa coerente con il testo.
* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — la vista gira con il perimetro di chi legge.

---

### Note di migrazione

* 2026-07-01 — nasce con il ramo del preventivo (`brief-db-proiezione-stato-dominio`); offerta,
  ordine e contratto entrano il 2026-07-02.
* 2026-07-18 — entrano i rami di bolla e reso (`brief-db-fatturazione-ddt-resi`).
* 2026-10-05 — si aggiungono le due colonne della chiave nativa, su cui si cerca.

---
{% include-markdown "signature-core.md" %}
