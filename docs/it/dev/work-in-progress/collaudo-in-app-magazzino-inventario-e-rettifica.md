# Collaudo in-app · Magazzino: il primo carico da video

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano: il *perché* sta in
> [piano-be-fe-magazzino-lotto-2-motore.md](piano-be-fe-magazzino-lotto-2-motore.md)
> (§5, §8 — il copione in forma breve) e nel brief chiuso
> [brief-db-magazzino-lotto-2-bis-be-fe.md](../work-done/brief-db-magazzino-lotto-2-bis-be-fe.md)
> (R-1 … R-7). Qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se
> non succede**.
>
> **Perché esiste.** Il Lotto 2 è chiuso a codice su tutti i lati: DB
> applicato (R-1 … R-7, pgTAP verdi), BE con tre prove sul DB vero (la matrice,
> i tre motivi di «Registra», il duplicato di posizione), smoke
> `smoke-magazzino-inventario-primo-carico.py` 12/12. Ma **nessun test monta il
> drawer**: la barra delle azioni regge solo sul pinning dei **nomi** del blob
> lato BE. Un campo letto col nome sbagliato non fa fallire niente: lascia un
> pulsante grigio che sembra una regola, o una barra vuota. E il frontend del
> magazzino **non è mai stato aperto a video**.
>
> **Stato**: ✏️ scritto il 2026-09-25, da eseguire.
> **Ambiente**: sviluppo (`dbdev`). **Utente**: un operatore con l'area
> magazzino in scrittura **e** l'azione di processo `registra_magazzino`; per
> il §6 un secondo operatore **senza** quell'azione e uno di **un altro
> emittente**.
> **Dove**: menu Magazzino → *Inventari*, *Rettifiche*, *Disponibilità*,
> *Movimenti*.

---

## ⛔ Prima di cominciare

Il dato del copione va **costruito**: al 2026-09-25 su `dbdev` c'è un solo
magazzino (`TEST`, a ubicazioni, **una** ubicazione), nessun articolo gestito
con lotto, nessun movimento, un inventario in bozza e una rettifica.

| | Cosa | Perché conta |
| --- | --- | --- |
| **Magazzino senza ubicazioni** | Crealo da Magazzino → *Magazzini* (`usa_ubicazioni` spento) | Il §1 è il caso semplice: nessun campo ubicazione nella riga |
| **Magazzino a ubicazioni** | `TEST` va bene, ma servono **due** ubicazioni: chiamale `UX` e `UY` | Il §2 conta in UY con la merce in UX |
| **Articolo gestito, semplice** | Un articolo con «Gestito a magazzino» acceso, senza lotto né seriale | Il carico base |
| **Articolo gestito con lotto** | «Gestito a magazzino» + «Richiede lotto» acceso, e **un** lotto attivo (Configurazione → Tabelle → Lotti) | Il §3.3 e il campo lotto che compare solo per lui |
| **Articolo non gestito** | Uno qualunque senza «Gestito a magazzino» (ce ne sono 254) | Il §3.1: la riga si salva ma non si registra |
| **Operatori** | Un operatore **di un altro emittente**: al 2026-09-25 `test_flusso_b` non vede l'emittente di `TEST`. Uno **senza** `registra_magazzino` | Il §6 |

⚠️ Il costo unitario vuoto vuol dire «alla media corrente del registro»: nel
§1 scrivilo (7 €), nel §4 lascialo vuoto apposta.

---

