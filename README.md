  # MuPay

Vaquita grupal sobre Stellar.

Para grupos que juntan plata para un viaje, un regalo o un gasto compartido,
sin depender de que una sola persona maneje los fondos.

Cada pozo es una cuenta multisig: los que aportan son firmantes y los pagos
a proveedores solo salen cuando aprueba el quórum, en una sola transacción
atómica. Se paga todo o nada.

## Cómo funciona

1. Se crea el pozo con sus líneas de gasto (proveedor + monto), definidas desde el inicio.
2. Cada miembro aporta USDC desde su wallet y queda registrado quién puso cuánto.
3. Al llegar al objetivo, se avisa a todos los firmantes.
4. Cualquier firmante propone liberar los fondos y los demás aprueban hasta alcanzar el quórum.
5. Con el quórum alcanzado, una sola transacción paga todas las líneas.
6. Si se cancela, a cada uno se le devuelve su parte, con el mismo quórum.

## Stack

- Python (FastAPI + Celery)
- stellar-sdk
- Multisig nativo de Stellar, sin contratos propios
- USDC
- Red: Stellar testnet (sprint actual)

## Estado

Arquitectura definida. El desarrollo arranca con el próximo sprint
(30 días, desde el 16/11/2026): núcleo en testnet.

- [ ] Pozo multisig con líneas de gasto y registro de aportes
- [ ] Liberación por quórum con pago atómico y devolución proporcional
- [ ] Demo de punta a punta y prueba con 3 grupos reales

## Equipo

Desarrollado por XUBIT SAS (Buenos Aires).

- Juan Manuel Servente — Cofundador y CEO
- Ivan Sanchez — Cofundador y CTO
