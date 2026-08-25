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
> **Correlati:**
> [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md) ·
> [collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md)

---

## 1. Il caso misurato

Nota di credito **20024** (numero 1, registro NC). Gli archi che la toccano oggi:

| arco | da | a | `is_ramo_inverso` |
| --- | --- | --- | --- |
| `G` | Commessa 322 | **NC 20024** | `f` |
| `N` | Fattura 835 (n. 11) | **NC 20024** | `t` |
| `R` | DDT 140 | **Reso 24** (`RESO0000017`, 14/07) | `t` |

**Dal reso 24 non esce nessun arco: è una foglia.** Il pannello «Passaggi» della
nota mostra la fattura rettificata e la commessa; il reso non c'è. E nel drawer
del reso l'unica traccia dell'accredito è `gia_accreditato`, che è **una
quantità**, non un documento.

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

### DB-A — l'arco `S` in `vendite.vw_documento_lineage_archi`

Undicesimo ramo della `WITH archi AS (...)`, nella stessa forma degli altri:

```sql
UNION ALL
 SELECT DISTINCT s_from.id,
        (rr.reso_id)::text,
        s_to.id,
        (fr.fattura_id)::text,
        NULL::character varying,
        'S'::text
   FROM vendite.resi_righe_accrediti a
   JOIN vendite.resi_righe rr           ON rr.id = a.resi_riga_id
   JOIN vendite.attivita_fatturabili af ON af.commessa_attivita_id = a.commessa_attivita_id
   JOIN vendite.fatture_righe fr        ON fr.id = af.fattura_riga_id
   JOIN config.sorgenti s_from ON s_from.codice_interno = 'RESO_VENDITA' AND s_from.attivo IS TRUE
   JOIN config.sorgenti s_to   ON s_to.codice_interno   = 'FATTURA'      AND s_to.attivo IS TRUE
  WHERE af.fattura_riga_id IS NOT NULL
```

Provato sui dati: torna **una riga**, `reso 24 → NC 20024`.

* `DISTINCT` serve: più accrediti dello stesso reso confluiscono nella stessa
  nota (tre, nel caso reale).
* Il `WHERE af.fattura_riga_id IS NOT NULL` è lo **stesso** dell'arco G: prima
  dell'emissione la riga di fattura non esiste ancora, e l'arco deve comparire
  quando c'è.
* Indici: `ix_resi_accrediti_commessa_attivita_id` c'è, e
  `uq_attivita_fatturabili_commessa_attivita` rende quel join **1:1**. Nessun
  indice nuovo.

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

### DB-C — due prose diventate false, da correggere nello stesso changeSet

Il `COMMENT` di `vendite.vw_documento_lineage` afferma:

> *«NON esiste una `frontiera_natura_doc_codice`, di proposito: l'arco N è un
> ramo di ritorno ed è escluso dal grafo forward, quindi una nota di credito non
> può mai essere la frontiera di nessuno e quella colonna varrebbe sempre NULL.»*

⛔ **È già falso oggi**, e non per colpa di questo cantiere: l'arco `G`
(commessa → fattura) **non** è un ramo di ritorno, e il backend lo aveva già
misurato il 2026-08-21 — *«la frontiera PUÒ essere una nota di credito: è già la
frontiera dell'ordine 240 e della commessa 322»*, tant'è che
`get_lineage_nodo` la legge davvero (`nfr.natura_doc_codice AS
frontiera_natura_doc_codice`). Con l'arco `S` diventa falso una seconda volta.

Da correggere:

1. il `COMMENT` di `vw_documento_lineage`;
2. lo stesso testo ricopiato nel pgTAP (`test-documento-lineage-v1.sql`, sopra
   il test 7 delle colonne) e la prosa del test 18 («un reso è però frontiera di
   sé stesso come foglia» → vale solo per un reso **non ancora accreditato**).

Nessuna delle due è un'asserzione: sono commenti. Ed è proprio per questo che
vanno corretti adesso — un commento sbagliato non fallisce mai.

### DB-D — ⚠️ la whitelist del pgTAP

`db/pgtap/vendite/test-documento-lineage-v1.sql`, test 13:

```sql
WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R','N')
```

