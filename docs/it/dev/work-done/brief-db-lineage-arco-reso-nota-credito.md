# Brief DB — l'arco che manca: dal reso alla nota di credito

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Cos'è.** Il grafo di genealogia dei documenti (`vendite.vw_documento_lineage_archi`,
> pannello «Passaggi») ha dieci archi e **si ferma sul reso**. La nota di credito
> che accredita quel reso esiste, è collegata alla fattura che rettifica (arco N)
> e alla commessa (arco G), ma **non al reso**. I due rami di ritorno — la merce
> che torna e il valore che torna — non si toccano mai.
>
> **Origine.** Tid, 2026-08-25, collaudo in-app della nota di credito: *«manca un
> collegamento tra la nota credito e il reso, non riesco a ritrovarlo — esempio
> nota credito 20024»*.
>
> **Il dato c'è già ed è esatto.** Non si inventa un legame: si legge quello che
> `vendite.resi_righe_accrediti` registra dal 2026-08-18. La consegna è **un
> undicesimo arco**, calcolato come G e N (soft-link, nessuna tabella ponte).
>
> **Stato.** 2026-08-25 — analisi **verificata sul DB vivo** (§0), **cinque**
> correzioni portanti al piano (§0.2), **tre decisioni di Tid** che hanno
> allargato il cantiere (§8): il perimetro RLS si chiude su tutti gli archi, non
> solo su `S`; la natura NOTA_CREDITO si asserisce; `vw_resi_lista` diventa la
> sesta sorella. **CONSEGNA DB SCRITTA E APPLICATA** il 2026-08-25:
> `20260825-19/20/21`, seed CSV, due pgTAP estesi — **38/38** e **30/30**,
> baseline `vendite` senza regressioni.
>
> ⛔ **2026-08-26 — il «zero BE, zero FE» del §5 DB-F.4 era FALSO**: tre buchi,
> tutti silenziosi, chiusi lo stesso giorno (repository, slot della lista,
> presidio esteso da 5 a 6 liste). Pagato anche il debito delle tre pagine
> **manual**, dove sopravviveva la prosa che il `20260825-20` aveva corretto nel
> `COMMENT`.
>
> 🔴 **E la misura ha trovato un difetto nuovo**: la colonna «Transito» chiama
> **«Fattura»** la nota di credito, perché la natura della frontiera non esce
> dalla summary (`frontiera_uid` non è in lista). Preesistente, già a video sugli
> ordini; questo cantiere lo rende **strutturale**. Richiesta al team DB nel
> **§7-bis** — BE/FE aspettano.
>
> Restano la verifica in-app (§6), il §7-bis e i due residui del §7.
>
> **Correlati:**
> [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md) §44 ·
> [collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md)

---

## 0. ⭐ Verifica critica (2026-08-25) — che cosa è stato misurato, e come

L'analisi dei §1-§7 è stata **rimisurata sul database di sviluppo**, non riletta.
Il metodo: la vista modificata è stata ricreata **dentro una transazione chiusa
in `ROLLBACK`**, con uno snapshot della summary prima e il diff dopo. Tutto ciò
che segue è un numero letto, non un ragionamento.

### 0.1 Quello che il brief diceva giusto — confermato sul dato

| Affermazione del brief | Esito della misura |
| --- | --- |
| La query dell'arco `S` torna **una riga**, reso 24 → NC 20024 | ✅ confermato — e **3 righe prima del `DISTINCT`**: il `DISTINCT` serve davvero |
| `uq_attivita_fatturabili_commessa_attivita` rende il join 1:1 | ✅ è un `CREATE UNIQUE INDEX` su `commessa_attivita_id` |
| Nessun indice nuovo | ✅ i quattro join sono su PK o UNIQUE; `ix_resi_accrediti_commessa_attivita_id` c'è |
| `fn_documento_lineage` non va toccata | ✅ il traversal attraversa **tutti** gli archi e si limita a esporre `is_ramo_inverso`: l'arco `S` compare da solo |
| `vw_documento_lineage` (il corpo) non va toccata | ✅ legge `is_ramo_inverso`, non le lettere |
| Nessuna modifica al frontend | ✅ `lineageDocumentoLabel` esiste, e le chiavi `vendite.lineage.natura_nota_credito` e `vendite.lineage.tipo_reso_vendita` sono **entrambe** già in `it.json`/`en.json` |
| Nessuna modifica al backend | ✅ nessun consumatore BE conosce le lettere degli archi (grep su `backend/`: zero occorrenze) |
| Le invarianti 18, 29, 30 restano vere | ✅ **misurate** dopo la modifica, non dedotte: valgono 0 tutte e tre, insieme a 13/14/17/19/20/27/28/31 |
| `20260821-01..04` sono applicati | ✅ `EXECUTED` in `databasechangelog`, 2026-08-21 |
| Il pgTAP `test-documento-lineage-v1` è verde | ✅ non compare in **nessuna** delle due baseline: una regressione si vedrebbe |

⭐ **Una misura che il brief non aveva e che cambia la lettura del `WHERE`.**
Gli accrediti registrati sono **5**, ma solo **3** hanno un'attività fatturabile
già emessa. I resi `5796` e `5798` sono accreditati e **non ancora fatturati**:
l'arco `S` per loro **non esiste ancora**, e comparirà all'emissione. Il
`WHERE af.fattura_riga_id IS NOT NULL` non è una formalità copiata dall'arco G —
è il cancello che tiene fuori due casi su tre **oggi**, sul dato vero.

### 0.2 ⛔ Cinque correzioni al piano — trovate misurando

Sono i punti in cui il brief, così com'era, avrebbe prodotto un difetto o una
verifica che non verifica. Ognuna è recepita nel §5 corrispondente.

| # | Rilievo | Dove è recepito |
| --- | --- | --- |
| **1** | ⛔ **L'arco `S` come scritto ESCE dal perimetro RLS dei resi** — e non è solo `S`: sono **quattro archi su dieci** già in esercizio. | §5 · DB-A |
| **2** | ⚠️ Il `COMMENT` di `vw_documento_lineage` **non va corretto ricreando la vista**. | §5 · DB-C |
| **3** | ⚠️ Il terzo pgTAP proposto misura il **dato**, non la **regola**. | §5 · DB-E |
| **4** | ⚠️ Gli **effetti sulla summary** non erano nominati: sono due righe su 425, ed entrambe vanno dichiarate. | §5-bis |
| **5** | ⭐ L'arco `S` arriva **sempre** a una nota di credito, e questo si può **asserire**: il brief lo dava per non asseribile. | §5 · DB-E, test 35 |

#### Rilievo 1 — la RLS, per esteso: non è un difetto di `S`, è una classe

`vendite.resi` ha la Row Level Security **attiva** (`rls_resi_ef_whitelist`,
changeSet `20260713-17`). `vendite.resi_righe` e `vendite.resi_righe_accrediti`
**no**. La query del brief arriva a `reso_id` **passando solo da `resi_righe`**:
l'arco esisterebbe anche per un reso che la whitelist dell'operatore nasconde.
L'estremo *fattura* è protetto (il join su `fatture_righe` porta la sua RLS),
l'estremo *reso* no.

⭐ **Cercati i gemelli, e ci sono.** Misurato ramo per ramo contro
`pg_class.relrowsecurity`:

| arco | estremi | la tabella con RLS è joinata? |
| --- | --- | --- |
| `A` · `C` · `D` · `H` · `R` | preventivi / offerte / ordini / contratti / ddt / resi | ✅ **sì**, entrambi |
| `N` | `fatture_righe` (RLS propria) su entrambi i lati | ✅ equivalente |
| **`B` · `E` · `F`** | sorgente **e** commessa, via `commesse_sorgenti` | ⛔ **no, nessuno dei due** — `commesse_sorgenti` non ha RLS, e né `preventivi`/`ordini`/`contratti` né `commesse` sono joinate |
| **`G`** | commessa | ⛔ **no** — emette `af.commessa_id` senza joinare `vendite.commesse` (che ha `relrowsecurity = t`) |
| **`S`** (proposto) | reso | ⛔ era **no** |

Le tabelle-ponte sono il denominatore comune: `commesse_sorgenti`,
`attivita_fatturabili`, `resi_righe`, `resi_righe_accrediti` hanno tutte
`relrowsecurity = f`, e un arco che si ferma lì eredita **zero** perimetro.

⚠️ **Sul dato di oggi non si riproduce**, e va detto: l'operatore di collaudo
vede tutte e 60 le commesse e tutti e 13 i resi, quindi **zero** archi fuori
perimetro (misurato come `zeroerp_app`, non come owner). È esattamente il caso in
cui i dati di sviluppo **non misurano la gravità**: la domanda è *«può
succedere?»*, e con `multi_emittente` in crescita la risposta è sì il giorno in
cui un operatore è ristretto a un emittente.

E la decorazione del nodo non salva: `vw_documento_lineage_nodi` è in
`LEFT JOIN`, quindi la riga dell'arco resterebbe con `from_codice` a `NULL`. E
`resi.numero` **è nullable**, quindi nemmeno un test su `from_codice IS NULL`
sarebbe un presidio sano (la forma sana è il test 38 di DB-E).

**Decisione di Tid (2026-08-25): si chiude la classe intera in questa passata.**
La vista si ricrea comunque per l'arco `S`; la correzione è **cinque join in
più, tutti su chiave primaria**, e misurata non cambia nemmeno una riga oggi. Un
buco misurato e lasciato aperto è quello che nessuno riapre — e non si sa quando
tornerà l'occasione di riscrivere quella vista.

#### Rilievo 5 — l'arco `S` punta sempre a una nota di credito, e si può dire

Il brief non poneva la domanda; io l'avevo posta male, raccomandando di **non**
asserirlo. La domanda giusta l'ha fatta Tid: *«di solito il reso si lega a una
nota di credito, anche se tecnicamente cambia solo il tipo documento ma la
tabella è la stessa»*. È esatto — `vendite.fatture` è **una** tabella, e fattura
e nota di credito si distinguono per `natura_doc_id`. Ed è proprio per questo
che la natura è stata portata sul nodo il 2026-08-21.

La risposta la dà il codice, in **due punti indipendenti**:

1. `vendite.fn_accredita_riga_reso` — l'**unico** scrittore di
   `resi_righe_accrediti` (lo dice il commento della tabella) — non deriva la
   natura dal segno: la **impone**, `v_natura_nc :=
   config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')`, e solleva
   `E_CONFIG_MANCANTE` se quella natura non esiste a catalogo;
2. `vendite.fn_build_fattura_key` porta `natura_doc_id` **dentro la chiave di
   aggregazione** — rev 2026-08-18, N3: *«è ciò che impedisce a un'attività di
   rettifica di finire nella fattura ordinaria»* — e `trg_fatture_lock_natura_doc`
   (`20260818-28`) la blocca sulla testata.

Non è quindi una coincidenza dei dati: è un'invariante tenuta all'origine e
ri-tenuta a valle. **Va asserita** (test 35). Se un giorno un accredito da reso
finisse su una fattura ordinaria, è un difetto, e questo è il posto dove si vede.

---

## 1. Il caso misurato

Nota di credito **20024** (numero 1, registro NC, natura `NOTA_CREDITO`, stato
`DEFINITIVA`, fase `IN_CORSO`). Gli archi che la toccano oggi:

| arco | da | a | `is_ramo_inverso` |
| --- | --- | --- | --- |
| `G` | Commessa 322 | **NC 20024** | `f` |
| `N` | Fattura 835 (n. 11) | **NC 20024** | `t` |
| `R` | DDT 140 | **Reso 24** (`RESO0000017`, fase `CHIUSO`) | `t` |

