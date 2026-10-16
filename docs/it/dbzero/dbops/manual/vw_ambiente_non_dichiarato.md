## 📘 Documentazione Concettuale – View `dbops.vw_ambiente_non_dichiarato`

> 👀 **Vedi anche**
>
> [dbops.installazione](/dbzero/dbops/manual/installazione) ·
> [script.fn_ambiente_installazione](/dbzero/script/manual/fn_ambiente_installazione)

### 🎯 Scopo
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**Presidio**: una riga se questa installazione non ha ancora dichiarato se è
di sviluppo o di produzione. **Deve restare vuota.**

La tabella [dbops.installazione](/dbzero/dbops/manual/installazione) nasce
vuota di proposito: l'ambiente si sceglie alla fase `post` del provisioning
(`-v ambiente=SVILUPPO` oppure `-v ambiente=PRODUZIONE`). Finché manca, il
provisioning dei dati di prova non parte e le sveglie dei processi spegnibili
falliscono con `E_CONFIG_MANCANTE`. Ognuna di quelle voci dice il sintomo;
questo presidio dice la **causa**, una volta, a chi la può sistemare: chi
gestisce il database.

Il panorama dei processi non ha una causa per questo: un fatto, un presidio.

### Forma

Una colonna, `database_nome`. Legge `script.fn_ambiente_dichiarato()`, che non
solleva. In CI è vuota (la CI dichiara `SVILUPPO`): il caso positivo lo
costruisce `db/pgtap/dbops/test-installazione-ambiente-v1.sql` (test 14).

Catalogo dei presidi: natura `ZERO`, cadenza giornaliera, chi agisce
`SISTEMISTA`.

---

{% include-markdown "signature-core.md" %}
