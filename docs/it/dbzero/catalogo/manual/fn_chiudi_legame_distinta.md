## 📘 Documentazione Concettuale – Funzione `catalogo.fn_chiudi_legame_distinta`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami della distinta
> * [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti) — i prezzi bundle dei legami
>
> Approfondimento funzioni:
>
> * [vendite.fn_prezzi_legame_oltre_la_fine](/dbzero/vendite/funzioni/fn_prezzi_legame_oltre_la_fine) — quali prezzi la chiusura tocca, e come
> * [script.fn_check_legame_distinta_chiudibile](/dbzero/script/funzioni/fn_check_legame_distinta_chiudibile) — perché un legame non si chiude
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — il guard che dà l'avviso al primo tentativo
> * [vendite.trgfn_listini_righe_comp_guard_immutabilita_v5](/dbzero/vendite/funzioni/trgfn_listini_righe_comp_guard_immutabilita_v5) — l'immutabilità dei prezzi, e la sua porta
> * [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello) — il permesso, nel verbo
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini) — la distinta e i prezzi del kit

---

### 🎯 Scopo Principale

Chiude un legame della distinta (un componente di un kit) a una data, **insieme ai suoi prezzi bundle**. È la
strada da usare quando il componente ha dei prezzi nei listini: il guard della distinta, alla prima richiesta,
risponde con un avviso che elenca i numeri, e la chiusura si conferma qui.

---

### Perché i prezzi si chiudono col legame

Un prezzo bundle vale solo finché il componente è nel kit: la tabella dei prezzi ha una chiave esterna temporale
verso il legame, e il periodo del prezzo deve stare dentro quello del legame. Se il prezzo restasse aperto oltre la
fine, il legame non si chiuderebbe.

Fuori dalla bozza, però, un prezzo di listino non cambia. Senza un'eccezione, un kit prezzato in una versione già
attiva non potrebbe più perdere un componente finché quella versione esiste. L'eccezione è stretta: la chiusura del
legame accorcia **la sola fine** dei prezzi, alla stessa data. Prezzo, IVA e inizio restano quelli, e la versione e
le altre righe non si toccano.

Che cosa succede a ogni prezzo lo dice il lettore `vendite.fn_prezzi_legame_oltre_la_fine`:

| Esito | Il prezzo… | La chiusura… |
| --- | --- | --- |
| `CHIUDE` | comincia entro la fine | gli dà la stessa fine |
| `TOGLIE` | comincia dopo la fine, in una versione in bozza | lo cancella |
| `BLOCCA` | comincia dopo la fine, in una versione non in bozza | non passa (vedi sotto) |

Il prezzo del kit in un listino è la somma dei prezzi dei suoi componenti: da quella data, nel listino, il kit
costa meno. La finestra di conferma lo mostra versione per versione (`importo_per_kit`).

---

### ⭐ Mai in silenzio, mai senza diritti

L'ordine dei passi:

1. **Permesso sul catalogo** (`catalogo.articolo`, livello TUTTO).
2. **Il legame e i suoi prezzi si bloccano** fino alla fine della transazione: la conferma vale per i prezzi di
   adesso.
3. **Prima ciò che vieta**, dalla check `script.fn_check_legame_distinta_chiudibile`:
   * prezzi in listini che chi chiude **non vede** (un'altra azienda): la distinta è comune a tutte le aziende, i
     listini no, e chi non può toccare un listino non lo tocca nemmeno dalla distinta;
   * prezzi di una versione **non in bozza che cominciano dopo la fine**: non si accorciano e non si cancellano.
     Il messaggio dice la prima fine ammessa.
4. Se ci sono prezzi da chiudere o togliere: **permesso sui listini** (`vendite.listino`, livello TUTTO), e la
   **conferma**. Chi conferma dichiara quanti prezzi ha visto; se il numero non è quello di adesso la risposta è di
   nuovo l'avviso, coi numeri aggiornati.
5. I prezzi, poi il legame. I guard della distinta parlano come sempre (fine già passata, fine prima di ieri).

Un legame **senza prezzi** da toccare chiede solo il permesso sul catalogo, e nessuna conferma.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — legame o data mancanti.
* `E_PERMESSO_NEGATO` — manca il livello TUTTO sul catalogo, o sui listini quando ci sono prezzi.
* `E_BOM_LEGAME_NOT_FOUND` — il legame non esiste.
* `E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE`, `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI` — campo `valido_al`: ciò che vieta.
* `E_BOM_CHIUSURA_CON_PREZZI` — campo `valido_al`: la conferma manca o non corrisponde; valori componente, kit,
  numero di prezzi e di versioni; bersaglio il kit.
* Dal guard della distinta: `E_BOM_LEGAME_CHIUSO`, `E_BOM_CHIUSURA_RETROATTIVA`.

---

### Come è fatta

`SECURITY DEFINER` con `search_path` bloccato, `EXECUTE` solo all'applicazione: legge i prezzi di tutte le aziende
(per rifiutare quelli che chi chiude non vede) e apre la porta del guard d'immutabilità dei prezzi, che la onora
solo insieme al proprietario della tabella. La porta è la GUC transazionale `zeroerp.legame_distinta_chiudi`, con
l'id del legame; il verbo la richiude dopo aver scritto i prezzi.

Ritorna il legame, la fine di prima e quella di adesso, quanti prezzi ha chiuso e quanti ne ha tolti.

---

### Test

* `db/pgtap/catalogo/test-chiudi-legame-con-prezzi-v1.sql` — il lettore, la check, l'avviso dal guard e dal
  verbo, la conferma che non corrisponde e quella giusta, i prezzi chiusi e tolti, la porta che non si apre
  dall'applicazione, il prezzo che comincia dopo, il prezzo di un'altra azienda, il legame senza prezzi, il legame
  assente, il permesso sul catalogo e quello sui listini.

---

### Note di migrazione

* 2026-11-09 — nasce: chiudere un legame coi prezzi bundle aperti moriva sulla chiave esterna temporale, e fuori
  dalla bozza quei prezzi non si potevano accorciare (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