**Dal reso 24 non esce nessun arco: è una foglia.** Il pannello «Passaggi» della
nota mostra la fattura rettificata e la commessa; il reso non c'è. E nel drawer
del reso l'unica traccia dell'accredito è `gia_accreditato`, che è **una
quantità**, non un documento.

Distribuzione attuale degli archi (misurata): `A` 64 · `B` 47 · `C` 1 · `D` 2 ·
`E` 28 · `F` 3 · `G` 20 · `H` 19 · `N` 1 · `R` 13. Totale dieci lettere.

---

## 2. La catena, che è esatta per riga

```
fatture_righe (NC 20024)          9993 / 9994 / 9995
  → attivita_fatturabili.fattura_riga_id        13755 / 13756 / 13757
  → .commessa_attivita_id                       35184 / 35185 / 35186
  → resi_righe_accrediti.commessa_attivita_id   457 / 458 / 459
  → .resi_riga_id                               24
  → resi_righe.reso_id → resi                   24 · RESO0000017 · 2026-07-14
```

⭐ `vendite.resi_righe_accrediti` è nata **esattamente** per reggere questo
legame — lo dice il commento della tabella:

> *«il FATTO, con chi/quando/quanto/contro cosa — una storia che altrimenti non
> esisterebbe da nessuna parte, perché la rettifica in commessa dice COSA è stato
> fatto, non A FRONTE DI COSA»*

Il difetto non è nella scrittura: è che **nessuno la legge**.

---

## 3. ⛔ La strada che sembra ovvia e sarebbe sbagliata

`vendite.fn_accredita_riga_reso` crea l'attività di rettifica passando
`p_sorgente_tipo_id => NULL, p_sorgente_uid => NULL` — le **uniche due righe**
di quella chiamata senza un commento che le motivi, in una funzione dove tutto
il resto lo è. Sembra il buco da tappare. **Non lo è.**

`vendite.commesse_attivita.sorgente_tipo_id/uid` non è un campo di provenienza:
è la **chiave di raggruppamento della fatturazione**,
`vendite.fn_build_gruppo_fatturabile_key(sorgente_tipo_id, sorgente_uid, commessa_id)`,
letta da `vw_dash_competenza_attivita`, `vw_dash_competenza_gruppi`,
`vw_lotti_gruppi_serviti` e da tutti i filtri di emissione mirata. Misurato:

| attività | `gruppo_key` |
| --- | --- |
| 538 (normale, da ordine) | `ORDINE_VENDITA:019f5f9c-…` |
| 35184 (rettifica da reso) | `MAN:322` — il gruppo «oneri di commessa» |

Scriverci il reso **sposterebbe la rettifica in un altro gruppo**, cioè in un
altro lotto e in un altro documento. Il legame va **letto**, non **trasportato**
([[feedback_bb_legge_non_trasporta]]).

### 3-bis. ⛔ E c'è una SECONDA strada ovvia, scoperta rileggendo la tabella

`vendite.resi_righe_accrediti` ha una colonna `fattura_riga_rettificata_id`, in
`FOREIGN KEY` su `vendite.fatture_righe`. Punta **direttamente alla riga della
fattura ORIGINALE** che l'accredito rettifica. Un dodicesimo arco *reso →
fattura originale* è a **un join di distanza**, e sembra completare il quadro.

**Non va aggiunto**, e la ragione non è estetica.

Quell'arco sarebbe **forward** (come `S`), quindi renderebbe la **fattura
originale** un discendente in avanti del reso. Nella regola della frontiera —
*l'attivo più a valle* — la fattura originale e la nota di credito finirebbero
allo **stesso livello**, con lo **stesso `pipeline_rank`** (sono entrambe nodi
`FATTURA`): il pareggio si spezzerebbe su `d_uid`, che è **testo**, cioè su un
ordinamento lessicografico fra `'20024'` e `'835'`. La frontiera del reso
diventerebbe un sorteggio.

E non serve: **il triangolo si chiude già**. `reso —S→ NC ←N— fattura originale`.
Chi guarda il reso vede la nota; chi guarda la nota vede la fattura rettificata.
Il terzo lato sarebbe una scorciatoia che costa la frontiera.

---

## 4. Decisione presa (Tid, 2026-08-25): il legame resta MOLTI-A-MOLTI

Poiché tutte le rettifiche di una commessa cadono nel gruppo `MAN:<commessa>`,
**due resi diversi sulla stessa commessa producono UNA sola nota di credito**, e
quella nota può rettificare righe di **fatture diverse** (cosa che il modello
ammette apposta — vedi il predicato per riga di
`fn_numera_fattura_opz_emessa`). Quindi: **un reso → una nota; una nota → più
resi.**

**Si lascia così.** Meno documenti fiscali è un bene, e una nota che accredita
due resi dello stesso cliente è normale amministrazione. La tracciabilità non si
perde: un arco calcolato regge un molti-a-molti senza sforzo, un puntatore
memorizzato no — ed è la ragione in più per cui la forma giusta è l'arco.

⚠️ **Se un giorno si volesse una nota per reso**, la leva è la chiave di
raggruppamento (§3), non l'arco: costerebbe dashboard competenza, emissione
mirata e `fatturazione_lotti_gruppi`. Va nominato qui perché non venga
riscoperto da zero.

⚠️ Effetto collaterale minore, che resta com'è: nel gruppo `MAN:<commessa>` una
**rettifica** e un **addebito manuale** stanno insieme, benché producano due
documenti diversi (si separano più a valle, sulla natura, dentro
`fn_build_fattura_key`).

---

## 5. La consegna

### DB-A — l'arco `S`, e il perimetro RLS di tutta la vista

Due cose nello stesso `CREATE OR REPLACE VIEW`, perché la seconda è la ragione
per cui la prima è scritta così.

#### A.1 — l'undicesimo ramo

> ⛔ **Versione SUPERATA (2026-08-25, mattina).** La prima stesura arrivava a
> `reso_id` passando solo da `resi_righe`, e per questo **usciva dal perimetro
> RLS dei resi** (rilievo 1 del §0.2). Resta qui perché è la forma che verrebbe
> in mente di nuovo: la differenza è un solo join.
>
> ```sql
>    FROM vendite.resi_righe_accrediti a
>    JOIN vendite.resi_righe rr           ON rr.id = a.resi_riga_id
>    JOIN vendite.attivita_fatturabili af ON af.commessa_attivita_id = a.commessa_attivita_id
>    -- ⛔ manca il passaggio da vendite.resi: la policy non morde
> ```

**Versione da scrivere:**

```sql
UNION ALL
-- S — Reso -> Nota di credito (avanzamento del reso; 1:N)
--   ⭐ Si legge da vendite.resi_righe_accrediti, la tabella nata il 2026-08-18
--   per registrare il FATTO dell'accredito «contro cosa». Soft-link calcolato,
--   come G e N: nessuna tabella ponte.
--   ⚠️ Il passaggio da vendite.resi NON e' decorativo: resi ha la RLS
--   (rls_resi_ef_whitelist), resi_righe e resi_righe_accrediti no. Senza questo
--   join l'arco esisterebbe anche per un reso che la whitelist dell'operatore
--   nasconde, con from_codice a NULL — e la decorazione e' in LEFT JOIN, quindi
--   non lo fermerebbe. E' lo stesso perimetro dell'arco R, che passa da resi
--   per la stessa ragione. Vedi la nota generale in testa alla vista.
--   DISTINCT come in G e N: piu' accrediti dello stesso reso confluiscono nella
--   stessa nota (tre, nel caso reale) e devono produrre UN arco.
--   Il WHERE e' lo stesso dell'arco G: prima dell'emissione la riga di fattura
--   non esiste ancora. Misurato il 2026-08-25: 5 accrediti registrati, 3 con la
--   riga di fattura — due resi accreditati e non ancora fatturati non hanno
--   arco, e lo prenderanno all'emissione.
 SELECT DISTINCT
        s_from.id, (r.id)::text,
        s_to.id,   (fr.fattura_id)::text,
        NULL::varchar, 'S'::text
   FROM vendite.resi_righe_accrediti acc
   JOIN vendite.resi_righe rr           ON rr.id = acc.resi_riga_id
   JOIN vendite.resi r                  ON r.id  = rr.reso_id
   JOIN vendite.attivita_fatturabili af ON af.commessa_attivita_id = acc.commessa_attivita_id
   JOIN vendite.fatture_righe fr        ON fr.id = af.fattura_riga_id
   JOIN config.sorgenti s_from ON s_from.codice_interno = 'RESO_VENDITA' AND s_from.attivo IS TRUE
   JOIN config.sorgenti s_to   ON s_to.codice_interno   = 'FATTURA'      AND s_to.attivo   IS TRUE
  WHERE af.fattura_riga_id IS NOT NULL
```

Provato in transazione sul DB vivo: torna **una riga**,
`reso 24 (RESO0000017) → NC 20024`, `is_ramo_inverso = f`,
`to_natura_doc_codice = NOTA_CREDITO`.

* L'alias è `acc`, non `a`: nella `SELECT` esterna della vista `a` è già l'alias
  della CTE `archi`. Gli scope sono distinti e non ci sarebbe errore, ma la
  stessa lettera per due cose diverse nella stessa vista è un invito a sbagliare.
* **Indici**: nessuno nuovo. `acc → rr` è PK, `rr → r` è PK,
  `acc → af` usa `ix_resi_accrediti_commessa_attivita_id` in lettura e
  `uq_attivita_fatturabili_commessa_attivita` (UNIQUE) in scrittura — è un 1:1 —
  `af → fr` è PK.
* ⚠️ `security_invoker=on` va **ri-specificato** nel `CREATE OR REPLACE VIEW`:
  è una reloption invisibile nel corpo, e PostgreSQL la azzera se non la si
  ripete. Il pgTAP 9 se ne accorgerebbe, ma solo dopo.

#### A.2 — ⭐ i quattro archi che erano già fuori perimetro

**Decisione di Tid, 2026-08-25**: `B`, `E`, `F` e `G` si chiudono qui, non in un
cantiere futuro (rilievo 1 del §0.2). Quattro join in più, tutti su chiave
primaria, **zero righe cambiate sul dato di oggi** (misurato).

```sql
-- B / E / F — sorgente -> Commessa
--   ⚠️ commesse_sorgenti NON ha RLS, e nessuno dei due estremi passava da una
--   tabella che ce l'ha: la sorgente (preventivi/ordini/contratti) e la
--   commessa hanno tutte relrowsecurity = t, e l'arco le saltava entrambe.
--   Ora l'arco esiste solo se il chiamante vede sia il padre sia il figlio.
 SELECT s_from.id, (p.uid)::text,
        s_to.id,   (cm.id)::text,
        cs.ruolo_link, 'B'::text
   FROM vendite.commesse_sorgenti cs
   JOIN vendite.preventivi p ON p.uid::text = cs.sorgente_uid          -- ⬅ nuovo
   JOIN vendite.commesse   cm ON cm.id      = cs.commessa_id           -- ⬅ nuovo
   JOIN config.sorgenti s_from ON s_from.id = cs.sorgente_tipo_id AND s_from.codice_interno = 'PREVENTIVO'
   JOIN config.sorgenti s_to   ON s_to.codice_interno = 'COMMESSA' AND s_to.attivo IS TRUE
-- E: identico con vendite.ordini o ON o.id::text = cs.sorgente_uid  e 'ORDINE_VENDITA'
-- F: identico con vendite.contratti c ON c.id::text = cs.sorgente_uid e 'CONTRATTO'

-- G — Commessa -> Fattura
 SELECT DISTINCT
        s_from.id, (cm.id)::text,
        s_to.id,   (f.id)::text,
        NULL::varchar, 'G'::text
   FROM vendite.attivita_fatturabili af
   JOIN vendite.commesse cm ON cm.id = af.commessa_id                  -- ⬅ nuovo
   JOIN vendite.fatture_righe fr ON fr.id = af.fattura_riga_id
   JOIN vendite.fatture f ON f.id = fr.fattura_id
   …
```

