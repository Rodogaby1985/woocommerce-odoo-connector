# Conector WooCommerce ↔ Odoo

Conector bidireccional en tiempo real para sincronizar **productos, stock, precios, pedidos, clientes y categorías** entre WooCommerce y Odoo.

## Arquitectura

```text
WooCommerce --(webhooks)--> Flask Middleware --(Celery/Redis)--> Workers --> Odoo XML-RPC
     ^                                                                  |
     |--------------------(eventos desde Odoo Automated Actions)--------|
```

- **Middleware**: Flask + Celery
- **Broker**: Redis
- **Entrada WooCommerce**: `POST /webhook/woocommerce`
- **Entrada Odoo**: `POST /webhook/odoo`

## Entidades sincronizadas

| Entidad | Woo → Odoo | Odoo → Woo |
|---|---:|---:|
| Productos | ✅ | ✅ |
| Stock | ✅ (en producto) | ✅ |
| Precios | ✅ | ✅ |
| Pedidos | ✅ | ✅ (estado/stock vía tareas) |
| Clientes | ✅ | ✅ |
| Categorías | ✅ | ✅ |

## Requisitos previos

- Python 3.11+
- Redis 7+
- Instancia de WooCommerce con API REST habilitada
- Instancia de Odoo con acceso XML-RPC

## Instalación local

1. Clonar repositorio.
2. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copiar variables:
   ```bash
   cp .env.example .env
   ```
4. Ejecutar Flask:
   ```bash
   gunicorn -w 2 -b 0.0.0.0:8000 connector.webhook_server:app
   ```
5. Ejecutar worker Celery:
   ```bash
   celery -A connector.tasks.celery_app worker --loglevel=info
   ```

## Instalación con Docker

```bash
docker compose up --build
```

Servicios:
- `redis`
- `middleware`
- `worker`

## Variables de entorno

Ver `.env.example`.

Campos clave:
- `WC_URL`, `WC_CONSUMER_KEY`, `WC_CONSUMER_SECRET`
- `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`
- `WEBHOOK_SECRET`
- `CELERY_BROKER`

## Configuración de webhooks en WooCommerce

Configurar webhooks apuntando a:
- `https://TU_MIDDLEWARE/webhook/woocommerce`

Topics soportados:
- `product.created`, `product.updated`
- `order.created`, `order.updated`
- `customer.created`, `customer.updated`

La firma se valida con `X-WC-Webhook-Signature` (HMAC-SHA256 + Base64).

## Configuración de Automated Actions en Odoo

Crear acciones automáticas para:
- Productos (`product.template`) usando `odoo_actions/product_action.py`
- Stock (`stock.quant`) usando `odoo_actions/stock_action.py`

Endpoint destino:
- `https://TU_MIDDLEWARE/webhook/odoo`

Eventos soportados:
- `product.write`
- `stock.change`

## Campo personalizado `x_wc_id` en Odoo

Se recomienda crear el campo técnico `x_wc_id` en `product.template` y `res.partner` para rastrear el ID remoto de WooCommerce y evitar duplicados.

## Prevención de bucles

`connector/loop_prevention.py` usa Redis para bloquear ecos recientes con un cooldown configurable (por defecto 30s).

## Mejores prácticas

- Usar HTTPS en todos los endpoints.
- Rotar secrets periódicamente.
- Monitorear logs de Celery y Flask.
- Agregar colas separadas por tipo de entidad cuando haya alto volumen.

## Troubleshooting

- **401 en webhook de WooCommerce**: verificar `WEBHOOK_SECRET` y firma.
- **Eventos no procesados**: revisar que Celery worker esté levantado.
- **Errores XML-RPC**: validar credenciales y permisos de modelos en Odoo.
- **Loops de sincronización**: revisar conectividad a Redis y TTL de claves.
