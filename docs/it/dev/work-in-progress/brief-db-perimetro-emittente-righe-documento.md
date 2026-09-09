# Brief DB — Il perimetro dell'emittente si ferma alla testata

> Stato: ✅ **TUTTI E OTTO I PASSI APPLICATI** — su database di sviluppo e su
> database ricostruito dai changelog. `db/pgtap/rls/`: **30 file su 30 verdi**.
> Analisi e realizzazione del 2026-09-09.
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

### ⭐ Il presidio che serve, e che NON è stato scritto (→ §10)

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
* `vendite` conta **83 policy** e `script` **35 adattatori `fn_scope_*`**;
* `db/pgtap/rls/`: **30 file, 30 verdi**, su database di sviluppo e su database
  ricostruito dai changelog.

### 🟠 Cosa resta scoperto, e non è una dimenticanza

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

### ⛔ Il presidio del §8 non è stato scritto, ed è la cosa da fare per prima

Questo cantiere ha prodotto **un** presidio transitivo, ed è piccolo: il test 4
di `test-rls-note-padre.sql`, che confronta i rami dello smistatore con il
`CHECK` della tabella. Funziona perché il suo perimetro è un **contratto** e non
una lista.

Il presidio generale — *ogni tabella con una FK verso una tabella in RLS ha a
sua volta una policy e la RLS accesa, oppure è dichiarata nel registro del
debito con la sua ragione tecnica* — **non esiste ancora**. La query che lo
alimenta è quella usata per la tabella qui sopra; il registro del debito
sarebbe, oggi, esattamente quelle dodici righe con le loro quattro ragioni.

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

*Analisi 2026-09-09 — letture di struttura sul database `zeroerp` (pg_policies,
pg_constraint, pg_class.relrowsecurity, role_table_grants). Nessun conteggio di
righe di lavoro è usato come argomento.*