⛔ **Attenzione alla chiave, che non è la stessa per i tre rami.** La colonna
`commesse_sorgenti.sorgente_uid` è **testo polimorfo** e segue la convenzione
`key_selector`: per preventivo e offerta è lo `uid`, per gli altri è `id::text`
([[reference_sorgente_polimorfa_key_selector]]). Il join va scritto con la
chiave **nativa** del ramo — `p.uid::text` per B, `o.id::text` per E, `c.id::text`
per F — non con una forma copiata da un ramo all'altro. È il difetto che il
cantiere sulla sorgente polimorfa ha già pagato una volta.

⚠️ **Da verificare prima di scrivere, non dopo**: che i tre join non facciano
sparire archi sul DB di oggi. La misura è già fatta (0 archi fuori perimetro come
`zeroerp_app`), ma va **rifatta a valle** — è la stessa istruzione che rende
verde il test 38, e un ramo scritto con la chiave sbagliata lo direbbe subito
azzerando quel gruppo di archi. Attesa: `B` 47, `E` 28, `F` 3, `G` 20, invariati.

⭐ Nel `COMMENT` della vista va scritta **la regola**, non i cinque casi: *ogni
ramo passa dalle tabelle-testata che portano la RLS; le tabelle-ponte
(`commesse_sorgenti`, `attivita_fatturabili`, `resi_righe`,
`resi_righe_accrediti`) hanno `relrowsecurity = f` e non danno perimetro*. È la
frase che impedisce al dodicesimo arco di ripetere l'errore.

### DB-B — ⭐ `S` **NON** è un ramo di ritorno

`is_ramo_inverso` resta `arco = ANY (ARRAY['R','N'])`: **non si tocca**.

⚠️ La decisione è consapevole e va scritta nel `COMMENT`. «Inverso» non vuol dire
«a valle di un ritorno»: vuol dire *ramo di ritorno*, cioè un verso che il grafo
forward non deve percorrere. `R` è il ritorno della merce, `N` è il ritorno del
valore. `S` invece è l'**avanzamento naturale del reso** — la merce è tornata,
adesso si accredita — esattamente come `H` è l'avanzamento dell'ordine.

⭐ **La conseguenza voluta: il reso smette di essere una foglia e prende la nota
di credito come FRONTIERA.** È l'informazione che oggi manca del tutto: *«questo
reso è già stato accreditato, con quel documento»*. Marcarlo inverso lo
lascerebbe frontiera di sé stesso, cioè al punto di partenza.

✅ **Misurato**, non dedotto: dopo la modifica il reso 24 passa da
`frontiera = sé stesso (RESO0000017)` a `frontiera = NC 20024`, e
`is_transitato` da `f` a `t`. Vedi §5-bis per il diff completo.

### DB-C — due prose diventate false, da correggere

Il `COMMENT` di `vendite.vw_documento_lineage` afferma:

> *«NON esiste una `frontiera_natura_doc_codice`, di proposito: l'arco N è un
> ramo di ritorno ed è escluso dal grafo forward, quindi una nota di credito non
> può mai essere la frontiera di nessuno e quella colonna varrebbe sempre NULL.»*

⛔ **È già falso oggi**, e non per colpa di questo cantiere: l'arco `G`
(commessa → fattura) **non** è un ramo di ritorno, e il backend lo aveva già
misurato il 2026-08-21 — *«la frontiera PUÒ essere una nota di credito: è già la
frontiera dell'ordine 240 e della commessa 322»*, tant'è che
`get_lineage_nodo` la legge davvero (`nfr.natura_doc_codice AS
frontiera_natura_doc_codice`). Con l'arco `S` diventa falso una seconda volta:
la NC diventa la frontiera **anche del reso**.

Da correggere:

1. il `COMMENT` di `vw_documento_lineage`;
2. lo stesso testo ricopiato nel pgTAP (`test-documento-lineage-v1.sql`, sopra
   il test 7 delle colonne) e la prosa del test 18 («un reso è però frontiera di
   sé stesso come foglia» → vale solo per un reso **non ancora accreditato**).

Nessuna delle due è un'asserzione: sono commenti. Ed è proprio per questo che
vanno corretti adesso — un commento sbagliato non fallisce mai.

> ⚠️ **Correzione al piano (rilievo 2 del §0.2).** Il brief diceva «nello stesso
> changeSet» e non diceva **come**. Il come conta: la correzione si fa con un
> `COMMENT ON VIEW` **da solo**, non ricreando `vw_documento_lineage`.
>
> Un `CREATE OR REPLACE VIEW` su quella vista per cambiarle il commento
> significherebbe riscriverne il corpo — 150 righe di `WITH RECURSIVE` copiate a
> mano — e **ri-specificare `security_invoker=on`**, che se dimenticato si
> azzera in silenzio. Sarebbe un rischio di regressione preso per una stringa.
> Il progetto ha già il precedente giusto: `20260819-23` e `20260819-24` sono
> changeSet `comment-…` che fanno solo quello.
>
> Conseguenza sulla forma: **due file, non uno** (§9, L1 e L2). Il secondo
> nomina nel proprio titolo la vista che tocca — ed è il punto, visto che questo
> cantiere nasce da un commento che nessuno ha riletto.

### DB-D — ⚠️ la whitelist del pgTAP

`db/pgtap/vendite/test-documento-lineage-v1.sql`, test 13:

```sql
WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R','N')
```

**Va aggiunto `'S'`**, o il test va rosso al primo arco emesso. È il caso da
manuale di [[feedback_whitelist_dal_percorso_reale]]: una whitelist si verifica
dal percorso che la attraversa, non dal nome del test.

Va corretta anche l'**etichetta** del test (`'archi: arco sempre in A..H,R,N'` →
`'…A..H,R,N,S'`) e la voce 13 dell'indice in testa al file: un'etichetta che
elenca dieci lettere sopra un'asserzione che ne ammette undici è la stessa specie
di bugia del §DB-C.

### DB-E — pgTAP nuovi su `test-documento-lineage-v1.sql`

Da aggiungere in coda, aggiornando l'indice in testa e portando `plan(32)` a
**`plan(38)`**.

> ⚠️ **Correzione al piano (rilievo 3 del §0.2).** Il brief ne proponeva tre, e
> il terzo era *«il reso 24 ha la NC 20024 come frontiera»*, protetto da `skip`.
> Quel test misura **il dato di oggi**, non la regola: il giorno in cui il reso
> 24 sparisce dal DB di sviluppo il presidio si spegne da solo, in verde. Le due
> invarianti che lo sostituiscono (36 e 37) sono **seed-agnostiche** — su un DB
> senza archi `S` valgono 0 senza saltare — e dicono la stessa cosa in forma di
> regola.

**33 — l'arco `S` parte sempre da un nodo `RESO_VENDITA`**

```sql
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'S'
        AND from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, '33) archi: l''arco S parte sempre da un nodo RESO_VENDITA');
```

**34 — l'arco `S` arriva sempre a un nodo `FATTURA`**

```sql
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'S'
        AND to_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')),
    0, '34) archi: l''arco S arriva sempre a un nodo FATTURA');
```

**35 — ⭐ e quella fattura è sempre una NOTA DI CREDITO** *(decisione di Tid, rilievo 5)*

```sql
-- ⭐ `vendite.fatture` e' UNA tabella: fattura e nota di credito si distinguono
--    solo per natura_doc_id, ed e' per questo che il tipo del nodo (test 34)
--    non basta a dire che cosa c'e' in fondo all'arco.
--    L'invariante e' tenuta in DUE punti indipendenti, e nessuno dei due deriva
--    la natura dal segno dell'importo:
--      · vendite.fn_accredita_riga_reso — l'UNICO scrittore di
--        resi_righe_accrediti — la impone:
--        v_natura_nc := config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO'),
--        con E_CONFIG_MANCANTE se quella natura non e' a catalogo;
--      · vendite.fn_build_fattura_key la porta DENTRO la chiave di aggregazione
--        (rev 2026-08-18, N3: «e' cio' che impedisce a un'attivita' di rettifica
--        di finire nella fattura ordinaria»), e trg_fatture_lock_natura_doc la
--        blocca sulla testata.
--    Se questo test diventa rosso, uno dei due si e' rotto: e' un difetto, non
--    un caso legittimo.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'S'
        AND to_natura_doc_codice IS DISTINCT FROM 'NOTA_CREDITO'),
    0, '35) archi: l''arco S arriva sempre a una NOTA DI CREDITO, non a una fattura qualsiasi');
```

⚠️ `IS DISTINCT FROM` e non `<>`: `natura_doc_id` su `vendite.fatture` è
**nullable** e il nodo la espone in `LEFT JOIN`. Con `<>` una natura a `NULL`
darebbe `NULL`, la riga non sarebbe contata e il test **passerebbe proprio sul
caso peggiore** — una nota senza natura.

**36 — un reso accreditato ed emesso non è più una foglia** *(presidio di DB-B, lato `disc`)*

```sql
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage s
      WHERE EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_archi a
                     WHERE a.arco = 'S' AND a.from_tipo_id = s.tipo_id AND a.from_uid = s.uid)
        AND NOT s.is_transitato),
    0, '36) summary: un reso con arco S non e'' piu'' una foglia (is_transitato)');
```

**37 — la frontiera del reso è la nota, non sé stesso** *(presidio di DB-B, lato `frontiera`)*

```sql
SELECT is(
    (SELECT count(*)::int
       FROM vendite.vw_documento_lineage s
       JOIN vendite.vw_documento_lineage_archi a
         ON a.arco = 'S' AND a.from_tipo_id = s.tipo_id AND a.from_uid = s.uid
      WHERE a.to_fase <> 'CHIUSO'
        AND NOT COALESCE(a.to_is_abortito, false)
        AND s.frontiera_tipo_id = s.tipo_id
        AND s.frontiera_uid     = s.uid),
    0, '37) summary: la frontiera di un reso accreditato e'' la nota, non se stesso');
```

⭐ L'invariante è **incondizionata rispetto allo stato del reso**, e va detto
perché non sembri una svista: nel `row_number()` della frontiera il nodo stesso
sta a `lvl 0` e la nota a `lvl 1`; a parità di rango (nota attiva → rango 0) il
tie-break è `lvl DESC`, quindi la nota vince **sempre**, che il reso sia chiuso o
no. Il filtro sulla fase serve solo a escludere le note chiuse o abortite, per le
quali il reso resta legittimamente frontiera di sé.

**38 — ⭐⭐ NESSUN arco esce dal perimetro RLS** *(presidio di DB-A.2, generale)*

