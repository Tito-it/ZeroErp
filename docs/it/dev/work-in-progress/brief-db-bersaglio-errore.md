# Brief DB — l'errore porta un bersaglio, non un nome

> **Cos'è.** Il piano per far sì che un errore, oltre a *dire* cosa è successo,
> dica **su quale cosa** — in una forma che l'interfaccia possa trasformare in un
> gesto («vai lì») e che chi diagnostica possa leggere come coordinata esatta.
>
> **Perimetro: DB per primo** (decisione di Tid, 2026-08-22). La convenzione
> nasce dove l'errore viene sollevato; il consumo lato BE/FE è dichiarato in §6
> ma **non** è questo brief.
>
> ⛔ **Niente è stato applicato.** Nessuna migrazione, nessun CSV toccato.
> Questo documento è un piano.
>
> **Origine.** Collaudo della nota di credito resi, 2026-08-22. Il messaggio
> **937** dice all'operatore *«Non si può numerare il documento 835»*: una chiave
> interna dentro una frase destinata a una persona. Da lì la domanda di Tid — se
> convenisse scrivere `schema.tabella.id` (`anagrafiche.soggetti.100`) invece di
> un id nudo — e il ragionamento che ne è uscito, che è il §1.
>
> **Cosa NON è.** Non è
> [brief-db-segnaposti-messaggi-errore.md](../work-done/brief-db-segnaposti-messaggi-errore.md)
> (chiuso il 18/08): quello riguarda i `%s` che restano letterali o che fanno
> fallire il messaggio. Qui il contenitore funziona: si discute **cosa metterci
> dentro**. ⚠️ I due si toccano in un punto solo, ed è una trappola: §5.3.

---

## 1. Perché «id o frase umana» non ha una risposta

La domanda presuppone che l'errore sia **testo**. Finché lo è, ogni scelta è un
compromesso fra due lettori che non hanno bisogno della stessa cosa:

| Chi | Quando | Cosa gli serve |
| --- | --- | --- |
| Operatore, sul momento | è appena successo | **cosa faccio adesso** — non identificare una riga |
| Operatore, cinque minuti dopo | sta rimediando | **arrivare** a quel record |
| Chi diagnostica | ore o giorni dopo | coordinate esatte, più la sequenza |

Il secondo è quello che conta, ed è la chiave del disegno: all'operatore non
serve *il nome* del record — gli serve **andarci**. Un identificativo dentro una
frase, per quanto umano, resta una cosa da ricopiare a mano in un campo di
ricerca.

**Le due strade ovvie, e perché nessuna delle due basta:**

| Strada | Perché non regge |
| --- | --- |
| **Identificativo umano nella frase** | spesso **non esiste**: sul 937 il documento un numero non ce l'ha, ed è tutta la ragione dell'errore. È ambiguo (due clienti omonimi) e invecchia — la frase si compone al sollevamento, il nome può cambiare dopo |
| **`schema.tabella.id` nella frase** | per l'operatore è **più** tecnico, non meno: è l'opposto dell'obiettivo. E fa uscire i nomi delle tabelle su superfici che non sono solo interne (§4.2) |

---

## 2. La soluzione — tre strati, uno per lettore

Due dei tre esistono già e non si toccano.

| Strato | Per chi | Cosa dice | Oggi |
| --- | --- | --- | --- |
| `messaggio` | operatore | cosa è successo, in italiano, **senza identificativi** | c'è (`config.messaggi_errore.messaggio`) |
| `soluzione` | operatore | cosa fare — sul 937 è già scritta bene | c'è, poco sfruttata a video |
| **bersaglio** | interfaccia **e** diagnosi | `{ tipo, id }` | 🔴 **manca** |

Il frontend riceve il bersaglio e disegna **un gesto**, non una lettura: *«Vai al
documento»*. L'operatore non legge nessun id e nessuno schema. Chi diagnostica
legge il bersaglio nel log e ha la coordinata esatta.