## 1. Il primo carico: inventario sul magazzino senza ubicazioni

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Inventari → «Nuovo»: magazzino **senza ubicazioni**, data oggi, una descrizione → «Apri» | Il dialog si chiude e si apre il **drawer** del documento, in bozza. Il magazzino non è più modificabile | Se il drawer non si apre da solo, il dialog non passa l'id: il documento c'è in lista |
| **1.2** | Guarda la barra del drawer in bozza | **«Conferma»** e **«Annulla»** accesi; **«Registra» c'è ma è spento**, e il tooltip dice *«Il documento non è ancora confermato…»* | Barra vuota = il drawer non legge `detail.capabilities`. «Registra» **assente** invece che spento = è tornato un `v-if` sullo stato |
| **1.3** | «Nuova riga»: l'articolo **semplice**, quantità contata 10, costo 7 → Salva | La riga è in lista; **nessun** campo ubicazione, lotto o seriale nel form | Se compare l'ubicazione, il form non legge `usa_ubicazioni` del magazzino |
| **1.4** | «Conferma» → accetta la conferma | Stato **Confermato**; il **piano si apre da solo** con una riga **Carico iniziale**, contata 10 | Piano che non si apre = Q-5 non è agganciato al cambio stato riuscito |
| **1.5** | Chiudi il piano. Guarda righe e barra | Righe **in sola lettura** (*«Le righe si scrivono solo in bozza…»*); «Registra» **acceso**; «Riapri» e «Annulla» presenti; «Piano» col badge | — |
| **1.6** | «Registra» | La conferma dice che è **irreversibile** e porta il riepilogo (*«1 con differenza · 0 non contate…»*). Conferma → toast *«Registrato: 1 movimenti sul registro.»* | — |
| **1.7** | Guarda il drawer dopo la registrazione | Il drawer **resta aperto**, stato **Registrato**, tutto in sola lettura; la nota di stato *«Registrato: i movimenti sono sul registro…»* compare **una volta sola**; «Registra» spento con *«…già registrato…»* | Due note uguali = la copia sulla testata è tornata |
| **1.8** | Lista inventari → kebab della riga | «**Movimenti**» c'è, «Elimina» no. «Movimenti» apre il registro col chip *«Movimenti dell'inventario #N»* e **un** movimento | Registro vuoto col chip = il filtro `inventario_id` non arriva, o il floor data lo taglia |
| **1.9** | Disponibilità → scheda per magazzino | L'articolo sul magazzino a **10** | — |

---

## 2. Le posizioni non contate: il caso di Tid (D-L2-n)

Sul magazzino **a ubicazioni**, con merce già in `UX`.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | Se `UX` è vuota: un primo inventario che conta 5 in `UX` → Conferma → Registra (come il §1) | Disponibilità a 5 su `TEST` | — |
| **2.2** | Nuovo inventario su `TEST`: riga stesso articolo, **12 in `UY`** | Nel form c'è il campo **Ubicazione**: lo decide il magazzino (`usa_ubicazioni`), non l'articolo | Campo assente = il form non legge `usa_ubicazioni` dal dettaglio |
| **2.3** | «Conferma» | Il piano si apre con **due** righe: `UY` **Carico** 12, e `UX` **Non contata**, in giallo | Se `UX` non c'è, il piano non vede la merce a registro: fermati, è il difetto che D-L2-n doveva togliere |
| **2.4** | Leggi l'aiuto del piano e la conferma di «Registra» | Le non contate **restano come sono**: la conferma dice *«… 1 non contate, che restano come sono.»* | — |
| **2.5** | «Registra» → Disponibilità | Il totale è **17** (5 in UX + 12 in UY), non 12 | 12 = la non contata è stata azzerata |

---