```sql
-- ⭐⭐ Il presidio della decisione del 2026-08-25: ogni ramo della vista passa
--    dalle tabelle-testata che portano la RLS. Le tabelle-ponte
--    (commesse_sorgenti, attivita_fatturabili, resi_righe, resi_righe_accrediti)
--    hanno relrowsecurity = f e non danno perimetro: un ramo che si ferma li'
--    produce un arco verso un documento che il chiamante NON puo' vedere, con
--    la decorazione a NULL perche' vw_documento_lineage_nodi e' in LEFT JOIN.
--    Prima del 2026-08-25 lo facevano B, E, F e G — quattro rami su dieci.
-- ⚠️ Questo test vale SOLO perche' la suite gira come zeroerp_app con la RLS
--    attiva (dal 2026-08-07). Con PGTAP_RUNNER=owner sarebbe verde per
--    costruzione e non presidierebbe niente. Chi lo sposta lo spegne.
-- ⚠️ E non e' una riproduzione: sul DB di sviluppo del 2026-08-25 la whitelist
--    dell'operatore copre tutte e 60 le commesse e tutti e 13 i resi, quindi
--    entrambe le forme sono verdi. E' un presidio per il giorno in cui non sara'
--    piu' cosi'.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.vw_documento_lineage_archi a
      WHERE NOT EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_nodi n
                         WHERE n.tipo_id = a.from_tipo_id AND n.uid = a.from_uid)
         OR NOT EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_nodi n
                         WHERE n.tipo_id = a.to_tipo_id   AND n.uid = a.to_uid)),
    0, '38) archi: nessun arco esce dal perimetro RLS (entrambi gli estremi sono nodi visibili)');
```

⭐ **È anche il collaudo dei tre join di B/E/F.** La chiave di
`commesse_sorgenti.sorgente_uid` è polimorfa (uuid per il preventivo,
`id::text` per ordine e contratto): un ramo scritto con la chiave sbagliata non
darebbe errore, **azzererebbe quel gruppo di archi**, e questo test lo direbbe
insieme al conteggio per lettera di L4.

⭐ **La decisione DB-B è già presidiata anche da un test che c'è.** Il **29**
asserisce `is_ramo_inverso <> (arco IN ('R','N'))` = 0, cioè *«è vero esattamente
per R e N»*: con `S` fuori dall'array resta **verde** (misurato), e diventerebbe
**rosso** il giorno in cui qualcuno aggiungesse `S` ai rami di ritorno «per
simmetria». Non serve un test nuovo — serve **non toccare** né l'array della
vista né quello del test 29.

⚠️ Invarianti esistenti che **restano vere** — non più «verificato leggendo le
asserzioni», ma **rimisurato dopo la modifica**, tutte a 0:

* **13** (whitelist) — **solo** dopo la correzione DB-D; senza, va rosso;
* **14** (`R` punta a un `RESO_VENDITA`), **17** (frontiera sempre valorizzata);
* **18** (*«RESO mai frontiera di un nodo non-reso»*): `S` porta **verso** una
  fattura, mai verso un reso, e nessun arco forward porta **a** un reso;
* **19** e **20** (le due invarianti fase/frontiera): reggono in tutte e quattro
  le combinazioni reso-chiuso/aperto × nota-chiusa/aperta;
* **27**, **28**, **29**, **31** (arco N e natura): l'arco `S` non li tocca;
* **30** (*«una FATTURA è sempre frontiera di sé stessa»*): `S` è un arco
  **entrante** nella fattura, e nel grafo forward una fattura continua a non
  avere archi uscenti.

### DB-F — ⭐ `vw_resi_lista` diventa la sesta sorella

**Decisione di Tid, 2026-08-25: dentro questo cantiere.** Senza, «questo reso è
già stato accreditato» resta un drawer da aprire una riga alla volta.

⭐ **E chiude, per la strada standard, il primo residuo del §7.** Sulle cinque
sorelle la colonna `transito` proietta `frontiera_codice`: sul reso quella
frontiera **è la nota di credito**, quindi la colonna mostra **il numero della
nota** senza nessuna consegna su misura.

#### F.1 — la vista

`vendite.vw_resi_lista` prende le colonne di genealogia nella stessa forma di
`vw_ddt_lista` (`20260715-05`): `pratica_id`, `pratica_numero`,
`frontiera_tipo_id`, `frontiera_codice`, `frontiera_stato_codice_interno`,
`frontiera_fase`, `n_discendenti_attivi`, `is_transitato`, via
`LEFT JOIN vendite.vw_documento_lineage lin` su `(tipo_id = RESO_VENDITA, uid = r.id::text)`.

⚠️ **Va aggiunta anche `fase`**, che oggi non c'è: `vw_resi_lista` espone
`stato_codice_interno` e `stato_descrizione` ma non la fase normalizzata, e il
seed della colonna `fase` la cerca con quel nome (`campo_sorgente = 'fase'`).
Sorgente: `sr.fase` da `config.stati_doc_reso`, già in join.

⚠️ `security_invoker=on` da ri-specificare, come sempre.

#### F.2 — il seed, che è **solo CSV**

Nessun changeSet nuovo: i mirror esistono e sono `runOnChange`
(`20260806-15` per `lista_colonna`, `20260507-09` per `lista_preset_colonna`).
Si **appende**, e il loader ripesca ([[feedback_messaggi_errore_no_new_loader]],
[[feedback_seed_80_data_csv]]).

| file | righe da appendere | id |
| --- | --- | --- |
| `80_data/sql/ui/lista_colonna.csv` | 3 (`pratica`, `fase`, `transito`) su `lista_id = 9` | da **549** (max attuale 548) |
| `80_data/sql/ui/lista_preset_colonna.csv` | 3, sul preset `resi_default` (**id 9**, `is_default = t`, già esistente) | ⛔ **nessun id**: vedi sotto |

Si copiano le righe `197/198/199` (lista 8, i DDT) cambiando `lista_id` e `id`:
stessi `campo_sorgente` (`pratica_numero` / `fase` / `frontiera_codice`), stesso
gruppo `Genealogia`, stessi `ordine_default` 200/210/220, stesse chiavi i18n
`vendite.lineage.col_pratica|col_fase|col_transito` — **che esistono già**.

⚠️ `sensibile = f`. Non è un dettaglio di stile: `sensibile = t` senza un grant
corrispondente rende la colonna **invisibile a tutti**
([[feedback_ui_sensibile_e_un_cancello]]).

⛔ **Correzione al piano, trovata scrivendo.** Questo brief diceva
«`lista_preset_colonna.csv`, id da 49 (max attuale 48)». È **falso**: quel CSV
**non ha una colonna `id`**. L'intestazione è
`preset_id,colonna_id,ordine,visibile,fissata` e la tabella ha una **PK composta
`(preset_id, colonna_id)`**. Il «48» che avevo letto era il `preset_id` della
lista fatture. Le righe giuste sono `9,549,205,t,f` / `9,550,215,t,f` /
`9,551,225,t,f`, cioè preset 9 + le tre colonne nuove, agli ordini 205/215/225
come sul preset DDT. ⚠️ La tabella ha anche una colonna `larghezza` che il CSV
**non** riporta: è nullable, e il loader la lascia a NULL come su tutte le altre
righe.

#### F.3 — ⛔ la trappola: tre test che NON diventano rossi

`db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` ancora i test **21**, **22**
e **25** a `lista_id IN (4,5,6,7,8)` e alla costante **15**.

Aggiungendo la lista 9 quei conteggi **restano 15 e i test restano verdi** — il
filtro esclude la nuova lista. **Non è un rosso da sistemare: è copertura che
sparisce in silenzio**, la forma peggiore, perché nessuno la va a cercare. La
sesta sorella nascerebbe senza presidio, e il file continuerebbe a chiamarsi
«colonne lineage sulle liste».

Da fare nello stesso passaggio: `(4,5,6,7,8,9)` e **18** in tutti e tre, più i
4 test di forma per la nuova vista (3 `has_column` + 1 `security_invoker`) →
`plan(26)` diventa **`plan(30)`**, con l'indice in testa aggiornato e il titolo
del file da «5 liste» a «6 liste».

#### F.4 — ⛔ «niente frontend, niente backend»: ERA FALSO (corretto 2026-08-26)

> **Testo originale, tenuto perché è la forma del difetto e non il difetto:**
>
> *«`ResiSearchTable.vue` è già `<ListaConfigurabile codice="vendite.resi">`
> (lista 9, seed DB). Le colonne arrivano dal seed e dal preset: **zero righe di
> FE, zero righe di BE**. È la stessa catena che ha funzionato per le cinque
> sorelle il 2026-07-15.»*

**La premessa è vera, la conclusione no**, e la prova che era sbagliata sta
proprio nelle cinque sorelle citate a sostegno: **anche loro** hanno righe di BE
e di FE, scritte il 2026-07-15 insieme al seed. «La catena ha funzionato» voleva
dire *«ha funzionato quando si sono scritti anche quei due pezzi»*.

⭐ **Il seed porta la COLONNA, non la CELLA.** `<ListaConfigurabile>` monta le
`Column` dalla configurazione e, senza uno slot del chiamante, rende il **valore
grezzo**. È la stessa specie di [[feedback_bb_legge_non_trasporta]]: il building
block unifica la **lettura** della configurazione, non il **rendering** di ogni
cella — e i punti che rendono si **cercano**, uno per lista.

**I tre buchi misurati, e cosa si vedeva a video senza:**

| # | Dove | Senza | Perché il difetto è silenzioso |
| --- | --- | --- | --- |
| 1 | `ResiRepository.list_resi` — manca `frontiera_tipo_codice` | la colonna «Transito» mostra **«—»**, cioè *«non transitato»*, **proprio sul reso accreditato** | la vista espone `frontiera_tipo_id` (il grafo parla per id), il FE parla per `codice_interno`; `LineageFrontieraChip` ha il gate su `isTransitato && tipoCodice` e senza il codice ricade sul ramo «—» |
| 2 | `ResiSearchTable.vue` — mancano i **tre slot** `#cell-pratica` / `#cell-fase` / `#cell-transito` | «Pratica» come testo non cliccabile, «Fase» come `CHIUSO` grezzo invece del Tag, «Transito» come **`1`** nudo invece del chip | il BB rende il valore grezzo: nessun errore, nessun log, solo tre colonne che non fanno il loro mestiere |
| 3 | `test_lineage_liste_be.py` — ancorato a **cinque** liste | i test restano **verdi** e smettono di coprire la sesta | ⛔ **è la trappola del §5 DB-F.3, sul lato Python**: la stessa specie dei pgTAP ancorati a `lista_id IN (4..8)`, e non l'avevo cercata qui |

⭐ **Il buco 1 era già stato sfiorato e non riconosciuto.** La whitelist `ORDER BY`
di `_ORDER_COLS_RESI` era stata estesa a `pratica_numero`/`fase` — trovata dal
presidio del seed, non a occhio. Chi l'ha scritta era **dentro il file giusto** e
si è fermato alla colonna che il presidio nominava: un presidio copre ciò che
sa, e la decodifica del tipo frontiera non la sapeva nessuno.

**Consegna del 2026-08-26** (tre file, `20260825-19..21` invariati):

1. `backend/apps/vendite/db/resi_repository.py` — `SELECT v.*, s.codice_interno
   AS frontiera_tipo_codice` + `LEFT JOIN config.sorgenti`, identico alle cinque
   sorelle;
2. `frontend/src/vendite/resi/components/ResiSearchTable.vue` — i tre slot con i
   BB `LineagePraticaCell` / `LineageFaseTag` / `LineageFrontieraChip`;