⭐ **Non c'è più il compromesso**, perché i due lettori smettono di condividere
lo stesso canale.

---

## 3. Il `tipo` è un'entità logica, non una tabella

E il vocabolario **esiste già**: `vendite.event_log.entity_type` usa
`LOTTO | FATTURA | COMMESSA | TASK_RUN`.

Riusarlo vale più di quanto sembri: significa **una tabella di rotte sola** —
«portami a questa cosa» diventa una funzione unica, condivisa fra il bersaglio
di un errore e la futura timeline per entità
([analisi-osservabilita-log.md](analisi-osservabilita-log.md), Passo A). Se il
bersaglio portasse il nome della tabella, servirebbe una seconda mappa
tabella → schermata: la stessa conoscenza in due posti, cioè il modo in cui
divergono.

⚠️ **Oggi quel vocabolario non è un vocabolario**: `entity_type` è `text` libero,
senza CHECK né catalogo.

> ✅ **DECISO (Tid, 2026-08-22): catalogo chiuso, e `event_log` lo adotta.**
> Non solo il bersaglio: la stessa nozione — *«che cosa è questa entità»* —
> governata in due modi sarebbe peggio di non governarla affatto. `entity_type`
> smette di essere `text` libero e punta allo stesso catalogo.

⚠️ **Due avvertenze sull'adozione**, entrambe da verificare **prima** di posare
il vincolo:

* le righe già scritte in `event_log` vanno controllate contro il catalogo: un
  CHECK/FK su valori storici fuori vocabolario non si applica. ⚠️ Il valore di
  quelle righe è comunque discutibile (§0-bis di
  [analisi-osservabilita-log.md](analisi-osservabilita-log.md)), e su quel
  cantiere è già in discussione se azzerare la tabella: **decidere lì, non qui**;
* 🔴 **`event_log` è toccato anche dal Passo 0** di quel piano (colonna
  emittente + RLS + `correlation_id` + `actor` + `entity_id` reale). Sono
  modifiche allo stesso oggetto: **un apply solo**, o si riapre due volte la
  stessa tabella e la stessa funzione di scrittura. Chi arriva secondo eredita
  il lavoro del primo — vedi **T-1b**.

---

## 4. Dove vive il bersaglio

### 4.1 Il canale esiste ed è già in servizio

`script.fn_log_and_raise_error` ha **già** il parametro del contesto in firma:

