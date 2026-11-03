## 📘 Documentazione Concettuale – Guard `vendite.trgfn_resi_righe_guard_origine_coerente`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
Viste collegate:
>
[vw_partite_merce](vw_partite_merce.md)
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)
> Brief autorevole: `docs/it/dev/work-done/brief-design-partita-merce-generalizzata.md` §8.5

---

### 🎯 Scopo Principale

(rev 2026-08-17 — nuovo, slice S6a della partita di merce generalizzata)

Una riga di reso dice **da dove viene la merce** in due modi:

| Campo | |
|---|---|
| `ddt_riga_id` | la riga di spedizione da cui è tornata — **obbligatorio** |
| `ordine_riga_id` | la riga d'ordine, quando c'è — **facoltativo** |

Il secondo si **ricava** dal primo: basta guardare quale riga d'ordine quella
spedizione stava evadendo. È una comodità, non un'informazione nuova.

⚠️ **Ma finora nulla verificava che i due andassero d'accordo**, e sbagliarli
non è un difetto estetico.

---

### Cosa succede se il riferimento è sbagliato

Il residuo dell'ordine — *«quanto resta da spedire»* — si calcola sommando i
resi **per riga d'ordine**. Quindi:

* **campo vuoto su merce ordinata** → la merce torna indietro e **l'ordine non
  se ne accorge**: resta evaso, e nessuno rispedisce nulla;
* **campo che punta a un altro ordine** → si riapre il residuo di un ordine che
  con quella merce non c'entra.

⭐ Fino al 2026-08-17 il campo vuoto faceva anche **sparire il reso dal conto
della merce**. Quel danno è già chiuso — il conto ora si aggancia alla riga di
spedizione, che è obbligatoria — ma il residuo dell'ordine resta appeso a questa
colonna, e quindi il controllo serve ancora.

---

### La regola: due direzioni, non una

```text
la spedizione evade un ordine   →  il riferimento dev'esserci, e combaciare
la spedizione non evade nulla   →  il riferimento dev'essere vuoto
```

Sono lo **stesso errore visto dai due lati**: un riferimento che non descrive la
merce. Presidiarne una sola lascerebbe passare l'altra — e quella che passerebbe
è la più probabile, perché per lasciare un campo vuoto non serve sbagliare
nulla: basta non compilarlo.

> ⚠️ **«Combaciare» non vuol dire «essere il primo».** Una riga di spedizione
> può in teoria evadere più righe d'ordine. Il controllo chiede che il valore
> sia **una** di quelle: scegliere d'ufficio la prima sarebbe un arbitrio
> travestito da verifica.

---

### Perché è stato sicuro introdurlo

* **Zero violazioni** sulle righe di reso esistenti al 2026-08-17;
* il **backend fa già la cosa giusta**: ricava il riferimento dalla riga di
  spedizione, e chi chiama passa solo quella. Il controllo non cambia il
  percorso normale — copre le scritture che non ci passano;
* verificati **tutti** i file di test che creano righe di reso: nessuno ne
  risulta rotto.

---

### Errore restituito

`E_RESO_ORIGINE_INCOERENTE` (classe `DATO_ERRATO`): è un valore sbagliato in un
campo, non un conflitto fra stati. Il contesto dell'errore porta la riga di
spedizione, il riferimento proposto, quante origini valide esistevano e **quale
delle tre situazioni** si è verificata.

---

### Un onere non si rende

(rev 3-11-2026, `20261103-31`, brief `brief-db-addebito-trasporto-ordine` §8.1)

Dal 2026-11-03 la bolla puo' portare **oneri** (trasporto, spese). Prima di
guardare l'origine, il guard chiede se la riga di spedizione e' **merce**
([`script.fn_natura_e_merce`](/dbzero/script/funzioni/fn_natura_e_merce) sulla
natura congelata della riga): se e' un onere rifiuta con `E_RESO_RIGA_ONERE`
(classe `DATO_ERRATO`; nella frase numero di riga, bolla e codice
dell'articolo; bersaglio il reso, poi la bolla). Con questo rifiuto accredito,
riconsegna e coda degli accrediti sono a posto per costruzione: nessun reso
nasce su un onere.

Verifica: `db/pgtap/vendite/test-bolla-onere-partita-reso-v1.sql`.

---

### Note operative

* Fase **`_a20_`**, accanto al controllo sulle quantità e dopo quelli che
  verificano che spedizione e ordine esistano ancora: una coerenza fra due campi
  ha senso solo quando entrambi puntano a qualcosa.
* Scatta su inserimento e su modifica **dei due campi in questione**, non su
  ogni modifica della riga.
* Test: `db/pgtap/vendite/test-resi-righe-guard-origine-coerente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