3. `backend/apps/vendite/tests/services/test_lineage_liste_be.py` — esteso a
   **sei** liste **e** con un presidio nuovo per il buco 1
   (`test_ogni_lista_decodifica_il_tipo_della_frontiera`, che legge il sorgente
   dei sei repository). ⭐ Verificato **al contrario**: rimessa la `SELECT v.*`
   nuda, il test diventa rosso.

**Misure.** 3+9 test verdi (lineage liste + presidio seed liste), `eslint` e
`vite build` puliti, `check_i18n_keys.py` e `check-liste-configurabili.mjs`
verdi. Query di lista provata sul DB vivo in contesto operatore: il reso 24 esce
con `frontiera_tipo_codice = FATTURA`, `frontiera_codice = 1`,
`is_transitato = t`, `n_discendenti_attivi = 1`.

🔴 **E la misura ha scoperto il §7-bis**: quel `FATTURA` è la nota di credito, e
il chip la etichetta «Fattura».

---

## 5-bis. ⭐ Effetti collaterali: due righe su 425, e vanno dichiarate

Il brief non li nominava. Misurati con snapshot prima/dopo su
`vendite.vw_documento_lineage` (425 righe, invariate come numero):

| nodo | colonna | prima | dopo |
| --- | --- | --- | --- |
| **Reso 24** | `frontiera_uid` | `24` (sé stesso) | **`20024`** (la NC) |
| | `n_discendenti_diretti` | 0 | **1** |
| | `n_discendenti_attivi` | 0 | **1** |
| | `is_transitato` | `f` | **`t`** |
| **NC 20024** | `n_sorgenti` | 1 | **2** |
| | `root_uid` / `root_codice` | commessa 322 | **invariato** |
| | `frontiera_*`, `n_discendenti_*`, `is_transitato` | — | **invariati** |

Tutto ciò che cambia è **voluto** ed è il cantiere. Ma tre cose vanno dette.

**(a) ⚠️ Il `root` della nota resta la commessa per un pelo, e non per una
regola.** Nella CTE `inc` il `root` si sceglie con
`ORDER BY (ruolo = 'ROOT') DESC NULLS LAST, from_tipo_id, from_uid`. Gli archi
`G` e `S` hanno entrambi `ruolo` a `NULL`, quindi il pareggio si spezza su
`from_tipo_id`: `COMMESSA` è **13**, `RESO_VENDITA` è **15**, e 13 vince. Se un
giorno i `config.sorgenti` fossero riseminati con altri id, il `root` di ogni
nota di credito passerebbe dalla commessa al reso — **senza errori e senza log**.

Non è un difetto introdotto qui (la fragilità è della `inc` dal 2026-07-14), ma
**questo cantiere è il primo a esporla**: finora la nota aveva una sola sorgente
forward e il tie-break non entrava mai in gioco. Va a §7, non alla consegna.

**(b) ⭐ Dove il beneficio NON si vedeva — ed è il motivo della decisione 3.**
`vw_resi_lista` **non espone colonne di lineage**: il passaggio
`is_transitato: f → t` del reso non arriverebbe **nella lista dei resi**, ma solo
nel pannello «Passaggi» e nella `DocumentoCollegamentiBar` — cioè un drawer da
aprire una riga alla volta. Sei liste sorelle su sette ce l'hanno
(`20260715-01..05`, `20260824-15`), i resi no.

⭐ **Tid ha deciso il 2026-08-25 di portarlo dentro questo cantiere** (§5 DB-F).
Ed è la scelta che chiude anche il primo residuo del §7 senza scrivere niente su
misura: sulle sorelle la colonna `transito` proietta `frontiera_codice`, e la
frontiera di un reso accreditato **è la nota di credito** — quindi in lista
compare **il numero della nota**, che era esattamente la richiesta.

**(c) `vw_fatture_lista` non espone `n_sorgenti`**, quindi il `1 → 2` della nota
si vede solo nell'endpoint «passaggi» (che legge `l.n_sorgenti, l.root_codice`).
Il commento di `vw_fatture_lista` — *«n_discendenti_attivi e is_transitato sono
zero per costruzione perché la fattura è terminale»* — **resta vero**: l'arco `S`
è entrante.

---

## 6. Cosa NON serve fare

* **Nessuna tabella ponte.** `S` è un soft-link calcolato, come `G` e `N`.
* **Nessun dodicesimo arco** *reso → fattura originale*, benché
  `resi_righe_accrediti.fattura_riga_rettificata_id` lo renda banale: §3-bis.
* **Nessuna modifica al CORPO di `fn_documento_lineage` né di
  `vw_documento_lineage`.** Dal 2026-08-20 le lettere dei rami di ritorno vivono
  in **un posto solo** (`is_ramo_inverso`, calcolato nella vista archi); il
  traversal e la summary la leggono. Era il difetto che l'arco N aveva già pagato
  — la lettera scritta in tre posti e il terzo dimenticato.
  ⚠️ Il **commento** di `vw_documento_lineage` invece cambia (DB-C): è l'unica
  cosa che si tocca lì, e si tocca con un `COMMENT ON VIEW`, non ricreando la
  vista.
* **Nessun indice nuovo** (§5 DB-A, verificato sui vincoli).
* **Nessuna modifica al frontend *per il PANNELLO*** — e solo per quello. Il
  pannello «Passaggi» non conosce le lettere: etichetta le tappe per **tipo** e
  **natura** (`lineageDocumentoLabel`), e le chiavi i18n
  `vendite.lineage.natura_nota_credito` e `vendite.lineage.tipo_reso_vendita`
  esistono già. La tappa `reso → nota di credito` compare da sola.
  ⛔ **Per la LISTA invece no**, e questa riga diceva il contrario: la lista resi
  è sì già `<ListaConfigurabile>` e le colonne arrivano davvero dal seed, ma il
  BB rende il **valore grezzo** senza gli slot del chiamante. Vedi §5 DB-F.4
  corretto.
* **Nessuna modifica al backend *per gli ARCHI e per il PANNELLO***.
  `list_lineage_passaggi` proietta l'arco così com'è e nessun consumatore BE
  conosce le lettere — questo resta vero.
  ⛔ **Ma la lista resi NON passa dallo stesso endpoint generico delle cinque
  sorelle**: ogni dominio ha il **suo** repository e la **sua** `SELECT`, e
  quella dei resi non decodificava `frontiera_tipo_id`. La frase originale
  scambiava «stesso pattern» per «stesso codice». Vedi §5 DB-F.4 corretto.
* **Nessun changeSet per il seed** di DB-F: i mirror CSV sono `runOnChange` e
  ripescano il file. Si appende, non si scrive un loader (§5 DB-F.2).

⚠️ Da **verificare in-app** dopo l'applicazione. Il brief diceva «che il chip
compaia»; la lettura del codice permette di essere più precisi, e un'attesa
precisa è ciò che rende utile una verifica:

| dove | atteso | perché |
| --- | --- | --- |
| drawer del **reso 24** | un chip **«Nota di credito»** con `→` | `chipsDaArchi(avanti, 'to')`, `is_ramo_inverso = f` → freccia avanti, non `↩` |
| drawer della **NC 20024** | un chip **«Reso»** con `←` | `chipsDaArchi(indietro, 'from')` |
| drawer del **DDT 140** | **nessun cambiamento** | `chipsDaArchi` filtra `livello === 1`, e `S` è al livello 2 |
| dialog «Passaggi» del DDT 140 | la timeline arriva **fino alla nota** | il traversal non filtra: misurato, `R` (lvl 1) → `S` (lvl 2) |
| **lista resi**, colonna «Transito» | un **chip** col numero della nota sulla riga del reso 24 | `transito` proietta `frontiera_codice`, e la frontiera del reso accreditato è la NC (§5 DB-F) |
| **lista resi**, colonne «Pratica» e «Fase» | valorizzate come sulle sorelle — «Fase» è un **Tag colorato** | stesso seed, stesso `campo_sorgente`, stessi tre slot (§5 DB-F.4 corretto) |

⚠️ **Due cose si vedranno e NON sono difetti di questa verifica**, entrambe già
in §7 / §7-bis — vale la pena saperlo prima, per non fermare il collaudo:

| Cosa si vede sulla riga del reso 24 | Perché | Dove |
| --- | --- | --- |
| il numero è **`1`**, non `NC0000001` | il `codice` del nodo fattura è `fatture.numero`, e il registro NC è al numero 1 | §7, terzo punto |
| il chip dice **«Fattura»**, non «Nota di credito» | la natura della frontiera non esce dalla summary (`frontiera_uid` non è in lista) | 🔴 §7-bis |

⛔ **Se invece «Transito» mostra «—»**, quello è un difetto: manca
`frontiera_tipo_codice` dal backend (§5 DB-F.4, buco 1).

---

## 7. Cosa resta aperto, e non è di questo cantiere

> ⭐ **Due voci sono uscite di qui il 2026-08-25**, promosse alla consegna da una
> decisione di Tid: il **perimetro RLS di B/E/F/G** (§5 DB-A.2) e le **colonne
> lineage in `vw_resi_lista`** (§5 DB-F), che porta in lista anche il **numero
> della nota** per la via standard.

> ⭐ **Le prime due voci sono uscite di qui il 2026-08-26** (voce **L7.5**):
> hanno un cantiere loro, con le misure rifatte —
> [brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md).
> ⚠️ E **la seconda è cresciuta misurandola**: le due righe `DDT_VENDITA` sono
> `ROOT`, sono l'**unica** sorgente delle loro commesse, i due DDT esistono e una
> riga è del **2026-08-17**. «Residuo» è l'ipotesi meno probabile, e intanto due
> commesse vive dichiarano nel grafo di **non avere origine**.

* ➡️ **Il tie-break del `root` nella CTE `inc` dipende dagli id dei
  `config.sorgenti`** (§5-bis-a) → §1 del brief residui.
* ➡️ **`commesse_sorgenti` ha 2 righe `DDT_VENDITA` che non producono nessun
  arco** → §2 del brief residui.
* ⚠️ **La colonna «Transito» mostra il numero nudo della fattura** (`1`), perché
  `vw_documento_lineage_nodi` espone `fatture.numero` come `codice` del nodo,
  mentre per gli altri sei tipi il `codice` è già parlante (`DDT0000031`,
  `ORD0000227`). Misurato all'apply del 2026-08-25 sul reso 24. Riguarda **ogni**
  lista che proietta `frontiera_codice` verso una fattura, non solo i resi: la
  sede della cura è il nodo, non questa vista.
* Il raggruppamento `MAN:<commessa>` e l'ipotesi «una nota per reso» (§4).
* Il fatto che `fn_accredita_riga_reso` passi `sorgente => NULL` **senza dirlo**:
  il valore è giusto (§3), il silenzio no. Un commento di due righe lì eviterebbe
  che il prossimo lo legga come una dimenticanza — e questo giro è la prova che
  succede.

---

## 7-bis. 🔴 Al team DB — la colonna «Transito» chiama «Fattura» la nota di credito

> **Trovato il 2026-08-26 misurando la consegna in-app** (§5 DB-F.4). Non è un
> difetto introdotto da questo cantiere: è un difetto **preesistente** che questo
> cantiere rende **strutturale**, ed è la ragione per cui va qui e non in §7.

### 7-bis.1 Il fatto

Sulla riga del reso 24 la colonna «Transito» rende, oggi, il chip

> `→ [Fattura] 1 · IN_CORSO`

dove **`1` è la nota di credito 20024**. Il pgTAP **35** asserisce che l'arco `S`
arriva **sempre** a una `NOTA_CREDITO`: quindi su questa lista l'etichetta
sbagliata non è un caso limite, è **il caso**.