**Va aggiunto `'S'`**, o il test va rosso al primo arco emesso. È il caso da
manuale di [[feedback_whitelist_dal_percorso_reale]]: una whitelist si verifica
dal percorso che la attraversa, non dal nome del test.

### DB-E — pgTAP nuovi

Da aggiungere in coda a `test-documento-lineage-v1.sql`, aggiornando l'indice in
testa:

1. l'arco `S` parte **sempre** da un nodo `RESO_VENDITA`;
2. l'arco `S` arriva **sempre** a un nodo `FATTURA`;
3. *(skip-able sui dati reali)* il reso 24 ha la NC 20024 come **frontiera**, e
   non più sé stesso — è la prova della decisione DB-B sul comportamento, non
   sulla forma.

⭐ **La decisione DB-B è già presidiata, e da un test che c'è.** Il **29** asserisce
`is_ramo_inverso <> (arco IN ('R','N'))` = 0, cioè *«è vero esattamente per R e
N»*: con `S` fuori dall'array resta **verde**, e diventerebbe **rosso** il giorno
in cui qualcuno aggiungesse `S` ai rami di ritorno «per simmetria». Non serve un
test nuovo — serve **non toccare** né l'array della vista né quello del test 29.

⚠️ Invarianti esistenti che **restano vere** e non vanno toccate — verificato
leggendo le asserzioni, non i titoli:

* **18** (*«RESO mai frontiera di un nodo non-reso»*): `S` porta **verso** una
  fattura, mai verso un reso;
* **29**: vedi sopra;
* **30** (*«una FATTURA è sempre frontiera di sé stessa»*, che presidia il fatto
  che una fattura non ha archi uscenti nel grafo forward): `S` è un arco
  **entrante** nella fattura.

---

## 6. Cosa NON serve fare

* **Nessuna tabella ponte.** `S` è un soft-link calcolato, come `G` e `N`.
* **Nessuna modifica a `fn_documento_lineage` né a `vw_documento_lineage`.** Dal
  2026-08-20 le lettere dei rami di ritorno vivono in **un posto solo**
  (`is_ramo_inverso`, calcolato nella vista archi); il traversal e la summary la
  leggono. Era il difetto che l'arco N aveva già pagato — la lettera scritta in
  tre posti e il terzo dimenticato.
* **Nessuna modifica al frontend.** Il pannello non conosce le lettere: etichetta
  le tappe per **tipo** e **natura** (`lineageDocumentoLabel`), e la chiave i18n
  `vendite.lineage.natura_nota_credito` esiste già. La tappa `reso → nota di
  credito` compare da sola, con la sua etichetta giusta.
* **Nessuna modifica al backend.** `list_lineage_passaggi` proietta l'arco così
  com'è.

⚠️ Da **verificare in-app** dopo l'applicazione, non da assumere: che il chip in
`DocumentoCollegamentiBar` sul drawer del reso mostri la nota fra i collegamenti
in avanti. Il codice dice di sì (raggruppa su `is_ramo_inverso`, non sulle
lettere), ma è una lettura, non una prova.

---

## 7. Cosa resta aperto, e non è di questo cantiere

* Il **verso reso → documento** dentro il drawer del reso oltre al pannello
  Passaggi: oggi la riga mostra `gia_accreditato`, una quantità. Se si vuole il
  **numero della nota** in colonna, è una consegna BE+FE separata (la fonte
  sarebbe la stessa di `S`).
* Il raggruppamento `MAN:<commessa>` e l'ipotesi «una nota per reso» (§4).
* Il fatto che `fn_accredita_riga_reso` passi `sorgente => NULL` **senza dirlo**:
  il valore è giusto (§3), il silenzio no. Un commento di due righe lì eviterebbe
  che il prossimo lo legga come una dimenticanza — e questo giro è la prova che
  succede.

---

## 8. Registro

### 2026-08-25 · Analisi e consegna

Legame ricostruito e verificato sui dati (NC 20024 → `RESO0000017`), tre archi
esistenti misurati, trappola della chiave di raggruppamento isolata prima di
scrivere, decisione molti-a-molti presa da Tid, arco `S` provato in query.
Nessuna riga di DB, BE o FE ancora scritta.
