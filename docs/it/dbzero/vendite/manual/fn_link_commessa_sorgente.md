## 📘 Documentazione Concettuale – Funzione `vendite.fn_link_commessa_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — il link che la porta scrive
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi, con la chiave di ognuno
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che traduce la chiave del chiamante in quella del modello
> * [vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente) — la commessa aperta che già trattiene il documento
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico sulla tabella
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.fn_link_commessa_sorgente` è la porta del link documento → commessa: collega un documento a una commessa in modo idempotente e ne decide il ruolo (ROOT o COLLEGATO).

---

### La chiave la decide il BB che scrive

Il chiamante passa il tipo del documento e la sua chiave come la conosce, id o uid resi a
testo. La porta non la interpreta da sé: la consegna a `script.fn_sorgente_chiave`, che legge
il `key_selector` del tipo, traduce la chiave dell'altra specie (l'uid per un tipo a chiave id,
l'id per un tipo a chiave uid), verifica che il documento esista e restituisce la coppia del
modello, `sorgente_id` oppure `sorgente_uid`. Idempotenza, lock e inserimento lavorano su
quella. La riga d'origine, se il chiamante la passa, la valida il guard unico sulla tabella.

---

### Regole applicate

* **Ruolo**: la prima sorgente di una commessa diventa ROOT, le successive COLLEGATO
  (commessa multi-sorgente, aggregazione del fatturabile).
* ⭐ **Un documento sta in una sola commessa aperta alla volta.** Se il documento sta già in
  un'altra commessa aperta, chiesto a `vendite.fn_commessa_viva_di_sorgente`, la porta solleva
  `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` con l'id di quella commessa. Una commessa **chiusa o
  annullata** non trattiene il documento: il suo link resta come **storia** (lineage,
  passaggi), e il documento si rimanda in una commessa nuova.
* **Idempotente sulla stessa commessa**: un secondo link dello stesso documento alla stessa
  commessa restituisce il link che c'è. Il `meta` si riscrive solo se il chiamante porta
  qualcosa di nuovo: la porta si chiama per ogni riga mandata, e un aggiornamento a vuoto
  scriverebbe una riga di storico per riga.
* **Due lock.** Quello sulla commessa serializza la scelta del ruolo; un lock advisory sulla
  **sorgente** serializza due invii dello stesso documento verso commesse diverse, che il lock
  sulla commessa non vede. Vale in `READ COMMITTED`, come lavora l'applicazione.

---

### Chi la chiama

* `vendite.fn_upsert_commessa_attivita`, per ogni riga che viene da un documento spinto in
  commessa (tipo con `scope = 'PUSH_COMMESSA'` in `config.sorgenti`): **il link nasce con la
  riga**, nel DB.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_PARAMETRO_INVALIDO` | manca la commessa, il tipo o la chiave (gli spazi attorno alla chiave si tolgono prima), o la riga è negativa |
| `E_VALORE_MANCANTE` | la commessa non esiste |
| `E_SORG_CONF` | il tipo non è censito o non è attivo |
| `E_SORG_FORMATO` | la chiave non ha la forma canonica della sua specie |
| `E_SORG_NORM_NON_RISOLTA` | la chiave dell'altra specie non si traduce |
| `E_SORG_NOT_FOUND` | il documento non esiste |
| `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` | il documento sta già in un'altra commessa aperta |

I codici `E_SORG_*` li solleva `script.fn_sorgente_chiave`, che la porta chiama.

---

### Note di migrazione

* 2026-07-18 — la porta normalizza la chiave testuale alla forma del `key_selector`
  (brief-db-guard-sorgente-polimorfa §2a).
* 2026-10-12 — da «una commessa per sempre» a «una sola commessa aperta alla volta»; il link
  nasce con la riga, nella madre delle righe (brief-db-annullo-a-valle-riapre-a-monte D-12, D-13).
* 2026-11-07 — la normalizzazione propria della porta lascia il posto al BB che scrive,
  `script.fn_sorgente_chiave`, e la tabella passa alla chiave tipizzata col guard unico al posto
  di `script.trgfn_guard_sorgente_polimorfa_testuale` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