⛔ E la colonna esiste per rispondere a *«questo reso è già stato accreditato, e
con quale documento»* (§5-bis-b). Chiamare «Fattura» l'accredito è dire la cosa
sbagliata **proprio nel punto** per cui la colonna è stata seminata.

### 7-bis.2 Perché il frontend non può rimediare da solo

La regola esiste già ed è una sola: `lineageDocumentoLabel(t, te, tipo, natura)`
— *la natura vince sul tipo quando c'è*. È stata scritta il 2026-08-21 per
esattamente questo motivo (`vendite.fatture` è **una** tabella; fattura e nota di
credito si distinguono solo per `natura_doc_id`) ed è già usata dai chip di
`DocumentoCollegamentiBar` e dalle tappe della dialog.

🔴 **Alla cella della lista quel dato non arriva, e non può arrivare.** Il
pannello lo ricava in `VenditeRepository.get_lineage_nodo`:

```sql
LEFT JOIN vendite.vw_documento_lineage_nodi nfr
       ON nfr.tipo_id = l.frontiera_tipo_id
      AND nfr.uid     = l.frontiera_uid      -- ⬅ la chiave
```

Il join ha bisogno di **`frontiera_uid`**. `vw_documento_lineage` ce l'ha; le
**sei** `vw_*_lista` **no** — proiettano `frontiera_tipo_id`, `frontiera_codice`,
`frontiera_stato_codice_interno`, `frontiera_fase`, e la chiave del nodo si ferma
lì. Verificato eseguendo il join dalla lista: `ERRORE: la colonna
v.frontiera_uid non esiste`.

⛔ **Quindi non c'è un rimedio BE onesto**, e va detto perché la tentazione c'è:
si potrebbe joinare `vendite.fatture` + `config.nature_doc_fiscale` filtrando su
`frontiera_tipo_id = FATTURA`. Sarebbe **il tipo cablato nel backend** — cioè la
cosa che il grafo esiste per non fare — moltiplicata per sei repository, e
divergerebbe dal pannello alla prima modifica di uno dei due.
[[feedback_no_quick_fix_soluzione_assoluta]].

### 7-bis.3 La misura

Contati i nodi la cui frontiera è una nota di credito, in contesto operatore, il
2026-08-26:

| nodo | quanti | dove si vede |
| --- | ---: | --- |
| `ORDINE_VENDITA` | 1 | lista ordini, colonna «Transito» → **oggi scrive «Fattura»** |
| `RESO_VENDITA` | 1 | lista resi, colonna «Transito» → **il caso di questo cantiere** |
| `COMMESSA` | 1 | drawer commessa (pannello, già corretto) |
| `FATTURA` | 1 | la NC frontiera di sé stessa |

⚠️ **Uno su quattro è già a video oggi**, sulla lista ordini, dal 2026-08-21. Non
se n'è accorto nessuno perché è **una riga**; sul reso diventa la regola.

### 7-bis.4 La richiesta

**Esporre `frontiera_natura_doc_codice` su `vendite.vw_documento_lineage`.**

* La sorgente è già lì: la CTE della frontiera conosce `frontiera_tipo_id` e
  `frontiera_uid`, e `vw_documento_lineage_nodi` porta già
  `natura_doc_codice` (rev 2026-08-20). È **un `LEFT JOIN` sul nodo di
  frontiera**, lo stesso che il BE scrive a mano in `get_lineage_nodo`.
* ⚠️ **`LEFT`, non `JOIN`**: `natura_doc_id` è nullable su `vendite.fatture`, e
  sugli altri sette tipi di nodo la natura è NULL **ed è corretto** (la natura è
  un asse diverso dal tipo, ed esiste solo per le fatture).
* Poi le **sei** `vw_*_lista` la portano avanti come già fanno con
  `frontiera_fase`, e i sei repository la proiettano accanto a
  `frontiera_tipo_codice`.

⭐ **E la ragione dichiarata nel `COMMENT` va aggiornata di conseguenza**, perché
è la seconda volta che quella frase è vera a metà. Il `20260825-20` ha corretto
*«varrebbe sempre NULL»* in *«il consumatore la ricava per conto suo»*. Ma il
consumatore che la ricava è **uno**, e i consumatori che non possono sono
**sei**: la frase giusta diventa *«la colonna c'è perché la chiave del nodo di
frontiera non esce dalla summary, e senza di lei ogni lista chiama Fattura una
nota di credito»*.

### 7-bis.5 Cosa fa il BE/FE nel frattempo

**Niente, e aspetta** ([[feedback_be_fe_attende_prerequisiti_db]]). Il lavoro a
valle è piccolo e già scritto qui, così quando la colonna arriva è un giro solo:

1. sei repository: `v.frontiera_natura_doc_codice` nella `SELECT`;
2. `LineageFrontieraChip`: prop `naturaCodice` e `lineageDocumentoLabel` al posto
   di `lineageTipoLabel` — **la funzione esiste già**, cambia la chiamata;
3. le **sei** liste passano la prop — ⚠️ e vanno passate **tutte e sei**: una
   prop dichiarata e non passata è un cancello che sembra esserci
   ([[feedback_bb_legge_non_trasporta]]);
4. un test nel presidio delle sei liste, gemello di
   `test_ogni_lista_decodifica_il_tipo_della_frontiera`.

⚠️ **Le chiavi i18n ci sono già tutte** (`vendite.lineage.natura_nota_credito`,
`natura_fattura`, `natura_nota_debito`, in `it.json` e `en.json`): non c'è niente
da tradurre, il giorno che si accende.

---

## 8. Registro

### 2026-08-25 · Analisi e consegna

Legame ricostruito e verificato sui dati (NC 20024 → `RESO0000017`), tre archi
esistenti misurati, trappola della chiave di raggruppamento isolata prima di
scrivere, decisione molti-a-molti presa da Tid, arco `S` provato in query.
Nessuna riga di DB, BE o FE ancora scritta.

### 2026-08-25 · Verifica critica

Piano rimisurato sul DB vivo con la vista ricreata **in transazione chiusa in
`ROLLBACK`** e diff snapshot prima/dopo. Esito: l'impianto regge, **cinque
correzioni portanti** (§0.2).

1. ⛔ **L'arco `S` usciva dal perimetro RLS dei resi** — `vendite.resi` ha la
   policy, `resi_righe` e `resi_righe_accrediti` no. Cercati i gemelli: **B, E,
   F e G fanno lo stesso** da luglio, saltando `commesse` e le testate delle
   sorgenti via `commesse_sorgenti` e `attivita_fatturabili`, che RLS non hanno.
2. ⚠️ Il `COMMENT` di `vw_documento_lineage` va corretto con un `COMMENT ON VIEW`
   **da solo**: ricreare la vista rischierebbe l'azzeramento di
   `security_invoker`.
3. ⚠️ Il terzo pgTAP proposto misurava il dato di oggi. Sostituito da due
   invarianti seed-agnostiche.
4. ⚠️ **Effetti sulla summary dichiarati**: 2 righe su 425 (§5-bis), fra cui un
   `root` che resta la commessa **per l'ordine degli id** e non per una regola —
   fragilità preesistente, portata a §7.
5. ⭐ **L'arco `S` arriva sempre a una NOTA DI CREDITO ed è asseribile** — vedi
   la decisione qui sotto.

Aggiunta la **seconda strada ovvia e sbagliata** (§3-bis:
`fattura_riga_rettificata_id`, l'arco a un join di distanza che farebbe della
frontiera del reso un sorteggio fra due `d_uid` testuali).

Confermate sul dato tutte le altre affermazioni del brief (§0.1), compresa una
misura nuova: **5 accrediti, 3 con la riga di fattura** — il `WHERE` non è una
formalità copiata dall'arco G, tiene fuori due casi su tre oggi.

### 2026-08-25 · Tre decisioni di Tid, e una domanda che ha corretto il piano

**1. Il perimetro RLS si chiude tutto, non solo `S`.** `B`, `E`, `F` e `G`
entrano nello stesso changeSet: cinque join in più su chiave primaria, zero
righe cambiate sul dato di oggi (misurato). Motivo: la vista si ricrea comunque,
e un buco misurato e rimandato è quello che nessuno riapre. Presidiato dal nuovo
test **38**, che è generale e non parla di `S`.

**2. ⭐ L'arco `S` deve asserire la NOTA DI CREDITO — la mia raccomandazione era
sbagliata.** Avevo proposto di lasciare il test agnostico sulla natura, per non
«asserire una conseguenza di `fn_build_fattura_key`». La domanda di Tid — *«di
solito il reso si lega a una nota credito, anche se tecnicamente cambia solo il
tipo documento ma la tabella è la stessa»* — ha spostato la verifica dove doveva
stare, cioè sul codice. E il codice dice che **non è una conseguenza, è
un'invariante tenuta in due punti indipendenti**: `fn_accredita_riga_reso`
impone `NOTA_CREDITO` (non la deriva dal segno) e `fn_build_fattura_key` la porta
dentro la chiave di aggregazione, con `trg_fatture_lock_natura_doc` a bloccarla
sulla testata. Il test 35 nasce da qui, con `IS DISTINCT FROM` perché la natura
è nullable e un `<>` passerebbe proprio sul caso peggiore.

**3. `vw_resi_lista` entra nel cantiere.** Diventa la sesta sorella (§5 DB-F).
Verificato che è **DB-only**: `ResiSearchTable.vue` è già
`<ListaConfigurabile codice="vendite.resi">`, il preset `resi_default` esiste, i
mirror CSV sono `runOnChange` e le chiavi i18n ci sono. Trovata nel farlo una
trappola: i test 21/22/25 di `test-colonne-lineage-liste-v1.sql` sono ancorati a
`lista_id IN (4..8)` e alla costante 15, quindi **non diventerebbero rossi** —
resterebbero verdi smettendo di coprire la lista nuova.

**4. Ci si ferma al piano.** Nessun file di migrazione scritto in quella
passata; nessuna migrazione applicata. *(Superata la sera stessa: vedi la voce
successiva.)*

⛔ **E nel frattempo la numerazione si è mossa.** Il piano nominava `12` e `13`;
un controllo su `databasechangelog` a fine passata ha trovato il `12` già preso e
**applicato** dal cantiere numerazione (`20260825-12-upsert-parameter-system-fuso-orario`),
in un file che `git status` mostrava come untracked. I lotti sono stati
rinumerati a **13/14/15** e la regola è stata scritta in L0.4: la sequenza è
globale per data fra tutte le cartelle, si legge dal `databasechangelog` e si
rilegge **immediatamente prima** di dare un nome ai file.

### 2026-08-25 · Consegna scritta e APPLICATA

Tid: «puoi iniziare il progressivo -19». Scritti e applicati.

| # | Oggetto | Esito |
| --- | --- | --- |
| `20260825-19` | `vw_documento_lineage_archi`: arco `S` + perimetro RLS su `B`/`E`/`F`/`G` | `EXECUTED` 17:03 |
| `20260825-20` | `COMMENT ON VIEW vw_documento_lineage` (la prosa falsa) | `EXECUTED` 17:03 |
| `20260825-21` | `vw_resi_lista`: `fase` + 9 colonne di genealogia | `EXECUTED` 17:03 |
| CSV | `lista_colonna` +3 (id 549-551), `lista_preset_colonna` +3 | caricate dal mirror `runOnChange` |
| pgTAP | `test-documento-lineage-v1` `plan(32)`→`plan(38)` | **38/38** |
| pgTAP | `test-colonne-lineage-liste-v1` `plan(26)`→`plan(30)` | **30/30** |

