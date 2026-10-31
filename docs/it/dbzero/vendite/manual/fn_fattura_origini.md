## 📘 Documentazione Concettuale – Funzione `vendite.fn_fattura_origini(bigint)`

> 👀 **Vedi anche**
>
> [config.sorgenti](/dbzero/config/tabelle/sorgenti) (colonna `citato_in_fattura`) ·
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) ·
> [vendite.fn_documento_lineage_nodi](/dbzero/vendite/funzioni/fn_documento_lineage_nodi) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §7

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15.10, §15.11, D-G1, Q-F6, Q-F7)

**I documenti a monte che una fattura cita**: la bolla, l'ordine, il contratto, l'offerta, il
preventivo; per una nota di credito anche la fattura che corregge e il reso. Sono tutte sorgenti, di
tipo diverso: una regola sola per ogni documento. Non la commessa, che per il cliente è un contenitore interno. La stampa e il dettaglio
della fattura leggono la stessa risposta.

### Come la trova

1. **Livello 1: i genitori diretti** della fattura nella catena dei documenti, di qualunque tipo.
   Per una nota di credito sono la fattura corretta (dalla riga che corregge) e il reso (dalla riga
   di reso accreditata).
2. Con **un'eccezione**: il legame commessa → fattura vale per la commessa intera, e al suo posto si
   usano i documenti delle **righe fatturate** (ogni attività fatturabile viene da una riga di
   commessa, che porta il suo documento).
3. Da ciascuno, la **catena all'indietro** (l'ordine nato da un preventivo, la bolla da un ordine, il
   reso da una bolla): gli antenati hanno livello 1 + la distanza.
4. Restano i soli tipi con `citato_in_fattura` nel registro delle sorgenti.

⭐ **La risalita non passa dalla commessa.** Risalendo da lì, una fattura citerebbe anche i documenti
le cui righe sono finite in un'altra fattura (una commessa che raccoglie le bolle di più mesi), e una
nota citerebbe tutto ciò che sta nella commessa della fattura che corregge. Una fattura citata porta già
i suoi riferimenti. Lo hanno mostrato i pgTAP.

⭐ **E non passa dalla revisione dell'offerta** (arco `V`, dal 31-10-2026): un contratto nato dalla
revisione 2 citerebbe anche la revisione 1, che il cliente non ha accettato.

⚠️ **La chiave.** La riga di commessa porta l'`uid` della testata; il nodo del lineage la chiave che
il registro dichiara (`key_selector`: `id` per ordine, contratto e bolla, `uid` per preventivo e
offerta). La traduzione passa dalla tabella del documento, letta dal registro: nessun tipo è scritto
nella funzione.

### Regole

* Ogni documento una volta, col livello più vicino, anche se arriva da più righe o da più commesse
  (P-3: l'unione).
* Fuori i documenti **annullati** (stato abortito).
* La risalita segue solo **legami vivi**: un documento raggiunto solo da legami ritirati (righe
  annullate) non ha portato nulla in fattura.
* Fuori i documenti che chi legge non vede: la funzione è `SECURITY INVOKER`, come il lineage.
* Ordine: livello, tipo, codice. Una fattura senza documenti a monte risponde zero righe.

### Che cosa restituisce

`livello`, `tipo_id`, `tipo_codice_interno`, `etichetta` (il nome del tipo sulla carta: «Ordine»,
«DDT»), `uid` (la chiave del nodo), `codice` (il numero del documento).

### Esempio: la nota di credito da reso

La fattura F fattura la bolla DA dell'ordine OA; il cliente rende 3 pezzi (reso R su DA) e la nota NR
li accredita. NR cita: F e R (livello 1), DA (2), OA (3). Non cita le altre bolle della commessa di
F. Una nota di sola correzione cita la sola fattura corretta.

---

{% include-markdown "signature-core.md" %}