## 3. Le righe che non passano

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Nuovo inventario → riga: cerca l'articolo **non gestito** | ⭐ **Non lo trovi**: il picker propone solo gli articoli gestiti a magazzino (R-5) | Se compare, il filtro `gestitiAMagazzino: 'solo'` non arriva al lookup |
| **3.2** | (Solo se vuoi vedere l'anteprima gialla) spegni «Gestito a magazzino» su un articolo **dopo** averlo messo in una riga in bozza, poi riapri la riga | Nel form un avviso giallo *«…non sarà registrabile»*; il Salva **resta acceso** (Q-3). Confermando, il piano la mostra **Non registrabile** in rosso col motivo nel tooltip, e **«Registra» è spento** con *«Una o più righe non passerebbero…»* | Salva bloccato = una regola più stretta del modello, scritta nel FE |
| **3.3** | Riga sull'articolo **con lotto**, senza scegliere il lotto → Salva | Il campo **Lotto** compare solo per questo articolo. Il salvataggio passa in bozza con l'avviso giallo; il piano la dà **Non registrabile** | Se il campo lotto non compare, il form non legge `requires_lotto` dalla riga dell'articolo scelto |
| **3.4** | Due righe con **stesso articolo e stessa posizione** nello stesso inventario | Rifiuto con un messaggio sul duplicato e il campo **Articolo acceso** in rosso (R-2) | Un errore generico senza campo = il `23505` non è tradotto |
| **3.5** | 🔴 Forza la mano: con una riga non registrabile in Confermato, chiama `POST …/registra/` via API | Rifiuto, e il documento **resta in Confermato**, zero movimenti | Se registra qualcosa, il guard a DB non morde: fermati e segnala |

---

## 4. La rettifica

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Rettifiche → «Nuovo» sul magazzino **senza ubicazioni** (quello del §1) | Il dialog **non** chiede la descrizione; si apre il drawer | — |
| **4.2** | Riga: stesso articolo del §1, correzione **−5**, un motivo, costo **vuoto** | Il campo è «Correzione» (non «Quantità contata»), c'è il **motivo**; con 0 il form rifiuta | — |
| **4.3** | Il drawer della rettifica | ⛔ **Nessun** pulsante «Piano»: il piano è solo dell'inventario | — |
| **4.4** | Conferma → Registra | 1 movimento; Disponibilità a **5**; il movimento sul registro ha il costo **alla media** (7 €) | — |

---

## 5. Gli stati

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **5.1** | Un documento in **Confermato** → «Riapri» | Torna in **Bozza**, le righe si riaprono | — |
| **5.2** | Un documento in **Bozza** → «Annulla» | La conferma porta l'etichetta **«Annulla»** (non «Elimina» col cestino); stato **Annullato**, nota *«Annullato: il documento è chiuso…»*, nessuna azione di stato | Cestino e «Elimina» = la conferma prende icona ed etichetta dalla severità, non dal dato |
| **5.3** | Lista → kebab di un documento **Registrato** | «Elimina» **non c'è**. Nel drawer la testata non si modifica | — |
| **5.4** | Lista → kebab di un documento in **Bozza** → «Elimina» | Il documento sparisce dalla lista | — |
| **5.5** | Nel drawer di un documento **non in bozza**, prova a cambiare il magazzino | Non si può: il magazzino è fisso dalla nascita (R-4, lucchetto a DB) | — |

---

## 6. Chi può che cosa

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **6.1** | Entra con l'operatore **senza** `registra_magazzino`, apri un documento Confermato | «Registra» **non c'è** (è un'azione pericolosa: si nasconde, non si spegne) | Se c'è e risponde 403, il gate FE non legge l'azione |
| **6.2** | Entra con l'operatore di **un altro emittente** (`test_flusso_b`) | Inventari, rettifiche, disponibilità e movimenti di `TEST` **non si vedono**; un deep-link al drawer di un documento di `TEST` dà *non trovato* e chiude il drawer | Se li vede, la RLS non è quella attesa: fermati e segnala |

---

## 7. 🔴 I punti già noti, da confermare a video

| | Cosa | Dove sta scritto |
| --- | --- | --- |
| **Testata** | Fuori da bozza la testata (data, descrizione) **a DB** resta modificabile: è una scelta (Q-2). A video il form è in sola lettura | piano §10, Q-2 |
| **Prontezza** | Il presidio `NESSUNO_MARCATO` non ha UI: suona nel digest settimanale finché nessun articolo è gestito a magazzino | piano §6 |
| **Barra** | Nessun presidio automatico FE della barra: questo collaudo **è** il presidio | brief 2-bis, §A BE/FE |

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-25** | ✏️ Stesura, dal copione breve del piano (§8, a-g), alla chiusura del brief 2-bis (archiviato in `work-done/` lo stesso giorno). Tutto a codice, **niente visto a video** |