**Verifiche.** `guardrail_run_on_change` e `guardrail_pgtap_preambolo` verdi.
`scripts/pgtap-baseline.sh vendite`: 225 file, **5 rossi, tutti già noti in
baseline, nessuna regressione**. Archi per lettera **esattamente come previsto**:
A 64 · B 47 · C 1 · D 2 · E 28 · F 3 · G 20 · H 19 · N 1 · R 13 · **S 1** —
zero archi persi sui quattro rami che hanno preso il join di perimetro.

⚠️ **L'apply non l'ha lanciato l'agente.** I tre changeSet risultano `EXECUTED`
alle 17:03 di un migrate **esterno** partito mentre il lavoro era in corso: ha
raccolto i file appena scritti e, essendo il mirror dei CSV `runOnChange`, anche
le sei righe di seed appena appese. Prima di quel momento erano stati provati
**solo in transazione chiusa in `ROLLBACK`**, che è il motivo per cui hanno
retto al primo colpo.

⛔ **Due correzioni al piano, trovate scrivendo.**

1. **La numerazione era di nuovo stantìa.** Il piano diceva 13/14/15; alle 16:50
   il cantiere numerazione era arrivato al **18**. Usati 19/20/21, come chiesto
   da Tid. È la seconda volta in una giornata: la regola di L0.4 non è teorica.
2. **`lista_preset_colonna.csv` non ha una colonna `id`** (§5 DB-F.2). Il piano
   diceva «id da 49, max attuale 48»: quel 48 era un `preset_id`, non un id. La
   PK è composta `(preset_id, colonna_id)`.

⚠️ **E una query sbagliata mia, che vale la pena ricordare**: per capire se i
changeSet fossero applicati avevo interrogato `databasechangelog` con
`id LIKE '20260825-1[6-9]%'`. In SQL `LIKE` le **parentesi quadre sono
letterali**, non una classe di caratteri: la query tornava vuota e sembrava che
`-19` non fosse applicato — mentre lo era. Per le classi serve `~` (regex).

⭐ **Un'osservazione dall'esecuzione reale, per la verifica in-app.** Sulla riga
del reso 24 la colonna «Transito» mostra **`1`**, non `NC0000001`: il `codice`
del nodo fattura è `fatture.numero`, e il registro delle note di credito è al
numero 1. Sulle sorelle la stessa colonna mostra `DDT0000031`. Non è un difetto
di questo cantiere — è come `vw_documento_lineage_nodi` espone il numero delle
fatture — ma è ciò che l'operatore vedrà, ed è in §7.

**Doc auto-gen rigenerata** (Tid, subito dopo): le tre viste in
`docs/it/dbzero/vendite/views/` riflettono ora l'oggetto vivo —
`vw_documento_lineage_archi` con l'undicesimo ramo e la regola di perimetro,
`vw_documento_lineage` con la prosa corretta, `vw_resi_lista` con `fase` e le
nove colonne di genealogia. ⛔ Non è stata toccata a mano.

⚠️ **Resta un debito documentale, e va nominato perché non si veda da solo.** Le
pagine **manual** delle tre viste (`docs/it/dbzero/vendite/manual/`) sono ferme:
`vw_documento_lineage_archi.md` è del 2026-08-21 e la sua tabella degli archi si
ferma a `N`; `vw_resi_lista.md` è del 2026-08-03 e non sa di avere la genealogia.
La auto-gen si rigenera, quella **no** — è scritta a mano ed è l'unica metà della
doc che può restare indietro senza che nessuno se ne accorga. È lo stesso difetto
che questo cantiere ha corretto sul `COMMENT` (§DB-C), un piano più in là.

### 2026-08-26 · Il BE/FE che il brief dichiarava inesistente

Tid: *«completa l'attività come da documento, anche se credo lato BE/FE ci sia
poco o nulla da fare»*. Il brief lo diceva più forte — **«zero righe di FE, zero
righe di BE»** (§5 DB-F.4) — ed è stato verificato invece che creduto.

**La consegna DB regge, misurata sul DB vivo** in contesto operatore
(`script.fn_pgtap_set_contesto_operatore`): archi
`A 64 · B 47 · C 1 · D 2 · E 28 · F 3 · G 20 · H 19 · N 1 · R 13 · **S 1**`,
esattamente le attese del §L6; reso 24 con `is_transitato = t`,
`frontiera_codice = 1`, `n_discendenti_attivi = 1`.

⚠️ **E la prima misura è stata sbagliata, vale la pena scriverlo**: interrogata
la vista come `zeroerp_app` **senza** contesto, `arco = 'S'` tornava **zero** —
che somiglia a «la migrazione non è passata» e invece è la RLS fail-closed
([[feedback_rls_conteggio_zero_non_e_un_dato]]). Le GUC si impostano **prima** di
misurare, non dopo aver trovato un numero strano.

⛔ **Tre buchi BE/FE, tutti silenziosi.** Dettaglio, misure e forma del difetto
nel §5 DB-F.4 corretto. In una riga: il seed porta la **colonna**, non la
**cella**, e la vista espone l'**id** del tipo di frontiera, mai il **codice**.
Senza i due pezzi la colonna «Transito» del reso accreditato avrebbe mostrato
**«—»**, cioè l'esatto contrario di ciò che il cantiere è servito a dire.

| # | File | Cosa |
| --- | --- | --- |
| 1 | `backend/apps/vendite/db/resi_repository.py` | `frontiera_tipo_codice` decodificato da `config.sorgenti`, come sulle cinque sorelle |
| 2 | `frontend/src/vendite/resi/components/ResiSearchTable.vue` | i tre slot `#cell-pratica` / `#cell-fase` / `#cell-transito` |
| 3 | `backend/apps/vendite/tests/services/test_lineage_liste_be.py` | esteso da **5 a 6** liste **+** presidio nuovo sulla decodifica della frontiera |

⭐ **Il terzo è la stessa trappola del §5 DB-F.3, sul lato Python**, e non
l'avevo cercata lì: un presidio ancorato a un elenco di cinque **resta verde**
mentre smette di coprire la sesta. Il nuovo test è stato verificato **al
contrario** — rimessa la `SELECT v.*` nuda, diventa rosso e lo dice con la frase
giusta.

**Verifiche.** `test_lineage_liste_be` 3/3 · `test_liste_configurabili_seed` 9/9
· `eslint` e `vite build` puliti · `scripts/check_i18n_keys.py` verde ·
`frontend/scripts/check-liste-configurabili.mjs` verde. Nessuna migrazione
scritta né applicata: `20260825-19/20/21` e i CSV restano quelli del 25.

🔴 **Un difetto nuovo trovato dalla misura, passato al team DB nel §7-bis.** Con
il chip finalmente vivo, quello che si legge è `→ [Fattura] 1`: la colonna
«Transito» **chiama «Fattura» la nota di credito**. Il FE non può rimediare — la
regola `lineageDocumentoLabel` esiste dal 2026-08-21, ma il join che porta la
natura ha bisogno di `frontiera_uid`, che la summary ha e le sei `vw_*_lista`
**no** (verificato: *«la colonna v.frontiera_uid non esiste»*). Il difetto è
**preesistente** — è già a video sulla lista ordini da cinque giorni, su una
riga — e questo cantiere lo rende **strutturale**, perché il pgTAP 35 asserisce
che l'arco `S` arriva *sempre* a una `NOTA_CREDITO`. BE/FE **aspettano**
([[feedback_be_fe_attende_prerequisiti_db]]), col lavoro a valle già scritto nel
§7-bis.5.

**Debito documentale del §8 pagato.** Le tre pagine **manual** erano ferme e la
auto-gen non le rigenera:

* `vw_documento_lineage_archi.md` — la tabella degli archi si fermava a `R`: ora
  ha `N` e `S`, la sezione dell'arco `S` (comprese le **due strade ovvie e
  sbagliate**) e la **regola generale del perimetro RLS**, con la trappola della
  chiave polimorfa di `B`/`E`/`F`;
* `vw_resi_lista.md` — era del 2026-08-03 e non sapeva di avere la genealogia:
  ora ha le nove colonne, la trappola di `fase`, e la sezione *«cosa serve al
  consumatore e non è nella vista»* (i due buchi sopra);
* `vw_documento_lineage.md` — ⛔ **portava ancora la frase falsa** corretta dal
  `20260825-20` nel `COMMENT`, e **si contraddiceva due paragrafi più sotto**
  sulla stessa pagina. Corretta, con il perché e col rimando al §7-bis.

⭐ **È la conferma del §DB-C sul terzo lato**: un commento sbagliato non fallisce
mai, e ce n'erano **due copie** — una nel database, una nella doc a mano. Il
changeSet ha corretto quella che il DB conosceva; l'altra è rimasta lì cinque
giorni, e nessun presidio l'avrebbe mai vista.

---

## 9. ⭐ Piano di sviluppo

> ⛔ **Nessuna migrazione viene applicata da questo piano.** L'applicazione
> (`liquibase update` / `make db-migrate`) la lancia **Tid**, a parole, sul
> comando specifico. Il piano si ferma ai file scritti e ai comandi che **non
> applicano** (`validate`, `updateSQL`, pgTAP in transazione).
>
> 🟡 **Stato: piano approvato, file non ancora scritti** (decisione 4 del §8).

### L0 — prerequisiti (prima di aprire un editor)

| # | Cosa | Nota |
| --- | --- | --- |
| 0.1 | Corpo corrente di `vw_documento_lineage_archi` e di `vw_resi_lista` **dalla doc auto-gen** — `docs/it/dbzero/vendite/views/` | ⛔ **mai** dallo YAML: cinque file definiscono la vista archi e solo l'ultimo conta |
| 0.2 | Modello di riferimento per DB-F: `20260715-05-update-vw-ddt-lista-lineage-mctit.yaml` | La sesta sorella si scrive come la quinta |
| 0.3 | Rileggere `docs/it/linee-guida-sql.md` §6/§6c e `.codex/AGENTS.md` §Liquibase | Fatto in questa passata: nessun vincolo di §6c è toccato (nessun alias `codice`/`codice_interno` nuovo) |
| 0.4 | Verificare la **numerazione libera** per il 2026-08-25 | Sequenza **globale per data**, non per cartella. **Occupati fino al 18; usati 19, 20, 21** — letti da `databasechangelog`, non dal filesystem |

⛔ **0.4 non è una formalità, e questo brief ne è la prova.** Alle 10 del
2026-08-25 il piano diceva «prossimi liberi: 12, 13». Un'ora dopo il `12` era
preso e **applicato** — `20260825-12-upsert-parameter-system-fuso-orario`, del
cantiere numerazione, che di questo non sa niente. La sequenza è **globale per
data fra tutte le cartelle**, e il cantiere accanto scrive nello stesso spazio
senza attraversare i tuoi file: il filesystem non basta, e nemmeno `git status`
(quel file era untracked). La misura giusta è una sola:

```bash
psql … -Atc "SELECT id FROM databasechangelog WHERE id LIKE '20260825-%' ORDER BY id;"
```

e va rifatta **immediatamente prima** di dare un nome ai file, non a inizio
sessione.

### L1 — `20260825-19` · l'arco `S` **e** il perimetro RLS

**File:** `db/changelog/migrations_v2/20_code/vendite/20260825-19-update-vw-documento-lineage-archi-arco-reso-e-perimetro-rls-mctit.yaml`