```sql
fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text,
                       p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

`p_context` finisce in `dbops.error_log.context` (jsonb, NOT NULL, default
`'{}'`), ed è già valorizzato dalla quasi totalità dei punti di sollevamento,
nella forma libera:

```sql
jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id)
jsonb_build_object('fattura_id', p_fattura_id)
```

**Non serve macchina nuova: serve una convenzione.**

### 4.2 La forma proposta

Chiave **annidata**, non due chiavi piatte, per non collidere con le chiavi
libere già in uso (`parametro`, `valore`, `fattura_id`, …) e per essere
riconoscibile da un presidio con un solo predicato.

> ✅ **DECISO (Tid, 2026-08-22): `target` è sempre un ARRAY**, anche con un solo
> elemento. I casi a due bersagli esistono già — il **937** ne ha due, il
> documento da numerare e la fattura rettificata — e partire dal singolo
> significherebbe cambiare la forma di una chiave **già in servizio** il giorno
> che serve il secondo. Il frontend con un elemento disegna un pulsante, con due
> ne disegna due.

```sql
jsonb_build_object(
    'target', jsonb_build_array(
        jsonb_build_object('tipo', 'FATTURA', 'id', p_fattura_id)
    )
)
```

⚠️ **Mai un oggetto nudo quando l'elemento è uno**: sarebbe una seconda forma da
riconoscere, e chi consuma dovrebbe interrogare il tipo prima di iterare — cioè
esattamente il costo che l'array evita.

⚠️ **Il nome della tabella non entra mai nel bersaglio.** Non è pignoleria: il
catalogo dei messaggi è **uno solo** (`config.messaggi_errore`) e serve anche il
portale cliente e lo shop B2C (`CLIENTE_PORTALE`, `SHOP_CUSTOMER`). Un messaggio
scritto per l'operatore può affacciarsi su una superficie pubblica, e lì i nomi
delle tabelle sono ricognizione regalata. Nel `context` il nome resta comunque
dentro il database — ma il `tipo` logico è **anche** ciò che serve al frontend,
quindi non c'è ragione di avere due forme.

### 4.3 Il bersaglio è un'offerta, non una promessa

Il bersaglio può puntare a qualcosa che **chi legge non può aprire**: permessi,
perimetro emittente, record cancellato. Lato DB non c'è nulla da fare — il
bersaglio si scrive comunque — ma va dichiarato qui perché è il patto col
frontend: **il messaggio si mostra lo stesso, il pulsante non compare**. Mai un
pulsante che porta in un vicolo cieco.

📌 E ne discende una regola per il **testo**: non si nomina in chiaro una riga
che il lettore non può vedere. ⚠️ Sul 937 la questione è quasi teorica — quell'id
è il `riga_rettificata_id` di una riga che l'operatore vede legittimamente,
quindi è un dato che possiede già. Vale per gli altri messaggi, dove l'id non
sarebbe ricavabile da nulla di visibile.

---

## 5. I passi DB

### 5.1 La convenzione, e dove si scrive

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| **T-1** | Il **catalogo** dei tipi di entità | `00_schema` + `80_data` | tabella in `config`, vocabolario chiuso. È il prerequisito di tutto il resto: senza, il `tipo` è testo libero e il presidio T-4 non ha contro cosa misurare |
| **T-1b** | `event_log.entity_type` adotta il catalogo | `00_schema` | 🔴 **da coordinare col Passo 0** di [analisi-osservabilita-log.md](analisi-osservabilita-log.md): stessa tabella, stesso apply. ⚠️ Prima va deciso lì cosa fare delle righe esistenti |
| **T-2** | La forma `target` nelle linee guida | doc | `docs/it/linee-guida-sql.md`: quando un errore riguarda **una** entità identificabile, il contesto porta `target` |
| **T-3** | Il pilota: **937** | `20_code` + `80_data` | `E_FATTURA_RETTIFICATA_SENZA_NUMERO` — bersaglio sul documento da numerare **e** messaggio senza id (⚠️ §5.3) |
| **T-4** | Il presidio | pgTAP / CI | un `target` con `tipo` fuori vocabolario fa fallire |
| **T-5** | Roll-out | vari | i messaggi che oggi mettono un id nella prosa, **uno alla volta** |

### 5.2 Perché il 937 come pilota

È il caso che ha fatto nascere il brief, è **in collaudo adesso**, e ha la
proprietà che serve a un pilota: l'identificativo umano **non esiste** (il
documento non ha numero). Se il disegno regge lì, regge dove è più facile.

### 5.3 🔴 La trappola: le due modifiche del messaggio vanno insieme

Togliere l'id dalla frase significa togliere un `%s`. I valori arrivano dal
chiamante come `VARIADIC p_valori`, e il cantiere dei segnaposti ha già pagato
questa lezione: **meno valori dei segnaposto → `22023`**, cioè un errore tecnico
opaco al posto dell'errore di dominio — e il caso rotto sarebbe **proprio quello
che il messaggio esiste per gestire**.

➡️ Per ogni messaggio toccato, **catalogo e chiamanti nello stesso changeSet**.
Mai il CSV per primo.

### 5.4 Cosa NON si fa

- ⛔ **Non si riscrivono i 756 messaggi.** Il bersaglio si aggiunge solo dove un
  identificativo serve davvero — cioè dove oggi c'è un id nella prosa;
- ⛔ **Non si tocca `error_log`**: la colonna `context` c'è già ed è jsonb;
- ⛔ **Non si tocca l'envelope API**: è §6, lato BE.

---

## 6. Cosa tocca dopo, e a chi *(dichiarato, non pianificato qui)*

| | Chi | Cosa |
| --- | --- | --- |
| **B-1** | BE | portare `target` nell'envelope d'errore, accanto a `code` / `message` / `ui_action` / `fields` |
| **B-2** | FE | il gesto: da `target` a una rotta. ⭐ È la **stessa** tabella di rotte della timeline per entità (§3): si scrive una volta |
| **B-3** | FE | il degrado di §4.3 — bersaglio non risolvibile → nessun pulsante, messaggio invariato |

⭐ **Un effetto laterale che vale da solo**: `ui_action` oggi è un canale
prodotto e non consumato — 126 codici promettono «evidenzia il campo» e nessun
componente legge `azioneUi`. Un errore che porta un bersaglio è il primo pezzo di
frontend che ha una **ragione** per leggere quel canale, e rende scrivibile il
presidio **C2** di
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).

---

## 7. Domande

### Chiuse — 2026-08-22, da Tid

1. ✅ **Il vocabolario dei tipi: CATALOGO CHIUSO**, e `event_log.entity_type` lo
   adotta. Motivo: la stessa nozione governata in due modi è peggio che non
   governarla. Conseguenze operative in §3 e nei passi **T-1** / **T-1b**.
2. ✅ **Il bersaglio è SEMPRE UN ARRAY**, anche con un elemento solo. Motivo: i
   casi a due bersagli esistono già (il 937), e cambiare la forma di una chiave
   in servizio costa più che nascere larghi. Forma in §4.2.

### Aperte — non bloccano la scrittura

3. 🔵 **`error_log` diventerà leggibile in-app?** Se sì il `context` smette di
   essere solo diagnostico e diventa una superficie: cambia cosa è lecito
   scriverci. Domanda gemella del Passo 3 di
   [analisi-osservabilita-log.md](analisi-osservabilita-log.md).
4. 🔵 **Il catalogo messaggi distingue le superfici?** Operatore, portale
   cliente, shop leggono lo stesso `config.messaggi_errore`. ⚠️ È più grossa di
   questo brief e non lo blocca, ma è la domanda che gli sta sotto.

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-22 (secondo giro) | ✅ **Chiuse le due domande che bloccavano la scrittura**, entrambe verso la forma più larga: **catalogo chiuso** per i tipi (con `event_log.entity_type` che lo adotta — nasce **T-1b**) e **`target` sempre array**. ⭐ Nessuna delle due è una preferenza di stile: la prima evita due vocabolari per la stessa nozione, la seconda evita di cambiare la forma di una chiave **già in servizio** il giorno del secondo bersaglio — e il secondo bersaglio esiste già oggi, sul messaggio pilota. 🔴 **Ne discende un vincolo di coordinamento che prima non c'era**: T-1b tocca `event_log`, che è anche l'oggetto del **Passo 0** dell'osservabilità (emittente + RLS + correlation + actor). Stessa tabella, stessa funzione di scrittura: **un apply solo**, e la sorte delle righe storiche si decide di là, non qui |
| 2026-08-22 | Stesura, su richiesta di Tid dopo il collaudo NC resi. ⭐ **Il disegno è cambiato durante la discussione, ed è la parte utile**: la proposta di partenza era `schema.tabella.id` nel messaggio; ragionandoci è emerso che la domanda «id o frase umana» **non ha risposta** perché presuppone che l'errore sia testo, e che all'operatore non serve il *nome* del record ma **arrivarci**. Da lì i tre strati e il bersaglio. ⭐ Il canale c'è già (`p_context` → `dbops.error_log.context`) e la quasi totalità dei sollevamenti lo valorizza: manca la **convenzione**, non la macchina. 🔴 Segnalata la trappola §5.3 (catalogo e chiamanti nello stesso changeSet, lezione del cantiere segnaposti). ⛔ Nulla applicato |

---

*Brief DB — il bersaglio dell'errore (22 agosto 2026).*
