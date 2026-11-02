## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_magazzini_guard_usa_ubicazioni`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — `usa_ubicazioni`, dove è montato
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — ciò che legge

---

### 🎯 Scopo Principale

**`usa_ubicazioni` si cambia solo a registro vuoto.** Il flag decide la *grana* del registro
di quel magazzino (ogni movimento nomina un'ubicazione, o nessuno); se esiste un movimento del
magazzino, il cambio è rifiutato.

---

### Perché si decide alla nascita

Cambiare il flag con merce a registro lascerebbe righe scritte con l'altra grana — cioè la
convivenza «con e senza posizione» che il flag esiste per rendere impossibile. Si decide alla
nascita del magazzino, prima del primo movimento. Con merce dentro, la strada è un magazzino
nuovo con l'impostazione giusta e un trasferimento.

---

### Che cosa conta

* Contano i **movimenti**, non il saldo: anche a saldo zero le righe hanno la grana vecchia.
* Non contano gli attesi: una promessa non è merce a registro.
* Riscrivere lo stesso valore non è un cambio.

Il guard legge i movimenti con i permessi di chi scrive, sotto la sicurezza di riga del
magazzino: è lo stesso perimetro della riga che si sta modificando. È montato prima
dell'aggiornamento di `usa_ubicazioni`.

---

### Codici errore

* `E_MAG_MAGAZZINO_CON_GIACENZA` — cambio di `usa_ubicazioni` su un magazzino con movimenti a
  registro; il campo è `usa_ubicazioni`, la frase nomina il codice del magazzino.

---

### Test

`db/pgtap/magazzino/test-fn-scrivi-movimento-controlli-v1.sql` (test 16-17).

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§3 D-L2-m).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
