# Brief DB — Il perimetro dell'emittente si ferma alla testata

> ⭐ **DOVE SIAMO, 2026-09-10.** Gli otto passi del cantiere originale sono
> chiusi (2026-09-09) e da allora il lavoro lo consegna il **presidio** del §11,
> non più un elenco: **sei famiglie applicate** — `pratiche` (§11.7), `lotti`
> (§11.9), `vendite_contabili_lotti` (§11.10), `listini` (§11.11), `commesse`
> (§11.15), `documenti` (§11.16) — e il registro del debito sceso da **33 a 12
> righe** in due giorni.
> `db/pgtap/rls/`: **36 file su 36 verdi**, zero rossi — misurato il 2026-09-10
> dopo l'apply di `commesse`. ⚠️ I file sono poi diventati **37** con
> `test-rls-documenti-satelliti.sql` (13/13 nella sua prova, e nessuna
> regressione riportata dopo l'apply): la corsa dell'intera cartella a 37 non è
> stata rifatta.
> ⭐ **Lo schema `vendite` è finito**: delle 12 righe rimaste due sono sue, e
> tutte e due sono domande di modello, non armamenti. Il fronte è ora
> `anagrafiche` e le singole di `config`/`magazzino`/`pagamenti`/`shop`.
>
> Stato del cantiere originale: ✅ **TUTTI E OTTO I PASSI APPLICATI** — su
> database di sviluppo e su database ricostruito dai changelog.
> `db/pgtap/rls/`: **30 file su 30 verdi** *(fotografia del 2026-09-09: i file
> erano trenta, oggi sono trentasei)*.
> Analisi e realizzazione del 2026-09-09.
>
> ✅ **DA LEGGERE PER PRIMO: il §11.** Il presidio che il §10 dichiarava «la
> cosa da fare per prima» è **scritto e APPLICATO** (slice `20260909-75..77` +
> `db/pgtap/rls/test-rls-perimetro-scoperto.sql`): applicato su dbdev il
> 2026-09-09 alle 22:52, e **verde in CI su database ricostruito da zero**.
> ⛔ E ha portato un fatto che cambia il §10: applicato a **tutto** il database
> invece che al solo `vendite`, lo stesso criterio non trova dodici tabelle
> scoperte ma **trenta**, più tre con una policy che non filtra.
> Origine: `migliorie-generali-da-test-valutazione.md` §D2.
> ⚠️ **D3 (lo `storico` senza RLS) è deliberatamente FUORI da questo brief**:
> decisione di Tid del 2026-09-09, e il motivo sta in fondo (§9).
>
> | Famiglia | Slice | Stato |
> | --- | --- | --- |
> | `preventivi` | `20260909-27..30` | ✅ **applicata**, pgTAP verde su dbdev e sul database ricostruito |
> | `ordini` | `20260909-33..35` | ✅ **applicata**, pgTAP verde su dbdev e sul database ricostruito |
> | `ddt` | `20260909-36..38` | ✅ **applicata** (17:12), pgTAP 10/10 verde; l'intera cartella `db/pgtap/rls/` verde su entrambi i database, nessuna regressione |
> | `resi` | `20260909-40..42` | ✅ **applicata** (17:35), pgTAP 10/10 verde |
> | `contratti` | `20260909-43..46` | ✅ **applicata** (18:19), pgTAP 10/10 verde. Porta anche l'aggiornamento della fixture `fn_pgtap_crea_cliente_ba` (`-43`) |
> | `offerte_commerciali` | `20260909-47..49` | ✅ **applicata** (18:43), pgTAP 11/11 verde |
>
> | Passo | Slice | Stato |
> | --- | --- | --- |
> | 7 — il resto di `fatture` | `20260909-69..71` | ✅ **applicato** (19:34), pgTAP 12/12 verde |
> | 8 — il padre `vendite.note` | `20260909-72..74` | ✅ **applicato** (19:49), pgTAP 9/9 verde. Ha ribaltato il test 11 di `test-rls-offerte-satelliti.sql` da «asserisce il buco» a «asserisce la difesa» |
>
> ✅ **Debito dei rimandi: sanato, ed era più grosso del previsto.** Cercando i
> due `COMMENT ON` di questo cantiere ne sono saltati fuori **24** in tutto il
> database, di cui **21 già morti** (documento spostato in `work-done/`).
> Rimedio: `20260909-39`, **applicato**: li riscrive tutti togliendo il solo
> prefisso di percorso — il testo non viene ricopiato, viene letto da
> `pg_description`. Verificato dopo l'apply: **zero** commenti vivi col path.
> Sul filesystem sono stati corretti anche i commenti `#` di **299** YAML e le
> intestazioni di **51** pgTAP (gratis: non entrano nel checksum), verificando
> che l'SQL estratto dai changelog non cambiasse di un byte.
>
> Fixture nate strada facendo, e riusabili da qui in avanti:
> `dbops.fn_pgtap_crea_emittente_operatore()` (`20260909-26`, valuta in `-32`) e
> `dbops.fn_pgtap_crea_cliente_ba()` (`20260909-31`).

---

## 1. Il difetto, detto sul modello

> **Una riga di documento appartiene all'emittente della sua testata.**

È una proprietà del modello, non una conseguenza di come l'applicazione legge
oggi. Ne segue che il perimetro deve valere **ovunque quella riga sia
leggibile** — non solo lungo il percorso che il frontend usa adesso.

Oggi non è così. Delle sei famiglie di documento di `vendite`, **una sola è
protetta fino in fondo**: `fatture`. Le altre cinque hanno la policy sulla sola
testata, e le loro righe sono leggibili da qualunque operatore.

⛔ **Anche questa frase era troppo generosa, e l'ho scoperto al passo 7**:
nemmeno `fatture` era protetta fino in fondo — erano protette le cinque figlie
che l'elenco del §2 nominava, e ce n'erano altre sei più una nipote. La
correzione è nel §2; lo stato di arrivo nel §10.

⛔ **E l'obiezione «tanto si passa sempre dalla testata» non regge**, per due
ragioni indipendenti:

* è un'affermazione sul **codice di oggi**, non sul modello. Il giorno in cui
  qualcuno scrive una query che parte dalla riga, il perimetro non c'è — e non
  se ne accorge nessuno, perché il sintomo è *vedere di più*, non un errore;
* **esiste già un controesempio**, e non è ipotetico. Vedi §3.

---

## 2. Il fatto, datato 2026-09-09 — lo stato DI PARTENZA

⚠️ **Questa tabella non si aggiorna: è la fotografia da cui il cantiere è
partito**, e va letta come tale. Lo stato di arrivo è nel §10.

Letto dal catalogo di `zeroerp` (struttura, non popolazione):

| Famiglia | Testata | Figlie e nipoti |
| --- | --- | --- |
| `fatture` | ✅ 2 policy | 🟠 **protette le cinque portanti** — `righe`, `scadenze`, `riepiloghi_iva`, `indirizzi`, `fondi_fattura_source` — ma **non tutte**: vedi la correzione qui sotto |
| `ordini` | ✅ 3 policy | ⛔ nessuna |
| `preventivi` | ✅ 1 policy | ⛔ nessuna |
| `ddt` | ✅ 1 policy | ⛔ nessuna |
| `contratti` | ✅ 1 policy | ⛔ nessuna |
| `resi` | ✅ 1 policy | ⛔ nessuna |
| `offerte_commerciali` | ✅ 1 policy | ⛔ nessuna |

**31 tabelle distinte** di `vendite` hanno una FK verso una di quelle testate (o
verso una loro figlia) e nessuna policy. Le dieci portanti — le `*_righe`, gli
`*_indirizzi`, `preventivi_riepiloghi_iva` — hanno tutte `SELECT` per
`zeroerp_app`.

⛔ **Correzione del 2026-09-09, e riguarda la riga `fatture` qui sopra.** Dire
«tutte protette» era sbagliato: erano protette le **cinque che avevo elencato**,
cioè quelle che avevo guardato. Riletto il catalogo per FK invece che a memoria,
`vendite.fatture` ha **altre sei figlie dirette scoperte**:

`fatture_atti` · `fatture_fondi_fattura` · `fatture_log` · `fatture_rettifiche`
· `fatture_sdi` · `note_fatture`

⭐ È lo stesso difetto che questo brief denuncia, in miniatura: *un elenco scritto
a mano è il perimetro di ciò che chi scriveva aveva in mente, non del modello.*
Ed è esattamente la ragione per cui il presidio del §8 deve avere un criterio
**transitivo** — «ogni tabella con una FK verso una tabella in RLS» — e non una
lista.

⚠️ Nessuna di quelle sei era coperta dai sei passi del §7: `fatture` non era un
passo, perché il brief la dava per fatta.

✅ **Chiuso dal passo 7** (`20260909-69..71`), che ne prende **sette**: le sei
qui sopra più la nipote `fatture_sdi_eventi`, che pende da `fatture_sdi`. Non era
«la slice più corta di tutte» come avevo scritto: `vendite.fatture` è l'unica
testata del brief con **due vesti**, quindi sono sette tabelle × due =
**quattordici policy**, e l'unico helper mancante era quello a due livelli per
gli eventi SDI.

---

## 3. Il controesempio che esiste già

`vendite.vw_preventivi_righe_dettaglio` legge `preventivi_righe` **senza passare
dalla testata**: le sue dipendenze sono `catalogo.articoli`,
`catalogo.unita_misura`, `config.iva` e `vendite.preventivi_righe` — la tabella
`preventivi` non compare. La vista è concessa in `SELECT` a `zeroerp_app`.

⇒ Articolo, quantità, prezzo e descrizione delle righe di preventivo di **ogni**
emittente passano da lì, oggi.

⭐ **E c'è un dettaglio che chiude il ragionamento.** Delle 60 viste di
`vendite`, 58 hanno `security_invoker`. Le due che non ce l'hanno sono
`vw_preventivi_righe_dettaglio` e `vw_preventivi_riepilogo_iva_dettaglio` —
esattamente le due che leggono i satelliti di `preventivi`. Il presidio
`db/pgtap/rls/test-rls-viste-security-invoker.sql` su di esse **tace
legittimamente**, perché il suo criterio è «tocca dati protetti da RLS» e quei
dati protetti non sono. *La difesa di secondo livello si spegne da sola quando
manca quella di primo.*

⚠️ Corollario operativo: nel momento in cui `preventivi_righe` riceve una policy,
quelle due viste diventano un buco — e il presidio le vede. Le due cose vanno
nello stesso changeSet.

✅ **Sanato dal passo 1** (`20260909-29`): entrambe le viste hanno oggi
`security_invoker`, verificato il 2026-09-09 a cantiere chiuso. Il controesempio
non esiste più — ed è l'unico punto del brief in cui una *fuga provata*, non
soltanto possibile, è stata chiusa.

---

## 4. Il modello da copiare: la famiglia `fatture`

Ogni satellite di `fatture` ha **due** policy:

```sql
-- operatore: il perimetro dell'emittente
CREATE POLICY rls_fatture_righe_ef_whitelist ON vendite.fatture_righe
FOR ALL USING (
    current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
AND script.fn_scope_ef_whitelist_via_fattura(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        fattura_id)
) WITH CHECK ( … stessa condizione … );

-- cliente del portale: la proprietà del BA
CREATE POLICY rls_fatture_righe_ba_ownership ON vendite.fatture_righe
FOR SELECT USING (
    current_setting('app.ruolo_applicativo', true) = 'CLIENTE_PORTALE'
AND script.fn_scope_ba_ownership_via_fattura(…, fattura_id)
);
```

E l'helper è tre righe:

```sql
-- script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id, p_fattura_id)
SELECT script.fn_scope_ef_whitelist_via_sr(
    p_auth_user_id,
    (SELECT f.emittente_soggetto_ruolo_id FROM vendite.fatture f WHERE f.id = p_fattura_id)
);
```

⭐ **Per le altre cinque famiglie è ancora più semplice.** `fatture` porta
`emittente_soggetto_ruolo_id` e deve passare dall'adattatore `_via_sr`; `ordini`,
`preventivi`, `ddt`, `contratti`, `resi` e `offerte_commerciali` portano
**`emittente_fiscale_id`** e le loro policy di testata usano già
`script.fn_scope_ef_whitelist(user, emittente_fiscale_id)` diretta. Quindi
l'helper nuovo è:

```sql
CREATE FUNCTION script.fn_scope_ef_whitelist_via_ordine(
    p_auth_user_id integer,
    p_ordine_id    vendite.ordini.id%TYPE
) RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT o.emittente_fiscale_id FROM vendite.ordini o WHERE o.id = p_ordine_id));
$$;
```

⚠️ `STABLE`, non `IMMUTABLE`, e **non** `SECURITY DEFINER`: è la postura degli
otto `fn_scope_*` esistenti, verificata. Una policy che chiamasse una funzione
`SECURITY DEFINER` guarderebbe con gli occhi dell'owner, cioè non guarderebbe.

**Sei helper nuovi**, uno per testata. Per i **nipoti** (`*_righe_componenti`)
l'helper risale di due livelli, oppure la policy richiama quello della figlia
passando la sua chiave: si sceglie caso per caso, e la seconda forma evita di
moltiplicare le funzioni.

---

## 5. Le tabelle, famiglia per famiglia

Elenco completo, dal catalogo. **Livello 1** = FK diretta alla testata;
**livello 2** = FK a una figlia di livello 1.

### `ordini` — 5 tabelle

* **L1**: `ordini_righe`, `ordini_indirizzi`, `note_ordini`
* **L2**: `ordini_righe_componenti`, `ordini_righe_fulfillment` (§6.2)

### `preventivi` — 5 tabelle

* **L1**: `preventivi_righe`, `preventivi_indirizzi`, `preventivi_riepiloghi_iva`, `note_preventivo`
* **L2**: `preventivi_righe_componenti`

### `ddt` — 6 tabelle

* **L1**: `ddt_righe`, `ddt_indirizzi`, `note_ddt`
* **L2**: `ddt_righe_componenti` — e basta: `ordini_righe_fulfillment` e `resi_righe_riconsegne` vanno con la LORO famiglia (§6.2)

### `contratti` — 8 tabelle

* **L1**: `contratti_righe`, `contratti_indirizzi`, `contratti_utilities`, `note_contratto` — `fatture_atti` va con `fatture` (§6.3) e `attivita_fatturabili` passa da `commesse` (§6.1)
* **L2**: `contratti_righe_componenti`, `note_attivita_fatturabili`

### `resi` — 4 tabelle

* **L1**: `resi_righe`
* **L2**: `resi_righe_accrediti`, `resi_righe_riconsegne` (§6.2), `resi_righe_rinunce`

### `offerte_commerciali` — 5 tabelle

* **L1**: `offerte_commerciali_eccezioni`, `offerte_commerciali_indirizzi`, `offerte_commerciali_utilities`, `note_offerte_commerciali`
* **L2**: `offerte_commerciali_eccezioni_componenti`

**Totale: 31 tabelle distinte.** Due compaiono sotto due famiglie e vanno con la propria (§6.2); due escono dal giro perche' si agganciano altrove (§6.1, §6.3).

---

## 6. I casi che sembravano ambigui, e non lo erano

⭐ **Questa sezione è stata riscritta il 2026-09-09 dopo le obiezioni di Tid.**
Tre dei quattro casi che avevo dichiarato «da decidere» non lo erano: bastava
guardare la nullabilità delle chiavi invece di fermarsi al numero delle FK.
Resta un solo caso aperto, ed è il più piccolo.

### 6.1 ✅ `attivita_fatturabili` — la sorgente c'è, ed è `commessa_id`

Avevo scritto «crocevia, cinque FK, ambiguo». È sbagliato: le FK non pesano
uguale, e la nullabilità le ordina.

| Colonna | Nullable |
| --- | --- |
| `commessa_id` | **NO** |
| `commessa_attivita_id` | **NO** |
| `billing_account_id` | sì |
| `contratto_id` | sì |
| `fattura_riga_id` | sì |

⛔ **La rotta portante è `commessa_id`, non il billing account.** Tid osservava
che senza BA non si può fatturare, e sul dominio è vero — ma il modello **ammette
oggi** il NULL, e una policy costruita su una chiave nullable ha un buco esatto
dove il NULL passa. È la trappola del NULL nelle chiavi, già scritta nelle linee
guida.

⭐ E `commessa_id` è la scelta buona anche per un secondo motivo: `vendite.commesse`
**è già protetta**, e `script.fn_scope_ef_whitelist_via_commessa` **esiste già**.
Zero helper nuovi, zero decisioni.

⚠️ Resta una domanda vera ma separata: *`billing_account_id` dovrebbe essere
`NOT NULL`?* Se la risposta è sì, è un cantiere suo — non si risolve mettendoci
sopra una policy.

### 6.2 ✅ Le tabelle «a doppia famiglia» discendono dalla propria testata

`ordini_righe_fulfillment` e `resi_righe_riconsegne` hanno **entrambe le FK
`NOT NULL`** — verso la riga d'ordine (o di reso) e verso la riga di DDT. Non
sono ambigue: appartengono al mondo del proprio documento, e il perimetro si
risolve di lì.

* `ordini_righe_fulfillment` → `ordini_righe` → `ordini`
* `resi_righe_riconsegne` → `resi_righe` → `resi`

⭐ E la coerenza fra i due lati non è lasciata al caso: **tutte e sette le
testate hanno un guard** `vendite.trgfn_<documento>_guard_emittente_ba`
(commesse, contratti, ddt, offerte_commerciali, ordini, preventivi, resi), più
`anagrafiche.fn_check_ba_coppia_emittente_omogenea`. L'emittente di un documento
è legato al suo BA da un presidio, non da una convenzione.

⚠️ **La domanda residua, e non blocca**: esiste un guard che imponga che il DDT
collegato condivida l'emittente dell'ordine che evade? Se non c'è, è un guard
mancante — **non** un problema di policy. Una policy non è il posto dove si
decide a chi appartiene una riga: lì si applica una decisione già presa.

### 6.3 ✅ `fatture_atti` va con `fatture`

Figlia di `contratti` **e** di `fatture`. `fatture` è protetta e
`fn_scope_ef_whitelist_via_fattura` è già scritta: si aggancia lì, e non serve
niente di nuovo.

### 6.4 ⛔ Le sette `note_*` sono PARTIZIONI, e la partizione non basta

Avevo scritto «polimorfe, servono un meccanismo loro». Sbagliato, e la struttura
lo dice a chiare lettere: in **tutte e sette** le tabelle

* `target_id` è **`NOT NULL`** e ha una **FK vera verso la testata**
  (`note_ordini.target_id` → `vendite.ordini`, `note_ddt.target_id` →
  `vendite.ddt`, e così via);
* `target_riga_id` è nullable e punta alla riga.

Non c'è nessun polimorfismo da risolvere: **ogni tabella di note è già
partizionata per famiglia**, e `target_tipo` è un'etichetta vincolata da un
`CHECK`, non un discriminante da interpretare a runtime. Tid aveva ragione — «le
note rispettano le sorgenti» — ed è letteralmente così, con una FK.

⇒ La policy è lo stesso monoriga di tutte le altre, sulla chiave `target_id`.
Ogni tabella di note va **con la propria famiglia**, non in un giro a parte.

⚠️ E `note_fatture` oggi non è protetta pur appartenendo a una famiglia che lo
è: è la conferma che il giro delle note fu saltato tutto insieme, non che avesse
un problema suo.

---

#### ⛔ La correzione del 2026-09-09: «le più facili» era sbagliato

Questa sezione si intitolava *«le sette `note_*` seguono il loro target, e sono
le più facili»*, e la parte sul `target_id` resta vera. È falsa la conclusione:
**le sette tabelle non sono tabelle**, sono **partizioni** di `vendite.note`,
che è una tabella partizionata con la **RLS spenta** e su cui `zeroerp_app` ha
`SELECT, INSERT, UPDATE, DELETE`.

⇒ **Una policy sulla partizione non chiude niente, se il padre è aperto.**
Misurato (2026-09-09, due emittenti costruiti, `note_ddt` già armata):

| Da dove si legge | Righe viste dall'operatore di A |
| --- | --- |
| `vendite.note_ddt` — la partizione, con la sua policy | **1** — la propria |
| `vendite.note` — il padre partizionato | **2** — anche quella di B |

⭐ **E la seconda misura dice come si ripara.** Accendendo la RLS sul padre
*senza* dargli una policy, il padre risponde **0**: le policy delle partizioni
**non risalgono**. Quindi non basta armare il padre — gli serve una **policy
sua**, che smisti su `target_tipo` verso l'adattatore giusto.

⚠️ **Perché è un passo A PARTE, e non un pezzo di ciascuna famiglia.** La policy
del padre è **una sola** e le nomina **tutte e sette**: non può nascere finché
manca anche un solo adattatore. Oggi mancano `_via_offerta` (arriva col passo 6)
e quello per `ATTIVITAFT`, che dipende dalla decisione aperta del §6.1. ⇒ La
policy *sulla partizione* resta con la sua famiglia — serve, ed è ciò che
protegge l'accesso diretto, che è **l'unico che il backend usa oggi**
(`partitioned_note_repository.py` interroga sempre `vendite.note_<tipo>`, mai il
padre). Ma **chiudere** il buco è un passo suo, e viene dopo.

⛔ **E tre partizioni non hanno policy nemmeno sulla partizione**:
`note_fatture`, `note_offerte_commerciali`, `note_attivita_fatturabili`.

⚠️ Fuori perimetro ma da sapere: `magazzino.note`, `acquisti.note` e
`catalogo.note` sono partizionate allo stesso modo e nella stessa condizione.

#### ✅ Come è stato chiuso — slice `20260909-72..74`

Tre policy sul **padre**, una per veste, che smistano su `target_tipo` verso
l'adattatore della famiglia:

| Veste | Copre | Perché |
| --- | --- | --- |
| `OPERATORE` (`FOR ALL`) | tutte e sette | ogni famiglia ha la veste operatore |
| `CLIENTE_PORTALE` (`FOR SELECT`) | solo `FATTURA` e `ORDINE` | sono le uniche due partizioni che concedono una veste cliente |
| `SHOP_CUSTOMER` (`FOR SELECT`) | solo `ORDINE` | e con la doppia condizione (proprietà **e** canale `SHOP`) che pretende la testata |

⭐ È l'**unione esatta** di ciò che le sette partizioni già concedono: il padre
non apre niente in più e non chiude niente che una partizione conceda.

⛔ **La riga che decide il futuro è l'`ELSE false`.** Un `target_tipo` non
gestito rende quelle note **invisibili** dal padre, non visibili a tutti. È la
scelta fra un difetto che si vede subito e uno che non fa rumore.
⭐ E il pgTAP la presidia in una forma che non invecchia: legge i valori ammessi
dal **`CHECK`** della tabella e pretende che ognuno compaia come ramo dello
smistatore. *Il perimetro del presidio è il contratto, non un elenco scritto a
mano* — che è esattamente l'errore da cui è nato il passo 7. Provato: la regex
estrae i sette tipi, e togliendo un ramo il presidio lo rileva.

⚠️ **L'ultimo adattatore mancante** era `ATTIVITAFT`, e non ha richiesto la
decisione aperta del §6.1: risale a `commessa_id` (`NOT NULL`), non a
`billing_account_id` (nullable). ⇒ La **nota** di un'attività fatturabile è
protetta; `vendite.attivita_fatturabili` **no**, e resta il debito dichiarato.
L'asimmetria è voluta.

⚠️ **Per l'applicazione non cambia niente**: il backend non passa mai dal padre
(`partitioned_note_repository.py` interroga sempre `vendite.note_<tipo>`). Questa
slice chiude una porta che l'applicazione non usa — ed è esattamente il motivo
per cui era rimasta aperta senza che nessuno se ne accorgesse.

### 6.5 ⚠️ Cosa restava aperto all'inizio: niente che bloccasse

Dopo questa revisione **non c'è nessun caso che impedisca di partire**. L'unica
voce che rimane è quella del §6.1 — se `attivita_fatturabili.billing_account_id`
debba diventare `NOT NULL` — e non è una domanda di perimetro: è una domanda sul
modello della fatturazione, e vive altrove.

---

## 7. Ordine di esecuzione — ✅ eseguito tutto il 2026-09-09

Un changeSet per famiglia, **mai uno solo per tutte**: se una policy sbaglia il
verso, si vuole sapere quale.

| # | Famiglia | Perché in questa posizione |
| --- | --- | --- |
| 1 ✅ | `preventivi` | ⭐ è l'unica con un'esposizione **provata** (§3), e chiude anche il `security_invoker` delle due viste. **Fatta**: slice `27..30`, cinque satelliti, una veste, pgTAP a 8 asserzioni |
| 2 ✅ | `ordini` | la famiglia più letta dopo le fatture; ha già tre policy di testata, quindi tre vesti da rispettare. **Fatta**: slice `33..35`, cinque satelliti × tre vesti = **quindici policy**, pgTAP a 9 asserzioni |
| 3 ✅ | `ddt` | le sue righe alimentano resi e fulfillment: protetta lei, il livello 2 delle altre due famiglie ha una sponda. **Scritta**: slice `36..38`, quattro satelliti × **una** veste (la testata ne ha una sola), pgTAP a 10 asserzioni. Non applicata |
| 4 ✅ | `resi` | dipende da `ddt` per `resi_righe_riconsegne`. **Scritta**: slice `40..42`, quattro satelliti × una veste, pgTAP a 10 asserzioni — la decima è nuova (§6.2 diventa un'asserzione). Non applicata |
| 5 ✅ | `contratti` | il più grosso, ma alleggerito: `fatture_atti` e `attivita_fatturabili` si agganciano altrove (§6.1, §6.3). **Scritta**: slice `44..46` (più la fixture `-43`), cinque satelliti × una veste, pgTAP a 10 asserzioni. Non applicata |
| 6 ✅ | `offerte_commerciali` | il meno esposto. Porta anche l'adattatore `_via_offerta`, che serve al passo 8. **Scritta**: slice `47..49`, cinque satelliti × una veste, pgTAP a 11 asserzioni — l'undicesima **fotografa il buco del padre** |
| 7 ✅ | `fatture` — il resto | il brief la dava per chiusa e non lo era: sei figlie dirette scoperte più una nipote (§2, correzione). **Scritto**: slice `69..71`, sette tabelle × **due vesti** = quattordici policy, pgTAP a 12 asserzioni — due esercitano la veste del PORTALE. Non applicato |
| 8 ✅ | **il padre `vendite.note`** | ⛔ **non è opzionale**: finché il padre è aperto, ogni policy sulle partizioni è aggirabile con `SELECT FROM vendite.note` (§6.4). **Scritto**: slice `72..74` — tre policy sul padre (una per veste) più l'adattatore `ATTIVITAFT` e la policy che mancava su `note_attivita_fatturabili`. pgTAP a 9 asserzioni |

⭐ **La policy SULLA PARTIZIONE viaggia con la sua famiglia**: ognuna ha una FK
`NOT NULL` verso la propria testata (§6.4), e protegge l'accesso diretto — che è
l'unico che il backend usa.
⛔ **Ma non chiude il buco**, e questo il brief lo diceva male: le sette `note_*`
sono partizioni di `vendite.note`, e dal padre si legge tutto. Il passo 8 esiste
per quello, e senza di lui i passi 1-6 lasciano le note scoperte.

Ogni passo porta: gli helper, le policy, **`ALTER TABLE … ENABLE ROW LEVEL
SECURITY`**, e un pgTAP che costruisce due emittenti e verifica che uno non veda
le righe dell'altro.

⭐ E la fixture per quel pgTAP **esiste gia'**: `dbops.fn_pgtap_crea_emittente_operatore()`
(changeSet `20260909-26`) fabbrica un'azienda con il suo operatore, e chiamandola
due volte si hanno i due mondi da tenere separati. Per i documenti serve anche un
cliente fatturabile: `dbops.fn_pgtap_crea_cliente_ba()` (`20260909-31`).

### ⭐ Cosa hanno insegnato le sei famiglie — e i due passi che ne sono nati

**Le vesti si rispecchiano tutte.** `preventivi` ne aveva una, `ordini` tre. La
tentazione, su `ordini`, era dare ai satelliti la sola `OPERATORE` — quella che
chiude il buco. Sarebbe stata una modifica funzionale mascherata da cantiere di
sicurezza: oggi un `CLIENTE_PORTALE` vede le righe di *tutti* gli ordini, e con
la sola veste operatore non ne vedrebbe **nessuna**, nemmeno dei propri.
⇒ **Questa slice chiude un buco, non apre e non chiude una porta.** Se un domani
si decide che il portale non deve vedere le righe, quella è una decisione di
dominio e si prende togliendo la policy, con la sua ragione scritta.

**Il rischio vero non è «vedo troppo poco»**, è che un satellite risulti **più
permissivo della propria testata**. Su `ordini` la veste SHOP pretende *due*
condizioni — proprietà **e** `canale_origine = 'SHOP'` — e un adattatore che si
fosse fermato alla proprietà avrebbe aperto il satellite più del documento.
⇒ Da qui in avanti ogni pgTAP di famiglia porta le due asserzioni che lo
verificano: *nessuna riga visibile il cui documento non lo sia*, e il caso
specifico di ogni veste con una condizione in più.

**Una fixture non si costruisce se il soggetto è dati di macchina.**
`ordini_righe_componenti` pretende una distinta base: 25 righe su dbdev, **zero**
su un database ricostruito. Invece di costruirla o di cercarne una, il test
interroga direttamente l'adattatore `_via_ordine_riga`. *Non serve una riga per
chiedere a una funzione se dice il vero*, ed è una prova più forte perché nomina
la cosa da verificare invece di contare righe attorno.

**Le viste erano un problema di `preventivi` soltanto.** Verificato il
2026-09-09: nessuna vista che legge i satelliti delle quattro famiglie rimaste è
priva di `security_invoker`. ⇒ Ogni famiglia che resta costa **tre** changeSet —
helper, policy inerti, armamento — non quattro. Confermato su `ddt`, le cui sei
viste lettrici di `ddt_righe` avevano già tutte `security_invoker`.

**⭐ Il numero delle vesti cambia, il criterio no.** `ddt` ha **una** policy di
testata, contro le tre di `ordini`: quattro satelliti × una veste = quattro
policy. Non è «la famiglia facile»: è la stessa regola — *il satellite
rispecchia tutte le vesti della propria testata* — applicata a una testata che
di vesti ne ha una. ⚠️ Il corollario va scritto **nel changeSet**, perché è lì
che qualcuno lo leggerà: il giorno in cui `vendite.ddt` ricevesse una veste
cliente, i suoi satelliti vanno estesi **nello stesso gesto**, o restano
indietro rispetto al documento.

**⛔ Il test si allunga dove la chiave CAMBIA NOME.** Su `ddt` due satelliti su
quattro non si chiamano `ddt_id`: `note_ddt` risale da `target_id` e
`ddt_righe_componenti` da `riga_ddt_id`. Sono i punti in cui un refuso nella
policy **non fa rumore** — la tabella resterebbe semplicemente aperta. ⇒ Il
pgTAP di `ddt` ha due asserzioni in più delle altre, una per la nota e una per
l'indirizzo, e la fixture le costruisce apposta. *Si prova la chiave che si
potrebbe sbagliare, non quella che si copia.*

**⚠️ `ddt_righe` è la prima figlia che è anche MADRE di altre famiglie.**
`ordini_righe_fulfillment` (già armata dal lato ordine), `resi_righe` e
`resi_righe_riconsegne` hanno tutte una FK `NOT NULL` verso di lei. Armato il
DDT, quelle righe si leggono attraverso un `ddt_righe` filtrato: **due strade
verso la stessa riga**, che devono dare la stessa risposta. Se dissentissero non
è la policy da allargare — è il guard mancante fra ordine e DDT sull'emittente
(§6.2), e resta una domanda dichiarata, non risolta qui.

**⭐⭐ Una domanda del §6.2 è diventata un'ASSERZIONE, e questo è il modo.**
`vendite.resi_righe` ha **due genitori `NOT NULL`**: `reso_id` e `ddt_riga_id`.
Il perimetro lo risolve il reso — la riga appartiene a quel documento — ma da
quando `ddt_righe` è armata la stessa riga è raggiungibile per due strade. Il
brief chiedeva: *esiste un guard che imponga a DDT e reso di condividere
l'emittente?* Il pgTAP di `resi` ora **lo pretende** (test 9), invece di
lasciarlo scritto in prosa. ⚠️ Verde sul database di sviluppo il 2026-09-09 —
che è un fatto datato, non una prova che il guard esista: prova che oggi nessuna
riga lo smentisce. ⛔ Se un giorno diventasse rosso, il difetto **non è la
policy**: si spezza in due test — uno che pinna il difetto, uno che pretende la
riparazione — e non lo si allarga per farlo tacere.

**⛔ La fixture lunga si costruisce lo stesso.** Un reso pretende un DDT
**consegnato**, quindi la fixture porta il DDT per tutti e tre i passi
(`EMESSO` → `SPEDITO` → `CONSEGNATO`) passando dai suoi guard: causale di
trasporto alla nascita (è immutabile dopo), IVA sulla riga che ha un prezzo,
indirizzo `CON` obbligatorio. È lungo, e vale: il file misura la stessa cosa su
dbdev e su un database ricostruito.
⚠️ Il precedente `test-rls-resi-ef-whitelist-write.sql` fa il contrario — cerca
dati esistenti e ha un `EXCEPTION WHEN OTHERS THEN NULL` che lo fa **passare a
vuoto** quando la fixture non si costruisce. È il «verde per sottrazione», ed è
un debito da guardare quando si passa di lì.

**⚠️ E una figlia di secondo livello si costruisce SE la costruzione è onesta.**
Delle tre di `resi`, solo `rinunce` chiede poco (riga + quantità) e sta nella
fixture — ma pretende una riga di tipo `RESO_PER_RICONSEGNA`, non a credito.
`accrediti` vuole una riga di fattura rettificata e una commessa: lì il
perimetro si prova interrogando l'adattatore, non fabbricando una catena che non
appartiene alla slice.

**⛔⛔ Il billing account obbligatorio cambia le carte, e si scopre al QUINTO
documento.** `contratti` e `offerte_commerciali` portano `billing_account_id`
**`NOT NULL`**; preventivi, ordini, ddt e resi lo hanno nullable. Su tutte e
sette le testate c'è un guard `trgfn_<documento>_guard_emittente_ba` che pretende
`emittente_fiscale_id = anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`.
Con il BA nullo quel guard **esce subito** — ed è il motivo per cui le prime
quattro slice non l'hanno mai incontrato.

⚠️ **E il modo in cui morde è insidioso**: senza una riga in
`emittenti_fiscali_billing_account`, `fn_get_emittente_fiscale_pk` **non
fallisce** — ricade sull'emittente di **default** dell'installazione. Quindi non
dice «legame mancante»: risponde un emittente *plausibile* ma di un'altra
azienda, e il guard rifiuta il documento con un messaggio che parla di
incoerenza. Una fixture che costruisce due mondi separati e non lega il BA sta
di fatto chiedendo un contratto per l'azienda sbagliata.
⇒ Il legame è entrato nella **fixture condivisa** (`fn_pgtap_crea_cliente_ba`,
terzo parametro opzionale, changeSet `20260909-43`), non nei singoli test: è una
regola sola, e scritta due volte prima o poi diverge. Vale identico per
`offerte_commerciali`, che è l'ultimo passo.

⚠️ **Un parametro in più è un OVERLOAD**: la funzione si droppa e si ricrea, non
`CREATE OR REPLACE`. Con due funzioni in servizio una chiamata a due argomenti
diventa ambigua e i quattro test già applicati si romperebbero.

**⭐ `contratti` non è letta da nessuna vista.** Non «ce l'hanno già tutte il
`security_invoker`»: proprio **nessuna** delle 60 viste di `vendite` legge i suoi
cinque satelliti (verificato 2026-09-09). È la famiglia più isolata — e il
corollario è che una divergenza dopo l'armamento si vedrebbe **solo** dalle query
dirette del backend, non da una lista che smette di popolarsi.

**⛔⛔ Un presidio può asserire un BUCO, e a volte deve.** Il pgTAP delle offerte
ha un test in più degli altri cinque, e non verifica una difesa: verifica che
**dal padre `vendite.note` la nota di un'altra azienda si veda ancora**. È il
debito del §6.4 messo per iscritto in una forma che non invecchia.
⭐ Il verso è quello giusto: quando il passo 8 chiuderà il padre, quel test
diventerà **rosso** — cioè si accorgerà della riparazione. ⚠️ E allora va
**sostituito** con l'asserzione positiva («dal padre si vede solo il proprio»),
non allargato per farlo tacere: un test che pinna il sintomo e uno che pretende
la riparazione sono due test, non uno.

**⚠️ L'ultima famiglia ha la catena più lunga, e non era prevedibile dal §5.**
`offerte_commerciali` pretende `billing_account_id`, `istanza_utility_id` **e
`listino_id`**, tutti `NOT NULL` — e un listino è a sua volta *scoped per
emittente*. Quindi ogni mondo della fixture ha il suo listino, oltre al suo BA
legato. Il §5 conta le tabelle da proteggere; il costo vero di una slice lo
decide invece ciò che la sua **testata pretende per nascere**, che è
un'informazione che il brief non portava.

---

## 8. Il presidio, e cosa non fare

### ⛔ Una policy senza RLS accesa non è una difesa

`pg_policy` avrebbe la riga e il filtro non si applicherebbe. **Succede già**:
`acquisti.ddt`, `acquisti.ordini` e `shop.ricevute` hanno una policy e
`relrowsecurity = false` (2026-09-09). Chi verifica con
`EXISTS (SELECT 1 FROM pg_policies …)` legge verde.

⇒ Ogni changeSet di questo brief deve fare **entrambe** le cose, e il pgTAP deve
asserire `relrowsecurity`, non l'esistenza della policy.

### ✅ Il presidio che serve — SCRITTO il 2026-09-09 (→ §11)

⚠️ Questa sezione si intitolava *«Il presidio che serve, e che NON è stato
scritto»*. Il criterio qui sotto è rimasto quello, parola per parola; è cambiato
il fatto che ora esiste. Realizzazione, misure e forma nel **§11**.

Un pgTAP unico, sulla falsariga di `test-rls-viste-security-invoker.sql` (che è
il presidio meglio scritto del repo: criterio **transitivo**, casi costruiti,
niente elenchi a mano):

> Ogni tabella con una FK verso una tabella in RLS ha a sua volta una policy
> **e** la RLS accesa, oppure è dichiarata nel registro del debito con la sua
> ragione tecnica.

⚠️ La seconda metà non è un cedimento: `attivita_fatturabili` (§6.1) ci starà
dentro finché la sua ambiguità non è risolta, e **con la ragione scritta**, non
con un'etichetta. Un presidio senza registro diventa un presidio spento.

### ⛔ Cosa non fare

* **niente `security_invoker` dimenticato**: le due viste di `preventivi` vanno
  sistemate nello stesso changeSet della famiglia 1, o il presidio esistente
  diventa rosso — il che è corretto, ma allora si sta lavorando in due tempi;
* **niente policy sulle figlie senza aver guardato le viste** che le leggono
  saltando la testata: sono il punto in cui il perimetro si perde davvero;
* **niente `FOR SELECT` dove serve `FOR ALL`**: una policy di sola lettura
  lascia scrivere, e la `WITH CHECK` è ciò che impedisce a un operatore di
  *creare* una riga fuori dal proprio perimetro.

---

## 9. Perché lo `storico` (D3) resta fuori — decisione del 2026-09-09

`storico` ha 120 tabelle, zero RLS, e 52 con `SELECT` per `zeroerp_app`: ogni
versione precedente di una riga protetta è leggibile. È un buco reale e resta
aperto **di proposito**.

⭐ La ragione è di sequenza, non di gravità: la difesa giusta per lo storico non
è una policy per tabella scritta a mano — sarebbero 120, e nascerebbero
disallineate — ma una policy **generata dallo stesso framework** che genera la
tabella storico e il suo trigger (`dbops.fn_run_automations_storico`,
`fn_ensure_storico_table`), derivando lo scope dalla madre.

⇒ Un generatore ha senso quando le madri sono ferme. Con `acquisti` e
`magazzino` ancora da scrivere — 9 e 26 tabelle modellate e quasi senza logica —
lo si rifarebbe a ogni tabella nuova.

⚠️ **Ma il debito va dichiarato adesso, non quando lo si apre**: finché `storico`
è aperto, chiudere questo brief non chiude il buco — sposta solo il punto da cui
si legge. Chi legge questo documento deve saperlo.

---

---

## 10. Lo stato di arrivo, e cosa resta aperto — 2026-09-09

Letto dal catalogo a cantiere chiuso (struttura, non popolazione).

### ✅ Cosa è protetto adesso

* le **sei famiglie di documento** hanno testata *e* satelliti in RLS, con
  tutte le vesti della testata rispecchiate su ciascun satellite;
* la famiglia `fatture` è completa: alle cinque figlie già protette se ne sono
  aggiunte **sette** (passo 7), fra cui la nipote `fatture_sdi_eventi`;
* le **sette partizioni** di `vendite.note` hanno la loro policy — e il
  **padre** ha le sue tre, quindi la via che le aggirava è chiusa (passo 8);
* `vendite` conta **83 policy** e `script` **35 adattatori `fn_scope_*`**
  *(fotografia del 2026-09-09; dopo le sei famiglie del §11 sono **94** e **41**,
  letti il 2026-09-10)*;
* `db/pgtap/rls/`: **30 file, 30 verdi**, su database di sviluppo e su database
  ricostruito dai changelog.

### 🟠 Cosa resta scoperto, e non è una dimenticanza

⚠️ **Questa tabella è VERA ma PARZIALE, e il §11 la corregge**: il criterio è
stato applicato *«a ogni tabella di `vendite`»*, cioè con un perimetro scelto a
mano — lo stesso errore che il §2 aveva già fatto sull'elenco delle figlie di
`fatture`, alla scala dello schema invece che della famiglia. Su tutto il
database le tabelle sono **trenta**, più tre di un secondo criterio.

Applicando il criterio **transitivo** del §8 — *ogni tabella di `vendite` con
una FK verso una tabella in RLS, priva di policy* — restano **dodici** tabelle,
in quattro gruppi:

| Gruppo | Tabelle | Perché resta fuori |
| --- | --- | --- |
| **Lotti** | `fatturazione_lotti_esiti`, `_fatture`, `_gruppi`, `_log`, `_task_runs` | `vendite.fatturazione_lotti` **è protetta** e i suoi satelliti no: è lo stesso difetto di questo brief, su un'altra famiglia. È un **cantiere suo**, e la forma da copiare è quella dei passi 1-6 |
| **Attività** | `attivita_fatturabili`, `attivita_consumi`, `commesse_attivita_log`, `commesse_sorgenti` | `attivita_fatturabili` è il debito dichiarato del §6.1; le altre tre pendono da lì o da `commesse`. ⭐ La rotta esiste già (`commessa_id`, `NOT NULL`) — manca la decisione, non lo strumento |
| **Listini** | `listini_righe`, `listini_righe_componenti` | pendono da `listini_versioni`; `vendite.listini` è protetta ma la catena versione→riga no |
| **Arrotondamenti** | `fatture_arrotondamenti_scope` | FK verso `anagrafiche.billing_account` |

⚠️ **E resta il debito più grosso, dichiarato in apertura**: lo `storico`
(§9). Chiudere questo brief non chiude quel buco — **sposta il punto da cui si
legge**, e chi legge deve saperlo.

⚠️ Fuori da `vendite`: `magazzino.note`, `acquisti.note` e `catalogo.note` sono
partizionate come `vendite.note` era, quindi nella stessa condizione. E
`acquisti.ddt`, `acquisti.ordini`, `shop.ricevute` hanno una policy con la
**RLS spenta** — l'unico caso rimasto in tutto il database di «policy che non
è una difesa».

### ✅ Il presidio del §8 — scritto il 2026-09-09 (dettaglio nel §11)

⚠️ Questa sezione si intitolava *«Il presidio del §8 non è stato scritto, ed è
la cosa da fare per prima»*, e diceva che il registro del debito sarebbe stato
«esattamente quelle dodici righe con le loro quattro ragioni». **La prima metà
è stata fatta; la seconda era sbagliata, e di parecchio**: dodici era il conto
del solo `vendite`. Il §11 porta il numero vero.

Questo cantiere ha prodotto **un** presidio transitivo, ed è piccolo: il test 4
di `test-rls-note-padre.sql`, che confronta i rami dello smistatore con il
`CHECK` della tabella. Funziona perché il suo perimetro è un **contratto** e non
una lista. Il presidio generale è ora della stessa specie.

⭐ **Perché conta più delle dodici tabelle**: senza quel presidio, la prossima
tabella con una FK verso un documento nascerà scoperta e nessuno lo saprà — che
è, parola per parola, il modo in cui è nato questo brief.

### ⭐ Le tre lezioni che sopravvivono al cantiere

1. **Un elenco scritto a mano ha per perimetro ciò che chi lo scriveva aveva in
   mente.** Il §2 diceva «`fatture`: tutte protette» ed erano protette le cinque
   che l'elenco nominava. Sei figlie e una nipote non c'erano. ⇒ Un presidio si
   aggancia al **contratto** (una FK, un `CHECK`), mai a una lista.
2. **Una difesa parziale non si vede.** Le policy sulle sette partizioni di
   `vendite.note` erano tutte corrette e tutte aggirabili con un `SELECT` dal
   padre: il sintomo di un perimetro mancante è *vedere di più*, non un errore.
3. **Un test può asserire un buco**, e allora va scritto nel verso che si
   accorge della riparazione — e quando la riparazione arriva si **sostituisce**
   con l'asserzione positiva, non si allarga per farlo tacere. È successo una
   volta, sul test 11 delle offerte, ed è andata come doveva.

---

## 11. Il presidio — scritto e applicato il 2026-09-09

> Stato: ✅ **applicato.** Slice `20260909-75..77` sul database di sviluppo il
> 2026-09-09 alle **22:52**; pgTAP **8/8 verde**.
>
> ⭐ **E verde anche in CI, che è la prova che vale.** Il merge #1551 tocca
> `db/**`, quindi `ci-validate.yaml` ha eseguito la suite su un PostgreSQL
> ricostruito **da zero**: il file non compare in nessuna delle due baseline dei
> rossi, quindi è passato davvero. ⇒ Le **33 righe del registro di quel giorno combaciavano con
> il perimetro calcolato su un database vergine**, non solo su quello di
> sviluppo — cioè il registro descrive il *contratto* e non la macchina di chi
> l'ha scritto. Era l'unica cosa che il dry-run non poteva dire.

### 11.1 I pezzi

| # | ChangeSet / file | Che cosa porta |
| --- | --- | --- |
| 1 | `20260909-75` (`00_schema/dbops`) | `dbops.rls_perimetro_debito` — il registro, con `criterio` nella chiave |
| 2 | `20260909-76` (`20_code/dbops`) | `dbops.vw_rls_perimetro_scoperto` — il criterio, e i tre stati |
| 3 | `20260909-77` (`80_data`) | il mirror CSV del registro, ognuna con la sua ragione — **33 righe alla nascita**, 26 dopo la slice `pratiche` (§11.7) |
| — | `db/pgtap/rls/test-rls-perimetro-scoperto.sql` | il presidio, plan 8 |
| — | `docs/it/dbzero/dbops/manual/` | le due schede concettuali (tabella e vista) |

⚠️ **Numerazione**: gli slot liberi del 2026-09-09 sotto il massimo erano
**uno solo** (il `-50`), e la slice ne vuole tre consecutivi e crescenti —
tabella prima della vista, o l'autogen esegue la vista su una tabella che non
c'è. Quindi `75..77`, sopra il massimo. **Il `-50` resta libero.**

### 11.2 ⛔ Il fatto che cambia il §10: trenta, non dodici

Il criterio non è cambiato di una parola. È cambiato il **perimetro su cui lo si
applica**: il §10 lo aveva ristretto a `vendite`.

| | tabelle |
| --- | ---: |
| §10, criterio applicato al solo schema `vendite` | 12 |
| stesso criterio, **tutto il database** | **30** |
| secondo criterio — una policy scritta e mai applicata | **3** |

Le diciotto in più non sono una scoperta di questo passo: sono la **terza
occorrenza della stessa lezione**, dopo le sei figlie di `fatture` (§2) e le
sette partizioni di `vendite.note` (§6.4). Le famiglie nuove:

| Famiglia | Tabelle | In una riga |
| --- | ---: | --- |
| **pratiche** | 7 | `pratiche.pratiche` è protetta, i suoi sette satelliti no. È la forma dei passi 1-6 su un altro dominio, e vuole **un solo** adattatore `_via_pratica` |
| **anagrafiche** | 4 | `clienti` più le due tabelle che **definiscono** il legame emittente ↔ BA, e quelle sono un caso a parte (§11.4) |
| **documenti** | 2 | gli eventi e il **file** di `documenti_generati` |
| **pagamenti** | 2 | `sepa_mandati`, e il ponte con **due perimetri diversi** sulla stessa riga |
| **config** | 1 | `email_allegato`: qui l'asse non è l'emittente ma l'**ambito** |
| **magazzino** | 1 | `assets`: due rotte protette, **tutte e due nullable** |
| **shop / acquisti** | 3 | le tre policy inerti (§11.3) |

### 11.3 ⛔ Il secondo criterio: una policy che non filtra

Il §8 di questo brief apre proprio di lì — *«`pg_policy` avrebbe la riga e il
filtro non si applicherebbe»* — e nomina tre tabelle. Il primo criterio ne
prende **una sola**: le altre due non sono figlie di niente di protetto.

⇒ Sono due **domande** diverse, e restano due righe diverse.
`shop.ricevute` le porta entrambe: non è rumore, sono due difetti indipendenti.

⭐ E il registro ha reso leggibile **perché** quelle tre non erano state armate,
che il brief non sapeva: `acquisti.ddt` e `acquisti.ordini` hanno una policy di
sola veste `FORNITORE_PORTALE`, e la RLS è **default-deny** — accenderla oggi
renderebbe le due tabelle invisibili e non scrivibili all'**operatore**, che ci
ha `SELECT/INSERT/UPDATE/DELETE`. E la veste operatore non è nemmeno scrivibile:
**quelle due tabelle non hanno nessuna colonna emittente.** Manca il modello,
non l'accensione.

⚠️ `shop.ricevute` è invece un caso da un minuto, ed è scritto nella sua riga di
registro: `zeroerp_app` non ha **nessun** GRANT su quella tabella, quindi
accendere la RLS non toglie niente a nessuno. Costa una riga. Resta spenta
perché il dominio shop è allo Stage D e la decisione appartiene a quel cantiere
— ma è la prima da pagare, ed è segnalata come tale.

### 11.4 ⭐ Due tabelle che non sono un armamento, ma una domanda

`anagrafiche.emittenti_fiscali_billing_account` e la gemella
`resellers_billing_account` **definiscono** il legame da cui la whitelist
dell'operatore si deriva. Una policy che le filtrasse per perimetro emittente si
appoggerebbe a **sé stessa**.

⇒ Non è un lavoro rimandato per mancanza di tempo: è una domanda di modello — *il
legame è catalogo, o è dato di perimetro?* — e le due si decidono insieme, o due
tabelle gemelle risponderebbero in due modi.

### 11.5 ⚠️ L'invariante NON è «la vista è vuota»

Trenta tabelle sono scoperte oggi. Un cancello rosso dal primo giorno viene
disattivato, e *un presidio spento è peggio di uno assente*. L'invariante
verificabile è **«nessuna riga fuori da `DEBITO_DICHIARATO`»**, e morde nei due
versi:

* `NON_DICHIARATO` — una tabella è nata scoperta e non se n'è accorto nessuno;
* `DEBITO_ESTINTO` — una riga di registro **non ha più il suo difetto**. Va
  tolta dal CSV, o continuerebbe a far tacere il presidio su quella tabella
  anche il giorno in cui tornasse scoperta per un'altra strada. ⭐ È il verso in
  cui un registro marcisce **senza che nessuno se ne accorga**, cioè quello
  permissivo, ed è il motivo per cui esiste.

⚠️ **E va detto dove sta il prezzo: dichiarare un debito zittisce il test 2.**
Per una tabella nuova il presidio vero sono i **casi costruiti** (test 4..8), che
provano che il flag è un **gesto** e non l'impostazione di fabbrica.

### 11.6 ⭐ La mutazione che ha trovato un verde per sottrazione — nel presidio

Il file è stato provato **facendolo fallire**, non solo passare. Due mutazioni:

| Mutazione | Atteso | Esito |
| --- | --- | --- |
| tolta una riga dal registro (`pratiche.flussi`) | rosso il test 2 | ✅ |
| tolto alla vista il ramo `POLICY_INERTE` | rossi 2, **3** e 7 | 🔴 il **3 restava VERDE** |

⛔ **E il test 3 era proprio quello che doveva accorgersene.** Chiede *«ogni
criterio ammesso dal `CHECK` ha un ramo vivo nella vista?»* — ma il ramo del
**debito estinto** ripubblica il `criterio` leggendolo dal **registro**: la
parola `POLICY_INERTE` continuava a comparire nella vista perché stava scritta
nel CSV, non perché la regola la producesse ancora.

⇒ Corretto guardando solo ciò che il criterio produce (`stato <> 'DEBITO_ESTINTO'`).
⭐ È la forma esatta del **verde per sottrazione**, trovata sul test che esiste
per impedirlo — e si è vista solo perché il presidio è stato mutato. *Un
presidio che non è mai stato fatto fallire non è stato provato.*

### 11.7 ✅ La prima famiglia consegnata dal presidio: `pratiche`

> Stato: ✅ **applicata** il 2026-09-10 — slice `20260910-01..04` +
> `db/pgtap/rls/test-rls-pratiche-satelliti.sql`, pgTAP **12/12 verde**.

⭐ **È la prima slice che non nasce da un elenco letto a mano.** Le sei di ieri
venivano dal §5 di questo brief; questa viene da
`dbops.vw_rls_perimetro_scoperto`, che ha nominato sette satelliti di
`pratiche.pratiche` che nessuno aveva mai guardato.

#### ⛔ E il criterio ne ha trovate NOVE, non sette

Il registro dichiarava le sette con una FK **diretta** verso la testata. Ma
`pratiche.allegati_flussi` e `pratiche.note_flussi` hanno una FK `NOT NULL`
verso `pratiche.flussi`, che non era protetta — quindi erano **fuori
perimetro**, non nascoste.

⇒ Armando `flussi` sarebbero entrate nel perimetro **al giro dopo**, facendo
rosso il presidio su due tabelle mai censite. È la transitività descritta nel
§11.2, vista funzionare **prima** che costasse un rosso: *il criterio si estende
da solo*. La slice ne arma nove.

#### La forma, e le due cose che valgono per le prossime famiglie

| | |
| --- | --- |
| vesti | **una** — `pratiche.pratiche` ha la sola `OPERATORE` `FOR ALL`. I nove la rispecchiano: stessa regola, testata con una veste sola |
| chiavi | sette da `pratica_id`, due da `flusso_id` → due adattatori, il secondo **delega** al primo |
| viste | ⭐ **nessuna da sistemare**: le dieci che leggono i satelliti hanno già tutte `security_invoker` |
| registro | le sette righe **tolte** dal CSV *e* cancellate con `20260910-04` |

⛔ **Il quarto changeSet non è una pulizia, ed è stato provato.** Armando senza
cancellare, le sette righe escono come `DEBITO_ESTINTO` e il test 2 del presidio
diventa **rosso** — verificato. Il registro non può marcire nel verso
permissivo, ed è il presidio stesso a pretenderlo.

#### ⭐ Le due cose che le mutazioni hanno insegnato

Il pgTAP è stato provato **facendolo fallire**, non solo passare:

| Mutazione | Chi se ne accorge |
| --- | --- |
| `_via_pratica` al posto di `_via_flusso` su `note_flussi` | test 3 (struttura) **e** test 12 |
| `pratiche.flussi` senza `ENABLE` | test 2, 6, 10 |

⛔ **La prima è il refuso che non fa rumore**: le due chiavi sono entrambe
`bigint`, quindi scambiarle compila e gira. E alla prima stesura la prendeva
**solo** il test strutturale: sul verso negativo la policy sbagliata sembra
corretta — un `flusso_id` letto come `pratica_id` non trova nessuna pratica,
quindi la riga altrui resta invisibile lo stesso. ⇒ Aggiunto il **gemello
positivo** (test 12): con l'adattatore sbagliato sparirebbe anche la nota
*propria*, e lì il difetto si vede.

⚠️ **Due inciampi della fixture, entrambi istruttivi**: il tipo di prestazione
non può essere «il primo attivo» (il suo preset non ha step, e il flusso non
nasce), e il `FORCE` va messo su **tutte e nove** — sulle tre che la fixture non
popola l'owner restava esente e contava le righe vere di sviluppo. ⭐ Su un
database ricostruito da zero quelle tabelle sono vuote: il test sarebbe passato
**per sottrazione**, cioè proprio dove nessuno guarda.

#### Il registro dopo questa slice

**33 → 26 righe** (23 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`).

---

### 11.9 ✅ La seconda famiglia: `lotti`

> Stato: ✅ **applicata** il 2026-09-10 — slice `20260910-14..17` +
> `db/pgtap/rls/test-rls-lotti-satelliti.sql`, pgTAP **12/12 verde**, nessuna
> regressione.
> ⚠️ Numerazione da `-14`: i progressivi `05..13` sono di un altro cantiere
> (indicazione di Tid, 2026-09-10).

I cinque satelliti di `vendite.fatturazione_lotti`: `esiti`, `fatture`,
`gruppi`, `log`, `task_runs`. Una chiave sola (`lotto_id`, `NOT NULL`), quindi
un adattatore solo; **nessun nipote**, quindi nessuna sorpresa al giro dopo —
al contrario di `pratiche`.

#### ⭐ La decisione: `fatturazione_lotti_fatture` risale dal LOTTO

Decisione di Tid, 2026-09-10. È l'unica dei cinque con **due** genitori protetti
e tutti e due `NOT NULL` — e i due non hanno le stesse vesti: il lotto ha la sola
`OPERATORE`, la fattura ha anche `CLIENTE_PORTALE`.

⭐ Comanda il **lotto**, e la ragione sta sul modello: quella riga racconta
*com'è andato il giro di emissione* — porta `stato_esecuzione`, `stato_sdi_id`,
`stato_doc_fiscale_id` — ed esiste solo perché un lotto ha girato. La fattura
esiste anche senza.

⛔ Agganciarla alla fattura avrebbe portato dentro la veste del portale: un
cliente vedrebbe in quale giro la propria fattura è stata prodotta. Oggi quella
porta è chiusa ⇒ sarebbe stata una **modifica funzionale mascherata da cantiere
di sicurezza**, la stessa trappola già evitata su `ordini` al passo 2.
⚠️ Se un giorno si deciderà che il portale deve vederlo, si **aggiunge** la
veste con la sua ragione — non la si eredita di straforo.

#### ⛔ Il refuso muto di questa famiglia è diverso dagli altri

`vendite.fatturazione_lotti` nomina l'emittente per **soggetto-ruolo**, non per
emittente fiscale: l'adattatore delega a `fn_scope_ef_whitelist_via_sr`, non
alla canonica. Scambiarle non dà errore — confronterebbe un id di soggetto-ruolo
con una whitelist di id di emittente fiscale, cioè **zero righe**.

⚠️ **Un fail-closed per la ragione sbagliata somiglia a una difesa che
funziona.** Provato mutando l'adattatore: i test negativi (6, 7, 8) restano
**verdi**; a cadere sono il **5** («A vede il PROPRIO») e il **12** (l'adattatore
interrogato nei due versi). È la stessa lezione del gemello positivo di
`pratiche`, su un errore diverso.

| Mutazione | Chi se ne accorge |
| --- | --- |
| l'adattatore delega alla canonica invece che a `_via_sr` | test 5 e 12 |
| il legame agganciato alla **fattura** (decisione ribaltata) | test 3, 4 e 10 |

⭐ Il test 4 pinna la decisione **dove vive**, cioè nella definizione della
policy: il giorno in cui qualcuno la cambia deve cambiare anche quella riga, e
leggere perché.

#### Il registro dopo questa slice

**26 → 21 righe** (18 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`).

⚠️ **`pagamenti.vendite_contabili_lotti` resta**, e non è una dimenticanza:
nomina `vendite.fatturazione_lotti` ma ha due genitori con **due perimetri
diversi** — il lotto (whitelist emittente) e `pagamenti.vendite_contabili`
(perimetro di incasso). Quale comandi è una domanda aperta, non un armamento.

---

### 11.10 ✅ `pagamenti.vendite_contabili_lotti` — la riga che era una DOMANDA

> Stato: ✅ **applicata** il 2026-09-10 — slice `20260910-18..20` +
> `db/pgtap/rls/test-rls-vendite-contabili-lotti.sql`, pgTAP **10/10 verde**,
> nessuna regressione.

⭐ **Questa riga del registro non era un arretrato: era una domanda.** Le altre
dicono «manca un adattatore», «va con il cantiere X». Questa diceva *«due
perimetri diversi sulla stessa riga, va deciso quale comanda»*: due genitori
protetti e `NOT NULL` — `pagamenti.vendite_contabili` (perimetro di incasso) e
`vendite.fatturazione_lotti` (whitelist emittente).

⇒ Esce dal registro non perché è stato scritto del codice, ma perché è stata
presa una **decisione**: *«è legato a `pagamenti.vendite_contabili`»* (Tid,
2026-09-10). Sul modello regge — la riga dice **quali lotti una distinta
raccoglie**, quindi è il manifesto della distinta; il lotto esiste anche senza.

⚠️ È la decisione **speculare** a quella presa lo stesso giorno su
`fatturazione_lotti_fatture` (§11.9), dove comandava il *lotto*. Non è una
contraddizione: in tutti e due i casi **comanda il documento di cui la riga è il
manifesto**.

#### ⭐ La slice è di tre pezzi, non quattro

`script.fn_scope_ef_whitelist_via_contabile` **esiste già** ed è usata da
`vendite_contabili_righe`: nessuna funzione nuova. *La regola su come una
distinta nomina il proprio emittente resta scritta in un posto solo.*

#### ⛔ Il ramo scritto a mano: la distinta INTERNA

L'adattatore risolve l'emittente dal **canale di incasso**. Su una distinta
interna (fondo fattura, compensazione) canale non ce n'è, l'emittente resta NULL
e la funzione risponde `false` — mentre la **testata è visibile**, perché la sua
policy ammette esplicitamente `ente_incasso_id IS NULL`.

⇒ Con il solo adattatore il manifesto di una distinta interna sarebbe invisibile
a tutti mentre la distinta si vede: un satellite **più chiuso** della propria
testata, cioè un pannello vuoto senza spiegazione. La policy porta un secondo
ramo che rispecchia esattamente ciò che la testata concede — la stessa forma che
la sorella `vendite_contabili_righe` ha già.

#### ⛔ E l'invariante si è auto-neutralizzato, come il presidio a §11.6

Il test 8 doveva dire *«nessuna distinta visibile ha un manifesto nascosto»*, e
la prima stesura chiedeva quali distinte hanno un manifesto con un `EXISTS` su
`vendite_contabili_lotti` — cioè **leggendo attraverso la policy che stava
verificando**. Con il manifesto nascosto l'`EXISTS` è falso, la distinta non
entra nel confronto: togliendo il ramo della distinta interna il test restava
**verde**.

⭐ *Un invariante che si misura attraverso il proprio filtro non misura niente.*
Riscritto sul denominatore noto — le tre distinte che la fixture costruisce da
owner — ora la mutazione lo fa cadere.

| Mutazione | Chi se ne accorge |
| --- | --- |
| via il ramo della distinta interna | test 7 e 8 |
| il manifesto agganciato al **lotto** (decisione ribaltata) | test 3, 4 e 9 |

⚠️ E la seconda dice una cosa che vale per le prossime: nel verso della
**lettura** le due scelte sono indistinguibili (A vede il proprio manifesto in
entrambi i casi). A separarle sono la **struttura** e la **scrittura** — chi può
appendere un lotto al manifesto di chi.

#### ⚠️ Due trappole della fixture, per chi tocca `pagamenti`

* `anagrafiche.bank_branches` **non ha un seed**: una riga sola su sviluppo,
  creata a mano, e `conti_bancari.bank_branch_id` è `NOT NULL`. Un test che
  cercasse una filiale esistente sarebbe verde qui e **senza materia in CI**. La
  fixture la costruisce — e il soggetto-ruolo della filiale vuole il ruolo
  **`BANK_B`**, non quello dell'emittente: c'è un guard, e ha ragione.
* i lotti si costruiscono **prima** di entrare nei panni di qualcuno:
  `trgfn_guard_emittente_scope` è un trigger e scatta anche per l'owner.

#### Il registro dopo questa slice

**21 → 20 righe** (17 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`).

---

### 11.11 ✅ `listini` — la catena, e un anello solo da aggiungere

> Stato: ✅ **applicata** il 2026-09-10 — slice `20260910-21..24` +
> `db/pgtap/rls/test-rls-listini-satelliti.sql`, pgTAP **10/10 verde**, nessuna
> regressione.

⭐ **La catena era già mezza costruita**, e la slice aggiunge un anello:

```
listini ──(_via_sr)──────────> emittente        [già protetta]
listini_versioni ──(_via_listino)──>            [già protetta]
listini_righe / _componenti ──(_via_listino_versione)──>   [QUESTA slice]
categorie_clienti_listini ──(_via_listino)──>              [QUESTA slice]
```

Un solo adattatore nuovo: `fn_scope_ef_whitelist_via_listino_versione`, che
delega a `_via_listino` — la stessa che già protegge `listini_versioni`, quindi
la riga e la sua versione **non possono divergere**.

⚠️ Il contenuto qui sono **i prezzi**: articolo, unità di misura e prezzo dei
listini di ogni emittente erano leggibili da chiunque.
⚠️ `anagrafiche.categorie_clienti_listini` sta in un altro schema ma è un
satellite di `vendite.listini`: la slice è cross-schema, con il precedente di
`20260601-39-enable-rls-ondata2`.

#### Le mutazioni

| Mutazione | Chi se ne accorge |
| --- | --- |
| adattatore scambiato su `categorie_clienti_listini` | test 3 **e 7** |
| `listini_righe` senza `ENABLE` | test 2, 5, 9 |

⛔ Le due chiavi — `listino_versione_id` e `listino_id` — sono entrambe `bigint`
e i due adattatori hanno la **stessa firma**: scambiarli non dà nessun errore. E
nel verso negativo lo scambio *sembra funzionare* (un id di versione letto come
listino non trova quasi mai un listino ⇒ fail-closed). ⇒ A smascherarlo sono i
versi **positivi**: il test 7 esiste solo per questo.

#### 🔴 Il guard che legge sotto RLS — seconda occorrenza

`vendite.trgfn_listini_righe_guard_tipologia` **non è `SECURITY DEFINER`** e la
sua query risale `listini_versioni → listini` per confrontare le tipologie.
Sotto RLS quella lettura torna **zero righe**, il `SELECT INTO` lascia le
variabili NULL e il guard rifiuta **prima** della `WITH CHECK` — con un
messaggio che parla d'altro: *«articolo privo di listino_tipologia_id»*.

⭐ La scrittura è rifiutata lo stesso, quindi il perimetro tiene. ⚠️ Ma il
*motivo* che l'operatore leggerebbe è falso. Non è un difetto introdotto da
questa slice e non si corregge qui: è la trappola nota del guard che legge sotto
row level security, e questa slice ne registra la **seconda occorrenza**.
⇒ Candidato a un cantiere suo: rendere il guard `SECURITY DEFINER`, come è già
stato fatto altrove per la stessa ragione.

#### ⚠️ Due trappole della fixture, e la seconda è grossa

* `catalogo/articoli.csv` è **vuoto** (sola intestazione): i 257 articoli di
  sviluppo sono **dati di macchina**. Un test che cercasse un articolo esistente
  sarebbe verde qui e **senza materia in CI** ⇒ la fixture se lo costruisce. È
  la stessa specie di `anagrafiche.bank_branches` (§11.10).
* la tipologia **non si sceglie separatamente** dall'articolo:
  `trgfn_listini_righe_guard_tipologia` pretende
  `articolo.listino_tipologia_id = listino.tipologia_id`.
* e il `FORCE` va su **tutte e cinque** le tabelle toccate, non solo su quelle
  che la fixture popola — stesso inciampo di `pratiche`, stessa conseguenza: su
  un database ricostruito il test sarebbe passato **per sottrazione**.

#### Il registro dopo questa slice

**20 → 17 righe** (14 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`).

⚠️ **`vendite.attivita_fatturabili` resta**, e non è una dimenticanza: punta a
`listini_righe` (`listino_riga_id`, *nullable*) e da oggi ha un padre protetto in
più — ma la sua riga non è mai stata «manca un adattatore», è il debito
dichiarato del §6.1. *Aggiungere un padre protetto a una tabella scoperta non la
protegge: la rende scoperta per una ragione in più.*

---

### 11.12 🔴 Correzione: la riga di registro di `attivita_fatturabili` diceva il falso

Scritta il 2026-09-09, corretta il 2026-09-10 dopo una domanda di Tid.

La `ragione` diceva *«manca la DECISIONE, non l'attrezzo»*. ⛔ È **il contrario**
di ciò che il §6.1 aveva concluso, e con parole esplicite: *«la rotta portante è
`commessa_id`; `vendite.commesse` è già protetta e
`script.fn_scope_ef_whitelist_via_commessa` esiste già. **Zero helper nuovi, zero
decisioni.**»*

La domanda che il §6.1 lascia aperta è **un'altra** — *`billing_account_id`
dovrebbe essere `NOT NULL`?* — ed è lo stesso §6.1 a dire che **non blocca**:
*«è un cantiere suo, non si risolve mettendoci sopra una policy»*.

⇒ `vendite.attivita_fatturabili` non aspetta nessuna decisione: è **lavoro
pronto**.

⭐ **Perché la correzione conta più della riga.** Il campo `ragione` esiste per
dire a chi legge se ha davanti *un allarme*, *un lavoro pronto* o *una domanda
aperta*. Una riga che dice «manca una decisione» quando la decisione c'è
**ferma un cantiere che poteva partire** — e lo ferma in silenzio, perché nessuno
va a rileggere il paragrafo del brief per verificare la riga del registro.
⚠️ È lo stesso difetto che il registro serve a prevenire, capitato al registro
stesso.

⚠️ Corretta anche la riga di `attivita_consumi`, che diceva *«pende da
attivita_fatturabili»*: la FK va nel verso opposto
(`attivita_fatturabili.attivita_consumi_id`).

#### Che cosa manca davvero alla famiglia `commesse`

| Tabella | Rotta `NOT NULL` | Adattatore |
| --- | --- | --- |
| `attivita_fatturabili` | `commessa_id` → `vendite.commesse` | ✅ `_via_commessa` |
| `commesse_sorgenti` | `commessa_id` → `vendite.commesse` | ✅ `_via_commessa` |
| `commesse_attivita_log` | `commessa_attivita_id` → `vendite.commesse_attivita` | 🟠 da scrivere (un livello) |
| `attivita_consumi` | `billing_account_id` → `anagrafiche.billing_account` | 🟠 da scrivere |

⇒ **Nessuna decisione, due adattatori da scrivere.** È una slice come le altre.

> ⚠️ **Questa tabella è la fotografia dell'analisi, e una sua riga era pure
> sbagliata.** ✅ La slice è stata scritta e applicata: **§11.15**. E lì si è
> scoperto che gli adattatori da scrivere erano **uno**, non due —
> `script.fn_scope_ef_whitelist_via_efba` esisteva già ed è esattamente quello
> che protegge `anagrafiche.billing_account`. ⭐ Lo stesso difetto che questo
> paragrafo denuncia, capitato al paragrafo stesso.

⚠️ Le due `ragione` corrette vivono nel CSV: le porta nel database il mirror
`20260909-77` (`runOnChange`) al prossimo migrate, non serve un changeSet.

---

### 11.13 ✅ `attivita_fatturabili.billing_account_id` è `NOT NULL` — analisi e realizzazione

> Domanda aperta dal §6.1, decisa da Tid il **2026-09-10**.
> ✅ Slice `20260910-25..26` + `db/pgtap/vendite/test-af-billing-account-obbligatorio-v1.sql`:
> **applicata** il 2026-09-10, pgTAP **6/6 verde**, nessuna regressione.
> ⚠️ Ha richiesto la correzione di **sette `INSERT` in quattro pgTAP** esistenti,
> le cui fixture costruivano attività fatturabili senza billing account (§11.14).
>
> 📄 Doc aggiornata: `dbzero/vendite/manual/attivita_fatturabili.md` (il BA non è
> più «opz.», e la riga sulle FK diceva **due** cose false — vedi sotto) e
> `dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_ba_coerenza.md`,
> riscritta perché descriveva un controllo che il codice non faceva.
>
> 🔴 **Trovato aggiornando la doc**: il manual dichiarava la FK verso il billing
> account come `ON DELETE SET NULL`. Sul vincolo vivo **non c'è nessuna azione di
> cancellazione** (`ON UPDATE CASCADE` e basta): era gia' falso prima di questa
> slice, e nessuno se ne era accorto perché la doc di una FK non la rilegge
> nessuno finché non la si tocca.

#### L'argomento di dominio, ed è quello che mancava

Tid: *«se sono attività fatturabili devono per forza essere associate a un BA.
Tra l'altro la tabella BA esiste apposta, e si differenzia da `clienti` proprio
per rendere possibile la fatturazione di attività prima che un cliente sia
definito — l'utility del gas che fattura un allaccio.»*

⭐ È il pezzo che il §6.1 non aveva: non solo *«serve un BA»*, ma **perché il BA
è la cosa giusta da pretendere**. Il billing account è stato separato da
`clienti` proprio per esistere *prima* del cliente. ⇒ «non c'è ancora un
cliente» non è un motivo per cui il BA possa mancare: è la ragione per cui il BA
esiste.

#### La struttura dice la stessa cosa, e in modo indipendente

Letto dal catalogo il 2026-09-10 — **contratto, non popolazione**:

| Fatto | Conseguenza |
| --- | --- |
| `attivita_fatturabili.commessa_id` è **`NOT NULL`** | ogni attività ha una commessa |
| `vendite.commesse.billing_account_id` è **`NOT NULL`** | ogni commessa ha un BA |
| `vendite.fatture.billing_account_id` è **`NOT NULL`** | a fatturare, il BA è obbligatorio |

⇒ **Ogni attività fatturabile ha già un BA garantito, raggiungibile per una
catena di sole colonne obbligatorie.** Un `NULL` su
`attivita_fatturabili.billing_account_id` non può quindi significare *«non ce
n'è uno»*: può significare solo *«non è ancora stato copiato giù»*.

⭐ E questo risponde anche all'obiezione del §6.1 — *«una policy su una chiave
nullable ha un buco esatto dove il NULL passa»*: il buco esiste perché la
colonna è nullable **senza che il modello lo richieda**, non perché il dato
manchi.

#### ⚠️ Il fatto datato, e vale solo come assenza di controesempio

2026-09-10, su 59 righe: **0** con BA nullo, **59** con BA uguale a quello della
propria commessa, **0 dissenzienti**.

⛔ Questo **non è** l'argomento: «oggi non capita mai» non dice che il caso non
esista. Vale in un verso solo — *non c'è nessun controesempio da spiegare*, e un
eventuale backfill non troverebbe righe incoerenti da decidere.

#### 🔴 Trovato strada facendo: un guard che non arriva mai a validare

`vendite.trgfn_attivita_fatturabili_guard_ba_coerenza` (BEFORE INSERT OR UPDATE)
apre così:

```sql
IF NEW.commessa_attivita_id IS NOT NULL THEN RETURN NEW; END IF;
```

Ma `commessa_attivita_id` è **`NOT NULL`** sulla tabella. ⇒ Il ramo che valida
la coerenza BA/utility si raggiunge **solo** su righe che il `NOT NULL`
rifiuterà comunque un istante dopo — il vincolo si controlla dopo i BEFORE
trigger. In pratica: su ogni riga che sopravvive, il guard esce subito.

⚠️ Non è un difetto introdotto oggi e non si corregge qui, ma va saputo prima di
toccare quella tabella: *un guard che sembra presidiare la coerenza del BA, e
non la presidia.* La sua intestazione lo dice pure — «coerenza garantita a monte
dal push» — quindi la scelta era consapevole; è la colonna che nel frattempo è
diventata obbligatoria.

#### Il cantiere previsto, e com'è andato davvero

Il piano era in quattro punti. ⭐ **Ne è servito uno**, e vale la pena
registrare perché — verificato sul catalogo il 2026-09-10:

| # | Previsto | Esito |
| --- | --- | --- |
| 1 | il **normalizzatore** deriva il BA dalla commessa quando arriva `NULL` | ⛔ **non fatto, e non serviva** |
| 2 | backfill delle righe esistenti | ✅ **niente da fare**: zero righe con BA nullo |
| 3 | `SET NOT NULL` + il pgTAP che pinna l'invariante | ✅ `20260910-25`, pgTAP 6/6 |
| 4 | l'armamento sulla rotta del §6.1 (`commessa_id`) | ✅ §11.15, slice `20260910-27..30` |

⛔ **Il punto 1 è caduto, e la ragione è che il punto 3 lo rende irraggiungibile**:
con la colonna `NOT NULL` un `NULL` non arriva mai al normalizzatore — lo
rifiuta il vincolo. Letto il corpo di `trgfn_attivita_fatturabili_normalize`,
`billing_account_id` compare **solo in lettura** (per risolvere valuta ed
emittente): non c'è nessun `NEW.billing_account_id := …`, e non ci deve essere.
⇒ Chi scrive senza BA prende un errore di vincolo invece di un valore dedotto —
*fail-fast invece che derivazione silenziosa*, ed è la scelta giusta quando il
dato **si può fornire**.
⚠️ È anche il motivo per cui il §11.14 ha dovuto correggere sette `INSERT` in
quattro pgTAP: senza normalizzatore, chi non passa il BA si ferma.

⛔ **E i punti 1-3 non erano un prerequisito dell'armamento** (§11.12): sono un
cantiere di modello, e l'ordine fra i due non contava — infatti il §11.15 si è
armato sulla rotta `commessa_id`, che con il billing account non c'entra.

---

### 11.14 🔴 Il difetto di METODO che ha quasi fatto passare una regressione

> Successo il 2026-09-10, scrivendo la slice del §11.13. È la cosa più
> importante di quella giornata, e non riguarda il database.

Prima di rendere `billing_account_id` obbligatorio ho fatto la cosa giusta —
censire i pgTAP che **scrivono** su `attivita_fatturabili`, 42 file — e li ho
confrontati prima/dopo. Esito: *«nessuna divergenza, tranne il test nuovo»*.

⛔ **Era falso, e il metodo era cieco proprio al caso peggiore.** Confrontavo il
numero di righe `not ok`. Ma un file che muore nel **fixture** non produce
nessun `not ok`: produce *meno asserzioni*. Quattro test collassavano —
`test-esito-gruppi-giro-v1` da **12 asserzioni a 2**,
`test-vw-dash-competenza-v1` da **23 a 3**, e altri due — e tre di loro
risultavano «zero rossi prima, zero rossi dopo».

⭐ **La metrica giusta è il numero di ASSERZIONI ESEGUITE, non quello dei
fallimenti.** È la stessa cosa che il progetto già scrive della baseline — *«un
file che fallisce nel fixture non esegue nessuna asserzione: la sua copertura
vale zero, non parziale»* — ma io la stavo misurando nel modo che quella frase
descrive come sbagliato.

#### ⚠️ E la causa era un secondo errore di perimetro

Avevo scritto, nel changeSet: *«l'UNICA funzione che scrive in questa tabella è
`fn_emit_attivita_fatturabili_da_commessa`, e il BA lo passa già»*. Vero — ma il
censimento era su **`pg_proc`**, cioè sulle funzioni del database. ⛔ **Le
fixture dei pgTAP inseriscono direttamente**, e non passavano il BA.

⭐ Il che, però, è un argomento **a favore** del vincolo, non contro: quelle
fixture costruivano righe che il dominio non ammette — attività fatturabili
senza billing account. ⇒ Corrette tutte e sette le `INSERT` nei quattro file,
derivando il BA dalla commessa, che è la stessa rotta del backfill.

#### Le mutazioni della slice

| Mutazione | Chi se ne accorge |
| --- | --- |
| rimessa l'uscita anticipata nel guard | test 2 (struttura) **e 4** (comportamento) |
| tolto il `SET NOT NULL` | test 1 |

⚠️ E il **test 2 era rosso alla prima stesura per la ragione sbagliata**: cercava
`commessa_attivita_id IS NOT NULL` in `prosrc`, e la trovava nel **commento** che
spiega il difetto. Corretto cercando nel codice privato dei commenti — è la
trappola nota del presidio che si accende sulla prosa.

---

### 11.15 ✅ La quinta famiglia: `commesse`

> Stato: ✅ **applicata** il 2026-09-10 alle **18:33** — slice `20260910-27..30` +
> `db/pgtap/rls/test-rls-commesse-satelliti.sql`, pgTAP **16/16 verde**, nessuna
> regressione. Verificato a valle sul catalogo: le quattro tabelle hanno
> `relrowsecurity` e una policy ciascuna, `fn_scope_ef_whitelist_via_commessa_attivita`
> è `STABLE` e non `SECURITY DEFINER`, il registro è a **14 righe** e
> `dbops.vw_rls_perimetro_scoperto` non ha **nessuna riga** fuori da
> `DEBITO_DICHIARATO`.
>
> ⭐ Prima dell'apply la slice era stata provata eseguendo l'**SQL estratto dai
> changeSet** (non riscritto) dentro una transazione chiusa da `ROLLBACK`, con lo
> stesso esito: 16/16, e presidio del perimetro 8/8 con il registro aggiornato.

Le quattro righe di registro della famiglia — id 10, 11, 12, 13 — sono
`attivita_fatturabili`, `attivita_consumi`, `commesse_attivita_log`,
`commesse_sorgenti`.

| Tabella | Rotta `NOT NULL` | Adattatore |
| --- | --- | --- |
| `attivita_fatturabili` | `commessa_id` → `vendite.commesse` | ✅ `_via_commessa` |
| `commesse_sorgenti` | `commessa_id` → `vendite.commesse` | ✅ `_via_commessa` |
| `commesse_attivita_log` | `commessa_attivita_id` → `commesse_attivita` | ✅ `_via_commessa_attivita`, **l'unico nuovo** (`20260910-27`) |
| `attivita_consumi` | `billing_account_id` → `anagrafiche.billing_account` | ✅ `_via_efba` |

#### 🔴 Una seconda `ragione` del registro diceva il falso

La riga di `attivita_consumi` sosteneva che *«l'adattatore che risale da un
billing account all'emittente non esiste ancora: è **l'unico pezzo da
scrivere** della famiglia commesse»*. ⛔ `script.fn_scope_ef_whitelist_via_efba`
esiste, ed è **esattamente la funzione che protegge `anagrafiche.billing_account`**
— cioè il padre di quella tabella. Delegarle è la stessa forma di
`_via_listino_versione → _via_listino` (§11.11): il consumo e il suo billing
account non possono divergere.

⭐ È la **seconda** occorrenza dopo quella corretta al §11.12, e la lezione è la
stessa scritta lì: *una riga che dice «manca un attrezzo» quando l'attrezzo c'è
ferma un cantiere che poteva partire, e lo ferma in silenzio.* ⇒ Il §11.12
prometteva **due** adattatori da scrivere. Ne serviva **uno**.

#### ⭐ La decisione: `attivita_consumi` porta UNA veste sola

Decisione di Tid, 2026-09-10. È l'unica delle quattro la cui testata ha più
vesti: `anagrafiche.billing_account` porta `OPERATORE FOR ALL`, una `FOR INSERT`,
`CLIENTE_PORTALE FOR SELECT` e `SHOP_CUSTOMER FOR SELECT` con la condizione in
più sul canale.

⭐ Comanda la sola veste operatore, e la ragione sta sul modello:
`attivita_consumi` **non è una faccia dell'anagrafica** — è un documento
*sorgente* della pipeline di fatturazione (`config.sorgenti`, codice interno
`ATTIVITA_CONSUMI`) che *nomina* un cliente. Non ha nessuna colonna emittente, e
il cliente i consumi li vede resi **sulla fattura**, non come righe grezze.

⛔ **E non è neutra, quindi va dichiarata**: oggi quella tabella non filtra
affatto, quindi una sessione `CLIENTE_PORTALE` o `SHOP_CUSTOMER` ne vede
**tutte** le righe; da questa slice non ne vedrà **nessuna**. È una porta che si
chiude — l'opposto della postura tenuta al passo 2 su `ordini`, dove le vesti si
rispecchiarono tutte. ⚠️ Il giorno in cui il portale dovrà mostrare i consumi, la
veste si **aggiunge** con la sua ragione: non la si eredita di straforo.
⚠️ Fatto datato, e vale solo come assenza di controesempio: al 2026-09-10 nessun
percorso del backend legge quella tabella (zero riferimenti in `backend/`).

#### ⛔ E il criterio ne consegna CINQUE, non quattro — di nuovo

`vendite.attivita_fatturabili_log` ha **una sola FK**, verso `attivita_consumi`.
Finché la madre non era protetta era **fuori perimetro**, non nascosta: armandola
entra nel criterio e uscirebbe `NON_DICHIARATO`, cioè rosso. È la transitività
già vista su `pratiche` (§11.7), che qui costa una riga di registro invece di un
rosso.

⛔ **Ma non si arma**, e la ragione è la stessa che tiene fuori
`magazzino.assets` e `pagamenti.sepa_mandati`: quella FK è **nullable**, e una
policy costruita su una chiave nullable ha un buco esatto dove il NULL passa.
⇒ Riga nuova nel registro (id 14, `2026-09-10`) con la domanda per intero — che
è **doppia**, perché la tabella non ha **nessuno scrittore**, né nel database né
nel backend (l'unica citazione in `fn_riporta_attivita_da_emettere` è un commento
che dice «non è questa tabella»): o `attivita_consumi_id` diventa `NOT NULL` e
allora si arma come le sorelle, oppure è un residuo e si **ritira**.

#### ⚠️ La rotta di `attivita_fatturabili`: la decisione tiene, l'argomento no

Il §6.1 scelse `commessa_id` perché `billing_account_id` era **nullable**. Dalla
slice `20260910-25` (§11.13) quella colonna è `NOT NULL`: **quell'argomento non
esiste più**, e la decisione va ri-appoggiata o non è una decisione.

Regge su due ragioni che non dipendono dalla nullabilità:

* sul **modello**, un'attività fatturabile è una riga del *giornale della
  commessa* — è l'emittente che fatturerà a decidere chi la vede;
* `script.fn_scope_ef_whitelist_via_attivita_fatturabile`, che protegge già
  `note_attivita_fatturabili` dal passo 8, risale per `commessa_id`. Una rotta
  diversa qui farebbe rispondere in due modi **la nota e il suo soggetto**.

#### ⭐ Provato facendolo fallire

| Mutazione | Chi se ne accorge |
| --- | --- |
| `_via_commessa` al posto di `_via_commessa_attivita` sul diario | test 3 **e 9** |
| una veste `CLIENTE_PORTALE` su `attivita_consumi` | test 4, e **solo** lui |
| `commesse_attivita_log` senza `ENABLE` | test 2, 10, 13, 15 |
| la policy del diario **rinominata** | test 3 |

⛔ La prima è il refuso muto della famiglia: le due funzioni hanno la stessa
firma `(integer, bigint)` e le due chiavi sono entrambe `bigint`. Nel verso
**negativo** lo scambio *sembra funzionare* — il test 10 resta verde, perché un
id di riga letto come id di commessa non trova nessuna commessa e la riga altrui
resta invisibile lo stesso. Senza il gemello **positivo** sarebbe passato: è la
stessa lezione di `pratiche` (§11.7) e di `lotti` (§11.9), su un terzo errore.

⛔ **La quarta mutazione ha trovato un verde per sottrazione nella prima
stesura.** Il test 3 era scritto come `is_empty` — *«nessuna policy usa
l'adattatore sbagliato»* — e con la policy **rinominata** il join non trovava più
niente da giudicare: zero righe cattive, verde. ⇒ Riscritto sul **denominatore
noto** (`= 4`), la rinomina lo fa cadere. *Un presidio che conta i cattivi è muto
quando il rotto esce dal join.*

⚠️ E i test 1 e 3 sono stati **ristretti** dopo la seconda mutazione: contavano
le *policy* invece delle *tabelle*, e pretendevano l'adattatore operatore da
*ogni* policy. Una veste aggiunta domani li avrebbe fatti cadere entrambi — nel
posto sbagliato. A pretendere che la veste resti una sola è il **test 4**, che
quella decisione la nomina; gli altri due misurano copertura e chiave.

#### ⚠️ Le regressioni: misurate DOPO l'apply, e da chi poteva

Le regressioni sugli altri **73 pgTAP** che nominano queste quattro tabelle non
erano misurabili prima: la misura che conta va fatta come `zeroerp_app` — l'owner
è esente dalla RLS senza `FORCE`, quindi da lì sarebbe muta — e `titodb` non può
`SET ROLE` su di lui. ⇒ Andava fatta **dopo l'apply**, ed è stata fatta.

✅ Esito riportato da Tid, 2026-09-10 dopo l'apply: **nessuna regressione né su
`db-test` né su `db-ci`** — cioè né sul database di sviluppo né su un database
ricostruito da zero. ⭐ È la seconda metà che conta: `anagrafiche` in CI è
**vuoto**, quindi un verde su dbdev non dice niente su `zeroerp_ci`.

⭐ L'argomento strutturale che dice dove guardare — e non sostituisce la corsa:
`vendite.commesse`, `vendite.commesse_attivita` e `anagrafiche.billing_account`
sono **già** in RLS, e le quattro policy nuove usano **gli stessi adattatori
delle rispettive madri**. Un test che oggi attraversa la madre è già dentro un
perimetro, e il satellite non può essere più chiuso di lei. ⇒ Il rischio non è
lì: è nei test che **leggono un satellite senza passare dalla madre**, cioè che
contano righe preesistenti del database di sviluppo. I cruscotti di competenza
(`vw_dash_competenza_*`) sono di quella specie, e il §11.14 li ha già visti
collassare una volta.

⛔ **E si misura sulle ASSERZIONI ESEGUITE, non sui `not ok`** — §11.14: un file
che muore nel fixture non produce nessun rosso, produce *meno asserzioni*.

✅ Quello che **è** stato verificato, con la slice simulata in transazione:
`test-rls-note-padre` (9/9), `test-rls-policies-structure` (28/28),
`test-rls-write-policies-structure` (33/33), `test-role-batch-fatturazione-postura`
(19/19), `dbops/test-catalogo-presidi-v1` (11/11) e
`test-rls-viste-security-invoker` (5/5) restano verdi.
⭐ E su quest'ultimo non c'era niente da sistemare: le **otto** viste che leggono
le quattro tabelle hanno già tutte `security_invoker` — a differenza di
`preventivi` al passo 1, dove le due viste andarono nello stesso changeSet.

#### 🔴 Trovato strada facendo: la baseline di `vendite` segnala regressioni che non lo sono

Misurato il 2026-09-10, **prima** di questa slice e con la slice **non
applicata**: `scripts/pgtap-baseline.sh vendite` segnala **18 rossi su 278**, di
cui **13 «regressioni»** non presenti in `baseline-rossi.tsv`.

⛔ Non lo sono, e ci sono **due** prove indipendenti:

* rilanciati **uno per uno** quei file sono **tutti verdi** (provati:
  `test-emittente-ddt-simmetria-v1`, `test-vw-dash-competenza-gruppi-cliente-v1`,
  `test-documento-lineage-v1`, `test-elimina-fattura-da-lotto-v1`);
* ⭐ e **la seconda corsa consecutiva dà un insieme DIVERSO**: 12 invece di 13,
  con **sei** file in comune e gli altri sostituiti — spariscono i cinque
  `vw_dash_*` e `emittente-ddt-simmetria`, compaiono i quattro `resi-*` e i due
  `registro-*`. Stesso database, nessuna modifica in mezzo.

⇒ Quello che le due prove stabiliscono è che **quei rossi dipendono dalla corsa,
non dal codice**: nessuno di quei file ha un difetto proprio. ⛔ La **causa** non
è stata trovata, e chiamarla «contaminazione» sarebbe una conclusione più larga
della misura — l'interferenza fra file è l'ipotesi naturale (la trappola nota dei
pgTAP non transazionali, dichiarata chiusa il 2026-08-06), ma andrebbe provata,
e potrebbe essere anche ordine di esecuzione, sequenze o stato residuo di sessione.

⚠️ **L'insieme instabile è però il segno diagnostico da usare**: un rosso vero
non cambia nome fra due corse consecutive. Prima di inseguire una «regressione»
segnalata dalla baseline, **rilanciarla** e confrontare i due elenchi.

⚠️ **Perché va scritto qui**: chi applicherà questa slice lancerà la baseline
subito dopo, vedrà quei tredici e li attribuirà al cantiere commesse. Non sono
suoi, ed erano lì **prima**. ⛔ Ma non sono nemmeno innocui: una baseline che
produce tredici falsi rossi non distingue più una regressione vera da una
finta — cioè *smette di essere un presidio nel momento in cui serve*. È un
cantiere suo, e va aperto.

#### Il registro dopo questa slice

**17 → 14 righe** (11 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`): quattro
pagate, una nuova.

---

### 11.16 ✅ La sesta famiglia: `documenti`

> Stato: ✅ **applicata** il 2026-09-10 alle **19:17** — slice `20260910-31..34`
> + `db/pgtap/rls/test-rls-documenti-satelliti.sql`, pgTAP **13/13 verde**,
> **nessuna regressione** (esito riportato da Tid dopo l'apply).
> Verificato a valle sul catalogo: i due satelliti hanno `relrowsecurity` e una
> policy ciascuno, `fn_scope_ef_whitelist_via_documento_generato` è `STABLE` e
> non `SECURITY DEFINER`, il registro è a **12 righe** e
> `dbops.vw_rls_perimetro_scoperto` non ha **nessuna riga** fuori da
> `DEBITO_DICHIARATO`.
>
> ⭐ Prima dell'apply la slice era stata provata eseguendo l'**SQL estratto dai
> changeSet** (non riscritto) dentro una transazione chiusa da `ROLLBACK`, con lo
> stesso esito: 13/13, presidio del perimetro 8/8 col registro aggiornato,
> `liquibase validate` pulito, sei guardrail CI verdi, timeline autogen
> nell'ordine 31 → 32 → 33.

I due satelliti di `documenti.documenti_generati`: **`documenti_generati_eventi`**
(il diario) e **`documenti_generati_file`** (la riga da cui si arriva al file su
storage). Righe di registro id **40** e **41**.

#### ⭐ È la famiglia più semplice di tutte, e i fatti dicono perché

Letto dal catalogo il 2026-09-10 — **struttura, non popolazione**:

| | |
| --- | --- |
| chiave | **una sola**, `documento_generato_id` `NOT NULL` su entrambi ⇒ **un** adattatore |
| vesti | **una**, `rls_documenti_generati_ef_whitelist` (`OPERATORE`, `FOR ALL`) — nessuna decisione come su `attivita_consumi` |
| rotta | la testata porta `emittente_fiscale_id` **`NOT NULL`** e usa `script.fn_scope_ef_whitelist` **diretta** — non `_via_sr`, non `_via_efba` |
| nipoti | ⭐ **nessuno**: niente ha una FK verso i due satelliti ⇒ nessuna sorpresa al giro dopo, al contrario di `pratiche` (§11.7) e `commesse` (§11.15) |
| viste | ⭐ **nessuna**: zero viste li leggono ⇒ niente `security_invoker` da sistemare |
| grant | `zeroerp_app` ha `SELECT, INSERT, UPDATE, DELETE` su entrambi ⇒ serve `FOR ALL` con `WITH CHECK`, non `FOR SELECT` |

⚠️ **Il contenuto è il motivo per cui vale**: `documenti_generati_file` porta
`storage_key`, `file_name`, `sha256` e `mime_type` — è la riga da cui si **arriva
al file**. Fuori perimetro non si leggono metadati: si leggono le coordinate del
PDF di un'altra azienda.

#### ⚠️ Due trigger che cambiano come si scrive il pgTAP

* `documenti_generati_eventi` è **append-only**: due guard `a10_` bloccano
  `UPDATE` e `DELETE`. ⇒ La prova di scrittura fuori perimetro dev'essere un
  **`INSERT`**, non un update — e con un update il test sarebbe verde per la
  ragione sbagliata, cioè per il trigger e non per la `WITH CHECK`.
* `documenti_generati_file` ha `a10_protect_file` su `UPDATE`. Stessa
  conseguenza.

⭐ `zeroerp_batch_fatturazione` è `BYPASSRLS`: la generazione documentale in
batch non cambia comportamento.

#### ⚠️ Quello che la fixture deve costruirsi, e la sorpresa

`documenti.template_documenti` porta **`emittente_fiscale_id` `NOT NULL`**: il
template è *scoped per emittente*, come i listini (§11.11). ⇒ Ogni mondo del
pgTAP ha il **suo** template e la sua versione — e per quelle due tabelle non
c'è nessun seed: sono **dati di macchina**. Un test che cercasse un template
esistente sarebbe verde su dbdev e **senza materia in CI**.

⭐ Vengono invece dai changelog e si possono leggere: `tipi_documento_output`
(6 righe), `tipi_file_documento` (2), `render_engine_documento` (1),
`config.sorgenti` (15).
⚠️ E i quattro campi del documento devono **combaciare** con quelli del
template: `trgfn_documenti_generati_check_coerenza` pretende versione, tipo
output, sorgente ed emittente coerenti. Un campo fuori posto e il documento non
nasce — con un errore che parla di coerenza, non di perimetro.

#### ⭐ Provato facendolo fallire — e la quarta mutazione ha aggiunto un test

| Mutazione | Chi se ne accorge |
| --- | --- |
| `_via_sr` al posto di `_via_documento_generato` | test 3, **4**, 12 |
| `documenti_generati_file` senza `ENABLE` | test 2, 5, 9, 10 |
| la policy del file **rinominata** | test 3 |
| **`FOR SELECT`** invece di `FOR ALL` | test 3 e **13** |
| `FOR ALL` con la `WITH CHECK` **omessa** | test 3 soltanto |

⛔ **La quarta ha trovato un buco, e il test 13 è nato da lì.** Con una policy di
sola lettura la RLS è **deny-all in scrittura**: i test 8 e 9 restano *verdi* —
«l'INSERT altrui è rifiutato» è vero anche quando sarebbe rifiutato pure il
**proprio**. *Un fail-closed su tutto supera ogni prova negativa.* ⇒ Aggiunto il
gemello positivo della scrittura: *A scrive nel proprio documento*.

⭐ **La quinta invece NON è un difetto**, ed è il motivo per cui resta in
tabella: omettere la `WITH CHECK` su un `FOR ALL` non cambia il comportamento,
perché PostgreSQL riusa la `USING` ([linee-guida-sql §10.6](../../linee-guida-sql.md)).
Cambia solo la forma — e a vederlo è il test **strutturale**, che è il posto
giusto.

🔴 **E c'è un errore di metodo da registrare**: la prima stesura della quarta
mutazione *non mutava quello che credevo*. Sostituiva `FOR ALL` con un match
sull'indentazione sbagliata, quindi produceva `FOR ALL` **senza `WITH CHECK`** —
cioè la quinta. Da lì avevo concluso che «il test 8 non distingue `FOR ALL` da
`FOR SELECT`»: conclusione **giusta**, ma tratta da una prova che non la
sosteneva. ⚠️ Verificato interrogando `pg_policies` invece di fidarsi dello
script: *una mutazione va guardata in ciò che PRODUCE, non in ciò che il diff
sembra dire.*

#### Il registro dopo questa slice

**14 → 12 righe** (9 `FIGLIA_DI_TABELLA_PROTETTA` + 3 `POLICY_INERTE`).
⭐ E questa volta **non entra nessuna riga nuova**: nessuna tabella ha una FK
verso i due satelliti, quindi armarli non fa entrare nessuno nel criterio al
giro dopo — al contrario di `pratiche` (§11.7) e `commesse` (§11.15).

---

### 11.8 Che cosa resta, ora che il presidio è in servizio

* le **12 righe** del registro sono dodici lavori con un nome, il più corto
  dei quali (`shop.ricevute`) è una riga di SQL;
* ✅ **`pratiche`** (§11.7), **`lotti`** (§11.9),
  **`vendite_contabili_lotti`** (§11.10), **`listini`** (§11.11),
  **`commesse`** (§11.15) e **`documenti`** (§11.16) sono **applicate** — e
  `commesse` ha consegnato al registro una riga nuova
  (`attivita_fatturabili_log`).
  Restano: **anagrafiche** (3, di cui due sono una domanda di modello, §11.4) e
  le singole di `config`, `magazzino`, `pagamenti`, `shop`, più
  `vendite.fatture_arrotondamenti_scope` e `vendite.attivita_fatturabili_log`;
* ⭐ **`vendite` è finito.** Delle 12 righe rimaste **due** sono in questo
  schema — `fatture_arrotondamenti_scope` e la nuova `attivita_fatturabili_log`
  — e nessuna delle due è un armamento: sono domande di modello. ⇒ Il cantiere
  del perimetro esce da `vendite` e passa agli altri schemi;
* ⭐ **Due righe di registro su diciassette dicevano il falso**, e in tutti e
  due i casi nel verso che *ferma* un cantiere: «manca una decisione» quando la
  decisione c'era (§11.12), «manca un adattatore» quando l'adattatore c'era
  (§11.15). ⇒ Quando una riga si legge come «lavoro bloccato», la sua `ragione`
  va **verificata sul catalogo** prima di crederle;
* ⚠️ resta fuori dal criterio, e va ricordato, il debito dello **`storico`**
  (§9): 120 tabelle senza RLS. Non entrano qui perché non hanno una FK verso le
  madri — sono **gemelle**, non figlie. Il criterio non le vede, e questo brief
  non deve far credere il contrario.

---

*Analisi 2026-09-09 — letture di struttura sul database `zeroerp` (pg_policies,
pg_constraint, pg_class.relrowsecurity, role_table_grants). Nessun conteggio di
righe di lavoro è usato come argomento.*
