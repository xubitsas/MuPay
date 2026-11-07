"""
MuPay — Prueba técnica en Stellar testnet
=========================================

Demuestra el núcleo de MuPay con multisig nativo de Stellar (sin Soroban):

  1. Se crea el fondo: una cuenta "pozo" con 3 integrantes como firmantes
     (peso 1 cada uno), umbral 2 (quórum 2 de 3) y la clave maestra en peso 0.
     Nadie, ni siquiera quien creó el pozo, puede mover fondos solo.
  2. Cada integrante aporta al pozo.
  3. Se arma UNA transacción con un pago por proveedor (atómica: sale todo o nada).
     - Con 1 sola firma, la red la rechaza (tx_bad_auth).
     - Con 2 firmas (quórum), la red la acepta y paga a todos.

Como asset de los aportes usa "MUSD", un dólar de prueba emitido por el propio
script (reemplaza al USDC de testnet para no depender de faucets externos).

Uso:
    pip install stellar-sdk requests
    python spike_quorum.py

Genera keys-testnet.json con las claves de las cuentas de PRUEBA (testnet, sin
valor). Igual no se sube al repo: está en .gitignore.
"""

import json
import sys
import time

import requests
from stellar_sdk import (
    Asset,
    Keypair,
    Network,
    Server,
    Signer,
    TransactionBuilder,
)
from stellar_sdk.exceptions import BadRequestError

try:  # consola de Windows: evitar errores con tildes y símbolos
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HORIZON = "https://horizon-testnet.stellar.org"
FRIENDBOT = "https://friendbot.stellar.org"
PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
EXPERT = "https://stellar.expert/explorer/testnet"

server = Server(HORIZON)
evidence = []  # (descripción, link)


def tx_link(h):
    return f"{EXPERT}/tx/{h}"


def acc_link(pk):
    return f"{EXPERT}/account/{pk}"


def fund(name, kp):
    r = requests.get(FRIENDBOT, params={"addr": kp.public_key}, timeout=60)
    if r.status_code != 200 and "createAccountAlreadyExist" not in r.text:
        sys.exit(f"Friendbot falló para {name}: {r.status_code} {r.text[:200]}")
    print(f"  ✓ {name:<12} {kp.public_key}")


def builder(source_pk):
    return TransactionBuilder(
        source_account=server.load_account(source_pk),
        network_passphrase=PASSPHRASE,
        base_fee=100,
    ).set_timeout(300)


def submit(tx, desc):
    res = server.submit_transaction(tx)
    evidence.append((desc, tx_link(res["hash"])))
    print(f"  ✓ {desc}\n    {tx_link(res['hash'])}")
    return res


def main():
    names = ["emisor", "pozo", "ana", "bruno", "carla", "proveedor1", "proveedor2"]
    kp = {n: Keypair.random() for n in names}
    with open("keys-testnet.json", "w") as f:
        json.dump({n: {"public": k.public_key, "secret": k.secret} for n, k in kp.items()}, f, indent=2)

    musd = Asset("MUSD", kp["emisor"].public_key)
    integrantes = ["ana", "bruno", "carla"]
    proveedores = {"proveedor1": "90", "proveedor2": "60"}  # líneas de gasto acordadas

    print("\n[0] Creando cuentas de prueba con Friendbot")
    for n in names:
        fund(n, kp[n])

    print("\n[1] Trustlines a MUSD (cada cuenta acepta el asset) y emisión a integrantes")
    for n in ["pozo"] + integrantes + list(proveedores):
        tx = builder(kp[n].public_key).append_change_trust_op(asset=musd).build()
        tx.sign(kp[n])
        server.submit_transaction(tx)
    tx = builder(kp["emisor"].public_key)
    for n in integrantes:
        tx.append_payment_op(destination=kp[n].public_key, asset=musd, amount="100")
    tx = tx.build()
    tx.sign(kp["emisor"])
    submit(tx, "Emisión de 100 MUSD a cada integrante")

    print("\n[2] Se crea el fondo: multisig 2 de 3, clave maestra desactivada")
    tx = builder(kp["pozo"].public_key)
    for n in integrantes:
        tx.append_set_options_op(signer=Signer.ed25519_public_key(kp[n].public_key, 1))
    tx.append_set_options_op(master_weight=0, low_threshold=2, med_threshold=2, high_threshold=2)
    tx = tx.build()
    tx.sign(kp["pozo"])  # última vez que firma la clave maestra
    submit(tx, "Pozo configurado: firmantes Ana, Bruno y Carla, quórum 2 de 3")

    print("\n[3] Aportes: cada integrante pone 50 MUSD")
    for n in integrantes:
        tx = builder(kp[n].public_key).append_payment_op(
            destination=kp["pozo"].public_key, asset=musd, amount="50"
        ).build()
        tx.sign(kp[n])
        submit(tx, f"Aporte de {n.capitalize()}: 50 MUSD")

    def pago_atomico():
        tx = builder(kp["pozo"].public_key)
        for n, monto in proveedores.items():
            tx.append_payment_op(destination=kp[n].public_key, asset=musd, amount=monto)
        return tx.build()

    print("\n[4a] Intento de pago con UNA sola firma (Ana) → debe rechazarse")
    tx = pago_atomico()
    tx.sign(kp["ana"])
    try:
        server.submit_transaction(tx)
        sys.exit("  ✗ ERROR: la red aceptó un pago sin quórum")
    except BadRequestError as e:
        code = (e.extras or {}).get("result_codes", {}).get("transaction")
        print(f"  ✓ Rechazado por la red: {code}")
        evidence.append(("Pago con 1 firma rechazado por la red", code))

    print("\n[4b] Pago con quórum (Ana + Bruno) → una transacción, dos proveedores")
    time.sleep(1)
    tx = pago_atomico()
    tx.sign(kp["ana"])
    tx.sign(kp["bruno"])
    submit(tx, "Pago atómico aprobado 2 de 3: 90 MUSD a proveedor 1 y 60 MUSD a proveedor 2")

    print("\n[5] Saldos finales")
    for n in ["pozo"] + list(proveedores):
        bal = next(
            (b["balance"] for b in server.accounts().account_id(kp[n].public_key).call()["balances"]
             if b.get("asset_code") == "MUSD"),
            "0",
        )
        print(f"  {n:<12} {bal} MUSD")

    print("\n=== Evidencia (para el formulario / SOW) ===")
    print(f"Cuenta del pozo: {acc_link(kp['pozo'].public_key)}")
    for d, l in evidence:
        print(f"- {d}: {l}")
    with open("evidencia-testnet.md", "w", encoding="utf-8") as f:
        f.write("# MuPay — Evidencia prueba técnica en testnet\n\n")
        f.write(f"Cuenta del pozo: {acc_link(kp['pozo'].public_key)}\n\n")
        for d, l in evidence:
            f.write(f"- {d}: {l}\n")
    print("\nGuardado en evidencia-testnet.md")


if __name__ == "__main__":
    main()