* **Modello**: `20260821-02` (stesso oggetto, stessa forma) — header GPL, blocco
  di prosa, `logicalFilePath`, `runOnChange: false`,
  `validCheckSums: [ANY]` (⚠️ **al plurale**), `failOnError: true`.
* **Contenuto**: `CREATE OR REPLACE VIEW … WITH (security_invoker=on)` — corpo
  dalla doc auto-gen, **più** il ramo `S` (§5 DB-A.1) e **più** i cinque join di
  perimetro su `B`/`E`/`F`/`G` (§5 DB-A.2), seguito dal `COMMENT ON VIEW`
  aggiornato: undici archi, `S` non è ramo di ritorno **e perché**, e la regola
  generale del perimetro (le tabelle-ponte non danno RLS).
* ⛔ **Il punto in cui si sbaglia**: la chiave di `commesse_sorgenti.sorgente_uid`
  è polimorfa — `p.uid::text` per B, `o.id::text` per E, `c.id::text` per F.
  Verificato sul dato: 47 uuid per il preventivo, 28 e 3 id numerici per ordine e
  contratto.
* **`preConditions`** (`onFail: HALT`):
  * `viewExists` su `vendite.vw_documento_lineage_archi`;
  * `tableExists` su `vendite.resi_righe_accrediti`;
  * `sqlCheck` = 1 su `config.sorgenti WHERE codice_interno = 'RESO_VENDITA' AND attivo IS TRUE`.
* **`rollback`**: `SELECT 1` con la motivazione, come in `20260821-02`.

### L2 — `20260825-20` · il commento che mentiva

**File:** `db/changelog/migrations_v2/20_code/vendite/20260825-20-comment-vw-documento-lineage-frontiera-natura-mctit.yaml`

* Un solo statement: `COMMENT ON VIEW vendite.vw_documento_lineage IS '…'`.
  **Nessun `CREATE OR REPLACE`** (§DB-C).
* Testo nuovo = quello corrente **meno** la frase sulla
  `frontiera_natura_doc_codice` che «varrebbe sempre NULL», sostituita da: una
  nota di credito **può** essere frontiera — lo è già della commessa via `G` e
  dal 2026-08-25 anche del **reso** via `S`; la colonna non c'è perché il
  backend la ricava in `get_lineage_nodo`, non perché sarebbe vuota.
* **`preConditions`** (`onFail: HALT`): `sqlCheck` = 1 che l'arco `S` sia già
  nella vista —
  `SELECT count(*) FROM pg_views WHERE schemaname='vendite' AND viewname='vw_documento_lineage_archi' AND definition LIKE '%''S''::text%'`.
  È «L1 prima di L2» in una forma che il DB può verificare.

### L3 — `20260825-21` · `vw_resi_lista`, la sesta sorella

**File:** `db/changelog/migrations_v2/20_code/vendite/20260825-21-update-vw-resi-lista-lineage-mctit.yaml`

* `CREATE OR REPLACE VIEW vendite.vw_resi_lista WITH (security_invoker=on)` —
  corpo dalla doc auto-gen, più `fase` (da `sr.fase`) e il `LEFT JOIN` su
  `vw_documento_lineage`, nella stessa forma di `vw_ddt_lista` (§5 DB-F.1).
* `COMMENT ON VIEW` che dice **cosa mostra la colonna transito su un reso**: la
  frontiera di un reso accreditato è la nota di credito, quindi lì compare il
  numero della nota.
* **`preConditions`**: `viewExists` su `vw_resi_lista` e su
  `vw_documento_lineage`; `sqlCheck` = 1 che l'arco `S` ci sia (come L2) — senza,
  la colonna nascerebbe sempre vuota sui resi accreditati.

### L4 — seed: **solo append ai CSV**, nessun changeSet

⛔ Nessun loader nuovo: i mirror sono `runOnChange` e ripescano il file
(`20260806-15`, `20260507-09`).

| file | righe | id |
| --- | --- | --- |
| `80_data/sql/ui/lista_colonna.csv` | 3 su `lista_id = 9`, copiate da 197/198/199 | 549, 550, 551 |
| `80_data/sql/ui/lista_preset_colonna.csv` | 3 sul preset 9 (`resi_default`) | 49, 50, 51 |

⚠️ `sensibile = f`, `attivo = t`, chiavi i18n `vendite.lineage.col_*` (esistono).
⚠️ Ricontrollare i `max(id)` al momento della scrittura: i CSV sono condivisi e
un altro cantiere può averli fatti crescere.

### L5 — pgTAP

**5.1 — `db/pgtap/vendite/test-documento-lineage-v1.sql`**

| # | Modifica |
| --- | --- |
| a | `plan(32)` → **`plan(38)`** |
| b | Test **13**: `'S'` nella whitelist **e** nell'etichetta |
| c | Prosa sopra il test **7**: la nota sulla `frontiera_natura_doc_codice` è falsa, va riscritta come nel `COMMENT` di L2 |
| d | Prosa del test **18**: «un reso è però frontiera di sé stesso come foglia» → **finché non è accreditato** |
| e | Test **33..38** in coda, col blocco che spiega il cantiere (§5 DB-E) |
| f | Indice in testa: voci `33..38`, e correzione delle voci **13** e **18** |

**5.2 — `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql`** ⛔ *la trappola del §5 DB-F.3*

| # | Modifica |
| --- | --- |
| a | Test **21**, **22**, **25**: `lista_id IN (4,5,6,7,8)` → `(4,5,6,7,8,9)` e la costante `15` → **`18`** |
| b | 3 `has_column` su `vw_resi_lista` (`pratica_numero`, `fase`, `frontiera_codice`) + 1 `security_invoker` |
| c | `plan(26)` → **`plan(30)`**, indice in testa e intestazione da «5 liste» a «6 liste» |

⚠️ Senza (a) i tre test **restano verdi** e smettono di coprire la lista nuova:
è il caso in cui non c'è nessun rosso ad avvisare.
⚠️ Il preambolo (`BEGIN;`, contesto operatore, `SET CONSTRAINTS ALL IMMEDIATE`)
c'è già in entrambi i file e non si tocca: il guardrail CI lo verifica.

### L6 — verifica (nessuno di questi comandi applica)

```bash
# 1. sintassi e ordine dei changeSet — non applica
scripts/liquibase5.sh validate
scripts/liquibase5.sh updateSQL | grep -n "20260825-(19|2[01])"

# 2. i guardrail statici che questa consegna attraversa
python3 scripts/guardrail_run_on_change.py      # runOnChange in 20_code
python3 scripts/guardrail_pgtap_preambolo.py    # preambolo dei due test

# 3. i test, DOPO che Tid ha applicato — girano in transazione
scripts/testpgtap.sh vendite/test-documento-lineage-v1.sql
scripts/testpgtap.sh vendite/test-colonne-lineage-liste-v1.sql

# 4. nessuna regressione altrove nello schema
scripts/pgtap-baseline.sh vendite
```

**Atteso**, misurato in anticipo su questa stessa modifica:

* `test-documento-lineage-v1` → **38/38**; `test-colonne-lineage-liste-v1` → **30/30**;
* archi per lettera: **A 64 · B 47 · C 1 · D 2 · E 28 · F 3 · G 20 · H 19 · N 1 ·
  R 13 · S 1**. ⛔ Se `B`, `E`, `F` o `G` calano, un join di perimetro ha la
  chiave sbagliata (§L1);
* `vw_documento_lineage`: **425 righe prima, 425 dopo**, **2 righe cambiate**
  (§5-bis);
* `scripts/pgtap-baseline.sh vendite` → nessuna regressione nuova (nessuno dei
  due file è in baseline: sono verdi oggi).

### L7 — documentazione e chiusura

| # | Cosa |
| --- | --- |
| 7.1 | Riga di registro in **§8** con l'esito reale dell'apply (data, changeSet, conteggio archi, test) |
| 7.2 | Aggiornare **§44** di [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md): l'arco `S` chiude la richiesta 2 anche dal lato reso |
| 7.3 | Spuntare la voce corrispondente in [collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md) dopo la verifica in-app della tabella del §6, **più** la colonna «Transito» nella lista resi |
| 7.4 | ⚠️ La doc auto-gen si rigenera **da sola** al migrate: **non editarla a mano**. Finché Tid non applica, nel repo resta la prosa vecchia — è atteso, non un debito |
| 7.5 | Portare a un cantiere suo i due residui del §7: il tie-break del `root` e le 2 righe `DDT_VENDITA` in `commesse_sorgenti` senza arco |

### Definition of Done

* [X] `20260825-19` scritto: arco `S` **e** perimetro su B/E/F/G, chiavi polimorfe verificate
* [X] `20260825-20` scritto, con la precondizione che lega L2 a L1
* [X] `20260825-21` scritto: `vw_resi_lista` con `fase` + colonne lineage
* [X] CSV `lista_colonna` e `lista_preset_colonna` appesi (3 + 3 righe, `sensibile = f`)
* [X] `test-documento-lineage-v1` a `plan(38)`, test 13/18 e prosa del 7 corretti
* [X] `test-colonne-lineage-liste-v1` a `plan(30)`, **costante 15 → 18** (test rinumerati 25/26/29)
* [X] guardrail statici verdi (`run_on_change`, `pgtap_preambolo`)
* [X] ⛔ migrazione applicata da un migrate **esterno** alle 17:03, non dall'agente
* [X] `38/38` + `30/30`, conteggio archi invariato su A..R, `pgtap-baseline.sh vendite` pulito
* [X] §8 aggiornato con l'esito reale
* [X] doc auto-gen delle tre viste rigenerata (`scripts/gen_db_docs.py`) — ⛔ mai a mano — *verificata il 2026-08-26: `vw_resi_lista` porta `fase` + le nove colonne, `vw_documento_lineage_archi` l'undicesimo ramo, `vw_documento_lineage` la prosa corretta*

**BE/FE — la metà che il brief dichiarava inesistente (2026-08-26, §5 DB-F.4):**

* [X] `ResiRepository.list_resi` decodifica `frontiera_tipo_codice` (senza, il chip resta muto)
* [X] `ResiSearchTable.vue` monta i tre slot `#cell-pratica` / `#cell-fase` / `#cell-transito`
* [X] `test_lineage_liste_be.py` esteso da 5 a **6** liste + presidio sulla decodifica della frontiera, verificato **al contrario**
* [X] `eslint` · `vite build` · `check_i18n_keys.py` · `check-liste-configurabili.mjs` verdi

**Documentazione:**

* [X] §44 di `brief-design-note-credito-resi.md` allineato (L7.2)
* [X] `collaudo-in-app-nota-credito-resi.md`: voce di collaudo della genealogia (L7.3)
* [X] debito documentale del §8 pagato: le **tre** pagine **manual** in `docs/it/dbzero/vendite/manual/` (⛔ fra cui la prosa falsa sopravvissuta al `20260825-20`)

**Aperto — non dipende da me:**

* [ ] ⏳ **verifica in-app** dei quattro casi della tabella §6 + colonna «Transito» sulla lista resi (Tid)
* [ ] 🔴 **§7-bis al team DB**: `frontiera_natura_doc_codice` su `vw_documento_lineage` — senza, la colonna «Transito» chiama «Fattura» la nota di credito. BE/FE **aspettano**, lavoro a valle già scritto nel §7-bis.5
* [ ] L7.5: i due residui del §7 (tie-break del `root`, le 2 righe `DDT_VENDITA` senza arco) portati a un cantiere loro
