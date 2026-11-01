## 📘 Documentazione Concettuale – Funzione `magazzino.fn_scrivi_movimento`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro che questa funzione è l'unica a scrivere
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia del valore che aggiorna
> * [magazzino.causali](/dbzero/magazzino/tabelle/causali) — verso, rettifica, stock negativo
>
> Approfondimento viste:
>
> * [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — la media corrente (il passo 12)
> * [dbops.vw_magazzino_movimenti_senza_costo](/dbzero/dbops/views/vw_magazzino_movimenti_senza_costo) — la spia delle entrate senza costo
>
> Approfondimento funzioni:
>
> * [script.fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino) — articolo, lotto, seriale, ubicazione (i passi 5-8)
> * [script.fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita) — quanto può uscire (il passo 11)
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il perimetro, anche qui dentro
> * [magazzino.fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza) — la ri-somma della copia del valore
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §5b la funzione madre
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — come si sollevano i codici

---

### 🎯 Scopo Principale

**L'unica funzione che scrive un movimento di magazzino**: fa tutti i controlli nell'ordine
del contratto, scrive la riga sul registro e aggiorna la copia del valore. Ritorna l'id del
movimento.

Riceve la merce (magazzino, articolo, quantità *con segno* in unità base,
lotto/seriale/ubicazione se servono), la **causale** per codice (`INV_INIZIALE`, `RETT_NEG`, …),
la **sorgente** a catalogo (quale operazione lo genera: tipo più *una* chiave) e, quando ha
senso, un costo.

Le **operazioni** (l'inventario, la rettifica, il trasferimento, la bolla, il reso, lo storno)
non ricontrollano niente: compongono le righe e la chiamano, in una transazione sola. Se la
settima riga di dieci è rifiutata, le prime sei si annullano con lei.

---

### È chiusa a chiave, ed è il punto

L'applicazione **non ha il permesso di scrivere** sul registro né sulla copia del valore: può
solo leggerli. Questa funzione gira con i permessi del **proprietario** delle tabelle (non di
un superuser), quindi è la sola strada. *«Scrive solo la primitiva»* non è una disciplina: è un
fatto che il database garantisce. La postura sta in tre sedi (il changeSet che la applica, il
ciclo dei permessi di `ci_apply`, il provisioning dei ruoli) e il pgTAP `test-porta-ledger-v1`
le tiene allineate.

⚠️ Girare da proprietario vuol dire **scavalcare** la sicurezza di riga del registro. Il
perimetro dell'operatore lo rimette il guard di perimetro comune a tutto il progetto, montato
sul registro e sulla copia del valore: legge chi è in sessione e chiede se può scrivere su quel
magazzino. Il guard si ferma **anche senza identità in sessione**: una sessione che non dice
chi è non scrive un movimento, nemmeno passando di qui.

---

### I quattordici passi (l'ordine è il contratto)

| # | Controllo | Se fallisce |
| --- | --- | --- |
| 1 | i parametri hanno una forma possibile (identificativi maggiori di zero, quantità diversa da zero, costo non negativo, una chiave di sorgente sola) | `E_MAG_CHIAMATA_NON_VALIDA` — tecnico: chi chiama è rotto |
| 2 | la causale esiste ed è attiva, cercata per `codice_interno` | `E_CONFIG_MANCANTE` |
| 3 | il segno della quantità è quello della causale | `E_MAG_MOVIMENTO_VERSO_INCOERENTE` (la frase la dà qui la funzione; il trigger sul registro resta la rete) |
| 4 | il magazzino esiste ed è attivo | `E_MAG_MAGAZZINO_NON_VALIDO` |
| 5-8 | l'articolo è gestito a magazzino; lotto e seriale come l'articolo pretende; l'ubicazione come il magazzino pretende; il seriale è dell'emittente del magazzino — letti da [fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino) | il **primo motivo** della check, col campo da correggere |
| 9 | uno storno è lo specchio esatto dell'originale (stesso articolo, magazzino, posizione, sorgente; quantità opposta; causale di storno) e l'originale non è già stornato | `E_MAG_STORNO_INCOERENTE` |
| 9-bis | la **posizione del seriale**: in entrata non è dentro da nessuna parte, in uscita è qui | `E_MAG_ASSET_POSIZIONE_INCOERENTE` |
| 10 | lo stesso movimento non è già a registro (sorgente + causale + posizione) | `E_MAG_MOVIMENTO_GIA_REGISTRATO`, con l'id esistente nella frase |
| 11 | **solo in uscita**: prende il lock su (magazzino, articolo) e chiede a [fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita) se la merce c'è e non è promessa ad altri — salvo `consente_stock_negativo`; una rettifica ignora i blocchi ma non il fisico | `E_MAG_GIACENZA_INSUFFICIENTE` · `E_MAG_MERCE_BLOCCATA` |
| 12 | il **costo**, deciso dalla struttura del movimento (sotto) | `E_MAG_COSTO_NON_AMMESSO` · `E_MAG_GEMELLA_NON_TROVATA` |
| 13 | la riga sul registro | — |
| 14 | la copia del valore: aumenta della quantità per il costo, arrotondata a sei decimali | — |

---

### Il costo, deciso dalla struttura

Il costo non lo sceglie il chiamante: lo dice il movimento stesso.

| Se il movimento è… | il costo è | e un costo passato da chi chiama |
| --- | --- | --- |
| uno **storno** | quello dell'originale | non è ammesso |
| l'**entrata gemella** di un trasferimento (stesso `transfer_uid`, segno positivo) | quello dell'uscita gemella, che deve esistere già | non è ammesso |
| un'**uscita** qualunque | la **media corrente** di (articolo, magazzino), letta da `vw_costo_medio` dentro il lock | non è ammesso |
| un'**entrata** da documento o da conteggio | quello passato, oppure la media corrente | facoltativo |

⭐ Un'entrata senza costo e senza media (il primo carico di un articolo mai valorizzato) scrive
il costo vuoto, lascia il valore com'è e **diluisce** la media: è un fatto dichiarato, non un
errore, e lo si vede nella spia `dbops.vw_magazzino_movimenti_senza_costo`. Non si inventa uno
zero.

Il costo scritto è arrotondato a sei decimali *prima* di calcolare il contributo al valore, e il
ricalcolo somma gli stessi arrotondamenti: copia e ri-somma coincidono per costruzione. La riga
della copia nasce anche quando il contributo è zero, così «giacenza con movimenti ma senza riga
di valore» resta la spia di una scrittura fuori porta.

---

### Il lock, e perché sta al passo 11

Il lock (advisory, transazionale, sulla coppia magazzino e articolo) si prende **solo in
uscita** e **dopo** i controlli 1-10: una chiamata sbagliata non deve mettersi in fila con le
altre. Fra i controlli e il lock nessuna lettura decide una scrittura non idempotente
(l'identità del passo 10 è protetta anche dal vincolo unico), quindi la finestra è benigna.
Tutto ciò che si legge dentro il lock — il fisico dell'articolo, del lotto o del seriale, i
blocchi, la media — sta dentro la coppia (magazzino, articolo): un lock più stretto non
serializzerebbe niente.

⚠️ **Una corsa benigna che qualcuno cercherà**: due entrate simultanee dello *stesso seriale*
in due magazzini si fermano sul secondo solo se la prima è già visibile — un'entrata non ha
lock per regola. La posizione derivata (9-bis) la difende al primo movimento successivo.

---

### Chi la chiama

* [fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) e
  [fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — i documenti interni di
  conteggio e correzione;
* [fn_posta_trasferimento](/dbzero/magazzino/funzioni/fn_posta_trasferimento) — la coppia
  uscita / entrata gemella del trasferimento interno;
* [fn_storna_movimenti_sorgente](/dbzero/magazzino/funzioni/fn_storna_movimenti_sorgente) —
  lo storno, attraverso il ramo storno;
* [vendite.fn_posta_ddt](/dbzero/vendite/funzioni/fn_posta_ddt) e
  [vendite.fn_posta_reso](/dbzero/vendite/funzioni/fn_posta_reso) — lo scarico da bolla e il
  rientro da reso.

---

### Codici errore

I codici dei quattordici passi, nella tabella sopra. Dal passo 5-8 e dal passo 11 arriva il
**primo motivo** della check chiamata, con il suo codice.

---

### Test

* `db/pgtap/magazzino/test-fn-scrivi-movimento-controlli-v1.sql` — i passi, uno per test;
* `db/pgtap/magazzino/test-fn-scrivi-movimento-disponibilita-v1.sql`,
  `test-fn-scrivi-movimento-seriali-v1.sql`, `test-fn-scrivi-movimento-valore-v1.sql`;
* `db/pgtap/magazzino/test-porta-ledger-v1.sql` — la porta, il proprietario, il perimetro anche
  senza identità.

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§4.2), insieme alla porta
  (l'applicazione perde la scrittura sul registro e sulla copia del valore, e il guard di
  perimetro si ferma anche senza identità) e alle due check condivise.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
